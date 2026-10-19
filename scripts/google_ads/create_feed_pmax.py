#!/usr/bin/env python3
"""Založení feedové PMax (retail, skupina podkladů BEZ podkladů) se stromem podle kategorií.

Nastavení se kopíruje z referenční PMax (merchant, feed label, lokální zboží, geo typ, asset automation,
brand guidelines, lokality, jazyky, vylučující slova kampaně (mimo „skip_negatives“), kampaňové podklady — logo,
název firmy, sitelinky).
Retail asset group bez podkladů je podle dokumentace platná (performance-max/structure-requests).

BEZPEČNOST: kampaň vzniká VŽDY jako PAUSED. Bez přepínače jen výpis; --validate = validate_only;
--apply = zápis (jen schválený plán); vše v jednom atomickém mutate; po zápisu read-back.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/create_feed_pmax.py clients/<plan>.json [--validate|--apply]

Plán:
{"customer_id": "…", "reference_campaign_id": "…", "name": "Pmax_Feed_Kategorie", "asset_group_name": "Kategorie",
 "daily_budget": 80, "target_roas": 5.0,
 "tree": {"mode": "include", "paths": [[1, 2]], "exclude_custom_attribute": {"index": "INDEX1", "value": "sezona-vyprodej"}},
 # ID kategorií a štítek jsou smyšlené; skutečná Google category ID vezmi z taxonomie produktů
 "approval": {"status": "approved", …}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402
from pmax_category_tree import tree_ops, print_tree  # noqa: E402

COPY_ASSET_TYPES = ("LOGO", "LANDSCAPE_LOGO", "BUSINESS_NAME", "SITELINK")


def too_small(row) -> bool:
    """Loga pod minimem Google (LOGO 128×128, LANDSCAPE_LOGO 512×128) nepřebírat — u reference
    můžou viset ze starší doby, ale nová vazba skončí DIMENSIONS_NOT_ALLOWED (ověřeno 2026-10-07)."""
    ft = row.campaign_asset.field_type.name
    w, h = row.asset.image_asset.full_size.width_pixels, row.asset.image_asset.full_size.height_pixels
    if ft == "LOGO" and (w < 128 or h < 128):
        print(f"  přeskakuji LOGO {row.campaign_asset.asset} ({w}×{h}) — pod minimem 128×128")
        return True
    if ft == "LANDSCAPE_LOGO" and (w < 512 or h < 128):
        print(f"  přeskakuji LANDSCAPE_LOGO {row.campaign_asset.asset} ({w}×{h}) — pod minimem 512×128")
        return True
    return False


def read_reference(client, cid, camp_id):
    svc = client.get_service("GoogleAdsService")
    q = ("SELECT campaign.shopping_setting.merchant_id, campaign.shopping_setting.feed_label, "
         "campaign.shopping_setting.enable_local, campaign.geo_target_type_setting.positive_geo_target_type, "
         "campaign.geo_target_type_setting.negative_geo_target_type, campaign.brand_guidelines_enabled, "
         "campaign.asset_automation_settings, campaign.advertising_channel_type "
         f"FROM campaign WHERE campaign.id = {camp_id}")
    ref = next(r.campaign for b in svc.search_stream(customer_id=cid, query=q) for r in b.results)
    if ref.advertising_channel_type.name != "PERFORMANCE_MAX":
        raise SystemExit("Referenční kampaň není PMax.")
    crit = [r.campaign_criterion for b in svc.search_stream(customer_id=cid, query=(
        "SELECT campaign.id, campaign_criterion.type, campaign_criterion.negative, "
        "campaign_criterion.location.geo_target_constant, campaign_criterion.language.language_constant "
        f"FROM campaign_criterion WHERE campaign.id = {camp_id} AND campaign_criterion.type IN ('LOCATION','LANGUAGE')"))
        for r in b.results]
    # Vylučující slova kampaně — bez nich nová PMax chytá i dotazy, které reference blokuje
    # (reálný případ 2026-10: v dotazech nové kampaně se objevily značky konkurence,
    # protože se negativa z reference nepřenesla).
    negs = [r.campaign_criterion for b in svc.search_stream(customer_id=cid, query=(
        "SELECT campaign.id, campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
        f"FROM campaign_criterion WHERE campaign.id = {camp_id} AND campaign_criterion.type = 'KEYWORD' "
        "AND campaign_criterion.negative = TRUE"))
        for r in b.results]
    assets = [(r.campaign_asset.field_type.name, r.campaign_asset.asset) for b in svc.search_stream(customer_id=cid, query=(
        "SELECT campaign.id, campaign_asset.field_type, campaign_asset.asset, campaign_asset.status, "
        "asset.image_asset.full_size.width_pixels, asset.image_asset.full_size.height_pixels "
        f"FROM campaign_asset WHERE campaign.id = {camp_id} AND campaign_asset.status = 'ENABLED'"))
        for r in b.results if r.campaign_asset.field_type.name in COPY_ASSET_TYPES and not too_small(r)]
    return ref, crit, assets, negs


def main() -> None:
    p = argparse.ArgumentParser(description="Založení feedové PMax (PAUSED)")
    p.add_argument("plan")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    if args.apply and (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Plán není schválený (approval.status).")
    cid = normalize_cid(plan["customer_id"], "write")
    client = build_client()
    ref, crit, assets, negs = read_reference(client, cid, plan["reference_campaign_id"])
    skip = {t.lower() for t in plan.get("skip_negatives", [])}  # např. negativa, která v nové kampani nedávají smysl
    negs = [n for n in negs if n.keyword.text.lower() not in skip]
    e = client.enums
    BUD, CAMP, AG = -1, -2, -3
    bud_rn = f"customers/{cid}/campaignBudgets/{BUD}"
    camp_rn = f"customers/{cid}/campaigns/{CAMP}"
    ops = []

    op = client.get_type("MutateOperation")
    b = op.campaign_budget_operation.create
    b.resource_name = bud_rn
    b.name = f"{plan['name']} budget"
    b.amount_micros = int(plan["daily_budget"] * 1_000_000)
    b.delivery_method = e.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    ops.append(op)

    op = client.get_type("MutateOperation")
    c = op.campaign_operation.create
    c.resource_name = camp_rn
    c.name = plan["name"]
    c.status = e.CampaignStatusEnum.PAUSED
    c.advertising_channel_type = e.AdvertisingChannelTypeEnum.PERFORMANCE_MAX
    c.campaign_budget = bud_rn
    c.maximize_conversion_value.target_roas = plan["target_roas"]
    c.shopping_setting.merchant_id = ref.shopping_setting.merchant_id
    if ref.shopping_setting.feed_label:
        c.shopping_setting.feed_label = ref.shopping_setting.feed_label
    c.shopping_setting.enable_local = ref.shopping_setting.enable_local
    c.geo_target_type_setting.positive_geo_target_type = ref.geo_target_type_setting.positive_geo_target_type
    c.geo_target_type_setting.negative_geo_target_type = ref.geo_target_type_setting.negative_geo_target_type
    c.brand_guidelines_enabled = ref.brand_guidelines_enabled
    c.contains_eu_political_advertising = e.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    for s in ref.asset_automation_settings:
        x = client.get_type("Campaign").AssetAutomationSetting()
        x.asset_automation_type = s.asset_automation_type
        x.asset_automation_status = s.asset_automation_status
        c.asset_automation_settings.append(x)
    ops.append(op)

    for cr in crit:
        op = client.get_type("MutateOperation")
        n = op.campaign_criterion_operation.create
        n.campaign = camp_rn
        n.negative = cr.negative
        if cr.type_.name == "LOCATION":
            n.location.geo_target_constant = cr.location.geo_target_constant
        else:
            n.language.language_constant = cr.language.language_constant
        ops.append(op)

    for n_ in negs:
        op = client.get_type("MutateOperation")
        n = op.campaign_criterion_operation.create
        n.campaign = camp_rn
        n.negative = True
        n.keyword.text = n_.keyword.text
        n.keyword.match_type = n_.keyword.match_type
        ops.append(op)

    for ft, asset_rn in assets:
        op = client.get_type("MutateOperation")
        ca = op.campaign_asset_operation.create
        ca.campaign = camp_rn
        ca.asset = asset_rn
        ca.field_type = getattr(e.AssetFieldTypeEnum, ft)
        ops.append(op)

    op = client.get_type("MutateOperation")
    ag = op.asset_group_operation.create
    ag.resource_name = f"customers/{cid}/assetGroups/{AG}"
    ag.name = plan["asset_group_name"]
    ag.campaign = camp_rn
    ag.status = e.AssetGroupStatusEnum.ENABLED
    ops.append(op)

    t = plan["tree"]
    tree = tree_ops(client, cid, str(AG), t["mode"], t["paths"], t.get("exclude_custom_attribute"))
    ops += tree

    print(f"Kampaň „{plan['name']}“ PAUSED, rozpočet {plan['daily_budget']}/den, tROAS {plan['target_roas']}, "
          f"merchant {ref.shopping_setting.merchant_id}, lokalit/jazyků {len(crit)}, negativ {len(negs)}, kampaňových podkladů {len(assets)}, "
          f"uzlů stromu {len(tree)} (režim {t['mode']}, {len(t['paths'])} kategorií).")
    if not (args.validate or args.apply):
        print("DRY-RUN: nic neodesláno.")
        return
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = cid
    req.mutate_operations.extend(ops)
    req.partial_failure = False
    req.validate_only = not args.apply
    resp = client.get_service("GoogleAdsService").mutate(request=req)
    if not args.apply:
        print("VALIDACE OK (nic nezapsáno)")
        return
    new_camp = resp.mutate_operation_responses[1].campaign_result.resource_name
    new_ag = next(r.asset_group_result.resource_name for r in resp.mutate_operation_responses
                  if r.asset_group_result.resource_name)
    print(f"ZAPSÁNO: {new_camp}, {new_ag}")
    print_tree(client, cid, new_ag.split("/")[-1])


if __name__ == "__main__":
    main()

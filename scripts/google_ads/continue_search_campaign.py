#!/usr/bin/env python3
"""Dokončí pozastavenou Search kampaň po přerušení před sestavami.

Používej jen s existující PAUSED kampaní. Default je dry-run; --apply zapisuje
jen rozšíření, sestavy, klíčová slova a RSA z plánu — nevytváří rozpočet ani kampaň.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402
from create_search_campaign import _mutate_exemptible, match_enum, print_plan, validate  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Dokončení pozastavené Search kampaně")
    p.add_argument("customer_id")
    p.add_argument("campaign_id")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--skip-assets", action="store_true", help="Přeskočí rozšíření, která už byla zapsána")
    p.add_argument("--assets-only", action="store_true", help="Zapíše jen rozšíření a skončí")
    p.add_argument("--snippets-only", action="store_true", help="Zapíše jen structured snippety")
    args = p.parse_args()
    cid = normalize_cid(args.customer_id)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    print_plan(plan, args.customer_id)
    errs = validate(plan)
    if errs:
        for err in errs:
            print(f"CHYBA: {err}")
        raise SystemExit(1)
    if not args.apply:
        print(f"\nDRY-RUN — dokončil by kampaň {args.campaign_id}; nic nezapsáno.")
        return

    client = build_client()
    campaign_rn = f"customers/{cid}/campaigns/{args.campaign_id}"
    svc = client.get_service("GoogleAdsService")
    q = ("SELECT campaign.name, campaign.status, campaign.advertising_channel_type "
         f"FROM campaign WHERE campaign.id = {args.campaign_id}")
    rows = [r for batch in svc.search_stream(customer_id=cid, query=q) for r in batch.results]
    if len(rows) != 1 or rows[0].campaign.status.name != "PAUSED" or rows[0].campaign.advertising_channel_type.name != "SEARCH":
        raise SystemExit("Cílová kampaň neexistuje, není PAUSED nebo není typu SEARCH — zápis zastaven.")

    camp = plan["campaign"]
    assets = {} if args.skip_assets else camp.get("campaign_assets", {})
    if args.snippets_only:
        assets = {"structured_snippets": assets.get("structured_snippets", [])}
    asset_svc = client.get_service("AssetService")
    campaign_asset_svc = client.get_service("CampaignAssetService")
    ft = client.enums.AssetFieldTypeEnum
    asset_specs = []
    for spec in assets.get("sitelinks", []):
        op = client.get_type("AssetOperation")
        sl = op.create.sitelink_asset
        sl.link_text, sl.description1, sl.description2 = spec["text"], spec.get("description1", ""), spec.get("description2", "")
        op.create.final_urls.append(spec["final_url"])
        asset_specs.append((ft.SITELINK, op))
    for text in assets.get("callouts", []):
        op = client.get_type("AssetOperation")
        op.create.callout_asset.callout_text = text
        asset_specs.append((ft.CALLOUT, op))
    for spec in assets.get("structured_snippets", []):
        op = client.get_type("AssetOperation")
        op.create.structured_snippet_asset.header = spec["header"]
        op.create.structured_snippet_asset.values.extend(spec["values"])
        asset_specs.append((ft.STRUCTURED_SNIPPET, op))
    for field_type, op in asset_specs:
        asset_rn = asset_svc.mutate_assets(customer_id=cid, operations=[op]).results[0].resource_name
        link = client.get_type("CampaignAssetOperation")
        link.create.campaign, link.create.asset, link.create.field_type = campaign_rn, asset_rn, field_type
        campaign_asset_svc.mutate_campaign_assets(customer_id=cid, operations=[link])
    print(f"✓ Rozšíření: {len(asset_specs)} assetů")
    if args.assets_only:
        print(f"✅ Rozšíření doplněna: {campaign_rn} zůstává PAUSED.")
        return

    ag_svc = client.get_service("AdGroupService")
    agc_svc = client.get_service("AdGroupCriterionService")
    aga_svc = client.get_service("AdGroupAdService")
    for a in plan["ad_groups"]:
        ag_op = client.get_type("AdGroupOperation")
        ag = ag_op.create
        ag.name, ag.campaign, ag.status, ag.type_ = a["name"], campaign_rn, client.enums.AdGroupStatusEnum.ENABLED, client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ag_rn = ag_svc.mutate_ad_groups(customer_id=cid, operations=[ag_op]).results[0].resource_name
        kw_ops = []
        for k in a["keywords"]:
            op = client.get_type("AdGroupCriterionOperation")
            op.create.ad_group, op.create.status = ag_rn, client.enums.AdGroupCriterionStatusEnum.ENABLED
            op.create.keyword.text, op.create.keyword.match_type = k["text"], match_enum(client, k.get("match"))
            kw_ops.append(op)
        _mutate_exemptible(client, agc_svc.mutate_ad_group_criteria, cid, kw_ops)
        ad_op = client.get_type("AdGroupAdOperation")
        ad_op.create.ad_group, ad_op.create.status = ag_rn, client.enums.AdGroupAdStatusEnum.ENABLED
        ad_op.create.ad.final_urls.append(a["rsa"].get("final_url") or a["final_url"])
        rsa = ad_op.create.ad.responsive_search_ad
        for text in dict.fromkeys(a["rsa"]["headlines"]):
            asset = client.get_type("AdTextAsset"); asset.text = text; rsa.headlines.append(asset)
        for text in dict.fromkeys(a["rsa"]["descriptions"]):
            asset = client.get_type("AdTextAsset"); asset.text = text; rsa.descriptions.append(asset)
        _mutate_exemptible(client, aga_svc.mutate_ad_group_ads, cid, [ad_op])
        print(f"✓ Sestava '{a['name']}': {len(a['keywords'])} KW + 1 RSA")
    print(f"✅ Dokončeno: {campaign_rn} zůstává PAUSED.")


if __name__ == "__main__":
    main()

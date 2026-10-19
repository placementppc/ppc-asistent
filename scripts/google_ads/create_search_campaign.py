#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Založení celé NOVÉ Search kampaně z plán-JSONu (rozpočet + kampaň + sestavy + KW + RSA).

Kampaň se zakládá jako PAUSED — nic se nezačne zobrazovat, dokud ji ručně nespustíš.
AI reklamní texty tak projdou lidskou kontrolou (a Google je stejně schvaluje).

BEZPEČNOST:
- Default DRY-RUN: jen vypíše, co by založil + zkontroluje délky RSA. NIC nezapíše.
- Reálný zápis jen s --apply. Zakládá SÉRIOVĚ (žádný paralelní souběh), na chybu zastaví
  a vypíše, co už vzniklo (kvůli případnému úklidu).
- Validace: nadpis ≤ 30, popis ≤ 90, 3–15 nadpisů, 2–4 popisy. Při překročení NEzapíše.

Plán (JSON) — formát generovaný builderem:
{
  "campaign": {
    "name": "...", "daily_budget_czk": 400,
    "campaign_negatives": [{"text": "...", "match": "PHRASE|BROAD|EXACT"}, ...],
    "campaign_assets": {
      "sitelinks": [{"text": "...", "description1": "...", "description2": "...", "final_url": "https://..."}],
      "callouts": ["..."],
      "structured_snippets": [{"header": "Types", "values": ["...", "..."]}]
    }
  },
  "ad_groups": [
    {
      "name": "...", "final_url": "https://...",
      "keywords": [{"text": "...", "match": "PHRASE|EXACT|BROAD"}, ...],
      "rsa": {"headlines": [...], "descriptions": [...], "final_url": "https://..."}
    }, ...
  ]
}

Použití:
  python scripts/google_ads/create_search_campaign.py <customer_id> <plan.json>          # náhled
  python scripts/google_ads/create_search_campaign.py <customer_id> <plan.json> --apply  # zápis
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


def _mutate_exemptible(client, mutate_fn, cid, ops):
    """Zavolá mutate; když padne na EXEMPTIBLE policy violation (typicky u citlivých
    kategorií), odbaví ji prohlášením
    (exempt_policy_violation_keys) a zopakuje. Neexemptible chyby propadnou dál.
    """
    from google.ads.googleads.errors import GoogleAdsException
    try:
        return mutate_fn(customer_id=cid, operations=ops)
    except GoogleAdsException as ex:
        keys, non_exemptible = [], []
        for err in ex.failure.errors:
            pv = err.details.policy_violation_details
            if pv and pv.is_exemptible:
                keys.append(pv.key)
            elif err.details.policy_violation_details:
                non_exemptible.append(err.message)
        if not keys or non_exemptible:
            raise
        for op in ops:
            op.exempt_policy_violation_keys.extend(keys)
        return mutate_fn(customer_id=cid, operations=ops)


H_MAX, D_MAX = 30, 90
# Geo/jazyk konstanty Google Ads
GEO_CZECHIA = "geoTargetConstants/2203"     # Czech Republic
LANG_CZECH = "languageConstants/1021"       # Czech


def validate(plan: dict) -> list[str]:
    errs = []
    camp = plan.get("campaign", {})
    if not camp.get("name"):
        errs.append("chybí campaign.name")
    if not camp.get("daily_budget_czk"):
        errs.append("chybí campaign.daily_budget_czk")
    assets = camp.get("campaign_assets", {})
    for sl in assets.get("sitelinks", []):
        if not sl.get("text") or not sl.get("final_url"):
            errs.append("sitelink musí mít text a final_url")
        for field, limit in (("text", 25), ("description1", 35), ("description2", 35)):
            if len(sl.get(field, "")) > limit:
                errs.append(f"sitelink.{field} je delší než {limit} znaků: '{sl[field]}'")
    for callout in assets.get("callouts", []):
        if len(callout) > 25:
            errs.append(f"callout je delší než 25 znaků: '{callout}'")
    for snippet in assets.get("structured_snippets", []):
        if not snippet.get("header") or not snippet.get("values"):
            errs.append("structured snippet musí mít header a values")
        for value in snippet.get("values", []):
            if len(value) > 25:
                errs.append(f"hodnota structured snippetu je delší než 25 znaků: '{value}'")
    ags = plan.get("ad_groups", [])
    if not ags:
        errs.append("žádné ad_groups")
    for ag in ags:
        nm = ag.get("name", "?")
        if not ag.get("keywords"):
            errs.append(f"[{nm}] žádná klíčová slova")
        rsa = ag.get("rsa", {})
        h, d = rsa.get("headlines", []), rsa.get("descriptions", [])
        if not (3 <= len(h) <= 15):
            errs.append(f"[{nm}] nadpisů musí být 3–15 (je {len(h)})")
        if not (2 <= len(d) <= 4):
            errs.append(f"[{nm}] popisů musí být 2–4 (je {len(d)})")
        for t in h:
            if len(t) > H_MAX:
                errs.append(f"[{nm}] nadpis {len(t)}>{H_MAX}: '{t}'")
        for t in d:
            if len(t) > D_MAX:
                errs.append(f"[{nm}] popis {len(t)}>{D_MAX}: '{t}'")
        if not (rsa.get("final_url") or ag.get("final_url")):
            errs.append(f"[{nm}] chybí final_url")
        # POLICY (telefonní čísla apod.) — SystemExit při nálezu
        from lib.policy import check_ad_texts
        check_ad_texts(h, context=f"nadpisy RSA [{nm}]")
        check_ad_texts(d, context=f"popisky RSA [{nm}]")
    from lib.policy import check_ad_texts
    check_ad_texts(
        [x for sl in assets.get("sitelinks", []) for x in (sl.get("text"), sl.get("description1"), sl.get("description2"))]
        + list(assets.get("callouts", []))
        + [x for s in assets.get("structured_snippets", []) for x in s.get("values", [])],
        context="sitelinky/callouty/snippety",
    )
    return errs


def match_enum(client, m: str):
    return getattr(client.enums.KeywordMatchTypeEnum, (m or "PHRASE").upper())


def print_plan(plan: dict, customer_id: str) -> None:
    camp = plan["campaign"]
    ags = plan["ad_groups"]
    total_kw = sum(len(a.get("keywords", [])) for a in ags)
    print(f"PLÁN: nová Search kampaň → účet {customer_id}")
    print(f"  Název:    {camp['name']}")
    print(f"  Rozpočet: {camp['daily_budget_czk']} Kč/den")
    print(f"  Bidding:  Maximalizace konverzí (bez cíle, učení)")
    print(f"  Stav:     PAUSED (nezobrazuje se, dokud ručně nespustíš)")
    print(f"  Síť:      jen Google Vyhledávání (bez Display, bez partnerů)")
    print(f"  Geo/jazyk: Česko / čeština")
    print(f"  Sestav: {len(ags)} · klíčových slov: {total_kw} · "
          f"negativ (kampaň): {len(camp.get('campaign_negatives', []))}")
    assets = camp.get("campaign_assets", {})
    print(f"  Rozšíření: {len(assets.get('sitelinks', []))} sitelinky · "
          f"{len(assets.get('callouts', []))} callouty · "
          f"{len(assets.get('structured_snippets', []))} structured snippety")
    for a in ags:
        print(f"\n  ── Sestava: {a['name']}  ({len(a.get('keywords', []))} KW)")
        print(f"     URL: {a.get('final_url') or a['rsa'].get('final_url')}")
        kws = ", ".join(f"{k['text']}[{k['match'][:1]}]" for k in a["keywords"][:6])
        more = "" if len(a["keywords"]) <= 6 else f" … (+{len(a['keywords'])-6})"
        print(f"     KW: {kws}{more}")
        print(f"     RSA: {len(a['rsa']['headlines'])} nadpisů / {len(a['rsa']['descriptions'])} popisů")


def main() -> None:
    p = argparse.ArgumentParser(description="Založení celé nové Search kampaně z plánu")
    p.add_argument("customer_id")
    p.add_argument("plan", help="Cesta k plán JSON")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ založí (jinak dry-run)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))

    print_plan(plan, args.customer_id)

    errs = validate(plan)
    if errs:
        print("\n🔴 CHYBY (nezapíšu ani s --apply):")
        for e in errs:
            print(f"  - {e}")
        raise SystemExit(1)

    if not args.apply:
        print("\n🟡 DRY-RUN — nic nezaloženo. Pro provedení přidej --apply")
        return

    # ---------- Reálný zápis (sériově) ----------
    print("\n🔴 --apply: zakládám kampaň (sériově)...")
    client = build_client()
    camp = plan["campaign"]
    created: list[str] = []  # log vzniklých objektů pro případný úklid

    try:
        # 1) Rozpočet
        budget_svc = client.get_service("CampaignBudgetService")
        b_op = client.get_type("CampaignBudgetOperation")
        b = b_op.create
        b.name = f"{camp['name']} — rozpočet"
        b.amount_micros = int(round(float(camp["daily_budget_czk"]) * 1_000_000))
        b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        b.explicitly_shared = False
        budget_rn = budget_svc.mutate_campaign_budgets(
            customer_id=cid, operations=[b_op]).results[0].resource_name
        created.append(budget_rn)
        print(f"  ✓ Rozpočet: {budget_rn}")

        # 2) Kampaň (PAUSED, Search, Maximalizace konverzí)
        camp_svc = client.get_service("CampaignService")
        c_op = client.get_type("CampaignOperation")
        c = c_op.create
        c.name = camp["name"]
        c.status = client.enums.CampaignStatusEnum.PAUSED
        c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        c.campaign_budget = budget_rn
        c.maximize_conversions = client.get_type("MaximizeConversions")  # bez target_cpa = čistá max. konverzí
        # Povinné od API v24: deklarace politické reklamy EU (naše = neobsahuje)
        c.contains_eu_political_advertising = (
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        )
        ns = c.network_settings
        ns.target_google_search = True
        ns.target_search_network = False          # bez vyhledávacích partnerů
        ns.target_content_network = False         # bez Display
        ns.target_partner_search_network = False
        campaign_rn = camp_svc.mutate_campaigns(
            customer_id=cid, operations=[c_op]).results[0].resource_name
        created.append(campaign_rn)
        print(f"  ✓ Kampaň (PAUSED): {campaign_rn}")

        # 3) Geo (Česko) + jazyk (čeština) + 4) negativa kampaně
        cc_svc = client.get_service("CampaignCriterionService")
        cc_ops = []
        for geo in (GEO_CZECHIA,):
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = campaign_rn
            op.create.location.geo_target_constant = geo
            cc_ops.append(op)
        for lang in (LANG_CZECH,):
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = campaign_rn
            op.create.language.language_constant = lang
            cc_ops.append(op)
        for neg in camp.get("campaign_negatives", []):
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = campaign_rn
            op.create.negative = True
            op.create.keyword.text = neg["text"]
            op.create.keyword.match_type = match_enum(client, neg.get("match"))
            cc_ops.append(op)
        if cc_ops:
            cc_svc.mutate_campaign_criteria(customer_id=cid, operations=cc_ops)
            print(f"  ✓ Geo/jazyk + {len(camp.get('campaign_negatives', []))} negativ kampaně")

        # 5) Rozšíření kampaně: sitelinky, popisky a structured snippety.
        # Zakládáme a napojujeme postupně, aby případná chyba šla snadno dohledat.
        assets = camp.get("campaign_assets", {})
        asset_svc = client.get_service("AssetService")
        campaign_asset_svc = client.get_service("CampaignAssetService")
        ft = client.enums.AssetFieldTypeEnum
        asset_specs = []
        for sl_spec in assets.get("sitelinks", []):
            op = client.get_type("AssetOperation")
            sl = op.create.sitelink_asset
            sl.link_text = sl_spec["text"]
            sl.description1 = sl_spec.get("description1", "")
            sl.description2 = sl_spec.get("description2", "")
            op.create.final_urls.append(sl_spec["final_url"])
            asset_specs.append((ft.SITELINK, op))
        for text in assets.get("callouts", []):
            op = client.get_type("AssetOperation")
            op.create.callout_asset.callout_text = text
            asset_specs.append((ft.CALLOUT, op))
        for snippet in assets.get("structured_snippets", []):
            op = client.get_type("AssetOperation")
            ss = op.create.structured_snippet_asset
            ss.header = snippet["header"].upper()
            ss.values.extend(snippet["values"])
            asset_specs.append((ft.STRUCTURED_SNIPPET, op))
        for field_type, op in asset_specs:
            asset_rn = asset_svc.mutate_assets(customer_id=cid, operations=[op]).results[0].resource_name
            link_op = client.get_type("CampaignAssetOperation")
            link_op.create.campaign = campaign_rn
            link_op.create.asset = asset_rn
            link_op.create.field_type = field_type
            campaign_asset_svc.mutate_campaign_assets(customer_id=cid, operations=[link_op])
        if asset_specs:
            print(f"  ✓ Rozšíření kampaně: {len(asset_specs)} assetů")

        # 6) Sestavy + 7) klíčová slova + 8) RSA (po sestavě)
        ag_svc = client.get_service("AdGroupService")
        agc_svc = client.get_service("AdGroupCriterionService")
        aga_svc = client.get_service("AdGroupAdService")
        for a in plan["ad_groups"]:
            # 5) sestava
            ag_op = client.get_type("AdGroupOperation")
            ag = ag_op.create
            ag.name = a["name"]
            ag.campaign = campaign_rn
            ag.status = client.enums.AdGroupStatusEnum.ENABLED
            ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ag_rn = ag_svc.mutate_ad_groups(
                customer_id=cid, operations=[ag_op]).results[0].resource_name
            created.append(ag_rn)

            # 6) klíčová slova (dávka na sestavu)
            kw_ops = []
            for k in a["keywords"]:
                op = client.get_type("AdGroupCriterionOperation")
                cr = op.create
                cr.ad_group = ag_rn
                cr.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                cr.keyword.text = k["text"]
                cr.keyword.match_type = match_enum(client, k.get("match"))
                kw_ops.append(op)
            if kw_ops:
                _mutate_exemptible(client, agc_svc.mutate_ad_group_criteria, cid, kw_ops)

            # 7) RSA
            final_url = a["rsa"].get("final_url") or a["final_url"]
            ad_op = client.get_type("AdGroupAdOperation")
            aga = ad_op.create
            aga.ad_group = ag_rn
            aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
            ad = aga.ad
            ad.final_urls.append(final_url)
            rsa = ad.responsive_search_ad
            # dedup (Google: DUPLICATE_ASSET), zachovej pořadí
            for h in list(dict.fromkeys(a["rsa"]["headlines"])):
                asset = client.get_type("AdTextAsset"); asset.text = h; rsa.headlines.append(asset)
            for d in list(dict.fromkeys(a["rsa"]["descriptions"])):
                asset = client.get_type("AdTextAsset"); asset.text = d; rsa.descriptions.append(asset)
            _mutate_exemptible(client, aga_svc.mutate_ad_group_ads, cid, [ad_op])
            print(f"  ✓ Sestava '{a['name']}': {len(a['keywords'])} KW + 1 RSA")

        print("\n✅ Hotovo. Kampaň je založená a POZASTAVENÁ.")
        print("   Reklamy jdou do schvalování Google. Před spuštěním zkontroluj texty a klikni Enable.")
        print(f"   Kampaň: {campaign_rn}")

    except Exception as e:  # noqa: BLE001
        print(f"\n🔴 CHYBA při zakládání: {e}")
        if created:
            print("   Už vzniklo (zkontroluj/ukliď v účtu):")
            for rn in created:
                print(f"     - {rn}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

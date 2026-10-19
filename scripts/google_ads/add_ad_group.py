#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Přidá NOVOU sestavu (+ klíčová slova + RSA) do EXISTUJÍCÍ Search kampaně.

Doplňuje mezeru mezi create_search_campaign.py (zakládá celou kampaň, vyžaduje
novou) a continue_search_campaign.py (vyžaduje kampaň ve stavu PAUSED). Tenhle
skript umí přidat sestavu do BĚŽÍCÍ kampaně, aniž by se musela pozastavit.

BEZPEČNOST:
- Default DRY-RUN: jen vypíše, co by založil, a zkontroluje délky RSA. NIC nezapíše.
- --validate nechá plán zkontrolovat přímo Googlem (validate_only) — nic nevznikne.
- Reálný zápis jen s --apply. Sestava se zakládá jako PAUSED (--enabled ji zapne),
  aby reklamní texty prošly lidskou kontrolou před spuštěním.
- Zakládá sériově; na chybu zastaví a vypíše, co už vzniklo.

Plán (JSON):
{
  "campaign_id": "0000000000",
  "ad_group": {
    "name": "Služba Město",
    "cpc_bid_czk": 18.0,
    "keywords": [{"text": "služba město", "match": "PHRASE"}, ...],
    "rsa": {"headlines": [...], "descriptions": [...], "final_url": "https://..."}
  }
}

Použití:
  python scripts/google_ads/add_ad_group.py <customer_id> <plan.json>
  python scripts/google_ads/add_ad_group.py <customer_id> <plan.json> --validate
  python scripts/google_ads/add_ad_group.py <customer_id> <plan.json> --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

MATCH = {"EXACT", "PHRASE", "BROAD"}


def validate(plan: dict) -> list[str]:
    errs = []
    if not plan.get("campaign_id"):
        errs.append("chybí campaign_id")
    ag = plan.get("ad_group") or {}
    if not ag.get("name"):
        errs.append("chybí ad_group.name")
    bid = ag.get("cpc_bid_czk")
    if not isinstance(bid, (int, float)) or bid <= 0:
        errs.append("ad_group.cpc_bid_czk musí být kladné číslo")
    kws = ag.get("keywords") or []
    if not kws:
        errs.append("sestava nemá žádná klíčová slova")
    for k in kws:
        if k.get("match") not in MATCH:
            errs.append(f"KW '{k.get('text')}': neplatný match '{k.get('match')}'")
    rsa = ag.get("rsa") or {}
    hs, ds = rsa.get("headlines") or [], rsa.get("descriptions") or []
    if not 3 <= len(hs) <= 15:
        errs.append(f"RSA: nadpisů musí být 3–15, je {len(hs)}")
    if not 2 <= len(ds) <= 4:
        errs.append(f"RSA: popisů musí být 2–4, je {len(ds)}")
    for h in hs:
        if len(h) > 30:
            errs.append(f"nadpis >30 znaků ({len(h)}): {h!r}")
    for d in ds:
        if len(d) > 90:
            errs.append(f"popis >90 znaků ({len(d)}): {d!r}")
    if not rsa.get("final_url"):
        errs.append("chybí rsa.final_url")
    return errs


def print_plan(plan: dict, cid: str) -> None:
    ag = plan["ad_group"]
    rsa = ag["rsa"]
    print(f"PLÁN: nová sestava → kampaň {plan['campaign_id']} (účet {cid})\n")
    print(f"  Sestava:  {ag['name']}")
    print(f"  CPC bid:  {ag['cpc_bid_czk']:.2f} Kč")
    print(f"  Cílová URL: {rsa['final_url']}")
    print(f"\n  KLÍČOVÁ SLOVA ({len(ag['keywords'])}):")
    for k in ag["keywords"]:
        print(f"    [{k['match']:6}] {k['text']}")
    print(f"\n  RSA — nadpisy ({len(rsa['headlines'])}/15):")
    for h in rsa["headlines"]:
        print(f"    {len(h):2}/30  {h}")
    print(f"\n  RSA — popisy ({len(rsa['descriptions'])}/4):")
    for d in rsa["descriptions"]:
        print(f"    {len(d):2}/90  {d}")


def main() -> None:
    p = argparse.ArgumentParser(description="Přidání sestavy do existující Search kampaně")
    p.add_argument("customer_id")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ založí (jinak dry-run)")
    p.add_argument("--validate", action="store_true", help="Nechá plán zkontrolovat Googlem, nic nevytvoří")
    p.add_argument("--enabled", action="store_true", help="Založí rovnou ENABLED (default PAUSED)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    print_plan(plan, cid)

    errs = validate(plan)
    if errs:
        print("\n❌ VALIDACE NEPROŠLA:")
        for e in errs:
            print(f"   - {e}")
        raise SystemExit(1)
    print("\n✓ Lokální validace prošla (délky RSA, match typy, bid).")

    if not args.apply and not args.validate:
        print("\n🟡 DRY-RUN — nic nezapsáno. Dál: --validate (kontrola Googlem) nebo --apply (zápis).")
        return

    client = build_client()
    svc = client.get_service("GoogleAdsService")
    camp_id = plan["campaign_id"]

    q = ("SELECT campaign.name, campaign.status, campaign.advertising_channel_type "
         f"FROM campaign WHERE campaign.id = {camp_id}")
    rows = [r for b in svc.search_stream(customer_id=cid, query=q) for r in b.results]
    if len(rows) != 1 or rows[0].campaign.advertising_channel_type.name != "SEARCH":
        raise SystemExit("Cílová kampaň neexistuje nebo není typu SEARCH — zápis zastaven.")
    print(f"\n✓ Cílová kampaň ověřena: {rows[0].campaign.name} ({rows[0].campaign.status.name})")

    ag = plan["ad_group"]
    ag_svc = client.get_service("AdGroupService")
    crit_svc = client.get_service("AdGroupCriterionService")
    ad_svc = client.get_service("AdGroupAdService")
    vo = args.validate

    op = client.get_type("AdGroupOperation")
    c = op.create
    c.name = ag["name"]
    c.campaign = f"customers/{cid}/campaigns/{camp_id}"
    c.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    c.status = (client.enums.AdGroupStatusEnum.ENABLED if args.enabled
                else client.enums.AdGroupStatusEnum.PAUSED)
    c.cpc_bid_micros = int(round(ag["cpc_bid_czk"] * 1_000_000))
    req = client.get_type("MutateAdGroupsRequest")
    req.customer_id = cid
    req.operations.append(op)
    req.validate_only = vo
    res = ag_svc.mutate_ad_groups(request=req)
    ag_rn = None if vo else res.results[0].resource_name
    print(f"  ✓ sestava {'(validate)' if vo else ag_rn}")

    if vo:
        print("\n✅ VALIDATE: Google plán přijal. Nic nevzniklo. Pro zápis pusť --apply.")
        return

    kw_ops = []
    for k in ag["keywords"]:
        o = client.get_type("AdGroupCriterionOperation")
        cc = o.create
        cc.ad_group = ag_rn
        cc.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        cc.keyword.text = k["text"]
        cc.keyword.match_type = getattr(client.enums.KeywordMatchTypeEnum, k["match"])
        kw_ops.append(o)
    crit_svc.mutate_ad_group_criteria(customer_id=cid, operations=kw_ops)
    print(f"  ✓ klíčová slova: {len(kw_ops)}/{len(kw_ops)} OK")

    rsa = ag["rsa"]
    o = client.get_type("AdGroupAdOperation")
    a = o.create
    a.ad_group = ag_rn
    a.status = client.enums.AdGroupAdStatusEnum.ENABLED
    a.ad.final_urls.append(rsa["final_url"])
    for h in rsa["headlines"]:
        asset = client.get_type("AdTextAsset")
        asset.text = h
        a.ad.responsive_search_ad.headlines.append(asset)
    for d in rsa["descriptions"]:
        asset = client.get_type("AdTextAsset")
        asset.text = d
        a.ad.responsive_search_ad.descriptions.append(asset)
    ad_res = ad_svc.mutate_ad_group_ads(customer_id=cid, operations=[o])
    print(f"  ✓ RSA {ad_res.results[0].resource_name}")

    state = "ENABLED" if args.enabled else "PAUSED"
    print(f"\n✅ Hotovo. Sestava je ve stavu {state}.")
    if state == "PAUSED":
        print("   Spuštění až po lidské kontrole reklamních textů.")


if __name__ == "__main__":
    main()

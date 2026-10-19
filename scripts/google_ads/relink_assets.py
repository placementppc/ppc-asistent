#!/usr/bin/env python3
"""Výměna rozšíření (sitelinky, telefony, popisky, úryvky) na úrovni kampaní podle plánu (JSON).

Postup je vratný: nové sitelinky se ZALOŽÍ a připojí, staré vazby se jen ODPOJÍ
(campaign_asset remove) — samotné assety v účtu zůstávají a jdou kdykoli připojit zpět.

BEZPEČNOST:
- Výchozí režim DRY-RUN: atomická dávka s validate_only=True, nic se nezapíše.
- Zápis jen s --apply; dávka je atomická (partial_failure=False).
- Skript před odesláním ověří, že URL nových sitelinků vracejí 200 bez přesměrování.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/relink_assets.py clients/<plan>.json [--apply]

Schéma plánu:
{"<customer_id>": {
   "create_sitelinks": [{"key": "sluzby", "text": "Naše služby", "url": "https://…"}],
   "create_calls": [{"key": "tel", "country": "CZ", "phone": "777 123 456"}],   # číslo musí být na webu
   "create_callouts": [{"key": "c1", "text": "Doprava zdarma"}],                  # max 25 znaků, tvrzení ověřit na webu
   "create_snippets": [{"key": "s1", "header": "Typy", "values": ["A", "B", "C"]}],  # header jako v UI (česky „Typy“/„Značky“ — ověřeno v reálném účtu)
   "link":   [{"campaign_id": "123", "asset": "0000000000" | "new:sluzby", "field_type": "SITELINK"}],
   "unlink": ["customers/…/campaignAssets/123~456~SITELINK"]
}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402
from update_ad_urls import check_url  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Výměna rozšíření kampaní (dry-run bez --apply)")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    client = build_client()
    svc = client.get_service("GoogleAdsService")
    ft_enum = client.enums.AssetFieldTypeEnum

    for raw_cid, acc in plan.items():
        if not raw_cid.isdigit():
            continue
        cid = normalize_cid(raw_cid, "write")
        bad = {s["url"]: code for s in acc.get("create_sitelinks", []) if (code := check_url(s["url"])) != 200}
        if bad:
            raise SystemExit(f"{cid}: URL nevrací 200 bez přesměrování: {bad}")

        ops, temp = [], {}
        for i, s in enumerate(acc.get("create_sitelinks", []), start=1):
            rn = f"customers/{cid}/assets/-{i}"
            temp[s["key"]] = rn
            op = client.get_type("MutateOperation")
            a = op.asset_operation.create
            a.resource_name = rn
            a.final_urls.append(s["url"])
            a.sitelink_asset.link_text = s["text"]
            ops.append(op)
            print(f"{cid} nový sitelink „{s['text']}“ → {s['url']}")
        offset = len(acc.get("create_sitelinks", []))
        for i, c in enumerate(acc.get("create_calls", []), start=offset + 1):
            rn = f"customers/{cid}/assets/-{i}"
            temp[c["key"]] = rn
            op = client.get_type("MutateOperation")
            a = op.asset_operation.create
            a.resource_name = rn
            a.call_asset.country_code = c["country"]
            a.call_asset.phone_number = c["phone"]
            ops.append(op)
            print(f"{cid} nový telefon {c['country']} {c['phone']}")
        n = offset + len(acc.get("create_calls", []))
        for c in acc.get("create_callouts", []):
            if len(c["text"]) > 25:
                raise SystemExit(f"Popisek nad 25 znaků: {c['text']!r}")
            n += 1
            rn = f"customers/{cid}/assets/-{n}"
            temp[c["key"]] = rn
            op = client.get_type("MutateOperation")
            a = op.asset_operation.create
            a.resource_name = rn
            a.callout_asset.callout_text = c["text"]
            ops.append(op)
            print(f"{cid} nový popisek „{c['text']}“")
        for c in acc.get("create_snippets", []):
            if len(c["values"]) < 3 or any(len(v) > 25 for v in c["values"]):
                raise SystemExit(f"Úryvek potřebuje 3+ hodnot do 25 znaků: {c}")
            n += 1
            rn = f"customers/{cid}/assets/-{n}"
            temp[c["key"]] = rn
            op = client.get_type("MutateOperation")
            a = op.asset_operation.create
            a.resource_name = rn
            a.structured_snippet_asset.header = c["header"]
            a.structured_snippet_asset.values.extend(c["values"])
            ops.append(op)
            print(f"{cid} nový úryvek {c['header']}: {', '.join(c['values'])}")
        for ln in acc.get("link", []):
            asset = ln["asset"]
            rn = temp[asset[4:]] if asset.startswith("new:") else f"customers/{cid}/assets/{asset}"
            op = client.get_type("MutateOperation")
            ca = op.campaign_asset_operation.create
            ca.campaign = f"customers/{cid}/campaigns/{ln['campaign_id']}"
            ca.asset = rn
            ca.field_type = getattr(ft_enum, ln["field_type"])
            ops.append(op)
            print(f"{cid} připojit {ln['field_type']} {asset} → kampaň {ln['campaign_id']}")
        for rn in acc.get("unlink", []):
            op = client.get_type("MutateOperation")
            op.campaign_asset_operation.remove = rn
            ops.append(op)
            print(f"{cid} odpojit {rn}")

        req = client.get_type("MutateGoogleAdsRequest")
        req.customer_id = cid
        req.mutate_operations.extend(ops)
        req.partial_failure = False
        req.validate_only = not args.apply
        svc.mutate(request=req)
        print(f"{cid}: {'ZAPSÁNO' if args.apply else 'DRY-RUN OK (validate_only, nic nezapsáno)'} — {len(ops)} operací")


if __name__ == "__main__":
    main()

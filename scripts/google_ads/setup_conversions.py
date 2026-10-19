#!/usr/bin/env python3
"""Založení konverzních akcí + call assetu v Google Ads a výpis měřicích kódů.

BEZPEČNOST: default DRY-RUN. Reálný zápis až s --apply.

Vytvoří WEBPAGE konverze s gtag snippetem. Které, určíš:
  - `--konverze "Název:KATEGORIE"` (opakovatelně), nebo
  - `--plan plan.json` se seznamem `[{"name": "...", "category": "..."}]`.
Bez obojího použije obecný výchozí seznam:
  - "Klik na telefon (web)"   (kategorie PHONE_CALL_LEAD)
  - "Odeslání formuláře"      (kategorie SUBMIT_LEAD_FORM)
  - "Klik na e-mail"          (kategorie CONTACT)
KATEGORIE = hodnota enumu ConversionActionCategory (např. PURCHASE, SUBMIT_LEAD_FORM,
BOOK_APPOINTMENT, PHONE_CALL_LEAD, CONTACT).
Přidá call asset (tel. číslo) do kampaně. Volitelně přepne danou konverzi na sekundární.
Po vytvoření vypíše conversion ID/label + gtag snippety (k vložení na web).

Použití:
  python scripts/google_ads/setup_conversions.py <customer_id> --campaign-id <id> \
      --phone "+0000000000" [--konverze "Odeslání poptávky:SUBMIT_LEAD_FORM"] \
      [--demote-id <conversion_action_id>] [--apply]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

DEFAULT_CONVERSIONS = [
    {"name": "Klik na telefon (web)", "category": "PHONE_CALL_LEAD"},
    {"name": "Odeslání formuláře", "category": "SUBMIT_LEAD_FORM"},
    {"name": "Klik na e-mail", "category": "CONTACT"},
]


def parse_conversions(konverze: list[str] | None, plan: str | None) -> list[dict]:
    """Seznam konverzí z argumentů / plánu, jinak obecný výchozí seznam."""
    if konverze and plan:
        raise SystemExit("Použij buď --konverze, nebo --plan, ne obojí.")
    if plan:
        data = json.loads(Path(plan).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("konverze") or data.get("conversions") or []
        out = [{"name": str(c["name"]).strip(), "category": str(c["category"]).strip().upper()}
               for c in data]
    elif konverze:
        out = []
        for k in konverze:
            name, sep, cat = k.rpartition(":")
            if not sep or not name.strip() or not cat.strip():
                raise SystemExit(f"--konverze čeká tvar \"Název:KATEGORIE\", dostal jsem {k!r}")
            out.append({"name": name.strip(), "category": cat.strip().upper()})
    else:
        out = [dict(c) for c in DEFAULT_CONVERSIONS]
    if not out:
        raise SystemExit("Seznam konverzí je prázdný.")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Založení konverzí + call asset")
    p.add_argument("customer_id")
    p.add_argument("--campaign-id", required=True)
    p.add_argument("--phone", required=True, help="Tel. číslo pro call asset, např. +0000000000")
    p.add_argument("--country", default="CZ")
    p.add_argument("--demote-id", help="ID stávající konverze, kterou přepnout na sekundární (page-view)")
    p.add_argument("--konverze", action="append",
                   help='konverze k založení ve tvaru "Název:KATEGORIE" (opakovatelně)')
    p.add_argument("--plan", help='JSON se seznamem [{"name": ..., "category": ...}]')
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    conversions = parse_conversions(args.konverze, args.plan)

    cid = normalize_cid(args.customer_id)
    client = build_client()

    type_enum = client.enums.ConversionActionTypeEnum
    cat_enum = client.enums.ConversionActionCategoryEnum
    status_enum = client.enums.ConversionActionStatusEnum
    counting_enum = client.enums.ConversionActionCountingTypeEnum
    for c in conversions:
        if not hasattr(cat_enum, c["category"]):
            raise SystemExit(f"Neznámá kategorie konverze: {c['category']}")

    print("PLÁN — konverze k založení:")
    for c in conversions:
        print(f"  [+ KONV] {c['name']}  (kategorie {c['category']}, primární)")
    print(f"  [+ ASSET] call asset {args.phone} ({args.country}) → kampaň {args.campaign_id}")
    if args.demote_id:
        print(f"  [~ DEMOTE] konverze id={args.demote_id} → sekundární (primary_for_goal=false)")

    if not args.apply:
        print("\n🟡 DRY-RUN — nic nezaloženo. Pro reálné provedení přidej --apply")
        return

    print("\n🔴 --apply: zakládám...")
    ca_service = client.get_service("ConversionActionService")

    # 1) Konverzní akce
    ops = []
    for c in conversions:
        op = client.get_type("ConversionActionOperation")
        ca = op.create
        ca.name = c["name"]
        ca.type_ = type_enum.WEBPAGE
        ca.category = getattr(cat_enum, c["category"])
        ca.status = status_enum.ENABLED
        ca.primary_for_goal = True
        ca.counting_type = counting_enum.ONE_PER_CLICK
        ca.value_settings.default_value = 0.0
        ca.value_settings.always_use_default_value = True
        ops.append(op)
    resp = ca_service.mutate_conversion_actions(customer_id=cid, operations=ops)
    created = [r.resource_name for r in resp.results]
    print(f"  ✓ {len(created)} konverzí založeno")

    # 2) Přepnutí page-view na sekundární
    if args.demote_id:
        op = client.get_type("ConversionActionOperation")
        op.update.resource_name = f"customers/{cid}/conversionActions/{args.demote_id}"
        op.update.primary_for_goal = False
        op.update_mask.paths.append("primary_for_goal")
        ca_service.mutate_conversion_actions(customer_id=cid, operations=[op])
        print(f"  ✓ konverze {args.demote_id} přepnuta na sekundární")

    # 3) Call asset + napojení na kampaň
    asset_op = client.get_type("AssetOperation")
    call = asset_op.create.call_asset
    call.country_code = args.country
    call.phone_number = args.phone
    a_resp = client.get_service("AssetService").mutate_assets(
        customer_id=cid, operations=[asset_op])
    asset_rn = a_resp.results[0].resource_name
    link_op = client.get_type("CampaignAssetOperation")
    link = link_op.create
    link.campaign = f"customers/{cid}/campaigns/{args.campaign_id}"
    link.asset = asset_rn
    link.field_type = client.enums.AssetFieldTypeEnum.CALL
    client.get_service("CampaignAssetService").mutate_campaign_assets(
        customer_id=cid, operations=[link_op])
    print(f"  ✓ call asset {args.phone} přidán do kampaně {args.campaign_id}")

    # 4) Výpis měřicích kódů (gtag snippety)
    print("\n=== MĚŘICÍ KÓDY (vlož na web) ===")
    ga = client.get_service("GoogleAdsService")
    ids = ",".join(f"'{rn}'" for rn in created)
    q = ("SELECT conversion_action.id, conversion_action.name, conversion_action.tag_snippets "
         f"FROM conversion_action WHERE conversion_action.resource_name IN ({ids})")
    for batch in ga.search_stream(customer_id=cid, query=q):
        for r in batch.results:
            ca = r.conversion_action
            print(f"\n### {ca.name}  (Conversion ID: {ca.id})")
            for ts in ca.tag_snippets:
                print(f"--- Global site tag (page_format={ts.page_format.name}) ---")
                print(ts.global_site_tag)
                print("--- Event snippet ---")
                print(ts.event_snippet)


if __name__ == "__main__":
    main()

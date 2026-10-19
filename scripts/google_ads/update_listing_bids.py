#!/usr/bin/env python3
"""Úprava CPC bidů u listing groups (Shopping/PLA) podle plánu (JSON).

BEZPEČNOST:
- Ve výchozím stavu DRY-RUN: vypíše aktuální → nový bid, NIC nezapíše.
- Reálný zápis pouze s --apply (po schválení uživatelem).

Použití:
  python scripts/google_ads/update_listing_bids.py <customer_id> clients/<plan>.json
  python scripts/google_ads/update_listing_bids.py <customer_id> clients/<plan>.json --apply

Schéma plánu (JSON):
{
  "ad_group_id": "0000000000",
  "bids": [
    {"criterion_id": "0000000000", "cpc_bid": 5.5, "note": "produktová skupina A"},
    ...
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


def current_bids(client, cid: str, ag_id: str) -> dict[str, tuple[float, str]]:
    """Mapa {criterion_id: (bid_kč, display_name)} pro UNIT listing groups v sestavě."""
    svc = client.get_service("GoogleAdsService")
    q = (
        "SELECT ad_group_criterion.criterion_id, ad_group_criterion.cpc_bid_micros, "
        "ad_group_criterion.display_name, ad_group_criterion.listing_group.type "
        f"FROM ad_group_criterion WHERE ad_group.id = {ag_id} "
        "AND ad_group_criterion.type = 'LISTING_GROUP' "
        "AND ad_group_criterion.status != 'REMOVED'"
    )
    out = {}
    for batch in svc.search_stream(customer_id=cid, query=q):
        for r in batch.results:
            c = r.ad_group_criterion
            out[str(c.criterion_id)] = (c.cpc_bid_micros / 1e6, c.display_name)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Úprava CPC bidů listing groups")
    p.add_argument("customer_id")
    p.add_argument("plan", help="Cesta k plán JSON")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ provede změny (jinak dry-run)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    client = build_client()

    ag_id = plan["ad_group_id"]
    existing = current_bids(client, cid, ag_id)

    svc = client.get_service("AdGroupCriterionService")
    ops = []
    for item in plan.get("bids", []):
        crit_id = str(item["criterion_id"])
        new_bid = float(item["cpc_bid"])
        if crit_id not in existing:
            print(f"⚠️  criterion {crit_id} v sestavě {ag_id} nenalezen — přeskakuji")
            continue
        old_bid, name = existing[crit_id]
        note = item.get("note", name)
        print(f"{'[APPLY]' if args.apply else '[DRY-RUN]'} {note}: {old_bid:.2f} → {new_bid:.2f} Kč "
              f"(criterion {crit_id})")
        op = client.get_type("AdGroupCriterionOperation")
        op.update.resource_name = (
            f"customers/{cid}/adGroupCriteria/{ag_id}~{crit_id}"
        )
        op.update.cpc_bid_micros = int(round(new_bid * 1e6))
        op.update_mask.paths.append("cpc_bid_micros")
        ops.append(op)

    if not ops:
        print("Žádné operace.")
        return
    if not args.apply:
        print(f"\nDry-run: {len(ops)} změn NEPROVEDENO. Spusť s --apply pro reálný zápis.")
        return

    resp = svc.mutate_ad_group_criteria(customer_id=cid, operations=ops)
    for r in resp.results:
        print(f"✅ {r.resource_name}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Přepnutí konverzní akce primární ↔ sekundární (primary_for_goal).

Typický důvod: dvojí počítání objednávek (Google tag + GA4 purchase obě primární)
→ jedna z nich se přepne na sekundární (zaznamenává se, ale nebiduje se na ni).

BEZPEČNOST:
- Ve výchozím stavu DRY-RUN: vypíše aktuální → nový stav, NIC nezapíše.
- Reálný zápis pouze s --apply (po schválení uživatelem).

Použití:
  python scripts/google_ads/update_conversion_goal.py <customer_id> <conversion_action_id> --primary false
  python scripts/google_ads/update_conversion_goal.py <customer_id> <conversion_action_id> --primary false --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Přepnutí primary_for_goal u konverzní akce")
    p.add_argument("customer_id")
    p.add_argument("conversion_action_id")
    p.add_argument("--primary", required=True, choices=["true", "false"],
                   help="Cílový stav primary_for_goal")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ provede změnu (jinak dry-run)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    ca_id = args.conversion_action_id
    target = args.primary == "true"
    client = build_client()

    svc = client.get_service("GoogleAdsService")
    q = (
        "SELECT conversion_action.id, conversion_action.name, "
        "conversion_action.primary_for_goal, conversion_action.status "
        f"FROM conversion_action WHERE conversion_action.id = {ca_id}"
    )
    rows = [r for batch in svc.search_stream(customer_id=cid, query=q) for r in batch.results]
    if not rows:
        raise SystemExit(f"Konverzní akce {ca_id} nenalezena.")
    ca = rows[0].conversion_action
    mode = "[APPLY]" if args.apply else "[DRY-RUN]"
    print(f"{mode} '{ca.name}' (id {ca.id}): primary_for_goal {ca.primary_for_goal} → {target}")

    if ca.primary_for_goal == target:
        print("Už je v cílovém stavu — nic k provedení.")
        return
    if not args.apply:
        print("\nDry-run: NEPROVEDENO. Spusť s --apply pro reálný zápis.")
        return

    ca_svc = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    op.update.resource_name = f"customers/{cid}/conversionActions/{ca_id}"
    op.update.primary_for_goal = target
    op.update_mask.paths.append("primary_for_goal")
    resp = ca_svc.mutate_conversion_actions(customer_id=cid, operations=[op])
    print(f"✅ {resp.results[0].resource_name}")


if __name__ == "__main__":
    main()

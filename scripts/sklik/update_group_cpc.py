#!/usr/bin/env python3
"""Sklik: změna max. CPC sestav (groups.update) nebo klíčových slov (keywords.update), pole `cpc` v haléřích, podle plánu.

BEZPEČNOST:
- Výchozí DRY-RUN: jen náhled + ověření aktuálních CPC (nic nezapíše). `groups.check` použít NEJDE —
  validuje jen zakládání sestav, pole `id` odmítne (ověřeno 2026-10-19).
- Zápis jen s --apply a plánem s approval.status == "approved".
- Pojistka: změna max ±20 % za krok proti hodnotě `from` v plánu; skript před zápisem ověří,
  že aktuální CPC sestavy v účtu = `from` (jinak se mezitím něco změnilo → stop).
- Po zápisu read-back přes groups.list.

Použití:
  SKLIK_TOKEN_VAR=SKLIK_DRUHY_TOKEN python scripts/sklik/update_group_cpc.py clients/<plan>.json [--apply]

Plán:
{"user_id": 123456, "approval": {"status": "approved", ...},
 "groups": [{"id": 123, "name": "...", "from": 1000, "to": 1150}]}   # haléře
 nebo "keywords": [{"id": 0000000000, "name": "...", "from": 1000, "to": 1150}]   (KW s vlastním CPC)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_search_changes import Api, ensure_ok  # noqa: E402

MAX_STEP = 0.20


def read_cpc(api: Api, ids: list[int], kind: str) -> dict[int, int]:
    if kind == "groups":
        r = api.call("groups.list", {"ids": ids},
                     {"offset": 0, "limit": 100, "displayColumns": ["id", "name", "maxCpc"]})
        ensure_ok("groups.list", r)
        return {g["id"]: g["maxCpc"] for g in r.get("groups") or []}
    r = api.call("keywords.list", {"ids": ids},
                 {"offset": 0, "limit": 1000, "displayColumns": ["id", "name", "cpc"]})
    ensure_ok("keywords.list", r)
    return {k["id"]: k.get("cpc") for k in r.get("keywords") or []}


def main() -> None:
    p = argparse.ArgumentParser(description="Sklik max. CPC sestav (dry-run bez --apply)")
    p.add_argument("plan", type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám plán: approval.status není approved.")
    kind = "groups" if plan.get("groups") else "keywords"
    rows = plan[kind]
    for g in rows:
        if abs(g["to"] - g["from"]) / g["from"] > MAX_STEP:
            raise SystemExit(f"Změna nad {MAX_STEP:.0%}: {g}")
    api = Api(int(plan["user_id"]))
    ids = [g["id"] for g in rows]
    now = read_cpc(api, ids, kind)
    for g in rows:
        if now.get(g["id"]) != g["from"]:
            raise SystemExit(f"{kind} {g['id']} má teď {now.get(g['id'])}, plán čeká {g['from']} — stop.")
        print(f"{g['id']} {g.get('name', '')}: {g['from'] / 100:.2f} → {g['to'] / 100:.2f} Kč")
    payload = [{"id": g["id"], "cpc": g["to"]} for g in rows]
    if not args.apply:
        print("DRY-RUN: nic nezapsáno.")
        return
    ensure_ok(f"{kind}.update", api.call(f"{kind}.update", payload))
    after = read_cpc(api, ids, kind)
    bad = [g for g in rows if after.get(g["id"]) != g["to"]]
    print("Read-back:", "OK" if not bad else f"NESEDÍ {bad}", {k: v / 100 for k, v in after.items()})


if __name__ == "__main__":
    main()

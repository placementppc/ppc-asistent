#!/usr/bin/env python3
"""Sklik: hromadná sestavová negativa + CPC klíčových slov + pozastavení kampaní podle plánu.

BEZPEČNOST:
- Výchozí režim je DRY-RUN: volají se jen *.check metody, nic se nezapíše.
- Zápis jen s --apply a plánem s approval.status == "approved".
- Negativa se jen PŘIDÁVAJÍ na sestavy (keywords.negative.create). Negativa kampaní
  se záměrně nepoužívají: campaigns.update posílá celé pole negativeKeywords a mohl by
  stávající přepsat.
- Před plánem zkontroluj, že negativum neblokuje existující KW v téže sestavě (pravidlo
  v .claude/skills/dotazy-vylouceni/SKILL.md).
- Rozpočty skript neumí měnit (klíče budget/dayBudget/totalBudget plán odmítne).
- Dávky podle api.limits, sériově, backoff na 429 (Api z apply_search_changes).

Použití:
  python scripts/sklik/apply_negatives_bids.py clients/<plan>.json
  python scripts/sklik/apply_negatives_bids.py clients/<plan>.json --apply

Schéma plánu:
{
  "user_id": 123456,
  "approval": {"status": "approved", "by": "...", "date": "YYYY-MM-DD"},
  "negative_keywords": [{"groupId": 1, "name": "zdarma", "matchType": "negativePhrase"}],
  "keyword_cpc": [{"id": 123, "cpc": 2500, "from": 3800, "name": "..."}],   # haléře
  "pause_campaigns": [{"id": 1234567, "name": "..."}]
}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_search_changes import Api, batch_limit, ensure_ok  # noqa: E402

FORBIDDEN_KEYS = {"budget", "dayBudget", "totalBudget", "sharedBudgetId"}
MAX_CPC_DROP = 0.60  # pojistka: snížení CPC max o 60 % v jednom kroku


def chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám plán: approval.status není approved.")
    text = json.dumps(plan)
    for key in FORBIDDEN_KEYS:
        if f'"{key}"' in text:
            raise SystemExit(f"Odmítám plán: obsahuje zakázaný klíč {key}.")
    for row in plan.get("keyword_cpc") or []:
        if row["cpc"] > row["from"]:
            raise SystemExit(f"Plán zvyšuje CPC (tento skript jen snižuje): {row}")
        if (row["from"] - row["cpc"]) / row["from"] > MAX_CPC_DROP:
            raise SystemExit(f"Snížení CPC nad {MAX_CPC_DROP:.0%}: {row}")
    return plan


def run(api: Api, method: str, rows: list, size: int, sleep: float = 0.5) -> list:
    out = []
    for part in chunks(rows, size):
        resp = api.call(method, part)
        ensure_ok(method, resp)
        out.append(resp)
        time.sleep(sleep)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Sklik negativa + CPC + pauzy (dry-run bez --apply)")
    p.add_argument("plan", type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan = load_plan(args.plan)
    api = Api(int(plan["user_id"]))
    limits = api.call("api.limits", managed=False)
    ensure_ok("api.limits", limits)
    size = min(batch_limit(limits, "global.check"), batch_limit(limits, "global.create"),
               batch_limit(limits, "global.update"))

    negs = plan.get("negative_keywords") or []
    cpcs = [{"id": r["id"], "cpc": r["cpc"]} for r in plan.get("keyword_cpc") or []]
    # campaigns.update vyžaduje i "type" (fulltext/context/…), jinak 400 — ověřeno 2026-10-05
    pauses = [{"id": r["id"], "type": r.get("type", "fulltext"), "status": "suspend"}
              for r in plan.get("pause_campaigns") or []]

    run(api, "keywords.negative.check", negs, size)
    run(api, "keywords.check", cpcs, size)
    # campaigns.check pole status nepřijímá (ověřeno 2026-10-05) — pauzu jen vypíšeme
    for row in plan.get("pause_campaigns") or []:
        print(f"Pozastavím kampaň {row['id']} {row.get('name', '')}")
    print(f"Kontrola OK: negativa {len(negs)}, CPC {len(cpcs)}, pauzy kampaní {len(pauses)}")
    if not args.apply:
        print("DRY-RUN: nic nezapsáno.")
        return

    # keywords.negative.create nevrací ID (jen status) — ověřeno v DRAK docs 2026-10-12;
    # počet zapsaných ověř read-backem přes keywords.negative.list.
    run(api, "keywords.negative.create", negs, size)
    run(api, "keywords.update", cpcs, size)
    run(api, "campaigns.update", pauses, size)
    print(f"ZAPSÁNO (status 200): negativa {len(negs)}, CPC {len(cpcs)}, pauzy {len(pauses)} — ověř read-backem")


if __name__ == "__main__":
    main()

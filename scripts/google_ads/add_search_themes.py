#!/usr/bin/env python3
"""Hledaná témata (search themes) do skupin podkladů Performance Max podle plánu (JSON).

BEZPEČNOST:
- Výchozí režim je DRY-RUN: dávka se pošle s validate_only=True — Google ji zkontroluje,
  ale NIC nezapíše. Reálný zápis jen s --apply. Dávka je atomická (buď celá, nebo nic).
- Téma, které ve skupině už je, se přeskočí (žádné duplicity).
- Téma, které by zablokovalo vylučující slovo kampaně, skript ODMÍTNE celou dávku.
  Pravidla shody negativ (bez blízkých variant): přesná = celý text shodný,
  frázová = slova za sebou ve stejném pořadí, volná = všechna slova kdekoli.
- Nic jiného (publika, rozpočty, texty) skript neumí měnit.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/add_search_themes.py clients/<plan>.json
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/add_search_themes.py clients/<plan>.json --apply

Schéma plánu:
{
  "<customer_id>": [
    {"campaign_id": "...", "asset_group_id": "...", "themes": ["téma vyhledávání", ...]}
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


def words(text: str) -> list[str]:
    return text.lower().split()


def blocked_by(theme: str, negatives: list[tuple[str, str]]) -> list[str]:
    """Vrátí vylučující slova kampaně, která by téma zablokovala."""
    t = words(theme)
    hits = []
    for text, match in negatives:
        k = words(text)
        if match == "EXACT" and k == t:
            hits.append(f"{text} [přesná]")
        elif match == "PHRASE" and any(t[i:i + len(k)] == k for i in range(len(t) - len(k) + 1)):
            hits.append(f"{text} [frázová]")
        elif match == "BROAD" and all(w in t for w in k):
            hits.append(f"{text} [volná]")
    return hits


def campaign_negatives(svc, cid: str, campaign_id: str) -> list[tuple[str, str]]:
    q = ("SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
         "FROM campaign_criterion WHERE campaign_criterion.type = 'KEYWORD' "
         f"AND campaign_criterion.negative = true AND campaign.id = {int(campaign_id)}")
    return [(r.campaign_criterion.keyword.text, r.campaign_criterion.keyword.match_type.name)
            for b in svc.search_stream(customer_id=cid, query=q) for r in b.results]


def existing_themes(svc, cid: str, asset_group_id: str) -> set[str]:
    q = ("SELECT asset_group_signal.search_theme.text FROM asset_group_signal "
         f"WHERE asset_group.id = {int(asset_group_id)}")
    return {r.asset_group_signal.search_theme.text.lower()
            for b in svc.search_stream(customer_id=cid, query=q) for r in b.results
            if r.asset_group_signal.search_theme.text}


def main() -> None:
    p = argparse.ArgumentParser(description="Hledaná témata do PMax (dry-run bez --apply)")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true", help="Reálně zapsat (jinak validate_only)")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    client = build_client()
    svc = client.get_service("GoogleAdsService")

    for raw_cid, groups in plan.items():
        cid = normalize_cid(raw_cid)
        ops, problems = [], []
        for g in groups:
            negs = campaign_negatives(svc, cid, g["campaign_id"])
            have = existing_themes(svc, cid, g["asset_group_id"])
            print(f"\nKampaň {g['campaign_id']} / skupina {g['asset_group_id']} "
                  f"(negativ: {len(negs)}, témat už: {len(have)})")
            for theme in g["themes"]:
                hits = blocked_by(theme, negs)
                if hits:
                    problems.append(f"{theme!r} blokuje: {', '.join(hits)}")
                    print(f"  ✗ {theme}  — BLOKUJE {', '.join(hits)}")
                    continue
                if theme.lower() in have:
                    print(f"  = {theme}  (už je, přeskakuji)")
                    continue
                op = client.get_type("MutateOperation")
                sig = op.asset_group_signal_operation.create
                sig.asset_group = svc.asset_group_path(cid, g["asset_group_id"])
                sig.search_theme.text = theme
                ops.append(op)
                print(f"  + {theme}")
        if problems:
            sys.exit("\nZASTAVENO — témata kolidují s vylučujícími slovy, nic se neposílá:\n  "
                     + "\n  ".join(problems))
        if not ops:
            print("\nNení co přidat.")
            continue
        req = client.get_type("MutateGoogleAdsRequest")
        req.customer_id = cid
        req.mutate_operations.extend(ops)
        req.partial_failure = False
        req.validate_only = not args.apply
        resp = client.get_service("GoogleAdsService").mutate(request=req)
        mode = "ZAPSÁNO" if args.apply else "DRY-RUN OK (validate_only, nic nezapsáno)"
        print(f"\n{cid}: {mode} — témat {len(ops)}"
              + (f", výsledků {len(resp.mutate_operation_responses)}" if args.apply else ""))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only stahování dat ze Sklik.

Použití:
  python scripts/sklik/fetch.py --user-id <ID> campaigns
  python scripts/sklik/fetch.py --user-id <ID> --call <metoda> [JSON_params]

Tento skript je POUZE PRO ČTENÍ. Žádné změny v účtu neprovádí.
Názvy metod (campaigns.list, stats.*, …) ověř dle aktuální Sklik API dokumentace —
mohou se lišit dle verze. --call umožní zavolat libovolnou (čtecí) metodu.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
from client import SklikClient  # noqa: E402
from lib.redact import SECRET_KEYS, strip_secrets  # noqa: E402,F401  (`session` se nevypisuje)


def main() -> None:
    p = argparse.ArgumentParser(description="Sklik read-only fetch")
    p.add_argument("report", nargs="?", help="campaigns | (jinak použij --call)")
    p.add_argument("--user-id", type=int, help="ID cílového (klientského) účtu pro agenturní přístup")
    p.add_argument("--call", help="Libovolná čtecí metoda API, např. campaigns.list")
    p.add_argument("--params", help="JSON s parametry pro --call", default="[]")
    p.add_argument("--anon", metavar="KLIENT",
                   help="Výstup rovnou anonymizovat (NDA klient v režimu anonymizace)")
    args = p.parse_args()

    c = SklikClient().login()
    c.nda_kind = "read-anon" if args.anon else "read-raw"

    if args.call:
        params = json.loads(args.params)
        if not isinstance(params, list):
            params = [params]
        out = c.call(args.call, *params, user_id=args.user_id)
    elif args.report == "campaigns":
        out = c.call("campaigns.list", user_id=args.user_id)
    else:
        p.error("Zadej 'campaigns' nebo --call <metoda>.")

    out = strip_secrets(out)
    if args.anon:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import sanitize as san
        pseudo = san.Pseudonymizer(args.anon)
        out = san.sanitize(out, pseudo)
        pseudo.save()  # bez uložené mapy by nešel zpětný překlad tokenů
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

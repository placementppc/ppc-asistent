#!/usr/bin/env python3
"""Stáhne standardní sadu Google Ads reportů a rovnou je anonymizuje (NDA klienti).

Pro klienty pod NDA (`NDA: true` v clients/<klient>.md). Spojuje `fetch.py` +
`sanitize.py` do jednoho kroku, aby syrová data nikdy neskončila tam, kam se dívá Claude.

Výstup:
  - clients/.secret/<klient>-raw-<datum>.json   syrová data (gitignored, NEČTI)
  - clients/<klient>-data-<datum>.json          anonymizovaná data (TADY analyzuj)
  - clients/.secret/<klient>-map.json            mapa token→realita (gitignored)

Použití:
  python scripts/google_ads/fetch_safe.py <customer_id> --client acme [--days 30]
  # bez --days se zeptá interaktivně na období
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))  # kvůli importu sanitize

from client import build_client, normalize_cid  # noqa: E402
from fetch import REPORTS, run_gaql  # noqa: E402
import sanitize as san  # noqa: E402

# Sériově (žádný souběh — API limity). 'shopping' jen na vyžádání (bývá objemné).
DEFAULT_REPORTS = ["campaigns", "budgets", "ad_groups", "keywords",
                   "search_terms", "ads", "pmax_channels"]


def main() -> None:
    p = argparse.ArgumentParser(description="Google Ads fetch + anonymizace (NDA)")
    p.add_argument("customer_id", nargs="?",
                   help="Customer ID klienta. Bez něj se načte z "
                        "clients/.secret/<client>-account.json (klíč google_ads_customer_id).")
    p.add_argument("--client", required=True, help="Slug klienta (názvy souborů + mapa)")
    p.add_argument("--days", type=int, help="Okno ve dnech (bez něj se zeptá)")
    p.add_argument("--reports", nargs="*", default=DEFAULT_REPORTS,
                   help="Které reporty stáhnout (default: " + ", ".join(DEFAULT_REPORTS) + ")")
    p.add_argument("--keep-all-campaigns", action="store_true",
                   help="Nevyhazuj brandové kampaně (jinak se vynechá vše s 'brand' v názvu)")
    args = p.parse_args()

    if args.days is None:
        try:
            args.days = int(input("Za kolik dní stáhnout data? [30]: ").strip() or "30")
        except (EOFError, ValueError):
            args.days = 30

    customer_id = args.customer_id
    if not customer_id:
        acc_path = san.SECRET_DIR / f"{args.client}-account.json"
        if not acc_path.exists():
            raise SystemExit(
                f"Zadej customer_id, nebo vytvoř {acc_path} s klíčem 'google_ads_customer_id'.")
        customer_id = json.loads(acc_path.read_text(encoding="utf-8"))["google_ads_customer_id"]

    cid = normalize_cid(customer_id, nda_kind="read-anon")
    end = date.today() - timedelta(days=1)            # včerejšek (dnešek nekompletní)
    start = end - timedelta(days=args.days - 1)
    today = date.today().isoformat()

    secret_dir = san.SECRET_DIR
    secret_dir.mkdir(parents=True, exist_ok=True)
    raw_path = secret_dir / f"{args.client}-raw-{today}.json"
    safe_path = san.ROOT / "clients" / f"{args.client}-data-{today}.json"

    client = build_client()
    raw: dict[str, list] = {}
    for name in args.reports:
        if name not in REPORTS:
            print(f"[fetch_safe] přeskakuji neznámý report '{name}'", file=sys.stderr)
            continue
        query = (REPORTS[name]
                 .replace("{START}", start.isoformat())
                 .replace("{END}", end.isoformat()))
        print(f"[fetch_safe] stahuji {name} ({start}–{end})…", file=sys.stderr)
        raw[name] = run_gaql(client, cid, query)       # sériově, přes search_stream

    # Syrová data uložíme jen do .secret (audit/možnost znovu sanitizovat jinak).
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # Anonymizace: nejdřív vyhoď brandové kampaně, pak pseudonymizuj.
    if not args.keep_all_campaigns:
        raw, dropped = san.drop_campaigns(raw, san.DROP_CAMPAIGN_DEFAULT)
        if dropped:
            print(f"[fetch_safe] vynecháno {dropped} řádků brandových kampaní "
                  f"(podle názvu: {san.DROP_CAMPAIGN_DEFAULT})", file=sys.stderr)
    pseudo = san.Pseudonymizer(args.client)
    safe = san.sanitize(raw, pseudo)
    pseudo.save()
    safe_path.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[fetch_safe] hotovo • syrová (NEČTI): {raw_path}", file=sys.stderr)
    print(f"[fetch_safe] anonymizovaná (analyzuj TADY): {safe_path}", file=sys.stderr)
    print(str(safe_path))    # na stdout cesta k bezpečnému souboru


if __name__ == "__main__":
    main()

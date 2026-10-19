#!/usr/bin/env python3
"""Read-only stahování dat z GA4 (Google Analytics Data API v1, přes REST).

Používá stejné OAuth přístupy jako Google Ads (.env: GOOGLE_ADS_CLIENT_ID/SECRET/
REFRESH_TOKEN) — refresh token musí mít scope `analytics.readonly`
(vygeneruj přes scripts/google_ads/generate_refresh_token.py).

Použití:
  python scripts/ga4/fetch.py properties                       # seznam dostupných GA4 properties
  python scripts/ga4/fetch.py items <PROPERTY_ID> --days 90    # prodeje po položkách
  python scripts/ga4/fetch.py daily <PROPERTY_ID> --days 45    # denní tržby/transakce
  python scripts/ga4/fetch.py report <PROPERTY_ID> \
      --dimensions itemCategory,itemName --metrics itemRevenue,itemsPurchased --days 90

Jen čte (runReport / accountSummaries). Žádné zápisy.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402


def access_token() -> str:
    cfg = require("GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN")
    data = urllib.parse.urlencode({
        "client_id": cfg["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": cfg["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": cfg["GOOGLE_ADS_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    tok = json.loads(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30).read())
    if "analytics.readonly" not in tok.get("scope", ""):
        raise SystemExit(
            "Refresh token nemá scope analytics.readonly — vygeneruj nový: "
            "! .venv/bin/python scripts/google_ads/generate_refresh_token.py --write-env"
        )
    return tok["access_token"]


def call(url: str, token: str, body: dict | None = None) -> dict:
    for attempt in range(4):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 503) and attempt < 3:
                time.sleep(3 * 2 ** attempt)
                continue
            detail = exc.read().decode(errors="replace")[:500]
            raise SystemExit(f"GA4 API {exc.code}: {detail}") from exc
    raise SystemExit("GA4 API: vyčerpány pokusy po rate limitu")


def run_report(prop: str, token: str, dimensions: list[str], metrics: list[str],
               date_from: str, date_to: str, limit: int = 10000,
               dimension_filter: tuple[str, list[str]] | None = None) -> list[dict]:
    body = {
        "dateRanges": [{"startDate": date_from, "endDate": date_to}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
    }
    if dimension_filter:
        field, values = dimension_filter
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": field,
                "inListFilter": {"values": values, "caseSensitive": True},
            }
        }
    out = call(f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport",
               token, body)
    rows = []
    for r in out.get("rows", []):
        row = {d: v.get("value") for d, v in zip(dimensions, r.get("dimensionValues", []))}
        row.update({m: v.get("value") for m, v in zip(metrics, r.get("metricValues", []))})
        rows.append(row)
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="GA4 read-only fetch")
    p.add_argument("mode", choices=["properties", "items", "daily", "report"])
    p.add_argument("property", nargs="?", help="GA4 property ID (jen číslo)")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--date-from", help="YYYY-MM-DD (přepíše --days)")
    p.add_argument("--date-to", default="yesterday")
    p.add_argument("--dimensions", help="čárkou oddělené GA4 dimenze (pro mode report)")
    p.add_argument("--metrics", help="čárkou oddělené GA4 metriky (pro mode report)")
    p.add_argument("--limit", type=int, default=10000, help="maximální počet řádků")
    p.add_argument(
        "--filter",
        help="volitelný filtr dimenze, např. country=Germany,Austria",
    )
    args = p.parse_args()

    from lib.nda import guard, filter_listing
    if args.property:
        guard(args.property, "read-raw")
    token = access_token()

    if args.mode == "properties":
        out = call("https://analyticsadmin.googleapis.com/v1beta/accountSummaries", token)
        summary = [
            {"account": a.get("displayName"),
             "properties": [{"id": pr.get("property", "").replace("properties/", ""),
                             "name": pr.get("displayName")}
                            for pr in filter_listing(
                                [{**x, "id": x.get("property", "").replace("properties/", "")}
                                 for x in a.get("propertySummaries", [])])]}
            for a in out.get("accountSummaries", [])
        ]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if not args.property:
        p.error("Zadej PROPERTY_ID (zjistíš přes: fetch.py properties)")
    date_from = args.date_from or (date.today() - timedelta(days=args.days)).isoformat()

    dimension_filter = None
    if args.filter:
        if "=" not in args.filter:
            p.error("--filter musí mít tvar dimenze=hodnota1,hodnota2")
        field, raw_values = args.filter.split("=", 1)
        values = [value for value in raw_values.split(",") if value]
        if not field or not values:
            p.error("--filter musí obsahovat dimenzi a alespoň jednu hodnotu")
        dimension_filter = (field, values)

    if args.mode == "items":
        rows = run_report(args.property, token,
                          ["itemCategory", "itemName"],
                          ["itemsPurchased", "itemRevenue"], date_from, args.date_to,
                          limit=args.limit, dimension_filter=dimension_filter)
    elif args.mode == "daily":
        rows = run_report(args.property, token, ["date"],
                          ["transactions", "purchaseRevenue", "sessions"],
                          date_from, args.date_to, limit=args.limit,
                          dimension_filter=dimension_filter)
    else:
        if not (args.dimensions and args.metrics):
            p.error("mode report vyžaduje --dimensions a --metrics")
        rows = run_report(args.property, token, args.dimensions.split(","),
                          args.metrics.split(","), date_from, args.date_to,
                          limit=args.limit, dimension_filter=dimension_filter)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

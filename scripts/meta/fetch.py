#!/usr/bin/env python3
"""Meta (Facebook/Instagram) Ads — READ-ONLY konektor přes Graph API.

Autentizace: `META_API_TOKEN` v `.env` (system-user / long-lived token s `ads_read`).
Volitelně `META_API_VERSION` (default v21.0).

Bezpečnost / limity (viz `knowledge/api-limity-bezpecnost.md`, `knowledge/meta-ads.md`):
- Tento skript jen ČTE. Žádné zápisy. Nespouštěj paralelně, jedeme sériově.
- Na rate-limit (kód 4/17/32/613 nebo HTTP 429) → počkej a zopakuj (backoff).

Použití:
  python scripts/meta/fetch.py accounts
  python scripts/meta/fetch.py campaigns act_000000000000000
  python scripts/meta/fetch.py adsets    act_000000000000000
  python scripts/meta/fetch.py ads       act_000000000000000
  python scripts/meta/fetch.py insights  <act_/campaign/adset/ad id> --level campaign --days 90
  python scripts/meta/fetch.py insights  act_000000000000000 --level adset --preset maximum
  # vlastní volání:
  python scripts/meta/fetch.py --get "act_000000000000000/campaigns" --fields "name,status,objective" --params "limit=50"

Reporty: accounts, campaigns, adsets, ads, insights.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402
from lib.redact import redact  # noqa: E402

FIELDS = {
    "campaigns": "id,name,status,effective_status,objective,buying_type,daily_budget,"
    "lifetime_budget,bid_strategy,start_time,stop_time,created_time,updated_time",
    "adsets": "id,name,status,effective_status,campaign_id,daily_budget,lifetime_budget,"
    "optimization_goal,billing_event,bid_strategy,bid_amount,destination_type,"
    "start_time,end_time,targeting",
    "ads": "id,name,status,effective_status,adset_id,campaign_id,creative{id,name,title,body,"
    "object_story_spec,thumbnail_url}",
    "accounts": "id,account_id,name,account_status,currency,amount_spent,balance,business_name",
}

INSIGHTS_FIELDS = (
    "campaign_name,adset_name,ad_name,impressions,reach,frequency,clicks,ctr,cpc,cpm,spend,"
    "actions,action_values,cost_per_action_type,purchase_roas,objective,date_start,date_stop"
)


def base_url() -> str:
    import os
    v = os.environ.get("META_API_VERSION", "v21.0")
    return f"https://graph.facebook.com/{v}"


def api_get(path: str, params: dict, token: str, paginate: bool = True) -> list | dict:
    url = f"{base_url()}/{path.lstrip('/')}"
    params = {**params, "access_token": token}
    out: list = []
    backoff = 2
    while True:
        try:
            r = requests.get(url, params=params, timeout=60)
        except requests.RequestException as e:
            # výjimka z requests nese URL i s access_token → začernit
            raise SystemExit(f"Meta API nedostupné: {redact(e)}") from None
        if r.status_code == 429 or (r.status_code >= 400 and _is_rate_limit(r)):
            if backoff > 64:
                _die(r)  # ne raise_for_status(): jeho hláška obsahuje URL s tokenem
            time.sleep(backoff)
            backoff *= 2
            continue
        if r.status_code >= 400:
            _die(r)
        payload = r.json()
        if "data" not in payload:  # single object (např. insights na 1 řádek, nebo detail)
            return payload
        out.extend(payload["data"])
        if not paginate:
            return payload["data"]
        nxt = payload.get("paging", {}).get("next")
        if not nxt:
            return out
        url, params = nxt, {}  # 'next' už obsahuje access_token i cursor


def _is_rate_limit(r: requests.Response) -> bool:
    try:
        code = r.json().get("error", {}).get("code")
        return code in (4, 17, 32, 613)
    except Exception:
        return False


def _die(r: requests.Response) -> None:
    try:
        err = r.json().get("error", {})
        msg = err.get("message", r.text)
        code = err.get("code")
        sub = err.get("error_subcode")
        raise SystemExit(redact(f"Meta API chyba (HTTP {r.status_code}, code {code}/{sub}): {msg}"))
    except ValueError:
        raise SystemExit(redact(f"Meta API chyba (HTTP {r.status_code}): {r.text[:400]}"))


def main() -> None:
    p = argparse.ArgumentParser(description="Meta Ads READ-ONLY fetch (Graph API)")
    p.add_argument("report", nargs="?",
                   help="accounts | campaigns | adsets | ads | insights")
    p.add_argument("object_id", nargs="?", help="act_<id> / campaign / adset / ad id")
    p.add_argument("--level", default="campaign",
                   help="insights level: account|campaign|adset|ad (default campaign)")
    p.add_argument("--days", type=int, help="insights: posledních N dní (time_range)")
    p.add_argument("--preset", help="insights date_preset (napr. maximum, last_30d, last_90d)")
    p.add_argument("--since", help="insights time_range od (YYYY-MM-DD)")
    p.add_argument("--until", help="insights time_range do (YYYY-MM-DD)")
    p.add_argument("--get", help="vlastní GET path, napr. 'act_123/campaigns'")
    p.add_argument("--fields", help="override fields (čárkou)")
    p.add_argument("--params", help="extra params 'k=v;k2=v2'")
    args = p.parse_args()

    token = require("META_API_TOKEN")["META_API_TOKEN"]

    # NDA: kontrolujeme účet act_… (u id kampaní/sestav se klient z ID poznat nedá).
    import re as _re
    from lib.nda import guard, filter_listing
    for _src in (args.object_id or "", args.get or ""):
        for _acc in _re.findall(r"act_\d+", _src):
            guard(_acc, "read-raw")

    extra = {}
    if args.params:
        for kv in args.params.replace(";", "&").split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                extra[k.strip()] = v.strip()

    if args.get:
        params = {"limit": 200, **extra}
        if args.fields:
            params["fields"] = args.fields
        print(json.dumps(api_get(args.get, params, token), ensure_ascii=False, indent=2))
        return

    rep = args.report
    if rep == "accounts":
        params = {"fields": args.fields or FIELDS["accounts"], "limit": 500, **extra}
        rows = api_get("me/adaccounts", params, token)
        if isinstance(rows, list):
            rows = filter_listing(rows)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if rep in ("campaigns", "adsets", "ads"):
        if not args.object_id:
            raise SystemExit(f"Report '{rep}' potřebuje act_<id>.")
        params = {"fields": args.fields or FIELDS[rep], "limit": 200, **extra}
        print(json.dumps(api_get(f"{args.object_id}/{rep}", params, token),
                         ensure_ascii=False, indent=2))
        return

    if rep == "insights":
        if not args.object_id:
            raise SystemExit("Insights potřebuje id (act_/campaign/adset/ad).")
        params = {"fields": args.fields or INSIGHTS_FIELDS, "level": args.level,
                  "limit": 500, **extra}
        if args.days:
            import datetime as _dt  # jen pro formát; 'today' bere Graph API sám
            until = args.until or None
            # time_range vyžaduje konkrétní datumy; days přepočítáme od dneška
            end = until or _today()
            start = _minus_days(end, args.days)
            params["time_range"] = json.dumps({"since": start, "until": end})
        elif args.since or args.until:
            params["time_range"] = json.dumps({"since": args.since, "until": args.until})
        elif args.preset:
            params["date_preset"] = args.preset
        else:
            params["date_preset"] = "maximum"
        print(json.dumps(api_get(f"{args.object_id}/insights", params, token),
                         ensure_ascii=False, indent=2))
        return

    p.print_help()


def _today() -> str:
    import datetime
    return datetime.date.today().isoformat()


def _minus_days(end_iso: str, days: int) -> str:
    import datetime
    y, m, d = map(int, end_iso.split("-"))
    return (datetime.date(y, m, d) - datetime.timedelta(days=days)).isoformat()


if __name__ == "__main__":
    main()

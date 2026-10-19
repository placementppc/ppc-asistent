#!/usr/bin/env python3
"""Read-only keyword research přes Google Ads Keyword Planner (KeywordPlanIdeaService).

Použití:
  # nápady ze seedů (expanze) — vrátí i sezónnost po měsících
  python scripts/google_ads/keyword_ideas.py <customer_id> --seeds "běžecké boty" "jak vybrat běžecké boty"

  # hledanost konkrétního seznamu slov (bez expanze)
  python scripts/google_ads/keyword_ideas.py <customer_id> --historical "běžecké boty na asfalt" "trailové boty"

  # nápady z URL (stránka nebo celý web)
  python scripts/google_ads/keyword_ideas.py <customer_id> --url https://www.example.cz/bezecke-boty

Volby: --lang cs (default), --geo CZ (default), --network search|search_partners,
       --limit N (default 1500), --out soubor.json

Tento skript je POUZE PRO ČTENÍ. Žádné změny v účtu neprovádí
(KeywordPlanIdeaService nic v účtu nevytváří).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11,
    "DECEMBER": 12,
}


def lookup_language(client, customer_id: str, code: str) -> str:
    """Resource name jazyka podle kódu ('cs'). Ověřeno dotazem do API, ne z paměti."""
    ga = client.get_service("GoogleAdsService")
    rows = ga.search(
        customer_id=customer_id,
        query=(
            "SELECT language_constant.resource_name, language_constant.id, "
            "language_constant.code, language_constant.name "
            f"FROM language_constant WHERE language_constant.code = '{code}'"
        ),
    )
    for row in rows:
        return row.language_constant.resource_name
    raise SystemExit(f"Jazyk s kódem '{code}' nenalezen.")


def lookup_geo(client, customer_id: str, country_code: str) -> str:
    """Resource name země podle ISO kódu ('CZ')."""
    ga = client.get_service("GoogleAdsService")
    rows = ga.search(
        customer_id=customer_id,
        query=(
            "SELECT geo_target_constant.resource_name, geo_target_constant.id, "
            "geo_target_constant.name, geo_target_constant.country_code "
            "FROM geo_target_constant "
            f"WHERE geo_target_constant.country_code = '{country_code}' "
            "AND geo_target_constant.target_type = 'Country' "
            "AND geo_target_constant.status = 'ENABLED'"
        ),
    )
    for row in rows:
        return row.geo_target_constant.resource_name
    raise SystemExit(f"Země s kódem '{country_code}' nenalezena.")


def metrics_to_dict(text: str, m) -> dict:
    monthly = [
        {
            "rok": v.year,
            "mesic": MONTHS.get(v.month.name, v.month.name),
            "hledani": v.monthly_searches,
        }
        for v in m.monthly_search_volumes
    ]
    return {
        "keyword": text,
        "avg_monthly_searches": m.avg_monthly_searches,
        "competition": m.competition.name,
        "competition_index": m.competition_index,
        "low_top_page_bid_kc": round(m.low_top_of_page_bid_micros / 1_000_000, 2),
        "high_top_page_bid_kc": round(m.high_top_of_page_bid_micros / 1_000_000, 2),
        "monthly": monthly,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Keyword Planner — read-only")
    p.add_argument("customer_id")
    p.add_argument("--seeds", nargs="*", default=[], help="seed slova pro expanzi")
    p.add_argument("--historical", nargs="*", default=[], help="konkrétní slova (bez expanze)")
    p.add_argument("--url", default=None, help="URL stránky / webu jako seed")
    p.add_argument("--site", action="store_true", help="URL brát jako celý web (site seed)")
    p.add_argument("--lang", default="cs")
    p.add_argument("--geo", default="CZ")
    p.add_argument("--network", default="search", choices=["search", "search_partners"])
    p.add_argument("--limit", type=int, default=1500)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    client = build_client()
    svc = client.get_service("KeywordPlanIdeaService")

    language = lookup_language(client, cid, args.lang)
    geo = lookup_geo(client, cid, args.geo)
    network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        if args.network == "search"
        else client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )

    out: dict = {
        "zdroj": "Google Ads Keyword Planner (KeywordPlanIdeaService)",
        "customer_id": cid,
        "jazyk": language,
        "geo": geo,
        "sit": args.network,
        "ideas": [],
        "historical": [],
    }

    if args.historical:
        req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        req.customer_id = cid
        req.keywords = args.historical
        req.language = language
        req.geo_target_constants.append(geo)
        req.keyword_plan_network = network
        resp = svc.generate_keyword_historical_metrics(request=req)
        for r in resp.results:
            d = metrics_to_dict(r.text, r.keyword_metrics)
            d["close_variants"] = list(r.close_variants)
            out["historical"].append(d)

    if args.seeds or args.url:
        req = client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = cid
        req.language = language
        req.geo_target_constants.append(geo)
        req.keyword_plan_network = network
        req.include_adult_keywords = False
        if args.seeds and args.url:
            req.keyword_and_url_seed.url = args.url
            req.keyword_and_url_seed.keywords.extend(args.seeds)
        elif args.seeds:
            req.keyword_seed.keywords.extend(args.seeds)
        elif args.site:
            req.site_seed.site = args.url
        else:
            req.url_seed.url = args.url

        for i, r in enumerate(svc.generate_keyword_ideas(request=req)):
            if i >= args.limit:
                break
            out["ideas"].append(metrics_to_dict(r.text, r.keyword_idea_metrics))

    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(txt, encoding="utf-8")
        print(f"Zapsáno: {args.out} (ideas: {len(out['ideas'])}, historical: {len(out['historical'])})")
    else:
        print(txt)


if __name__ == "__main__":
    main()

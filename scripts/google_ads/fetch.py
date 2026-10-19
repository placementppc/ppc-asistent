#!/usr/bin/env python3
"""Read-only stahování dat z Google Ads přes GAQL.

Použití:
  python scripts/google_ads/fetch.py <customer_id> <report> [--days 30]
  python scripts/google_ads/fetch.py <customer_id> --gaql "SELECT ... FROM ..."
  python scripts/google_ads/fetch.py --list-clients      # vypíše účty pod MCC

Reporty (předdefinované): accounts, campaigns, budgets, ad_groups, keywords,
  search_terms, ads, pmax_channels, pmax_asset_groups, pmax_assets, shopping
Výstup: JSON na stdout (snadno parsovatelné).

Tento skript je POUZE PRO ČTENÍ. Žádné změny v účtu neprovádí.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

REPORTS: dict[str, str] = {
    "campaigns": """
        SELECT campaign.id, campaign.name, campaign.status,
               campaign.advertising_channel_type, campaign.bidding_strategy_type,
               campaign_budget.amount_micros, campaign.target_cpa.target_cpa_micros,
               campaign.target_roas.target_roas,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr,
               metrics.conversions, metrics.conversions_value, metrics.cost_per_conversion,
               metrics.search_impression_share, metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share
        FROM campaign
        WHERE campaign.status != 'REMOVED' AND segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    "budgets": """
        SELECT campaign.name, campaign_budget.amount_micros, campaign_budget.name,
               metrics.cost_micros, metrics.search_budget_lost_impression_share,
               metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE campaign.status = 'ENABLED' AND segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    "ad_groups": """
        SELECT campaign.name, ad_group.name, ad_group.status,
               metrics.cost_micros, metrics.clicks, metrics.conversions,
               metrics.conversions_value, metrics.cost_per_conversion
        FROM ad_group
        WHERE ad_group.status != 'REMOVED' AND segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    "keywords": """
        SELECT campaign.name, ad_group.name, ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type, ad_group_criterion.status,
               metrics.cost_micros, metrics.clicks, metrics.conversions,
               metrics.conversions_value, metrics.cost_per_conversion, metrics.ctr
        FROM keyword_view
        WHERE segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    "search_terms": """
        SELECT campaign.name, ad_group.name, search_term_view.search_term,
               search_term_view.status,
               metrics.cost_micros, metrics.clicks, metrics.conversions,
               metrics.conversions_value, metrics.cost_per_conversion
        FROM search_term_view
        WHERE segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    "ads": """
        SELECT campaign.name, ad_group.name, ad_group_ad.ad.id,
               ad_group_ad.ad.type, ad_group_ad.status, ad_group_ad.ad_strength,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr,
               metrics.conversions, metrics.conversions_value, metrics.cost_per_conversion
        FROM ad_group_ad
        WHERE ad_group_ad.status != 'REMOVED' AND segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    # Rozpad PMax podle sítě — jediná cesta, jak se u PMaxu dostat "do černé skříňky".
    # segments.ad_network_type: 2=SEARCH (vč. Shopping!), 3=SEARCH_PARTNERS, 4=CONTENT(Display),
    # 7=MIXED, 8=YOUTUBE, 9=GOOGLE_TV, 10=GOOGLE_OWNED_CHANNELS, 11=GMAIL, 12=DISCOVER, 13=MAPS
    "pmax_channels": """
        SELECT campaign.name, segments.ad_network_type,
               metrics.cost_micros, metrics.conversions,
               metrics.conversions_value, metrics.impressions, metrics.clicks
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
          AND segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    # Výkon asset groups (které skupiny podkladů reálně servírují a s jakým výsledkem).
    "pmax_asset_groups": """
        SELECT campaign.name, asset_group.id, asset_group.name, asset_group.status,
               metrics.cost_micros, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.conversions_value
        FROM asset_group
        WHERE segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
    # Výkon jednotlivých podkladů. POZOR na tři věci:
    #  1) Imprese se přičítají KAŽDÉMU podkladu v zobrazené kombinaci → nesčítají se na součet
    #     kampaně. Použitelné na "co se vůbec zobrazuje", NE na dělení nákladů.
    #  2) NEPŘIDÁVEJ do SELECTu `campaign.name` — join na campaign tiše zahodí ~90 % řádků
    #     (ověřeno 7/2026: 452 → 43 řádků). Kampaň si spáruj přes `pmax_asset_groups`.
    #  3) `asset_group_asset.performance_label` v API neexistuje (ověřeno 7/2026).
    "pmax_assets": """
        SELECT asset_group.id, asset_group.name, asset_group_asset.field_type,
               asset.id, asset.type, asset.name,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions, metrics.conversions_value
        FROM asset_group_asset
        WHERE segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.impressions DESC
    """,
    "shopping": """
        SELECT campaign.name, segments.product_item_id, segments.product_title,
               metrics.cost_micros, metrics.clicks, metrics.conversions,
               metrics.conversions_value
        FROM shopping_performance_view
        WHERE segments.date BETWEEN '{START}' AND '{END}'
        ORDER BY metrics.cost_micros DESC
    """,
}


def list_clients(client) -> list[dict]:
    svc = client.get_service("GoogleAdsService")
    mcc = client.login_customer_id
    q = """
        SELECT customer_client.id, customer_client.descriptive_name,
               customer_client.currency_code, customer_client.manager,
               customer_client.status
        FROM customer_client
        WHERE customer_client.level <= 1
    """
    out = []
    for row in svc.search_stream(customer_id=mcc, query=q):
        for r in row.results:
            c = r.customer_client
            out.append({
                "id": c.id, "name": c.descriptive_name,
                "currency": c.currency_code, "manager": c.manager,
                "status": c.status.name,
            })
    return out


def run_gaql(client, customer_id: str, query: str) -> list[dict]:
    svc = client.get_service("GoogleAdsService")
    rows = []
    for batch in svc.search_stream(customer_id=customer_id, query=query):
        for r in batch.results:
            # proto-plus -> dict
            rows.append(json.loads(type(r).to_json(r)))
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Google Ads read-only fetch (GAQL)")
    p.add_argument("customer_id", nargs="?", help="Customer ID klienta (s/bez pomlček)")
    p.add_argument("report", nargs="?", help="Předdefinovaný report: " + ", ".join(REPORTS))
    p.add_argument("--days", type=int, default=30, help="Okno ve dnech (default 30)")
    p.add_argument("--gaql", help="Vlastní GAQL dotaz")
    p.add_argument("--list-clients", action="store_true", help="Vypíše účty pod MCC")
    args = p.parse_args()

    client = build_client()

    if args.list_clients:
        from lib.nda import filter_listing
        print(json.dumps(filter_listing(list_clients(client)), ensure_ascii=False, indent=2))
        return

    if not args.customer_id:
        p.error("Zadej customer_id (nebo --list-clients).")

    cid = normalize_cid(args.customer_id, nda_kind="read-raw")
    if args.gaql:
        query = args.gaql
    elif args.report:
        if args.report not in REPORTS:
            p.error(f"Neznámý report '{args.report}'. Dostupné: {', '.join(REPORTS)}")
        # GAQL nemá literál LAST_90_DAYS — používáme explicitní rozsah dat.
        end = date.today() - timedelta(days=1)  # včerejšek (dnešek bývá nekompletní)
        start = end - timedelta(days=args.days - 1)
        query = (REPORTS[args.report]
                 .replace("{START}", start.isoformat())
                 .replace("{END}", end.isoformat()))
    else:
        p.error("Zadej report nebo --gaql.")

    print(json.dumps(run_gaql(client, cid, query), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

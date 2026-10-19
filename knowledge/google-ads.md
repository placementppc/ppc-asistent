# Google Ads — referenční přehled (pro seniorní optimalizaci)

> API se vyvíjí. Když řešíš konkrétní volání/feature, ověř aktuální verzi přes Context7 MCP
> (`resolve-library-id` → "google-ads") nebo oficiální dokumentaci developers.google.com/google-ads/api.

## ⚠️ Limity API & bezpečnost účtu
Než stahuješ data nebo (po schválení) zapisuješ, drž se `api-limity-bezpecnost.md`.
Stručně: Basic token = 15 000 operací/den, Explorer = 2 880/den (produkce); rate limit je
dynamický per účet+token, překročení → `RESOURCE_TEMPORARILY_EXHAUSTED` → backoff. Žádný
paralelní souběh, dávkuj zápisy, žádné hromadné zápisy bez schválení a lidské kontroly textů.

## Hierarchie účtu
MCC (manažerský) → klientské účty (customer ID) → kampaně → sestavy (ad groups) → KW / reklamy / podklady.

## Typy kampaní (relevantní pro optimalizaci)
- **Search** — textové reklamy ve vyhledávání (RSA).
- **Performance Max (PMax)** — napříč kanály (Shopping, Search, Display, YouTube, Discover, Gmail, Maps). Viz `pmax-produktove.md`.
- **Shopping** (standardní) — produktové, řízené feedem (Merchant Center).
- **Display / Demand Gen / Video** — dosahové/poptávkové.
- **App** — propagace aplikací.

## Klíčové metriky a reporty (GAQL)
- Výkon: impressions, clicks, ctr, average_cpc, cost_micros, conversions, conversions_value, cost_per_conversion, value_per_conversion (ROAS = conversions_value / cost).
- Podíl zobrazení: search_impression_share, search_budget_lost_impression_share, search_rank_lost_impression_share.
- Search terms: `search_term_view`. Reklamy: `ad_group_ad`. KW: `keyword_view`. PMax: `campaign` + asset/listing group reporty.
- Data se tahají přes **GAQL** (Google Ads Query Language) v Google Ads API.

## Bidding strategie
Manual CPC, eCPC, Maximize clicks, Maximize conversions (+ tCPA), Maximize conversion value (+ tROAS), Target impression share. Viz `strategie-biddingu.md`.

## Smart bidding — učící fáze
Po nasazení/změně strategie cca 7–14 dní učení. Nehodnoť výkon během ní.

## Senior checklist pro Search účet
- Struktura: téma → kampaň/sestava, relevance KW ↔ reklama ↔ landing page.
- Shody KW (přesná/frázová/volná) + negativa (viz `vyhledavaci-dotazy.md`).
- Rozšíření/podklady (sitelinks, popisky, ceny, call) — kompletní a relevantní.
- Konverze: správné měření, hodnoty konverzí, vyloučení duplicit, enhanced conversions.
- Geo/čas/zařízení bid adjustmenty dle dat.

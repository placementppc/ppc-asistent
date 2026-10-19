---
name: perf_shop
description: >
  Analýza výkonu produktových kampaní — Google Standard Shopping, Performance
  Max, Merchant Center feed, Sklik produktová inzerce a Seznam Nákupy/Zboží.cz
  — z lokálních exportů dat. Použij VŽDY, když uživatel analyzuje produktové
  kampaně, srovnává výkon jednotlivých produktů v čase (WoW/MoM/YoY), řeší
  PMax vs. Standard Shopping, price benchmark / cenovou konkurenceschopnost,
  feed, zombie produkty, kanibalizaci brandu, nebo hledá potenciál v
  produktové inzerci. Načti spolu se skillem perf (sdílená metodika).
---

# perf_shop — Shopping / PMax / produktová inzerce

Nejdřív načti **perf**. Tento skill přidává produktová specifika.
Klíčový princip: **výkon produktové kampaně je z velké části výkon feedu** —
největší páky (titles, images, cena, dostupnost, custom labels) jsou mimo
Ads rozhraní.

## 0. 🔴 Povinné druhé okno — dlouhá řada (doplněno 2026-08-31)

Ke každé analýze patří **dvě** řady, ne jedna: krátká (operativa) **a měsíční řada za celou
historii účtu** (měřítko, sezóna, drift metrik). PPC operacionalizace a sladění s pravidlem „hodnoť jen
v okně změny": `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
Sloupce, které v té dlouhé řadě chceš vidět vždy: **útrata • hodnota • ROAS/PNO • konverze
• AOV (hodnota na konverzi) • CPC nebo CPM**.

Kanálový dotaz na dlouhou řadu:
```sql
SELECT segments.product_item_id, segments.month, metrics.cost_micros,
  metrics.clicks, metrics.conversions, metrics.conversions_value
FROM shopping_performance_view WHERE segments.date BETWEEN '<zalozeni uctu>' AND '<vcera>'
```
Na co se v ní u produktovek dívat: **AOV po měsících** (padající hodnota na nákup při rostoucím
počtu nákupů = kampaň se naučila prodávat nejlevnější položku feedu), **útrata na produkt
v čase** (pár položek běžně sežere polovinu rozpočtu — a to se v 30denním okně nepozná od
normálu), a **produkty s impresemi blízko nule** — drahé novinky a balíčky, které algoritmus
vůbec neservíruje, protože nemají historii.

## 1. Požadovaná vstupní data

### Google Ads — product-level (GAQL)
```sql
SELECT segments.product_item_id, segments.product_title,
  segments.product_brand, segments.product_type_l1, segments.date,
  metrics.impressions, metrics.clicks, metrics.cost_micros,
  metrics.conversions, metrics.conversions_value, metrics.ctr,
  metrics.search_impression_share,
  metrics.search_budget_lost_impression_share,
  metrics.search_rank_lost_impression_share
FROM shopping_performance_view
WHERE segments.date DURING LAST_30_DAYS
```

> ⚠️ `LAST_30_DAYS` v příkladech výše je jen **detailní řez pro operativu**. Sám o sobě
> na závěr nestačí — vždy k němu patří dlouhá řada ze sekce 0.

- `shopping_performance_view` = historický výkon (stav produktu v době záznamu).
- `shopping_product` = aktuální stav + issues bránící servírování
  (pole `issues.documentation` říká, zda řešit v MC nebo Ads).
- Pro YoY: exportuj stejné schéma za loňské období, join přes `product_item_id`.

### Price benchmark — Merchant Center Reports API
`PriceCompetitivenessProductView`: `id`, `price_micros`, `benchmark_price_micros`
(+ join s `product_view`). Odvozeně: `price_vs_benchmark = price / benchmark − 1`.

### PMax Channel Performance
UI: Campaigns → Insights & Reports → Channel Performance → export CSV.
Rozpad Search/Shopping/YouTube/Display/Discover/Gmail/Maps + feed-based vs.
asset-based. Pozn.: feed-based pod „Search" = Shopping. U retailu očekávej
60–80 % spendu na Shopping — výrazně méně = PMax utrácí v display/video,
zkontroluj kvalitu.

### PMax search terms + asset groups
Search terms insights (kampaň → Insights), asset group report — exportuj,
je to hlavní viditelnost do PMax.

### Sklik produktová inzerce / Seznam Nákupy
- Typ přehledu: **Produktové skupiny**. Sklik **neposkytuje výkon jednotlivých
  produktů** — jen skupiny + dotazy.
- Product-level workaround: GA4 data per produkt/LP + štítky v Mergado →
  produktové skupiny podle štítků (např. „nenákladné produkty" vyloučit/snížit).
  Náklad na produkt jen aproximace (CPC × návštěvy).
- Bidding třetí stranou: Seznam doporučuje bidding přes XML feed.

## 2. Product-level analýza (jádro skillu)

Postup pro srovnání období (WoW/MoM/YoY):
1. Join product_item_id přes období → delta tabulka (impr, kliky, cena,
   konverze, hodnota, CTR, CVR, PNO per produkt).
2. Segmentuj produkty:
   - **Ztrácející imprese** (−30 %+ WoW se vzorkem): lost IS budget vs. rank
     na úrovni produktu, dostupnost ve feedu, disapproval, sezónnost.
   - **Zombie** (imprese OK, CTR ~0): cena vs. benchmark, obrázek, titulek.
   - **Klesající CTR**: (1) cena vs. benchmark, (2) titulek/obrázek změněn?,
     (3) konkurent zlevnil (benchmark klesl, tvá cena ne).
   - **Vysoké PNO produkty**: kandidáti na vyloučení/snížení priority —
     ale pozor na marži (viz §4) a asistenční roli (vstupní produkty).
   - **Hvězdy s lost IS (budget)**: největší růstový potenciál.
3. **Price competitiveness syntéza:** % katalogu nad/na/pod benchmarkem.
   Orientačně: ~5 % nad benchmarkem ≈ −10 % CTR; 20 %+ nad benchmarkem
   sráží CVR na zlomek (složený efekt CTR × CVR). 60 %+ katalogu nad
   benchmarkem = systémový cenový problém → eskaluj klientovi, ne bidding.

## 3. PMax vs. Standard Shopping

- Vyhodnocuj PMax až po **4–6 týdnech a 30–50 konverzích**; Standard
  Shopping potřebuje 30+ konverzí/měsíc.
- **Kanibalizace brandu:** PMax nasává brand dotazy i přes exact match
  v Search → bez brand exclusions jsou PMax čísla nafouknutá a incrementalita
  zamlžená. Kontrola: PMax search terms insights — podíl brand dotazů.
- Srovnání PMax vs. Standard experiment: stejné produkty, stejné období,
  srovnej PNO/objem; PMax kanály rozpadni (channel performance) — čistý
  Shopping podíl vs. „ostatní" (display/video může ředit kvalitu).
- PMax „terrier" efekt: když najde levné konverze nižší kvality, honí objem —
  krmit jen nejkvalitnějšími konverzemi (purchase, ne add_to_cart).
- Kontroly PMax (2026): brand exclusions, campaign-level negatives, search
  themes, device/age controls — v auditu ověř, že jsou využité.

## 4. Ekonomika: marže a tROAS segmentace

- Jeden tROAS nemůže sloužit produktům s 60% i 10% marží — algoritmus
  defaultuje na bestsellery, zbytek hladoví.
- Segmentace podle maržových tierů (custom_label s marží ve feedu) →
  kampaně/asset groups per tier s vlastním tROAS.
- Break-even ROAS = 1 / marže (40 % marže → BE ROAS 2,5 / 250 %).
  Break-even PNO = marže.
- Value-based bidding: posílej transakčně specifické hodnoty; PNO/hodnoty
  bez DPH (Sklik to výslovně doporučuje).

## 5. Diagnostické stromy

### Produktová kampaň: zobrazení ↓ náhle
1. Feed: disapprovals / expirace / chyba uploadu (MC diagnostics, Sklik
   Centrum prodejce).
2. Fakturace, policy.
3. Lost IS budget (rozpočet došel — Q4?).
4. Změna priorit kampaní / negativ.

### PNO ↑ postupně
1. Price benchmark drift — konkurence zlevnila?
2. Mix efekt: prodává se víc nízkomaržových/levných produktů (AOV ↓)?
3. CPC ↑ (aukční tlak) při stejném CVR?
4. PMax expanze do slabších kanálů (channel performance rozpad)?

### CTR produktů ↓
1. Cena vs. benchmark (nejčastější příčina).
2. Změna obrázků/titulků ve feedu (feed changelog).
3. Konkurent s lepší nabídkou/promotions v aukci.

## 6. Playbook hledání potenciálu

1. **Hvězdy s lost IS (budget)** → rozpočet (spočti hodnotu ztracených konverzí).
2. **Produkty pod benchmarkem s dobrým PNO** → zvýšit prioritu/bid — cenová
   výhoda je dočasná, využij ji.
3. **Feed optimalizace titulků** (klíčové atributy dopředu: značka + typ +
   parametry) — nejlevnější páka na CTR.
4. **Custom labels s obchodní logikou** (marže, sezóna, skladovost,
   bestseller/longtail) → umožní segmentované biddování.
5. **Zombie čistka** → vyloučit nebo opravit (cena/obrázek), uvolní rozpočet.
6. **Sezónní příprava:** feed + skladovost hotové v říjnu; promotions/akční
   ceny na BF nasazené předem.
7. **Sklik:** Seznam Nákupy po propojení s Centrem prodejce (zobrazení i na
   Zboží.cz, Obrázky.cz, Sbazar.cz); DRTG s feedem; štítkování v Mergado
   pro pseudo-product-level řízení.

## 7. Výstup

Šablona z perf §7. U shoppingu navíc: tabulka top 20 produktů podle delta
spend/PNO, price benchmark distribuce (% nad/na/pod), PMax channel rozpad,
podíl brand dotazů v PMax (pokud dostupný), feed health poznámky.

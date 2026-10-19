---
name: perf_srch
description: >
  Analýza výkonu a diagnostika vyhledávacích kampaní — Google Ads Search a
  Sklik vyhledávání — z lokálních exportů dat. Použij VŽDY, když uživatel
  analyzuje search kampaně, řeší změny CPC/CTR/CVR/pozic ve vyhledávání,
  impression share, kvalitu (Quality Score), search terms / vyhledávací
  dotazy, match typy, klíčová slova, RSA assety nebo hledá potenciál či
  diagnostikuje propad ve vyhledávacích kampaních. Načti spolu se skillem
  perf (sdílená metodika).
---

# perf_srch — Search kampaně (Google Ads + Sklik)

Nejdřív načti **perf** (časová srovnání, statistika, caveaty, šablona reportu).
Tento skill přidává search specifika.

## 0. 🔴 Povinné druhé okno — dlouhá řada (doplněno 2026-08-31)

Ke každé analýze patří **dvě** řady, ne jedna: krátká (operativa) **a měsíční řada za celou
historii účtu** (měřítko, sezóna, drift metrik). PPC operacionalizace a sladění s pravidlem „hodnoť jen
v okně změny": `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
Sloupce, které v té dlouhé řadě chceš vidět vždy: **útrata • hodnota • ROAS/PNO • konverze
• AOV (hodnota na konverzi) • CPC nebo CPM**.

Kanálový dotaz na dlouhou řadu:
```sql
SELECT campaign.name, segments.month, metrics.cost_micros, metrics.clicks,
  metrics.impressions, metrics.conversions, metrics.conversions_value,
  metrics.average_cpc, metrics.search_impression_share
FROM campaign WHERE segments.date BETWEEN '<zalozeni uctu>' AND '<vcera>'
```
Na co se v ní u Searche dívat: **CPC v čase** (skokový růst = přeplácení, ne dražší trh),
**poměr brand / nebrand hodnoty** po měsících, a **konverze na kampaň** — když jich účet má
řádově desítky za měsíc a mezitím přibyla kampaň, dělí se signál a chytré strategie se nemají
z čeho učit.

## 1. Požadovaná vstupní data

### Google Ads — GAQL exporty (nebo ekvivalentní UI export)

Kampaně + IS (denní granularita):
```sql
SELECT campaign.name, segments.date, metrics.impressions, metrics.clicks,
  metrics.cost_micros, metrics.conversions, metrics.conversions_value,
  metrics.ctr, metrics.average_cpc, metrics.search_impression_share,
  metrics.search_budget_lost_impression_share,
  metrics.search_rank_lost_impression_share,
  metrics.search_absolute_top_impression_share
FROM campaign
WHERE campaign.advertising_channel_type = 'SEARCH'
  AND segments.date DURING LAST_30_DAYS
```

Search terms:
```sql
SELECT search_term_view.search_term, campaign.name, ad_group.name,
  metrics.impressions, metrics.clicks, metrics.cost_micros,
  metrics.conversions, metrics.conversions_value
FROM search_term_view WHERE segments.date DURING LAST_30_DAYS
```

Keywords + QS:
```sql
SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
  ad_group_criterion.quality_info.quality_score,
  ad_group_criterion.quality_info.creative_quality_score,
  ad_group_criterion.quality_info.post_click_quality_score,
  ad_group_criterion.quality_info.search_predicted_ctr,
  metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM keyword_view WHERE segments.date DURING LAST_30_DAYS
```

> ⚠️ `LAST_30_DAYS` v příkladech výše je jen **detailní řez pro operativu**. Sám o sobě
> na závěr nestačí — vždy k němu patří dlouhá řada ze sekce 0.


Pozn.: `cost_micros` / 1 000 000. GAQL nemá JOIN/GROUP BY — agregace dělej
v pandas. `segments.device`, `segments.day_of_week`, `segments.hour` přidávej
podle potřeby analýzy (device/dayparting).

### Sklik — statistický report
- Typ přehledu: **Kampaně / Sestavy / Klíčová slova** (u KW zaškrtnout sloupec
  **Dotazy** — Sklik dotazy NEfiltruje, máš 100% pokrytí, na rozdíl od Google).
- Zobrazit: po dnech (pro normalizaci období), rozpad podle zařízení.
- Sloupce: Zobrazení, Prokliky, CTR, CPC Ø, Cena, Pozice Ø, Konverze,
  Konverzní poměr, Hodnota konverze, **PNO**, Podíl zobrazení, **Kvalita**,
  **Win rate**, **Ztracená zobrazení** (komponenty: Rozpočet kampaně /
  Časové plánování / Nízký rank).
- Formáty: CSV/TSV/XLSX/JSON; **kódování ověř** (UTF-8/UTF-16/Win-1250)
  a desetinné čárky.
- Programmaticky: Sklik API Drak (`api.sklik.cz/drak/RPC2/v5`).

## 2. Diagnostické stromy

### CPC ↑ (např. +20 % WoW, signifikantní)
1. **Auction Insights / Win rate** — nový konkurent, vyšší overlap? Sklik:
   pokles Win rate = konkurenční tlak.
2. **Change history** — změna bid strategie / zvýšení tROAS/tCPA cíle?
3. **QS / Kvalita klesla?** Nižší QS = vyšší CPC za stejnou pozici. Rozpad QS:
   predicted CTR vs. ad relevance vs. LP experience — ukáže co spravit.
4. **Sezónní aukční tlak** (Q4?) — srovnej YoY, ne jen WoW.
5. **Match type drift** — broad zachytává dražší dotazy? Rozpad CPC podle
   match type + kontrola search terms.

### Zobrazení ↓
1. **Lost IS (budget) ↑** → rozpočtový strop (často při růstu CPC/poptávky).
   Sklik: „Ztracená zobrazení – rozpočet".
2. **Lost IS (rank) ↑** → bid/QS problém nebo konkurence.
3. **Poptávka klesla?** — Google Trends + YoY stejné období.
4. **Eligibility** — zamítnuté reklamy/KW, policy, fakturace, příliš úzké
   geo/jazyk/časování (pozor UTC vs. lokální čas).
5. **Nová negativa** omylem široká? Change history.

### CVR ↓
1. **Tracking first** — konverze po dnech; pád na ~0 = měření (viz perf §5).
2. **Consent/modeling změna** v mezidobí?
3. **Landing page** — rychlost, dostupnost, mobil, změna ceny/nabídky.
4. **Query drift** — search terms sklouzly do méně relevantních dotazů
   (typicky po rozvolnění match typů nebo zvýšení rozpočtu).
5. **Cenová konkurenceschopnost / skladovost** produktů na LP.

Pravidlo: skokový pád CVR = problém MIMO platformu (web/tracking);
skokový růst CPC = problém UVNITŘ platformy (aukce/bidding/QS).

### CTR ↓
1. Pozice/Abs. top IS klesly? (rank problém)
2. Nový konkurent v aukci s agresivní nabídkou?
3. RSA assety — ad strength, spálené promo (skončila akce v textu?)
4. Query mix — více generických dotazů s nižším CTR?

## 3. Analýza search terms (query mining)

1. **N-gram analýza** (1-, 2-, 3-gramy): agreguj kliky/cenu/konverze podle
   n-gramů napříč dotazy. Python: rozbij dotazy na tokeny, groupby n-gram.
2. **Waste:** n-gramy s cenou > 3× cílové CPA a 0 konverzí → kandidáti na
   negativa (zkontroluj kontext před vyloučením!).
3. **Poklady:** dotazy s konverzemi, které nejsou v účtu jako KW → nová
   klíčová slova / ad groups. Sklik postup: export dotazů + export všech KW
   účtu, anti-join.
4. **Brand leak:** broad/phrase zachytává brand (vlastní i konkurence)?
   Brand dotazy patří do brand kampaně s exact match.
5. Match type srovnání: CPC/CVR/PNO per exact/phrase/broad. Broad je OK jen
   se Smart Biddingem a čistými konverzemi.

## 4. Targeting analýza

- **Device:** rozpad CPC/CVR/PNO per zařízení; velké rozdíly → bid adjustments
  (Sklik pozor: Maximalizace konverzí přepisuje část ručních multiplikátorů).
- **Geo:** kraje/města s odlišným PNO; vylučuj/posiluj.
- **Ad schedule / dayparting:** hodinové reporty (`segments.hour`), přesun
  rozpočtu do hodin s nejvyšším CVR. Sklik: časové plánování.
- **Publika jako observation** (RLSA, in-market): srovnej CVR publik vs.
  baseline → bid adjustment nebo samostatné kampaně.
- **Demografie:** věk/pohlaví rozpad, hlavně u kategorií s vyhraněnou cílovkou.

## 5. Playbook hledání potenciálu

1. **IS headroom:** kampaně s Lost IS (budget) > 10 % a PNO pod cílem →
   navýšit rozpočet. Spočti dopad: ztracené konverze ≈ konverze ×
   (lost IS budget / IS); vynásob hodnotou konverze → rámuj jako investici.
2. **Lost IS (rank) na ziskových kampaních** → zvýšit bid/cíl nebo QS práce
   (ad relevance, LP), NE rozpočet.
3. **Dotazy-poklady** (viz §3.3) → nová KW.
4. **Dayparting příležitosti** → viz §4.
5. **tROAS/tCPA ladění:** změny po 10–15 %, 1–2× měsíčně; vyšší tROAS = nižší
   IS (systém soutěží v méně aukcích) — očekávané, ne chyba.
6. **Brand/non-brand/competitor separace** — pokud chybí, je to první
   strukturální doporučení (jiná ekonomika každé části).
7. **RSA hygiena:** min. 1, ideálně 2 RSA per ad group; plná paleta assetů.
8. **Sklik specifika:** neužívat `&` v názvech kampaní (GA ořízne URL);
   dotazy nefiltrované = plnohodnotný query mining; automatická pravidla
   na CPA/PNO/pozici tam, kde je dost dat.

## 6. Výstup

Použij šablonu z perf §7. U search navíc vždy reportuj: IS tabulku
(IS / lost budget / lost rank per kampaň), top 10 waste n-gramů,
top 10 dotazů-pokladů, QS distribuce (pokud dostupná).

---
name: perf_meta
description: >
  Analýza výkonu Meta Ads (Facebook/Instagram) kampaní z lokálních exportů
  dat (Ads Manager export, Marketing API Insights). Použij VŽDY, když
  uživatel analyzuje Meta kampaně, řeší creative fatigue, frekvenci, CTR/CPM/
  ROAS trendy, Advantage+ vs. manuální publika, rozpad podle umístění
  (feed/stories/reels), atribuci a iOS/consent zkreslení, learning phase,
  nebo hledá potenciál v Meta účtu. Načti spolu se skillem perf (sdílená
  metodika).
---

# perf_meta — Meta Ads (Facebook/Instagram)

Nejdřív načti **perf**. Tento skill přidává Meta specifika.
Klíčový princip 2026: **největší páka je kreativa a kvalita signálu, ne
mikrocílení** (Meta Performance 5: simplifikace účtu, automatizace,
diverzifikace kreativy, kvalita dat, validace výsledků).

## 0. 🔴 Povinné druhé okno — dlouhá řada (doplněno 2026-08-31)

Ke každé analýze patří **dvě** řady, ne jedna: krátká (operativa) **a měsíční řada za celou
historii účtu** (měřítko, sezóna, drift metrik). PPC operacionalizace a sladění s pravidlem „hodnoť jen
v okně změny": `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
Sloupce, které v té dlouhé řadě chceš vidět vždy: **útrata • hodnota • ROAS/PNO • konverze
• AOV (hodnota na konverzi) • CPC nebo CPM**.

Kanálový dotaz na dlouhou řadu:
```bash
python scripts/meta/fetch.py insights act_<id> --level account \
  --since <zalozeni uctu> --until <vcera> --params "time_increment=monthly"
```
Na co se v ní u Mety dívat: **AOV (hodnota na nákup) po měsících** — to je nejspolehlivější
dlouhodobé číslo, protože vzniká uvnitř Mety z jejích vlastních dat (absolutní hladina ROAS
zpřed roku je kvůli změnám atribuce a pixelů slabší); **CPM proti útratě** (když účet kdysi
jel na násobku útraty při stejném CPM, strop trhu to není); a **jaký typ kreativy tehdy vyhrával**
(`--level ad` za vítězné období) — přechod z jednoproduktových kreativ na katalogovku umí
srazit AOV, aniž by se cokoli „rozbilo".

## 1. Požadovaná vstupní data

### Marketing API Insights (nebo Ads Manager export)
- `level=campaign|adset|ad`; fields: impressions, clicks, spend, ctr, cpc,
  cpm, reach, **frequency**, actions, action_values, purchase_roas.
- Breakdowns: age, gender, region, publisher_platform, **platform_position**
  (feed/stories/reels/audience network), device_platform, hourly_stats,
  image_asset/video_asset (Dynamic Creative).
- Video: video_3_sec_views, video_p25/50/75/95/100_watched_actions
  (hook rate = 3s views / impressions; hold rate = p75/3s).
- `use_unified_attribution_setting=true` pro shodu s Ads Managerem.
- Omezení API: frequency/reach = 0 při hodinových breakdownech; video metriky
  nejdou s hodinovými breakdowny; některé kombinace breakdown × field nejdou.

### Denní granularita je nutná
Pro WoW/MoM/YoY normalizaci (perf §2) exportuj `time_increment=1`.

## 2. Atribuce a měření — čti PŘED každým závěrem

- Default okno **7d click + 1d view**. Historická data před změnou oken
  (28d click éra) nejsou přímo srovnatelná — u YoY přes tuto hranici uveď caveat.
- **iOS ATT:** podhlášení typicky 20–40 % (H); konverze dobíhají 24–72 h →
  poslední 3 dny NEvyhodnocuj.
- **View-through kontrola:** srovnej ROAS s/bez view-through (breakdown
  action_attribution_windows). Gap >30 % = view-through nafukuje čísla →
  pro rozhodování click-only.
- **Modelované konverze** používej pro reporting kontext, ne jako ground truth.
- **Korekce reality:** blended ROAS / MER (celkový obrat / celkový spend)
  jako sanity check nad platformním ROAS. Pixel+CAPI dedup (eventID/event_id
  + shodný event name) musí běžet — jinak dvojí počítání.
- Events Manager health: event coverage, event match quality, data freshness
  — zahrň do sekce Measurement health v reportu.

## 3. Creative fatigue detekce (hlavní diagnostická osa)

1. Pro každou reklamu s dostatečným vzorkem spočti: frequency, CTR trend
   (7denní okna), CPM trend, denní spend.
2. **Flag pravidlo:** frequency > 3,0 A CTR pokles > 25 % od 7denního peaku
   (H). Retargeting: prahy ~2× benevolentnější.
3. Pokles engagementu (hook rate, komentáře) předchází poklesu CTR o 2–4 dny
   — early warning.
4. Rozpad výkonu podle frekvenčních pásem (1×, 2–3×, 4–6×, 7+×): kvalitní
   kreativa drží výkon i při vyšší frekvenci — fatigue vyhlašuj z dat, ne
   jen z frekvence.
5. CPM ↑ + CTR ↓ současně = aukce penalizuje unavenou kreativu → rotace.

## 4. Diagnostické stromy

### ROAS ↓ náhle
1. **Tracking:** pixel/CAPI eventy (Events Manager), purchase má value+currency?
   dedup běží? → perf §5.
2. Learning phase reset — velká editace ad setu/rozpočtu (>20–30 %)?
3. Kreativa zamítnutá / účet flag?
4. Web/nabídka (cena, skladovost, konec akce).

### ROAS ↓ postupně
1. Creative fatigue (§3).
2. Saturace publika — reach se zplošťuje, frequency roste.
3. CPM ↑ trend — aukční tlak (Q4, volby, konkurence).
4. Signal decay — pokles event match quality, consent rate.

### CPM ↑
1. Sezónní aukce (Q4) — YoY srovnání.
2. Úzké publikum + vysoká frekvence.
3. Nízký engagement kreativy (aukce penalizuje).
4. Změna mixu umístění (např. víc FB feed = dražší než reels).

### CPA ↑ při stabilním CTR
1. CVR na webu (LP, cena) — problém mimo platformu.
2. Kvalita trafficu z nových umístění (audience network?) — rozpad podle umístění.
3. Atribuce: posun click→view mixu.

## 5. Targeting analýza (realita 2026)

- Meta zrušila velkou část detailed targetingu (konsolidace od 6/2025,
  staré možnosti přestaly doručovat 1/2026; exclusions odstraněny).
  V Advantage+ jsou tvrdé jen lokalita a min. věk — zbytek je signál,
  ne omezení.
- **Kdy Advantage+ funguje:** 50+ konverzí/týden na ad set, rozpočet
  ~50+ €/den ekvivalent, pravidelně obměňované kreativy.
- **Kdy manuál dává smysl:** malé rozpočty, high-ticket/B2B, nutnost
  vyloučit zákazníky, hyper-lokální, strukturované testy.
- **Hybrid standard:** ~70–80 % broad/ASC prospecting, 10–20 % RTG,
  5–10 % testy.
- **Lookalike posun:** místo statického LAL krmit ASC kvalitní custom
  audience (top 20 % zákazníků dle LTV) jako signál.
- **Breakdown analýza:** umístění/age/gender/region — hledej segmenty
  s výrazně horším CPA (audience network bývá podezřelý č. 1); funnel
  sanity: RTG reach < prospecting reach.
- **Struktura:** příliš mnoho ad setů = tenký signál, věčná learning phase
  → konsolidace na 2–3 dobře financované ad sety je časté doporučení č. 1.

## 6. Playbook hledání potenciálu

1. **Konsolidace fragmentovaného účtu** (ad sety pod ~50 konverzí/týden
   sloučit).
2. **Creative testing rytmus:** vysoký objem vizuálně ODLIŠNÝCH konceptů
   (hook, nabídka, UGC vs. brand, statika vs. video, formáty) — Meta uvádí
   až +32 % výkonu u vizuálně odlišných kreativ; netestovat „barvu tlačítka".
   Vítěze vyhlašuj po 50–100 konverzích na variantu.
3. **Budget realokace:** přesuny 10–20 % týdně z podprůměrných na top
   (velké skoky destabilizují learning).
4. **RTG hygiene:** vyloučení kupujících, oddělení fází (produkt/košík/
   checkout), catalog sales/DPA pokud e-shop nemá.
5. **Příležitosti v umístěních:** reels často levnější CPM — je tam kreativa
   v nativním formátu (9:16, rychlý hook)?
6. **Signal upgrade:** CAPI, event match quality, value optimization
   (posílat hodnoty objednávek) → lepší bidding.
7. **Sezónní příprava:** kreativy a publika na Q4 otestované v říjnu;
   learning phase nesmí běžet během BF špičky.

## 7. Výstup

Šablona z perf §7. U Meta navíc: fatigue tabulka (reklamy nad prahem
s frequency/CTR delta), rozpad podle umístění s CPA, frekvenční pásma, blended
MER vs. platformní ROAS, Measurement health (coverage/EMQ/dedup/freshness),
learning phase stav ad setů.

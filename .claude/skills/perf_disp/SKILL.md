---
name: perf_disp
description: >
  Analýza výkonu kampaní v obsahové síti — Google Display Network a Sklik
  obsahová síť (banner, kombinovaná reklama, branding) — z lokálních exportů
  dat. Použij VŽDY, když uživatel analyzuje display/obsahové kampaně, řeší
  umístění a jejich vylučování, frekvenci, retargeting/DRTG,
  zájmy a témata, kontextové vs. audience cílení, nebo diagnostikuje výkon
  bannerů a kombinované reklamy. Načti spolu se skillem perf (sdílená
  metodika). Pro tvorbu textů kombinované reklamy použij skill
  sklik-ppc.
---

# perf_disp — Obsahová síť (GDN + Sklik)

Nejdřív načti **perf**. Tento skill přidává display specifika.
Pro TVORBU kreativy/textů kombinované reklamy → skill
`sklik-ppc`; tady jde o ANALÝZU výkonu.

## 0. 🔴 Povinné druhé okno — dlouhá řada (doplněno 2026-08-31)

Ke každé analýze patří **dvě** řady, ne jedna: krátká (operativa) **a měsíční řada za celou
historii účtu** (měřítko, sezóna, drift metrik). PPC operacionalizace a sladění s pravidlem „hodnoť jen
v okně změny": `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
Sloupce, které v té dlouhé řadě chceš vidět vždy: **útrata • hodnota • ROAS/PNO • konverze
• AOV (hodnota na konverzi) • CPC nebo CPM**.

Kanálový dotaz na dlouhou řadu (kampaň po měsících; jednotlivá umístění až potom):
```sql
SELECT campaign.name, segments.month, metrics.cost_micros, metrics.impressions,
  metrics.clicks, metrics.conversions, metrics.conversions_value
FROM campaign WHERE segments.date BETWEEN '<zalozeni uctu>' AND '<vcera>'
```
Na co se v ní u obsahovky dívat: **CPM po měsících** (odliší dražší aukci od horší kreativy),
**podíl retargetingu na hodnotě** v čase a **kdy naposledy proběhl refresh kreativy** —
u display se únava projeví až v řádu měsíců.

## 1. Požadovaná vstupní data

### Google Ads (GAQL)
```sql
-- detail_placement_view = view s výkonem jednotlivých umístění (detail_…_view);
-- přesný název zdroje a polí ověř v dokumentaci Google Ads API přes Context7
SELECT detail_placement_view.display_name, detail_placement_view.target_url,
  campaign.name, metrics.impressions, metrics.clicks, metrics.cost_micros,
  metrics.conversions, metrics.conversions_value
FROM detail_placement_view WHERE segments.date DURING LAST_30_DAYS
```

> ⚠️ `LAST_30_DAYS` v příkladech výše je jen **detailní řez pro operativu**. Sám o sobě
> na závěr nestačí — vždy k němu patří dlouhá řada ze sekce 0.

Dále: `topic_view`, `display_keyword_view`, audience rozpady,
`metrics.display_lost_impression_share`, frekvence (reach reporty per kampaň).

### Sklik
- Typ přehledu: **Umístění** (URL stránek, kde se reklama zobrazila v OS)
  + Kampaně/Sestavy po dnech.
- Sloupce: Zobrazení, Prokliky, CTR, CPC Ø, Cena, Konverze, PNO, **Win rate**,
  Ztracená zobrazení (u obsahovky jsou komponenty Časové plánování a Nízký
  rank vždy 0 — relevantní je jen Rozpočet).
- Rozpad podle typu cílení (Retargeting / Umístění / Zájmy / Zájmy o koupi /
  Témata / KW v OS / Lookalike / DRTG).

### ⚠️ Sklik: čtení statistik při kombinaci cílení
Při více typech cílení v jedné sestavě se statistika přičítá cílení, které
v aukci **zvítězilo** (např. vyšší CPC). Retargeting 85 prokliků + Umístění 15
= 100 prokliků uživatelů, kteří splňovali OBĚ podmínky; retargeting jen častěji
vyhrál. NIKDY nesčítej cílení jako nezávislé segmenty — došlo by k dvojímu
počítání interpretace. Pro čisté srovnání cílení = oddělené sestavy.

## 2. Diagnostické stromy

### PNO ↑ / CVR ↓ v obsahovce
1. **Audit umístění** — nová umístění s vysokou cenou a 0 konverzemi?
   (nejčastější příčina driftu v display)
2. **Frekvence ↑** — stejné publikum přesycené? (fatigue)
3. **Publikum se vyčerpalo** — retargeting seznam se zmenšil (méně trafficu
   z ostatních kanálů → menší RTG pool → vyšší frekvence, horší výkon).
   Display výkon je závislý na zdraví ostatních kanálů!
4. Změna kreativy / spálené promo v banneru (skončila akce?).
5. Tracking (perf §5).

### Zobrazení ↓
1. Rozpočet (u Sklik OS jediná složka ztracených zobrazení).
2. Win rate ↓ = konkurence přeplatila → CPC/rank.
3. Zmenšení publika (RTG seznamy, změna cílení).
4. Zamítnuté bannery / formáty.

### CTR ↓ postupně
= klasická creative fatigue v display. Řešení: rotace kreativ, nové vizuály,
capping frekvence. Srovnej CTR křivku vs. kumulativní frekvenci.

## 3. Targeting analýza

- **Analýza umístění:** seřaď umístění podle ceny; vylučuj vysokoobjemová
  bez konverzí (práh: cena > 3× CPA cíl, 0 konverzí, dostatečný vzorek).
  Pozor na view-through hodnotu u brandových kampaní — nevylučuj čistě
  podle last-click.
- **Kontextové vs. audience:** srovnej výkon témat/KW v OS vs. publik
  (v Skliku přes oddělené sestavy, viz §1 varování).
- **Zájmy vs. Zájmy o koupi (Sklik):** Zájmy = širší, branding/vyvolání
  poptávky; Zájmy o koupi = užší, výkon/dokončení nákupu. Výkonnostní cíle
  → primárně Zájmy o koupi; Zájmy hodnoť benevolentněji (upper funnel).
- **Frekvenční analýza:** výkon podle frekvenčních pásem, capping tam, kde
  CVR za pásmem padá.
- **Retargeting struktura:** odděl návštěvníky produktů vs. kategorií vs.
  košíku; vylučuj konvertory; Sklik DRTG předdefinované seznamy (Návštěvníci
  produktů, Návštěvníci kategorií) mají default 14 dní — návštěvníci produktů
  typicky výkonnější → vyšší CPC. Mikrokonverze (scroll, čas, add_to_cart)
  přes upravený RTG kód/GTM = kvalitnější seznamy.

## 4. Playbook hledání potenciálu

1. **Výkonná umístění** → whitelist kampaň s vyšším CPC.
2. **RTG segmentace** (produkt/košík/checkout) s odstupňovanými bidy,
   pokud chybí.
3. **DRTG (Sklik)** s feedem, pokud běží jen statický RTG.
4. **Zájmy o koupi** segmenty relevantní k produktu, které neběží.
5. **Levný upper funnel v létě** — nižší CPC mimo sezónu pro budování
   publik před Q4.
6. **Lookalike (Sklik podobná publika)** z konvertorů, pokud nevyužité.
7. **Frequency capping** tam, kde vysoká frekvence bez konverzí pálí rozpočet.

## 5. Výstup

Šablona z perf §7. U display navíc: top 15 umístění podle ceny s PNO,
doporučená vyloučení (s vzorkem a úsporou), frekvence per kampaň, rozpad
výkonu podle typu cílení (s upozorněním na aukční vítězství u kombinací),
stav RTG seznamů (velikost, okna).

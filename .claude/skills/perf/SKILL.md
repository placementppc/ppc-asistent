---
name: perf
description: >
  Sdílený základ pro analýzu výkonu PPC kampaní (Google Ads, Sklik, Meta Ads)
  z lokálních exportů dat (CSV/XLSX/JSON). VŽDY načti tento skill jako první
  krok, když uživatel analyzuje výkon kampaní, porovnává období (mezitýdenní
  WoW, meziměsíční MoM, meziroční YoY), řeší změny CPC, zobrazení, CTR,
  konverzního poměru, PNO/ROAS, hledá potenciál nebo diagnostikuje propad
  výkonu. Kanálové skilly perf_srch, perf_shop, perf_disp a perf_meta na
  tento skill navazují — načti perf VŽDY spolu s nimi.
---

# perf — Univerzální metodika PPC analýzy

Sdílený základ pro všechny performance analýzy. Kanálová specifika hledej v:
- **perf_srch** — Search (Google Ads + Sklik vyhledávání)
- **perf_shop** — Shopping / PMax / produktová inzerce
- **perf_disp** — Obsahová síť (GDN + Sklik obsahovka)
- **perf_meta** — Meta Ads (Facebook/Instagram)

## 1. Tři roviny pravdy (drž je oddělené v každé analýze)

1. **Technická pravda** — odeslala se událost korektně? (tracking, dedup, consent)
2. **Atribuční pravda platformy** — jak si systém přisoudil kredit (model + okno)
3. **Ekonomická pravda firmy** — skutečné tržby, marže, cashflow

Fatální chyba = optimalizovat rozpočet výhradně podle jedné roviny. Každý závěr
v reportu označ, ze které roviny vychází. Platformní ROAS ≠ účetní výsledek.

## 2. Metodika časového srovnávání (WoW / MoM / YoY)

### Pravidla normalizace — VŽDY dodržuj
1. **Srovnávej stejné dny v týdnu.** Nikdy nesrovnávej období začínající jiným
   dnem. WoW = po–ne vs. předchozí po–ne.
2. **Vyluč neúplné dny/týdny.** Dnešek a poslední částečný týden do srovnání nepatří.
3. **Vyluč nedozrálé konverze.** Odečti conversion lag: e-commerce typicky
   1–7 dní, Meta iOS konverze dobíhají 24–72 h. Poslední ~3 dny konverzních
   metrik ber jako předběžné a v reportu to explicitně uveď.
4. **7denní klouzavý průměr** pro trend (eliminuje day-of-week efekt),
   4týdenní klouzavý průměr pro střednědobý trend.
5. **YoY podle nákupní události, ne data.** Black Friday se posouvá — srovnávej
   „týden před BF" vs. „týden před BF loni", ne kalendářní shodu.
6. **Vrstvení pohledů:** WoW = operativa, 4W MA = trend, MoM/Q = strategie,
   YoY = sezónní kontext.
7. **🔴 Krátké okno nikdy nestačí na soud o účtu.** Žádný závěr o rozpočtu, měřítku,
   sezóně ani o tom, že „účet nefunguje", nesmí vzniknout ze 7denního nebo 30denního
   součtu — ani z jednoho takového okna proti předchozímu. Povinné minimum je
   **8 týdnů po týdnech** (operativa) **a k tomu měsíční řada za celou historii účtu**
   (kontext: měřítko, sezóna, drift AOV). Ta druhá řada odpovídá na otázku
   „je dnešní hladina normální?", na kterou ta první odpovědět neumí.
   PPC detail, příklad a sladění s pravidlem „hodnoť jen v okně změny":
   `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
   Kanálové dotazy na dlouhou řadu: sekce 0 v `perf_srch` / `perf_shop` / `perf_disp` / `perf_meta`.

### Statistická významnost — kdy je změna reálná
- Standard: **95% konfidence** (p < 0,05).
- **Minimální vzorek na segment: ~100 kliknutí / ~1000 zobrazení.** Pod tím
  označ změnu jako „nedostatečná data / šum", NE jako trend.
- U CVR: pro detekci ±10% relativní změny při 5% baseline potřebuješ řádově
  desetitisíce návštěv. Malé kampaně vyhodnocuj agregovaně (4W okna).
- Rychlý test proporcí (CTR/CVR): dvouvýběrový z-test. Python:
  `statsmodels.stats.proportion.proportions_ztest`. U malých čísel Fisher.
- V reportu u KAŽDÉ vyhlášené změny uveď: velikost změny, vzorek, zda je
  signifikantní. Formát: „CVR −18 % (2,4 % → 2,0 %; n=4 210 vs. 3 980 kliků;
  p=0,03 → signifikantní)".

### Sezónní kalendář CEE (referenční)
Detailní kalendář: `references/sezony.md`. Klíčové: Q4 = 30–40 % ročního
obratu; Black Friday je celý „Black November"; vrchol plateb bývá pondělí/neděle
před Vánoci, ne samotný BF; back-to-school srpen–září; leden výprodeje.
Před vyhlášením „propadu" v lednu vždy srovnej s loňským lednem, ne s prosincem.

## 3. Slovník metrik

| Metrika | Vzorec | Pozor na |
|---|---|---|
| CPC | náklady / kliky | nízké CPC ≠ kvalitní traffic |
| CPM | náklady / imprese × 1000 | hodnoť s CTR dohromady |
| CTR | kliky / imprese | vysoké CTR bez konverzí = kliky bez kvality |
| CVR | konverze / kliky | tracking a consent zkreslení |
| CPA | náklady / konverze | stejné CPA ≠ stejná kvalita zákazníků |
| ROAS | tržby / náklady | bez marže může být vysoký ROAS ztrátový |
| **PNO** | náklady / obrat × 100 % | počítej z částek **bez DPH**; inverzní k ROAS |
| AOV | obrat / počet objednávek | mix produktů mění AOV bez změny výkonu |
| MER | celkový obrat / celkový ad spend | korekce platformní atribuce |

**Break-even:** break-even PNO = příspěvková marže (25% marže → BE PNO 25 %);
break-even ROAS = 1 / marže (25% marže → BE ROAS 4,0 / 400 %).
Čím větší rozdíly marží mezi produkty, tím víc value-based bidding místo
jednotného CPA/ROAS cíle.

## 4. Měřicí caveaty (EU/CZ) — kontroluj PŘED každým srovnáním

- **Consent mode v2** (povinný EEA od 3/2024): modelované konverze jsou ve
  sloupci Konverze spolu s observed. Modeling vyžaduje ~700 kliků/7 dní na
  zemi+doménu — u malých účtů nemusí běžet vůbec. Konsentující uživatelé
  konvertují 2–5× víc → CVR bez consent kontextu je zkreslený.
- **Změna consent setupu / zapnutí modelingu v mezidobí = BLOKUJ přímé
  YoY/MoM srovnání konverzí.** Doporuč blended metriky (MER) a označ to.
- **GA4 vs. platforma:** rozdíl 20–30 % je normální (jiné modely, okna).
  Rozdíl >30 % nebo opačný trend = pravděpodobně technická chyba měření.
- **Sklik:** zahrnuje modelované konverze; PNO počítá z hodnot konverzí.
- **Meta:** default 7d click + 1d view; iOS podhlašuje 20–40 %. Detail v perf_meta.

## 5. Univerzální diagnostický postup (náhlý propad výkonu)

Postupuj v tomto pořadí, dokud nenajdeš příčinu:
1. **Tracking** — konverze po dnech; pád na ~0 ze dne na den = rozbité měření
   (GTM, pixel, SEM, consent lišta). Skokový pád CVR = problém MIMO platformu.
2. **Fakturace / zamítnutí** — billing, policy, disapproved ads/produkty.
3. **Change history** — co se změnilo v účtu (bid strategie, rozpočty, negativa).
4. **Rozpočet / IS** — lost IS (budget) vs. lost IS (rank).
5. **Trh** — sezónnost (YoY!), poptávka (Trends), nový konkurent (Auction Insights).
6. **Web** — dostupnost, rychlost, ceny, skladovost, změny LP.

Postupný pokles (týdny) = spíš creative fatigue, saturace, rostoucí konkurence,
cenová nekonkurenceschopnost. Náhlý (den–dva) = spíš technika/policy/rozpočet.

## 6. Workflow analýzy (standardní kroky)

1. **Načti data + validuj schéma.** Zkontroluj kódování (Sklik: UTF-8/UTF-16/
   Windows-1250!), desetinné čárky, formát dat, měnu, mikro-jednotky
   (Google `cost_micros` / 1 000 000).
2. **Normalizuj období** dle pravidel v sekci 2. Vytvoř srovnávací páry
   (týden vs. týden, stejné dny).
3. **Spočti delta tabulku** hlavních metrik + test významnosti.
4. **Diagnostikuj** signifikantní změny přes kanálové stromy (perf_srch atd.).
5. **Hledej potenciál** dle kanálového playbooku.
6. **Sepiš report** dle šablony níže.

## 7. Šablona výstupní zprávy (povinná struktura)

```markdown
# [Klient] — [kanál] analýza [období A] vs. [období B]

## Executive summary
3–5 vět: co se stalo, proč, co s tím. Čísla s kontextem.

## Zjištění (podle závažnosti)
🔴 Kritické — aktivní ztráta peněz / rozbité měření
🟠 Střední — signifikantní negativní trend
🟢 Příležitost — nevyužitý potenciál
U každého: metrika, změna, vzorek, signifikance, pravděpodobná příčina (rovina pravdy).

## Doporučené akce
Tabulka: akce | očekávaný dopad | priorita | pracnost.

## Data caveats
Consent/modeling změny, nedozrálé konverze, malé vzorky, rozdíl GA4 vs. platforma.
```

Report končí rozhodnutím (kde škálovat, kde ubrat, co testovat), ne dashboardem.

## 8. Optimalizační rytmus (referenční)

| Frekvence | Co | Výstup |
|---|---|---|
| Denně | pacing, chyby měření, disapprovals | operativní zásah |
| Týdně | queries, assety, feed, fatigue, CPA/PNO | budget shifts, experimenty |
| Měsíčně | cross-channel, marže, kvalita leadů | management report |
| Kvartálně | atribuce, incrementalita, struktura | audit a roadmapa |

Pro velká rozpočtová rozhodnutí (±30 %+ spend) nestačí platformní data ani GA4 —
doporuč lift test / geo holdout.

## Reference
- `references/sezony.md` — sezónní kalendář CEE + pravidla YoY srovnání
- `references/prahy.md` — statistické prahy, benchmarky, learning fáze

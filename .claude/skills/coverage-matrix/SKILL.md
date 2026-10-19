---
name: coverage-matrix
description: >
  Coverage Matrix — kreativní audit účtu po buňkách (persona × úhel sdělení × formát).
  Použij, když uživatel chce analýzu pokrytí kreativ, kreativní grid/matici, zjistit
  „kde nám leží prostor", co briefovat do výroby, proč roste CPM při škálování, nebo
  říká „coverage", „pokrytí", „grid", „kreativní audit", „co vyrábět za kreativy".
  Primárně Meta Ads (vlastní reklamy + Ad Library), úhly sdělení slouží i jako
  checklist pro RSA / Sklik texty. Read-only analýza; výroba/vypnutí jen po schválení.
---

# Coverage Matrix — kreativní produkce po buňkách

Metodika je v **`knowledge/coverage-matrix.md`** — přečti si ji celou před prvním během.
Tento skill je prováděcí workflow nad ní. Platí všechna pravidla projektu ppc-fachman
(žádné změny bez schválení, cíle klienta z `clients/<klient>.md`, zapisuj a uč se).

## Kdy tenhle skill NEpoužít
- Běžná PPC optimalizace (rozpočty, bidding, dotazy) → skill `ppc-fachman`.
- Tvorba jedné reklamy/textu → stačí 6 úhlů jako checklist (viz metodika), ne celý grid.

## Workflow běhu

### Krok 0 — Klient a grid soubor
- Identifikuj klienta, přečti `clients/<klient>.md` (cíle, Meta account ID).
- Grid žije v **`clients/<klient>-coverage.md`**. Existuje → načti (persóny, minulé stavy
  buněk, minulé briefy). Neexistuje → založ (šablona níže) a nejdřív s uživatelem
  **definuj macro-persóny** (situace/motivace, ne demografie; uzavřený seznam).
  Bez odsouhlasených persón grid nestav.

### Krok 1 — PULL (data)
- Vlastní aktivní reklamy: `python scripts/meta/fetch.py ads <act_id>` + insights
  (`--level ad`, okno od posledního běhu, min. 14 dní). Sériově, respektuj limity.
- Konkurence (volitelně, když uživatel chce): Meta Ad Library — jen JESTLI v buňce
  někdo je, nikdy „jak mu to funguje".
- U účtů bez Mety: grid lze vést i nad RSA/Sklik texty (dimenze persona × úhel,
  formát odpadá) — chudší, ale čitelný.

### Krok 2 — TAG (klasifikace)
- Každou reklamu zařaď do buňky: **persona × úhel (6) × formát (6)**, volitelně TOF/MOF/BOF.
- **Uzavřená taxonomie:** úhly a formáty přesně dle metodiky, persóny přesně dle grid
  souboru. Nejde-li reklama zařadit → oprav taxonomii (po dohodě s uživatelem), nevymýšlej
  nový tag ad-hoc. Tagy zapisuj ke každé reklamě (ad_id → buňka) do grid souboru.

### Krok 3 — GRID (stav buněk)
- Obarvi buňky z VLASTNÍCH dat: Hit / Performer / Loser / Briefed / Open.
- **Práh pro barvu (malé CZ/SK účty):** buňka dostane Hit/Loser až od min. prahu
  (default: ≥ 500 Kč spendu NEBO ≥ 3 konverze v okně; jinak „běží — málo dat").
  Winner-metrika = ROAS/PNO vs. cíl klienta.
- Spočítej: pokrytí % per persóna, počty hit/performer/loser/briefed/open,
  změny od minulého běhu (nové winnery, nové losery, zaplněné buňky).

### Krok 4 — BRIEF (výstup)
Tři čtení gridu + doporučení, každé s datovou oporou:
1. **Vypnout / utlumit** — stabilní losery (jen vlastní data, nad prahem).
2. **Otestovat** — prázdné buňky s nejvyšším skóre (skóre = blízkost k existujícím
   winnerům, objem persóny, volno u konkurence). Vyplnit grid ≠ zaplnit vše.
3. **Nebriefovat** — přeplněné buňky (my + konkurence) a kombinace bez smyslu pro produkt.
- Diagnostika škálování: řádek má pokrytí a CPM roste → doporuč **novou macro-persónu**,
  ne vyšší budget. Max ~3 micro-persóny ve výrobě naráz.
- Výstup uživateli drž krátký: rozhodnutí (vypnout/briefovat) nahoře, čísla pokrytí
  jednou větou, detail jen do grid souboru.

### Krok 5 — Zápis
- Aktualizuj `clients/<klient>-coverage.md` (grid, tagy, brief, datum).
- Schválené akce (vypnutí reklamy, brief do výroby) → changelog v `clients/<klient>.md`
  se statusem `🟡 čeká na vyhodnocení` + baseline buňky (learning loop ppc-fachman).
- Obecné vzorce → `knowledge/_learnings.md`.

## Šablona `clients/<klient>-coverage.md`

```markdown
# Coverage grid — <klient>
Aktualizováno: <datum> • Okno dat: <od–do> • Zdroj: Meta act_<id>

## Persóny (uzavřený seznam)
1. <macro-persóna — situace/motivace> (micro: …)

## Grid — <persóna 1>
| úhel \ formát | UGC video | UGC photo | Designed static | Talking-head | Animation | Native static |
|---|---|---|---|---|---|---|
| Pain-point | … | | | | | |
(buňka: STAV [ad_id/y, spend, ROAS] nebo Open)

## Pokrytí
<persóna>: X % (hits A / performers B / losers C / briefed D / open E) • minule: …

## Tagy reklam
| ad_id | název | persona | úhel | formát | funnel | stav |

## Brief <datum>
- Vypnout: … • Briefovat: … • Nebriefovat: …
```

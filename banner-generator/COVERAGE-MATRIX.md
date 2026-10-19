# Coverage Matrix — metodika kreativní produkce po buňkách

Znalostní soubor. Zdroj inspirace: koncept „Creative Intelligence / Coverage Matrix" (6clickz, Milan Cidilo), adaptováno pro vlastní použití. V tomto repu je metodika závazná přes **JEDENÁCTÉ ZLATÉ PRAVIDLO** v `BANNER-INSTRUCTIONS.md` a spustitelná přes skill **`coverage-matrix`** (v kořeni appky, `.claude/skills/coverage-matrix/`).

## Základní princip

Účet se nestaví po kampaních, ale **po persónách**. Kreativní produkce se neřídí intuicí („uděláme další banner"), ale **gridem**: persona × úhel sdělení × formát × fáze funnelu. Každá aktivní reklama (vlastní i konkurenční) dostane tag a padne do své buňky.

**Klíčové pravidlo taxonomie:** pouze uzavřené kategorie. Žádné tagy typu „lifestyle", „obecné", „brandové". Pokud kreativa nejde jednoznačně zařadit, taxonomie je špatně, ne kreativa.

## Dimenze gridu

**Persóny (řádky):**
- Macro-persóna = jeden řádek gridu. Definovaná situací/motivací, ne demografií (např. „začátečník, který neví, co vybrat", „spěchající zákazník", „skeptik", „nadšenec, který srovnává parametry").
- Micro-persóny = podsekce macro-persóny, přidávají se postupně, každá dostane vlastní sekci gridu a stejný systematický průchod.

**Úhly sdělení (6 uzavřených kategorií):**
1. **Pain-point** — problém, který produkt řeší
2. **Mechanism** — jak/proč produkt funguje
3. **Aspiration** — kým se zákazník stane, cílový stav
4. **Social-proof** — recenze, čísla, UGC důkazy
5. **Identity** — „tohle je pro lidi jako ty"
6. **Comparison** — srovnání s alternativou / starým řešením (v tomto repu NIKDY s odborníkem/konkurencí — viz pravidla 10 a 17 v `CLAUDE.md` a zakázané věci v `BRAND-MANUAL.md`)

**Formáty (6 uzavřených kategorií):**
1. UGC video
2. UGC photo
3. Designed static (grafický banner)
4. Talking-head video
5. Animation / explainer
6. Native static (vypadá jako obsah, ne reklama) — má vlastní uzavřenou sub-taxonomii 10 formátů `NS1`–`NS10` (`NEREKLAMNI-KREATIVY.md`). V gridu se zapisuje jako `native-static (NS3)`, aby bylo vidět, které nereklamní formáty už klient testoval. Povinné minimum v každé sadě: 2 ze 6 konceptů (DVANÁCTÉ ZLATÉ PRAVIDLO).

**Fáze funnelu:** TOF / MOF / BOF (volitelný filtr nad gridem).

## Stavy buněk

- **Hit / Winner** — běží a vyhrává (podle winner-ROAS z vlastních dat)
- **Performer** — běží, solidní výkon
- **Loser** — běží/běžela, opakovaně padá
- **Briefed** — zadaná do výroby, čeká na spuštění
- **Open** — nedotčený prostor

**Metriky gridu:** počet live buněk (winners/losers), briefed, open, **pokrytí %** (podíl buněk s aktivní kreativou).

## Klíčová metrika: pokrytí

> ROAS říká, jestli reklamy fungují. Neříká, kolik prostoru necháváš ležet. To vidíš až z gridu — kolik buněk má aktivní kreativu.

Pokrytí je doplněk ROAS, ne náhrada. Nízké pokrytí = riziko, že škálování narazí na strop jedné kombinace.

## Tři čtení gridu

1. **Přeplněné buňky** — tlačí tam každý, ty i konkurence. → Dělej tu míň, dražší aukce, unavené sdělení.
2. **Prázdné buňky** — nikdo tam nepouští kreativu. → Kandidáti na test.
3. **Ztrátové kombinace** — stabilně ti padají. → Přestaň vyrábět.

**Zásadní omezení:** vlastní buňky posuzuješ přes výkon. Konkurenční buňky říkají jen to, JESTLI tam někdo je — ne jak mu to funguje. Ztrátovost lze určit pouze z vlastních dat. Konkurenci nesledujeme, abychom ji kopírovali, ale abychom věděli, kde se netlačit a kde je volno.

## Pravidla rozhodování

**Kdy přidat další macro-persónu:**
Když má řádek pokrytí a CPM přesto roste. Každé další euro oslovuje méně ziskového člověka — víc spendu to nevyřeší, nová persóna ano.

**Priorita výroby:**
Vyplnit grid ≠ zaplnit každou buňku za každou cenu. Některá buňka pro produkt nedává smysl. Prázdná buňka může být prázdná i proto, že ji jiní zkusili a zahodili. O pořadí výroby rozhoduje **skóre postavené na datech**, ne pocit, že buňka je volná.

**Testovací režim při stavbě persóny:**
Každou buňku řádku otestovat aspoň jednou. Ne stejný spend do každé: otestovat → přečíst vlastní data → koncentrovat budget do toho, co funguje.

**Paralelní produkce:** max ~3 micro-persóny naráz, přidávají se postupně.

## Workflow (automatizovatelný loop)

```
1. PULL  — týdenní stažení aktivních reklam z účtu (Meta Marketing API)
           + konkurenční reklamy (Meta Ad Library)
2. TAG   — klasifikace každé reklamy do buňky (persona × úhel × formát)
           → ideální úloha pro LLM klasifikátor s uzavřenou taxonomií
3. GRID  — aktualizace matice, obarvení podle winner-ROAS
4. BRIEF — automatický podklad k pondělnímu briefingu:
           co vypnout, co doplnit, co briefovat do výroby
```

Není to plug-n-play — systém připraví podklady, rozhodnutí a kreativní exekuce zůstává na stratégovi.

## Aplikace v banner-generátoru

- **Negenerovat „varianty banneru", ale generovat po buňkách**: každý koncept v `configs/<projekt>.ts` = jedna buňka (mikro-persona × úhel × formát) a nese její tag v komentáři (`// BUŇKA:` — viz pre-flight checklist v `BANNER-INSTRUCTIONS.md`).
- **Brief pro novou sadu = seznam prázdných buněk** s nejvyšší prioritou, ne „dalších 6 nápadů". Anti-recyklace (Páté zlaté pravidlo) tím dostává systém: stará sada se zmapuje do gridu a nová sada míří do buněk Open.
- **Grid per klient žije v `banners-<klient>/COVERAGE.md`** — udržuje ho skill `coverage-matrix` (kořen appky). Stavy Winner/Performer/Loser doplňuje uživatel z výkonu v Meta Ads; nástroj sám zná jen Briefed (koncept v configu) a Generated (PNG existuje).
- **Vizuální jazyk podle úhlu:** pain-point ≠ aspiration vizuál. Diverzifikační šablona médií (pastel ilustrace, lifestyle foto, infografika, komiks, UGC-style, typografie) je sub-osa uvnitř formátu, ne náhrada úhlu.

### Mapování formátů na možnosti tohoto repa

Repo vyrábí jen 2 z 6 formátů (+ 1 odvozený):

| Formát z taxonomie | V tomto repu |
|---|---|
| Designed static | ✅ default výstup (ilustrace, foto, infografika, komiks, typografie) |
| Native static | ✅ 10 nereklamních formátů NS1–NS10 (`NEREKLAMNI-KREATIVY.md`, prompt bloky v `lib/native-static.ts`) — min. 2 v každé sadě |
| Animation / explainer | ⚠️ odvozeně přes skill `animate` (MP4 z hotového PNG) |
| UGC video, UGC photo, talking-head | ❌ mimo scope — v gridu zůstávají jako Open buňky (kandidáti pro externí výrobu) |

### Mapování našich úhlů na uzavřenou taxonomii

Volné úhly z Desátého zlatého pravidla se tagují takto:

| Náš úhel (free-form) | Uzavřená kategorie |
|---|---|
| problém jako otázka, sendvič problém→akce, pojmenování problému, úleva od konfliktu | **pain-point** |
| jak to funguje, hygiena/mechanismus, edukační infografika | **mechanism** |
| cílový stav, „klidné ráno", kým se zákazník stane | **aspiration** |
| doslovná recenze, čísla, UGC, sociální tlak | **social-proof** |
| „tohle je pro lidi jako vy", příslušnost ke skupině | **identity** |
| cena/kotva („co za peníze dostanu"), srovnání se starým řešením (automat v práci, kavárna cestou, staré ruční nůžky) | **comparison** |

Pozor: **comparison NIKDY vůči zdravotním profesionálům ani konkurenčním značkám** (pravidla 10 a 17 v `CLAUDE.md`) — jen vůči ceně, starému řešení nebo vlastní nečinnosti.

## Aplikace v dalších nástrojích (mimo toto repo)

- **PPC strana appky / audity (skill `coverage-matrix`):** analýza pokrytí do auditu účtu (kolik kombinací persona × úhel klient pokrývá); 6 úhlů jako checklist pro RSA, Sklik kombinovky i Meta copy; reporting pokrytí a pohybu buněk vedle ROAS/PNO; diagnostika škálování (pokrytý řádek + rostoucí CPM → nová persóna, ne vyšší budget).

## Na co si dát pozor (kritický pohled)

- Grid má 108+ buněk na persónu — u menších CZ/SK účtů s omezeným budgetem nelze testovat vše. Skóre priorit je důležitější než samotné pokrytí.
- Tagging konzistence je Achillova pata: bez přísné uzavřené taxonomie a jednoho klasifikátoru se grid rozpadne.
- Winner-ROAS na úrovni jedné reklamy je u malých spendů statisticky křehký — pro CZ/SK e-commerce dávat buňkám minimální práh spendu/konverzí, než dostanou barvu.
- Pokrytí je prostředek, ne cíl. Cílem zůstává zisk — nízké pokrytí u profitabilního účtu není samo o sobě problém, je to informace o prostoru pro škálování.

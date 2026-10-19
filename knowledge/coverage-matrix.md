# Coverage Matrix — metodika kreativní produkce po buňkách

Znalostní soubor pro banner generátor (`banner-generator/`) a audity účtů (skill `ppc-fachman`).
Zdroj inspirace: veřejně prezentovaný koncept "Creative Intelligence / Coverage Matrix", adaptováno pro vlastní použití.

## Základní princip

Účet se nestaví po kampaních, ale **po persónách**. Kreativní produkce se neřídí intuicí ("uděláme další banner"), ale **gridem**: persona × úhel sdělení × formát × fáze funnelu. Každá aktivní reklama (vlastní i konkurenční) dostane tag a padne do své buňky.

**Klíčové pravidlo taxonomie:** pouze uzavřené kategorie. Žádné tagy typu "lifestyle", "obecné", "brandové". Pokud kreativa nejde jednoznačně zařadit, taxonomie je špatně, ne kreativa.

## Dimenze gridu

**Persóny (řádky):**
- Macro-persóna = jeden řádek gridu. Definovaná situací/motivací, ne demografií (např. pro zahradní nářadí "víkendový chalupář", "majitel velké zahrady bez času"; pro cyklistiku "dojíždějící do práce na kole", "rodina na výletech").
- Micro-persóny = podsekce macro-persóny, přidávají se postupně, každá dostane vlastní sekci gridu a stejný systematický průchod.

**Úhly sdělení (6 kategorií):**
1. **Pain-point** — problém, který produkt řeší
2. **Mechanism** — jak/proč produkt funguje
3. **Aspiration** — kým se zákazník stane, cílový stav
4. **Social-proof** — recenze, čísla, UGC důkazy
5. **Identity** — "tohle je pro lidi jako ty"
6. **Comparison** — srovnání s alternativou / konkurencí / starým řešením

**Formáty (6 kategorií):**
1. UGC video
2. UGC photo
3. Designed static (grafický banner)
4. Talking-head video
5. Animation / explainer
6. Native static (vypadá jako obsah, ne reklama)

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

## Aplikace do našich nástrojů

### Banner generátor (`banner-generator/`)
- Negenerovat "varianty banneru", ale generovat **po buňkách**: vstup = persona + úhel + formát, výstup dostane tag.
- Brief pro generování = seznam prázdných buněk s nejvyšším datovým skóre.
- Každý vygenerovaný banner nese metadata buňky → výkon se dá zpětně mapovat do gridu.
- Pro designed static / native static rozlišovat vizuální jazyk podle úhlu (pain-point ≠ aspiration vizuál).

### Audity účtů (skill `ppc-fachman`)
- Do auditu účtu přidat **analýzu pokrytí**: kolik kombinací persona × úhel klient aktivně pokrývá vs. kolik nechává ležet.
- 6 úhlů použít jako checklist při tvorbě RSA, Sklik kombinovek i Meta copy — každá sada textů by měla vědomě mířit na konkrétní úhel, ne mixovat.
- Reporting: vedle ROAS/PNO reportovat pokrytí a pohyb buněk (nové winnery, nové losery).
- Diagnostika škálování: řádek má pokrytí + roste CPM → doporučit novou persónu místo navyšování budgetu.

### Automatizace (agent nad Meta Marketing API)
- Celý loop pull → tag → grid → pondělní brief jde svěřit Claude agentovi nad Meta Marketing API.
- Tagging: klasifikace kreativ do uzavřené taxonomie (text + vizuál reklamy → buňka).
- Grid: týdenní výpočet pokrytí, detekce ztrátových kombinací, návrh priorit výroby se skórem.
- „Creative Coverage Report" jako samostatný výstup vedle běžného reportu výkonu.

## Na co si dát pozor (kritický pohled)

- Grid má 108+ buněk na persónu — u menších CZ/SK účtů s omezeným budgetem nelze testovat vše. Skóre priorit je důležitější než samotné pokrytí.
- Tagging konzistence je Achillova pata: bez přísné uzavřené taxonomie a jednoho klasifikátoru se grid rozpadne.
- Winner-ROAS na úrovni jedné reklamy je u malých spendů statisticky křehký — pro CZ/SK e-commerce dávat buňkám minimální práh spendu/konverzí, než dostanou barvu.
- Pokrytí je prostředek, ne cíl. Cílem zůstává zisk — nízké pokrytí u profitabilního účtu není samo o sobě problém, je to informace o prostoru pro škálování.

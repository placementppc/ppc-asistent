---
name: forecast
description: >
  Forecast útraty, obratu a konverzí na příští měsíc (nebo víc měsíců) z historie účtu v Google Ads,
  Skliku a Metě: scénáře konzervativní / realistický / ambiciózní jako pásmo, ne jedno číslo, a „co když
  dáme o X % víc". Použij, když uživatel řekne „forecast", „kolik utratíme", „kolik vyděláme",
  „plán na listopad", „co čekat příští měsíc", „kolik dát do rozpočtu", „co když přidáme 20 %",
  „odhad obratu", „plán na Q4". Jen čte. Navazuje na něj skill kryci-plan (rozpad na dny).
  Načti spolu s perf a tempo-rozpoctu.
---

# Forecast

Forecast odpovídá na otázku „kolik asi utratíme a kolik to přinese" **dřív**, než měsíc začne.
Je to odhad z historie, ne slib. Vždy ho podávej jako pásmo a řekni, z čeho vychází.

## 1. Na co se zeptat (jednou, všechno najednou)

1. **Který klient a který měsíc** (výchozí příští měsíc; víc měsíců `--mesicu 3`).
2. **Rozpočet**: je daný („máme 80 tisíc"), nebo ho teprve hledáme? Když je daný → `--rozpocet`.
3. **Cíl**: PNO, ROAS, nebo počet konverzí? Kolik? (zapsat do `clients/hlidac-ucty.json` → `cile`).
4. **Co se v měsíci stane**: akce, Black Friday, výprodej, nový produkt, výpadek skladu, změna cen,
   nová kampaň nebo systém. Forecast o tom neví — patří to do krycího plánu jako `--udalost`
   a do komentáře k forecastu.
5. **Odkud data**: API (účty v `clients/hlidac-ucty.json` s polem `"klient"`), nebo CSV export.

## 2. Spuštění

```bash
# z API (účty klienta z clients/hlidac-ucty.json)
python3 scripts/plan/forecast.py --klient muj-eshop
python3 scripts/plan/forecast.py --klient muj-eshop --mesic 2026-11 --mesicu 2
python3 scripts/plan/forecast.py --klient muj-eshop --mesic 2026-11 --rozpocet 80000

# bez API — vyzkoušej na smyšlených datech (2 systémy, 15 měsíců)
python3 scripts/plan/forecast.py --klient ukazka --csv scripts/plan/ukazka-data.csv
```

CSV vlastního účtu: sloupce `datum, system, naklady, obrat, konverze` (volitelně `kliky`), jeden řádek
= jeden den jednoho systému. Oddělovač čárka nebo středník, desetinná čárka projde. Data z API se
po stažení uloží do `plans/<klient>/historie.csv` — příště stačí `--csv plans/<klient>/historie.csv`.

Výstup: `plans/<klient>/forecast-<YYYY-MM>.md` + `.csv`, `--json` pro stroj.
Návratový kód: 0 OK, 1 forecast je, ale se slabší oporou (bez loňska), 2 chyba.

## 3. Jak to počítá

- **Nesuď z krátkého okna.** Tempo z posledních **8 celých týdnů po týdnech**, k tomu **měsíční řada
  celé historie** (obojí je ve výstupu). Pod 8 týdnů historie forecast odmítne.
- **Historie ≥ 13 měsíců** → loňský stejný měsíc × meziroční trend. Trend = posledních 8 týdnů letos /
  stejných 8 týdnů loni (posun o 364 dní, ať sedí dny v týdnu). V odhadu je tak sezóna i loňský
  Black Friday. Trend mimo 0,4–2,5× se ořízne a nahlásí (nejspíš se změnil účet nebo měření).
- **Kratší historie** → tempo 8 týdnů × skladba dnů v měsíci. Sezónu nezná, pásmo je širší.
  U listopadu a prosince to řekni nahlas: realita může být úplně jinde.
- **Scénáře** při stejné útratě: realistický = bodový odhad, konzervativní / ambiciózní = ± kolísání
  týdenního meziročního poměru (8 týdnů), min. ±8 %, max. ±35 % (bez loňska ±15–45 %). Každý měsíc
  dál dopředu +3 body. **Není to statistický interval**, je to poctivé pásmo.
- **Co když rozpočet +X %**: obrat ~ útrata^b. b < 1 znamená, že každá další koruna vydělá míň.
  b se zkusí odhadnout z týdnů historie (log-log), bere se jen v pásmu 0,3–0,9; jinak b = 0,6
  (obecný předpoklad, ne změřený). Odhad je zkreslený sezónou (v sezóně se víc utrácí i víc prodává).
  **Marginální PNO** = kolik stojí koruna obratu navíc. To je číslo pro rozhodnutí o navýšení,
  ne PNO celkem.

## 4. Jak výsledek podat

1. Nahoře jedna věta: „Při útratě kolem X čekej obrat Y až Z, nejspíš W (PNO A až B)."
2. Řekni metodu (YoY, nebo jen tempo) a co forecast neví (akce, sklad, ceny, měření).
3. U „co když přidáme" ukaž marginální PNO proti cíli a break-even PNO (= marže). Když marginální
   PNO přeleze cíl, další navýšení se nevyplatí, i když PNO celkem ještě vypadá dobře.
4. Velký skok rozpočtu (víc než +30 %) model jen hádá. Doporuč navyšovat po krocích 15–30 % a po
   každém kroku 7–14 dní vyhodnotit (`knowledge/rozpocty.md`). Skutečný strop najde jen test.
5. Obrat je atribuce platforem, ne tržba e-shopu. U rozhodnutí o velkém rozpočtu porovnej s e-shopem
   (skill `konverze-vs-ga4`).

## 5. Navazuje

- **Black Friday a Vánoce**: plán po týdnech s fázemi, kreativami a PDF dělá skill `black-friday`
  (stejný výpočet měsíců + rozpad podle loňské sezóny, umí i ruční exporty z Ads, Mety a GA4).

- **Krycí plán**: forecast → měsíční čísla → `scripts/plan/kryci_plan.py` je rozpadne na dny
  (skill `kryci-plan`). Bez zadaného rozpočtu si krycí plán vezme realistický forecast sám.
- Rozpočty v účtech se podle forecastu **nemění automaticky**. Změna jen po schválení člověkem,
  postup ve skillu `kryci-plan` (sekce Změny v účtu).

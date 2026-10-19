# Sklik — Zboží.cz a produktové kampaně — metodika

Cíl: optimalizovat produktovou inzerci v Sklik/Zboží.cz (CPC/ROAS, feed, segmentace).

## Specifika Sklik / Zboží.cz
- Kampaně na Zboží.cz se řídí přes Sklik (produktové kampaně) — bidding obvykle CPC nebo automatické
  strategie (cílové **PNO** / cílový podíl dle dostupnosti). Hodně závisí na **kvalitě feedu a párování**.
  - **Pozor na metriku:** Sklik jede na **PNO** (náklady/obrat v %), ne ROAS. PNO chce dolů; je to
    převrácená hodnota ROASu. Viz `knowledge/sklik.md` a `_learnings.md`.
- Klíčové je správné napárování produktů na Zboží.cz katalog (kategorie, název, EAN/párovací kód).
- **Hodnocení Zboží.cz** (kvalita nabídky, dostupnost, recenze) ovlivňuje výkon — hlídej.

## Co kontrolovat a optimalizovat
- **CPC / cílové PNO strategie**: sedí na cíl? Úprava příhozů u produktů/skupin — konzervativně, postupně.
- **Top vs. ostatní produkty**: segmentace skupin produktů; top produkty vlastní skupina s vyšším příhozem.
- **Nízko výkonné / nezobrazované („zombie") produkty**: samostatná skupina, oprava feedu, jiný příhoz.
- **Feed**: názvy, kategorie, dostupnost, ceny, párovací kódy, obrázky — nejčastější páka výkonu.
- **Vyloučení**: nežádoucí dotazy/produkty (kde to platforma umožní), nevýdělečné položky.
- **Segmentace dle marže/obratu** přes vlastní štítky/skupiny.

## Návrhy typů zásahů
- Rozdělit skupiny dle výkonu (top / standard / zombie) a nastavit jim odlišné příhozy/cíle.
- Zlepšit feed (titulky s klíčovými parametry, doplnit chybějící atributy) → lepší párování a CTR.
- Upravit příhozy u produktů s dobrým PNO (nízké) nahoru (v rámci cíle), u špatných (vysoké PNO) dolů.
- A/B na úrovni feedu (titulky/obrázky) — vyhodnoť jako experiment.

## Konzervativně
- Sklik má menší objemy než Google → o to víc pozor na statistickou významnost, delší okna.
- Změny příhozů postupně (±15–30 %), zapiš baseline (útrata, konverze/ROAS, podíl) před změnou.
- Ověř aktuální možnosti Sklik API/rozhraní (feature se mění) — viz `knowledge/sklik.md` a Sklik dokumentace.

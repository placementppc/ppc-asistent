# Prahy a benchmarky (referenční tabulka)

Hodnoty označené (H) jsou praktické heuristiky z agenturních zdrojů — orientační,
ne tvrdá fakta. Uváděj je v reportech jako orientační.

## Statistika

| Pravidlo | Hodnota |
|---|---|
| Konfidence pro rozhodnutí | 95 % (p < 0,05) |
| Min. vzorek na segment pro vyhlášení změny | ~100 kliků / ~1000 zobrazení (H) |
| CTR test na reklamu | řádově tisíce zobrazení na variantu |
| CVR test (±10 % rel. při 5% baseline) | řádově desetitisíce návštěv na variantu |
| Pod prahem vzorku | reportuj „nedostatečná data", agreguj do 4W oken |

## Learning fáze a minimální data pro vyhodnocení

| Systém | Prahy |
|---|---|
| Google Smart Bidding | po velké změně cíle (>10–15 %) restart učení; změny cílů 1–2× měsíčně, po 10–15 % |
| PMax | vyhodnocuj až po 4–6 týdnech a 30–50 konverzích; Google doporučuje min. 6 týdnů běhu s MC feedem |
| Standard Shopping | 30+ konverzí/měsíc pro smysluplné srovnání |
| Meta learning phase | ~50 konverzí na ad set/týden pro výstup z učení |
| Sklik Maximalizace konverzí | před zapnutím min. 1 týden běhu na max. CPC na všech zařízeních (doporučení Seznamu) |

## Impression share benchmarky (Search)

| Typ kampaně | Zdravé IS |
|---|---|
| Brand | 90 %+ |
| Konkurenční non-brand | 40–60 % (tlačit výš = často přeplácení) (H) |
| IS je pokrytí, ne výkon | 90 % IS může mít mizerný CVR |

## Meta creative fatigue prahy (H)

| Signál | Práh |
|---|---|
| Frequency (prospecting) | >3–4 = riziko fatigue |
| CTR pokles | >15 % za 3–5 dní, nebo >25 % od 7denního peaku |
| Flag pravidlo | frequency >3,0 A ZÁROVEŇ CTR −25 % od peaku |
| Retargeting | přirozeně vyšší frekvence — prahy zvyš ~2× |

## Měřicí odchylky

| Jev | Očekávaná hodnota |
|---|---|
| GA4 vs. platforma | rozdíl 20–30 % normální; >30 % nebo opačný trend = technická chyba |
| Meta iOS podhlášení | 20–40 % (H); konverze dobíhají 24–72 h |
| Consent mode modeling | Google uvádí obnovu >70 % ztracených cest; práh ~700 kliků/7 dní/země+doména |
| Konsentující vs. nekonsentující CVR | 2–5× vyšší u konsentujících |

## Search terms waste (H)

| Metrika | Hodnota |
|---|---|
| Typický podíl waste spend v účtu | 5–15 %+; pod 5 % má málokterý účet |
| N-gram s náklady > 3× CPA cíl bez konverze | kandidát na negativum |

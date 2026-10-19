---
name: konverze-vs-ga4
description: >
  Senior postup pro porovnání konverzí, které si připisuje reklamní systém (Sklik, Google Ads,
  Meta), s tržbami v GA4 a v e-shopu po kampaních. Odhalí kampaně, které si výkon nafukují
  (remarketing, katalog, view-through). Použij, když uživatel řekne „věřit Skliku / Metě?",
  „konverze nesedí s Analytics", „kampaň vypadá dobře, ale e-shop to necítí",
  „porovnej systém a GA4". Načti spolu s perf.
---

# Konverze podle systému vs. realita e-shopu

Každý systém si konverze počítá po svém a připisuje si i nákupy, které by přišly tak jako tak.
Senior **nevěří jednomu zdroji**. Před přidáním peněz porovná systém, GA4 a e-shop.

## 1. Postup

1. Po kampaních za **8 týdnů**: konverze a hodnota podle systému vs. transakce a tržby v GA4
   pro stejnou kampaň (zdroj / médium / kampaň).
2. Poměr systém ÷ GA4 po kampaních. Kde se liší o víc než 30 %, uveď typ kampaně a
   pravděpodobný důvod: atribuční okno, konverze po zobrazení, remarketing, cross-device,
   nezpracovaná data.
3. **Součet všech platforem vs. tržby e-shopu.** Když se blíží 100 % nebo je víc, platformy
   si dělí i nákupy z e-mailu a přímé návštěvnosti.
4. Doplň, kolik objednávek GA4 vůbec zachytí proti e-shopu (typicky 75–90 %).

## 2. Rozhodovací pravidla

- Rozpočet přidávej jen kampaním, které vycházejí dobře **i** v GA4 nebo e-shopu.
- Remarketing a katalog s velkým rozdílem: otestuj vypnutí na část období nebo regionu
  (inkrementalita), neber jejich čísla jako fakt.
- Nikdy nesčítej konverze z platforem jako tržby e-shopu.

## 3. Zkušenost týmu

- Obsahová síť a konverze po zobrazení v PMax / Display umí ukázat PNO 20 %, zatímco
  GA4 dá stejné kampani 40–50 %.
- Dynamický remarketing ve Skliku si připisuje výrazně víc, než vidí GA4.

## 4. Výstup

Tabulka: kampaň | systém (konverze, hodnota) | GA4 (transakce, tržby) | poměr | vysvětlení
(ověřeno / domněnka) | doporučení. Pod ní součet platforem vs. e-shop.

## 5. Pasti

- GA4 za poslední 1–3 dny není dopočítané. Transakce „bez zdroje" jsou nezpracované.
- Hodnota v systému může být s DPH, v GA4 bez. Sjednoť před porovnáním.

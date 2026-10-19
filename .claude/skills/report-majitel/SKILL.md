---
name: report-majitel
description: >
  Týdenní (nebo měsíční) report pro majitele e-shopu napříč Google Ads, Sklikem a Metou:
  čte se za minutu, bez marketingových zkratek, s tržbami e-shopu, důvody a doporučeními.
  Použij, když uživatel řekne „týdenní report", „report pro klienta / majitele", „jak dopadl
  týden", „shrnutí pro vedení", „pondělní report". Načti spolu s perf.
---

# Report pro majitele

Majitel nepotřebuje ROAS po kampaních. Potřebuje vědět, **jestli e-shop vydělal, proč
a co dělat dál**. Senior píše report tak, aby se přečetl za minutu a nedal se špatně pochopit.

## 1. Než začneš

- Tržby a objednávky ber z **e-shopu**. Když nejsou, z GA4 a napiš, kolik objednávek GA4
  obvykle zachytí.
- Útrata vždy z reklamních systémů, ne z GA4.
- Kalendář akcí a e-mailů za týden a změny v účtech. **Nejčastější důvod výkyvu není
  kampaň, ale akce, e-mail, sklad nebo cena.**
- Marže (a fixní náklady, pokud je máš), ať jde odhadnout, co zbylo.

## 2. Struktura (povinná)

1. **Jedna věta:** jak dopadl týden.
2. **Tabulka 6–7 čísel:** tržby, objednávky, průměrná objednávka, návštěvy, kolik návštěv
   nakoupí, útrata za reklamu, kolik Kč reklamy připadá na 100 Kč tržeb, (odhad) co zbylo
   po zboží a reklamě. Sloupce: tento týden | minulý | průměr 4 předchozích týdnů | změna.
3. **Tři věty „proč"**, každá s jedním číslem a zdrojem. Pořadí kontroly: akce a e-maily →
   sklad a ceny → změny v účtech → výkon kampaní.
4. **Tři doporučení:** co udělat, kolik to přinese nebo ušetří, kdo rozhoduje.
5. **Upozornění k datům** (drobně): nedopočítané dny, víkend, svátky, akce.
6. **Příloha pro specialistu:** kanály (útrata, hodnota podle systému, tržby v GA4).

## 3. Pravidla

- Týden = pondělí až neděle. Srovnání s minulým týdnem **a** s průměrem 4 týdnů.
- Nesuď trend z jednoho týdne. Když je týden mimo průměr, najdi konkrétní důvod,
  nebo napiš „nevím".
- Žádné zkratky v hlavní části (ROAS, PNO, CPC jen v příloze).
- Součet konverzí z platforem nikdy nevydávej za tržby.

## 4. Automatizace

Report jde generovat pravidelně: naplánovaná úloha v aplikaci Claude (počítač musí běžet),
nebo cron na serveru (Vercel) s odesláním e-mailem či do Slacku. Pro majitele stačí týdně,
pro specialistu může běžet denně jako „ranní hlídač" (čerpání rozpočtu, propady zobrazení
a jejich důvod, tempo 7 / 14 / 30 dní).

## 5. Pasti z praxe

- GA4 za neděli bývá v pondělí ráno nedopočítané. Report pusť až v úterý, nebo to napiš.
- Na testovaném účtu si platformy dohromady připsaly 98 % všech tržeb e-shopu, i když část
  přišla z e-mailu a přímé návštěvnosti.

# Reklamy a A/B testy — metodika

Cíl: poznat nejlepší/nejhorší reklamy, zlepšovat je řízeně a vyhodnocovat testy.

## Hodnocení reklam
Metriky podle cíle: CTR, konverzní poměr, CPA/ROAS, podíl zobrazení, počet konverzí.
- **Nejlepší**: vysoký konv. poměr + dobré CPA/ROAS při dostatečném objemu → škálovat, použít jako vzor.
- **Nejhorší**: nízký CTR i konv. poměr při dost datech → přepsat / pozastavit.
- U **RSA** (responzivní v hledání): sleduj hodnocení podkladů (Asset performance: Best/Good/Low),
  počet aktivních nadpisů/popisků (ideál hodně silných), Ad Strength (Excellent/Good).

## Optimalizace RSA
- Nahraď „Low" podklady, posiluj „Best" motivy. Měj dost rozmanitých nadpisů (užitky, USP, CTA, cena/akce).
- Připni jen když to dává smysl (brand do pozice 1), jinak nech systém testovat.
- Reflektuj nabídku, sezónu, USP klienta (z `clients/<klient>.md`).

## A/B testy — jak vést
1. **Hypotéza** (např. „CTA "Doprava zdarma" zvedne CTR vs. obecné CTA").
2. Jedna proměnná na test (ať je výsledek čitelný). U Google Ads využij **Experimenty / Drafts** kde to jde.
3. Definuj **úspěšnou metriku** předem (CTR / konv. poměr / CPA) a min. objem (viz `vyhodnoceni-zmen.md`).
4. Nech běžet dost dlouho (14–30 dní, ≥ ~100 prokliků/variantu), neukončuj předčasně.
5. **Vyhodnoť** a zapiš do changelogu jako experiment se závěrem + poučením. Vítěze nasaď, poražené archivuj.

## Zápis do changelogu (experiment)
Eviduj: hypotéza, varianty, start, plánované vyhodnocení, úspěšná metrika, baseline, výsledek, závěr/poučení.
Tohle je klíčové pro učení — vyhodnocené testy tvoří know-how o tom, co u klienta funguje.

## Konzervativní pravidla
> Pinovací strom, A/B minima (200 kliků / 50 konverzí / 14 dní), matice čtení CTR×CVR a tabulka
> „co testovat s očekávaným dopadem": `heuristiky-toprank.md` § 9.

- Neměň reklamy zbrkle při malém objemu (CTR/konv. poměr jsou pak šum).
- Netestuj 5 věcí naráz v jedné reklamě — nepoznáš, co zabralo.
- Zachovej historicky výkonné reklamy jako kontrolu.

## Policy checklist před zápisem textů do účtu (závazné)
Vzniklo z reálné chyby (sitelink typu „Zavolejte <číslo telefonu>" → Google zamítl).
Před KAŽDÝM zápisem reklamních textů (RSA, sitelinky, callouty, snippety) zkontroluj:
1. **Žádná telefonní čísla v textech** — telefon patří výhradně do call assetu. (Hlídá i automatika:
   `scripts/lib/policy.py::check_ad_texts`, zapojeno v create_rsa / create_search_campaign —
   write skript se při nálezu zastaví před mutací.)
2. Žádné vykřičníky v nadpisech, ne nadměrná interpunkce/CAPS.
3. Žádné zavádějící claims („nejlevnější", „č. 1") bez doložení; u zdraví/doplňků bezpečná slovesa.
4. E-mail/URL nepatří do textů (od toho jsou assety).
Když Google podklad zamítne, oprav TEXT (ne jen odvolání) — zamítnutý podklad se nezobrazuje
a stahuje výkon celé kampaně potichu.

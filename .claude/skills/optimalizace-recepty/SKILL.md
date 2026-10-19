---
name: optimalizace-recepty
description: >
  Rozcestník optimalizačních úloh (webinář Optimalizace reklam pomocí AI, 24. 9. 2026).
  Použij, když uživatel chce „optimalizovat účet" a není jasné, kterou úlohu: podle otázky
  vybere správný skill (Seznam Nákupy mobil/PC, PMax kanály, PMax produkty, vyhledávací
  dotazy, Meta strop, Meta katalog, konverze vs. GA4, report pro majitele, audit měření,
  anomálie, reklama vs. stránka, aukce a konkurence, tempo rozpočtu).
---

# Rozcestník: kterou úlohu spustit

| Otázka uživatele | Skill |
|---|---|
| Rozdělit Seznam Nákupy (Zboží.cz) na mobil a PC, CPC podle cen | `nakupy-mobil-pc` |
| Utíká PMax do Discoveru / YouTube? Proč se hýbe ROAS PMax? | `pmax-kanaly` |
| Které produkty v PMax / nákupech jen utrácí? | `pmax-produkty` |
| Které vyhledávací dotazy vyloučit? | `dotazy-vylouceni` |
| Můžu Metě přidat? Kde je strop? | `meta-strop` |
| Co propaguje katalog a komu? | `meta-katalog` |
| Hotový produktový report katalogu do PDF | `produktovy-report` |
| Věřit konverzím ze systému? | `konverze-vs-ga4` |
| Týdenní report pro majitele / ranní hlídač | `report-majitel` |
| Funguje měření? Dá se věřit konverzím před změnou biddingu? | `mereni-audit` |
| Něco skočilo nebo spadlo, co se stalo? | `anomalie` |
| Dobré CTR, špatný konverzní poměr. Sedí reklama a stránka? | `reklama-vs-stranka` |
| Zdražily prokliky, kdo nás v aukci tlačí? | `aukce-konkurence` |
| Dočerpáme rozpočet? Kam přesunout? | `tempo-rozpoctu` |

## Co platí vždy (senior standard)

1. **Nejdřív kontext, pak čísla:** cíl klienta a marže, akce a e-maily, sklad, ceny,
   změny v účtech, sezóna. Většina výkyvů má příčinu mimo kampaň.
2. **Dvě okna:** dlouhá řada (měsíce za celou historii) + 8–16 týdnů po týdnech.
   7 dní je jen spouštěč, nikdy důkaz.
3. **Každé číslo se zdrojem a obdobím.** Domněnku označ. „Nevím" je platná odpověď.
4. **Doporučení s efektem a rizikem:** co to přinese, na co to může sáhnout, kdy a podle
   čeho to vyhodnotit, kdy změnu vrátit.
5. **Jen návrh.** Zápis do účtu až po schválení a náhledu bez zápisu.
6. **Konverze posledních ~3 dnů dobíhají, GA4 zpracovává 24–72 h.** Hodnota podle systému
   není tržba e-shopu.
7. Technické detaily (API, pole, endpointy) ověř vždy v aktuální dokumentaci přes Context7.
   Do výstupů pro klienta nepatří.

## Automatizace pravidelných úloh (zkušenost týmu)

- **Ranní hlídač:** čerpání rozpočtu, propady zobrazení a jejich důvod, výkyvy CTR,
  tempo 7 / 14 / 30 dní. Specialista otevře jen účty, které svítí.
- **Akce na jeden pokyn:** promo reklama a rozšíření do všech vyhledávacích kampaní
  v Google i Skliku s datem konce. Kde systém konec neumí, naplánovat vypnutí (cron ve 23:55).
  Po akci stáhnout nabídky v remarketingu. Texty vždy lidsky zkontrolovat, AI si domýšlí podmínky.
- **Optimalizátor s mantinely:** smí jen rozpočty a pauzy v malých krocích, každou změnu
  předem posoudí druhý model, vypínač jednou proměnnou. Texty, cílení a nové kampaně jen po schválení.
- Frekvence: denně nebo týdně. Kontrola každých pár minut stojí peníze a nic nepřinese.

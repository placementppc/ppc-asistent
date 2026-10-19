---
name: pmax-produkty
description: >
  Senior postup pro produkty v Performance Max a nákupních kampaních: které produkty utrácí
  bez prodejů, vyprodané zboží v aukcích, přeplácené balíčky, produkty s vysokým PNO a návrh
  vyřazení nebo rozdělení do skupin. Použij, když uživatel řekne „které produkty v PMax
  utrácí", „vyřaď produkty z PMax", „zombie produkty", „PMax přeplácí", „listing groups".
  Načti spolu s perf a perf_shop.
---

# PMax a nákupy: produkty, které jen utrácí

Výkon produktové kampaně je z velké části výkon jednotlivých produktů. Senior se dívá na
**ekonomiku kusu**: kolik produkt vydělá po marži a kolik ho stojí reklama. Ne jen ROAS kampaně.

## 1. Než otevřeš čísla

- Marže po produktech nebo aspoň po skupinách (vlastní značka vs. cizí, kus vs. sada).
- Sklad: co je vyprodané, co se právě naskladnilo (návrat do aukcí je legitimní).
- Ceny a akce za období (zdražení mění hodnotu i ROAS).

## 2. Postup

1. Produkty za **90 dní** (a 180 dní pro kontext): útrata, prokliky, CPC, konverze, hodnota,
   ROAS. Sluč varianty jednoho produktu do rodin (velikosti, barvy, sady).
2. **Kategorie problémů:**
   - útrata nad prahem (např. 1,5× cílové CPA) a **nula konverzí**,
   - **vyprodané**, ale pořád v aukcích,
   - **zdražení prokliku** za posledních 14 dní o víc než 50 % (typicky po snížení cíle),
   - PNO nad hranicí výnosnosti po započtení marže.
3. U každého produktu rozhodni: **vyřadit** / **vlastní skupina s jiným cílem** / **nechat**
   (málo dat, sezóna, čerstvě naskladněno).
4. Zkontroluj, jestli produkt nevydělává jinde (e-shop, jiný kanál, jiná varianta nebo sada).
   Senior raději přesune rozpočet na variantu, která prodává, než aby vyřadil celou rodinu.

## 3. Rozhodovací pravidla

- Vyřazuj až při dostatku dat. Pod ~30 prokliků je nula konverzí náhoda.
- Vyprodané zboží řeš feedem (dostupnost), ne ručním vyřazením, ať se po naskladnění vrátí.
- Když PMax přeplácí levné položky a nedoplácí dražší, rozděl produkty do skupin podle marže
  nebo ceny, ne podle kategorie webu.
- Po vyřazení sleduj 2–3 týdny, jestli PMax nepřesunul útratu jinam (jiné produkty, kanály).

## 4. Výstup

Tabulka: produkt | útrata | konverze | ROAS | problém | návrh | důvod. Nahoře součet úspory
(Kč / 14 dní) a co tím můžeme ztratit (konverze, hodnota). Plán kontroly za 14 a 28 dní.

## 5. Pasti z praxe

- Po snížení tROAS i jen o pár procentních bodů může cena prokliku u části produktů vyskočit
  na několikanásobek, a to bez konverzí. Změnu cíle hodnoť i po produktech.
- Katalog a PMax často tlačí levnou variantu, zákazníci kupují jinou. Ekonomiku počítej po rodinách.
- Report produktů ukazuje konverze podle platformy. Prodeje e-shopu po produktech mohou vyjít jinak.

## 6. Technická nápověda

`perf_shop` → Product-level analýza. Zápis do skupin produktů jen po schválení
(`scripts/google_ads/update_pmax_listing_groups.py`, nejdřív náhled bez zápisu).

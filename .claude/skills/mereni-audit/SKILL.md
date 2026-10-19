---
name: mereni-audit
description: >
  Senior audit měření konverzí v Google Ads, Skliku a Metě PŘED tím, než se věří Smart
  Biddingu nebo jakémukoli výkonovému závěru: dvojí počítání, chybějící akce (hovory,
  formuláře, offline), špatné počítání (jedna vs. každá), primární vs. sekundární akce,
  hodnota konverze, atribuční okno, Consent Mode. Použij, když uživatel řekne „funguje
  měření?", „konverze nesedí", „zkontroluj tracking", „můžu věřit konverzím", „skok
  v konverzích", nebo před každou změnou biddingu a při přebírání účtu. Načti spolu s perf.
---

# Audit měření konverzí

Smart Bidding optimalizuje na to, co mu měření pošle. Když měření lže, kampaň se
optimalizuje na lež a rozpočet mizí potichu. Senior proto **audituje měření před každým
výkonovým závěrem** a při přebírání účtu. Špatná data jsou horší než žádná.

## 1. Kdy to pustit

- Přebírání účtu nebo první analýza pro nového klienta.
- Před zapnutím nebo změnou tCPA / tROAS / maximalizace konverzí.
- Konverze skočily nahoru nebo dolů bez změny v kampaních (cliff = měření, ne trh).
- Po změně webu, formuláře, pokladny, migraci, nasazení nového tagu nebo GTM.
- Pravidelně jednou za kvartál.

## 2. Co stáhnout

- Google Ads: seznam konverzních akcí (název, kategorie, zdroj: tag / GA4 import / offline /
  hovory, počítání ONE / MANY, primární vs. sekundární, atribuční okno, hodnota), konverze
  po akcích za 8 týdnů po týdnech. Google Ads API: `conversion_action` a segmentace
  `segments.conversion_action_name` (pole a názvy ověř v dokumentaci přes Context7).
- Sklik: konverzní kódy a jejich počty, zda je zapnutá hodnota objednávky.
- Meta: události pixelu a Conversions API, deduplikace přes event_id, nastavení
  „kvalita shody událostí".
- GA4: transakce / klíčové události za stejné období (`scripts/ga4/fetch.py`).
- E-shop nebo CRM: skutečné objednávky nebo poptávky. Zdroj pravdy.

## 3. Postup

1. **Inventura akcí.** Tabulka všech akcí se zdrojem, počítáním, stavem primární /
   sekundární a objemem za 8 týdnů. Akce bez názvu nebo „Website“ bez popisu = nikdo to
   nenastavil (`knowledge/heuristiky-toprank.md` § 3).
2. **Dvojí počítání.** Stejná událost měřená tagem i importem z GA4, obě primární. Nebo
   nákup počítaný ONE a lead počítaný MANY. Pravidlo: **lead-gen jedna za proklik, e-shop
   každá.** Porovnej součet primárních akcí s GA4 a e-shopem; když je systém nad 110 %
   e-shopu, hledej duplicitu.
3. **Díry.** Co se v byznysu děje a neměří se: hovory (v ČR jen klik na `tel:` odkaz,
   forwarding čísla nefungují, ověřeno v praxi), formuláře, chat, offline
   objednávky, B2B poptávky. Page-view jako primární konverze je antipattern, přepnout na
   sekundární.
4. **Hodnota.** U e-shopu musí každá primární akce nést hodnotu objednávky, bez DPH nebo
   s DPH konzistentně napříč systémy (Sklik vs. Google vs. GA4). Bez hodnoty tROAS nemá na
   čem stát.
5. **Atribuce a okno.** Model a délka okna odpovídají nákupnímu cyklu (e-shop 30 dní stačí,
   B2B 90). Při změně modelu nebo okna se řada láme, zapsat datum do changelogu.
6. **Consent Mode v2 a enhanced conversions.** EU provoz bez Consent Mode = chybí část
   konverzí a modelování nefunguje. Ověř v nastavení tagu a v GA4.
7. **Signály rozbitého měření** (`heuristiky-toprank.md` § 3): CVR nad 50 % = tag pálí při
   načtení; nula konverzí při útratě nad 5× obvyklého CPA = tracking, ne kampaň; útes na nulu
   k jednomu dni = změna tagu, webu nebo formuláře.
8. **Konzistentní řada.** Jakmile přibyla nová akce nebo import, měřené konverze se přes tu
   hranici nesmí srovnávat. Trend ber z jedné řady, která platila celou dobu (typicky GA4
   událost), a napiš, odkud je.

## 4. Rozhodovací pravidla

- **Měření materiálně rozbité** (duplicita nad 30 %, chybí hlavní akce, tag pálí na page-view
  jako primární): zastav změny biddingu a rozpočtů do opravy, nic jiného nehodnoť.
- **Drobné nesrovnalosti** (10 až 30 %): pracuj dál, ale každé číslo v reportu označ zdrojem.
- Smart Bidding pod 15 konverzí za měsíc hladoví. Tam nejdřív spoj akce nebo přidej
  mikrokonverzi jako sekundární, ne jako primární.
- Opravu měření vždy zapsat jako změnu do changelogu s datem, ať příští vyhodnocení ví,
  kde se řada láme.

## 5. Výstup

Tabulka: akce | zdroj | počítání | primární | konverze 8 týdnů | GA4 / e-shop | stav
(v pořádku / duplicita / díra / špatně nastaveno) | oprava. Pod ní jedna věta: **dá se
datům věřit, nebo ne**, a co se musí opravit před další optimalizací.

## 6. Pasti

- Sklik měří PNO, ne ROAS, a hodnotu bere jen když ji e-shop posílá v konverzním kódu.
- Meta bez deduplikace pixel + CAPI počítá nákup dvakrát a Ads Manager to neukáže.
- GA4 za poslední 1 až 3 dny není dopočítané. Nesrovnávej včerejšek.
- Google Ads API umí konverzní akce založit (`scripts/google_ads/setup_conversions.py`,
  dry-run bez `--apply`), ale zápis jen po schválení uživatele.

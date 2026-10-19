---
name: tempo-rozpoctu
description: >
  Senior kontrola tempa čerpání měsíčního rozpočtu napříč Google Ads, Sklikem, Metou
  a ChatGPT Ads: kolik je utraceno vs. kolik by mělo být k dnešnímu dni, které kampaně
  dojedou dřív a které nedočerpají, a návrh přesunů bez rozhození biddingu. Použij, když
  uživatel řekne „jak jsme na tom s rozpočtem", „dočerpáme?", „utrácí to moc rychle",
  „kolik zbývá do konce měsíce", „přerozděl rozpočet", nebo jako týdenní kontrolu.
  Načti spolu s perf, metodika v knowledge/rozpocty.md.
---

# Tempo čerpání rozpočtu

Klient má měsíční strop a cíl. Senior hlídá, aby rozpočet **nedošel 20. dne u kampaně,
která vydělává**, a aby neležel u kampaně, která nic nedělá. Přesuny dělá po krocích,
ne skokem.

## 1. Data

- Měsíční rozpočet klienta po systémech a případně po kampaních z `clients/<klient>.md`.
  Když tam není, zeptej se, nehádej.
- Útrata od 1. dne měsíce po dnech a po kampaních: Google Ads (`fetch.py <účet> campaigns`,
  `budgets`), Sklik (`fetch.py campaigns`), Meta (`scripts/meta/fetch.py`), ChatGPT Ads
  (`/chatgpt-ads`). Denní rozpočty a stav „omezeno rozpočtem“.
- Cílová metrika po kampaních za 8 týdnů (CPA nebo PNO), ztracený podíl zobrazení kvůli
  rozpočtu.

## 2. Postup

1. **Očekávané čerpání k dnešku** = měsíční rozpočet × (uplynulé dny ÷ dny v měsíci).
   Odchylka do ±10 % je v pořádku, nepiš o ní.
2. **Projekce do konce měsíce** z průměru posledních 7 dnů (ne z celého měsíce, tempo
   se mění). U sezónních klientů zohledni, že druhá půlka měsíce bývá jiná než první
   (výplaty, akce, Black Friday).
3. **Kampaně, které dojedou dřív:** projekce přes 100 % stropu. Rozděl: plní cíl (nechat
   dojet, nebo navýšit po dohodě) vs. neplní cíl (brzdit hned).
4. **Kampaně, které nedočerpají:** projekce pod 80 %. Nejdřív důvod (nízká nabídka, malý
   dosah, slabá relevance, zamítnuté reklamy), rozpočet není problém, navyšovat ho
   nepomůže (`knowledge/rozpocty.md`).
5. **Návrh přesunů.** Odkud kam, kolik, od kdy. Krok max +15 až 30 % na kampaň, po
   změně 7 až 14 dní nechat doběhnout. Rozdělit podíl zobrazení ztracený kvůli rozpočtu
   vs. kvůli hodnocení dřív, než někam přidáš (`heuristiky-toprank.md` § 1).
6. **Sdílené rozpočty a PMax.** Řeš na úrovni portfolia. PMax po změně rozpočtu mění
   kanály druhý den, zkontroluj (zkušenost z praxe).

## 3. Rozhodovací pravidla

- Denní rozpočet × 30,4 je měsíční strop systému, Google smí utratit 2× denní v jednom
  dni. Projekci dělej z reálné útraty, ne z nastavení.
- Kampaň plní cíl a brzdí ji rozpočet: navýšit, ale po krocích a se zápisem baseline.
- Konec měsíce a zbývá hodně: **nevylévat** do remarketingu nebo Display, aby se
  „dočerpalo“. Nedočerpaný rozpočet je lepší než drahé konverze. Klientovi to napiš.
- Učící fáze po změně rozpočtu nebo biddingu: data z ní neber jako finální.
- Žádná změna bez schválení uživatele. Výstup je návrh.

## 4. Výstup

Tabulka: systém / kampaň | měsíční strop | utraceno | očekáváno k dnešku | projekce
konec měsíce | cíl (CPA / PNO) plní? | omezeno rozpočtem | návrh. Pod ní jedna věta pro
klienta: dočerpáme, nebo ne, a jestli to vadí.

## 5. Automatizace

Týdenní běh (pondělí) jako součást `report-majitel` nebo samostatně do Slacku. Denní
tempo hlídá `anomalie` (ranní hlídač). Nastavit konec akce v systému nebo cron ve 23:55,
kde systém konec neumí (`optimalizace-recepty`).

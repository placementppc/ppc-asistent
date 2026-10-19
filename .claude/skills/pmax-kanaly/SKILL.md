---
name: pmax-kanaly
description: >
  Senior postup pro Performance Max: kam tečou peníze podle kanálů (nákupy, vyhledávání,
  YouTube, Display, Discover, Gmail) a jak se to mění v čase, proč roste nebo klesá ROAS
  a co s tím. Použij, když uživatel řekne „PMax utíká do Discoveru / YouTube", „výkon kanálů
  PMax", „kolik je v searchi a kolik mimo", „proč PMax zhoršuje ROAS", „zkontroluj PMax po
  změně tROAS". Načti spolu s perf a perf_shop.
---

# PMax: výkon kanálů v čase a proč se hýbe ROAS

Senior nezačíná otázkou „kam PMax utíká", ale **„co přesně se změnilo: cena prokliku,
konverzní poměr, hodnota objednávky, nebo mix kanálů?"** Kanály jsou jedna z hypotéz,
ne automatický viník.

## 1. Než otevřeš čísla

- Jaký je cíl (tROAS / break-even) a jaký je typ PMax: **jen feed** (produktové reklamy),
  nebo **feed + textové a obrazové podklady**, nebo **bez feedu**. Každý typ „utíká" jinak.
- Changelog klienta a historie změn: rozpočet, tROAS, nové asset groups, feed, akce, sklad.
- Sezóna a velké akce. Po velké akci PMax typicky několik týdnů „dotahuje" cíl a přelévá se
  do levných kanálů.

## 2. Postup

1. **Dlouhá řada po měsících** (celá historie, kterou systém po kanálech ukáže) a **16 týdnů
   po týdnech**. Pro každý kanál: útrata, podíl, CPC, konverzní poměr, ROAS. Nákupy odděl od
   textové reklamy ve vyhledávání, jinak se schovají pod „vyhledávání".
2. **Podíl útraty mimo nákupy a vyhledávání** v čase. Hledej trend, ne jeden měsíc.
3. **Souvisí to s výkonem?** Porovnej podíl mimo vyhledávání s ROAS, CPC a konverzním
   poměrem celku. Typický vzorec: víc mimo vyhledávání = levnější, ale horší prokliky.
   Jestli se to na ROAS projeví, ukážou až data.
4. **Rozlož změnu ROAS** mezi dvěma obdobími na **CPC × konverzní poměr × průměrnou
   objednávku**. Řekni, který faktor změnu nese. Tohle je nejdůležitější krok celé analýzy.
5. **Zlomy spoj s událostmi** (změny nastavení, feed, akce, sklad). Co nejde vysvětlit,
   označ jako „nevím", nevymýšlej příčinu.
6. **Brand v PMax:** kolik útraty a hodnoty jde z brandových dotazů. PMax si ho rád připisuje.
   Zkontroluj vyloučení značky a vylučující slova na úrovni účtu.

## 3. Rozhodovací pravidla

| Zjištění | Co dělá senior |
|---|---|
| PMax bez feedu jde z většiny do Discoveru / Display a konverzní poměr padá | vypnout, obecnou poptávku pokrýt klasickou vyhledávací kampaní |
| Feedová PMax drží nákupy, ale zdražuje proklik | páka jsou produkty a cíl: vyřadit produkty bez konverzí, vyprodané, zdražené balíčky |
| Po změně cíle nebo rozpočtu skočí podíl mimo nákupy nad ~10 % | nejdřív zkontrolovat feed (vypadlé produkty), teprve pak řešit cíl |
| PMax dlouhodobě upadá a ladění cíle nepomáhá | zvážit novou kampaň s cílovým ROAS od začátku místo dalšího ladění (zkušenost týmu) |
| Vysoký podíl brandu v PMax | vyloučení značky, brand nechat brandové kampani |

- Cíl (tROAS) měň v krocích **do 10 %** a nejdřív po **14 dnech** od poslední změny.
- Kanál pod ~30 konverzí nehodnoť přes ROAS. Je to šum.
- Před sezónou (vrchol oboru, Black Friday) PMax nerozděluj. Nové učení v nejhorší chvíli.

## 4. Výstup

Executive summary ve 3 větách (utíká / neutíká, proč se hýbe ROAS, co jako první) →
tabulka měsíců → tabulka 16 týdnů → rozklad ROAS → zlomy s událostmi → doporučení
v pořadí podle dopadu, s odhadem efektu a plánem kontroly (co zkontrolovat zítra a za 14 dní).

## 5. Pasti z praxe

- „PMax utíká" je častý dojem. Na jednom účtu šla skoro celá útrata hlavní PMax do nákupů
  a ROAS klesal kvůli dražšímu prokliku. Utíkala jen PMax bez feedu (podíl Discoveru
  za pár měsíců z jednotek procent na většinu útraty, konverzní poměr pod 1 %).
- Přidání textových a obrazových podkladů do feedové PMax otevírá Discover, YouTube a Display.
- Systém ukáže rozpad po kanálech jen za omezenou historii. Starší měsíce máš jen jako součet.
- Hodnota konverzí je podle Google Ads, ne tržby e-shopu. Pro rozhodnutí o penězích
  srovnej s e-shopem nebo GA4.

## 6. Technická nápověda (ověř v dokumentaci)

Dotazy na kanály a produkty: `perf_shop` → PMax Channel Performance. Vždy ověř aktuální
verzi Google Ads API přes Context7, rozpad PMax po kanálech se v API měnil.

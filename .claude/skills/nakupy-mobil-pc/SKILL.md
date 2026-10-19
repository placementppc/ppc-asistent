---
name: nakupy-mobil-pc
description: >
  Senior postup pro produktovou kampaň ve Skliku na Seznam Nákupy (dřív Zboží.cz):
  rozdělení na mobil a počítač, cena prokliku podle cenových hladin a výkonu produktů,
  rozpočty oddělených kampaní. Použij, když uživatel chce „rozdělit Nákupy / Zboží na mobil
  a PC", „nastavit CPC na Seznam Nákupech", „segmentovat produktovou kampaň ve Skliku",
  „cenové hladiny", „které produkty na Nákupech utrácí". Načti spolu s perf a perf_shop.
---

# Seznam Nákupy: mobil vs. PC a cena prokliku podle cenových hladin

Senior se neptá „jaké CPC nastavit", ale **„kolik mi přinese jeden proklik na daném zařízení
a u daného zboží, a kolik z toho můžu dát Seznamu"**. Celý postup stojí na hodnotě prokliku.

## 1. Než otevřeš čísla

- **Cíl klienta** z `clients/<klient>.md`: cílové PNO, nebo aspoň marže (hranice výnosnosti
  = marže). Vlastní značka a cizí zboží mívají jinou marži, a proto i jiné cílové PNO.
- **Co se v e-shopu dělo:** akce, výprodeje, výpadky skladu, změna cen, nové sady.
  Bez toho si spleteš výkyv s trendem.
- **Sezóna:** na Nákupech bývá listopad nejsilnější měsíc. Strukturu měň nejpozději 6–8 týdnů
  předem, ať se nové kampaně stihnou ustálit.
- **Jak se hodnota konverze počítá** (s DPH / bez DPH). Jinak porovnáváš PNO se špatnou marží.

## 2. Postup

1. **Zařízení, dlouhá řada.** Po letech a měsících za celou historii, pak 12 týdnů po týdnech:
   CPC, konverzní poměr, **hodnota na proklik** (hodnota ÷ prokliky), PNO, podíl útraty.
   Rozdíl konverzního poměru ověř statisticky. Rozdělovat má smysl, jen když rozdíl drží
   dlouhodobě, ne jeden měsíc.
2. **Brzdí rozpočet, nebo cena prokliku?** Porovnej útratu s denním rozpočtem. Když kampaň
   utrácí zlomek rozpočtu, přidávání peněz nic neudělá. Jediná páka je cena prokliku.
3. **Cenové hladiny.** Rozlož ceny sortimentu a najdi přirozené hranice (typicky levné /
   běžné / prémiové zboží / sady). Pro každou hladinu spočítej PNO
   po zařízeních. Levné zboží skoro vždy prodělává, protože proklik stojí stejně jako
   u drahého a objednávka je malá.
4. **Segmenty, které hýbou penězi:** vlastní značka vs. cizí, jednotlivé kusy vs. sady, top produkty,
   „zombie" (útrata bez prodejů), vyprodané, produkty bez jediné návštěvy.
   Když Sklik produkty neukáže, odhadni náklad z GA4 podle vstupní stránky
   (návštěvy × náklad na návštěvu daného zařízení) a vždy napiš, že jde o odhad.
5. **Struktura:** dvě kampaně, **PC** a **mobil + tablet**. Opačné zařízení −100 % na úrovni
   KAMPANĚ (a na sestavách jako pojistka), ať to platí i pro později přidané sestavy.
   Uvnitř nepřekrývající se produktové skupiny výrobce × cenová hladina.
6. **Cena prokliku pro každou skupinu:** hodnota na proklik × cílové PNO. Kde je málo dat
   (pod ~15 objednávek za rok), jdi jen polovinou cesty. **První krok nejvýš ±30–40 %**
   proti dnešku, zbytek po vyhodnocení.
7. **Rozpočty:** strop 3–5× nad reálnou útratou (chrání před přečerpáním po zvýšení CPC),
   nebo rozdělení dnešního rozpočtu podle podílu hodnoty. Obě varianty nabídni.
8. **Co vyloučit:** kategorie, které na Nákupy nepatří (poplatky, dárky zdarma, vzorky),
   vyprodané zboží řeš ve feedu, ne cenou prokliku.

## 3. Jak to senior prezentuje

- Jedna věta pro majitele: kde dnes přepláceme a kolik to stojí.
- Tabulka zařízení (dlouhá řada) → tabulka cenových hladin → navržená struktura s CPC
  (dnes / první krok / cíl) a rozpočty.
- Očekávaný efekt jako rozpětí, ne jedno číslo. Riziko (na co to může sáhnout).
- **Plán vyhodnocení:** za 4 a 8 týdnů, jen okno od změny, po týdnech. Kritérium návratu
  (např. konverze −25 % bez zlepšení PNO → vrátit krok).
- Co je ověřené a co domněnka (typicky: odhad nákladu na produkt z GA4).

## 4. Pasti z praxe

- Jedno CPC na celý sortiment = levné kusy a mobil dotují zbytek.
- Hodnocení podle CPC místo hodnoty na proklik. Stejné CPC může mít úplně jiný výnos.
- Mix zařízení se v čase mění (na jednom účtu se podíl PC na útratě za pár let zhruba zpolovičil). Průměr za
  celý účet pak tiše zhoršuje PNO.
- Sklik nemusí umět filtr na konkrétní produkt. Nejhorší produkty pak označ štítkem ve feedu
  (vlastní štítek top / standard / zombie / vyprodáno) a dej jim vlastní skupinu.
- Nové kampaně nemají historii, první 1–2 týdny kolísají. Nehodnoť je po třech dnech.

## 5. Technická nápověda

🔴 **Nejdřív si přečti `knowledge/sklik.md`, kapitolu „Než začneš volat API".** Je v ní, co už
víme, ať to neobjevuješ znovu: Sklik není v Context7 (dokumentace je na api.sklik.cz),
`clickMoney` je v haléřích a `conversionValue` v korunách, rozpad podle zařízení funguje,
výkon po jednotlivých produktech Sklik nedává (ber ho z GA4) a filtr na konkrétní produkt API
odmítá.

Data a konektory: `perf_shop` → Sklik produktová inzerce / Seznam Nákupy, skripty `scripts/sklik/`.
Před zápisem struktury nech Sklik změnu zkontrolovat (validace bez zápisu) a zapisuj až po schválení.

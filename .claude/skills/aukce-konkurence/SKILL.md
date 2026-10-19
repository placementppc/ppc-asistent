---
name: aukce-konkurence
description: >
  Senior čtení Statistik aukcí (Auction Insights) v Google Ads, Search i Shopping: kdo
  přišel a kdo odešel, kdo tlačí CPC, jestli ztrácíme podíl zobrazení kvůli rozpočtu nebo
  kvůli pozici, a co s tím. Použij, když uživatel řekne „zdražily prokliky", „kdo nás
  přeplácí", „konkurence v aukci", „Temu", „podíl zobrazení padá", „statistiky aukcí".
  Načti spolu s perf a perf_srch nebo perf_shop.
---

# Statistiky aukcí a konkurence

Dražší prokliky bez změny v účtu znamenají, že se změnila aukce. Senior **nejdřív vyloučí
vlastní zásahy**, pak čte aukce po měsících a rozhoduje, jestli se bránit, nebo ustoupit.

## 1. Data

- Google Ads API Statistiky aukcí **nevystavuje**. Export z UI: Statistiky aukcí → období
  po měsících → stáhnout CSV, zvlášť Search a Shopping, na úrovni kampaně. Exporty pojmenuj
  konzistentně (účet, typ kampaně, měsíc) a slož je do jedné tabulky po měsících. U NDA
  klientů pracuj jen s anonymizovanými exporty.
- K tomu z API za stejné měsíce: podíl zobrazení, **ztracený podíl kvůli rozpočtu**
  a **kvůli hodnocení**, CPC, pozice nad, konverze (`scripts/google_ads/fetch.py <účet>
  campaigns`; názvy polí ověř přes Context7).
- Sklik Statistiky aukcí nemá. Tam jen podíl zobrazení a CPC po měsících.

## 2. Postup

1. **Vlastní zásahy nejdřív.** `change_event` a changelog za období: změna biddingu, cíle,
   rozpočtu, shody, pozastavení. Bez toho nelze říct, že za CPC může konkurence.
2. **Matice 2×2 podle `knowledge/heuristiky-toprank.md` § 1:** ztrácíme kvůli rozpočtu,
   nebo kvůli hodnocení? Rank-limited kampaň rozpočtem nespravíš, budget-limited
   nabídkou nespravíš.
3. **Řada po měsících za 6 až 12 měsíců** pro každého konkurenta: podíl zobrazení, míra
   překrytí, pozice nad, podíl absolutní první pozice. Nový řádek = nový hráč. Rostoucí
   překryv při rostoucím CPC = ten, kdo tlačí.
4. **Shopping zvlášť.** Jeden konkurent bývá dvě entity (např. „Temu CZ CSS“ a „Temu“),
   sčítej. CSS partneři a srovnávače jsou v aukci taky.
5. **Dopad na byznys.** CPC × CVR = CPA. Zdražení aukce o 20 % při stejném CVR = CPA +20 %.
   Porovnej s marží klienta, ne s pocitem.
6. **Kde ustoupit, kde držet.** Brand dotazy: držet, konkurent na brandu je drahý pro něj.
   Obecné dotazy s nízkou marží: nechat, nebo přesunout do long-tail a produktových kampaní.
   Nepauzuj brand Search jen podle PNO, které ukazuje systém (zkušenost z praxe).

## 3. Rozhodovací pravidla

- Konkurent přitlačil a my ztrácíme kvůli hodnocení: nejdřív relevance a stránka
  (`reklama-vs-stranka`), pak nabídka. Přeplácet jen tam, kde to marže unese.
- Ztrácíme kvůli rozpočtu a kampaň plní cíl: navýšit po krocích +15 až 30 %
  (`knowledge/rozpocty.md`).
- Nový hráč s dumpingovou cenou (Temu): neslevovat na CPC, přesunout na dotazy, kde
  rozhoduje důvěra a dostupnost, a posílit produktové texty.
- Nikdy nesuď aukci z jednoho měsíce. Minimum tři měsíce, ideálně YoY.

## 4. Výstup

Tabulka po měsících: konkurent | podíl zobrazení | překryv | pozice nad | náš podíl |
ztráta rozpočet | ztráta hodnocení | CPC. Pod ní: kdo přišel / odešel / tlačí, zda je
dražší CPC z aukce nebo z našich změn (ověřeno / domněnka), co s tím a kolik to může
stát nebo přinést.

## 5. Pasti

- Export z UI nemá název účtu, identita se bere z názvu souboru. U NDA klientů jen
  anonymizovaně.
- Podíl zobrazení konkurenta je z aukcí, kde jsme byli i my. Neříká nic o jeho celkovém
  objemu.
- Google Ads doporučení „zvyšte rozpočet“ v době, kdy ztrácíme kvůli hodnocení, je
  klik na špatnou páku.

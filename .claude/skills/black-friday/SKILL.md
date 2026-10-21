---
name: black-friday
description: >
  Průvodce plánem Black Friday a Vánoc: zeptá se na cíle, rozpočet, akci, loňskou sezónu a grafiku,
  vezme data z API nebo z exportů (Google Ads, Meta, Sklik, GA4), spočítá forecast listopadu a prosince,
  rozpadne ho po týdnech podle loňské sezóny a vyrobí plán v PDF (fáze, rozpočty, kreativy, co kdy dělat).
  Použij, když uživatel řekne „Black Friday", „plán na Black Friday", „plán na Vánoce", „sezóna",
  „forecast na Black Friday", „kolik dát na Black Friday", „připrav sezónu", „vánoční plán",
  „plán Q4 po týdnech", „domácí úkol z webináře". Jen čte. Navazuje na forecast, kryci-plan a bannery.
---

# Plán Black Friday a Vánoc

Výsledkem je **jedno PDF pro majitele nebo klienta**: kolik utratit a kolik čekat v listopadu
a prosinci, týden po týdnu, co v které fázi dělat a jaké kreativy kdy připravit.
Je to odhad z historie, ne slib. Vždy ho podávej jako pásmo.

Postup je rozhovor. Ptej se ve **dvou kolech**, ne po jedné otázce. Co uživatel neví, nech prázdné
a jeď dál, plán se dá spočítat i bez toho.

## 1. Kolo otázek: byznys

1. **Který klient / e-shop?** (slug do `plans/<klient>/`)
2. **Cíl:** PNO, ROAS, nebo obrat? Kolik? A jaká je **marže** (hranice, kde reklama začne prodělávat)?
3. **Rozpočet na listopad a prosinec:** je daný, nebo ho hledáme? Když je daný, zapiš ho.
4. **Akce:** jaká sleva / nabídka, od kdy do kdy (early access, Black Week, Cyber Monday)?
5. **Top produkty** na sezónu a **sklad**: hrozí, že něco dojde?
6. **Poslední den doručení do Vánoc** (výchozí 18. 12.).

## 2. Kolo otázek: loni a kreativy

1. **Jak loni sezóna běžela?** Co fungovalo, co ne, kdy to naběhlo, kdy došly rozpočty.
   (Čísla si vezmu z dat, tady jde o příběh, který v datech není.)
2. **Grafika:** má klient brand manuál? Kdo dělá bannery (grafik, AI, nikdo)? Do kterých systémů
   a formátů? Kolik variant chcete testovat?
3. **Systémy:** Google Ads, Sklik, Meta, další? Plánujete letos něco nového (nová země, ChatGPT Ads)?

## 3. Data

Ověř si, co je k dispozici, a řekni uživateli, z jakého období data máš. **Pro odhad sezóny je
potřeba loňský listopad a prosinec.** Bez nich plán použije obecný profil a musí to říct nahlas.

**A. Napojené API** (účty klienta v `clients/hlidac-ucty.json` s polem `"klient"`): nic dalšího,
skript si data stáhne sám.

**B. Bez API: ruční exporty.** Ať je uživatel uloží do `plans/<klient>/exporty/`. Období vždy
**od 1. 9. loňského roku do včera, po dnech**:

| Systém | Kde | Co nastavit |
|---|---|---|
| Google Ads | Kampaně → Přehledy (Reports) → nový přehled | Řádky: Den. Sloupce: Náklady, Hodnota konv., Konverze, Prokliky. Stáhnout CSV |
| Meta | Správce reklam → Reporty (nebo tabulka kampaní) | Rozpad: Den. Sloupce: Utracená částka, Nákupy, Hodnota konverze nákupů. Export CSV |
| Sklik | Statistiky → po dnech | Cena, Konverze, Hodnota konverzí, Prokliky. Export CSV |
| GA4 | Průzkumy → Volný formát | Dimenze: Datum. Metriky: Celkové výnosy, Transakce. Sdílet → Stáhnout CSV |

GA4 nemá útratu, ale ukáže **tvar sezóny celého e-shopu**. Hodí se hlavně tam, kde reklamní účty
loni neběžely nebo se mezitím změnily.

Převod do jednoho formátu (sečte kampaně po dnech, pozná české i anglické sloupce):

```bash
python3 scripts/plan/exporty.py --klient muj-eshop \
  --google plans/muj-eshop/exporty/google.csv --meta plans/muj-eshop/exporty/meta.csv \
  --ga4 plans/muj-eshop/exporty/ga4.csv
```

Výstup: `plans/<klient>/historie.csv` (reklamní systémy) a `plans/<klient>/ga4.csv`. Když skript
nenajde sloupec, napíše, který chybí. Ukaž uživateli, co přesně v exportu přidat, a pusť znovu.

**C. Nic z toho** (jen vyzkoušet): `--csv scripts/plan/ukazka-data.csv --klient ukazka`.

## 4. Zadání a výpočet

Odpovědi z rozhovoru zapiš do `plans/<klient>/bf-zadani.json` podle vzoru
`scripts/plan/bf-zadani.example.json` (co nevíš, nech `null`). Pak:

```bash
# API
python3 scripts/plan/bf_plan.py --klient muj-eshop --zadani plans/muj-eshop/bf-zadani.json
# exporty
python3 scripts/plan/bf_plan.py --klient muj-eshop --csv plans/muj-eshop/historie.csv \
  --ga4 plans/muj-eshop/ga4.csv --zadani plans/muj-eshop/bf-zadani.json
```

Výstup: `plans/<klient>/bf-plan-<rok>.md`, `.html` a `.pdf` (PDF přes Chrome nebo Edge bez okna;
když není, otevři `.html` a Tisk → Uložit jako PDF). Návratový kód 1 = plán je, ale bez loňské sezóny.

Jak to počítá:
- Měsíce = stejný výpočet jako skill `forecast` (loňský měsíc × meziroční trend, pásmo scénářů).
  Zadaný rozpočet posune odhad podle modelu klesajícího výnosu.
- Týdny = měsíc rozpadnutý podle loňských dnů. Do týdne po Cyber Monday se loňsko zarovná
  **na den Black Friday** (2025: 28. 11., 2026: 27. 11.), prosinec podle kalendáře (Vánoce mají pevné datum).
- Fáze: příprava → rozjezd → Black Week → Black Friday až Cyber Monday → vánoční nákupy →
  po posledním doručení → po Vánocích. Ke každé fázi úkoly, kreativy a rozpočet.

## 5. Jak výsledek podat

1. Nahoře jedna věta: „V listopadu při útratě X čekej obrat Y až Z, vrchol je týden Black Friday."
2. Tabulka týdnů. Zvýrazni týdny, kde odhad PNO přeleze cíl, a řekni proč (konec prosince, slabá
   historie…). Tam se nenavyšuje naslepo.
3. **Co udělat tento týden** (podle fáze, ve které jsme dnes), max. 3 body.
4. **Kalendář kreativ** z fází + odpovědi o grafice: kdy jaké bannery mít hotové. Rovnou nabídni
   skill `bannery` („udělám teď sadu na Black Week?").
5. Řekni, z čeho plán vychází (loňská sezóna z Ads / z GA4 / obecný profil) a co neví.
6. Ukaž cestu k PDF a nabídni ho otevřít.

## 6. Kalkulačka v Excelu (bez Pythonu, i pro šéfa)

`docs/plan-black-friday-kalkulacka.xlsx`: stejná logika po týdnech v tabulce. Na list „Data“ se vloží
denní útrata a obrat (součet systémů, od 1. 9. loni), na „Zadání“ data Black Friday, cíl PNO a marže.
List „Plán“ ukáže loňské týdny × trend a ve žlutém sloupci jde zkoušet navýšení: hned je vidět PNO týdne
a **marginální PNO** (jestli se přidaná koruna vyplatí). Funguje v Excelu, Numbers i Google Tabulkách.
Když uživatel chce „si to naplánovat sám“ nebo potřebuje tabulku pro klienta, nabídni ji.

## 7. Navazuje

- **Krycí plán po dnech** na listopad: `kryci_plan.py` s rozpočtem z plánu a akcí jako `--udalost`
  (skill `kryci-plan`). Pak každé ráno „jsme v plánu?".
- **Hlídače** na sezónu zpřísnit a pustit i o víkendu (skill `nasazeni`, hlídač akcí `hlidac-akci`).
- Rozpočty v účtech se podle plánu **nemění samy**. Změna jen po schválení člověkem.

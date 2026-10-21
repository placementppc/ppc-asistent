# Plán Black Friday a Vánoc s AI: tahák

Z webináře PLACEMENT.cz „Black Friday a Vánoce s AI“ (22. 10. 2026). Dva prompty: jeden pro
PPC asistenta (data přes API nebo exporty), druhý pro jakoukoli AI (Claude, ChatGPT, Gemini)
s přiloženými exporty. Výsledek: plán po týdnech, kdy přidat, kdy ubrat, jaké kreativy kdy.

## 1. Než začnete (10 minut)

Připravte si odpovědi. Co nevíte, napište „nevím“, plán se spočítá i tak.

- [ ] **Cíl:** PNO, ROAS, nebo obrat? Kolik?
- [ ] **Marže:** od jakého PNO reklama prodělává (hrubá marže v %). Cíl musí být **pod** marží.
- [ ] **Rozpočet** na listopad a prosinec (nebo „hledáme“).
- [ ] **Akce:** jaká sleva / nabídka, od kdy do kdy (early access, Black Week, Cyber Monday).
- [ ] **Top produkty** na sezónu a jestli hrozí, že dojdou.
- [ ] **Poslední den doručení** do Vánoc.
- [ ] **Grafika:** kdo dělá bannery, máte brand manuál, do kterých systémů a formátů.
- [ ] **Loni:** kdy sezóna naběhla, kdy došly rozpočty, co fungovalo a co ne.

## 2. Data

Období vždy **od 1. 9. loňského roku do včera, po dnech**. Bez loňského listopadu a prosince AI
nezná vaši sezónu a bude hádat.

| Systém | Kde | Sloupce |
|---|---|---|
| Google Ads | Přehledy → nový přehled, řádky: Den | Náklady, Hodnota konv., Konverze |
| Meta | Správce reklam → Reporty, rozpad: Den | Utracená částka, Nákupy, Hodnota konverze nákupů |
| Sklik | Statistiky → po dnech | Cena, Konverze, Hodnota konverzí |
| GA4 | Průzkumy → Volný formát, dimenze: Datum | Celkové výnosy, Transakce |

GA4 nemá útratu, ale ukáže tvar sezóny celého e-shopu. Hodí se, když reklamy loni běžely jinak.

## 3A. Prompt pro PPC asistenta

```text
Připrav plán na Black Friday a Vánoce 2026 pro [e-shop].

1. Nejdřív se mě zeptej ve dvou kolech: (a) cíl PNO a marže, rozpočet na listopad
   a prosinec, akce (sleva, od–do), top produkty a sklad, poslední den doručení;
   (b) jak loni běžela sezóna a kdo dělá grafiku, do kterých systémů a formátů.
2. Data vezmi přes API z Google Ads, Skliku a Mety od 1. 9. 2025 (nebo z exportů
   ve složce plans/[e-shop]/exporty). Napiš mi, z jakého období je máš a co chybí.
3. Spočítej forecast listopadu a prosince jako pásmo (konzervativně, realisticky,
   ambiciózně) a rozpadni ho po týdnech podle loňské sezóny zarovnané na Black Friday.
4. Označ týdny, kde PNO přeleze cíl, a kde se navýšení nevyplatí, protože
   marginální PNO je nad marží.
5. Ke každé fázi napiš, co udělat a jaké kreativy mít hotové a kdy.
6. Výstup ulož jako PDF pro majitele. V účtech nic neměň.
```

PPC asistent na to má skill `black-friday` (spustí se sám) a kalkulačku
`docs/plan-black-friday-kalkulacka.xlsx`.

## 3B. Prompt pro jakoukoli AI (Claude, ChatGPT, Gemini) s přiloženými exporty

Přiložte CSV exporty z kroku 2 a pošlete:

```text
Jsi PPC specialista e-shopu. V příloze jsou denní exporty z [Google Ads / Mety /
Skliku / GA4] od 1. 9. 2025 do včera. Připrav plán na Black Friday (27. 11. 2026)
a Vánoce 2026.

Postup:
1. Nejdřív mi napiš, jaké období a systémy v datech vidíš a co chybí. Nic si nedomýšlej.
2. Zeptej se mě najednou na: cíl PNO, marži, rozpočet na listopad a prosinec, akci
   (sleva, od–do), top produkty, poslední den doručení a kdo dělá grafiku.
3. Spočítej trend: posledních 8 celých týdnů letos proti stejným 8 týdnům loni
   (posun o 364 dní, ať sedí dny v týdnu). Útratu i obrat zvlášť.
4. Plán po týdnech od 2. 11. do 27. 12.: loňský týden (posunutý o 364 dní, tím se
   zarovná i Black Friday 28. 11. 2025 na 27. 11. 2026) × trend. Tabulka: týden,
   fáze, loni útrata, loni obrat, plán útrata, plán obrat, plán PNO.
5. U každého navýšení rozpočtu počítej s klesajícím výnosem (+10 % útraty ≈ +6 %
   obratu, pokud nemám lepší data) a ukaž marginální PNO = útrata navíc / obrat
   navíc. Kde je nad marží, napiš, že přidávat se nevyplatí.
6. Ke každé fázi (rozjezd, Black Week, Black Friday až Cyber Monday, vánoční nákupy,
   po posledním doručení, po Vánocích) napiš 2–3 úkoly a jaké kreativy kdy připravit.
7. Počítej v kódu / tabulce, ne odhadem. Na konci napiš, co plán neví (akce, sklad,
   ceny) a že obrat je atribuce reklamních systémů, ne tržba e-shopu.
```

## 4. Jak poznat, že AI nehalucinuje

- Řekla, **z jakého období** data má? Sedí s tím, co jste přiložili?
- **Součet týdnů** dává měsíc? Loňský týden Black Friday v tabulce sedí s tím, co vidíte v účtu?
- Žádná čísla, která v datech nejsou (vymyšlené konverzní poměry, „průměry trhu“).
- Trend pod 0,6× nebo nad 1,8× = účet se změnil. Zeptejte se proč a případně ho přepište ručně.

## 5. Navazující prompty

```text
Z plánu udělej kalendář kreativ: co musí být hotové do kdy, kolik variant hooků
a v jakých formátech pro Metu, Google a Sklik.
```

```text
Rozpadni listopad na dny (krycí plán) a každé ráno mi řekni, jestli jsme v plánu
a kolik dohnat nebo ubrat. Nic v účtech neměň bez mého schválení.
```

---
PLACEMENT.cz · vzdelavani.placement.cz

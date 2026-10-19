---
name: kryci-plan
description: >
  Denní krycí plán rozpočtu a obratu (Google Ads, Sklik, Meta): rozpadne měsíční rozpočet a cíl obratu
  na dny a systémy (dny v týdnu z historie, svátky ČR, akce jako Black Friday) a každý den porovná
  skutečnost s plánem — odchylka, prognóza konce měsíce, kolik denně dohnat nebo ubrat, semafor a návrh.
  Použij, když uživatel řekne „krycí plán", „denní plán", „rozpad rozpočtu na dny", „jsme v plánu?",
  „plníme plán?", „dohnat plán", „kolik denně utratit", „jak jsme na tom s plánem", „plán na listopad
  po dnech". Jen čte, změny rozpočtů jen po schválení. Načti spolu s forecast a tempo-rozpoctu.
---

# Krycí plán

Krycí plán je **denní plán, jak má měsíc vypadat**: kolik který den v kterém systému utratit a kolik
má přijít obratu a konverzí. Pak se každý den podíváme, jestli jsme v plánu, a včas dorovnáme —
ne až 28. v měsíci.

## 1. Na co se zeptat (jednou, všechno najednou)

1. **Měsíc** a **měsíční rozpočet** celkem (nebo po systémech).
2. **Cíl obratu** nebo **cíl PNO / ROAS** (u leadů počet konverzí nebo CPA).
3. **Akce v měsíci**: Black Friday, výprodej, Vánoce, doprava zdarma, výpadek skladu, dovolená firmy.
   Kdy a o kolik víc / míň než běžný den (odhad stačí, upřesní se z loňska).
4. **Podíl systémů**: dává ho klient (pak do `cile.mesicni_rozpocet` u každého účtu), nebo podle historie?

Rozpočty a cíle patří do `clients/hlidac-ucty.json` k účtům klienta (pole `cile.mesicni_rozpocet`,
`cile.mesicni_obrat`, `cile.typ` + `cile.hodnota`, `limity.max_navyseni_pct`) a do `hlidat` přidej
`"kryci-plan"` — pak plnění běží pro klienta i v denním cronu.

## 2. Sestavení plánu

```bash
python3 scripts/plan/kryci_plan.py --klient muj-eshop --mesic 2026-11 --rozpocet 90000 --obrat 600000 \
    --udalost 2026-11-27:+40% --udalost 2026-11-28..2026-11-30:+20%

# bez API — vyzkoušej na smyšlených datech
python3 scripts/plan/kryci_plan.py --klient ukazka --mesic 2026-10 --csv scripts/plan/ukazka-data.csv \
    --rozpocet 72000 --obrat 510000
```

Odkud cíle: `--rozpocet` / `--obrat` → `cile` v konfiguraci → realistický forecast (s varováním,
že částku musí někdo potvrdit). Mezi systémy: `cile.mesicni_rozpocet`, jinak podíl útraty za
8 týdnů. Obrat systému = jeho rozpočet × jeho návratnost (z forecastu na daný měsíc, jinak z 8 týdnů).
Konverze = obrat / průměrná objednávka (u leadů rozpočet / CPA).

Rozpad na dny:
- **Dny v týdnu**: index z posledních 16 celých týdnů — každý den proti průměru svého týdne,
  medián přes týdny. Útrata a obrat mají každý své váhy. Pod 8 týdnů rovné váhy + varování.
- **Svátky ČR** (13 dnů volna vč. Velkého pátku a Velikonočního pondělí, počítáno bez knihovny):
  koeficient z historie (svátek vs. stejný den v týdnu ±3 týdny, medián). Pod 3 svátky v historii
  1,0 — nehádáme. Vánoce (24.–26. 12.) do koeficientu nepočítá, ty patří do `--udalost`.
- **Události** `--udalost DATUM:+40%` nebo `OD..DO:-50%`: den si vezme větší díl na úkor ostatních.
  Měsíční součet se nemění, dny sedí na korunu.
- Plán bere historii jen do dne před začátkem měsíce (nevidí data z plánovaného měsíce).

Výstup: `plans/<klient>/kryci-plan-<YYYY-MM>.csv` (sloupce `datum, den, system, plan_naklady,
plan_obrat, plan_konverze, plan_pno, kum_plan_naklady, kum_plan_obrat, kum_plan_konverze, poznamka`),
`.xlsx` (když je nainstalované `openpyxl`) a `.md` souhrn. Návratový kód 0 / 1 (varování) / 2 (chyba).

## 3. Každý den: jsme v plánu?

```bash
python3 scripts/plan/plneni.py --klient muj-eshop            # k dnešku, data do včerejška
python3 scripts/plan/plneni.py                               # všichni klienti s "kryci-plan" v hlidat
python3 scripts/plan/plneni.py --klient ukazka --csv scripts/plan/ukazka-data.csv --datum 2026-10-19
```

Pro každý systém i celkem: kumulativ od 1. dne a včerejšek proti plánu, PNO proti cíli, prognóza
konce měsíce (skutečnost + zbytek plánu × tempo posledních 7 dnů proti plánu), kolik denně dohnat
nebo ubrat. Report `reports/kryci-plan/<datum>.md` (s `--klient` `<datum>-<klient>.md`), `--json`.
Návratový kód: 0 vše 🟢, 1 něco 🟡, 2 něco 🔴 nebo chybí plán / účet nešel načíst.

**Semafor:** 🟢 odchylka do ±10 %, 🟡 do ±25 %, 🔴 víc. Útrata se hodnotí oběma směry, obrat
a konverze jen dolů (nad plánem je vždy 🟢). První 4 dny měsíce nejvýš 🟡 — to je ještě šum.
Systém pod 10 % rozpočtu klienta nezčervená celého klienta.

## 4. Jak číst návrhy

| Situace | Návrh |
|---|---|
| Nedočerpává, PNO pod cílem | Zvednout denní rozpočty o X Kč, max `limity.max_navyseni_pct` (výchozí 20 %) za krok. Zbytek nedohánět najednou. |
| Nedočerpává, PNO nad cílem | **Nepřidávat.** Nedočerpaný rozpočet je lepší než drahé konverze. Nejdřív proč (`tempo-rozpoctu`, `anomalie`). |
| Přečerpává, PNO nad cílem | Ubrat denní rozpočty o X Kč. |
| Přečerpává, PNO drží | Domluvit s klientem vyšší měsíční rozpočet, nebo ubrat, ať měsíc vyjde. Rozhoduje klient. |
| Čerpá podle plánu, obrat zaostává | Rozpočet to nespraví. Hledat příčinu (`anomalie`, `konverze-vs-ga4`, `mereni-audit`). |

Poctivě k nejistotě:
- Konverze a obrat z posledních ~3 dnů ještě dobíhají (u Mety 24–72 h). Včerejší obrat pod plánem
  sám o sobě nic neznamená — rozhoduje kumulativ.
- Plán je jen tak dobrý jako vstupy. Když se v měsíci stane něco, co v plánu není (výpadek, akce
  navíc), plán přepočítej s `--udalost` a řekni to klientovi.
- Obrat je atribuce reklamních systémů, ne tržba e-shopu.
- Denní rozpočet v účtu ≠ skutečná útrata (Google smí v jednom dni utratit až 2× denní rozpočet).
  Než navrhneš konkrétní nastavení, podívej se na aktuální denní rozpočty kampaní v účtu.

## 5. Změny v účtu (jen po schválení)

Skripty plánu **nic nemění**. Postup u změny rozpočtu:
1. Návrh ukaž uživateli: systém, kampaň, z kolika na kolik Kč/den, proč (odchylka, PNO), krok max +15–30 %.
2. Po výslovném schválení:
   - **Google Ads**: plán JSON s `set_budget` (`budget_id`, `amount_micros`) ulož do
     `plans/<klient>/` (je v `.gitignore`, do kořene appky plány nepatří) → náhled
     `python3 scripts/google_ads/apply_changes.py <customer_id> plans/<klient>/rozpocet-YYYY-MM-DD.json` (dry-run) → po kontrole
     stejný příkaz s `--apply`.
   - **Sklik a Meta**: apka zatím nemá skript na změnu rozpočtů (`scripts/sklik/apply_search_changes.py`
     rozpočty záměrně odmítá). Změnu udělá člověk v administraci podle návrhu.
3. Zapiš baseline a datum změny do `clients/<klient>.md` (changelog `### YYYY-MM-DD`) — hlídač cílů
   pak vyhodnocuje od této změny. Po změně nech 7–14 dní doběhnout, nehoupej rozpočtem denně.

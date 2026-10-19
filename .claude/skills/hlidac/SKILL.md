---
name: hlidac
description: Denní hlídač reklamních účtů (Sklik, Meta, Google Ads) — ráno projde vybrané účty, porovná včerejšek s běžným dnem a nahlásí jen ty, které svítí (stojí, utíkají, propad zobrazení, skok CPC, nula konverzí, zamítnuté reklamy, zablokovaný účet). Večer pohlídá, jestli dnešek neutíká. Rozcestník i pro hlídač cílů a hlídač akcí a pro konfiguraci clients/hlidac-ucty.json (které účty, frekvence, cíle, limity). Použij, když uživatel řekne „hlídač", „pohlídej účty", „ranní kontrola účtů", „projdi účty jestli něco nehoří", „pohlídej to přes víkend", „nastav denní hlídání", „přidej účet do hlídače", „jak často hlídat", nebo když ho spustí naplánovaná úloha. Jen čte, nic nemění.
---

# Hlídač účtů

Tři hlídače nad jednou konfigurací `clients/hlidac-ucty.json`. Všechny **jen čtou**.

| Hlídač | Otázka | Příkaz | Skill |
|---|---|---|---|
| výkyvy | Stalo se včera / dnes něco náhlého? | `python3 scripts/hlidac/hlidac.py` · `--dnes` | tenhle |
| cíle | Plní účet od poslední změny cíl klienta? | `python3 scripts/hlidac/cile.py` | `hlidac-cilu` |
| akce | Kde je prostor přidat (i v pátek večer)? | `python3 scripts/hlidac/akce.py` · `--vikend` · `--dnes` | `hlidac-akci` |

Hlídač výkyvů hledá **náhlé výkyvy** proti běžnému dni (medián posledních 28 dní). Neříká,
jestli účet „funguje" — z jednoho dne se to poznat nedá (CLAUDE.md 4b). Řekne jen „tady se
včera něco stalo, podívej se".

**V účtech nic nemění.** Ani když je nález jasný. Navrhne, schválí člověk (CLAUDE.md #1).

## 1. Konfigurace `clients/hlidac-ucty.json`

Vzor s vysvětlením každého pole: `scripts/hlidac/ucty.example.json` (klíč `_navod`).
Když soubor chybí, zeptej se uživatele, které účty hlídat a s jakým cílem, a založ ho podle vzoru.
Validaci a české chybové hlášky řeší `scripts/hlidac/config.py` — chybu ukaž uživateli tak, jak je.

```json
{
  "planovani": {"frekvence": "denne", "casy": ["07:30", "19:00"],
                "akce_casy": ["fri 18:00", "sat 10:00", "sun 10:00"], "timezone": "Europe/Prague"},
  "notifikace": {"kanal": "zadny"},
  "ucty": [{
    "nazev": "Můj e-shop", "klient": "muj-eshop", "system": "google", "id": "123-456-7890",
    "min_utrata": 100,
    "hlidat": ["vykyvy", "cile", "akce", "kryci-plan"],
    "cile": {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 30000, "mesicni_obrat": 200000},
    "limity": {"max_denni_rozpocet": 1500, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30},
    "posledni_zmena": "2026-10-01"
  }]
}
```

- `hlidat` určuje, které hlídače účet projdou. Účet bez `vykyvy` hlídač výkyvů přeskočí.
  Když pole chybí (starý formát `{"ucty": [...]}`), hlídají všechny, které mají data —
  cíle a akce jen u účtů s blokem `cile`.
- `cile.typ`: `pno` (v %), `roas` (násobek, 6 = 600 %), `cpa` (Kč), `konverze` (počet za měsíc).
  Cíl ber z `clients/<klient>.md` sekce 2 — ať jsou oba zdroje stejné.
- `limity` hlídá jen hlídač akcí: max krok, týdenní strop a strop součtu denních rozpočtů účtu.
- `posledni_zmena` je volitelná; jinak se bere z changelogu klienta (`### RRRR-MM-DD`).
- `planovani.frekvence`: `denne | pracovni-dny | tydne | vlastni`. Plánovač si časy sám nečte —
  nastavují se ve zvolené variantě nasazení (sekce 4). `cile.py --podle-planu` v ostatní dny
  jen skončí s kódem 0.
- `notifikace.kanal`: kam reporty posílat — napojení řeší `docs/notifikace.md`.

## 2. Hlídač výkyvů — spuštění

```
python3 scripts/hlidac/hlidac.py          # ráno: vyhodnotí včerejšek
python3 scripts/hlidac/hlidac.py --dnes   # večer: utíká dnešek, nebo stojí?
```

- Report se uloží do `reports/hlidac/<datum>.md` (večer `<datum>-vecer.md`).
- Návratový kód: 0 vše v pořádku · 1 něco žluté · 2 něco červené nebo účet nešel načíst.
- Sklik se večer nekontroluje: není ověřené, jak rychle Sklik plní dnešní statistiky.

## 3. Co hlídá (prahy v `scripts/hlidac/kontroly.py`)

| Nález | Úroveň | Kdy |
|---|---|---|
| Útrata stojí | 🔴 | včera pod 20 % běžného dne |
| Útrata utíká | 🔴 | včera přes 160 % běžného dne |
| Nula konverzí | 🔴 | běžně aspoň 2 denně, včera 0 |
| Účet nejde načíst / zablokovaný | 🔴 | chyba API, Meta `account_status` ≠ 1 |
| Propad zobrazení | 🟡 | pod 50 % běžného dne (když útrata nesvítí) |
| Skok CPC | 🟡 | o 40 % dráž, jen při 20+ proklicích |
| Propad konverzí | 🟡 | pod 40 % běžného dne, jen u účtů s 5+ denně |
| Zamítnuté reklamy | 🟡 | Meta `DISAPPROVED`, Google aktivní reklamy `DISAPPROVED` |
| Večer: utíká dnešek | 🔴 | dnes už víc než 130 % běžného celého dne |
| Večer: dnešek stojí | 🟡 | po 18:00 pod 20 % běžného dne |

Prahy jsou záměrně volné. Hlídač, který píská každý den, přestane někdo číst.

## 4. Co udělat s nálezem

1. **Účty v pořádku nerozebírej.** Stačí jedna věta.
2. **Každý 🔴 nález projdi postupem skillu `anomalie`** (měření → změny v účtu → web a nabídka →
   trh a sezóna → aukce), jen čtecími skripty. U „utíká" se nejdřív podívej na historii změn
   (Google `change_event`, Meta activity log), u „stojí" na platbu/kredit, zamítnutí a stav kampaní.
3. **Příčinu piš jen ověřenou.** Co nevíš, označ jako domněnku (CLAUDE.md tvrdé pravidlo 1).
4. **Report stručně:** nahoře „🔴 X účtů svítí / ✅ vše v pořádku", pod tím ke každému svítícímu
   účtu 1–2 věty: co se stalo, ověřená příčina, návrh kroku. Detail jen do `clients/<klient>.md`.
5. **Návrh změny jen jako návrh.** Nic nespouštěj. Klientský soubor doplň jen o datum a nález.
6. Ráno se hodí pustit i hlídač cílů (skill `hlidac-cilu`): výkyvy říkají „co se stalo včera",
   cíle „jestli to od poslední změny jde správným směrem".

## 5. Naplánování (ráno, večer, pátek večer, víkend)

Jak hlídače pustit samy (aplikace Claude, cloudová rutina, GitHub Actions, Vercel Cron, launchd),
co kdy pouštět a jak posílat reporty: **`docs/nasazeni.md` a skill `nasazeni`**. Tady jen rytmus:

| Kdy | Co |
|---|---|
| ráno (`planovani.casy[0]`) | `hlidac.py` + `cile.py` (+ krycí plán u účtů s `kryci-plan`) |
| večer (`planovani.casy[1]`) | `hlidac.py --dnes` |
| pátek večer | `akce.py --vikend` (opatrnější kroky + rizika přečerpání do pondělí) |
| sobota, neděle | `akce.py --vikend` |

Frekvenci (`denne`, `pracovni-dny`, `tydne`) si ulož do `planovani`, ať je na jednom místě.
Pro běh se zavřeným počítačem jen u Google Ads existuje i Google Ads skript
`scripts/google_ads_scripts/ucet_hlidac.js` (běží u Googlu).

---
name: nasazeni
description: Průvodce nasazením hlídačů, aby běžely samy v cronu — vybere variantu (naplánovaná úloha v aplikaci Claude, cloudová rutina Claude Code, GitHub Actions, Vercel Cron, launchd) podle toho, co uživatel má a chce, a provede nastavením krok za krokem. Použij, když uživatel řekne „nasadit", „nasaď hlídač", „cron", „Vercel", „ať to běží samo", „nechat to na agentovi", „agent", „GitHub Actions", „naplánovat hlídač", „spouštět každé ráno", „běh se zavřeným notebookem", „routine", „/schedule". Klíče nikdy nevypisuje, v účtech nic nemění.
---

# Nasazení hlídačů

Cíl: hlídače (`deploy/spust.py` → `scripts/hlidac/*`, `scripts/plan/plneni.py`) běží samy
ve správný čas. Podklady: `docs/nasazeni.md` (srovnání, ověřená fakta, odkazy),
šablony v `deploy/`, notifikace `docs/notifikace.md`.

## Pravidla

- **Klíče nikdy nečti ani nevypisuj** — ani zkrácené. `.env` blokuje hook. Hodnoty do Secrets /
  Environment Variables kopíruje uživatel sám, ty mu řekneš jen **názvy**.
- **Nic nezakládej za uživatele** na GitHubu, Vercelu ani v claude.ai, dokud to výslovně
  neodsouhlasí. Push, deploy, vytvoření rutiny = vždy napřed se zeptat.
- **Jeden krok, počkat na „hotovo".** Ruční kroky v prohlížeči dávej po jednom.
- Hlídače jen čtou. Do promptu rutin vždy patří „nic neměň, nic s --apply / --confirm".
- Fakta o službách ber z `docs/nasazeni.md`. Když uživatel chce něco, co tam není ověřené,
  ověř v oficiální dokumentaci (Context7 / web) a řekni, odkud to máš.

## 1. Zeptej se (najednou, krátce)

1. Je tvůj počítač ráno a večer zapnutý a nespí? Nebo to má běžet i se zavřeným notebookem?
2. Chceš, aby nálezy rovnou prošel Claude (analýza příčin), nebo stačí report z hlídače?
3. Máš účet na GitHubu? A Vercel (který tarif)?
4. Máš klienty pod NDA? (ti nepatří do cloudu bez souhlasu — `docs/nda-rezim.md`)

Než budeš pokračovat, ověř, že hlídač vůbec běží lokálně:
`python3 deploy/spust.py --rezim rano`. Když chybí `clients/hlidac-ucty.json`, založ ho
nejdřív (skill `hlidac`). Když hlásí chybějící přístupy, ať je uživatel doplní do `.env`
podle `.env.example`.

## 2. Doporuč jednu variantu

| Situace | Varianta |
|---|---|
| počítač běží, chce analýzu Claudem, začátečník | **A. Úloha v aplikaci Claude** |
| běh i se zavřeným notebookem + analýza Claudem, žádné NDA klíče | **B. Cloudová rutina** |
| běh vždy, stačí report, zdarma | **C. GitHub Actions** |
| už má appku na Vercelu s tarifem Pro | **D. Vercel Cron** |
| chce jen skripty na Macu bez aplikace | **E. launchd** |

Řekni proč jednou větou a jedno hlavní omezení (z tabulky v `docs/nasazeni.md`).
Vercel Hobby nedoporučuj pro klientské účty: je jen pro nekomerční použití a cron 1× denně ±59 min.

## 3. Proveď nastavení (po jednom kroku)

### A. Úloha v aplikaci Claude
1. Ať otevře aplikaci Claude → Code → Routines → New routine → **Local**.
2. Prompt z `deploy/claude-routine/prompt.md` (REŽIM `rano`), složka = tahle appka,
   plán Daily 7:30. Pak stejně `vecer` 19:05, `akce` pátek 18:05, `vikend` so+ne 10:05
   (vlastní plán zadá Claudovi slovy).
   Úlohu umíš založit i sám, když máš nástroj na plánované úlohy — ale jen po souhlasu.
3. **Run now** u ranní úlohy, povolit nástroje („always allow").
4. Doporuč „Keep computer awake" (Settings → This computer → System).

### B. Cloudová rutina
1. **Nové privátní repo** na GitHubu (ne fork) s appkou (bez `.env`). Push jen po souhlasu.
2. Cloudové prostředí jen pro sebe: síť **Custom** s `api.sklik.cz`, `graph.facebook.com`
   + výchozí seznam; proměnné: `HLIDAC_UCTY_JSON` (konfigurace na jeden řádek) a přístupy
   se stejnými názvy jako v `.env.example`; setup script `pip install -r requirements.txt`.
   Upozorni: proměnné vidí každý, kdo prostředí používá; network secrets naše skripty
   neumí využít (`docs/nasazeni.md`, B).
3. Rutina: `/schedule` nebo claude.ai/code/routines → Cloud, prompt z
   `deploy/claude-routine/prompt.md`, repo, prostředí, plán. Odebrat nepotřebné konektory.
4. Run now → otevřít běh a přečíst, co Claude udělal (zelený stav ≠ úspěch hlídače).

### C. GitHub Actions
Postup v `deploy/github-actions/README.md`. Klíčové body: **nové privátní repo (ne fork)**, kopie
`hlidac.yml` do `.github/workflows/`, Secrets (`HLIDAC_UCTY_JSON` + přístupy), ruční
spuštění Run workflow → režim `rano`, kontrola Artifacts.

### D. Vercel Cron
Postup v `deploy/vercel/README.md`: `priprav.sh` → `vercel link` → `vercel env add …`
(uživatel zadává hodnoty sám) → `vercel deploy --prod` (jen po souhlasu) →
`vercel crons run /api/hlidac`. Nejdřív zmiň neověřený zapisovatelný `/tmp`.

### E. launchd
Postup v `deploy/launchd/README.md`. Cestu `CESTA_K_APPCE` v plistu doplň za uživatele
(jen do jeho `~/Library/LaunchAgents/`, ne do šablony).

## 4. Ověř první běh

- Exit 0/1/2 a report v `reports/` (nebo v Artifacts / logu Vercelu / relaci rutiny).
- „Účet nejde načíst" u všech účtů = chybí nebo nesedí přístup → ať zkontroluje název secretu.
- Napiš stav: kde to běží, kdy příště, co není ověřené (např. víkendový běh ještě neproběhl).

## 5. Notifikace (volitelné)

Zeptej se, kam chce výsledky. Pak `docs/notifikace.md`: řekni mu, co založit a jaké
**názvy** proměnných doplnit. Napojení dopiš až po jeho „hotovo" a pošli jednu testovací zprávu.

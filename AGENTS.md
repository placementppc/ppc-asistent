# PPC asistent — instrukce pro AI agenta

> **Tenhle soubor je jen rozcestník. Skutečná pravidla jsou jinde a musíš si je přečíst.**
> Agent, který hlavní instrukce nenajde, si začne vymýšlet vlastní postup (třeba klikat
> kampaně v prohlížeči, přestože projekt má API skript). Proto nejdřív čti.

## Než uděláš cokoli jiného

Přečti si v tomhle pořadí, celé:

1. **`CLAUDE.md`** — tvrdá pravidla, přístupy, rozcestník skillů.
2. **`.claude/skills/ppc-fachman/SKILL.md`** — mozek projektu. Workflow a neporušitelná
   pravidla pro Google Ads, Sklik i Metu. **Bez tohohle souboru nezačínej pracovat.**
3. **`clients/<klient>.md`** — všechno o klientovi, se kterým pracuješ. Zdroj pravdy.
4. Podle úkolu pak jeden z:
   - `.claude/skills/perf_meta/SKILL.md` + `knowledge/meta-ads.md` — Meta Ads
   - `.claude/skills/perf_srch/`, `.claude/skills/perf_shop/`, `.claude/skills/perf_disp/` — výkon podle kanálu
   - `knowledge/tvorba-kampani/` — zakládání nových kampaní a reklam
   - `knowledge/api-limity-bezpecnost.md` — limity API (závazné)
   - `.claude/skills/start/SKILL.md` — první nastavení (když chybí `.env` nebo `clients/hlidac-ucty.json`)

> **Codex a podobné nástroje bez mechanismu skillů:** `.claude/skills/` jsou obyčejné
> markdown soubory, čti je jako text. Žádná `.agents/` ani `.Codex/` kopie neexistuje
> a nezakládej ji — dvě kopie pravidel se rozejdou.

## Pět věcí, které platí vždy

1. **Nikdy neprováděj změny v účtu bez schválení uživatele.** Zápisové skripty nejdřív bez
   `--apply` / `--confirm` (dry-run) a aplikuj jen schválený plán.
2. **Ověřuj, nehádej.** Každé tvrzení je buď doložené (odpověď API, dokumentace), nebo
   výslovně označené jako domněnka. U API napřed dokumentace, pak pokusy.
3. **Používej skripty z `scripts/` a `chatgpt-ads/run.sh`, ne prohlížeč.** Prohlížeč jen tehdy,
   když si ho uživatel výslovně vyžádá.
4. **Nesuď účet z krátkého okna.** Žádný závěr o rozpočtu, měřítku ani věta „účet nefunguje"
   ze 7denního nebo 30denního součtu. Povinné jsou tři řezy: detail ~30 dní, **8 týdnů po
   týdnech** a **měsíční řada za celou historii účtu**.
5. **Soubory s klíči nečti.** `.env`, `chatgpt-ads/.env`, `banner-generator/.env.local`,
   `google-ads.yaml`. Skripty si klíče načtou samy. NDA klienti: `docs/nda-rezim.md`.

## Kde co je

| Cesta | Co tam je |
|---|---|
| `.claude/skills/ppc-fachman/SKILL.md` | **mozek** — workflow a pravidla |
| `.claude/skills/` | všechny skilly (rozcestník v `CLAUDE.md`) |
| `knowledge/` | metodika PPC + `_learnings.md` (napříč-klientské vzorce) |
| `clients/<klient>.md` | vše o klientovi, šablona `clients/_TEMPLATE.md` |
| `clients/hlidac-ucty.json` | konfigurace hlídačů (vzor `scripts/hlidac/ucty.example.json`) |
| `scripts/google_ads/` | Google Ads API — `fetch.py` (čte), `apply_changes.py` (zapisuje s `--apply`) |
| `scripts/meta/` | Meta API — `preflight.py`, `fetch.py`, `apply.py` |
| `scripts/sklik/` | Sklik API |
| `scripts/ga4/` | GA4 — `fetch.py` (jen čte) |
| `scripts/hlidac/`, `scripts/plan/` | hlídače, forecast, krycí plán |
| `chatgpt-ads/` | ChatGPT Ads CLI (`run.sh`), vlastní soubor s klíčem `chatgpt-ads/.env` |
| `banner-generator/` | AI bannery, klíče v `banner-generator/.env.local` |
| `docs/` | napojení systémů, bezpečnost, NDA, nasazení, notifikace |

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # vyplní člověk, ne agent
```

Skripty pouštěj přes `.venv/bin/python`. Celé nastavení krok za krokem: skill `start`.

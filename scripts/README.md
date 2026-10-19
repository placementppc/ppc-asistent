# Skripty — API konektory

> **Read-only** (default): `fetch.py` (Google Ads), `sklik/fetch.py` — jen čtou.
> **Write** (jen po schválení): `apply_changes.py` (dry-run, reálně až `--apply`),
> `update_listing_bids.py` (CPC bidy listing groups u Shopping/PLA),
> `update_conversion_goal.py` (primary/sekundární konverzní akce),
> `setup_conversions.py`, `apply_assets.py`, `add_search_themes.py` (hledaná témata do PMax,
> odmítne téma blokované negativem kampaně) — zapisují do účtu. NIKDY je nespouštěj
> bez explicitního schválení uživatele a bez dry-run náhledu. Viz pravidla skillu
> a `knowledge/api-limity-bezpecnost.md`.

## Setup (jednorázově)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # a vyplň přístupy
```

## Google Ads
```bash
# Seznam účtů pod MCC:
python scripts/google_ads/fetch.py --list-clients

# Předdefinované reporty (customer ID s/bez pomlček):
python scripts/google_ads/fetch.py 123-456-7890 campaigns --days 30
python scripts/google_ads/fetch.py 0000000000 search_terms --days 30
python scripts/google_ads/fetch.py 0000000000 ads
python scripts/google_ads/fetch.py 0000000000 pmax_channels

# Vlastní GAQL:
python scripts/google_ads/fetch.py 0000000000 --gaql "SELECT campaign.name FROM campaign"
```
Dostupné reporty: `campaigns, budgets, ad_groups, keywords, search_terms, ads, pmax_channels, shopping`.

```bash
# Keyword research (Keyword Planner) — read-only, vrací i sezónnost po měsících:
python scripts/google_ads/keyword_ideas.py 0000000000 --seeds "běžecké boty" --limit 2000
python scripts/google_ads/keyword_ideas.py 0000000000 --historical "běžecké boty na asfalt" "jak vybrat běžecké boty"
python scripts/google_ads/keyword_ideas.py 0000000000 --url https://www.example.cz/bezecke-boty
```
Jazyk (`--lang cs`) a zemi (`--geo CZ`) si dohledá přes API, nehádá ID. `KeywordPlanIdeaService`
v účtu nic nevytváří. Hledanost je zaokrouhlená do pásem; **0 = pod hranicí vykazování (~<10/měs.),
ne „nikdo nehledá"**.

### Google Ads skripty (běží v účtu klienta, ne tady)
`google_ads_scripts/pmax_hlidac.js` — denní hlídač kanálů PMax do Google Sheetu (Přehled s grafy,
Týdně, Denně, Změny, Historie upozornění) + volitelný pondělní e-mail. Vkládá se v Google Ads:
Nástroje → Hromadné akce → Skripty, frekvence Denně. Jen čte. Nastavení v bloku `CONFIG`
(break-even a cílový ROAS klienta, URL sheetu, e-mail).

## Meta Ads (Facebook/Instagram)
Vyžaduje `META_API_TOKEN` v `.env` — system-user token s `ads_management`
(čtení i zápis). Volitelně `META_API_VERSION` (default v21.0).
```bash
python scripts/meta/fetch.py accounts                                   # seznam ad účtů
python scripts/meta/fetch.py campaigns act_000000000000000             # kampaně
python scripts/meta/fetch.py adsets    act_000000000000000             # ad sety (vč. targeting)
python scripts/meta/fetch.py ads       act_000000000000000             # inzeráty + kreativy
python scripts/meta/fetch.py insights  <act_/campaign/adset/ad id> --level adset --preset maximum
python scripts/meta/fetch.py insights  <id> --level campaign --days 30
# vlastní GET:
python scripts/meta/fetch.py --get "act_.../campaigns" --fields "name,status" --params "limit=50"
```
`fetch.py` jen čte. Stránkuje, na rate-limit (kód 4/17/32/613 / HTTP 429) dělá backoff. Metodika: `knowledge/meta-ads.md`.

```bash
# PŘED stavbou kampaně v novém účtu — projde všechny předpoklady najednou (read-only):
python scripts/meta/preflight.py 0000000000 --catalog 0000000000 --page 0000000000
```
`preflight.py` ověří token/scopes, ad účet, katalog a jeho business, product sety, zdraví feedu
a pixely. Co z API ověřit NEJDE (režim aplikace, právo Ads na stránce, IG přístup) vypíše jako
seznam s chybovými subkódy — ty se projeví až při zápisu, proto **zkoušej tvorbu kreativy jako
PRVNÍ krok stavby, ne poslední**. Viz `knowledge/meta-ads.md` § 15.

```bash
# Schválená dávková změna (kampaně/ad sety/reklamy) — defaultně jen dry-run:
python scripts/meta/apply.py clients/plan.json
python scripts/meta/apply.py clients/plan.json --apply   # zápis jen po schválení
```
`apply.py` vyžaduje v plánu `approval.status=approved`, zapisuje sériově s backoffem.

## OpenAI Ads (ChatGPT Ads)

ChatGPT Ads obsluhuje samostatné CLI ve složce `chatgpt-ads/` (`chatgpt-ads/run.sh`, návod
v `chatgpt-ads/README.md`, skill `/chatgpt-ads`). Klíč patří do `chatgpt-ads/.env` podle
`chatgpt-ads/.env.example` (Ads Manager → Settings → API keys, jeden klíč na jeden účet).

```bash
chatgpt-ads/run.sh account                      # info o ad účtu
chatgpt-ads/run.sh campaigns --json             # kampaně
chatgpt-ads/run.sh insights --days 7 --json     # výkon
```

Zápisy jsou defaultně dry-run, reálně až s `--confirm` a jen po schválení.

## GA4 (Google Analytics) — READ-ONLY
Používá stejné OAuth přístupy jako Google Ads; refresh token musí mít i scope
`analytics.readonly` (vygeneruj: `generate_refresh_token.py --write-env`).
```bash
python scripts/ga4/fetch.py properties                     # seznam GA4 properties
python scripts/ga4/fetch.py items <PROPERTY_ID> --days 90  # prodeje po položkách
python scripts/ga4/fetch.py daily <PROPERTY_ID> --days 45  # denní tržby/transakce
python scripts/ga4/fetch.py report <PROPERTY_ID> --dimensions itemCategory,itemName \
    --metrics itemRevenue,itemsPurchased --days 90          # vlastní report
```
Jen čte (runReport). Property ID klientů patří do `clients/<klient>.md`.

## Sklik
```bash
python scripts/sklik/fetch.py --user-id <KLIENT_ID> campaigns
python scripts/sklik/fetch.py --user-id <KLIENT_ID> --call campaigns.list
python scripts/sklik/fetch.py --user-id <KLIENT_ID> --call stats.campaigns --params '[{...}]'

# Schválená dávková změna CPC productSetů — defaultně jen dry-run/check:
python scripts/sklik/update_product_set_bids.py clients/plan.json
# Reálný zápis pouze po schválení a čistém dry-runu:
python scripts/sklik/update_product_set_bids.py clients/plan.json --apply

# Hromadná sestavová negativa + snížení CPC KW + pauza kampaní (dry-run = *.check):
python scripts/sklik/apply_negatives_bids.py clients/plan.json [--apply]
```

Google Ads: sdílené seznamy vylučujících slov + CPC klíčových slov jednou atomickou dávkou
(dry-run = `validate_only`): `python scripts/google_ads/apply_negative_lists.py clients/plan.json [--apply]`.
Názvy metod ověř dle aktuální dokumentace https://api.sklik.cz/ (API se vyvíjí).

## 🔒 NDA klienti — dva režimy
Každý NDA klient má v `.md` pole `NDA režim:` (`anonymizace` | `plna-data`) a `NDA účty:`.
Kontrolu dělá `scripts/lib/nda.py` — napojená je v `normalize_cid` (každý Google Ads skript),
ve Sklik klientovi, v `meta/fetch.py` + `meta/apply.py` a v `ga4/fetch.py`. Výpisy účtů
(`--list-clients`, Meta `accounts`, GA4 `properties`) skryjí NDA účty. Uvnitř Claude Code:

| režim | aplikace Claude (Max) | NDA relace `./nda.sh` |
|---|---|---|
| anonymizace | jen `fetch_safe.py` / `sklik/fetch.py --anon`, zápisy přes ID | stejné |
| plna-data | ⛔ vše zastaveno | ✅ vše |
| režim nezvolen | ⛔ vše zastaveno | ✅ jen zápisy |

Stav: `CLAUDECODE=1 .venv/bin/python scripts/lib/nda.py`. Testy: `.venv/bin/python -m unittest tests/test_nda.py`.
Nastavení NDA relace (API klíč v Klíčence): `docs/nda-rezim.md`.

### Režim anonymizace
Vrstva `sanitize.py` se vsadí mezi stažení a analýzu:

```bash
# Jeden krok (stáhne standardní sadu + anonymizuje + uloží):
python scripts/google_ads/fetch_safe.py 123-456-7890 --client acme --days 30
#  → clients/acme-data-<datum>.json   (anonymní — TADY analyzuj)
#  → clients/.secret/acme-raw-*.json  (syrové — gitignored, NEČTI)
#  → clients/.secret/acme-map.json    (mapa token→realita, gitignored)

# Sklik — anonymizace rovnou ve skriptu (syrové čtení NDA účtu se zablokuje):
python scripts/sklik/fetch.py --user-id <ID> campaigns --anon acme > clients/acme-data.json

# Zpětný překlad tokenů na realitu (kontrola, který token je která kampaň).
# V relaci Claude pod spotřebitelskými podmínkami jen do souboru v tajné složce, nikdy na výstup:
python scripts/sanitize.py --client acme --reverse --in plan.json --out clients/.secret/acme-reverse.json
```

Co dělá: **maže** název účtu / customer ID / URL / search terms / texty reklam,
**vynechává celé brandové kampaně** (název obsahuje „brand"), **pseudonymizuje**
názvy kampaní/sestav (stabilní token napříč běhy), **zachovává** metriky, číselná
ID a klíčová slova. `apply_changes.py` adresuje přes číselná ID (ta zůstávají), takže
zápis schválených změn funguje i nad anonymizovanými daty. Detaily v hlavičce `sanitize.py`.

## ⚠️ Limity API (čti před spuštěním)
- **Nespouštěj víc skriptů paralelně** proti API. Jedeme sériově.
- Google Ads: Basic token = 15 000 operací/den, Explorer = 2 880/den (produkce). Read přes
  `search_stream` = 1 operace bez ohledu na objem. Na `RESOURCE_TEMPORARILY_EXHAUSTED` → backoff.
- Sklik: nejdřív `api.limits` (minuteRequestLimit / dayRequestLimit / batchCallLimits). Na `429` → backoff.
- Write (`apply_changes.py`, `setup_*.py`): nejdřív DRY-RUN, reálně až `--apply`, jen po schválení,
  v malých dávkách. Plný přehled: `knowledge/api-limity-bezpecnost.md`.

## Poznámky
- Výstup je JSON na stdout → snadno se analyzuje.
- `cost_micros` v Google Ads je v mikro-jednotkách měny (vyděl 1 000 000).
- Customer ID klientů patří do `clients/<klient>.md`, ne do `.env`.
- Write operace mají samostatné skripty s explicitním potvrzením (`--apply`) a smí se
  spustit až po schválení návrhu uživatelem.

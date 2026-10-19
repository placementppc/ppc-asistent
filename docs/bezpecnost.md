# Bezpečnost PPC asistenta

> Klíče k reklamním účtům jsou hesla k místům, kde tečou peníze. Tahle stránka shrnuje,
> jak je appka chrání, co musíš udělat ty a co dělat, když klíč unikne.
> NDA klienti mají vlastní stránku: `docs/nda-rezim.md`.

## 1. Kde jsou klíče

| Soubor | Co v něm je | Kdo ho zakládá |
|---|---|---|
| `.env` | Google Ads, GA4, Sklik, Meta | ty: `cp .env.example .env` |
| `chatgpt-ads/.env` | ChatGPT Ads (`OPENAI_ADS_API_KEY…`) | `chatgpt-ads/setup.sh` |
| `banner-generator/.env.local` | Gemini, OpenAI (bannery) | ty: `cp banner-generator/.env.example banner-generator/.env.local` |
| Klíčenka macOS | Anthropic API klíč pro NDA relaci | ty: `security add-generic-password …` (viz `docs/nda-rezim.md`) |

ID účtů klientů do souborů s klíči nepatří. Jsou v `clients/<klient>.md` a skriptům se
předávají jako argument.

## 2. Jak appka brání tomu, aby Claude klíče viděl

1. **`permissions.deny`** v `.claude/settings.json` zakazuje číst `.env`, `.env.*`, `*.env`
   a `google-ads.yaml` (výjimka `.env.example`). Pokrývá nástroj Read i `cat` / `head` / `sed`.
2. **Hook** `.claude/hooks/nda_guard.py` → `env_guard.py` před každým nástrojem zkontroluje
   cestu nebo text příkazu a zastaví i okliky (`source .env`, `python -c "open('.env')"`,
   `printenv`, `os.environ`). Cena: Claude neumí `.env` ani založit, to děláš ty.
3. **Pro všechny projekty na počítači** to zapne jednou:
   ```bash
   python3 scripts/setup_env_guard.py            # --dry-run ukáže, co by změnil
   ```
   Zapíše pravidla a hook do `~/.claude/settings.json` (platí v CLI i v aplikaci Claude).
   Cloudové relace vidí jen nastavení uvnitř repa.
4. **Skripty si klíče načítají samy** a do výstupu je nevypisují. To je záměr: Claude vidí
   data z účtu, ne přístup k němu.

Známý limit: skript, který si soubor otevře sám, hook nezastaví. Úplné zamčení pro všechny
procesy by vyžadovalo sandbox Claude Code.

## 3. Co musíš udělat ty

- [ ] **Klíče nikdy do chatu**, e-mailu, Slacku ani sdíleného dokumentu. Co jednou pošleš
      do chatu, odešlo na servery poskytovatele.
- [ ] **2FA** na Google účtu (MCC), Seznam účtu, Facebooku a Business Manageru, OpenAI účtu.
- [ ] **Minimální oprávnění**: Meta systémový uživatel jen `ads_read`, dokud nepotřebuješ zápisy;
      GA4 role Viewer; ChatGPT Ads pojmenovaný klíč pro každý účet; Sklik a Google zápisová práva
      mají vždy, proto platí bod níž o dry-runu.
- [ ] **`.gitignore` nech být.** Hlídá soubory s klíči, `clients/`, `reports/`, `plans/`
      a vygenerované bannery. Před prvním pushem pusť `git status` a zkontroluj, že nic z toho
      není mezi soubory k odeslání.
- [ ] Repo s klientskými daty **nikdy veřejně**. Když appku dáváš na GitHub kvůli cronu,
      repo musí být soukromé.
- [ ] **Nedělej fork veřejného repa appky.** Fork veřejného repa je vždy veřejný a jeho viditelnost
      nejde změnit (dokumentace GitHubu „About permissions and visibility of forks"). Založ nové
      **privátní** repo a appku do něj nahraj.
- [ ] Kde platforma umí **limit útraty** (ChatGPT Ads spend limit, rozpočty kampaní), nastav ho.

## 4. Čtení vs. zápis

- Hlídače, forecast, krycí plán a `fetch.py` skripty **jen čtou**.
- Zápisové skripty jedou **nejdřív nanečisto** (dry-run, u Google Ads `validate_only`,
  u Skliku metody `*.check`). Ostře až `--apply` (Python) nebo `--confirm` (ChatGPT Ads),
  a jen po tvém schválení konkrétního plánu.
- Žádné hromadné zápisy bez lidské kontroly textů reklam. Žádné souběžné skripty proti
  jednomu API (limity, riziko zablokování účtu). Detail: `knowledge/api-limity-bezpecnost.md`.

## 5. Když klíč unikne

Postup je vždy stejný: **1) zneplatni na straně platformy, 2) vydej nový, 3) přepiš soubor
s klíči, 4) ověř read-only příkazem, 5) projdi historii změn v účtu.**

| Systém | Kde zneplatnit | Ověření |
|---|---|---|
| Google Ads / GA4 | Cloud Console → Google Auth Platform → Clients: smaž secret nebo celého klienta; vygeneruj nový refresh token | `scripts/google_ads/fetch.py --list-clients` |
| Sklik | Sklik → přístup k API: nový token (cesta v menu neověřena) | `scripts/sklik/fetch.py --call client.get` |
| Meta | Business Settings → Systémoví uživatelé → token zneplatnit | `scripts/meta/fetch.py accounts` |
| ChatGPT Ads | Ads Manager → Settings → API keys | `chatgpt-ads/run.sh account` |
| Gemini | AI Studio → API keys → smazat | `scripts/start/stav.py --ai` |
| OpenAI (bannery) | platform.openai.com/api-keys → revoke | `scripts/start/stav.py --ai` |
| Anthropic (NDA relace) | Claude Console → API keys | `./nda.sh`, pak `/status` |

Po úniku zkontroluj v účtech historii změn (Google Ads historie změn, Meta activity log,
Sklik historie) za dobu, kdy byl klíč venku. Když unikl do Gitu, nestačí ho smazat dalším
commitem — v historii zůstává, proto vždy zneplatnit.

## 6. Podmínky, pod kterými Claude běží (stručně)

Přihlášení tarifem Pro / Max = spotřebitelské podmínky, API klíč / Team / Enterprise =
obchodní podmínky s DPA a bez tréninku. Token z `claude setup-token` (pro běh v cronu)
podle dokumentace autentizuje **tvým předplatným**, takže i cron běží pod spotřebitelskými
podmínkami. Detail, zdroje a co z toho plyne pro NDA klienty: `docs/nda-rezim.md`.

## 7. NDA rozcestník

| Otázka | Kde |
|---|---|
| Je klient pod NDA? Jaký režim? | `docs/nda-rezim.md`, průvodce `/start` krok B |
| Anonymizovaná data | `scripts/google_ads/fetch_safe.py`, `scripts/sklik/fetch.py --anon <klient>` |
| Plná data přes API klíč | `./nda.sh` (Terminál, ne aplikace Claude) |
| Kdo to vynucuje | `scripts/lib/nda.py` (skripty), `.claude/hooks/nda_guard.py` (soubory) |
| Stav relace a NDA klientů | `CLAUDECODE=1 .venv/bin/python scripts/lib/nda.py` |

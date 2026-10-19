# Nasazení hlídačů: ať to běží samo

Hlídače (`scripts/hlidac/`, `scripts/plan/plneni.py`) jen čtou. Otázka je, **kde a kdy**
poběží. Pět možností, od nejjednodušší po nejpokročilejší.

Průvodce volbou a nastavením: řekni Claude Code „nasaď hlídač" (skill `nasazeni`).

Stav ověření: fakta o službách jsou z oficiální dokumentace k 19. 10. 2026 (odkazy u každé
varianty). Co ověřené není, je tak označené. Ceny a limity se mění — před rozhodnutím
klikni na odkaz.

## Co a kdy pouštět

| Kdy (Praha) | Co | Příkaz |
|---|---|---|
| denně 7:30 | výkyvy včerejška + plnění cílů + krycí plán | `python3 deploy/spust.py --rezim rano` |
| denně 19:05 | utíká dnešek? | `python3 deploy/spust.py --rezim vecer` |
| pátek 18:05 | hlídač akcí (prostor na víkend) | `python3 deploy/spust.py --rezim akce` |
| sobota, neděle 10:05 | hlídač akcí o víkendu | `python3 deploy/spust.py --rezim vikend` |

`deploy/spust.py` jen pouští hlídače ve správném pořadí:
- `rano` = `hlidac.py` + `cile.py` + `plneni.py --klient <k>` u klientů, kteří mají v
  `clients/hlidac-ucty.json` v `hlidat` položku `kryci-plan`,
- `vecer` = `hlidac.py --dnes`, `akce` = `akce.py --vikend --dnes` (pátek večer), `vikend` = `akce.py --vikend`.

Návratový kód je nejhorší z hlídačů: 0 OK, 1 žlutá, 2 červená nebo chyba.
Časy si můžeš uložit i do konfigurace (`planovani` v `clients/hlidac-ucty.json`), ať je máš
na jednom místě. Plánovač si je ale nečte sám — nastavuješ je ve zvolené variantě.

## Srovnání

| | A. Úloha v aplikaci Claude | B. Cloudová rutina Claude | C. GitHub Actions | D. Vercel Cron | E. launchd / cron |
|---|---|---|---|---|---|
| **Běží když** | aplikace běží a počítač nespí | vždy (cloud Anthropicu) | vždy (servery GitHubu) | vždy (servery Vercelu) | počítač nespí |
| **Zmeškaný běh** | po probuzení 1× doběhne (za 7 dní zpět) | — | — (jen zpoždění) | neopakuje se | po probuzení 1× doběhne |
| **Cena** | v rámci předplatného Claude | v rámci předplatného (Pro, Max, Team, Enterprise) | privátní repo: 2 000 min/měs zdarma (Free) | Hobby zdarma, ale jen nekomerčně → reálně Pro | zdarma |
| **Náročnost** | nízká | střední | střední | vysoká | střední |
| **Analýza Claudem** | ano, skilly | ano, skilly | jen skript; Claude volitelně (Claude Code Action) | jen skript | jen skript |
| **Kde jsou klíče** | `.env` na tvém disku | proměnné cloudového prostředí | GitHub Secrets | Vercel Environment Variables | `.env` na tvém disku |
| **Hlavní omezení** | zavřené víko = neběží | research preview; klíče v cloudu; Sklik a Meta je potřeba povolit v síti | cron se může zpozdit; potřebuješ privátní repo | Hobby jen 1× denně ±59 min a nekomerčně; max 300 s; čas v UTC | jen pro pokročilé, bez Clauda |

## Doporučení

- **Začínáš?** → **A. Úloha v aplikaci Claude.** Nejmíň nastavování, Claude rovnou projde
  nálezy skillem `anomalie`. Na noc a víkend přidej „Keep computer awake".
- **Chceš běh i se zavřeným notebookem a analýzu Claudem („nechat to na agentovi")** →
  **B. Cloudová rutina.** Jde to, ale klíče k reklamním účtům musí do cloudového prostředí
  a je to research preview. Viz omezení níž.
- **Stačí ti skriptový report zdarma a spolehlivě** → **C. GitHub Actions.**
- **Už máš appku na Vercelu (Pro)** → **D. Vercel Cron.** Jinak ho nedoporučuju.
- **Chceš jen skripty na vlastním Macu bez aplikace** → **E. launchd.**

Kombinace funguje taky: C nebo E jako pojistka, která běží vždy, a A na analýzu, když jsi u počítače.

---

## A. Naplánovaná úloha v aplikaci Claude (Desktop)

Dokumentace: [Desktop scheduled tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks).

**Jak:** aplikace Claude → záložka **Code** → **Routines** → **New routine** → **Local**.
Vyplň název, instrukce (prompt z `deploy/claude-routine/prompt.md`), pracovní složku = složka
appky, plán (Daily / Weekdays / Weekly; jiný interval napiš Claudovi slovy, např. „naplánuj
úlohu v sobotu a neděli v 10:05"). Volba **Local** vyžaduje Claude Desktop 1.1.5368 nebo novější.

**Co je ověřené:**
- Úloha běží jen, když je aplikace spuštěná a počítač nespí. Když počítač prospí plánovaný
  čas, běh se přeskočí.
- Po probuzení nebo spuštění aplikace se doběhne **jeden** zmeškaný běh (ten nejnovější
  z posledních 7 dní), starší se zahodí. Ranní úloha tedy může doběhnout třeba až večer —
  proto prompt pracuje s režimem a hlídač si datum hlídá sám.
- Každá úloha startuje o pár minut později než plán (pevný posun, kvůli rozložení provozu).
- „Keep computer awake" (Settings → This computer → System) brání uspání při nečinnosti,
  zavřené víko ale počítač uspí.
- Každá úloha má vlastní režim oprávnění. Po vytvoření dej **Run now** a u dotazů zvol
  „always allow" — jinak další běhy čekají na schválení.
- Klíče zůstávají v `.env` na disku, nic se nikam nenahrává.

## B. Cloudová rutina Claude Code („nechat to na agentovi")

Dokumentace: [Routines](https://code.claude.com/docs/en/routines),
[Cloud environments](https://code.claude.com/docs/en/cloud-environments).

**Co to je:** uložený prompt + repozitář + prostředí, které Claude spouští na infrastruktuře
Anthropicu podle plánu. Běží, i když máš notebook zavřený. Claude v něm pracuje sám bez
schvalování (žádný výběr režimu oprávnění) — proto prompt musí výslovně zakázat zápisy.

**Ověřené:**
- Je to **research preview** — chování a limity se můžou změnit.
- Tarify: Pro, Max, Team, Enterprise. Spotřebovává stejné limity předplatného jako běžná práce.
- Zakládá se na [claude.ai/code/routines](https://claude.ai/code/routines), v aplikaci
  (Routines → New routine → **Cloud**) nebo v terminálu příkazem `/schedule`
  (vyžaduje přihlášení předplatným claude.ai, ne API klíčem).
- Nejkratší interval 1 hodina. Čas zadáváš v místním čase, převod dělá sama. Běh přesně na
  celou hodinu může začít o pár minut později → dej 7:30, 19:05.
- **Repozitář jen z GitHubu.** Při každém běhu se naklonuje znovu (čistý klon). Tvůj `.env`
  ani `clients/` (jsou v `.gitignore`) v něm nejsou.
- **Klíče:** proměnné prostředí cloudového prostředí (formát jako `.env`). Dokumentace
  upozorňuje, že je **vidí každý, kdo to prostředí používá** — založ si proto vlastní
  prostředí jen pro sebe, ne sdílené.
- **„Network secrets"** (klíč, který Claude nevidí) tady **nepomůžou**: proxy je přidává do
  hlavičky požadavku, ale naše skripty posílají Sklik token v těle volání `client.loginByToken`
  a Meta token jako parametr `access_token` (ověřeno v kódu). Skripty navíc klíč potřebují
  mít v ruce, jinak se ani nespustí.
- **Síť:** výchozí úroveň „Trusted" pouští jen seznam povolených domén. Je v něm
  `*.googleapis.com` (Google Ads API), ale **ne** `api.sklik.cz` ani `graph.facebook.com`.
  Pro Sklik a Metu přepni prostředí na **Custom** a přidej tyhle dvě domény (a zaškrtni
  „Also include default list of common package managers", ať projde instalace knihoven).
- Knihovny: setup script `pip install -r requirements.txt` (výsledek se ukládá do cache).
- Limit: 100 naplánovaných běhů za hodinu na účet — pro hlídač bohatě stačí.

**Neověřené:** jak se rutina chová, když běh trvá dlouho (desítky účtů) — dokumentace uvádí
jen časové limity příkazů (2 min výchozí, až 10 min, pak běží na pozadí max. 30 min).

**Postup:** viz skill `nasazeni` nebo:
1. Nahraj appku do **privátního** repa na GitHubu (bez `.env`).
2. claude.ai/code → prostředí → nové prostředí „ppc-hlidac": síť Custom (`api.sklik.cz`,
   `graph.facebook.com` + výchozí seznam), proměnné prostředí: `HLIDAC_UCTY_JSON` (obsah
   konfigurace na jeden řádek) a přístupy se stejnými názvy jako v `.env.example`; setup
   script `pip install -r requirements.txt`.
3. Nová rutina → Cloud → prompt z `deploy/claude-routine/prompt.md` → repo → prostředí
   „ppc-hlidac" → plán. **Odeber konektory**, které hlídač nepotřebuje (Claude je smí
   v rutině používat i k zápisům bez ptaní).
4. **Run now** a zkontroluj relaci: zelený stav znamená jen „doběhlo bez chyby
   infrastruktury", ne „hlídač proběhl". Otevři běh a přečti, co Claude udělal.

**NDA klienti:** klíče a data klienta pod NDA do cloudového prostředí nedávej, pokud to
smlouva výslovně nedovoluje. Pro ně zůstaň u varianty A nebo E (`docs/nda-rezim.md`).

## C. GitHub Actions

Dokumentace: [schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[ceny](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[Claude Code Action](https://code.claude.com/docs/en/github-actions).

Šablona a návod: `deploy/github-actions/`.

**Ověřené:**
- Veřejná repa zdarma, privátní: GitHub Free 2 000 minut měsíčně, Pro 3 000 minut.
  **Používej privátní repo** — reporty v artefaktech obsahují čísla z účtů.
- Klíče v GitHub Secrets, za běhu se zapíšou do `.env`, konfigurace účtů ze secretu
  `HLIDAC_UCTY_JSON`. Python skripty běží přímo.
- Plán je výchozí v UTC, ale jde zadat `timezone: "Europe/Prague"` (šablona to dělá) —
  pak se nemusíš starat o letní a zimní čas.
- Naplánovaný běh se ve špičce **může zpozdit**, špičkou je začátek každé hodiny.
  Nejkratší interval 5 minut. Plán běží jen z výchozí větve. Ve veřejném repu se plán po
  60 dnech bez aktivity vypne.
- Analýza Claudem jde volitelně přes `anthropics/claude-code-action@v1` s předplatným
  (secret `CLAUDE_CODE_OAUTH_TOKEN` z `claude setup-token`) nebo API klíčem.
- Krycí plán (`plans/`) a changelog klientů (`clients/`) v repu nejsou → `plneni.py` se
  přeskočí a hlídač cílů bere `posledni_zmena` z konfigurace.

## D. Vercel Cron

Dokumentace: [Cron Jobs ceny a limity](https://vercel.com/docs/cron-jobs/usage-and-pricing),
[správa cronů](https://vercel.com/docs/cron-jobs/manage-cron-jobs),
[Python runtime](https://vercel.com/docs/functions/runtimes/python),
[limity funkcí](https://vercel.com/docs/functions/limitations),
[Hobby](https://vercel.com/docs/plans/hobby).

Šablona a návod: `deploy/vercel/`.

**Ověřené:**
- Python funkce v `api/` (třída `handler` z `BaseHTTPRequestHandler`), crony v `vercel.json`
  (`path` + `schedule`), běží jen na produkčním nasazení, čas v UTC.
- Zabezpečení: proměnná `CRON_SECRET`, Vercel ji posílá v hlavičce
  `Authorization: Bearer …`, funkce ji porovná.
- **Hobby:** jen 1× denně na záznam, čas kdykoli během dané hodiny, a hlavně **jen pro osobní,
  nekomerční použití** — hlídání klientských účtů je komerční → potřebuješ Pro.
- Max. délka běhu 300 s na Hobby, na Pro výchozí 300 s, až 800 s.
- Velikost: limit Python funkce 500 MB; `google-ads` + `requests` mají nainstalované cca 145 MB
  (změřeno). Vejde se.
- Proměnné prostředí: dohromady max. 64 KB na nasazení; změna platí až od nového nasazení.
- Vercel neúspěšný cron neopakuje a výjimečně ho doručí dvakrát nebo vůbec.

**Neověřené:** že je ve funkci zapisovatelný `/tmp` (šablona do něj kopíruje skripty, protože
hlídače zapisují reporty). Ověř ručním spuštěním `vercel crons run /api/hlidac`.

## E. Vlastní počítač: launchd (macOS) / cron (Linux)

Šablona a návod: `deploy/launchd/`.

**Ověřené** (`man launchd.plist`): launchd na rozdíl od cronu zmeškaný běh spustí po
probuzení; víc zmeškaných časů spojí do jednoho běhu. Proto plist volá `spust.py --rezim auto`,
který režim vybere podle aktuálního času.

## Notifikace

Kam poslat výsledek (e-mail, Slack, Telegram, Teams, Discord, ntfy…), si vybíráš sám:
`docs/notifikace.md`.

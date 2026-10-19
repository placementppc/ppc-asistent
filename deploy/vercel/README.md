# Hlídače na Vercelu (Vercel Cron)

## Nejdřív poctivě: kdy to dává smysl

Vercel jde, ale pro hlídače to **není první volba**. Vyber ho, jen když už Vercel používáš
a máš tarif **Pro**. Jinak je jednodušší GitHub Actions (`deploy/github-actions/`).

Ověřeno v dokumentaci Vercelu (říjen 2026):

| Co | Hobby (zdarma) | Pro |
|---|---|---|
| Komerční použití | **ne** — Hobby je jen pro osobní, nekomerční projekty ([fair use](https://vercel.com/docs/plans/hobby)). Hlídání klientských účtů je komerční. | ano |
| Jak často cron | nejvýš 1× denně na jeden záznam (víc záznamů jde, až 100 na projekt) | až každou minutu |
| Přesnost času | kdykoli během dané hodiny (`30 5 * * *` = 5:00–5:59 UTC) | na minutu |
| Max. délka běhu funkce | 300 s | 300 s výchozí, až 800 s |
| Velikost funkce (Python) | 500 MB | 500 MB |

- **Velikost:** knihovna `google-ads` s `requests` má nainstalovaná cca 145 MB (změřeno),
  limit Python funkce je 500 MB. Vejde se.
- **Délka běhu:** 300 s stačí na pár účtů. Hlídač čte účty jeden po druhém — u desítek účtů
  nebo pomalého API může limit přetéct (funkce vrátí 504). Pak rozděl účty nebo jdi na GitHub Actions.
- **Čas je v UTC** a Vercel neumí časové pásmo → při změně letního/zimního času se běh posune o hodinu.
- **Vercel cron neopakuje** neúspěšný běh a výjimečně ho doručí dvakrát nebo vůbec ne
  ([dokumentace](https://vercel.com/docs/cron-jobs/manage-cron-jobs)). Hlídači to nevadí (jen čte).
- **Kam se ukládá report:** funkce nemá trvalý disk a obsah reportu **nevrací** — odpověď
  i log vidí každý s přístupem k projektu, proto v nich je jen stav a počty (kolik kroků
  zelených, žlutých, červených). Plný report si pošli přes notifikaci (`docs/notifikace.md`)
  nebo ulož do úložiště (Blob); obojí si napojíš sám. Když chceš report číst, spusť hlídač
  lokálně nebo v GitHub Actions (report je tam v artefaktu).
- **Neověřeno:** že je na Vercelu zapisovatelná složka `/tmp` (funkce do ní kopíruje skripty,
  protože hlídače zapisují reporty). Dokumentace Vercelu to na stránkách, které jsem prošel,
  výslovně neuvádí. Ověř prvním ručním během (krok 6).

## Krok za krokem (Vercel CLI)

Předpoklad: účet na Vercelu (Pro), nainstalované [Vercel CLI](https://vercel.com/docs/cli)
a přihlášení `vercel login`. Vše spouštěj z kořene appky.

1. **Připrav balík skriptů:**
   ```
   bash deploy/vercel/priprav.sh
   ```
   Zkopíruje `scripts/` a `deploy/spust.py` do `deploy/vercel/balik/`. Klíče se nekopírují.
2. **Propoj projekt** (jednou):
   ```
   cd deploy/vercel && vercel link
   ```
   Vytvoř nový projekt, např. `ppc-hlidac`.
3. **Přidej proměnné prostředí** (Production). Hodnotu zadáváš sám do výzvy, nikam se nevypíše:
   ```
   vercel env add CRON_SECRET production --sensitive
   vercel env add HLIDAC_UCTY_JSON production --sensitive < ../../clients/hlidac-ucty.json
   vercel env add SKLIK_API_TOKEN production --sensitive
   vercel env add META_API_TOKEN production --sensitive
   vercel env add GOOGLE_ADS_CLIENT_ID production --sensitive
   vercel env add GOOGLE_ADS_CLIENT_SECRET production --sensitive
   vercel env add GOOGLE_ADS_REFRESH_TOKEN production --sensitive
   vercel env add GOOGLE_ADS_LOGIN_CUSTOMER_ID production --sensitive
   ```
   - Jen ty systémy, které hlídáš. `CRON_SECRET` = náhodný řetězec aspoň 16 znaků
     (Vercel ho doporučuje a sám ho posílá v hlavičce `Authorization: Bearer …`).
   - Proměnné se projeví až v **novém** nasazení — proto je přidej před krokem 4.
   - Totéž jde v dashboardu: projekt → Settings → Environment Variables (typ **Secret**).
4. **Nasaď do produkce** (crony běží jen na produkčním nasazení):
   ```
   vercel deploy --prod
   ```
5. **Zkontroluj crony:** `vercel crons ls`, nebo dashboard → Settings → Cron Jobs.
6. **Otestuj hned, nečekej na ráno:**
   ```
   vercel crons run /api/hlidac
   ```
   Výsledek: dashboard → Cron Jobs → View Logs. Odpověď má pole `exit` (0 OK, 1 žlutá,
   2 červená/chyba) a počty `kroku`, `v_poradku`, `zlute`, `cervene`, `preskoceno`, `reportu`. Bez správného `CRON_SECRET` vrátí 401 — tak to má být.

## Plán (vercel.json, UTC)

| Záznam | UTC | Praha letní (CEST) | Praha zimní (CET) | Režim |
|---|---|---|---|---|
| `30 5 * * *` | 5:30 | 7:30 | 6:30 | ráno: výkyvy + cíle + krycí plán |
| `0 17 * * *` | 17:00 | 19:00 | 18:00 | večer: utíká dnešek? |
| `0 16 * * 5` | pá 16:00 | 18:00 | 17:00 | hlídač akcí |
| `0 8 * * 0,6` | so, ne 8:00 | 10:00 | 9:00 | hlídač akcí `--vikend` |

Funkce pozná režim z hlavičky `x-vercel-cron-schedule`. Když v `vercel.json` změníš čas,
změň ho i v `REZIM_PODLE_PLANU` v `api/hlidac.py`.

## Import z GitHubu místo CLI

Jde to taky: Vercel → Add New → Project → vyber privátní repo → **Root Directory** nastav
na `deploy/vercel`. Pak ale musí být `deploy/vercel/balik/` v repu commitnutý (spusť
`priprav.sh` a commitni) a po každé změně skriptů ho přegeneruj. Proměnné nastav v dashboardu.

## Bezpečnost

- `HLIDAC_UCTY_JSON` obsahuje ID účtů → jen jako proměnná typu Secret, nikdy v repu.
- Nikdy nedávej `CRON_SECRET` do URL. Jde jen v hlavičce.
- Funkce jen čte. Nemá žádný zápis do účtů a nesmí ho dostat.

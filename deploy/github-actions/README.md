# Hlídače v GitHub Actions

Hlídače běží u GitHubu, i když máš notebook zavřený. Je to jen pravidlový report
(výkyvy, cíle, krycí plán, akce). Analýzu Claudem si můžeš přidat (krok na konci `hlidac.yml`).

Celý přehled variant: `docs/nasazeni.md`.

## 🔴 Repo musí být PRIVÁTNÍ

V repu budou skilly, skripty a v artefaktech reporty s čísly z účtů. Ve veřejném repu by je
viděl kdokoli. Klíče a seznam účtů do repa nikdy nedávej — patří do **Secrets**.

**Nedělej fork veřejného repa appky.** Fork veřejného repa je vždy veřejný a jeho viditelnost
nejde změnit (dokumentace GitHubu „About permissions and visibility of forks"). Založ nové
privátní repo a appku do něj nahraj (krok 1 níž).

## Kolik to stojí

Ověřeno v dokumentaci GitHubu (říjen 2026, [billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)):
- veřejná repa na standardních runnerech zdarma (pro tohle nepoužívej),
- privátní repa: GitHub Free 2 000 minut měsíčně, GitHub Pro 3 000 minut,
- úložiště artefaktů: Free 500 MB, Pro 1 GB.

Jeden běh hlídače trvá řádově minuty (hlavně instalace knihoven). Při 4 bězích denně se do
2 000 minut vejdeš s rezervou — přesnou délku uvidíš u prvního běhu v záložce Actions.

## Krok za krokem

1. **Založ privátní repo** na GitHubu a nahraj do něj appku (bez `.env`, `clients/`
   je v `.gitignore`). Když nevíš jak, řekni Claude Code: „nahraj appku do nového privátního
   repa na GitHubu".
2. **Zkopíruj workflow:** `deploy/github-actions/hlidac.yml` → `.github/workflows/hlidac.yml`.
   Commit a push.
3. **Přidej Secrets:** repo → Settings → Secrets and variables → Actions → New repository secret.
   Jen ty, které používáš:

   | Secret | Co do něj |
   |---|---|
   | `HLIDAC_UCTY_JSON` | celý obsah tvého `clients/hlidac-ucty.json` (povinné) |
   | `HLIDAC_PLANY_B64` | volitelné: zabalená složka `plans/` (viz „Krycí plán" níž) |
   | `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, `GOOGLE_ADS_DEVELOPER_TOKEN` | stejné hodnoty jako v `.env` (developer token může zůstat prázdný, viz `.env.example`) |
   | `SKLIK_API_TOKEN` | Sklik |
   | `META_API_TOKEN` | Meta |

   Hodnoty kopíruj sám z `.env`. Claude Code je nečte a nevypisuje (blokuje to hook).
   Když Sklik účet čteš jiným tokenem (`token_var` v konfiguraci), přidej ten secret
   a jeho název i do kroku „Přístupy do .env" v `hlidac.yml`.
4. **Otestuj ručně:** záložka Actions → „Hlídač účtů" → Run workflow → režim `rano`.
   Po doběhnutí: shrnutí je přímo v detailu běhu, reporty ke stažení dole v **Artifacts**.
5. **Zkontroluj výsledek:** exit 0 = vše v pořádku, 1 = něco žluté, 2 = červené nebo účet nešel
   načíst. „Účet nejde načíst" u všech účtů obvykle znamená chybějící nebo špatný secret.

## Co vědět

- **Časy:** workflow má `timezone: "Europe/Prague"`, takže 7:30 je 7:30 našeho času i po změně
  na letní/zimní čas. Bez `timezone` GitHub počítá v UTC — přepočet je v hlavičce `hlidac.yml`.
- **Zpoždění:** GitHub píše, že naplánované běhy se ve špičce můžou zpozdit a špičkou je
  začátek každé hodiny. Proto 7:30 a 19:05, ne 7:00 a 19:00. S přesností na minutu nepočítej.
- **Jen výchozí větev:** plán běží z poslední verze výchozí větve (`main`).
- **60 dní:** ve veřejném repu GitHub plán vypne po 60 dnech bez aktivity. V privátním repu
  to dokumentace u `schedule` neuvádí.
- **Krycí plán:** `plans/` je v `.gitignore` a **do repa nepatří ani v privátním repu**
  (jsou v něm rozpočty a obraty klientů). Bez plánů se krok `plneni.py` přeskočí.
  Když kontrolu plnění chceš i tady, nahraj plány jako secret `HLIDAC_PLANY_B64`:
  v Terminálu (mimo Claude) spusť `tar czf - plans | base64 | tr -d '\n' | pbcopy` (macOS)
  a obsah schránky vlož jako hodnotu secretu. Workflow ho na dobu běhu rozbalí.
  Secret má podle dokumentace GitHubu limit 48 KB; na pár klientů to stačí. Plány se mění
  každý měsíc — secret po vytvoření nového krycího plánu přepiš.
- **Hlídač cílů** bere datum poslední změny z `posledni_zmena` v konfiguraci. Changelog
  v `clients/<klient>.md` tady není (je v `.gitignore`), takže `posledni_zmena` vyplňuj.
- **Analýza Claudem (volitelné):** krok s `anthropics/claude-code-action@v1` na konci
  `hlidac.yml`. Potřebuje secret `CLAUDE_CODE_OAUTH_TOKEN` (předplatné Pro/Max/Team/Enterprise,
  vygeneruješ `claude setup-token`) nebo `ANTHROPIC_API_KEY` (platba za tokeny).
  [Dokumentace](https://code.claude.com/docs/en/github-actions).
- **Notifikace:** `docs/notifikace.md`.

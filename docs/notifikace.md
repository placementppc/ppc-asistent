# Notifikace z hlídačů: kam poslat výsledek

Hlídače uloží report do `reports/` a vrátí kód 0 / 1 / 2. Kam ti dá vědět, si vybereš sám.
Tady je jen přehled možností a co je k tomu potřeba — hotové napojení tu není schválně.

**Jak na to:** vyber kanál, založ si, co je v tabulce, doplň proměnné do `.env` (u GitHub
Actions do Secrets, u Vercelu do Environment Variables) a řekni svému Claude Code:

> „napoj notifikace hlídače na **X** podle docs/notifikace.md"

Claude Code dopíše odeslání do místa, kde hlídač běží (`deploy/spust.py`, krok v
`deploy/github-actions/hlidac.yml`, funkce ve `deploy/vercel/api/hlidac.py` nebo prompt
naplánované úlohy).

## Pravidla pro všechny kanály

- **Webhook URL a tokeny jsou tajemství.** Kdo je zná, může ti posílat zprávy do kanálu
  (u některých i číst). Patří jen do `.env` / Secrets, nikdy do kódu, repa ani do chatu.
- **Posílej shrnutí, ne celý report.** Stačí „🔴 2 účty mají problém" + 1–2 věty ke každému.
  Celý report zůstane v `reports/`.
- **Posílej hlavně, když je problém** (kód 1 nebo 2). Kanál, který pípá každý den „vše OK",
  přestaneš číst. Jedno ranní „✅ vše v pořádku" je v pohodě.
- **Do cizích nástrojů neposílej data klientů pod NDA**, pokud to smlouva nedovoluje
  (`docs/nda-rezim.md`). Názvy účtů nahraď zkratkou.
- Python skripty v appce posílají HTTP přes standardní knihovnu (`urllib`) nebo `requests` —
  nic dalšího instalovat nemusíš (kromě e-mailu přes SDK, které ale není potřeba).

---

## E-mail

### Resend (e-mailová služba s API)

- **Co založit:** účet na [resend.com](https://resend.com), API klíč. Pro odesílání z vlastní
  domény ji v Resendu ověř (DNS záznamy) — bez toho jde jen testovací odesílatel.
- **Do `.env`:** `RESEND_API_KEY`, `NOTIFIKACE_EMAIL_OD`, `NOTIFIKACE_EMAIL_KOMU`
- **Jak se posílá (ověřeno):** `POST https://api.resend.com/emails`, hlavička
  `Authorization: Bearer <klíč>`, povinné `from`, `to`, `subject`, k tomu `text` nebo `html`.
- **Docs:** [Send email](https://resend.com/docs/api-reference/emails/send-email)
- **Neověřeno:** limity a ceny bezplatného tarifu — podívej se na jejich ceník.

### Gmail přes SMTP s heslem aplikace

- **Co založit:** v Google účtu zapnout dvoufázové ověření a vytvořit **heslo aplikace**.
  Ověřeno: heslo aplikace jde jen s dvoufázovým ověřením a nemusí být dostupné u pracovních
  či školních účtů, u Advanced Protection nebo když máš 2FA jen přes bezpečnostní klíč.
- **Do `.env`:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_UZIVATEL`, `SMTP_HESLO`, `NOTIFIKACE_EMAIL_KOMU`
- **Hodnoty serveru:** podle nápovědy Googlu pro SMTP (neověřoval jsem; obvykle se uvádí
  `smtp.gmail.com`, port 587 se STARTTLS).
- **Bezpečnost:** heslo aplikace = plný přístup k poště. Nikdy ho nedávej do repa.
  Pro tohle si klidně založ samostatný Gmail jen na notifikace.
- **Docs:** [Hesla aplikací](https://support.google.com/accounts/answer/185833)

## Slack — Incoming Webhook

- **Co založit (ověřeno):** Slack app (nebo použij existující) → **Incoming Webhooks** →
  zapnout „Activate Incoming Webhooks" → „Add New Webhook to Workspace" → vybrat kanál →
  povolit. Dostaneš webhook URL.
- **Do `.env`:** `SLACK_WEBHOOK_URL`
- **Jak se posílá:** `POST` na webhook URL, JSON `{"text": "…"}`.
- **Bezpečnost:** Slack sám píše, že URL obsahuje tajemství, nemá se sdílet ani dávat do
  veřejného repa, a uniklé URL aktivně ruší.
- **Docs:** [Sending messages using incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)

## Telegram — bot

- **Co založit (ověřeno):** v Telegramu napiš **@BotFather** příkaz `/newbot` a projdi
  průvodce → dostaneš token bota. Pak botovi napiš libovolnou zprávu a zjisti `chat_id`
  (Claude Code ti ho vytáhne voláním `getUpdates`).
- **Do `.env`:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **Jak se posílá:** `https://api.telegram.org/bot<token>/sendMessage` s `chat_id` a `text`.
- **Bezpečnost:** Telegram píše, ať s tokenem zacházíš jako s heslem a nedáváš ho do kódu.
  Při úniku ho přes @BotFather zrušíš a dostaneš nový.
- **Docs:** [Tutoriál](https://core.telegram.org/bots/tutorial), [Bot API](https://core.telegram.org/bots/api)

## Microsoft Teams — Workflows webhook

- **Pozor:** staré „Office 365 Connectors" (Incoming Webhook konektor) Microsoft ruší.
  Podle oznámení v Microsoft 365 Message Center (MC1181996, citováno třetími stranami)
  měly definitivně skončit v květnu 2026 — přesné datum jsem v oficiálních docs neověřil.
  Nové napojení dělej **jen přes Workflows**.
- **Co založit (ověřeno):** v Teams otevři **Workflows** → najdi šablonu „Send webhook alerts
  to a channel" (nebo „… to a chat") → vyber tým a kanál → ulož → na detailu workflow
  zkopíruj webhook URL. Microsoft upozorňuje, že každá šablona má jiný typ ověření.
- **Do `.env`:** `TEAMS_WEBHOOK_URL`
- **Neověřeno:** přesný formát zprávy, který workflow přijme (karta Adaptive Card vs. prostý
  text). Nech Claude Code ověřit v dokumentaci a poslat testovací zprávu.
- **Docs:** [Create incoming webhooks with Workflows](https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498)

## Discord — webhook

- **Co založit:** v nastavení kanálu → Integrace → Webhooky → nový webhook → zkopírovat URL.
  (Cestu v menu jsem v oficiální nápovědě neověřil — stránka nešla načíst.)
- **Do `.env`:** `DISCORD_WEBHOOK_URL`
- **Jak se posílá (ověřeno):** `POST` na webhook URL s `content` (max. 2 000 znaků).
- **Bezpečnost:** webhook nepotřebuje žádné další přihlášení — kdo má URL, může do kanálu psát.
- **Docs:** [Webhook resource](https://docs.discord.com/developers/resources/webhook)

## Push notifikace do mobilu

### ntfy

- **Co založit:** nic — stačí appka ntfy v mobilu a odběr tématu. Volitelně účet a přístupový
  token.
- **Do `.env`:** `NTFY_TEMA` (a případně `NTFY_TOKEN`)
- **Jak se posílá (ověřeno):** `POST` na `https://ntfy.sh/<tema>` s textem zprávy.
- **Bezpečnost:** bez registrace je **název tématu heslo** — kdo ho uhodne, čte tvoje zprávy.
  Zvol dlouhý náhodný název. Kvůli tomu na veřejném ntfy.sh neposílej názvy klientů ani čísla,
  jen „🔴 hlídač: 2 účty mají problém, mrkni do reportu".
- **Docs:** [Publishing](https://docs.ntfy.sh/publish/)

### Pushover

- **Co založit:** účet na pushover.net, appka v mobilu, zaregistrovat aplikaci → API token;
  user key najdeš po přihlášení.
- **Do `.env`:** `PUSHOVER_TOKEN`, `PUSHOVER_USER`
- **Jak se posílá (ověřeno):** `POST https://api.pushover.net/1/messages.json` s `token`,
  `user`, `message` (max. 1 024 znaků). Dokumentace uvádí 10 000 zpráv měsíčně zdarma na účet.
- **Neověřeno:** cena mobilní aplikace.
- **Docs:** [Pushover API](https://pushover.net/api)

---

## Co říct Claude Code

Příklady:
- „napoj notifikace hlídače na Slack podle docs/notifikace.md, posílej jen když exit není 0"
- „pošli mi každé ráno shrnutí hlídače e-mailem přes Resend podle docs/notifikace.md"
- „v GitHub Actions odkomentuj notifikační krok a přepiš ho na Telegram"

Claude Code by měl: přidat odesílání, poslat **jednu testovací zprávu**, ověřit, že dorazila,
a hodnoty z `.env` nikde nevypsat.

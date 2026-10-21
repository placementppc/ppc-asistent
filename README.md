# PPC asistent

AI asistent pro PPC specialisty a majitele e-shopů. Pracuje nad Google Ads, Sklikem,
Meta Ads a ChatGPT Ads. Běží v [Claude Code](https://claude.com/claude-code): otevřete složku,
napište `/start` a průvodce vás provede vším ostatním.

> Vznikl pro webinář **[PLACEMENT.cz](https://www.placement.cz)**. Další webináře o AI v marketingu
> najdete na **[vzdelavani.placement.cz](https://vzdelavani.placement.cz)**.
>
> Autor: **Jakub Herrmann**, vibe marketér a CEO PLACEMENT

## Co umí

| Oblast | Co dělá | Jak říct |
|---|---|---|
| 🧭 **Průvodce** | Krok za krokem: NDA, bezpečnost, napojení systémů, cíle, limity, hlídače, kde to poběží | `/start` |
| 🎨 **Bannery AI** | Nejdřív brand manuál: buď ho dodáte, nebo si ho asistent vytvoří z webu klienta. Teprve podle něj koncepty, schválení a výroba (Gemini, volitelně OpenAI) | „udělej bannery na Black Friday" |
| 🔌 **Napojení** | Návody na přístupy do Google Ads, Skliku, Mety, ChatGPT Ads a GA4, včetně ověření, že to funguje | „napoj Sklik" |
| 📈 **Forecast** | Odhad na měsíc ze skutečné historie účtu: sezónnost, scénáře, co udělá vyšší rozpočet | „forecast na listopad" |
| 🛍 **Black Friday a Vánoce** | Průvodce: zeptá se na cíle, akci a grafiku, vezme data z API nebo exportů (Ads, Meta, Sklik, GA4) a vyrobí plán po týdnech v PDF | „plán na Black Friday" |
| 📅 **Denní krycí plán** | Měsíční rozpočet a obrat rozpadne na dny a systémy. Každý den porovná skutečnost s plánem a spočítá, kolik dohnat | „krycí plán na prosinec", „jsme v plánu?" |
| 🛠 **Optimalizace** | Přes 25 skillů: vyhledávací dotazy, PMax, Seznam Nákupy, Meta strop a katalog, měření, aukce, tempo rozpočtu, tvorba kampaní a textů | „projdi účet", „co vyloučit" |
| 🚨 **Hlídač výkyvů** | Ráno a večer zkontroluje, jestli účet nestojí, neutíká nebo nepadají konverze | „pohlídej účty" |
| 🎯 **Hlídač cílů** | Od poslední změny v účtu ověří, jestli plní cíl (PNO, ROAS, CPA), a navrhne další krok | „plní účet cíle?" |
| 🚀 **Hlídač akcí** | Hledá prostor pro škálování, klidně v pátek večer a o víkendu. Jen navrhuje, nic nemění | „kde přidat?" |
| ☁️ **Nasazení** | Poradí, kde nechat hlídače běžet: naplánovaná úloha v Claude, cloudový agent, GitHub Actions nebo Vercel cron | „ať to běží samo" |

## Rychlý start

1. Nainstalujte [Claude Code](https://claude.com/claude-code) (aplikace Claude nebo terminál).
2. Stáhněte si tuto složku (ZIP nebo `git clone`) a otevřete ji v Claude Code.
3. Napište **`/start`**.

Průvodce se zeptá na všechno potřebné a nastaví to s vámi. Technické minimum: Python 3.9+
a pro bannery Node.js 20+. Instalaci závislostí za vás spustí Claude, když mu to průvodce řekne.

## Bezpečnost na prvním místě

- **Žádná změna v reklamním účtu bez vašeho schválení.** Zapisující skripty běží ve výchozím
  stavu naprázdno (dry-run) a skutečně zapíšou až s `--apply` / `--confirm`.
- **Klíče patří jen do souboru `.env`**, který je v `.gitignore`. Claude ho nečte, hlídá to hook
  `.claude/hooks/env_guard.py`. Klíče nikdy nevkládejte do chatu.
- **Klienti pod NDA:** průvodce se ptá u každého klienta. Na výběr je anonymizace dat, nebo
  samostatná relace s API klíčem. Viz [`docs/nda-rezim.md`](docs/nda-rezim.md) a
  [`docs/bezpecnost.md`](docs/bezpecnost.md).
- Hlídače jen čtou. I hlídač akcí jen navrhuje a změnu schvalujete vy.

## Co je uvnitř

```
.claude/skills/     skilly (mozek asistenta), začněte u start/ a ppc-fachman/
scripts/            napojení na API: google_ads, sklik, meta, ga4, hlidac, plan, brand
banner-generator/   výroba bannerů, reels a animací
chatgpt-ads/        CLI pro ChatGPT Ads (OpenAI Advertiser API)
knowledge/          PPC metodika
docs/               návody: napojení, bezpečnost, NDA, nasazení, notifikace
deploy/             šablony pro běh v cronu (GitHub Actions, Vercel, launchd, Claude)
clients/            vaši klienti (šablona _TEMPLATE.md; obsah se necommituje)
```

## Poděkování a licence

- Kód tohoto repozitáře je pod licencí MIT, viz [`LICENSE`](LICENSE).
- `chatgpt-ads/` vychází z projektu [chatgpt-ads-app](https://github.com/faborsky/chatgpt-ads-app)
  od Jindřicha Fáborského, také pod MIT (`chatgpt-ads/LICENSE`).
- Skill `sklik-ppc` ovládá samostatnou appku [sklik-ppc-app](https://github.com/faborsky/sklik-ppc-app).
  Kdo ji chce používat, naklonuje si ji zvlášť a nastaví proměnnou prostředí `SKLIK_PPC_APP_DIR`
  na cestu ke klonu (např. `export SKLIK_PPC_APP_DIR="$HOME/dev/sklik-ppc-app"` v `~/.zshrc`).
  Do SKILL.md se cesta nezapisuje. Zbytek appky pracuje se Sklikem i bez ní (`scripts/sklik/`).

Asistent je nástroj, ne náhrada úsudku. Každý návrh si ověřte a za změny v účtech odpovídáte vy.

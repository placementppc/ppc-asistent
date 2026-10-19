# Napojení: ChatGPT Ads (OpenAI Advertiser API)

> Ověřeno v dokumentaci developers.openai.com/ads/api-overview 19. 10. 2026: klíč se vydává
> v Ads Manageru na stránce **Settings**, API běží na `https://api.ads.openai.com`, posílá se
> v hlavičce `Authorization: Bearer`, limity 600 dotazů/min na endpoint a 1 200/min celkem
> (na reklamní účet i na IP adresu).

## Pozor: vlastní složka, vlastní soubor s klíčem

ChatGPT Ads obsluhuje samostatná appka ve složce `chatgpt-ads/` (`chatgpt-ads/run.sh`,
skill `chatgpt-ads`). **Klíč čte jen ze souboru `chatgpt-ads/.env`**, ne z `.env` v kořeni.
Python skripty v `scripts/` ChatGPT Ads nečtou a hlídače ho zatím nehlídají.

## Co potřebuješ

- Účet v **Ads Manageru** (ads.openai.com) s dokončeným ověřením firmy a **brand review**
  (název, URL, favicon) a s platební metodou. Bez schváleného brand review účet nic nezobrazí
  (podle `chatgpt-ads/README.md`).
- Povolenou kategorii podle reklamních zásad OpenAI (souhrn
  `.claude/skills/chatgpt-ads/chatgpt-ads-policies.md`).
- 2FA na účtu OpenAI.
- Python 3.9+.

## Krok za krokem

1. Instalace (vytvoří `chatgpt-ads/.venv` a ze vzoru založí `chatgpt-ads/.env`):
   ```
   ! chatgpt-ads/setup.sh
   ```
2. Ads Manager → **Settings → API keys** → vydej klíč. Podle `chatgpt-ads/README.md` je klíč
   vázaný na **jeden** reklamní účet (v oficiální dokumentaci to výslovně neuvádí, **neověřeno**).
   Pozor, není to klíč z platform.openai.com: ten Ads API nepustí (vrací 401/403).
3. Otevři `chatgpt-ads/.env` v editoru a vyplň:
   - jeden účet: `OPENAI_ADS_API_KEY=`
   - víc účtů (agentura, víc značek): pro každý účet pojmenovaný klíč
     `OPENAI_ADS_API_KEY_MUJESHOP=`, `OPENAI_ADS_API_KEY_DRUHAZNACKA=` a holý klíč smaž.
     Volání pak vždy s účtem: `chatgpt-ads/run.sh --account mujeshop campaigns`.
     Při dvou a víc klíčích CLI volání bez `--account` odmítne (zápis na cizí účet nejde vrátit).
   - volitelně `OPENAI_ADS_DEFAULT_ACCOUNT=` (který pojmenovaný účet je výchozí).

## Ověření (jen čte)

```bash
chatgpt-ads/run.sh account
```

Vrátí název účtu, měnu, časové pásmo a stav brand review. Název a měna musí sedět na klienta.
Pak `chatgpt-ads/run.sh spend-limits` — pojistka útraty na úrovni účtu (na self-serve účtech
endpoint podle README vracel 404; pojistkou je pak denní rozpočet kampaně a datum konce).

## UTM (povinné, jinak GA4 návštěvy nepozná)

Každá sestava má mít šablonu
`utm_source=chatgpt&utm_medium=cpc&utm_campaign=<kampan>&utm_content=<sestava>&utm_term={ad_id}`
v poli `query_string_template`. Než kampaň zapneš:

- u nové kampaně dry-run `chatgpt-ads/run.sh plan-apply --file plan.json` vypíše u každé
  sestavy `utm=…` — žádná nesmí být prázdná;
- u běžící kampaně zkontroluj `landing_page_configuration.query_string_template` v detailu
  sestavy (`adgroup-detail`, výstup `--json`).

Za 48–72 hodin po spuštění ověř v GA4, že návštěvy padají do `chatgpt / cpc`.
Postup a páky optimalizace: `knowledge/chatgpt-ads-optimalizace.md`.

## Zápisy

Všechny zápisové příkazy jsou bez `--confirm` jen nanečisto. Kampaně vznikají pozastavené.
Ostře až po schválení člověkem. Detail ve skillu `chatgpt-ads`.

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| 401 / 403 | klíč z platform.openai.com místo z Ads Manageru, nebo zneplatněný | nový klíč v Ads Manageru → Settings |
| „No venv found" | neproběhl `setup.sh` | krok 1 |
| odmítnuté volání bez `--account` | v `.env` jsou 2+ klíče | přidej `--account <nazev>` |
| 404 na `spend-limits` | self-serve účet endpoint nemá | pojistka přes denní rozpočet a konec kampaně |
| 429 | limit dotazů | CLI má vlastní rozpočet dotazů a čeká; neběž víc instancí naráz |
| kampaň cílí na USA | kampaň vytvořená v Ads Manageru má výchozí zemi USA (podle README) | zkontroluj `campaign-detail` |

## Bezpečnost

- `chatgpt-ads/.env` je v `.gitignore`, hook `env_guard` ho Claudovi nedovolí číst.
- 🔴 Příkazy `api-key-create`, `capi-key-create`, `feed-sftp-create` a `lead-sync-create`
  vytisknou nový tajný údaj. **Spouštíš je sám v Terminálu mimo Claude** a hodnotu si hned
  uložíš (správce hesel nebo soubor s klíči v `chatgpt-ads/`). Claude je nespouští a hodnotu
  mu do chatu neposílej.
- Únik: Ads Manager → Settings → API keys → klíč zneplatni a vydej nový.

# Napojení: GA4 (Google Analytics 4)

> GA4 jede přes **stejné OAuth přístupy jako Google Ads**. Nejdřív projdi
> `docs/napojeni/google-ads.md`, kroky 1–3 a 5. Ověřeno v dokumentaci Google Analytics Data API
> (developers.google.com/analytics/devguides/reporting/data/v1) 19. 10. 2026: je potřeba zapnout
> Data API v Cloud projektu, mít přístup k property a scope `analytics.readonly`.

## Co potřebuješ

- Google účet, který má v GA4 přístup k property klienta. Na čtení stačí nejnižší role
  (Viewer / Čtenář).
- Cloud projekt z napojení Google Ads.

## Krok za krokem

1. V Cloud projektu zapni **Google Analytics Data API** (reporty) a **Google Analytics Admin
   API** (seznam property — skript volá `analyticsadmin.googleapis.com/v1beta/accountSummaries`).
   Cloud Console → vyhledávání → název API → **Enable**.
2. V GA4 → Správce → Správa přístupu k property přidej svůj Google účet (ten, kterým
   generuješ refresh token) s rolí Viewer. Přesné názvy položek v menu GA4 neověřeny.
3. Refresh token musí mít scope `analytics.readonly`. Skript
   `scripts/google_ads/generate_refresh_token.py` ho žádá automaticky spolu s `adwords`.
   Když jsi token generoval dřív bez GA4, vygeneruj ho znovu:
   ```
   ! .venv/bin/python scripts/google_ads/generate_refresh_token.py --write-env
   ```
4. Do `.env` nic nového nepřidáváš. GA4 čte `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`,
   `GOOGLE_ADS_REFRESH_TOKEN`. Profil druhého MCC (`GOOGLE_ADS_PROFILE`) GA4 skript nepoužívá.

## Ověření (jen čte)

```bash
.venv/bin/python scripts/ga4/fetch.py properties
```

Vypíše property, ke kterým máš přístup. Property ID klienta zapiš do `clients/<klient>.md`.
Denní tržby za 45 dní:

```bash
.venv/bin/python scripts/ga4/fetch.py daily 123456789 --days 45
```

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| „Refresh token nemá scope analytics.readonly" | token je starší, jen pro Google Ads | krok 3 |
| HTTP 403 „API has not been used / is disabled" | Data API nebo Admin API není zapnuté | krok 1 |
| HTTP 403 u konkrétní property | účet nemá v GA4 přístup | krok 2 |
| `properties` je prázdné | účet nemá přístup k žádné property | krok 2 |
| `invalid_grant` | aplikace v Cloud projektu je v režimu Testing (token platí 7 dní) | `google-ads.md`, krok 2 |

## K čemu to appka používá

Porovnání konverzí, které si připisuje reklamní systém, s tržbami v GA4 (skill
`konverze-vs-ga4`), ověření UTM u ChatGPT Ads a prodeje po produktech. Jen čte (`runReport`,
`accountSummaries`), v GA4 nic nemění.

# Napojení: AI pro bannery (Gemini, volitelně OpenAI)

> Výchozí generátor je **Gemini** (`banner-generator/generate-banners.ts`),
> volitelně **OpenAI** (`banner-generator/generate-banners-openai.ts`).
> Gemini ověřeno v dokumentaci ai.google.dev/gemini-api/docs/api-key 19. 10. 2026.

## Pozor: klíče patří do `banner-generator/.env.local`

Generátor bannerů je samostatný Node projekt. Klíče čte **jen** ze souboru
`banner-generator/.env.local` (ne z `.env` v kořeni):

| Proměnná | Pro | Povinná |
|---|---|---|
| `GEMINI_API_KEY` | `npm run generate:gemini` (model `gemini-3.1-flash-image`) | ano |
| `OPENAI_API_KEY` | `npm run generate:openai` (model `gpt-image-2`) | ne |

## Co potřebuješ

- Node.js a npm (pro `npm install`). Verzi Node generátor nepředepisuje (neověřeno, která
  minimální funguje).
- Google účet pro Google AI Studio. Volitelně účet na platform.openai.com s nastavenou platbou.

## Krok za krokem

1. Instalace závislostí (spustí Claude, klíče se netýká):
   ```bash
   cd banner-generator && npm install
   ```
2. Založ soubor s klíči ze vzoru (spusť sám):
   ```
   ! cp banner-generator/.env.example banner-generator/.env.local
   ```
3. **Gemini klíč**: aistudio.google.com/apikey → vytvoř klíč. Vlož do
   `banner-generator/.env.local` jako `GEMINI_API_KEY="…"`.
   Google doporučuje klíč **omezit** jen na Gemini API (v AI Studiu u klíče) a nikdy ho
   nedávat do Gitu ani do kódu na webu.
4. **OpenAI klíč (volitelně)**: platform.openai.com/api-keys → vytvoř klíč. Vlož jako
   `OPENAI_API_KEY="…"`. Podle poznámky v `banner-generator/.env.example` vyžaduje model
   `gpt-image-2` ověřenou organizaci (Settings → Organization → Verify). **Neověřeno**
   v dokumentaci OpenAI.

## Ověření

```bash
python3 scripts/start/stav.py --ai
```

Pošle jeden bezplatný dotaz na seznam modelů (Gemini `models.list`, OpenAI `/v1/models`).
Klíč si skript přečte sám a nevypisuje ho, vrátí jen OK nebo chybu. Že se dá generovat
obrázek, potvrdí až první banner přes skill `bannery` (stojí pár korun).

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| „Chybí .env.local" | soubor nevznikl | krok 2 |
| „GEMINI_API_KEY nenalezen" | prázdný nebo špatně pojmenovaný řádek | krok 3, název přesně `GEMINI_API_KEY` |
| HTTP 400 / 403 od Gemini | klíč neplatný nebo omezený na jiné API | nový klíč, omez ho na Gemini API |
| HTTP 429 | vyčerpaný limit (bezplatná úroveň má nízké limity) | počkej, nebo zapni placení v AI Studiu |
| OpenAI 403 u `gpt-image-2` | organizace není ověřená | ověř organizaci, nebo zůstaň u Gemini |

## Než začneš dělat bannery

1. Brand manuál klienta: skill `brand-manual` → `banner-generator/banners-<klient>/BRAND-MANUAL.md`.
2. Bannery jen přes skill `bannery` — načte pravidla generátoru, bez nich vznikají špatné bannery.

## Bezpečnost

- `banner-generator/.env.local` je v `.gitignore`, hook `env_guard` ho Claudovi nedovolí číst.
- Únik Gemini klíče: AI Studio → API keys → klíč smaž a vytvoř nový.
  Únik OpenAI klíče: platform.openai.com/api-keys → klíč zneplatni (revoke).
- Kde to platforma umožňuje, nastav si limit útraty, ať uniklý klíč nevyčerpá kartu
  (jaké limity Google a OpenAI aktuálně nabízí, jsme neověřovali).

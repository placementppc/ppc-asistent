# Instalace banner-generátoru

Banner-generátor je podsložka appky PPC asistent (`banner-generator/`). Nic se neklonuje zvlášť.
Tenhle návod je pro AI asistenta: když uživatel řekne „nainstaluj bannery", proveď tyto kroky.

## 1. Node.js

Potřeba Node.js 20 nebo novější: `node -v`. Když chybí nebo je starší, řekni uživateli, ať ho
nainstaluje z nodejs.org (verze LTS), a počkej.

## 2. Závislosti

Z kořene appky:

```bash
npm --prefix banner-generator install
```

Nainstaluje `sharp`, `puppeteer` (stáhne si vlastní Chromium), `tsx` a `ffmpeg-static`
(ffmpeg pro animace, Homebrew není potřeba). Trvá to pár minut.

## 3. Klíče

Řekni uživateli, ať ve složce `banner-generator/` zkopíruje `.env.example` na `.env.local`
a v novém souboru sám doplní:

- `GEMINI_API_KEY` — **povinný**, výchozí AI pro obrázky i animace. Klíč: Google AI Studio (aistudio.google.com → Get API key).
- `OPENAI_API_KEY` — **volitelný**, jen pro `generate:openai` a reely. Klíč: platform.openai.com → API keys.

Klíč si od uživatele do chatu nevyžaduj, soubor s klíči nečti a nevypisuj. Je v `.gitignore`.

## 4. Ověření

```bash
npm --prefix banner-generator run generate:gemini
```

Bez názvu configu vypíše použití (`Použití: npx tsx generate-banners.ts <config-název> …`) a skončí
s kódem 1. To stačí jako důkaz, že instalace i TypeScript fungují. Skutečný test s klíčem:

```bash
npm --prefix banner-generator run generate:gemini -- ukazka --only=K1 --format=1080x1080
```

Vznikne `banner-generator/banners-ukazka/gemini_k1-…_banner_1080x1080.png`. Generování stojí kredity
u Googlu, proto ho spusť jen se souhlasem uživatele.

## 5. Co dál

Řekni uživateli:

```
Bannery jsou připravené. Napiš např. „udělej bannery pro muj-eshop".
Nejdřív společně připravíme brand manuál klienta (z jeho manuálu, nebo z webu),
pak navrhnu koncepty ke schválení a teprve potom generuju.
```

Postup: skill `bannery` → `CLAUDE.md` → `BANNER-INSTRUCTIONS.md`.

## Časté problémy

- `Chybí .env.local` → krok 3.
- `GEMINI_API_KEY nenalezen` → v souboru s klíči chybí řádek s klíčem nebo je prázdný.
- `HTTP 404` od Gemini → model v kódu už neexistuje pod tímto názvem. Ověř aktuální název
  v dokumentaci Gemini API (Image generation) a uprav konstantu `MODEL`.
- `HTTP 403` od OpenAI → organizace v OpenAI není ověřená.
- `sharp` hlásí chybějící binárku → `npm --prefix banner-generator rebuild sharp`.

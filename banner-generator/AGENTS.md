# Banner Generátor — pokyny pro AI agenty (Codex, Cursor a další)

Tahle složka je součást appky PPC asistent. Kompletní a jediná platná pravidla jsou v **`CLAUDE.md`**
v této složce. Přečti ho celý před první prací s bannery, pak `BANNER-INSTRUCTIONS.md`
a `AI-EXECUTION-RULES.md`.

Nejdůležitější body (detail v `CLAUDE.md`):

1. Před prvním konceptem musí existovat schválený `banners-<klient>/BRAND-MANUAL.md`
   (šablona `BRAND-MANUAL.template.md`, postup ve skillu `../.claude/skills/brand-manual/SKILL.md`).
2. Koncepty schvaluje uživatel. Bez schválení negeneruj.
3. Výchozí AI je Gemini (`npm run generate:gemini -- <config> --format=1080x1080`),
   OpenAI jen s klíčem (`npm run generate:openai -- …`).
4. Text a logo skládá kód (`overlays`, `logo` v configu), nikdy AI.
5. Po generování přečti text na každém PNG a překlepy přegeneruj.
6. Soubor s klíči nečti, nevypisuj a klíče nepiš do chatu.
7. Komunikuj česky.

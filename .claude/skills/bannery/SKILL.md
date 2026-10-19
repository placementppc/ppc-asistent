---
name: bannery
description: Výroba bannerů (PNG, MP4, reels) pro Metu, Google Ads a Sklik přes banner-generátor v podsložce banner-generator/. Před prvním konceptem vyžaduje schválený brand manuál klienta (když chybí, spustí skill brand-manual). Použij VŽDY, když uživatel chce bannery, kreativy, vizuály, „udělej bannery na Black Friday / Vánoce", „rozhýbej banner", „reel", „nové kreativy pro klienta X", „co vyrobit podle coverage", nebo chce hotové bannery nahrát do kampaní. Bez tohoto skillu se pravidla banner-generátoru nenačtou celá a výstupy jsou špatné.
---

# Bannery

Banner-generátor je podsložka appky: `banner-generator/` (Node/TypeScript). Obrázky dělá
**Gemini** (výchozí), volitelně **OpenAI**. Text a logo na banner skládá kód, ne AI.

Proč tenhle skill: `banner-generator/CLAUDE.md` se načítá až ve chvíli, kdy Claude pracuje se
souborem v té složce (ověřeno v dokumentaci Claude Code, kapitola o paměti: CLAUDE.md v podsložkách
se načítají na požádání). Pravidla proto načti ručně, vždy a celá.

## 0. Připrav prostředí (jednou)

1. Existuje `banner-generator/node_modules/`? Když ne: `npm --prefix banner-generator install`
   (Node 20+). Návod: `banner-generator/INSTALL.md`.
2. Existuje `banner-generator/.env.local` s `GEMINI_API_KEY`? Když ne, řekni uživateli, ať
   zkopíruje `banner-generator/.env.example` na `.env.local` a klíč doplní sám
   (klíč: Google AI Studio). Klíč nečti, nevypisuj a nepiš do chatu.
3. `OPENAI_API_KEY` je volitelný. Bez něj jede všechno přes Gemini, jen reely (`reel-generator.ts`)
   potřebují OpenAI na pozadí scén.

## 1. Brand manuál — povinný před prvním konceptem

Otevři `banner-generator/banners-<klient>/BRAND-MANUAL.md`.

- **Chybí, nebo není `SCHVÁLENO`** → spusť skill **`brand-manual`** a počkej na schválení.
  Žádný koncept, žádný prompt, žádné generování předtím.
- **Je schválený** → řekni jednou větou, kdo a kdy ho schválil, a pokračuj.

Z manuálu bereš: barvy (HEX), fonty (`brand/fonts/*.ttf` → `fontFile`), logo (`brand/logo*.png` → `logo`),
tón a oslovení, claimy, fotostyl, kompozici, zakázané věci a legislativu.
Když manuál něco zakazuje, platí to přísněji než obecná pravidla banner-generátoru.

## 2. Povinné čtení před prvním konceptem (celé, ne výřez)

1. `banner-generator/CLAUDE.md` — pravidla 1–21, příkazy, dvouvrstvý render
2. `banner-generator/BANNER-INSTRUCTIONS.md` — fáze 0–4 a zlatá pravidla
3. `banner-generator/AI-EXECUTION-RULES.md` — práce s produktovou fotkou, žádné vymýšlení
4. Podle úkolu:
   - animace / MP4 → `banner-generator/ANIMACE.md` + skill `animate` (`.claude/skills/animate/SKILL.md`)
   - nereklamní formáty → `banner-generator/NEREKLAMNI-KREATIVY.md`
   - pokrytí a brief po buňkách → `banner-generator/COVERAGE-MATRIX.md` + skill `coverage-matrix` (`.claude/skills/coverage-matrix/SKILL.md`)
5. Klient: `banner-generator/banners-<klient>/BRAND-MANUAL.md` a `PROJECT.md`
   (produkty, cílovka, fotky; vzor `banner-generator/banners-ukazka/`).

## 3. Co přidává PPC strana appky

Než navrhneš koncepty, vezmi z `clients/<klient>.md` (a `clients/<klient>-coverage.md`, pokud je):
- cíle klienta a co v účtu prokazatelně prodává (produkty, úhly, persony s výkonem),
- prázdné a vítězné buňky gridu → brief míří do prázdných, vítěze škáluje formátem,
- zakázané věci (ceny bez souhlasu, legislativa, no-go z profilu klienta).

Do `PROJECT.md` doplň jen to, co tam chybí. Výkonová data tam nepiš (u NDA klientů nic z účtu, `docs/nda-rezim.md`).

## 4. Výroba — fáze 0–4 z BANNER-INSTRUCTIONS.md

1. **Fáze 0:** kontext (manuál, PROJECT.md, existující configy a PNG → anti-recyklace).
2. **Fáze 1:** analýza + 6 konceptů (persona × úhel × formát, min. 2 nereklamní).
   **Koncepty schvaluje uživatel. Bez „ano" negeneruj.**
3. **Fáze 2:** config `banner-generator/configs/<klient>-<téma>.ts` (vzor `configs/ukazka.ts`), pak generování.
4. **Fáze 3:** **kontrola textu na každém PNG** (přečti obrázek, hlídej překlepy a diakritiku),
   vadné přegeneruj (`--only=K3`). Úspěch hlas až po ověření, že soubor existuje.
5. **Fáze 4:** volitelně animace vybraných.

Příkazy (z kořene appky; npm spouští skript ve složce `banner-generator/`, takže cesty v configu
a `.env.local` se berou odtamtud):

```bash
npm --prefix banner-generator run generate:gemini -- <config> --format=1080x1080     # výchozí
npm --prefix banner-generator run generate:openai -- <config> --format=1080x1080     # jen s OPENAI_API_KEY
npm --prefix banner-generator run generate:gemini -- <config> --only=K1,K3 --format=1080x1080
npm --prefix banner-generator run animate -- "banners-<klient>/<soubor>.png"         # cesta relativně k banner-generator/
npm --prefix banner-generator run mp4 -- "banners-<klient>/<soubor>.html" --duration=6
```

`<config>` je název souboru v `banner-generator/configs/` bez `.ts` (např. `ukazka`).
Runnery nemají `--help`; bez argumentu vypíšou použití. Výchozí formát je jen čtverec 1080×1080,
Stories a Portrait jen na vyžádání. `generate:openai` nabízej jen uživateli, který má OpenAI klíč
(zeptej se, klíč nečti).

Další nástroje (stejně přes `npm --prefix banner-generator run …`, ne přes `npm exec`, které běží v kořeni appky):

```bash
npm --prefix banner-generator run cards -- <config> --format=1080x1080   # bez obrazové AI: výřezy produktu + sazba
npm --prefix banner-generator run reel -- <config> --probe              # reely 9:16, pozadí přes OpenAI
npm --prefix banner-generator run sklik -- banners-<klient>             # zmenšení na rozměry Skliku
```

## 5. Zpátky do kampaní (jen po schválení)

- Meta: `scripts/meta/upload_images.py` (nahrání obrázků), reklamy přes `scripts/meta/apply.py`
- Sklik: `scripts/sklik/apply_banner_campaign.py`, kombinovaná reklama viz
  `knowledge/tvorba-kampani/` a skill `sklik-kombinovana-reklama`
- Google Ads: skript na nahrání obrázků zatím není (`scripts/google_ads/apply_assets.py` umí jen texty
  a rozšíření). Řekni to rovnou a nabídni ruční nahrání v rozhraní.

Vždy dry-run → ukázat uživateli → teprve po „ano" zápis (`--apply` / `--confirm` podle skriptu).
Po nahrání zapiš do `clients/<klient>-coverage.md`, které buňky dostaly nové kreativy a kdy,
ať hlídač a další vyhodnocení ví, s čím porovnávat.

## Pravidla navíc

- Hotové bannery a klientské configy zůstávají lokálně (`banner-generator/.gitignore` je vynechává).
  Necommituj je do veřejného repozitáře.
- Cizí rozpracované změny v configu nepřepisuj, založ nový config se sufixem (`-v2`).
- Logo a text nikdy do AI promptu. Logo = `logo`, text = `overlays` v configu.

# Banner Generátor

Podsložka appky PPC asistent. Vyrábí reklamní bannery (PNG + MP4) pro Meta Ads, Google Ads a Sklik.
Obrázky generuje **Gemini** (výchozí), volitelně **OpenAI** (`gpt-image-2`). Text a logo skládá kód.

Z kořene appky se sem chodí přes skill **`bannery`** (ten tyhle pravidla načte celá).
Před prvním konceptem musí existovat **schválený** `banners-<klient>/BRAND-MANUAL.md`
(skill **`brand-manual`**, šablona `BRAND-MANUAL.template.md`).

## Jak to funguje

1. **Složka klienta** `banners-<klient>/`:
   - `BRAND-MANUAL.md` — barvy, fonty, logo, tón, claimy, zakázané věci (schválený),
   - `PROJECT.md` — produkty, cílovka, fotky, legislativa oboru,
   - `brand/` — logo, fonty, podklady z manuálu nebo webu,
   - produktové fotky (ideálně `*_transparent.png`).
   Vzor: `banners-ukazka/` (smyšlená značka).
2. **Config** `configs/<klient>-<téma>.ts` — koncepty, prompty, reference fotky, texty a logo.
   Typy jsou v `banner-formats.ts` (`Config`, `Concept`, `TextOverlay`, `LogoSpec`). Vzor: `configs/ukazka.ts`.
3. **PNG** — dva runnery nad stejným configem, oba do `config.outDir`, odlišené prefixem souboru:
   - **Gemini** → `generate-banners.ts` → `gemini_<slug>_banner_<formát>.png` (výchozí)
   - **OpenAI** → `generate-banners-openai.ts` → `openai_<slug>_banner_<formát>.png` (jen s `OPENAI_API_KEY`)

   **Výchozí formát: jen čtverec 1080×1080** (FB feed, IG feed, Marketplace, Audience Network).
   Stories 1080×1920 a Portrait 1080×1350 jen na výslovné přání. Landscape 1200×628 se nepoužívá.
   Runner proto spouštěj vždy s `--format=1080x1080`, pokud uživatel neřekne jinak.
4. **MP4** — z hotového PNG: text přiletí + jemný pohyb (`animate-banner.ts`, viz `ANIMACE.md`).

## Instalace

Viz `INSTALL.md`. Zkráceně: `npm install` v téhle složce, `cp .env.example .env.local`,
klíč doplní uživatel sám (Claude ho nečte ani nevypisuje).

## Workflow (detail v `BANNER-INSTRUCTIONS.md`)

0. **Fáze 0:** schválený `BRAND-MANUAL.md` + `PROJECT.md`; zkontroluj starší configy a PNG (anti-recyklace).
1. **Fáze 1:** analýza → 6 konceptů (persona × úhel × formát) → **schválení uživatelem**.
2. **Fáze 2:** config + generování (6 konceptů × 1 formát = 6 PNG).
3. **Fáze 3:** kontrola textu na každém PNG, výběr nejlepších.
4. **Fáze 4:** volitelně animace vybraných na MP4.

## Struktura

```
banner-generator/
├── CLAUDE.md / AGENTS.md         # kontext pro AI (tenhle soubor)
├── BANNER-INSTRUCTIONS.md        # hlavní postup a zlatá pravidla
├── AI-EXECUTION-RULES.md         # práce s produktovou fotkou, žádné vymýšlení
├── BRAND-MANUAL.template.md      # šablona brand manuálu
├── NEREKLAMNI-KREATIVY.md        # 10 nereklamních formátů NS1–NS10
├── COVERAGE-MATRIX.md            # metodika gridu persona × úhel × formát
├── ANIMACE.md / INSTALL-ANIMACE.md
├── banner-formats.ts             # sdílené typy configu
├── generate-banners.ts           # Gemini runner (výchozí)
├── generate-banners-openai.ts    # OpenAI runner (volitelný)
├── animate-banner.ts             # PNG → MP4 (Gemini)
├── compose-cards.ts              # banner bez obrazové AI (výřezy produktu + sazba)
├── reel-generator.ts             # reely 9:16 (pozadí přes OpenAI)
├── banner-to-mp4.ts              # ručně psané HTML → MP4
├── resize-sklik.mjs              # zmenšení hotových bannerů na rozměry Skliku
├── lib/                          # skládání textu a loga, nereklamní bloky, typy reelů
├── configs/ukazka.ts             # vzorový config
├── banners-ukazka/               # vzorový klient (BRAND-MANUAL.md, PROJECT.md)
├── .env.example                  # šablona pro .env.local (klíče doplní uživatel)
└── banners-<klient>/             # tvoji klienti (v .gitignore)
```

## Příkazy

Z této složky (`npm run …`), nebo z kořene appky s `npm --prefix banner-generator run …`.

```bash
# VÝCHOZÍ: 6 PNG přes Gemini, jen čtverec
npm run generate:gemini -- ukazka --format=1080x1080

# Stejný config přes OpenAI (jen s OPENAI_API_KEY)
npm run generate:openai -- ukazka --format=1080x1080

# Jiné formáty jen na vyžádání
npm run generate:gemini -- ukazka --format=1080x1920   # Stories
npm run generate:gemini -- ukazka --format=1080x1350   # Portrait

# Filtry (oba runnery)
npm run generate:gemini -- ukazka --only=K1,K3 --format=1080x1080
npm run generate:gemini -- ukazka --relayout            # jen přesazení textu nad uloženým podkladem, bez API
npm run generate:openai -- ukazka --quality=medium      # low / medium / high / auto, výchozí high

# PNG → MP4 (text přiletí, jemný pohyb) — viz ANIMACE.md
npm run animate -- "banners-ukazka/gemini_k1-automat_banner_1080x1080.png"   # vznikne po generate:gemini -- ukazka --only=K1
npm run animate -- "<png>" --no-text

# Bez obrazové AI: výřezy reálné produktové grafiky + sazba kódem
# <tvuj-config> = configs/<tvuj-config>.ts, který exportuje CardsConfig (v appce vzor není, typy v compose-cards.ts)
npm run cards -- <tvuj-config> --only=K1 --format=1080x1080

# Reely 9:16 z reálných obrázků (AI jen prázdná pozadí přes OpenAI, text skládá kód)
# <tvuj-reel> = configs/<tvuj-reel>.ts, který exportuje ReelConfig (typy v lib/reel.ts, barvy a písmo z BRAND-MANUAL.md do `style`)
npm run reel -- <tvuj-reel> --probe    # 1 PNG na záběr = rychlá kontrola
npm run reel -- <tvuj-reel>            # render MP4

# Zmenšení hotových bannerů na rozměry Skliku → banners-<klient>/sklik/
npm run sklik -- banners-ukazka          # nebo banners-<tvuj-klient>

# Ručně napsané animované HTML → MP4 (<tvuj-soubor>.html si napíšeš sám, v appce vzor není)
npm run mp4 -- banners-<tvuj-klient>/<tvuj-soubor>.html --duration=6 --fps=30
```

Runnery nemají `--help`. Bez argumentu vypíšou použití a skončí.

## Dvouvrstvý render — text a logo mimo AI

AI je nedeterministická a neumí spolehlivě český text, přesnou typografii, logo ani rozměry.
Engine proto generuje **jen obraz**; nadpis, cenu, CTA a logo skládá **kódem** (`lib/compose-overlays.ts`):

- Rozměry: resize `fit: 'cover'` (bez deformace), nikdy `fill`.
- Text: pole `overlays?: TextOverlay[]` na konceptu → SVG přes `sharp` (přesná diakritika a pixely).
  Brandový font: `fontFile` (cesta k .ttf/.otf z `banners-<klient>/brand/fonts/`) — vykreslí se přes libvips
  bez instalace do systému. `@font-face` + base64 v SVG přes librsvg nefunguje.
- Pod text: `band` (plný barevný pruh v barvě z manuálu) nebo `scrim` (tmavý přechod nad fotkou).
  `band` se vykreslí jen u overlaye s `fontFile` (bez souboru fontu se tiše vynechá). Vzor obou variant: `configs/ukazka.ts`.
- Logo: pole `logo?: LogoSpec` → composite přes `sharp`. **Logo NIKDY do AI promptu.**

Když koncept používá `overlays`/`logo`, jeho `buildPrompt()` musí AI zakázat kreslit tyto prvky:
`"DO NOT render any logo or headline text — leave clean space for it."`

## Gemini vs. OpenAI

Oba runnery čtou **stejný config**. Výchozí je Gemini. OpenAI spouštěj jen když má uživatel klíč a chce srovnání:
výstupy leží vedle sebe (`gemini_…` a `openai_…`, stejný slug i rozměr). Porovnej dodržení brand manuálu,
kvalitu fotky / ilustrace a čitelnost při 1,5 s scrollu.

OpenAI vyžaduje rozměry dělitelné 16: runner generuje 1088× a zmenší na 1080×.

## Nový klient

1. `banners-<klient>/` + skill `brand-manual` → schválený `BRAND-MANUAL.md`
2. `PROJECT.md` podle `banners-ukazka/PROJECT.md`
3. Produktové fotky (bílé pozadí odstranit před generováním, viz `AI-EXECUTION-RULES.md`)
4. Postup dle `BANNER-INSTRUCTIONS.md`

## Gemini API

- **Model v kódu:** `gemini-3.1-flash-image` (`generate-banners.ts`). `animate-banner.ts` volá
  `gemini-3.1-flash-image-preview` přes `v1beta`. Názvy modelů se mění: když API vrátí 404, ověř aktuální
  název v dokumentaci Gemini API (stránka Image generation) a uprav konstantu `MODEL` v souboru.
- **Klíč:** `.env.local` → `GEMINI_API_KEY` (Google AI Studio).

## OpenAI API (volitelné)

- **Model:** `gpt-image-2` — bez reference `images/generations`, s referenční fotkou `images/edits`.
- **Klíč:** `.env.local` → `OPENAI_API_KEY` (platform.openai.com → API keys).
- Organizace v OpenAI musí být ověřená (Verify organization), jinak API vrací 403
  (zkušenost z provozu; před prvním použitím ověř v dokumentaci OpenAI).

## Pravidla

1. Komunikuj česky.
2. **Problem-first, ne feature-first (NEJDŮLEŽITĚJŠÍ).** Headline rezonuje s bolestí, situací nebo potřebou
   cílovky, ne s tím, co produkt obsahuje. Max 1 ze 6 konceptů smí být čistě feature/price. Každý koncept
   v configu má komentář `// PERSONA:`, `// PROBLÉM/POTŘEBA:`, `// ÚHEL:`, `// BUŇKA:`. Nejde vyplnit = koncept selhal.
   Popis scény („Ráno u nás voní kávou") není problem-first. Detail: `BANNER-INSTRUCTIONS.md` (Zlaté pravidlo).
3. **Doménová jasnost (1 s test).** Banner v 1 sekundě řekne i TÉMA produktu (káva, pleť, kurz, nábytek…).
   Když není v headlinu, musí být v eyebrow nebo sub-line. Detail: Druhé zlaté pravidlo.
4. **Vyvážení médií.** Sada 6 konceptů = min 2× lifestyle foto + 2× ilustrace + 1× UGC + 1× typografie. Třetí zlaté pravidlo.
5. **Cold-audience test (1,5 s).** Je to produkt? Pro koho? Co řeší? Co mám udělat? Žádné headliny,
   které předpokládají, že divák značku zná. Vizuál ukazuje produkt poznatelně. Čtvrté zlaté pravidlo.
6. Bílé pozadí produktové fotky vždy odstranit (lokálně, před generováním).
7. **Stories safe zone = umístění obsahu, NE pruh.** Obsah mezi y=320 a y=1570, pozadí edge-to-edge bez pruhů a rámečků.
8. **Legislativa podle oboru** z `BRAND-MANUAL.md` (sekce Zakázané věci a legislativa). Žádná léčebná tvrzení,
   u doplňků stravy jen schválená zdravotní tvrzení EU, žádný slib výsledku.
9. MP4: NIKDY zoom/scale na Stories, jen fade-in / shimmer / glow / sparkles.
10. **Žádné srovnávání s konkurencí ani s odborníky** (lékař, poradce, servis) jako horší alternativou.
    Odborník smí být jen situace („Na servis se čeká dva týdny?"), nikdy poražený soupeř.
11. **Kategorie > aktivní claim.** „PRODUKT pro X" („kurz pro začátečníky") místo „AKTIVITA, která X"
    („kurz, který vás naučí plynně mluvit"). Detail: Frázování bezpečných sloves.
12. **Anti-recyklace.** Existuje-li config a PNG z minula, nespouštěj ho znovu. Vypiš staré koncepty,
    navrhni 6 nových (liší se ve 2 ze 3 os: bolest, headline, médium + paleta), počkej na schválení. Páté zlaté pravidlo.
13. **Žádné vymyšlené recenze ani persony.** UGC koncept jen s DOSLOVNOU recenzí z webu nebo srovnávače,
    se zdrojem v komentáři configu. Bez recenzí UGC koncept vypustit. Šesté zlaté pravidlo.
14. **Doménový signál ve vizuálu, ne jen v eyebrow.** Vizuál sám ukazuje, o jaký produkt a použití jde. Sedmé zlaté pravidlo.
15. **Kontrola textu po každé generaci.** Přečti všechen text na každém PNG, při překlepu přegeneruj. Osmé zlaté pravidlo.
16. **Sendvič pro performance bannery:** problém jako OTÁZKA nahoře → produkt jako čitelný DŮKAZ uprostřed →
    AKCE / reframe dole. Barvy z brand manuálu (primární nahoře, akcent na akci). Deváté zlaté pravidlo.
17. **Zakázaná slova a sliby z brand manuálu jsou tvrdá.** Co `BRAND-MANUAL.md` zakazuje, nesmí padnout
    v žádném banneru, ani parafrází. Výjimka: doslovná ověřená recenze zákazníka označená jako citát
    (uvozovky + jméno + „ověřený zákazník" + datum), pokud neslibuje konkrétní léčebný výsledek.
18. **Mikro-persony × úhly.** Cílovku rozlož na 3–4 mikro-persony s odlišným MOTIVEM. Sada pokryje min 3.
    Dvě stejné dvojice persona + úhel = recyklát. Desáté zlaté pravidlo.
19. **Coverage Matrix — generuj po buňkách.** Grid persona × úhel × formát, uzavřená taxonomie
    (pain-point / mechanism / aspiration / social-proof / identity / comparison; designed-static / native-static).
    Grid klienta: `banners-<klient>/COVERAGE.md`, skill `coverage-matrix` (kořen appky). Stavy Winner/Loser jen z dat. Jedenácté zlaté pravidlo.
20. **Nereklamní statiky — min 2 ze 6 konceptů.** Formáty NS1–NS10 (`NEREKLAMNI-KREATIVY.md`, `lib/native-static.ts`).
    Stylizovaný interface ano, UI konkrétní platformy a nefunkční prvky nikdy (Meta policy). Dvanácté zlaté pravidlo.
21. **Žádná dlouhá pomlčka „—"** ve viditelném textu bannerů a reklam (působí jako AI text). Místo ní čárka, tečka,
    dvojtečka nebo nový řádek. Do promptu vždy: `NEVER use the long dash "—" in any visible text.`

## Požadavky

- **Node.js 20+**
- **ffmpeg** pro animace se instaluje sám přes npm balíček `ffmpeg-static`. Jen `banner-to-mp4.ts`
  hledá systémový `ffmpeg` (`brew install ffmpeg` na Macu).
- **Claude Code** (nebo jiný AI asistent, který umí číst obrázky).

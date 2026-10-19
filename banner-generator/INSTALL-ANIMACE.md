# Instalace: Animace bannerů → MP4

Funkce, která z hotového statického PNG/JPEG banneru udělá jednoduché MP4 video: **hlavní nadpis přiletí**, zbytek textu zůstane statický, a volitelně přes produktovou fotku **projede sluneční glint + jiskra**. Žádný černý start.

**ffmpeg se nainstaluje automaticky** přes npm balíček `ffmpeg-static` — NEPOTŘEBUJEŠ Homebrew ani nic instalovat ručně.

---

## Instalace

Funkce je už součástí repa (`animate-banner.ts`, `ANIMACE.md`, skill `animate` v kořeni appky: `.claude/skills/animate/`). Stačí:

1. **Závislosti:**
   ```bash
   npm install
   ```
   (`ffmpeg-static` je už v `package.json`, takže se nainstaluje samo.)

2. **Gemini API klíč** — stejný jako pro bannery, doplní ho uživatel sám podle `INSTALL.md` (krok 3).
   Klíč: https://aistudio.google.com/apikey

3. **Ověření** na libovolném banneru:
   ```bash
   npm run animate -- "banners-ukazka/gemini_k1-automat_banner_1080x1080.png"
   ```
   (vzorový banner vznikne podle `INSTALL.md`, krok 4; místo něj můžeš dát cestu ke svému PNG)
   Video `*_animated.mp4` se uloží vedle vstupního obrázku. Když uvidíš `✅ Hotovo: ...mp4`, je hotovo. 🎉

Potřebuješ **Node.js 20+** (`node -v`).

---

## Jak se to používá

Plný návod je v **`ANIMACE.md`**. Zkráceně:

```bash
# default: hlavní nadpis přiletí, zbytek textu statický
npm run animate -- "<obrazek.png>"

# glint + jiskra přes horní fotku (produktové bannery)
npm run animate -- "<obrazek.png>" --glint

# dvousloupcový banner (nadpis vlevo, specifikace vpravo) → vymez nadpis obdélníkem
npm run animate -- "<obrazek.png>" --head-rect=0.03,0.62,0.60,0.79

# bílý/oranžový text na černém panelu → vyšší práh
npm run animate -- "<obrazek.png>" --threshold=100

# jen jemný pohyb bez vrstvení textu (nejbezpečnější)
npm run animate -- "<obrazek.png>" --no-text
```

V Claude Code stačí napsat **„rozhýbej tenhle banner"** / **„udělej z toho video"** (skill `animate`).

---

## Časté problémy

- **`GEMINI_API_KEY nenalezen`** → chybí `banner-generator/.env.local` s klíčem (zakládá ho uživatel sám podle `INSTALL.md`).
- **`ffmpeg nenalezen`** → nedoběhlo `npm install` / `npm install ffmpeg-static`. Spusť znovu ve složce `banner-generator/`.
- **Nadpis je oseknutý / něco zůstává statické** → layout banneru je jiný; vymez nadpis ručně přes `--head-rect=l,t,r,b` (podíly šířky/výšky). Detaily v `ANIMACE.md`.
- **Kolem textu je šum** → zvyš `--threshold` (např. 60, 100).

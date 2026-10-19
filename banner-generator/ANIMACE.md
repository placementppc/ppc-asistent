# Animace bannerů → MP4

Z hotového statického PNG banneru uděláš jednoduché video do Meta Ads: **text z banneru přiletí** zdola a pozadí se jemně pohne (fade-in, shimmer, glow, sparkles). Žádný zoom/scale na Stories.

Plně automatické — nic se neopisuje ručně. Text se z banneru vytáhne sám.

## Rychlý start

```bash
# ffmpeg se nainstaloval s npm install (balíček ffmpeg-static), nic dalšího není potřeba

# rozhýbej banner (text přiletí + jemný pohyb)
# (vzorový soubor vznikne po `npm run generate:gemini -- ukazka --only=K1 --format=1080x1080`)
npm run animate -- "banners-ukazka/gemini_k1-automat_banner_1080x1080.png"
```

Výsledek: `*_animated.mp4` vedle původního PNG.

Nebo prostě řekni Claudovi: **„rozhýbej tenhle banner"** / **„udělej z toho video"** (skill `animate` v kořeni appky, `.claude/skills/animate/`).

## Jak to funguje

1. **Gemini** odstraní z banneru všechen text → čisté pozadí (`*_anim-plate.png`).
2. **sharp** porovná originál vs. čisté pozadí → rozdíl = přesně pixely textu → průhledná textová vrstva (`*_anim-text.png`).
3. Auto-vygenerovaný **HTML**: pozadí + statický text jsou vidět hned od 1. snímku (**žádný černý start**), hlavní nadpis přiletí, k tomu glint / shimmer / glow / sparkles.
4. **puppeteer + ffmpeg** nahrají snímky a složí MP4 (H.264, yuv420p, faststart — Meta-ready).

Pozn.: Když Gemini nechá v pozadí slabý zbytek nadpisu, runner v oblasti nadpisu **přemaluje pozadí lokální barvou panelu** (`*_anim-bg.png`) — funguje na jednolitém pozadí (panel). Na členitém pozadí zbytek nech zmizet vyšším `--threshold`.

`*_anim-plate.png` se cachuje, takže opakované spuštění (jiná délka/fps/preset) už znovu nevolá Gemini. Přegeneruješ přes `--force`.

## Parametry

```bash
npm run animate -- "<png>" --preset=vyrazny      # víc sparkles, výraznější shimmer/glint
npm run animate -- "<png>" --duration=6 --fps=30 # delší video
npm run animate -- "<png>" --threshold=60        # přísnější odmaskování textu (méně šumu)
npm run animate -- "<png>" --threshold=100       # hodně přísné (bílý/oranžový text na černém panelu)
npm run animate -- "<png>" --no-text             # jen ambient pohyb, bez vrstvení textu
npm run animate -- "<png>" --force               # přegeneruj plate i z cache

# Glint = přejezd slunečního světla přes horní fotku + jiskra (lens-flare). Vhodné na produktové fotky.
npm run animate -- "<png>" --glint
npm run animate -- "<png>" --glint --flare=70,22 # pozice jiskry v % (x,y), default = pravý horní roh fotky
npm run animate -- "<png>" --glint --photo=0.55  # kam až sahá horní fotka (jinak auto-detekce tmavého panelu)

# Jiskřičky v očích maskota/postavy — postupně bliknou. Dvojice = pozice oka v % (x,y).
npm run animate -- "<png>" --eyes="30,40;70,40"

# Nadpis „přiletí a bouchne" (úderový nálet: zvětšený dolétne, dosedne s překmitem + náraz pod ním).
npm run animate -- "<png>" --slam --head-rect=0.05,0.70,0.55,0.88

# Stoupající kouř z bodu — kouř/pára z produktu. x,y v %.
npm run animate -- "<png>" --smoke=50,30
```

### Jiskřičky v očích (`--eyes`)

Na každou zadanou pozici sedne malá hvězdička, která dvakrát blikne (více postav postupně). Pozice = střed oka v procentech šířky/výšky. **Souřadnice si změř** vyříznutím obličeje z originálu (sharp `.extract` + Read na crop) — ilustrovaná očka bývají malá, takže to chce trefit. Pomůcka: vykreslená jiskra se objeví zhruba o ~2 % vlevo-nahoru od zadaného bodu, takže miř lehce vpravo-dolů od středu oka.

### Který text se animuje

Default se **automaticky najde hlavní nadpis** (největší písmo) a přiletí; zbytek textu zůstane statický. Když je banner ve **dvou sloupcích** (vlevo nadpis, vpravo další text), auto-detekce nestačí — vymez nadpis ručně obdélníkem:

```bash
# l,t,r,b = podíly šířky/výšky (levý okraj, horní, pravý, dolní)
npm run animate -- "<png>" --head-rect=0.05,0.70,0.55,0.88
# jen pás řádků (přes celou šířku), když je text v jednom sloupci:
npm run animate -- "<png>" --head-band=0.47,0.64
npm run animate -- "<png>" --all-text            # starý režim: přiletí všechen text najednou
```

| Flag | Default | Popis |
|------|---------|-------|
| `--preset` | `jemny` | `jemny` / `vyrazny` — síla ambient efektů |
| `--duration` | `5` | délka videa v sekundách |
| `--fps` | `30` | snímků za sekundu |
| `--threshold` | `40` | citlivost odmaskování textu 10–120 (níž = víc textu i šumu) |
| `--no-text` | — | jen ambient pohyb celého banneru, text se nevrství |
| `--force` | — | přegeneruj plate i kdyby cache existovala |

## Kontrola kvality

Po vygenerování **vždy zkontroluj odmaskovaný text** (`*_anim-text.png` nebo přímo MP4). Gemini občas u hodně členitého pozadí nechá na hranách textu artefakty. Když to nevypadá dobře:

- `--threshold=60` → přísnější, méně šumu okolo textu
- `--threshold=25` → citlivější, když se část tenkého textu neodmaskovala
- `--no-text` → bezpečná varianta: rozhýbe se jen celé pozadí, text zůstane statický, nula rizika artefaktů

## Požadavky

- **ffmpeg** — přichází s `npm install` (balíček `ffmpeg-static`)
- `GEMINI_API_KEY` v `.env.local` (stejný jako pro generování bannerů)
- Node 20+, puppeteer + sharp + tsx (už v `package.json`)

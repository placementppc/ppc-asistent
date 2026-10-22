---
name: animate
description: Skill se použije, když uživatel chce z hotového statického PNG banneru udělat jednoduché MP4 video — "rozhýbej banner", "udělej z toho video", "ať text přiletí", "animuj tenhle banner", "/animate". Vezme nejlepší bannery, které uživatel označí, a vyrobí krátká videa kde přiletí text + jemně se pohne pozadí.
argument-hint: [cesta-k-banneru.png | název projektu/konceptu] [--no-text] [--preset=jemny|vyrazny]
allowed-tools: [Read, Bash, Glob, Edit]
---

# Animate — rozhýbání banneru na MP4

Uživatel ti dá svůj **nejlepší hotový PNG banner** (nebo víc) a ty z něj uděláš jednoduché MP4 video do Meta Ads: **text z banneru přiletí** zdola + jemný pohyb pozadí (fade-in, shimmer, glow, sparkles). Žádný zoom/scale na Stories (pravidlo 9 v `banner-generator/CLAUDE.md`).

Engine: `banner-generator/animate-banner.ts` (z kořene appky `npm --prefix banner-generator run animate -- <png>`, cesta k PNG relativně ke složce `banner-generator/`). Plně automatické, nic se neopisuje ručně. Návod: `banner-generator/ANIMACE.md`, pravidla bannerů: `banner-generator/CLAUDE.md`.

## Jak to uvnitř funguje (jen pro tvůj kontext)

1. **Gemini odstraní text** z banneru → čisté pozadí (`*_anim-plate.png`, cachuje se).
2. **sharp porovná** originál vs. pozadí → rozdíl = pixely textu → průhledná textová vrstva (`*_anim-text.png`).
3. **HTML wrapper** (auto): pozadí stojí, textová vrstva přiletí + ambient efekty.
4. **puppeteer + ffmpeg** → `*_animated.mp4` vedle původního PNG.

## Bannery z banner-generátoru: vždy `--layers` (čisté okraje)

Když banner vznikl v banner-generátoru (text skládá kód), neodmaskovávej text přes Gemini. Vrstvy ulož přímo:

```bash
npm --prefix banner-generator run generate:gemini -- <config> --only=<ID> --format=1080x1920 --relayout --layers
# jemná: nadpis přiletí + přejezd světla jen přes produkt
npm --prefix banner-generator run animate -- "banners-<klient>/<banner>_1080x1920.png" --layers --glint --glint-rect=l,t,r,b --duration=6 --name=jemna
# výrazná: nadpis přiletí a bouchne (na 9:16 bez zvětšování: spadne a odskočí), nabídka je vidět celou dobu
npm --prefix banner-generator run animate -- "banners-<klient>/<banner>_1080x1920.png" --layers --slam --duration=6 --name=vyrazna
```

Nadpis = overlay s `role: 'head'` (dělá ho `S.nadpis`), přiletí; zbytek (štítek s nabídkou, podnadpis, CTA) stojí
od prvního snímku. Kontrola: první, prostřední a poslední snímek každého videa (ffmpeg `-ss`), ukázat uživateli.

## Postup

1. **Najdi banner(y).** Pokud uživatel dá konkrétní cestu k PNG, použij ji. Pokud řekne jen projekt/koncept ("rozhýbej čtyřku z jarní sady"), najdi přes Glob odpovídající `banner-generator/banners-*/**/*_banner_*.png` a potvrď, který soubor bereš.
2. **Ověř závislosti.** ffmpeg přichází s `npm install` (balíček `ffmpeg-static`). Když skript hlásí, že ffmpeg chybí, spusť znovu `npm --prefix banner-generator install`.
3. **Spusť animaci** pro každý banner:
   ```bash
   npm --prefix banner-generator run animate -- "<cesta-k-banneru.png>"
   ```
   Default = text přiletí + jemný ambient pohyb, 5 s, 30 fps.
4. **Zkontroluj výsledek.** Otevři/ukaž `*_animated.mp4`. Hlavně zkontroluj **odmaskování textu** — pokud má text ošklivé okraje nebo se odmaskovalo moc plochy (skript varuje při >45 %):
   - zkus `npm --prefix banner-generator run animate -- "<png>" --threshold=60` (přísnější, méně šumu),
   - nebo `--threshold=25` (citlivější, když se část textu ztratila),
   - nebo `--no-text` (bezpečná varianta: jen ambient pohyb celého banneru, žádné vrstvení).
5. **Necommituj** hotová MP4 ani mezivýstupy `*_anim-plate.png` / `*_anim-text.png` (cache). Bannery klientů zůstávají lokálně.

## Parametry

| Flag | Default | Popis |
|------|---------|-------|
| `--preset=jemny\|vyrazny` | `jemny` | síla ambient efektů (vyrazny = víc sparkles, výraznější shimmer/glint) |
| `--duration=5` | 5 | délka videa v sekundách |
| `--fps=30` | 30 | snímků za sekundu |
| `--threshold=40` | 40 | citlivost odmaskování textu (10–120; níž = víc textu i šumu; bílý/oranžový text na černém panelu → 90–110) |
| `--no-text` | — | přeskoč Gemini vrstvení, jen ambient pohyb celého banneru |
| `--force` | — | přegeneruj plate i z cache |
| `--glint` | — | přejezd slunečního světla přes horní fotku + jiskra (lens-flare). Vhodné na produktové fotky. |
| `--flare=70,22` | auto | pozice jiskry v % (x,y); default pravý horní roh fotky |
| `--eyes="30,40;70,40"` | — | jiskřičky v očích maskota/postavy; dvojice = střed oka v % (x,y), postupně bliknou. Souřadnice si změř výřezem obličeje z originálu (jiskra se objeví ~2 % vlevo-nahoru od bodu). |
| `--slam` | — | nadpis „přiletí a bouchne" (úderový nálet: zvětšený dolétne, dosedne s překmitem + náraz pod textem) místo hladkého náletu. |
| `--smoke=50,30` | — | stoupající tmavý kouř z bodu (kouř/pára z produktu); x,y v %. Tmavý kouř proti světlé obloze, světlý by splynul. |
| `--photo=0.55` | auto | podíl výšky, kam až sahá horní fotka (jinak auto-detekce tmavého panelu) |
| `--head-rect=l,t,r,b` | auto | obdélník nadpisu (podíly), nutné u dvousloupcových bannerů (nadpis vlevo, další text vpravo) |
| `--head-band=a,b` | auto | jen pás řádků nadpisu (přes celou šířku) |
| `--all-text` | — | starý režim: přiletí všechen text najednou |
| `--layers` | — | vrstvy z generátoru (`_layers/`, vzniknou přes `generate:gemini … --layers`) místo odmaskování: čisté okraje, bez Gemini |
| `--glint-rect=l,t,r,b` | — | přejezd světla jen přes obdélník (podíly), typicky přes produkt |
| `--name=jemna` | — | název verze ve výstupu: `<banner>_animated-jemna.mp4` (víc verzí vedle sebe) |

## Který text se animuje

Default se **automaticky najde hlavní nadpis** (blok s největším písmem) a ten přiletí; zbytek textu (CTA, podtitulek, specifikace) zůstane statický. Auto-detekce funguje na jednosloupcové bannery. **Když je text ve dvou sloupcích** (vlevo nadpis, vpravo další text), řádková detekce splyne — vymez nadpis ručně přes `--head-rect=l,t,r,b`. Souřadnice si ověř vyříznutím oblasti z originálu (sharp `.extract`) a Read na crop, než spustíš celý render.

## Pravidla

- **Žádný zoom/scale na Stories** (9:16) — skript text posouvá jen translateY, nikdy nescaluje. `--slam` na 9:16
  nadpis nezvětšuje: spadne shora, dosedne a odskočí (jen posun). Ambient efekty jsou jen fade/shimmer/glow/sparkles (soulad s pravidlem 9 v `banner-generator/CLAUDE.md`).
- **Vždy zkontroluj odmaskovaný text** než video předáš — Gemini občas u členitého pozadí nechá artefakty na hranách. Lepší `--no-text` než ošklivé okraje.
- Komunikuj česky.
- Když uživatel dá víc bannerů, zpracuj je popořadě a na konci vypiš seznam vzniklých MP4.

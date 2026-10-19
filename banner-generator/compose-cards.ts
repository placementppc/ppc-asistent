/**
 * Deterministický skladač bannerů „výřezy produktu na barvě" — BEZ obrazové AI.
 *
 * PROČ EXISTUJE: u produktů, jejichž hodnota je v čitelném obsahu (stránky, obal s textem,
 * ukázky, tabulky), se vyplatí otestovat i jednoduchou sazbu, ne jen fotky a AI scény:
 *   Styl A — plné barevné pozadí, nahoře kondenzovaný verzálkový nadpis,
 *            uprostřed 2–4 SKUTEČNÉ výřezy z produktové grafiky (čitelné), dole
 *            řádek „co to je + pro koho".
 *   Styl B — horní 2/3 výřez / ilustrace na přechodu do černé, pod ním malý
 *            podpis značky (logo + název + krátký řádek), spodní třetina černý pruh s nadpisem.
 * AI by produkt překreslila (vymyšlený nebo zrcadlený text). Proto tady AI nekreslí NIC:
 * výřezy jsou ořezy z produktové grafiky klienta, text sází libvips/pango s brandovým
 * fontem z BRAND-MANUAL.md — dokonalá diakritika.
 *
 * Použití (config si založíš sám, vzor typů níže):
 *   npx tsx compose-cards.ts <tvuj-config> [--only=K1,K3] [--format=1080x1080]
 *
 * Config: configs/<tvuj-config>.ts exportuje `CardsConfig` (typy níže).
 */

import * as fs from 'fs';
import * as path from 'path';
import sharp from 'sharp';

// ---------------------------------------------------------------- typy

export type CardFormat = { width: number; height: number; fileSuffix: string };

export const CARD_FORMATS: CardFormat[] = [
  { width: 1080, height: 1080, fileSuffix: '1080x1080' },
  { width: 1080, height: 1350, fileSuffix: '1080x1350' },
];

export type FontSpec = { family: string; file: string; /** pango weight, např. 'bold' — nutné u fontů s jediným řezem (Impact) */ weight?: string };

export type CardSpec = {
  /** Absolutní cesta ke zdrojové grafice produktu. */
  src: string;
  /** Ořez ve zdrojových pixelech (celá karta). */
  crop?: { left: number; top: number; width: number; height: number };
  /** Otočení PO ořezu ve stupních (např. 90, když je zdrojová grafika uložená naležato). */
  rotate?: number;
  /** Šířka karty jako podíl šířky banneru. */
  wPct: number;
  /** Střed karty: x jako podíl šířky banneru, y jako podíl VÝŠKY ZÓNY KARET (0–1). */
  xPct: number;
  yRel: number;
  /** Náklon ve stupních (+ = po směru hodin). */
  tilt?: number;
  /** Zaoblení rohů jako podíl šířky karty (default 0.045). */
  radiusPct?: number;
  /** Volitelný rámeček (barva + tloušťka px) — např. obálka produktu bez vlastního rámu. */
  frame?: { color: string; width: number };
  /** Pořadí vrstev (větší = navrchu). */
  z?: number;
  /** Zjemnění přeškálované malé grafiky. */
  sharpen?: boolean;
};

export type StyleAConcept = {
  id: string;
  slug: string;
  style: 'A';
  /** Barva pozadí (pastel). */
  bg: string;
  /** Barva ručních doodlů (tmavší tón pozadí). */
  doodle: string;
  headline: { lines: string[]; color: string; font: FontSpec; size?: number };
  cards: CardSpec[];
  /** Zvětšení karet ve formátu 4:5 (default 1.16). */
  portraitScale?: number;
  bottom: { lines: string[]; color: string; font: FontSpec; size?: number };
  /** Drobný řádek úplně dole (CTA / doména). */
  footer?: { text: string; color: string; font: FontSpec };
};

export type StyleBConcept = {
  id: string;
  slug: string;
  style: 'B';
  /** Barva horního okraje přechodu (dole vždy černá). */
  topColor: string;
  cards: CardSpec[];
  /**
   * Podpis značky pod výřezy: logo v kroužku + název + krátký řádek (web, slogan).
   * Záměrně bez prvků, které napodobují UI sociálních sítí (odznak ověření apod.).
   */
  badge: {
    /** Cesta k SVG logu. */
    avatarSvg: string;
    /** Volitelný výřez z loga (viewBox), když chceš jen symbol bez textu, např. '0 0 56 56'. */
    avatarViewBox?: string;
    name: string;
    handle: string;
    font: FontSpec;
  };
  headline: {
    /** Řádky; slovo v `keyword` se obarví a podtrhne. */
    lines: string[];
    keyword?: string;
    color: string;
    keywordColor: string;
    font: FontSpec;
    size?: number;
  };
  sub?: { lines: string[]; color: string; font: FontSpec; size?: number };
};

export type CardsConcept = StyleAConcept | StyleBConcept;

export type CardsConfig = {
  outDir: string;
  /** Další složky, kam se hotové PNG zkopírují (např. plocha). */
  copyTo?: string[];
  concepts: CardsConcept[];
};

// ---------------------------------------------------------------- pomocné

function escapeXml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

type Rendered = { buf: Buffer; width: number; height: number };

/** Vyrenderuje pango markup daným fontem; vrací ořezaný RGBA obraz. */
async function renderMarkup(
  markup: string,
  font: FontSpec,
  size: number,
  opts: { width: number; align?: 'centre' | 'left'; lineHeight?: number },
): Promise<Rendered> {
  const spacing = Math.round(size * ((opts.lineHeight ?? 1.08) - 1));
  if (font.weight) markup = `<span weight="${font.weight}">${markup}</span>`;
  const buf = await sharp({
    text: {
      text: markup,
      font: `${font.family} ${size}`,
      fontfile: font.file,
      rgba: true,
      dpi: 72,
      width: opts.width,
      align: opts.align ?? 'centre',
      spacing,
    },
  })
    .png()
    .toBuffer();
  const m = await sharp(buf).metadata();
  return { buf, width: m.width ?? 0, height: m.height ?? 0 };
}

/**
 * Zmenšuje stupeň písma, dokud se nejdelší řádek nevejde do maxWidth.
 * Řádky lámeme ručně (\n), pango nesmí lámat samo — proto měříme na obří šířce.
 */
async function fitMarkup(
  markup: string,
  font: FontSpec,
  startSize: number,
  maxWidth: number,
  opts: { align?: 'centre' | 'left'; lineHeight?: number; minSize?: number } = {},
): Promise<Rendered & { size: number }> {
  let size = startSize;
  const min = opts.minSize ?? Math.round(startSize * 0.55);
  // měření: šířka 6000 → žádné automatické lámání
  let r = await renderMarkup(markup, font, size, { width: 6000, align: opts.align, lineHeight: opts.lineHeight });
  while (r.width > maxWidth && size > min) {
    size = Math.max(min, Math.round(size * Math.min(0.94, maxWidth / r.width)));
    r = await renderMarkup(markup, font, size, { width: 6000, align: opts.align, lineHeight: opts.lineHeight });
  }
  return { ...r, size };
}

function linesToMarkup(lines: string[], color: string, keyword?: string, keywordColor?: string): string {
  return lines
    .map((l) => {
      const esc = escapeXml(l);
      if (keyword && keywordColor && l.includes(keyword)) {
        const k = escapeXml(keyword);
        return esc.replace(
          k,
          `<span foreground="${keywordColor}" underline="single" underline_color="${keywordColor}">${k}</span>`,
        );
      }
      return esc;
    })
    .map((l) => `<span foreground="${color}">${l}</span>`)
    .join('\n');
}

/** Připraví jednu kartu: ořez → resize → zaoblení → rámeček → stín → náklon. */
async function buildCard(card: CardSpec, W: number, scale: number): Promise<{ buf: Buffer; width: number; height: number }> {
  let img = sharp(card.src).ensureAlpha();
  if (card.crop) img = img.extract(card.crop);
  if (card.rotate) img = sharp(await img.rotate(card.rotate).png().toBuffer()).ensureAlpha();
  const targetW = Math.round(W * card.wPct * scale);
  let cardBuf = await img.resize({ width: targetW, kernel: 'lanczos3' }).png().toBuffer();
  if (card.sharpen) cardBuf = await sharp(cardBuf).sharpen({ sigma: 0.8 }).png().toBuffer();
  const meta = await sharp(cardBuf).metadata();
  const cw = meta.width ?? targetW;
  const ch = meta.height ?? targetW;
  const r = Math.round(cw * (card.radiusPct ?? 0.045));

  // zaoblené rohy
  const mask = Buffer.from(
    `<svg width="${cw}" height="${ch}" xmlns="http://www.w3.org/2000/svg"><rect width="${cw}" height="${ch}" rx="${r}" ry="${r}" fill="#fff"/></svg>`,
  );
  cardBuf = await sharp(cardBuf).composite([{ input: mask, blend: 'dest-in' }]).png().toBuffer();

  if (card.frame) {
    const fw = card.frame.width;
    const frame = Buffer.from(
      `<svg width="${cw}" height="${ch}" xmlns="http://www.w3.org/2000/svg"><rect x="${fw / 2}" y="${fw / 2}" width="${cw - fw}" height="${ch - fw}" rx="${r}" ry="${r}" fill="none" stroke="${card.frame.color}" stroke-width="${fw}"/></svg>`,
    );
    cardBuf = await sharp(cardBuf).composite([{ input: frame }]).png().toBuffer();
  }

  // stín: měkký, mírně dolů — karta „leží" na papíře
  const pad = Math.round(cw * 0.12);
  const canvasW = cw + pad * 2;
  const canvasH = ch + pad * 2;
  const shadowSvg = Buffer.from(
    `<svg width="${canvasW}" height="${canvasH}" xmlns="http://www.w3.org/2000/svg"><rect x="${pad}" y="${pad + Math.round(ch * 0.03)}" width="${cw}" height="${ch}" rx="${r}" ry="${r}" fill="#000" fill-opacity="0.28"/></svg>`,
  );
  const shadow = await sharp(shadowSvg).blur(Math.max(6, Math.round(cw * 0.035))).png().toBuffer();

  let out = await sharp({ create: { width: canvasW, height: canvasH, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: shadow, left: 0, top: 0 }, { input: cardBuf, left: pad, top: pad }])
    .png()
    .toBuffer();

  if (card.tilt) {
    out = await sharp(out).rotate(card.tilt, { background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer();
  }
  const m = await sharp(out).metadata();
  return { buf: out, width: m.width ?? canvasW, height: m.height ?? canvasH };
}

/** Ruční doodly do rohů — scrappy-authentic, ne korporát. Deterministické, bez náhody. */
function doodleSvg(W: number, H: number, color: string): Buffer {
  const s = W / 1080;
  const star = (cx: number, cy: number, r: number, rot = 0) => {
    const pts: string[] = [];
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI / 4) * i + rot;
      const rr = i % 2 === 0 ? r : r * 0.42;
      pts.push(`${(cx + Math.cos(a) * rr).toFixed(1)},${(cy + Math.sin(a) * rr).toFixed(1)}`);
    }
    return `<polygon points="${pts.join(' ')}" fill="none" stroke="${color}" stroke-width="${(5 * s).toFixed(1)}" stroke-linejoin="round"/>`;
  };
  const squiggle = (x: number, y: number, len: number) =>
    `<path d="M${x} ${y} q ${len / 8} -${len / 6} ${len / 4} 0 t ${len / 4} 0 t ${len / 4} 0 t ${len / 4} 0" fill="none" stroke="${color}" stroke-width="${(5 * s).toFixed(1)}" stroke-linecap="round"/>`;
  const dots = (x: number, y: number) =>
    [0, 1, 2].map((i) => `<circle cx="${x + i * 26 * s}" cy="${y + (i % 2) * 10 * s}" r="${(6 * s).toFixed(1)}" fill="${color}"/>`).join('');
  const svg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg" opacity="0.55">
    ${star(46 * s, 44 * s, 14 * s, 0.3)}
    ${star(W - 46 * s, 40 * s, 11 * s, 0.9)}
    ${squiggle(W - 250 * s, H - 56 * s, 170 * s)}
    ${dots(56 * s, H - 76 * s)}
    ${star(W - 60 * s, H * 0.46, 12 * s, 0.5)}
    ${star(52 * s, H * 0.52, 10 * s, 1.1)}
  </svg>`;
  return Buffer.from(svg);
}

/** Podpis značky: logo v kroužku + název + krátký řádek. Neutrální, nenapodobuje UI platformy. */
async function buildBadge(
  badge: StyleBConcept['badge'],
  W: number,
): Promise<Rendered> {
  const s = W / 1080;
  const av = Math.round(96 * s);
  const svgSrc = fs.readFileSync(badge.avatarSvg, 'utf-8');
  // volitelně jen část loga (symbol bez textu) — podle avatarViewBox z configu
  const avatarSvg = badge.avatarViewBox
    ? svgSrc
        .replace(/viewBox="[^"]*"/, `viewBox="${badge.avatarViewBox}"`)
        .replace(/<text[\s\S]*?<\/text>/g, '')
    : svgSrc;
  const avatarBuf = await sharp(Buffer.from(avatarSvg)).resize(av, av).png().toBuffer();
  const ring = Buffer.from(
    `<svg width="${av + 12}" height="${av + 12}" xmlns="http://www.w3.org/2000/svg"><circle cx="${(av + 12) / 2}" cy="${(av + 12) / 2}" r="${av / 2 + 4}" fill="none" stroke="#FFFFFF" stroke-width="3"/></svg>`,
  );
  const avatarRing = await sharp({ create: { width: av + 12, height: av + 12, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: avatarBuf, left: 6, top: 6 }, { input: ring }])
    .png()
    .toBuffer();

  const name = await renderMarkup(`<span foreground="#FFFFFF" weight="bold">${escapeXml(badge.name)}</span>`, badge.font, Math.round(34 * s), { width: 2000, align: 'left' });
  const handle = await renderMarkup(`<span foreground="#B9B9B9">${escapeXml(badge.handle)}</span>`, badge.font, Math.round(28 * s), { width: 2000, align: 'left' });
  const gap = Math.round(20 * s);
  const textW = Math.max(name.width, handle.width);
  const totalW = av + 12 + gap + textW;
  const totalH = Math.max(av + 12, name.height + handle.height + Math.round(6 * s));
  const textTop = Math.round((totalH - (name.height + handle.height + 6 * s)) / 2);
  const out = await sharp({ create: { width: totalW, height: totalH, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([
      { input: avatarRing, left: 0, top: Math.round((totalH - av - 12) / 2) },
      { input: name.buf, left: av + 12 + gap, top: textTop },
      { input: handle.buf, left: av + 12 + gap, top: textTop + name.height + Math.round(6 * s) },
    ])
    .png()
    .toBuffer();
  return { buf: out, width: totalW, height: totalH };
}

// ---------------------------------------------------------------- styl A

async function composeStyleA(c: StyleAConcept, f: CardFormat): Promise<Buffer> {
  const { width: W, height: H } = f;
  const portrait = H > W;
  const s = W / 1080;
  const margin = Math.round(W * 0.06);

  // 1) pozadí + doodly
  let canvas = await sharp({ create: { width: W, height: H, channels: 4, background: c.bg } })
    .composite([{ input: doodleSvg(W, H, c.doodle) }])
    .png()
    .toBuffer();

  // 2) nadpis nahoře — kondenzované verzálky, vždy se vejde
  const hl = await fitMarkup(linesToMarkup(c.headline.lines, c.headline.color), c.headline.font, Math.round((c.headline.size ?? 124) * s), W - margin * 2, { lineHeight: 1.0 });
  const hlTop = Math.round(H * (portrait ? 0.05 : 0.055));

  // 3) spodní řádek „co to je + pro koho"
  const bt = await fitMarkup(linesToMarkup(c.bottom.lines, c.bottom.color), c.bottom.font, Math.round((c.bottom.size ?? 46) * s), W - margin * 2, { lineHeight: 1.12 });
  const footer = c.footer
    ? await renderMarkup(`<span foreground="${c.footer.color}">${escapeXml(c.footer.text)}</span>`, c.footer.font, Math.round(26 * s), { width: W })
    : null;
  const footerH = footer ? footer.height + Math.round(H * 0.02) : 0;
  const btTop = H - Math.round(H * 0.045) - footerH - bt.height;

  // 4) zóna karet mezi nadpisem a spodním textem
  const zoneTop = hlTop + hl.height + Math.round(H * 0.035);
  const zoneBottom = btTop - Math.round(H * 0.03);
  const zoneH = zoneBottom - zoneTop;
  const cardScale = portrait ? (c.portraitScale ?? 1.16) : 1;

  const layers: sharp.OverlayOptions[] = [];
  const cards = [...c.cards].sort((a, b) => (a.z ?? 0) - (b.z ?? 0));
  for (const card of cards) {
    const built = await buildCard(card, W, cardScale);
    const cx = Math.round(W * card.xPct);
    const cy = Math.round(zoneTop + zoneH * card.yRel);
    layers.push({ input: built.buf, left: cx - Math.round(built.width / 2), top: cy - Math.round(built.height / 2) });
  }
  canvas = await sharp(canvas).composite(layers).png().toBuffer();

  const textLayers: sharp.OverlayOptions[] = [
    { input: hl.buf, left: Math.round((W - hl.width) / 2), top: hlTop },
    { input: bt.buf, left: Math.round((W - bt.width) / 2), top: btTop },
  ];
  if (footer) textLayers.push({ input: footer.buf, left: Math.round((W - footer.width) / 2), top: H - Math.round(H * 0.03) - footer.height });
  return sharp(canvas).composite(textLayers).png().toBuffer();
}

// ---------------------------------------------------------------- styl B

async function composeStyleB(c: StyleBConcept, f: CardFormat): Promise<Buffer> {
  const { width: W, height: H } = f;
  const portrait = H > W;
  const s = W / 1080;
  const margin = Math.round(W * 0.06);

  // 1) přechod: světlý vršek → černá od ~60 % výšky
  const bg = Buffer.from(`<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${c.topColor}"/>
      <stop offset="0.30" stop-color="${c.topColor}"/>
      <stop offset="0.62" stop-color="#0A0A0A"/>
      <stop offset="1" stop-color="#000000"/>
    </linearGradient></defs>
    <rect width="${W}" height="${H}" fill="url(#g)"/></svg>`);
  let canvas = await sharp(bg).png().toBuffer();

  // 2) karty v horní části
  const zoneTop = Math.round(H * 0.05);
  const zoneH = Math.round(H * (portrait ? 0.50 : 0.46));
  const layers: sharp.OverlayOptions[] = [];
  const cards = [...c.cards].sort((a, b) => (a.z ?? 0) - (b.z ?? 0));
  for (const card of cards) {
    const built = await buildCard(card, W, portrait ? 1.12 : 1);
    const cx = Math.round(W * card.xPct);
    const cy = Math.round(zoneTop + zoneH * card.yRel);
    layers.push({ input: built.buf, left: cx - Math.round(built.width / 2), top: cy - Math.round(built.height / 2) });
  }
  canvas = await sharp(canvas).composite(layers).png().toBuffer();

  // 3) podpis značky
  const badge = await buildBadge(c.badge, W);
  const badgeTop = zoneTop + zoneH + Math.round(H * 0.035);

  // 4) nadpis na černé + podřádek
  const hl = await fitMarkup(
    linesToMarkup(c.headline.lines, c.headline.color, c.headline.keyword, c.headline.keywordColor),
    c.headline.font,
    Math.round((c.headline.size ?? 78) * s),
    W - margin * 2,
    { lineHeight: 1.1 },
  );
  const hlTop = badgeTop + badge.height + Math.round(H * 0.05);
  const textLayers: sharp.OverlayOptions[] = [
    { input: badge.buf, left: Math.round((W - badge.width) / 2), top: badgeTop },
    { input: hl.buf, left: Math.round((W - hl.width) / 2), top: hlTop },
  ];
  if (c.sub) {
    const sub = await fitMarkup(linesToMarkup(c.sub.lines, c.sub.color), c.sub.font, Math.round((c.sub.size ?? 36) * s), W - margin * 2, { lineHeight: 1.15 });
    textLayers.push({ input: sub.buf, left: Math.round((W - sub.width) / 2), top: hlTop + hl.height + Math.round(H * 0.03) });
  }
  return sharp(canvas).composite(textLayers).png().toBuffer();
}

// ---------------------------------------------------------------- main

async function main() {
  const args = process.argv.slice(2);
  const configName = args.find((a) => !a.startsWith('--'));
  if (!configName) {
    console.error('Použití: npx tsx compose-cards.ts <config> [--only=K1,K3] [--format=1080x1080]');
    process.exit(1);
  }
  const onlyArg = args.find((a) => a.startsWith('--only='))?.split('=')[1];
  const formatArg = args.find((a) => a.startsWith('--format='))?.split('=')[1];
  const only = onlyArg ? onlyArg.split(',').map((x) => x.trim().toUpperCase()) : null;

  const configPath = path.resolve('configs', `${configName}.ts`);
  if (!fs.existsSync(configPath)) {
    console.error(`Config nenalezen: ${configPath}`);
    process.exit(1);
  }
  const config = ((await import(configPath)) as { default: CardsConfig }).default;
  const outDir = path.resolve(config.outDir);
  fs.mkdirSync(outDir, { recursive: true });
  for (const d of config.copyTo ?? []) fs.mkdirSync(d, { recursive: true });

  const concepts = only ? config.concepts.filter((c) => only.includes(c.id)) : config.concepts;
  const formats = formatArg ? CARD_FORMATS.filter((f) => f.fileSuffix === formatArg) : CARD_FORMATS;

  console.log(`🃏 compose-cards — bez AI, reálné výřezy produktu + sazba kódem`);
  console.log(`   Výstup: ${outDir}`);
  console.log(`   Koncepty: ${concepts.map((c) => c.id).join(', ')} · Formáty: ${formats.map((f) => f.fileSuffix).join(', ')}\n`);

  let ok = 0;
  let failed = 0;
  for (const c of concepts) {
    for (const f of formats) {
      const fileName = `${c.slug}_banner_${f.fileSuffix}.png`;
      try {
        const buf = c.style === 'A' ? await composeStyleA(c, f) : await composeStyleB(c, f);
        fs.writeFileSync(path.join(outDir, fileName), buf);
        for (const d of config.copyTo ?? []) fs.writeFileSync(path.join(d, fileName), buf);
        console.log(`   ✅ ${fileName} (${Math.round(buf.length / 1024)} KB)`);
        ok++;
      } catch (e: any) {
        console.error(`   ❌ ${fileName}: ${e?.message ?? e}`);
        failed++;
      }
    }
  }
  console.log(`\n📊 Hotovo: ${ok} úspěch / ${failed} selhání`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

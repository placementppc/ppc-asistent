/**
 * Dvouvrstvý render — deterministické skládání textu a loga přes sharp/SVG.
 *
 * AI (Gemini) generuje POUZE obraz (pozadí + produkt). Nadpis, cenu a logo skládá
 * tenhle modul po generování na přesných pixelech v safe zoně — perfektní česká
 * diakritika, žádné AI komolení, žádné zdeformované logo.
 */

import sharp from 'sharp';
import type { LogoSpec, TextOverlay } from '../banner-formats';
import { layoutTextBlock } from './brand-font';

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Vyrenderuje jeden textový overlay a složí ho na banner.
 *  - S `fontFile`: obrysy písmen přímo ze souboru fontu jako vektor (poloha = TOP textu).
 *  - Bez `fontFile`: SVG se systémovým fontem (poloha = ÚČARÍ / baseline prvního řádku).
 */
export async function compositeText(
  bannerBuf: Buffer,
  ov: TextOverlay,
): Promise<Buffer> {
  const banner = sharp(bannerBuf);
  const { width: W = 0, height: H = 0 } = await banner.metadata();

  // --- Větev A: přesný brandový font ze souboru (vektorové cesty, lib/brand-font.ts) ---
  if (ov.fontFile) {
    const anchor = ov.anchor ?? 'start';
    const color = ov.color ?? '#ffffff';

    const block = layoutTextBlock({ ...ov, fontFile: ov.fontFile });
    if (!block) return bannerBuf;

    // Vodorovná poloha bloku podle SKUTEČNÉ šířky textu a kotvy (xPct = poloha kotvy).
    const tw = Math.round(block.width);
    const th = Math.round(block.height);
    const anchorX = Math.round(W * ov.xPct);
    let left = anchorX; // 'start' → levá hrana na xPct
    if (anchor === 'middle') left = anchorX - Math.round(tw / 2);
    else if (anchor === 'end') left = anchorX - tw;

    const top = Math.round(H * ov.yPct);

    // Text přes celé plátno: co přeteče přes okraj, se ořízne (sharp nesloží vrstvu větší než banner).
    const textBuf = Buffer.from(
      `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">` +
        `<g transform="translate(${left} ${top})" fill="${escapeXml(color)}">` +
        block.paths.map(d => `<path d="${d}"/>`).join('') +
        `</g></svg>`,
    );

    // Plný pruh pod textem — kreslí se PŘED textem, aby písmo zůstalo ostré.
    if (ov.band) {
      const padX = Math.round(W * (ov.band.padXPct ?? 0.045));
      const padY = Math.round(H * (ov.band.padYPct ?? 0.028));
      const bandLeft = ov.band.fullWidth ? 0 : Math.max(0, left - padX);
      const bandW = ov.band.fullWidth ? W : Math.min(W - bandLeft, tw + padX * 2);
      let bandTop = Math.max(0, top - padY);
      let bandH = Math.min(H - bandTop, th + padY * 2);
      if (ov.band.toEdge === 'bottom') bandH = H - bandTop;
      else if (ov.band.toEdge === 'top') { bandH = bandTop + bandH; bandTop = 0; }
      const rect = Buffer.from(
        `<svg width="${bandW}" height="${bandH}" xmlns="http://www.w3.org/2000/svg">` +
          `<rect width="${bandW}" height="${bandH}" fill="${ov.band.color}" ` +
          `fill-opacity="${ov.band.opacity ?? 1}"/></svg>`,
      );
      return banner
        .composite([
          { input: rect, left: bandLeft, top: bandTop },
          { input: textBuf, left: 0, top: 0 },
        ])
        .png()
        .toBuffer();
    }

    return banner.composite([{ input: textBuf, left: 0, top: 0 }]).png().toBuffer();
  }

  // --- Větev B: systémový font přes SVG ---
  const x = Math.round(W * ov.xPct);
  const y0 = Math.round(H * ov.yPct);
  const lh = ov.fontSize * (ov.lineHeight ?? 1.15);
  const anchor = ov.anchor ?? 'start';
  const color = ov.color ?? '#ffffff';
  const weight = ov.weight ?? 800;
  const family = ov.fontFamily ?? 'Arial, "Helvetica Neue", sans-serif';

  const tspans = ov.lines
    .map(
      (line, i) =>
        `<text x="${x}" y="${Math.round(y0 + i * lh)}" text-anchor="${anchor}" ` +
        `font-family='${family}' font-size="${ov.fontSize}" font-weight="${weight}" ` +
        `fill="${color}">${escapeXml(line)}</text>`,
    )
    .join('');

  const svg = Buffer.from(
    `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${tspans}</svg>`,
  );
  return banner.composite([{ input: svg, top: 0, left: 0 }]).png().toBuffer();
}

/** Složí logo na hotový banner na přesných pixelech (respektuje safe zone dole). */
export async function compositeLogo(
  bannerBuf: Buffer,
  logo: LogoSpec,
  isStories: boolean, // 1080×1920 → přísnější spodní safe limit
): Promise<Buffer> {
  const banner = sharp(bannerBuf);
  const { width: W = 0, height: H = 0 } = await banner.metadata();

  const pad = logo.padding ?? 40;
  const targetW = Math.round(W * (logo.widthPct ?? 0.22));
  const logoBuf = await sharp(logo.path).resize({ width: targetW }).png().toBuffer();
  const { width: lw = 0, height: lh = 0 } = await sharp(logoBuf).metadata();

  // Spodní hranice: u Stories nelez pod ~82 % výšky (Instagram UI + safe zone).
  const bottomSafe = isStories ? Math.round(H * 0.82) : H - pad;

  const pos = logo.position ?? 'bottom-left';
  let left = pad;
  let top = bottomSafe - lh;
  if (pos.includes('center')) left = Math.round((W - lw) / 2);
  if (pos.includes('right')) left = W - lw - pad;
  if (pos.startsWith('top')) top = isStories ? Math.round(H * 0.18) : pad;

  return banner.composite([{ input: logoBuf, left, top }]).png().toBuffer();
}

/** Tmavý lineární přechod u horního nebo dolního okraje — podklad pro čitelnost textu.
 *  Kreslí se PŘED textem, takže text zůstane ostrý navrchu. */
async function compositeScrim(
  bannerBuf: Buffer,
  scrim: NonNullable<TextOverlay['scrim']>,
): Promise<Buffer> {
  const { width: W = 0, height: H = 0 } = await sharp(bannerBuf).metadata();
  const bandH = Math.round(H * scrim.heightPct);
  if (bandH <= 0) return bannerBuf;

  const opacity = scrim.opacity ?? 0.75;
  const fromTop = scrim.from === 'top';
  // Krytí nabíhá od okraje dovnitř: u okraje `opacity`, na vnitřní hraně 0.
  const stops = fromTop
    ? `<stop offset="0%" stop-color="#000" stop-opacity="${opacity}"/><stop offset="100%" stop-color="#000" stop-opacity="0"/>`
    : `<stop offset="0%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="${opacity}"/>`;

  const svg = `<svg width="${W}" height="${bandH}" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">${stops}</linearGradient></defs>
    <rect width="${W}" height="${bandH}" fill="url(#g)"/>
  </svg>`;

  return sharp(bannerBuf)
    .composite([{ input: Buffer.from(svg), left: 0, top: fromTop ? 0 : H - bandH }])
    .png()
    .toBuffer();
}

/** Postprocessing hotového banneru: nejdřív texty, logo naposled (navrchu). */
export async function applyOverlays(
  bannerBuf: Buffer,
  opts: { overlays?: TextOverlay[]; logo?: LogoSpec; isStories: boolean },
): Promise<Buffer> {
  let out = bannerBuf;
  for (const ov of opts.overlays ?? []) {
    if (ov.scrim) out = await compositeScrim(out, ov.scrim);
    out = await compositeText(out, ov);
  }
  if (opts.logo) {
    out = await compositeLogo(out, opts.logo, opts.isStories);
  }
  return out;
}

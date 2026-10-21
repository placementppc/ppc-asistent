/**
 * Brandový font (`fontFile`) se opravdu použije.
 *
 * Dřív sharp/libvips soubor písma tiše ignoroval (fontconfig) a text vysázel náhradním
 * písmem: render s Mulish byl bajtově shodný s 'sans-serif'. Test proto porovnává tvar
 * písmen — náš render proti systémovému písmu a proti nezávislé sazbě téhož fontu v Chromu.
 *
 *   npm --prefix banner-generator test
 *
 * Mulish (fixtures/) je z Google Fonts pod licencí SIL OFL 1.1, viz fixtures/Mulish-OFL.txt.
 */
import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import sharp from 'sharp';
import puppeteer, { type Browser } from 'puppeteer';
import type { TextOverlay } from '../banner-formats';
import { compositeText } from '../lib/compose-overlays';

const FONT = path.join(__dirname, 'fixtures', 'Mulish-VF.ttf');
const TEXT = 'Příliš žluťoučký kůň';
const SIZE = 74;

type Mask = { w: number; h: number; px: Uint8Array; ink: number };

/** Tmavé pixely (inkoust) oříznuté na svůj obdélník. */
async function inkMask(png: Buffer | Uint8Array): Promise<Mask> {
  const { data, info } = await sharp(png)
    .flatten({ background: '#ffffff' })
    .greyscale()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const W = info.width;
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  for (let i = 0; i < data.length; i++) {
    if (data[i] < 128) {
      const x = i % W, y = Math.floor(i / W);
      x0 = Math.min(x0, x); x1 = Math.max(x1, x);
      y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  assert.ok(x1 >= 0, 'render neobsahuje žádný text');
  const w = x1 - x0 + 1, h = y1 - y0 + 1;
  const px = new Uint8Array(w * h);
  let ink = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (data[(y0 + y) * W + x0 + x] < 128) { px[y * w + x] = 1; ink++; }
    }
  }
  return { w, h, px, ink };
}

/** Leží v masce `m` inkoust do 1 px od bodu (x, y)? */
function inkNear(m: Mask, x: number, y: number): boolean {
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const xx = x + dx, yy = y + dy;
      if (xx >= 0 && yy >= 0 && xx < m.w && yy < m.h && m.px[yy * m.w + xx]) return true;
    }
  }
  return false;
}

/**
 * Shoda tvaru 0–1: podíl inkoustu obou masek, který má protějšek v té druhé do 1 px
 * (masky zarovnané levým horním rohem). Tolerance 1 px pokryje rozdílné vyhlazování
 * hran — Chrome na Macu kreslí písmo o chlup tučněji. Stejné písmo ≈ 0,95–1, jiné ≈ 0,5–0,7.
 */
function shoda(a: Mask, b: Mask): number {
  let hit = 0;
  for (const [m, other] of [[a, b], [b, a]] as const) {
    for (let y = 0; y < m.h; y++) {
      for (let x = 0; x < m.w; x++) {
        if (m.px[y * m.w + x] && inkNear(other, x, y)) hit++;
      }
    }
  }
  return hit / (a.ink + b.ink);
}

/** Náš render: černý text na bílém plátně přes compositeText (obě větve). */
async function ours(extra: Partial<TextOverlay>): Promise<Buffer> {
  const canvas = await sharp({
    create: { width: 1200, height: 260, channels: 3, background: '#ffffff' },
  }).png().toBuffer();
  return compositeText(canvas, {
    lines: [TEXT], xPct: 0.05, yPct: 0.3, fontSize: SIZE, color: '#000000', weight: 800, ...extra,
  });
}

let browser: Browser | null = null;
before(async () => {
  try {
    browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--font-render-hinting=none'] });
  } catch (err) {
    console.warn(`Chrome (puppeteer) nejde spustit, srovnání s Chromem se přeskočí: ${err}`);
  }
});
after(async () => { await browser?.close(); });

/** Nezávislá sazba v Chromu: @font-face ze stejného souboru, nebo systémový sans-serif. */
async function chrome(font: 'brand' | 'sans-serif', weight: number): Promise<Uint8Array> {
  const page = await browser!.newPage();
  try {
    const b64 = fs.readFileSync(FONT).toString('base64');
    const family = font === 'brand' ? 'Brand' : 'sans-serif';
    await page.setContent(`<!doctype html><style>
      @font-face { font-family: Brand; src: url(data:font/ttf;base64,${b64}); font-weight: 1 1000; }
      html, body { margin: 0; background: #fff; }
      #t { display: inline-block; padding: 40px; color: #000; white-space: pre;
           font: ${weight} ${SIZE}px/1 ${family}; font-synthesis: none; }
    </style><div id="t"></div>`);
    await page.$eval('#t', (el, text) => { el.textContent = text as string; }, TEXT);
    await page.evaluate(() => document.fonts.ready);
    const el = await page.$('#t');
    return await el!.screenshot();
  } finally {
    await page.close();
  }
}

test('s fontFile vyjde jiné písmo než systémový sans-serif', async () => {
  const brand = await ours({ fontFile: FONT, fontFamily: 'Mulish' });
  const system = await ours({ fontFamily: 'sans-serif' });
  assert.notDeepEqual(brand, system);
  const s = shoda(await inkMask(brand), await inkMask(system));
  assert.ok(s < 0.8, `Mulish a sans-serif mají skoro stejný tvar (shoda ${s.toFixed(2)})`);
});

test('variabilní font: weight nastaví osu wght', async () => {
  const tucne = await inkMask(await ours({ fontFile: FONT, weight: 800 }));
  const normal = await inkMask(await ours({ fontFile: FONT, weight: 'normal' }));
  assert.ok(tucne.ink > normal.ink * 1.3, `800 má ${tucne.ink} px inkoustu, 400 jen ${normal.ink}`);
});

test('tvar písmen odpovídá Mulish v Chromu (včetně ř ž č ů ť)', async t => {
  if (!browser) return t.skip('Chrome není k dispozici');
  for (const weight of [800, 400]) {
    const nas = await inkMask(await ours({ fontFile: FONT, weight }));
    const mulish = await inkMask(await chrome('brand', weight));
    const sans = await inkMask(await chrome('sans-serif', weight));
    const sMulish = shoda(nas, mulish);
    const sSans = shoda(nas, sans);
    assert.ok(
      Math.abs(nas.w - mulish.w) <= 3 && Math.abs(nas.h - mulish.h) <= 3,
      `váha ${weight}: rozměr textu ${nas.w}×${nas.h}, Chrome ${mulish.w}×${mulish.h}`,
    );
    assert.ok(sMulish > 0.9, `váha ${weight}: shoda s Mulish v Chromu jen ${sMulish.toFixed(2)}`);
    assert.ok(sMulish > sSans + 0.2, `váha ${weight}: Mulish ${sMulish.toFixed(2)} vs. sans-serif ${sSans.toFixed(2)}`);
  }
});

test('chybějící znak ve fontu vypíše varování', async t => {
  const warn = t.mock.method(console, 'warn', () => {});
  await ours({ fontFile: FONT, lines: ['Šipka →'] });
  assert.ok(
    warn.mock.calls.some(c => String(c.arguments[0]).includes('U+2192')),
    'chybí varování pro znak →',
  );
});

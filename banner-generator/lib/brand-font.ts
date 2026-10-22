/**
 * Brandový font ze souboru → text jako vektorové cesty (SVG <path>).
 *
 * Proč ne libvips `fontfile`: sharp při nenačteném fontconfigu („Fontconfig error: Cannot
 * load default config file") soubor písma tiše ignoruje a vysází text náhradním písmem.
 * Obrysy písmen proto čteme přímo z .ttf/.otf přes fontkit (čistý JavaScript — Mac
 * i Windows bez systémových knihoven) a librsvg je vykreslí jako obyčejné tvary.
 * Žádné hledání písma v systému, žádná tichá náhrada.
 */

import * as fontkit from 'fontkit';
import type { Font, FontCollection, Path } from 'fontkit';

/** Slovní váhy, jak je znala původní sazba přes Pango, plus běžné názvy řezů. */
const WEIGHT_NAMES: Record<string, number> = {
  thin: 100, hairline: 100,
  ultralight: 200, extralight: 200,
  light: 300,
  normal: 400, regular: 400, book: 400,
  medium: 500,
  semibold: 600, demibold: 600,
  bold: 700,
  ultrabold: 800, extrabold: 800,
  heavy: 900, black: 900,
  ultraheavy: 1000, extrablack: 1000,
};

export function weightToNumber(weight: number | string | undefined): number {
  if (weight === undefined) return 800;
  if (typeof weight === 'number') return weight;
  const w = weight.trim().toLowerCase().replace(/[\s_-]/g, '');
  if (/^\d+$/.test(w)) return Number(w);
  return WEIGHT_NAMES[w] ?? 400;
}

const warned = new Set<string>();
function warnOnce(msg: string): void {
  if (warned.has(msg)) return;
  warned.add(msg);
  console.warn(msg);
}

const fonts = new Map<string, Font>();

/**
 * Načte písmo pro danou váhu. Variabilní font dostane osu `wght` podle `weight`
 * (ořízne se na rozsah fontu), statický soubor se použije tak, jak je.
 */
function loadFont(file: string, weight: number, family?: string): Font {
  const key = `${file}|${weight}|${family ?? ''}`;
  const cached = fonts.get(key);
  if (cached) return cached;

  const opened = fontkit.openSync(file) as Font | FontCollection;
  let font: Font;
  if ('fonts' in opened) {
    // .ttc / .dfont: řez s požadovanou rodinou a nejbližší váhou
    const sameFamily = opened.fonts.filter(f => !family || f.familyName.startsWith(family));
    const pool = sameFamily.length ? sameFamily : opened.fonts;
    font = pool.reduce((best, f) =>
      Math.abs(f['OS/2'].usWeightClass - weight) < Math.abs(best['OS/2'].usWeightClass - weight) ? f : best,
    );
  } else {
    font = opened;
  }

  const wght = font.variationAxes?.wght;
  if (wght) {
    font = font.getVariation({ wght: Math.min(wght.max, Math.max(wght.min, weight)) });
  } else if (Math.abs(font['OS/2'].usWeightClass - weight) > 100) {
    warnOnce(
      `   ⚠️  ${file}: statický řez s váhou ${font['OS/2'].usWeightClass}, požadováno ${weight} — ` +
        'pro jinou váhu nastav fontFile na soubor toho řezu.',
    );
  }

  fonts.set(key, font);
  return font;
}

export type TextBlock = {
  /** Jedna SVG cesta na písmeno; souřadnice v px, levý horní roh inkoustu = (0, 0). */
  paths: string[];
  /** Rozměr inkoustu (skutečně vybarvené plochy) celého bloku v px. */
  width: number;
  height: number;
  /** Vzdálenost od horní hrany inkoustu k účaří prvního řádku (px). */
  baseline: number;
};

/**
 * Vysází řádky brandovým písmem. Řádky se zarovnají podle `anchor` (po šířce kroku,
 * stejně jako dřív Pango), účaří jsou od sebe `fontSize × lineHeight`. Výsledek je
 * oříznutý na inkoust, takže `top`/`left` při skládání = horní/levá hrana písma.
 * Vrátí null, když není co kreslit (prázdný text).
 */
export function layoutTextBlock(opts: {
  lines: string[];
  fontFile: string;
  fontSize: number;
  lineHeight?: number;
  weight?: number | string;
  fontFamily?: string;
  anchor?: 'start' | 'middle' | 'end';
  letterSpacing?: number; // prostrkání v em (−0.02 = sevřený nadpis, 0.1 = kapitálky)
}): TextBlock | null {
  const font = loadFont(opts.fontFile, weightToNumber(opts.weight), opts.fontFamily);
  const scale = opts.fontSize / font.unitsPerEm;
  const lineStep = opts.fontSize * (opts.lineHeight ?? 1.15);
  const anchor = opts.anchor ?? 'start';
  const track = (opts.letterSpacing ?? 0) * opts.fontSize;

  const outlines: Path[] = [];
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

  opts.lines.forEach((line, i) => {
    for (const ch of line) {
      const cp = ch.codePointAt(0)!;
      if (!/\s/.test(ch) && !font.hasGlyphForCodePoint(cp)) {
        warnOnce(
          `   ⚠️  ${opts.fontFile}: písmo nemá znak „${ch}“ (U+${cp.toString(16).toUpperCase().padStart(4, '0')}) ` +
            '— v banneru by byl prázdný čtvereček. Uprav text nebo použij jiný soubor písma.',
        );
      }
    }

    const run = font.layout(line);
    const advance = run.advanceWidth * scale + track * Math.max(0, run.glyphs.length - 1);
    let penX = anchor === 'middle' ? -advance / 2 : anchor === 'end' ? -advance : 0;
    const baseline = i * lineStep;

    run.glyphs.forEach((glyph, g) => {
      const pos = run.positions[g];
      if (glyph.path.commands.length > 0) {
        // font má osu Y nahoru, SVG dolů → převrátit a posunout na pero
        const path = glyph.path
          .scale(scale, -scale)
          .translate(penX + pos.xOffset * scale, baseline - pos.yOffset * scale);
        const bb = path.bbox;
        minX = Math.min(minX, bb.minX); minY = Math.min(minY, bb.minY);
        maxX = Math.max(maxX, bb.maxX); maxY = Math.max(maxY, bb.maxY);
        outlines.push(path);
      }
      penX += pos.xAdvance * scale + track;
    });
  });

  if (!outlines.length) return null;
  return {
    paths: outlines.map(p => p.translate(-minX, -minY).toSVG()),
    width: maxX - minX,
    height: maxY - minY,
    baseline: -minY,
  };
}

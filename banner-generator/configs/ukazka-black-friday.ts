/**
 * UKÁZKA BLACK FRIDAY — smyšlená značka „Kávovar Ranní" (stejná jako configs/ukazka.ts).
 *
 * Dva kroky, jeden obrázek z AI:
 *   1. TEST CLAIMŮ (T1–T3): AI vygeneruje obrázek jen jednou (T1). T2 a T3 ho převezmou
 *      (`podklad`) a liší se JEN nadpisem. Čistý A/B test: vyhraje claim, ne obrázek.
 *   2. BLACK FRIDAY (BF1, BF2, V1): vítěz testu dostane skutečnou nabídku a termín.
 *      Zase stejný obrázek, AI se nevolá, nic to nestojí.
 *
 * Spuštění (z kořene appky):
 *   npm --prefix banner-generator run generate:gemini -- ukazka-black-friday --only=T1,T2,T3 --format=1080x1080
 *   … test 5–7 dní v reklamě, vítěze zapiš do VITEZ níž, pak:
 *   npm --prefix banner-generator run generate:gemini -- ukazka-black-friday --only=BF1,BF2,V1 --format=1080x1080
 *
 * Pro vlastního klienta zkopíruj na configs/<klient>-black-friday.ts. Nabídku (NABIDKA) piš
 * jen skutečnou, schválenou klientem. Bez ní si AI ani copywriter nic nevymýšlí.
 */
import * as fs from 'fs';
import * as path from 'path';
import type { Concept, Config, Format, TextOverlay } from '../banner-formats';

const DIR = path.resolve('banners-ukazka');
const PHOTO = path.join(DIR, 'kavovar_transparent.png');
const LOGO = path.join(DIR, 'brand', 'logo.png');
const FONT = path.join(DIR, 'brand', 'fonts', 'Inter-ExtraBold.ttf');

const C = { espresso: '#3B2A20', krem: '#F4ECE0', oranz: '#E8772E', bila: '#FFFFFF' };

// ── 1. Claimy k testu: stejný obrázek, jiný důvod koupit ─────────────────────
// Každý claim jiný úhel: problém zákazníka / přínos / peníze. Ne tři varianty téže věty.
const CLAIMY: Record<string, { nadpis: string[]; uhel: string }> = {
  T1: { nadpis: ['Kafe z automatu?', 'Zase?'], uhel: 'problém zákazníka' },
  T2: { nadpis: ['Espresso doma', 'za minutu'], uhel: 'přínos' },
  T3: { nadpis: ['Levnější než', 'káva cestou'], uhel: 'peníze' },
};

// ── 2. Po testu: vítěz a skutečná nabídka ────────────────────────────────────
const VITEZ = 'T1'; // ← po 5–7 dnech testu sem napiš claim s nejlepší cenou za nákup (ne CTR)
const NABIDKA = {
  sleva: '−20 %',          // jen sleva, kterou klient opravdu vyhlásil
  bfDo: 'do neděle 29. 11.',
  cmText: 'Poslední den',
  vanoce: 'Doručíme do Vánoc',
};

const photoRef = (): string | null => (fs.existsSync(PHOTO) ? PHOTO : null);
const logo = fs.existsSync(LOGO) ? { path: LOGO, position: 'bottom-left' as const, widthPct: 0.2 } : undefined;
const font = fs.existsSync(FONT) ? { fontFile: FONT, fontFamily: 'Inter' } : {};

function pruh(text: string, yPct: number, barva: string, velikost = 38): TextOverlay {
  // `band` (pruh za textem) kreslí jen větev s fontFile; bez fontu aspoň velký barevný text.
  return fs.existsSync(FONT)
    ? { lines: [text], xPct: 0.06, yPct, fontSize: velikost, color: C.bila, weight: 800, ...font,
        band: { color: barva, padXPct: 0.035, padYPct: 0.018 } }
    : { lines: [text], xPct: 0.06, yPct, fontSize: velikost + 6, color: barva, weight: 900 };
}

function nadpis(lines: string[], yPct: number): TextOverlay {
  return { lines, xPct: 0.06, yPct, fontSize: 66, color: C.espresso, weight: 800, ...font };
}

/** Jediný prompt, který jde do AI. Text, cena ani logo v obrázku nejsou. */
function prompt(f: Format): string {
  return `Create an advertising image for Facebook/Instagram.
Exact dimensions: ${f.width}x${f.height} pixels.
PRODUCT: compact home espresso machine in matte dark brown with a small steam wand.
${photoRef() ? 'The attached photo shows the actual product — reproduce its shape, color and label verbatim, background removed.' : ''}
STYLE: realistic lifestyle photo, early morning kitchen counter, warm window light, the machine pouring
a shot into a small cream cup. Calm cream (${C.krem}) and espresso brown (${C.espresso}) tones.
Keep the upper 35% and the bottom 15% calm and uncluttered for text added later.
TECHNICAL RULES:
- DO NOT render any text, logo, button, price, discount or "Black Friday" sign.
- Background extends edge-to-edge, no frames.
- Output exactly ${f.width}x${f.height} pixels.`;
}

const slug = (id: string) => `bf-test-${id.toLowerCase()}`;

// T1 obrázek generuje, T2 a T3 ho převezmou
const test: Concept[] = Object.entries(CLAIMY).map(([id, c], i) => ({
  id,
  slug: slug(id),
  buildPrompt: prompt,
  getReference: photoRef,
  ...(i === 0 ? {} : { podklad: slug('T1') }),
  overlays: [nadpis(c.nadpis, 0.12), pruh('Vybrat kávovar', 0.86, C.oranz)],
  logo,
}));

// Black Friday verze vítěze: stejný obrázek, nahoře nabídka, dole termín
const v = CLAIMY[VITEZ];
const bf: Concept[] = [
  { id: 'BF1', slug: 'bf-blackfriday', overlays: [
      pruh(`BLACK FRIDAY ${NABIDKA.sleva}`, 0.09, C.oranz, 52), nadpis(v.nadpis, 0.21),
      pruh(`Koupit se slevou · ${NABIDKA.bfDo}`, 0.86, C.oranz)] },
  { id: 'BF2', slug: 'bf-cybermonday', overlays: [
      pruh(`${NABIDKA.cmText} ${NABIDKA.sleva}`, 0.09, C.oranz, 52), nadpis(v.nadpis, 0.21),
      pruh('Sleva končí o půlnoci', 0.86, C.oranz)] },
  { id: 'V1', slug: 'bf-vanoce', overlays: [
      pruh(NABIDKA.vanoce, 0.09, C.oranz, 52), nadpis(v.nadpis, 0.21),
      pruh('Vybrat dárek', 0.86, C.oranz)] },
].map(k => ({ ...k, buildPrompt: prompt, getReference: photoRef, podklad: slug(VITEZ), logo }));

const config: Config = {
  outDir: 'banners-ukazka',
  concepts: [...test, ...bf],
};

export default config;

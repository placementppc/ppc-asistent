/**
 * UKÁZKA BLACK FRIDAY — smyšlená značka „Kávovar Ranní" (stejná jako configs/ukazka.ts).
 *
 * 1. TEST CLAIMŮ (T1–T3): 3 RŮZNÉ koncepty. Každý jiná mikro-persona × úhel × styl:
 *    profi lifestyle foto, UGC fotka z mobilu, text na obyčejném pozadí.
 *    NE jeden obrázek s jinými nadpisy: drobné varianty téhož čte Meta (Andromeda) jako jeden
 *    signál a účet stagnuje (BANNER-INSTRUCTIONS.md, pravidla 3, 10 a 12).
 * 2. BLACK FRIDAY (BF1, BF2, V1): vítěz testu se škáluje nabídkou na svém obrázku (BF1, `podklad`,
 *    AI se nevolá). Cyber Monday a Vánoce mají vlastní styl (post-it, dárková fotka).
 *
 * Spuštění (z kořene appky):
 *   npm --prefix banner-generator run generate:gemini -- ukazka-black-friday --only=T1,T2,T3 --format=1080x1350
 *   … test 5–7 dní v reklamě, vítěze zapiš do VITEZ, pak:
 *   npm --prefix banner-generator run generate:gemini -- ukazka-black-friday --only=BF1,BF2,V1 --format=1080x1350
 *
 * Pro vlastního klienta zkopíruj na configs/<klient>-black-friday.ts. Nabídku (NABIDKA) piš jen skutečnou.
 * Kde AI umístí papírek nebo volné místo, se může lišit: polohu textu dolaď přes --relayout (nic nestojí).
 */
import * as fs from 'fs';
import * as path from 'path';
import type { Concept, Config, Format, TextOverlay } from '../banner-formats';
import { nativeStaticStyle, NATIVE_STATIC_RULES } from '../lib/native-static';

const DIR = path.resolve('banners-ukazka');
const PHOTO = path.join(DIR, 'kavovar_transparent.png');
const FONT = path.join(DIR, 'brand', 'fonts', 'Inter-ExtraBold.ttf');
const C = { espresso: '#3B2A20', krem: '#F4ECE0', oranz: '#E8772E', bila: '#FFFFFF' };
const font = fs.existsSync(FONT) ? { fontFile: FONT, fontFamily: 'Inter' } : {};

const VITEZ = 'T1'; // ← po testu claim s nejlepší cenou za nákup (ne CTR)
const NABIDKA = { sleva: '−20 %', termin: 'do neděle 29. 11.' }; // jen skutečná nabídka klienta

const ref = (): string | null => (fs.existsSync(PHOTO) ? PHOTO : null);
const PRODUKT = 'compact home espresso machine in matte dark brown with a small steam wand'
  + ' (if a photo is attached, reproduce it exactly).';
const KONEC = (f: Format) => `TECHNICAL RULES:
- DO NOT render any text, logo, price, discount or button.
- Edge-to-edge, no frames. Output exactly ${f.width}x${f.height} pixels.`;

const pruh = (text: string, yPct: number, bg: string, fg = C.bila, size = 40): TextOverlay =>
  fs.existsSync(FONT)
    ? { lines: [text], xPct: 0.07, yPct, fontSize: size, color: fg, weight: 800, ...font,
        band: { color: bg, padXPct: 0.04, padYPct: 0.02 } }
    : { lines: [text], xPct: 0.07, yPct, fontSize: size + 6, color: bg, weight: 900 };
const nadpis = (lines: string[], yPct: number, color = C.espresso, size = 72): TextOverlay =>
  ({ lines, xPct: 0.07, yPct, fontSize: size, lineHeight: 1.08, color, weight: 800, ...font });
const pod = (lines: string[], yPct: number, color = C.espresso): TextOverlay =>
  ({ lines, xPct: 0.07, yPct, fontSize: 34, lineHeight: 1.25, color, weight: 500, ...font });

// T1 — profi lifestyle foto
// PERSONA: dojíždějící do práce · ÚHEL: pain-point · BUŇKA: dojíždějící × pain-point × designed-static
const T1: Concept = {
  id: 'T1', slug: 'bf-test-t1', getReference: ref,
  buildPrompt: f => `Realistic lifestyle advertising photo, ${f.width}x${f.height} pixels.
PRODUCT: ${PRODUKT}
SCENE: early morning kitchen counter, warm window light, the machine pouring a shot into a small cream cup,
keys and a work bag in soft focus. Cream ${C.krem} and espresso brown ${C.espresso} tones.
COMPOSITION: upper 40% calm and bright for text, bottom 12% calm.
${KONEC(f)}`,
  overlays: [nadpis(['Kafe z automatu', 'chutná jako pondělí?'], 0.08), pruh('Vybrat kávovar', 0.88, C.oranz)],
};

// T2 — UGC fotka z mobilu (native-static NS5)
// PERSONA: začátečník s obavou · ÚHEL: mechanism · BUŇKA: začátečník × mechanism × native-static
const T2: Concept = {
  id: 'T2', slug: 'bf-test-t2', getReference: ref,
  buildPrompt: f => `Image ${f.width}x${f.height} pixels.
${nativeStaticStyle('NS5', {
    product: 'the espresso machine on an ordinary home counter, a hand pressing its single button',
    scene: 'amateur smartphone snapshot by a customer, slightly tilted, mixed light, a bit of clutter; upper 35% plain wall',
  })}
${NATIVE_STATIC_RULES}
${KONEC(f)}`,
  overlays: [
    { lines: ['Bojíte se páky?', 'Stačí jedno tlačítko.'], xPct: 0.07, yPct: 0.07, fontSize: 60, lineHeight: 1.1,
      color: C.bila, weight: 800, ...font, scrim: { from: 'top', heightPct: 0.4, opacity: 0.55 } },
  ],
};

// T3 — text na obyčejném pozadí, sebe-selekce (native-static NS6)
// PERSONA: home-office · ÚHEL: identity · BUŇKA: home-office × identity × native-static
const T3: Concept = {
  id: 'T3', slug: 'bf-test-t3', getReference: ref,
  buildPrompt: f => `Image ${f.width}x${f.height} pixels.
${nativeStaticStyle('NS6', { palette: `flat cream ${C.krem}`, product: 'the espresso machine small in the lower right corner' })}
${NATIVE_STATIC_RULES}
COMPOSITION: upper 65% completely empty flat background.
${KONEC(f)}`,
  overlays: [nadpis(['Pracujete z domu', 'a kafe si chodíte', 'kupovat ven?'], 0.09, C.espresso, 84),
    pod(['Espresso za minutu, bez fronty.'], 0.45)],
};

const vitez = { T1, T2, T3 }[VITEZ] as Concept;

// BF1 — vítěz se škáluje nabídkou: stejný obrázek (podklad), AI se nevolá
const BF1: Concept = {
  id: 'BF1', slug: 'bf-blackfriday', buildPrompt: vitez.buildPrompt, getReference: ref, podklad: vitez.slug,
  overlays: [pruh(`BLACK FRIDAY ${NABIDKA.sleva}`, 0.05, C.espresso),
    ...(vitez.overlays ?? []).map(o => ({ ...o, yPct: o.yPct < 0.8 ? o.yPct + 0.07 : o.yPct }))
      .map(o => (o.band ? { ...o, lines: [`Koupit se slevou · ${NABIDKA.termin}`] } : o))],
};

// BF2 — Cyber Monday jako post-it (native-static NS4: slevy, krátká pobídka)
const BF2: Concept = {
  id: 'BF2', slug: 'bf-cybermonday', getReference: ref,
  buildPrompt: f => `Image ${f.width}x${f.height} pixels.
${nativeStaticStyle('NS4', {
    product: 'the espresso machine on a kitchen counter, lower right',
    scene: 'a large blank yellow sticky note on a kitchen cabinet, slightly rotated, upper left area, completely empty',
  })}
${NATIVE_STATIC_RULES}
${KONEC(f)}`,
  overlays: [{ ...nadpis(['Poslední den', NABIDKA.sleva], 0.2, C.espresso, 62), xPct: 0.24 }],
};

// V1 — Vánoce: dárková fotka, bez slevy
const V1: Concept = {
  id: 'V1', slug: 'bf-vanoce', getReference: ref,
  buildPrompt: f => `Warm Christmas advertising photo, ${f.width}x${f.height} pixels.
PRODUCT: ${PRODUKT}
SCENE: the machine with a simple red ribbon and a blank paper gift tag, cozy living room, blurred tree lights.
COMPOSITION: upper 45% calm dark-warm blurred background for text.
${KONEC(f)}`,
  overlays: [{ ...nadpis(['Dárek pro toho,', 'kdo ráno nestíhá.'], 0.13, C.bila, 70),
      scrim: { from: 'top', heightPct: 0.55, opacity: 0.65 } },
    pruh('Doručíme do Vánoc', 0.05, C.oranz), pruh('Vybrat dárek', 0.88, C.oranz)],
};

const config: Config = { outDir: 'banners-ukazka', concepts: [T1, T2, T3, BF1, BF2, V1] };
export default config;

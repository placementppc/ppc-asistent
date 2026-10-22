/**
 * UKÁZKA BLACK FRIDAY — smyšlená značka „Kávovar Ranní" (stejná jako configs/ukazka.ts).
 *
 * 1. TEST CLAIMŮ (T1–T3): 3 RŮZNÉ koncepty. Každý jiná mikro-persona × úhel × styl:
 *    profi lifestyle foto, UGC fotka z mobilu, nativní obrázek ze života (ručně psaný seznam úkolů).
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
import type { Concept, Config, Format } from '../banner-formats';
import { nativeStaticStyle, NATIVE_STATIC_RULES } from '../lib/native-static';
import { sazba } from '../lib/sazba';

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

// Profi sazba (lib/sazba.ts): velký nadpis bez šedého přechodu, podnadpis v bílé zaoblené kartě,
// CTA jako pilulka se stínem, okraj 80 px. Ostré pruhy a šedé přechody přes fotku působí amatérsky.
const S = sazba({ ...font, ink: C.espresso, cta: C.oranz });

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
  overlays: [S.nadpis(['Kafe z automatu', 'chutná jako pondělí?'], 0.06, 78),
    S.pod(['Espresso doma jedním tlačítkem.'], 0.215), S.cta('Vybrat kávovar')],
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
  overlays: [S.nadpis(['Bojíte se páky?', 'Stačí jedno tlačítko.'], 0.06, 80, C.bila), S.cta('Vybrat kávovar')],
};

// T3 — ručně psaný seznam úkolů na lince (native-static NS7: sdělení v reálném kontextu)
// PERSONA: home-office · ÚHEL: identity · BUŇKA: home-office × identity × native-static
// Ruční písmo (např. Caveat z Google Fonts) dej do brand/fonts; bez něj se seznam vysází běžným písmem.
// Kam AI blok položí, se liší: polohu textu dolaď přes --relayout.
const RUKA_FONT = path.join(DIR, 'brand', 'fonts', 'Caveat-VF.ttf');
const ruka = fs.existsSync(RUKA_FONT) ? { fontFile: RUKA_FONT, fontFamily: 'Caveat' } : font;
const T3: Concept = {
  id: 'T3', slug: 'bf-test-t3', getReference: ref,
  buildPrompt: f => `Image ${f.width}x${f.height} pixels.
${nativeStaticStyle('NS7', {
    product: 'the espresso machine on the desk to the right of the notepad',
    scene: 'top-down smartphone photo of a home-office desk on a Monday morning: a LARGE blank lined notepad (completely empty, '
      + 'no writing) in the left half, covering roughly x 6–62%, y 14–80%; a laptop corner, a pen, an empty coffee cup. Real, slightly messy.',
  })}
${NATIVE_STATIC_RULES}
${KONEC(f)}`,
  overlays: [
    { lines: ['Pondělí'], xPct: 0.12, yPct: 0.2, fontSize: 60, color: '#1d3a8a', weight: 700, ...ruka },
    { lines: ['– call v 8:30', '– odpovědět na maily', '– zajít si pro kafe', '– zase zajít si pro kafe'],
      xPct: 0.12, yPct: 0.29, fontSize: 42, lineHeight: 1.4, color: '#1d3a8a', weight: 500, ...ruka },
    S.nadpis(['Pracujete z domu a kafe', 'si chodíte kupovat ven?'], 0.03, 44, C.bila),
    S.cta('Vybrat kávovar'),
  ],
};

const vitez = { T1, T2, T3 }[VITEZ] as Concept;

// BF1 — vítěz se škáluje nabídkou: stejný obrázek (podklad), AI se nevolá
const BF1: Concept = {
  id: 'BF1', slug: 'bf-blackfriday', buildPrompt: vitez.buildPrompt, getReference: ref, podklad: vitez.slug,
  overlays: [S.stitek(`BLACK FRIDAY ${NABIDKA.sleva} · ${NABIDKA.termin}`, 0.035, C.espresso),
    ...(vitez.overlays ?? []).filter(o => o.yPct < 0.8).map(o => ({ ...o, yPct: o.yPct + 0.07 })),
    S.cta('Koupit se slevou')],
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
  overlays: [S.nadpis(['Poslední den', NABIDKA.sleva], 0.2, 62, C.espresso, 0.24), S.cta('Vybrat kávovar')],
};

// V1 — Vánoce: dárková fotka, bez slevy
const V1: Concept = {
  id: 'V1', slug: 'bf-vanoce', getReference: ref,
  buildPrompt: f => `Warm Christmas advertising photo, ${f.width}x${f.height} pixels.
PRODUCT: ${PRODUKT}
SCENE: the machine with a simple red ribbon and a blank paper gift tag, cozy living room, blurred tree lights.
COMPOSITION: upper 45% calm dark-warm blurred background for text.
${KONEC(f)}`,
  overlays: [S.stitek('Doručíme do Vánoc', 0.05, C.oranz),
    S.nadpis(['Dárek pro toho,', 'kdo ráno nestíhá.'], 0.12, 70, C.bila),
    S.cta('Vybrat dárek')],
};

const config: Config = { outDir: 'banners-ukazka', concepts: [T1, T2, T3, BF1, BF2, V1] };
export default config;

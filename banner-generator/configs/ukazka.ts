/**
 * UKÁZKOVÝ CONFIG — smyšlená značka „Kávovar Ranní" (neexistující e-shop).
 *
 * Ukazuje, jak vypadá config podle pravidel banner-generátoru:
 *   - brand z banners-ukazka/BRAND-MANUAL.md (barvy, oslovení, CTA, zakázané věci),
 *   - každý koncept má 4 řádky PERSONA / PROBLÉM/POTŘEBA / ÚHEL / BUŇKA,
 *   - 3 různé mikro-persony, max 1 cenová kotva, 2 nereklamní koncepty (native-static),
 *   - AI generuje JEN obraz; nadpis a CTA skládá kód (overlays), logo taky (logo).
 *
 * Spuštění (ze složky banner-generator):
 *   npm run generate:gemini -- ukazka --only=K1 --format=1080x1080
 *
 * Pro vlastního klienta zkopíruj na configs/<klient>-<téma>.ts a přepiš.
 * Produktová fotka a logo tu nejsou (smyšlená značka) — bez fotky si AI produkt vymyslí,
 * u skutečného klienta proto fotku VŽDY dodej (viz AI-EXECUTION-RULES.md).
 */
import * as fs from 'fs';
import * as path from 'path';
import type { Concept, Config, Format, TextOverlay } from '../banner-formats';
import { nativeStaticStyle, NATIVE_STATIC_RULES } from '../lib/native-static';

// Cesty se berou od složky banner-generator (odtud runner běží).
const DIR = path.resolve('banners-ukazka');
const PHOTO = path.join(DIR, 'kavovar_transparent.png'); // produkt bez pozadí (dodá klient / web)
const LOGO = path.join(DIR, 'brand', 'logo.png');         // PNG s průhledností
const FONT = path.join(DIR, 'brand', 'fonts', 'Inter-ExtraBold.ttf'); // font z BRAND-MANUAL.md (sekce 4)

// Barvy z BRAND-MANUAL.md (sekce 3)
const C = {
  espresso: '#3B2A20', // primární
  krem: '#F4ECE0',     // sekundární (plochy)
  oranz: '#E8772E',    // akcent (CTA)
  text: '#2B2B2B',
  bila: '#FFFFFF',
};

const photoRef = (): string | null => (fs.existsSync(PHOTO) ? PHOTO : null);
const logo = fs.existsSync(LOGO)
  ? { path: LOGO, position: 'bottom-left' as const, widthPct: 0.2 }
  : undefined;

/** Společná hlavička každého promptu. */
function header(f: Format, styl: string, sProduktem = true): string {
  const produkt = sProduktem
    ? 'PRODUCT: compact home espresso machine in matte dark brown with a small steam wand.'
    : 'NO product in the image.';
  return `Create an advertising image for Facebook/Instagram.
Exact dimensions: ${f.width}x${f.height} pixels.
${produkt}
${sProduktem && photoRef() ? 'The attached photo shows the actual product — reproduce its shape, color and label verbatim, background removed.' : ''}
STYLE: ${styl}
TECHNICAL RULES:
- DO NOT render any text, logo, button or price — leave clean space for text composed later.
- NEVER use the long dash "—" in any visible text.
- NEVER draw safe-zone indicators, rulers, pixel values or annotation marks.
- Background extends edge-to-edge, no visible seams, bands or frames.
- Output exactly ${f.width}x${f.height} pixels.`;
}

/**
 * CTA: s brandovým fontem jako bílý text v pomerančovém pruhu (`band`).
 * `band` vykresluje jen větev s `fontFile` (lib/compose-overlays.ts). Bez souboru fontu
 * se CTA vysází systémovým fontem v barvě akcentu, ať je pořád vidět.
 */
function ctaOverlay(text: string, yPct = 0.86): TextOverlay {
  return fs.existsSync(FONT)
    ? { lines: [text], xPct: 0.06, yPct, fontSize: 40, color: C.bila, weight: 700,
        fontFile: FONT, fontFamily: 'Inter', band: { color: C.oranz, padXPct: 0.04, padYPct: 0.02 } }
    : { lines: [text], xPct: 0.06, yPct, fontSize: 44, color: C.oranz, weight: 800 };
}

/** Nadpis nahoře + CTA dole, sazba kódem (sendvič). */
function sendvic(nadpis: string[], cta: string, barvaNadpisu = C.espresso): TextOverlay[] {
  return [
    { lines: nadpis, xPct: 0.06, yPct: 0.12, fontSize: 64, color: barvaNadpisu, weight: 800 },
    ctaOverlay(cta),
  ];
}

// K1 — "Kafe z automatu? Zase?"
// PERSONA: kancelářský dojížděč — pije kávu v práci, chce si ráno udělat dobrou doma a nemá čas.
// PROBLÉM/POTŘEBA: "Automatová káva je hrozná, ale na kavárnu cestou nemám čas ani peníze."
// ÚHEL: sendvič problém→akce (situace → produkt jako rychlé řešení doma).
// BUŇKA: kancelářský dojížděč × pain-point × designed-static
const K1: Concept = {
  id: 'K1',
  slug: 'k1-automat',
  buildPrompt: f => header(f,
    `Realistic lifestyle photo, early morning kitchen counter, warm window light, the espresso machine
pouring a shot into a small cream cup, keys and a work bag in soft focus. Calm cream (${C.krem}) and
espresso brown (${C.espresso}) tones. Keep the upper 30% and the bottom 15% calm and uncluttered for text.`),
  getReference: photoRef,
  overlays: sendvic(['Kafe z automatu?', 'Zase?'], 'Dobrá káva doma za minutu'),
  logo,
};

// K2 — doslovná recenze (Q&A)
// PERSONA: skeptik po zkušenostech — starý kávovar se rozbil po roce, nevěří slibům.
// PROBLÉM/POTŘEBA: "Minulý kávovar vydržel rok. Proč by tenhle měl být jiný?"
// ÚHEL: důkaz / doslovná ověřená recenze (třetí strana, ne náš claim).
// BUŇKA: skeptik po zkušenostech × social-proof × native-static (NS3 Q&A)
// Zdroj recenze: U SKUTEČNÉHO KLIENTA sem patří URL a datum. Tady je text jen zástupný,
// bez doslovné recenze z webu se tenhle koncept NEGENERUJE (Šesté zlaté pravidlo).
const K2: Concept = {
  id: 'K2',
  slug: 'k2-recenze',
  buildPrompt: f => `${header(f, 'see below')}
${nativeStaticStyle('NS3', { palette: `cream ${C.krem} + espresso brown ${C.espresso}`, product: 'the espresso machine on a home shelf, slightly out of focus' })}
${NATIVE_STATIC_RULES}`,
  getReference: photoRef,
  overlays: [
    { lines: ['Vydrží to víc', 'než rok?'], xPct: 0.5, yPct: 0.3, anchor: 'middle', fontSize: 52, color: C.text, weight: 700 },
    { lines: ['„<doslovná recenze z webu>"', '<jméno> · ověřený zákazník · <datum>'], xPct: 0.5, yPct: 0.55, anchor: 'middle', fontSize: 34, color: C.text, weight: 500 },
  ],
  logo,
};

// K3 — "Pracujete z domu? Káva bez fronty."
// PERSONA: home-office — pracuje doma, kávu si chodí kupovat ven a ztrácí čas.
// PROBLÉM/POTŘEBA: "Kvůli kávě každý den vyrážím ven a pak dohání práci."
// ÚHEL: sebe-selekce cílovky v první větě + úleva.
// BUŇKA: home-office × identity × native-static (NS6 text na obyčejném pozadí)
const K3: Concept = {
  id: 'K3',
  slug: 'k3-home-office',
  buildPrompt: f => `${header(f, 'see below', false)}
${nativeStaticStyle('NS6', { palette: `flat cream ${C.krem}` })}
${NATIVE_STATIC_RULES}`,
  overlays: [
    { lines: ['Pracujete z domu?'], xPct: 0.08, yPct: 0.22, fontSize: 70, color: C.espresso, weight: 800 },
    { lines: ['Espresso za minutu, bez fronty', 'a bez cesty do kavárny.'], xPct: 0.08, yPct: 0.42, fontSize: 40, color: C.text, weight: 500 },
    { lines: ['Kávovar Ranní · kávovary na doma'], xPct: 0.08, yPct: 0.84, fontSize: 30, color: C.espresso, weight: 600 },
  ],
  logo,
};

// K4 — ilustrace "Ráno bez spěchu?"
// PERSONA: kancelářský dojížděč — viz K1, ale jiný úhel (cílový stav).
// PROBLÉM/POTŘEBA: "Chci si ráno aspoň na pět minut sednout a nikam nespěchat."
// ÚHEL: aspirace (klidné ráno), sendvič.
// BUŇKA: kancelářský dojížděč × aspiration × designed-static
const K4: Concept = {
  id: 'K4',
  slug: 'k4-klidne-rano',
  buildPrompt: f => header(f,
    `Flat vector illustration, a person sitting by a window with a cup, the espresso machine on the counter
behind them, soft sunrise. Palette strictly cream ${C.krem}, espresso brown ${C.espresso}, one orange accent ${C.oranz}.
Keep the upper 30% plain cream for text.`),
  getReference: photoRef,
  overlays: sendvic(['Ráno bez spěchu?', 'Začíná u kávy.'], 'Vybrat kávovar'),
  logo,
};

// K5 — infografika "Jak to funguje"
// PERSONA: začátečník s obavou — bojí se, že kávovar nezvládne obsluhovat.
// PROBLÉM/POTŘEBA: "Pákové kávovary jsou složité, to se nenaučím."
// ÚHEL: mechanismus — tři kroky, žádná věda.
// BUŇKA: začátečník s obavou × mechanism × designed-static
const K5: Concept = {
  id: 'K5',
  slug: 'k5-tri-kroky',
  buildPrompt: f => header(f,
    `Clean educational infographic on dark espresso brown (${C.espresso}) background: the machine on the right,
the left half stays plain dark brown (text is added later), thin orange (${C.oranz}) arrows pointing to the machine.`),
  getReference: photoRef,
  overlays: [
    { lines: ['Bojíte se páky?'], xPct: 0.06, yPct: 0.1, fontSize: 60, color: C.krem, weight: 800 },
    { lines: ['1  Nasypat kávu', '2  Zmáčknout tlačítko', '3  Hotovo'], xPct: 0.08, yPct: 0.32, fontSize: 40, lineHeight: 1.6, color: C.krem, weight: 700 },
    ctaOverlay('Zjistit víc'),
  ],
  logo,
};

// K6 — cenová kotva (MAX 1 V SADĚ)
// PERSONA: počítač nákladů — utrácí v kavárně a porovnává.
// PROBLÉM/POTŘEBA: feature/price kotva — odpověď na „vyplatí se to?"
// ÚHEL: cena / srovnání se starým řešením (kavárna cestou), ne s konkurencí.
// BUŇKA: počítač nákladů × comparison × designed-static
// Pozn.: ceny jen se souhlasem klienta (BRAND-MANUAL.md, sekce 6). Tady bez konkrétní částky.
const K6: Concept = {
  id: 'K6',
  slug: 'k6-kavarna',
  buildPrompt: f => header(f,
    `Bold typographic layout: solid orange (${C.oranz}) background, the espresso machine large in the lower right
on a cream (${C.krem}) round shape. Upper left half empty for big headline.`),
  getReference: photoRef,
  overlays: [
    { lines: ['Kolik vás stojí', 'káva cestou?'], xPct: 0.06, yPct: 0.12, fontSize: 72, color: C.bila, weight: 900 },
    { lines: ['Espresso doma vyjde levněji.'], xPct: 0.06, yPct: 0.36, fontSize: 38, color: C.espresso, weight: 700 },
  ],
  logo,
};

const config: Config = {
  outDir: 'banners-ukazka',
  concepts: [K1, K2, K3, K4, K5, K6],
};

export default config;

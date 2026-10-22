/**
 * UKÁZKA SADY „OD GRAFIKA“ — smyšlená značka „Kávovar Ranní“ (stejná jako configs/ukazka-black-friday.ts).
 *
 * BEZ OBRAZOVÉ AI: podklad skládá kód (lib/grafik.ts) ze SKUTEČNÉ fotky produktu bez pozadí, značkových barev,
 * loga, hodnocení a faktů ze stránky produktu. Etiketa je proto vždy správně a nic nepůsobí jako AI.
 * Doplňuje sadu ze života (test claimů): stejné 3 hooky, každý jiné rozvržení, plus Black Friday,
 * poslední den a Vánoce = 6 bannerů.
 *
 *   npm --prefix banner-generator run generate:gemini -- ukazka-grafik --format=1080x1350
 *   (AI se nevolá, nic to nestojí; GBF1 i pro Stories: --only=GBF1 --format=1080x1920)
 *
 * Pro vlastního klienta zkopíruj na configs/<klient>-grafik.ts a vyměň:
 *   - PRODUKT: fotka produktu bez pozadí (PNG s průhledností), LOGO: logo klienta (PNG),
 *   - HODNOCENI a fakta (S.fakt): JEN skutečná čísla ze stránky produktu, nic nevymýšlej,
 *   - NABIDKA: jen skutečná sleva a termín (zeptej se klienta).
 * Čísla níž jsou smyšlená, protože i značka je smyšlená.
 */
import * as fs from 'fs';
import * as path from 'path';
import type { Concept, Config } from '../banner-formats';
import type { GrafikSpec } from '../lib/grafik';
import { sazba } from '../lib/sazba';

const DIR = path.resolve('banners-ukazka');
const PRODUKT = path.join(DIR, 'kavovar_transparent.png');
const LOGO = path.join(DIR, 'brand', 'logo.png');
const FONT = path.join(DIR, 'brand', 'fonts', 'Inter-ExtraBold.ttf');
if (!fs.existsSync(PRODUKT)) {
  throw new Error(`Chybí fotka produktu bez pozadí: ${PRODUKT}. Sada „od grafika“ stojí na skutečné fotce (PNG s průhledností).`);
}
const F = fs.existsSync(FONT) ? { fontFile: FONT, fontFamily: 'Inter' } : {};
const C = {
  espresso: '#3B2A20', oranz: '#E8772E', zlata: '#F2B33D', bila: '#FFFFFF', seda: '#6B5D52',
  krem: '#F4ECE0', kremSvetly: '#FAF5EE', broskev: '#F7DCC6', broskevSvetla: '#FBEADC',
};
const S = sazba({ ...F, ink: C.espresso, cta: C.oranz });
const HODNOCENI = { prumer: '4,7 z 5', pocet: '120 hodnocení zákazníků' }; // UKÁZKA: u klienta jen skutečné
const NABIDKA = { sleva: '−20 %', termin: 'jen do neděle' }; // UKÁZKA: u klienta jen skutečná nabídka
const nic = () => ''; // AI se nevolá

// Logo je volitelné: bez souboru se banner složí bez něj.
const logo = (svetle = false): Pick<GrafikSpec, 'logo'> =>
  fs.existsSync(LOGO) ? { logo: { src: LOGO, x: 0.074, y: 0.049, w: 0.231, svetle } } : {};
const svetly = (cx = 0.755): GrafikSpec => ({
  pozadi: [C.kremSvetly, C.krem],
  produkt: { src: PRODUKT, cx, dno: 0.8, vyska: 0.385 },
  ...logo(),
});
const hodnoceni = (y: number, color = C.espresso, seda = C.seda) => [
  { lines: [HODNOCENI.prumer], xPct: 0.24, yPct: y + 0.001, fontSize: 32, color, weight: 800, ...F },
  { lines: [HODNOCENI.pocet], xPct: 0.074, yPct: y + 0.04, fontSize: 32, color: seda, weight: 600, ...F },
];

// G1 — produkt v kruhu, hodnocení, fakta (hook T1)
// PERSONA: dojíždějící do práce · ÚHEL: pain-point · BUŇKA: dojíždějící × pain-point × designed-static (grafik)
const G1: Concept = {
  id: 'G1', slug: 'grafik-g1', buildPrompt: nic,
  grafik: { ...svetly(), tvary: [{ kruh: [0.755, 0.622, 0.296], barva: C.broskev, prechod: C.broskevSvetla }], hvezdy: { x: 0.074, y: 0.472 } },
  overlays: [
    S.nadtitulek('Espresso doma', 0.135),
    S.nadpis(['Kafe z automatu'], 0.17, 84),
    S.nadpis(['chutná jako pondělí?'], 0.238, 84, C.oranz),
    S.pod(['Espresso jedním tlačítkem.', 'Hotové dřív, než se obujete.'], 0.34, 34),
    ...hodnoceni(0.472),
    S.fakt('15 barů tlaku', 0.6),
    S.fakt('Napěňovač mléka', 0.665),
    S.fakt('Záruka 3 roky', 0.73),
    S.cta('Vybrat kávovar', 0.888),
  ],
};

// G2 — velké číslo jako hlavní grafický prvek (hook T2)
// PERSONA: skeptik („na to nemám ráno čas“) · ÚHEL: námitka · BUŇKA: skeptik × comparison × designed-static (grafik)
const G2: Concept = {
  id: 'G2', slug: 'grafik-g2', buildPrompt: nic,
  grafik: {
    ...svetly(0.765),
    produkt: { src: PRODUKT, cx: 0.765, dno: 0.865, vyska: 0.37 },
    tvary: [{ obdelnik: [0.52, 0.5, 0.42, 0.4, 36], barva: C.broskev }],
    hvezdy: { x: 0.074, y: 0.7 },
  },
  overlays: [
    S.nadtitulek('Kávovar Ranní', 0.135),
    S.nadpis(['Ráno nestíháte', 'ani kafe?'], 0.17, 76),
    { lines: ['30 s'], xPct: 0.066, yPct: 0.325, fontSize: 176, lineHeight: 1, letterSpacing: -0.03, color: C.oranz, weight: 900, ...F },
    S.pod(['od tlačítka', 'po hotové espresso.'], 0.48, 36),
    S.pod(['15 barů tlaku,', 'napěňovač mléka.'], 0.6, 32, C.seda),
    ...hodnoceni(0.7),
    S.cta('Vybrat kávovar', 0.888),
  ],
};

// G3 — typografický seznam: všechno odškrtnuté, jen kafe ne (hook T3)
// PERSONA: rodič, co ráno chystá všechny · ÚHEL: identity · BUŇKA: rodič × identity × designed-static (grafik)
const G3: Concept = {
  id: 'G3', slug: 'grafik-g3', buildPrompt: nic,
  grafik: {
    pozadi: [C.kremSvetly, '#F1E6D8'],
    produkt: { src: PRODUKT, cx: 0.765, dno: 0.83, vyska: 0.39 },
    tvary: [{ kruh: [0.765, 0.64, 0.27], barva: C.bila, prechod: C.bila }],
    ...logo(),
  },
  overlays: [
    S.nadpis(['Svačiny, budík, školka.', 'A kde je vaše kafe?'], 0.135, 64),
    S.nadtitulek('Dnešní ráno', 0.3, C.seda),
    { lines: ['svačiny'], xPct: 0.074, yPct: 0.345, fontSize: 56, color: C.seda, weight: 700, ...F, preskrtnuti: { color: C.oranz } },
    { lines: ['budík'], xPct: 0.074, yPct: 0.41, fontSize: 56, color: C.seda, weight: 700, ...F, preskrtnuti: { color: C.oranz } },
    { lines: ['školka'], xPct: 0.074, yPct: 0.475, fontSize: 56, color: C.seda, weight: 700, ...F, preskrtnuti: { color: C.oranz } },
    { lines: ['pořádné kafe'], xPct: 0.074, yPct: 0.54, fontSize: 56, color: C.oranz, weight: 800, ...F },
    S.pod(['Kávovar Ranní.', 'Espresso jedním tlačítkem.'], 0.645, 32),
    S.cta('Vybrat kávovar', 0.888),
  ],
};

// GBF1 — Black Friday z vítěze testu (G1): zlaté kolečko se slevou, termín ve štítku. Feed i Stories.
const GBF1: Concept = {
  id: 'GBF1', slug: 'grafik-bf1', buildPrompt: nic,
  grafik: f => f.height > 1500
    ? {
        ...svetly(),
        produkt: { src: PRODUKT, cx: 0.69, dno: 0.775, vyska: 0.27 },
        ...(fs.existsSync(LOGO) ? { logo: { src: LOGO, x: 0.074, y: 0.175, w: 0.231 } } : {}),
        tvary: [{ kruh: [0.69, 0.635, 0.3], barva: C.broskev, prechod: C.broskevSvetla }],
        odznak: { cx: 0.25, cy: 0.62, r: 0.12, barva: C.zlata },
      }
    : {
        ...svetly(),
        tvary: [{ kruh: [0.755, 0.622, 0.296], barva: C.broskev, prechod: C.broskevSvetla }],
        hvezdy: { x: 0.074, y: 0.472 },
        odznak: { cx: 0.6, cy: 0.5, r: 0.105, barva: C.zlata },
      },
  overlays: f => f.height > 1500
    ? [ // Stories 1080×1920: obsah jen v safe zóně y 0.17–0.82
        S.stitek(`BLACK FRIDAY · ${NABIDKA.termin}`, 0.235, C.zlata, C.espresso),
        S.nadpis(['Kafe z automatu'], 0.285, 84),
        S.nadpis(['chutná jako pondělí?'], 0.335, 84, C.oranz),
        S.pod(['Espresso jedním tlačítkem.', 'Hotové dřív, než se obujete.'], 0.41, 34),
        { lines: [NABIDKA.sleva], anchor: 'middle', xPct: 0.25, yPct: 0.603, fontSize: 70, letterSpacing: -0.02, color: C.espresso, weight: 900, ...F },
        S.cta('Vybrat kávovar', 0.775),
      ]
    : [
        S.stitek(`BLACK FRIDAY · ${NABIDKA.termin}`, 0.125, C.zlata, C.espresso),
        S.nadpis(['Kafe z automatu'], 0.19, 84),
        S.nadpis(['chutná jako pondělí?'], 0.258, 84, C.oranz),
        S.pod(['Espresso jedním tlačítkem.', 'Hotové dřív, než se obujete.'], 0.355, 34),
        ...hodnoceni(0.472),
        { lines: [NABIDKA.sleva], anchor: 'middle', xPct: 0.6, yPct: 0.483, fontSize: 64, letterSpacing: -0.02, color: C.espresso, weight: 900, ...F },
        S.fakt('15 barů tlaku', 0.6),
        S.fakt('Napěňovač mléka', 0.665),
        S.fakt('Záruka 3 roky', 0.73),
        S.cta('Vybrat kávovar', 0.888),
      ],
};

// GBF2 — poslední den akce, tmavá verze, obří sleva
const GBF2: Concept = {
  id: 'GBF2', slug: 'grafik-bf2', buildPrompt: nic,
  grafik: {
    pozadi: ['#3A2618', '#1A100A'],
    produkt: { src: PRODUKT, cx: 0.765, dno: 0.83, vyska: 0.4, tmave: true },
    tvary: [{ kruh: [0.765, 0.63, 0.29], barva: '#2C1C12', prechod: '#55361F' }],
    ...logo(true),
  },
  overlays: [
    S.stitek('BLACK FRIDAY', 0.135, C.zlata, C.espresso),
    S.nadpis(['Poslední den.'], 0.2, 84, C.bila),
    { lines: [NABIDKA.sleva], xPct: 0.06, yPct: 0.275, fontSize: 210, lineHeight: 1, letterSpacing: -0.03, color: C.zlata, weight: 900, ...F },
    S.pod(['Sleva končí dnes', 'o půlnoci.'], 0.47, 40, C.bila),
    S.pod(['Kávovar Ranní,', '15 barů tlaku.'], 0.6, 32, '#E3D6C8'),
    S.cta('Vybrat kávovar', 0.888),
  ],
};

// GV1 — Vánoce: tmavé teplé pozadí se světýlky (kód, ne AI), bez slevy
const GV1: Concept = {
  id: 'GV1', slug: 'grafik-v1', buildPrompt: nic,
  grafik: {
    pozadi: ['#4A2C1C', '#1C110B'],
    svetla: true,
    produkt: { src: PRODUKT, cx: 0.74, dno: 0.84, vyska: 0.41, tmave: true },
    tvary: [{ kruh: [0.74, 0.65, 0.27], barva: '#2B1A10', prechod: '#5A3820' }],
    ...logo(true),
    hvezdy: { x: 0.074, y: 0.6 },
  },
  overlays: [
    S.nadtitulek('Tip na dárek', 0.135, C.zlata),
    S.nadpis(['Dárek pro toho,', 'kdo bez kafe', 'nemluví.'], 0.17, 80, C.bila),
    S.pod(['Kávovar Ranní.', 'Espresso jedním tlačítkem.'], 0.43, 32, '#EFE4D8'),
    ...hodnoceni(0.6, C.bila, '#D8C9B8'),
    S.cta('Vybrat dárek', 0.888),
  ],
};

const config: Config = { outDir: 'banners-ukazka', concepts: [G1, G2, G3, GBF1, GBF2, GV1] };
export default config;

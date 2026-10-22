/**
 * Profi sazba textu na banner: nadpis / podnadpis / tlačítko / štítek.
 *
 * Jak má vypadat (zpětná vazba Jakuba, 21. 10. 2026):
 * - čistý text přímo na klidné ploše fotky (AI ji nechá volnou), žádné bubliny, žádné šedé přechody,
 *   žádná světlá záře kolem písma,
 * - nadpis brandovým písmem ExtraBold, lehce sevřený (−1,5 % prostrkání), krátký řádkový proklad,
 * - nic zbytečně malého: podnadpis a tvrzení min. 32 px, tlačítko 40 px (na šířce 1080),
 * - tlačítko jako zaoblená pilulka s jemným stínem, okraj 80 px u všeho.
 *
 * Použití v configu:
 *   const S = sazba({ fontFile, fontFamily: 'Mulish', ink: '#16121f', cta: '#bc25a4' });
 *   overlays: [S.nadpis(['Hook na', 'dva řádky'], 0.05, 80), S.pod(['Podnadpis.', 'Tvrzení.'], 0.19), S.cta('Vyzkoušet')]
 * Stories 1080×1920: obsah jen mezi y 0.17 a 0.82 (safe zóna), viz overlays jako funkce formátu.
 */
import type { TextOverlay } from '../banner-formats';

export type SazbaBrand = {
  fontFile?: string;   // brandový font (.ttf, i variabilní); bez něj systémový sans
  fontFamily?: string;
  ink: string;         // barva nadpisu a textu
  cta: string;         // barva tlačítka
  ctaText?: string;    // barva písma v tlačítku, default bílá
};

export const OKRAJ = 0.074; // 80 px z 1080
const MIN_TEXT = 32;

export function sazba(b: SazbaBrand) {
  const F = b.fontFile ? { fontFile: b.fontFile, fontFamily: b.fontFamily } : {};
  const hlidej = (lines: string[], size: number) => {
    if (size < MIN_TEXT) console.warn(`   ⚠️  sazba: „${lines[0]}…“ má ${size} px, ve feedu bude zbytečně malé (min. ${MIN_TEXT}).`);
  };
  // Bílý text na tmavé fotce dostane jen jemný tmavý stín (ne šedý přechod přes obraz).
  const stin = (color?: string) => (color && color.toLowerCase() === '#ffffff'
    ? { textShadow: { color: '#000000', opacity: 0.45, blur: 10, offsetY: 2 } } : {});

  return {
    /** Hlavní nadpis (hook). Při exportu pro video je to vrstva, která přiletí. */
    nadpis: (lines: string[], yPct: number, fontSize = 80, color = b.ink, xPct = OKRAJ): TextOverlay => ({
      lines, xPct, yPct, fontSize, lineHeight: 1.06, letterSpacing: -0.015, color, weight: 800, role: 'head', ...F,
      ...stin(color),
    }),
    /** Podnadpis / zdravotní tvrzení: čistý text, polotučně, čitelná velikost. */
    pod: (lines: string[], yPct: number, fontSize = 36, color = b.ink, xPct = OKRAJ): TextOverlay => {
      hlidej(lines, fontSize);
      return { lines, xPct, yPct, fontSize, lineHeight: 1.28, color, weight: 600, ...F, ...stin(color) };
    },
    /** Tlačítko: zaoblená pilulka s jemným stínem, dole vlevo (yPct = horní hrana písma). */
    cta: (text: string, yPct = 0.872): TextOverlay => ({
      lines: [`${text}  ›`], xPct: OKRAJ + 0.052, yPct, fontSize: 40, letterSpacing: 0.005, color: b.ctaText ?? '#ffffff',
      weight: 800, ...F,
      band: { color: b.cta, padXPct: 0.052, padYPct: 0.022, radius: 'pill', shadow: { opacity: 0.28, blur: 16, offsetY: 8 } },
    }),
    /** Nadtitulek nad nadpisem: verzálky, prostrkané, akcentní barva (téma banneru v 1 s). */
    nadtitulek: (text: string, yPct: number, color = b.cta): TextOverlay => ({
      lines: [text.toUpperCase()], xPct: OKRAJ, yPct, fontSize: 30, letterSpacing: 0.13, color, weight: 800, ...F,
    }),
    /** Fakt z webu jako bílý štítek (300 mg hořčíku denně…). */
    fakt: (text: string, yPct: number, xPct = OKRAJ, color = b.ink, bg = '#ffffff'): TextOverlay => ({
      lines: [text], xPct: xPct + 0.03, yPct, fontSize: 32, color, weight: 700, ...F,
      band: { color: bg, padXPct: 0.03, padYPct: 0.014, radius: 'pill', shadow: { opacity: 0.08, blur: 10, offsetY: 4 } },
    }),
    /** Štítek nahoře (BLACK FRIDAY −20 %, Doručíme do Vánoc): menší pilulka. */
    stitek: (text: string, yPct: number, bg: string, fg = '#ffffff'): TextOverlay => ({
      lines: [text], xPct: OKRAJ + 0.034, yPct, fontSize: 36, letterSpacing: 0.02, color: fg, weight: 800, ...F,
      band: { color: bg, padXPct: 0.034, padYPct: 0.015, radius: 'pill', shadow: { opacity: 0.22, blur: 12, offsetY: 6 } },
    }),
  };
}

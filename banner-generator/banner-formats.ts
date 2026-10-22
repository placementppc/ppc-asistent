/**
 * Sdílené typy a konstanty pro oba runnery (Gemini i OpenAI).
 * Žádné side effects — bezpečně importovatelné odkudkoli.
 */

export type Format = {
  name: string;
  width: number;
  height: number;
  fileSuffix: string;
};

export const FORMATS: Format[] = [
  { name: 'Square',    width: 1200, height: 1200, fileSuffix: '1200x1200' },
  { name: 'Feed',      width: 1080, height: 1080, fileSuffix: '1080x1080' },
  { name: 'Stories',   width: 1080, height: 1920, fileSuffix: '1080x1920' },
  { name: 'Portrait',  width: 1080, height: 1350, fileSuffix: '1080x1350' },
];

// Logo se NIKDY nevkládá přes AI prompt — skládá se kódem přes sharp až po generování.
export type LogoSpec = {
  path: string; // absolutní cesta k logu (PNG s průhledností)
  position?:
    | 'bottom-left'
    | 'bottom-center'
    | 'bottom-right'
    | 'top-left'
    | 'top-right'; // default 'bottom-left'
  widthPct?: number; // šířka loga jako podíl šířky banneru, default 0.22
  padding?: number; // odsazení od okraje v px, default 40
};

// Text (nadpis, cena, CTA) se skládá kódem přes SVG — perfektní diakritika, přesné pixely.
export type TextOverlay = {
  lines: string[]; // řádky textu (ručně zalomené — SVG nezalamuje samo)
  anchor?: 'start' | 'middle' | 'end'; // zarovnání, default 'start'
  xPct: number; // vodorovná pozice kotvy (0–1 šířky)
  yPct: number; // svislá pozice prvního řádku (0–1 výšky)
  fontSize: number; // v px vůči cílovému rozměru banneru
  lineHeight?: number; // násobek fontSize, default 1.15
  color?: string; // default '#ffffff'
  weight?: number | string; // default 800; u variabilního fontFile nastaví osu wght
  fontFamily?: string; // default systémový sans-serif; s fontFile jen výběr řezu z .ttc
  // Přesný brandový font ze souboru (.ttf/.otf). Když je uveden, obrysy písmen se čtou
  // přímo ze souboru a skládají jako vektor (lib/brand-font.ts) — Mac i Windows, bez
  // instalace do systému. Variabilní font dostane váhu z `weight`, statický řez se použije,
  // jak je. yPct je pak HORNÍ hrana textu (ne účaří).
  fontFile?: string;
  letterSpacing?: number; // prostrkání v em (jen s fontFile): −0.015 sevřený nadpis
  // 'head' = hlavní nadpis; při exportu vrstev pro video (--layers) jde do samostatné vrstvy, která přiletí.
  role?: 'head';
  // Přeškrtnutí řádku (typografický seznam „hotovo“). Jen jednořádkové overlaye s fontFile.
  preskrtnuti?: { color?: string; width?: number };
  // Tmavý přechod pod textem, aby zůstal čitelný i nad fotkou. Bez něj text padne
  // na cokoli, co model do té části obrazu nakreslí (u fotoscén typicky produkt).
  // 'top' | 'bottom' = odkud přechod nabíhá; hodnota je podíl výšky banneru.
  scrim?: {
    from: 'top' | 'bottom';
    heightPct: number;   // jak vysoký pruh přechod zabere (0–1)
    opacity?: number;    // krytí u kraje, default 0.75
  };
  // Plný barevný pruh POD textem. Na rozdíl od `scrim` (tmavý přechod, který fotku
  // zašpiní do šeda) je to designový prvek — text sedí v plné ploše, ne v mlze.
  // Vzniklo z praxe: šedohnědý přechod přes půl obrázku působil amatérsky,
  // plný pruh pod textem vypadá čistě.
  band?: {
    color: string;        // barva pruhu, např. '#F5A623'
    opacity?: number;     // default 1 (plná)
    padXPct?: number;     // vodorovné odsazení textu od hrany pruhu (podíl šířky), default 0.045
    padYPct?: number;     // svislé odsazení (podíl výšky), default 0.028
    fullWidth?: boolean;  // true = pruh přes celou šířku; false = obepne jen text
    // Dotáhne pruh až na hranu plátna. Bez toho pod pruhem zůstane proužek fotky,
    // což vypadá jako nedodělek. Text si drží svoji pozici.
    toEdge?: 'top' | 'bottom';
    // Zaoblení rohů v px, nebo 'pill' = půlkruhové konce (tlačítko). Bez něj ostrý obdélník.
    radius?: number | 'pill';
    // Měkký stín pod pruhem (tlačítko pak „sedí“ nad fotkou, ne nalepené).
    shadow?: { opacity?: number; blur?: number; offsetY?: number };
  };
  // Měkký stín pod písmem: čitelnost nad fotkou bez šedého přechodu přes obraz.
  textShadow?: { opacity?: number; blur?: number; offsetY?: number; color?: string };
};

export type Concept = {
  id: string; // "K1", "K2" ...
  slug: string; // pro prefix souboru: "koncept_1" ...
  buildPrompt: (f: Format) => string;
  getReference?: (f: Format) => string | null; // absolutní cesta k jedné fotce nebo null
  getReferences?: (f: Format) => string[]; // víc reference fotek (např. ukázkové bannery)
  logo?: LogoSpec; // NOVÉ (opt-in) — logo se složí kódem po generaci
  // Texty skládané kódem po generaci. Funkce = jiná sazba pro každý formát (Stories mají safe zónu).
  overlays?: TextOverlay[] | ((f: Format) => TextOverlay[]);
  // Kam posunout ořez, když se formát skládá z obrázku jiného formátu (0 = vlevo, 0.5 = střed, 1 = vpravo).
  fokusX?: number;
  // Banner „od grafika“ BEZ obrazové AI: pozadí, tvary, skutečná fotka produktu, logo a hvězdy skládá kód
  // (lib/grafik.ts). Text dál přes `overlays`. Runner AI nevolá, podklad uloží do `_raw/` (relayout, video).
  grafik?: import('./lib/grafik').GrafikSpec | ((f: Format) => import('./lib/grafik').GrafikSpec);
  /**
   * Slug jiného konceptu, jehož surový obrázek (bez textu, `_raw/`) se použije. AI se nevolá,
   * jen se složí jiný text. Pro test claimů (stejný obrázek, liší se jen nadpis) a pro
   * Black Friday verzi vítěze testu. Jen runner Gemini (ten ukládá `_raw/`).
   */
  podklad?: string;
};

export type Config = {
  outDir: string;
  concepts: Concept[];
};

/** Texty konceptu pro daný formát (pole, nebo funkce podle formátu). */
export function overlaysFor(c: Concept, f: Format): TextOverlay[] {
  return typeof c.overlays === 'function' ? c.overlays(f) : (c.overlays ?? []);
}

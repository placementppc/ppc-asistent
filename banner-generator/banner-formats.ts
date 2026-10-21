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
  weight?: number | string; // default 800
  fontFamily?: string; // default systémový sans-serif
  // Přesný brandový font ze souboru (.ttf/.otf). Když je uveden, text se vykreslí
  // nativně přes libvips (fontfile) — přesný řez bez instalace do systému.
  // fontFamily pak musí odpovídat názvu rodiny uvnitř toho fontu.
  fontFile?: string;
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
  };
};

export type Concept = {
  id: string; // "K1", "K2" ...
  slug: string; // pro prefix souboru: "koncept_1" ...
  buildPrompt: (f: Format) => string;
  getReference?: (f: Format) => string | null; // absolutní cesta k jedné fotce nebo null
  getReferences?: (f: Format) => string[]; // víc reference fotek (např. ukázkové bannery)
  logo?: LogoSpec; // NOVÉ (opt-in) — logo se složí kódem po generaci
  overlays?: TextOverlay[]; // NOVÉ (opt-in) — texty skládané kódem po generaci
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

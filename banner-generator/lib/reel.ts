/**
 * Typy pro svislé reely 9:16 (1080×1920) skládané z reálných produktových obrázků.
 *
 * Filozofie je stejná jako u bannerů (dvouvrstvý render):
 *   - AI generuje JEN pozadí (prázdný stůl, polička, pracovní deska) — žádný text, žádný produkt,
 *   - skutečné výřezy produktu i všechny titulky skládá kód deterministicky.
 * Díky tomu se text na produktu nikdy nerozpadne a diakritika sedí.
 */

/** Pozadí záběru: cesta k PNG (AI scéna nebo foto) nebo plná barva / gradient v CSS. */
export type Backdrop = { image: string } | { css: string };

/** Pohyb pozadí — velmi jemný, aby záběr působil jako natočený na mobil, ne jako prezentace. */
export type BgMotion = 'in' | 'out' | 'left' | 'right' | 'none';

/** Umístění jednoho výřezu produktu (karty) v záběru. Souřadnice v % plátna, šířka v % šířky plátna. */
export interface CardPlacement {
  /** Cesta k PNG s reálným výřezem produktu. */
  src: string;
  /** Střed výřezu: x, y v % plátna. */
  x: number;
  y: number;
  /** Šířka výřezu v % šířky plátna. */
  w: number;
  /** Naklonění ve stupních (lehký nepořádek = autentické). */
  rot?: number;
  /** Jak výřez přijde do záběru. */
  in?: 'none' | 'drop' | 'slide-left' | 'slide-right' | 'pop';
  /** Zpoždění nástupu v sekundách. */
  delay?: number;
  /** Jemné „dýchání" (pomalé houpání) po dosednutí. */
  idle?: boolean;
  /** Naklonění do perspektivy scény ve stupních (rotateX) — výřez pak leží na stole, nelepí se na obraz. */
  tilt?: number;
}

/** Titulek v záběru. Pozice drží bezpečné zóny Instagramu (hook ~y430, hlavní ~y1290, nikdy pod y1450). */
export interface Caption {
  text: string;
  /** 'top' = hook (y≈430), 'bottom' = hlavní titulek (y≈1290), 'center' = typografický záběr. */
  at: 'top' | 'bottom' | 'center';
  /** 'white' = základní barva textu (default), 'yellow' = zvýrazňující barva pro CTA
   *  (název zůstal kvůli zpětné kompatibilitě; skutečné barvy určuje `ReelConfig.style`). */
  color?: 'white' | 'yellow';
  /** Velikost písma v px při 1080×1920. Obecné doporučení: 90–110 px, aby se titulek
   *  dal přečíst na mobilu bez zvuku. Výchozí hodnota je `style.captionSize`. */
  size?: number;
  /** Menší řádek pod hlavním titulkem. */
  sub?: string;
  /** Pět hvězdiček nad titulkem (jen u doslovných ověřených recenzí). */
  stars?: boolean;
  /** Podpis pod citátem (jméno · ověřený zákazník · datum). */
  credit?: string;
  /** Ruční svislá pozice bloku v px (jinak hook 360 / hlavní 1180). Nikdy tak, aby text spadl pod y=1450. */
  top?: number;
}

export interface Shot {
  id: string;
  /** Délka záběru v sekundách. */
  dur: number;
  backdrop: Backdrop;
  bgMotion?: BgMotion;
  cards?: CardPlacement[];
  caption?: Caption;
}

export interface Reel {
  /** Slug do názvu souboru. */
  slug: string;
  /** Krátký popis pro README (persona × úhel). */
  note?: string;
  shots: Shot[];
}

/** AI scéna (pozadí) — generuje se jednou a cachuje se na disku. */
export interface SceneSpec {
  /** Název souboru bez přípony, uloží se do <outDir>/_assets/<file>.png */
  file: string;
  /** Anglický prompt pro obrazový model OpenAI (lib/modely.ts). NIKDY nesmí obsahovat text, produkt ani lidi. */
  prompt: string;
}

/**
 * Vizuální styl titulků reelu. Hodnoty převezmi z `banners-<klient>/BRAND-MANUAL.md`
 * (barvy, písmo). Co nevyplníš, má neutrální výchozí hodnotu: bílý text s černou konturou,
 * písmo Inter (se systémovým záložním), CTA ve výrazné žluté.
 */
export interface ReelStyle {
  /** Barva hlavního textu titulků. Default '#FFFFFF'. */
  text?: string;
  /** Barva kontury titulků. Default '#000000'. */
  stroke?: string;
  /** Zvýrazňující barva pro CTA titulky (`color: 'yellow'`) a hvězdičky. Default '#FFD60A'. */
  accent?: string;
  /** CSS font-family titulků. Default "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif". */
  fontFamily?: string;
  /**
   * URL stylesheetu s písmem (např. Google Fonts css2). Default Inter z Google Fonts.
   * Prázdný řetězec = žádné stahování, použije se systémové písmo z `fontFamily`.
   */
  fontCssUrl?: string;
  /** Výchozí velikost hlavního titulku v px (hook nahoře o 2 px větší). Default 98. */
  captionSize?: number;
}

export interface ReelConfig {
  name: string;
  /** Barvy a písmo titulků — z BRAND-MANUAL.md klienta. Bez vyplnění neutrální výchozí styl. */
  style?: ReelStyle;
  /** Složka s výstupy (MP4) i s _assets (scény, výřezy produktu). */
  outDir: string;
  width?: number;   // default 1080
  height?: number;  // default 1920
  fps?: number;     // default 30
  scenes: SceneSpec[];
  reels: Reel[];
}

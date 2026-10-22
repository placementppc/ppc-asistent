/**
 * Banner „od grafika“ BEZ obrazové AI.
 *
 * Proč (Jakub, 22. 10. 2026): AI scény s produktem působí „suše“ a jako AI (AI překreslí etiketu,
 * plastový vzhled). Grafik by vzal SKUTEČNOU produktovou fotku, značkové barvy, logo, hodnocení
 * zákazníků a fakta z webu. Tenhle modul skládá podklad: plocha nebo přechod, tvary (kruh, obdélník),
 * jemné zrno, vánoční světýlka, skutečná fotka produktu se stínem, logo, hvězdy hodnocení a kolečko
 * se slevou. Text (nadpis, fakta, CTA) se pak sází přes `overlays` a `lib/sazba.ts` jako u ostatních.
 *
 * Všechny polohy jsou podíly: x a šířky vůči šířce banneru, y a výšky vůči výšce.
 */
import sharp from 'sharp';

export type GrafikTvar =
  | { kruh: [cx: number, cy: number, r: number]; barva: string; prechod?: string }
  | { obdelnik: [x: number, y: number, w: number, h: number, radius: number]; barva: string };

export type GrafikSpec = {
  /** Barva plochy, nebo [střed, okraj] pro jemný kruhový přechod. */
  pozadi: string | [string, string];
  tvary?: GrafikTvar[];
  /** Skutečná fotka produktu bez pozadí. cx = střed, dno = kde produkt stojí, vyska = výška produktu. */
  produkt: { src: string; cx: number; dno: number; vyska: number; tmave?: boolean };
  /** Logo (PNG s průhledností). `svetle` = tmavé části loga přebarví na bílo (na tmavé pozadí). */
  logo?: { src: string; x: number; y: number; w: number; svetle?: boolean };
  /** Pět hvězd hodnocení (zlaté), levý horní roh. Číslo hodnocení dej do `overlays`. */
  hvezdy?: { x: number; y: number; barva?: string };
  /** Kruhové kolečko se slevou (text „−20 %“ do `overlays` s anchor 'middle'). */
  odznak?: { cx: number; cy: number; r: number; barva: string };
  /** Rozostřená vánoční světýlka (na tmavé teplé pozadí). */
  svetla?: boolean;
  /** Síla jemného zrna (default 0.035), aby plocha nepůsobila digitálně ploše. 0 = bez zrna. */
  zrno?: number;
};

/** Fotka produktu: odstraní studiový stín zapečený ve fotce (šedý, poloprůhledný; na barvě dělá šmouhu). */
async function cistyProdukt(src: string, vyska: number): Promise<Buffer> {
  const { data, info } = await sharp(src).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const ch = info.channels;
  for (let y = 0; y < info.height; y++) {
    for (let x = 0; x < info.width; x++) {
      const i = (y * info.width + x) * ch;
      const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      const sat = Math.max(r, g, b) - Math.min(r, g, b);
      // bílé písmo etikety je neprůhledné → zůstane; pryč jen šedé poloprůhledné a šedé u dna
      if (sat < 40 && lum > 90 && (a < 245 || y > info.height * 0.86)) data[i + 3] = 0;
    }
  }
  return sharp(data, { raw: info }).trim().resize({ height: vyska }).png().toBuffer();
}

async function svetleLogo(src: string): Promise<Buffer> {
  const { data, info } = await sharp(src).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  for (let i = 0; i < data.length; i += info.channels) {
    const r = data[i], g = data[i + 1], b = data[i + 2];
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    if (sat < 40 && 0.299 * r + 0.587 * g + 0.114 * b < 140) { data[i] = 255; data[i + 1] = 255; data[i + 2] = 255; }
  }
  return sharp(data, { raw: info }).png().toBuffer();
}

const hvezda = (x: number, s: number, barva: string) =>
  `<path transform="translate(${x} 0) scale(${s})" d="M12 1.5l3.1 6.6 7.2.9-5.3 5 1.4 7.1L12 17.6 5.6 21.1 7 14l-5.3-5 7.2-.9z" fill="${barva}"/>`;

export async function renderGrafik(spec: GrafikSpec, W: number, H: number): Promise<Buffer> {
  const [stred, okraj] = Array.isArray(spec.pozadi) ? spec.pozadi : [spec.pozadi, spec.pozadi];
  const tvary = (spec.tvary ?? []).map((t, k) => {
    if ('kruh' in t) {
      const [cx, cy, r] = t.kruh;
      const fill = t.prechod ? `url(#t${k})` : t.barva;
      const grad = t.prechod
        ? `<defs><radialGradient id="t${k}" cx="0.5" cy="0.45" r="0.5"><stop offset="0" stop-color="${t.prechod}"/><stop offset="1" stop-color="${t.barva}"/></radialGradient></defs>`
        : '';
      return `${grad}<circle cx="${Math.round(W * cx)}" cy="${Math.round(H * cy)}" r="${Math.round(W * r)}" fill="${fill}"/>`;
    }
    const [x, y, w, h, rr] = t.obdelnik;
    return `<rect x="${Math.round(W * x)}" y="${Math.round(H * y)}" width="${Math.round(W * w)}" height="${Math.round(H * h)}" rx="${rr}" fill="${t.barva}"/>`;
  }).join('');

  let img = await sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
<defs><radialGradient id="bg" cx="0.75" cy="0.6" r="0.8"><stop offset="0" stop-color="${stred}"/><stop offset="1" stop-color="${okraj}"/></radialGradient></defs>
<rect width="${W}" height="${H}" fill="url(#bg)"/>${tvary}</svg>`)).png().toBuffer();

  const vrstvy: sharp.OverlayOptions[] = [];

  if (spec.svetla) {
    // pevně dané pozice (stejný výsledek při každém přesazení), různé velikosti a jas
    const body = [[0.62, 0.08, 46], [0.82, 0.14, 30], [0.93, 0.05, 54], [0.71, 0.22, 22], [0.9, 0.3, 38], [0.55, 0.3, 18],
      [0.97, 0.42, 26], [0.6, 0.5, 14], [0.78, 0.36, 16], [0.48, 0.12, 20], [0.86, 0.56, 20], [0.68, 0.04, 16]];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">${body.map(([x, y, r], k) =>
      `<circle cx="${Math.round(W * x)}" cy="${Math.round(H * y)}" r="${r}" fill="#ffc768" fill-opacity="${(0.35 + (k % 4) * 0.12).toFixed(2)}"/>`).join('')}</svg>`;
    vrstvy.push({ input: await sharp(Buffer.from(svg)).blur(9).png().toBuffer(), left: 0, top: 0, blend: 'screen' });
  }

  // produkt: kontaktní stín pod dnem + měkký stín ze siluety + skutečná fotka
  const p = spec.produkt;
  const vyska = Math.round(H * p.vyska);
  const prod = await cistyProdukt(p.src, vyska);
  const pm = await sharp(prod).metadata();
  const cx = Math.round(W * p.cx), dno = Math.round(H * p.dno);
  const px = cx - Math.round(pm.width! / 2), py = dno - vyska;
  const stinBarva = p.tmave ? '#000000' : '#2a1626';
  const kontakt = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
<ellipse cx="${cx}" cy="${dno - 4}" rx="${Math.round(pm.width! * 0.47)}" ry="15" fill="${stinBarva}" fill-opacity="${p.tmave ? 0.7 : 0.55}"/></svg>`);
  const alpha = await sharp(prod).extractChannel(3).toBuffer();
  const silueta = await sharp({ create: { width: pm.width!, height: vyska, channels: 3, background: stinBarva } })
    .joinChannel(alpha).png().toBuffer();
  const pad = 110;
  const mekky = await sharp({ create: { width: pm.width! + pad * 2, height: vyska + pad * 2, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: silueta, left: pad, top: pad }]).blur(38).linear([1, 1, 1, p.tmave ? 0.45 : 0.26], [0, 0, 0, 0]).png().toBuffer();
  vrstvy.push(
    { input: await sharp(kontakt).blur(9).png().toBuffer(), left: 0, top: 0 },
    { input: mekky, left: px - pad + 16, top: py - pad + 24 },
    { input: prod, left: px, top: py },
  );

  if (spec.odznak) {
    const o = spec.odznak;
    const r = Math.round(W * o.r), ox = Math.round(W * o.cx), oy = Math.round(H * o.cy);
    const stin = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><circle cx="${ox}" cy="${oy + 10}" r="${r}" fill="#000" fill-opacity="0.22"/></svg>`;
    vrstvy.push({ input: await sharp(Buffer.from(stin)).blur(14).png().toBuffer(), left: 0, top: 0 });
    vrstvy.push({ input: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><circle cx="${ox}" cy="${oy}" r="${r}" fill="${o.barva}"/></svg>`), left: 0, top: 0 });
  }

  if (spec.logo) {
    const l = spec.logo;
    const src = l.svetle ? await svetleLogo(l.src) : l.src;
    vrstvy.push({ input: await sharp(src).resize({ width: Math.round(W * l.w) }).png().toBuffer(), left: Math.round(W * l.x), top: Math.round(H * l.y) });
  }

  if (spec.hvezdy) {
    const b = spec.hvezdy.barva ?? '#ffbb00';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="160" height="30">${[0, 30, 60, 90, 120].map(x => hvezda(x, 1.15, b)).join('')}</svg>`;
    vrstvy.push({ input: Buffer.from(svg), left: Math.round(W * spec.hvezdy.x), top: Math.round(H * spec.hvezdy.y) });
  }

  img = await sharp(img).composite(vrstvy).png().toBuffer();

  const zrno = spec.zrno ?? 0.035;
  if (zrno > 0) {
    const noise = await sharp({ create: { width: W, height: H, channels: 3, noise: { type: 'gaussian', mean: 128, sigma: 10 } } })
      .greyscale().png().toBuffer();
    img = await sharp(img).composite([{ input: await sharp(noise).ensureAlpha(zrno).png().toBuffer(), blend: 'overlay' }]).png().toBuffer();
  }
  return img;
}

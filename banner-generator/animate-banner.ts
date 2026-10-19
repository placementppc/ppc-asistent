/**
 * Rozhýbe hotový PNG banner na jednoduché MP4 video — text z banneru přiletí.
 *
 * Plně automatické, nic se neopisuje ručně:
 *   1) Gemini odstraní z banneru všechen text → čisté pozadí ("plate")
 *   2) sharp porovná originál vs. plate → rozdíl = pixely textu → průhledná textová vrstva
 *   3) HTML wrapper: pozadí stojí, textová vrstva přiletí zdola + fade, k tomu shimmer/glow/sparkles
 *   4) puppeteer nahraje snímky → ffmpeg složí MP4 (H.264, Meta-ready)
 *
 * Použití:
 *   npx tsx animate-banner.ts banners-ukazka/gemini_k1-automat_banner_1080x1080.png
 *   (vzorový banner vznikne z configs/ukazka.ts; jinak dej cestu ke svému PNG)
 *
 * Parametry (volitelné):
 *   --preset=jemny      jemny | vyrazny (default jemny) — síla ambient efektů
 *   --duration=5        délka videa v sekundách (default 5)
 *   --fps=30            snímků za sekundu (default 30)
 *   --threshold=40      citlivost odmaskování textu 10–120 (níž = víc textu, víc šumu)
 *   --no-text           přeskoč Gemini vrstvení, jen ambient pohyb celého banneru
 *   --force             přegeneruj plate i kdyby cache existovala
 */

import puppeteer from 'puppeteer';
import sharp from 'sharp';
import { execSync } from 'child_process';
import { createRequire } from 'module';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const require = createRequire(import.meta.url);

const args = process.argv.slice(2);
const pngArg = args.find(a => !a.startsWith('--'));

if (!pngArg) {
  console.error('Použití: npx tsx animate-banner.ts <cesta-k-banneru.png> [--preset=jemny] [--duration=5] [--fps=30] [--no-text]');
  process.exit(1);
}

const preset = args.find(a => a.startsWith('--preset='))?.split('=')[1] || 'jemny';
const duration = parseInt(args.find(a => a.startsWith('--duration='))?.split('=')[1] || '5');
const fps = parseInt(args.find(a => a.startsWith('--fps='))?.split('=')[1] || '30');
const threshold = parseInt(args.find(a => a.startsWith('--threshold='))?.split('=')[1] || '40');
const noText = args.includes('--no-text');
const force = args.includes('--force');
// --all-text = starý režim (všechen text přiletí najednou zespodu).
// Default = přijede jen horní nadpis, zbytek textu zůstane statický.
const allText = args.includes('--all-text');
// --head-band=0.47,0.64 = ruční pás nadpisu (podíly výšky) místo auto-detekce.
const headBandArg = args.find(a => a.startsWith('--head-band='))?.split('=')[1];
// --head-rect=l,t,r,b = ruční obdélník nadpisu (podíly šířky/výšky). Nutné když je text ve sloupcích.
const headRectArg = args.find(a => a.startsWith('--head-rect='))?.split('=')[1];
// --glint = přejezd slunečního světla přes horní fotku + jiskra (lens-flare). Vhodné na produktové fotky.
const glint = args.includes('--glint');
// --eyes=30,40;70,40 = jiskřičky v očích (maskot/postava); každá dvojice = pozice oka v % (x,y), postupně bliknou.
const eyesArg = args.find(a => a.startsWith('--eyes='))?.split('=')[1];
// --smoke=50,30 = stoupající kouř z bodu (x,y v %). Vhodné na kouř/páru z produktu.
const smokeArg = args.find(a => a.startsWith('--smoke='))?.split('=')[1];
// --slam = nadpis „přiletí a bouchne" (úderový nálet: zvětšený → dosedne s překmitem + otřes + náraz).
const slam = args.includes('--slam');
// --flare=66,18 = pozice jiskry v % (x,y). Default = pravý horní roh fotky.
const flareArg = args.find(a => a.startsWith('--flare='))?.split('=')[1];
// --photo=0.43 = podíl výšky, kam až sahá horní fotka (jinak auto-detekce tmavého panelu).
const photoArg = parseFloat(args.find(a => a.startsWith('--photo='))?.split('=')[1] || '');

const pngPath = path.resolve(pngArg);
if (!fs.existsSync(pngPath)) {
  console.error(`Soubor nenalezen: ${pngPath}`);
  process.exit(1);
}

const dir = path.dirname(pngPath);
const base = path.basename(pngPath, path.extname(pngPath));
const platePath = path.join(dir, `${base}_anim-plate.png`);
const textPath = path.join(dir, `${base}_anim-text.png`);      // celý text (režim --all-text)
const headPath = path.join(dir, `${base}_anim-text-head.png`); // horní nadpis (animuje se)
const restPath = path.join(dir, `${base}_anim-text-rest.png`); // zbytek textu (statický)
const bgPath = path.join(dir, `${base}_anim-bg.png`);          // pozadí s vyčištěnou oblastí nadpisu
const outputFile = path.join(dir, `${base}_animated.mp4`);

// ---------- ffmpeg lokace ----------
function resolveFfmpeg(): string {
  // 1) npm balíček ffmpeg-static (správný binár pro tuhle platformu, bez brew)
  try {
    const p = require('ffmpeg-static');
    if (p && fs.existsSync(p)) {
      execSync(`"${p}" -version`, { stdio: 'ignore' });
      return `"${p}"`;
    }
  } catch { /* není nainstalovaný, zkus systém */ }

  // 2) systémový ffmpeg
  const candidates = ['ffmpeg', '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/tmp/ffmpeg'];
  for (const c of candidates) {
    try {
      execSync(`${c} -version`, { stdio: 'ignore' });
      return c;
    } catch { /* zkus další */ }
  }
  console.error('❌ ffmpeg nenalezen. Nainstaluj ho: npm install ffmpeg-static   (nebo brew install ffmpeg)');
  process.exit(1);
}

// ---------- Gemini: odstranění textu → plate ----------
function loadApiKey(): string {
  const envPath = path.resolve('.env.local');
  if (!fs.existsSync(envPath)) {
    console.error('Chybí .env.local — zkopíruj .env.example a doplň GEMINI_API_KEY');
    process.exit(1);
  }
  const envText = fs.readFileSync(envPath, 'utf-8');
  const key = envText.match(/GEMINI_API_KEY\s*=\s*(.+)/)?.[1].trim().replace(/^["']|["']$/g, '');
  if (!key) {
    console.error('GEMINI_API_KEY nenalezen v .env.local');
    process.exit(1);
  }
  return key;
}

const MODEL = 'gemini-3.1-flash-image-preview';

const REMOVE_TEXT_PROMPT = `You are editing an advertising banner image. Remove ALL text from the image — every headline, sub-headline, caption, button label, price, number, letter and any typographic word-mark. Reconstruct the background that was behind the removed text completely naturally and seamlessly: match the surrounding colors, gradients, textures, lighting and patterns so there is absolutely no trace, smudge or blur where text used to be. Do NOT move, resize, recolor or remove any product, person, illustration, photo or non-text graphic element — keep every non-text pixel identical. Keep the exact same dimensions and aspect ratio. Output only the cleaned image.`;

async function generatePlate(): Promise<void> {
  if (fs.existsSync(platePath) && !force) {
    console.log(`♻️  Plate z cache: ${path.basename(platePath)} (--force pro přegenerování)`);
    return;
  }
  const apiKey = loadApiKey();
  // Klíč jde v hlavičce x-goog-api-key, ne v URL — URL se objevuje v chybových hláškách a logu.
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;
  const data = fs.readFileSync(pngPath).toString('base64');
  const ext = path.extname(pngPath).toLowerCase();
  const inMime = ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' : ext === '.webp' ? 'image/webp' : 'image/png';

  const body = {
    contents: [{
      parts: [
        { inlineData: { mimeType: inMime, data } },
        { text: REMOVE_TEXT_PROMPT },
      ],
    }],
    generationConfig: { responseModalities: ['IMAGE', 'TEXT'] },
  };

  console.log('🧹 Gemini odstraňuje text z banneru…');
  let lastErr = '';
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        lastErr = `HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`;
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
        continue;
      }
      const json = await res.json();
      const partsOut = json?.candidates?.[0]?.content?.parts ?? [];
      const imgPart = partsOut.find((p: any) => p.inlineData?.data);
      if (!imgPart) {
        lastErr = `žádný obrázek (finish=${json?.candidates?.[0]?.finishReason})`;
        await new Promise(r => setTimeout(r, 1500));
        continue;
      }
      fs.writeFileSync(platePath, Buffer.from(imgPart.inlineData.data, 'base64'));
      console.log(`   ✅ plate: ${path.basename(platePath)}`);
      return;
    } catch (e: any) {
      lastErr = e.message || String(e);
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }
  console.error(`❌ Odstranění textu selhalo: ${lastErr}`);
  process.exit(1);
}

// ---------- sharp: diff originál vs. plate → alfa textu ----------
async function computeTextAlpha(width: number, height: number): Promise<{ origRaw: Buffer; plateRaw: Buffer; alpha: Uint8Array; textPx: number }> {
  const origRaw = await sharp(pngPath).removeAlpha().resize(width, height, { fit: 'fill' }).raw().toBuffer();
  const plateRaw = await sharp(platePath).removeAlpha().resize(width, height, { fit: 'fill' }).raw().toBuffer();

  const px = width * height;
  const alpha = new Uint8Array(px);
  let textPx = 0;
  for (let i = 0; i < px; i++) {
    const diff = Math.max(
      Math.abs(origRaw[i * 3] - plateRaw[i * 3]),
      Math.abs(origRaw[i * 3 + 1] - plateRaw[i * 3 + 1]),
      Math.abs(origRaw[i * 3 + 2] - plateRaw[i * 3 + 2]),
    );
    if (diff > threshold) {
      alpha[i] = Math.min(255, (diff - threshold) * 5);
      textPx++;
    }
  }
  if (textPx / px > 0.45) {
    console.warn('   ⚠️  Odmaskováno >45 % plochy — práh je možná moc nízký nebo Gemini změnil i pozadí.');
    console.warn('       Zkus --threshold=60 nebo --no-text.');
  }
  return { origRaw, plateRaw, alpha, textPx };
}

// Vyčistí pozadí v obdélníku nadpisu: když je tam jednolité pozadí (panel), přemaluje ho jeho průměrnou
// barvou → zmizí případný zbytek textu, který Gemini v plate úplně nesmazal. Na členitém pozadí ponechá plate.
async function cleanHeadBg(plateRaw: Buffer, alpha: Uint8Array, width: number, height: number, top: number, bottom: number, left: number, right: number, outPath: string): Promise<boolean> {
  let n = 0, sr = 0, sg = 0, sb = 0;
  for (let y = top; y < bottom; y++) {
    for (let x = left; x < right; x++) {
      const i = y * width + x;
      if (alpha[i] === 0) { sr += plateRaw[i * 3]; sg += plateRaw[i * 3 + 1]; sb += plateRaw[i * 3 + 2]; n++; }
    }
  }
  if (n < 50) return false;
  const mr = sr / n, mg = sg / n, mb = sb / n;
  // odchylka pozadí (jak moc je jednolité)
  let dev = 0;
  for (let y = top; y < bottom; y++) {
    for (let x = left; x < right; x++) {
      const i = y * width + x;
      if (alpha[i] === 0) dev += Math.abs(plateRaw[i * 3] - mr) + Math.abs(plateRaw[i * 3 + 1] - mg) + Math.abs(plateRaw[i * 3 + 2] - mb);
    }
  }
  if (dev / n / 3 > 22) return false; // členité pozadí → neměň, nech plate

  const out = Buffer.from(plateRaw);
  for (let y = top; y < bottom; y++) {
    for (let x = left; x < right; x++) {
      const i = y * width + x;
      out[i * 3] = mr; out[i * 3 + 1] = mg; out[i * 3 + 2] = mb;
    }
  }
  await sharp(out, { raw: { width, height, channels: 3 } }).png().toFile(outPath);
  return true;
}

// Auto-detekce pásu hlavního nadpisu = nejvýraznější (nejhustší) blok textu, kdekoli na banneru.
// Mezi „velkými" bloky vybere ten nejvýše položený a přilehlé velké bloky (víceřádkový nadpis) sloučí.
function detectHeadBand(alpha: Uint8Array, width: number, height: number): { top: number; bottom: number } {
  const rc = new Array(height).fill(0);
  for (let i = 0; i < alpha.length; i++) {
    if (alpha[i] > 30) rc[(i / width) | 0]++;
  }
  const minRow = Math.max(3, width * 0.004);

  // Rozsekej na bloky (souvislé řádky s textem) + jejich špičkovou hustotu.
  const bands: { top: number; bottom: number; peak: number }[] = [];
  let s = -1, peak = 0;
  for (let y = 0; y <= height; y++) {
    const texty = y < height && rc[y] > minRow;
    if (texty) { if (s < 0) { s = y; peak = 0; } if (rc[y] > peak) peak = rc[y]; }
    else if (s >= 0) { bands.push({ top: s, bottom: y, peak }); s = -1; }
  }
  if (!bands.length) return { top: 0, bottom: Math.round(height * 0.22) };

  // Hlavní nadpis = blok s největší VÝŠKOU (≈ velikost písma), ne jen hustotou řádku.
  // Při shodě výšky preferuj ten nejvýše (typicky hlavní headline). Přilehlé stejně vysoké řádky (víceřádkový nadpis) sluč.
  bands.sort((a, b) => a.top - b.top);
  const heightOf = (b: { top: number; bottom: number }) => b.bottom - b.top;
  const maxH = Math.max(...bands.map(heightOf));
  let si = bands.findIndex(b => heightOf(b) >= 0.9 * maxH);
  if (si < 0) si = 0;
  const seedH = heightOf(bands[si]);
  let top = bands[si].top, bottom = bands[si].bottom;
  for (let k = si + 1; k < bands.length; k++) {
    if (bands[k].top - bottom < height * 0.05 && heightOf(bands[k]) >= 0.5 * seedH) bottom = bands[k].bottom;
    else break;
  }
  for (let k = si - 1; k >= 0; k--) {
    if (top - bands[k].bottom < height * 0.05 && heightOf(bands[k]) >= 0.5 * seedH) top = bands[k].top;
    else break;
  }
  return { top: Math.max(0, top - Math.round(height * 0.006)), bottom: Math.min(height, bottom + Math.round(height * 0.01)) };
}

// Auto-detekce spodní hrany horní fotky = vrch souvislého tmavého panelu odspodu.
function detectPhotoBottom(origRaw: Buffer, width: number, height: number): number {
  const lum = new Array(height).fill(0);
  for (let y = 0; y < height; y++) {
    let sum = 0;
    for (let x = 0; x < width; x += 4) {
      const i = (y * width + x) * 3;
      sum += 0.299 * origRaw[i] + 0.587 * origRaw[i + 1] + 0.114 * origRaw[i + 2];
    }
    lum[y] = sum / Math.ceil(width / 4);
  }
  let darkTop = height;
  for (let y = height - 1; y >= 0; y--) {
    if (lum[y] < 45) darkTop = y; else break;
  }
  const frac = darkTop / height;
  return frac > 0.2 && frac < 0.85 ? darkTop : Math.round(height * 0.58);
}

// Zapíše textovou vrstvu jen z obdélníku [left,right)×[top,bottom); invert = naopak všechno KROMĚ obdélníku.
async function writeBand(origRaw: Buffer, alpha: Uint8Array, width: number, height: number, top: number, bottom: number, outPath: string, invert = false, left = 0, right = width): Promise<void> {
  const px = width * height;
  const out = Buffer.alloc(px * 4);
  for (let i = 0; i < px; i++) {
    const row = (i / width) | 0;
    const col = i - row * width;
    const inRect = row >= top && row < bottom && col >= left && col < right;
    out[i * 4] = origRaw[i * 3];
    out[i * 4 + 1] = origRaw[i * 3 + 1];
    out[i * 4 + 2] = origRaw[i * 3 + 2];
    out[i * 4 + 3] = (invert ? !inRect : inRect) ? alpha[i] : 0;
  }
  await sharp(out, { raw: { width, height, channels: 4 } }).blur(0.6).png().toFile(outPath);
}

// ---------- HTML wrapper ----------
function buildHtml(width: number, height: number, mode: 'none' | 'all' | 'head', glintCfg: { photoH: number; fx: number; fy: number } | null, bgImg: string, smokeCfg: { x: number; y: number } | null, headCenter: { cx: number; cy: number } | null): string {
  const strong = preset === 'vyrazny';

  const fileUrl = (p: string) => `file://${p}`;

  // sparkles — pozice jako procenta, generické bílo-zlaté tečky
  const sparkles = [
    { x: 14, y: 30, s: 5, c: '255,255,255,0.7', d: 2.0, t: 4.0 },
    { x: 82, y: 44, s: 3, c: '255,210,120,0.6', d: 2.6, t: 5.0 },
    { x: 55, y: 24, s: 4, c: '255,255,255,0.5', d: 3.0, t: 4.5 },
    { x: 30, y: 66, s: 3, c: '255,210,120,0.6', d: 3.4, t: 5.0 },
    { x: 70, y: 60, s: 4, c: '255,255,255,0.45', d: 4.0, t: 4.0 },
    ...(strong ? [
      { x: 44, y: 78, s: 4, c: '255,255,255,0.5', d: 3.2, t: 4.5 },
      { x: 88, y: 22, s: 3, c: '255,210,120,0.55', d: 2.2, t: 5.0 },
      { x: 20, y: 48, s: 5, c: '255,255,255,0.6', d: 3.8, t: 4.2 },
    ] : []),
  ];

  const sparkleCss = sparkles.map((sp, i) => `
.sparkle:nth-child(${i + 1}) {
  width: ${sp.s}px; height: ${sp.s}px;
  background: rgba(${sp.c});
  top: ${sp.y}%; left: ${sp.x}%;
  animation: sparkleFloat ${sp.t}s ${sp.d}s ease-in-out infinite;
}`).join('\n');

  const sparkleDivs = sparkles.map(() => '<div class="sparkle"></div>').join('\n');

  const layerImg = `width: ${width}px; height: ${height}px; display: block;`;
  const rise = Math.round(height * 0.035);

  // Sestavení textových vrstev podle režimu:
  //  'head' = jen horní nadpis přijede (pomalu, moderně: vyjede nahoru + rozostření do ostra + fade),
  //           zbytek textu statický na místě.
  //  'all'  = starý režim, všechen text přiletí najednou zespodu.
  let textLayerHtml = '';
  let textLayerCss = '';

  if (mode === 'head') {
    textLayerHtml = `
  <div class="text-rest"><img src="${fileUrl(restPath)}" alt=""></div>
  <div class="text-head"><img src="${fileUrl(headPath)}" alt=""></div>`;
    textLayerCss = `
/* zbytek textu (CTA, popisky) — statický, viditelný hned od 1. snímku */
.text-rest { position: absolute; top: 0; left: 0; z-index: 6; }
.text-rest img { ${layerImg} }

${slam ? `
/* horní nadpis — PŘILETÍ A BOUCHNE: zvětšený dolétne, dosedne s nárazem a překmitem */
.text-head { position: absolute; top: 0; left: 0; z-index: 7; opacity: 0; transform: scale(1.6); transform-origin: ${headCenter ? headCenter.cx : 50}% ${headCenter ? headCenter.cy : 50}%; animation: headSlam 0.8s 0.6s cubic-bezier(0.55, 0, 0.85, 0.2) forwards; }
.text-head img { ${layerImg} }
@keyframes headSlam {
  0%   { opacity: 0; transform: scale(1.6); }
  40%  { opacity: 1; }
  58%  { opacity: 1; transform: scale(0.92); }                 /* DOSEDNUTÍ — náraz */
  70%  { opacity: 1; transform: scale(1.06) translateY(-7px); }/* odskok */
  82%  { opacity: 1; transform: scale(0.98) translateY(4px); }
  92%  { opacity: 1; transform: scale(1.012) translateY(-1px); }
  100% { opacity: 1; transform: scale(1.0) translateY(0); }
}` : `
/* horní nadpis — moderní příjezd: vyjede nahoru + rozostření do ostra + fade, pomaleji */
.text-head { position: absolute; top: 0; left: 0; z-index: 7; opacity: 0; transform: translateY(${rise}px); filter: blur(10px); animation: headIn 1.3s 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
.text-head img { ${layerImg} }
@keyframes headIn {
  0%   { opacity: 0; transform: translateY(${rise}px); filter: blur(10px); }
  55%  { opacity: 1; }
  100% { opacity: 1; transform: translateY(0); filter: blur(0); }
}`}`;
  } else if (mode === 'all') {
    const drop = Math.round(height * 0.05);
    textLayerHtml = `
  <div class="text-layer"><img src="${fileUrl(textPath)}" alt=""></div>`;
    textLayerCss = `
.text-layer { position: absolute; top: 0; left: 0; z-index: 7; opacity: 0; transform: translateY(${drop}px); animation: textFlyIn 0.9s 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
.text-layer img { ${layerImg} }
@keyframes textFlyIn {
  0%   { opacity: 0; transform: translateY(${drop}px); }
  100% { opacity: 1; transform: translateY(0); }
}`;
  }

  // glint = přejezd slunečního světla přes horní fotku + jiskra (lens-flare). Nahrazuje plošný shimmer.
  const beamOp = strong ? 1.0 : 0.85;
  const glintCss = glintCfg ? `
.glint { position: absolute; top: 0; left: 0; width: ${width}px; height: ${glintCfg.photoH}px; overflow: hidden; pointer-events: none; z-index: 8; }
.glint-beam { position: absolute; top: -20%; left: -50%; width: 26%; height: 140%; transform: rotate(10deg); filter: blur(5px); opacity: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,246,220,0) 18%, rgba(255,251,238,${beamOp}) 50%, rgba(255,246,220,0) 82%, transparent 100%);
  animation: glintSweep 1.8s 1.9s ease-in-out forwards; }
@keyframes glintSweep { 0% { left: -50%; opacity: 0; } 12% { opacity: 1; } 88% { opacity: 1; } 100% { left: 125%; opacity: 0; } }
.flare { position: absolute; left: ${glintCfg.fx}%; top: ${glintCfg.fy}%; width: 0; height: 0; z-index: 9; pointer-events: none; }
.flare::before, .flare::after { content: ''; position: absolute; transform: translate(-50%,-50%) scale(0.3); opacity: 0; }
.flare::before { width: 200px; height: 200px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,250,235,1) 0%, rgba(255,238,205,0.6) 22%, rgba(255,230,190,0.18) 45%, transparent 70%);
  animation: flarePulse 2.6s 2.05s ease-in-out forwards; }
.flare::after { width: 300px; height: 300px;
  background:
    linear-gradient(0deg, transparent 47%, rgba(255,251,238,0.95) 50%, transparent 53%),
    linear-gradient(90deg, transparent 47%, rgba(255,251,238,0.95) 50%, transparent 53%),
    linear-gradient(45deg, transparent 48.5%, rgba(255,248,228,0.7) 50%, transparent 51.5%),
    linear-gradient(135deg, transparent 48.5%, rgba(255,248,228,0.7) 50%, transparent 51.5%);
  animation: flareStar 2.6s 2.05s ease-in-out forwards; }
@keyframes flarePulse { 0% { opacity: 0; transform: translate(-50%,-50%) scale(0.3); } 40% { opacity: 1; transform: translate(-50%,-50%) scale(1.25); } 70% { opacity: 0.85; transform: translate(-50%,-50%) scale(1.05); } 100% { opacity: 0; transform: translate(-50%,-50%) scale(0.9); } }
@keyframes flareStar { 0% { opacity: 0; transform: translate(-50%,-50%) scale(0.2) rotate(0deg); } 45% { opacity: 1; transform: translate(-50%,-50%) scale(1) rotate(18deg); } 100% { opacity: 0; transform: translate(-50%,-50%) scale(0.55) rotate(38deg); } }` : '';

  const glintHtml = glintCfg ? `
  <div class="glint"><div class="glint-beam"></div></div>
  <div class="flare"></div>` : '';
  const shimmerHtml = glintCfg ? '' : '<div class="shimmer"></div>';

  // jiskřičky v očích maskota/postavy — postupně bliknou (dvojitý záblesk)
  const eyes = eyesArg
    ? eyesArg.split(';').map(s => s.split(',').map(parseFloat)).filter(p => p.length === 2 && p.every(Number.isFinite))
    : [];
  const eyesHtml = eyes.map((p, i) => `<div class="eye" style="left:${p[0]}%;top:${p[1]}%;--ed:${(2.0 + i * 0.35).toFixed(2)}s"></div>`).join('\n  ');

  // stoupající kouř/pára z produktu
  // POZN.: snímkování nastavuje animation currentTime → fungují jen KONEČNÉ (forwards) animace,
  // nikoli `infinite`. Plynulý kouř proto děláme víc obláčky s konečným náletem a posunutým startem.
  const puffDelays = [0, 0.42, 0.84, 1.26, 1.68, 2.1, 2.52, 2.94];
  const smokeCss = smokeCfg ? `
.smoke { position: absolute; left: ${smokeCfg.x}%; top: ${smokeCfg.y}%; width: 0; height: 0; z-index: 9; pointer-events: none; }
.smoke span { position: absolute; left: 0; top: 0; width: 125px; height: 125px; border-radius: 50%; filter: blur(8px); opacity: 0;
  background: radial-gradient(circle, rgba(38,36,35,0.92) 0%, rgba(48,45,44,0.7) 38%, rgba(60,57,55,0.3) 58%, transparent 74%);
  transform: translate(-50%,-50%) scale(0.25); }
${puffDelays.map((d, i) => `.smoke span:nth-child(${i + 1}) { animation: puff 2.6s ${d}s ease-out forwards; }`).join('\n')}
@keyframes puff {
  0%   { opacity: 0;    transform: translate(-50%,-50%) translate(0,0) scale(0.25); }
  14%  { opacity: 0.9;  }
  55%  { opacity: 0.5;  }
  100% { opacity: 0;    transform: translate(-50%,-50%) translate(-46px,-225px) scale(2.2); }
}` : '';
  const smokeHtml = smokeCfg ? `<div class="smoke">${puffDelays.map(() => '<span></span>').join('')}</div>` : '';

  // náraz pod nadpisem při „bouchnutí" (jen se --slam)
  const impactCss = (slam && headCenter) ? `
.impact { position: absolute; left: ${headCenter.cx}%; top: ${headCenter.cy}%; width: 0; height: 0; z-index: 6; pointer-events: none; }
.impact::before { content: ''; position: absolute; opacity: 0; transform: translate(-50%,-50%) scaleX(0.15) scaleY(0.4);
  width: ${Math.round(width * 0.55)}px; height: 44px; border-radius: 50%;
  background: radial-gradient(ellipse, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0.14) 45%, transparent 72%);
  animation: impactBurst 0.55s 0.92s ease-out forwards; }
@keyframes impactBurst {
  0%   { opacity: 0;   transform: translate(-50%,-50%) scaleX(0.15) scaleY(0.4); }
  25%  { opacity: 0.8; }
  100% { opacity: 0;   transform: translate(-50%,-50%) scaleX(2.2) scaleY(1.3); }
}` : '';
  const impactHtml = (slam && headCenter) ? '<div class="impact"></div>' : '';
  const eyesCss = eyes.length ? `
.eye { position: absolute; width: 0; height: 0; z-index: 10; pointer-events: none; }
.eye::before, .eye::after { content: ''; position: absolute; left: 0; top: 0; opacity: 0; transform: translate(-50%,-50%) scale(0); }
.eye::before { width: 30px; height: 30px; border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(255,255,255,0.55) 32%, transparent 70%); animation: eyeTwinkle 1.7s var(--ed) ease-in-out forwards; }
.eye::after { width: 56px; height: 56px;
  background: linear-gradient(0deg, transparent 46%, rgba(255,255,255,0.95) 50%, transparent 54%), linear-gradient(90deg, transparent 46%, rgba(255,255,255,0.95) 50%, transparent 54%);
  animation: eyeTwinkle 1.7s var(--ed) ease-in-out forwards; }
@keyframes eyeTwinkle {
  0% { opacity: 0; transform: translate(-50%,-50%) scale(0) rotate(0deg); }
  22% { opacity: 1; transform: translate(-50%,-50%) scale(1.15) rotate(12deg); }
  44% { opacity: 0.25; transform: translate(-50%,-50%) scale(0.7) rotate(22deg); }
  66% { opacity: 1; transform: translate(-50%,-50%) scale(1.0) rotate(34deg); }
  100% { opacity: 0; transform: translate(-50%,-50%) scale(0.4) rotate(46deg); }
}` : '';

  return `<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: ${width}px; height: ${height}px; overflow: hidden; background: #000; position: relative; }

/* pozadí (plate / nebo originál když --no-text) — viditelné hned od 1. snímku (žádný černý start), žádný zoom */
.bg-wrap { position: absolute; top: 0; left: 0; width: ${width}px; height: ${height}px; }
.bg-wrap img { width: ${width}px; height: ${height}px; display: block; }
@keyframes fadeIn { to { opacity: 1; } }

${textLayerCss}

/* shimmer — světelný přejezd přes banner */
.shimmer { position: absolute; top: 0; left: -80%; width: 45%; height: 100%;
  background: linear-gradient(105deg, transparent 0%, rgba(255,255,255,0.04) 40%, rgba(255,255,255,${strong ? '0.12' : '0.08'}) 50%, rgba(255,255,255,0.04) 60%, transparent 100%);
  animation: shimmerSweep ${strong ? '2.8s' : '3.2s'} 1.6s ease-in-out ${strong ? 'infinite' : 'forwards'}; pointer-events: none; z-index: 8; }
@keyframes shimmerSweep { 0% { left: -50%; } 100% { left: 130%; } }

/* glow — jemné dýchání světla po okrajích */
.glow { position: absolute; inset: 0; pointer-events: none; z-index: 5; opacity: 0;
  background: radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0) 55%, rgba(0,0,0,${strong ? '0.18' : '0.12'}) 100%);
  animation: glowFade 1s 0.8s ease-out forwards, glowPulse 4s 2s ease-in-out infinite; }
@keyframes glowFade { to { opacity: 1; } }
@keyframes glowPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }

/* sparkles */
.sparkle { position: absolute; border-radius: 50%; z-index: 9; opacity: 0; pointer-events: none; }
${sparkleCss}
@keyframes sparkleFloat {
  0%   { opacity: 0; transform: translateY(0) scale(0); }
  20%  { opacity: 0.9; transform: translateY(-6px) scale(1.2); }
  50%  { opacity: 0.7; transform: translateY(-12px) scale(1); }
  80%  { opacity: 0.4; transform: translateY(-20px) scale(0.7); }
  100% { opacity: 0; transform: translateY(-28px) scale(0.3); }
}
${glintCss}
${eyesCss}
${smokeCss}
${impactCss}
</style>
</head>
<body>
  <div class="bg-wrap"><img src="${fileUrl(bgImg)}" alt=""></div>
  ${smokeHtml}${textLayerHtml}
  <div class="glow"></div>
  ${shimmerHtml}${glintHtml}
  ${impactHtml}
  ${sparkleDivs}
  ${eyesHtml}
</body>
</html>`;
}

// ---------- render: puppeteer → frames → ffmpeg → mp4 ----------
async function renderMp4(html: string, width: number, height: number): Promise<void> {
  const ffmpeg = resolveFfmpeg();
  const totalFrames = duration * fps;
  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), 'banner-anim-'));
  const htmlPath = path.join(framesDir, 'banner.html');
  fs.writeFileSync(htmlPath, html);

  console.log(`🎬 ${duration}s @ ${fps}fps = ${totalFrames} snímků (${width}×${height})`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--font-render-hinting=none', `--window-size=${width},${height}`],
  });
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.evaluate(() => (document as any).fonts.ready);
  await new Promise(r => setTimeout(r, 800));

  await page.evaluate(() => { document.getAnimations().forEach(a => a.pause()); });

  console.log('📸 Nahrávám snímky…');
  for (let i = 0; i < totalFrames; i++) {
    const t = (i / fps) * 1000;
    await page.evaluate((time) => { document.getAnimations().forEach(a => { (a as any).currentTime = time; }); }, t);
    await new Promise(r => setTimeout(r, 8));
    await page.screenshot({
      path: path.join(framesDir, `frame_${String(i).padStart(5, '0')}.png`) as `${string}.png`,
      type: 'png',
      clip: { x: 0, y: 0, width, height },
    });
    if (i % 30 === 0) process.stdout.write(`  ${Math.round((i / totalFrames) * 100)}%\r`);
  }
  console.log('  100%');
  await browser.close();

  console.log('🎥 Skládám MP4…');
  const cmd = [
    ffmpeg, '-y',
    '-framerate', String(fps),
    '-i', path.join(framesDir, 'frame_%05d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', '18',
    '-movflags', '+faststart',
    `"${outputFile}"`,
  ].join(' ');
  execSync(cmd, { stdio: 'inherit' });

  fs.rmSync(framesDir, { recursive: true });
  const mb = (fs.statSync(outputFile).size / 1024 / 1024).toFixed(1);
  console.log(`\n✅ Hotovo: ${outputFile} (${mb} MB)`);
}

async function main() {
  const meta = await sharp(pngPath).metadata();
  const width = meta.width!;
  const height = meta.height!;

  const mode: 'none' | 'all' | 'head' = noText ? 'none' : allText ? 'all' : 'head';
  console.log(`📐 Banner: ${path.basename(pngPath)} (${width}×${height}), preset=${preset}, režim=${mode}`);

  let origRaw: Buffer | null = null;
  let bgImg = pngPath; // mode 'none' → originál; jinak plate (příp. vyčištěné pozadí)
  let headCenter: { cx: number; cy: number } | null = null; // střed nadpisu v % (pro slam náraz)

  if (mode === 'none') {
    console.log('⏭️  --no-text: jen ambient pohyb celého banneru, text se nevrství.');
  } else {
    await generatePlate();
    const res = await computeTextAlpha(width, height);
    origRaw = res.origRaw;
    const { plateRaw, alpha, textPx } = res;
    const pct = ((textPx / (width * height)) * 100).toFixed(1);
    bgImg = platePath;

    if (mode === 'all') {
      await writeBand(origRaw, alpha, width, height, 0, height, textPath);
      console.log(`   ✅ textová vrstva: ${path.basename(textPath)} (${pct} % plochy = text)`);
    } else {
      let top: number, bottom: number, left = 0, right = width;
      if (headRectArg) {
        const [l, t, r, b] = headRectArg.split(',').map(parseFloat);
        left = Math.round(width * l); top = Math.round(height * t);
        right = Math.round(width * r); bottom = Math.round(height * b);
      } else if (headBandArg) {
        const [a, b] = headBandArg.split(',').map(parseFloat);
        top = Math.round(height * a); bottom = Math.round(height * b);
      } else {
        ({ top, bottom } = detectHeadBand(alpha, width, height));
      }
      await writeBand(origRaw, alpha, width, height, top, bottom, headPath, false, left, right);
      await writeBand(origRaw, alpha, width, height, top, bottom, restPath, true, left, right);
      headCenter = { cx: ((left + right) / 2 / width) * 100, cy: ((top + bottom) / 2 / height) * 100 };
      console.log(`   ✅ nadpis (animuje): obdélník x${left}–${right} y${top}–${bottom}  →  ${path.basename(headPath)}`);
      console.log(`   ✅ zbytek textu (statický): ${path.basename(restPath)} (${pct} % plochy = text celkem)`);

      // vyčistit případný zbytek nadpisu v pozadí (Gemini občas nesmaže úplně)
      const cleaned = await cleanHeadBg(plateRaw, alpha, width, height, top, bottom, left, right, bgPath);
      if (cleaned) { bgImg = bgPath; console.log('   🧽 pozadí pod nadpisem vyčištěno (jednolitý panel).'); }
      else console.log('   ℹ️  pozadí pod nadpisem je členité → ponechán plate (kdyby prosvítal zbytek, zkus --threshold výš).');
    }
  }

  // glint = přejezd slunce přes horní fotku + jiskra
  let glintCfg: { photoH: number; fx: number; fy: number } | null = null;
  if (glint) {
    if (!origRaw) origRaw = await sharp(pngPath).removeAlpha().resize(width, height, { fit: 'fill' }).raw().toBuffer();
    const photoH = Number.isFinite(photoArg) ? Math.round(height * photoArg) : detectPhotoBottom(origRaw, width, height);
    let fx = 66, fy = 18;
    if (flareArg) { const [a, b] = flareArg.split(',').map(parseFloat); fx = a; fy = b; }
    else { fy = Math.round((photoH / height) * 100 * 0.32); } // default jiskra v horní třetině fotky
    glintCfg = { photoH, fx, fy };
    console.log(`   ✨ glint přes fotku 0–${photoH}px, jiskra na ${fx}%,${fy}%`);
  }

  // kouř/pára z bodu
  let smokeCfg: { x: number; y: number } | null = null;
  if (smokeArg) {
    const [x, y] = smokeArg.split(',').map(parseFloat);
    if (Number.isFinite(x) && Number.isFinite(y)) { smokeCfg = { x, y }; console.log(`   💨 kouř z ${x}%,${y}%`); }
  }
  if (slam) console.log('   💥 nadpis: úderový nálet (přiletí a bouchne)');

  const html = buildHtml(width, height, mode, glintCfg, bgImg, smokeCfg, headCenter);
  await renderMp4(html, width, height);

  if (mode !== 'none') {
    console.log(`\n💡 Mezivýstupy ke kontrole: ${path.basename(platePath)} + textové vrstvy`);
    console.log('   Nadpis sedí špatně? Uprav pás: --head-band=0.47,0.64. Ošklivé okraje? --threshold=60.');
  }
}

main().catch(err => {
  // Jen zpráva, ne celý objekt chyby (ten může nést URL požadavku a hlavičky).
  console.error(`Chyba: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});

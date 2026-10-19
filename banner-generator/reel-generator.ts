/**
 * Generátor svislých reelů 9:16 (1080×1920) pro Meta — z reálných produktových obrázků.
 *
 * Proč takhle: image-to-video AI rozpadá text na produktu a dělá šestiprsté ruce.
 * Tady AI generuje POUZE pozadí (prázdný stůl, polička…) — výřezy produktu i titulky skládá
 * deterministicky kód. Pohyb je jednoduchý (pomalý nájezd, dosedání výřezů, pop-in textu)
 * plus jemný „z ruky" drift, aby záběr nepůsobil jako leštěná reklama.
 *
 * Použití:
 *   npx tsx reel-generator.ts <config>            # vyrenderuje všechny reely do MP4
 *   npx tsx reel-generator.ts <config> --scenes   # jen dogeneruje chybějící AI pozadí
 *   npx tsx reel-generator.ts <config> --only=r1  # jen jeden reel
 *   npx tsx reel-generator.ts <config> --probe    # jen 1 PNG na záběr (rychlá vizuální kontrola)
 *   npx tsx reel-generator.ts <config> --crf=23   # komprese (default 21), kvůli limitu 20 MB
 */

import puppeteer from 'puppeteer';
import sharp from 'sharp';
import { execFileSync } from 'child_process';
import { createRequire } from 'module';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { ReelConfig, ReelStyle, Reel, Shot, Caption, CardPlacement } from './lib/reel';

const require = createRequire(import.meta.url);
const ffmpegBin: string = require('ffmpeg-static');

const args = process.argv.slice(2);
const configName = args.find(a => !a.startsWith('--'));
if (!configName) {
  console.error('Použití: npx tsx reel-generator.ts <config> [--scenes] [--only=slug] [--probe] [--crf=21]');
  process.exit(1);
}
const scenesOnly = args.includes('--scenes');
const probe = args.includes('--probe');
const onlyArg = args.find(a => a.startsWith('--only='))?.split('=')[1];
const crf = args.find(a => a.startsWith('--crf='))?.split('=')[1] || '21';

/**
 * Neutrální výchozí styl titulků. Barvy a písmo konkrétního klienta patří do configu reelu
 * (`style`, hodnoty z BRAND-MANUAL.md) — tady se nic klientského nenastavuje.
 */
const DEFAULT_STYLE: Required<ReelStyle> = {
  text: '#FFFFFF',
  stroke: '#000000',
  accent: '#FFD60A',
  fontFamily: "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  fontCssUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@600;700;800&display=swap',
  captionSize: 98,
};

/** Styl z configu doplněný o výchozí hodnoty. */
function resolveStyle(cfg: ReelConfig): Required<ReelStyle> {
  const s = cfg.style ?? {};
  return {
    text: s.text ?? DEFAULT_STYLE.text,
    stroke: s.stroke ?? DEFAULT_STYLE.stroke,
    accent: s.accent ?? DEFAULT_STYLE.accent,
    fontFamily: s.fontFamily ?? DEFAULT_STYLE.fontFamily,
    fontCssUrl: s.fontCssUrl ?? DEFAULT_STYLE.fontCssUrl,
    captionSize: s.captionSize ?? DEFAULT_STYLE.captionSize,
  };
}

/** Hodnota do HTML atributu (URL písma z configu). */
function escAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function openaiKey(): string {
  const envPath = path.resolve('.env.local');
  const envText = fs.readFileSync(envPath, 'utf-8');
  const key = envText.match(/OPENAI_API_KEY\s*=\s*(.+)/)?.[1].trim().replace(/^["']|["']$/g, '');
  if (!key) throw new Error('OPENAI_API_KEY nenalezen v .env.local');
  return key;
}

/** Pozadí generujeme v 1088×1920 (gpt-image-2 chce násobky 16) a zmenšíme na 1080×1920. */
async function generateScenes(cfg: ReelConfig) {
  const assetsDir = path.join(cfg.outDir, '_assets');
  fs.mkdirSync(assetsDir, { recursive: true });
  const key = openaiKey();
  for (const scene of cfg.scenes) {
    const out = path.join(assetsDir, `${scene.file}.png`);
    if (fs.existsSync(out)) { console.log(`   ↩︎ ${scene.file}.png už existuje`); continue; }
    console.log(`   🎨 generuji ${scene.file}…`);
    const res = await fetch('https://api.openai.com/v1/images/generations', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'gpt-image-2',
        prompt: scene.prompt,
        n: 1,
        size: '1088x1920',
        quality: 'high',
        output_format: 'png',
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 500)}`);
    const json: any = await res.json();
    const buf = Buffer.from(json.data[0].b64_json, 'base64');
    await sharp(buf).resize(1080, 1920, { fit: 'cover' }).png().toFile(out);
    console.log(`   ✅ ${out}`);
  }
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function captionHtml(c: Caption | undefined, W: number, st: Required<ReelStyle>): string {
  if (!c) return '';
  const size = c.size ?? (c.at === 'top' ? st.captionSize + 2 : st.captionSize);
  const color = c.color === 'yellow' ? st.accent : st.text;
  const posClass = c.at === 'top' ? 'cap-top' : c.at === 'center' ? 'cap-center' : 'cap-bottom';
  const topStyle = c.top != null ? `top:${c.top}px;` : '';
  const stars = c.stars ? `<div class="stars">★★★★★</div>` : '';
  const sub = c.sub ? `<div class="sub">${esc(c.sub)}</div>` : '';
  const credit = c.credit ? `<div class="credit">${esc(c.credit)}</div>` : '';
  return `<div class="cap ${posClass}" style="${topStyle}">
    ${stars}
    <div class="cap-main" style="font-size:${size}px;color:${color};-webkit-text-stroke:${Math.round(size * 0.13)}px ${st.stroke}">${esc(c.text).replace(/\n/g, '<br>')}</div>
    ${sub}${credit}
  </div>`;
}

function cardHtml(card: CardPlacement, i: number, onPhoto: boolean): string {
  const anim = card.in ?? 'pop';
  const delay = card.delay ?? 0;
  const rot = card.rot ?? 0;
  const tilt = card.tilt ?? 0;
  return `<div class="slot" style="left:${card.x}%;top:${card.y}%;width:${card.w}%;--rot:${rot}deg;--tilt:${tilt}deg;--delay:${delay}s">
    <div class="enter enter-${anim}"><img class="shot-card${card.idle ? ' idle' : ''}${onPhoto ? ' on-photo' : ''}" src="file://${path.resolve(card.src)}"></div>
  </div>`;
}

function shotHtml(shot: Shot, W: number, H: number, st: Required<ReelStyle>): string {
  const bg = 'image' in shot.backdrop
    ? `background-image:url('file://${path.resolve(shot.backdrop.image)}');background-size:cover;background-position:center`
    : shot.backdrop.css;
  const motion = shot.bgMotion ?? 'in';
  const onPhoto = 'image' in shot.backdrop;
  const cards = (shot.cards ?? []).map((c, i) => cardHtml(c, i, onPhoto)).join('\n');

  return `<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8">
${st.fontCssUrl ? `<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="${escAttr(st.fontCssUrl)}" rel="stylesheet">` : ''}
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:${W}px; height:${H}px; overflow:hidden; background:#000; }
  .stage { position:relative; width:${W}px; height:${H}px; overflow:hidden;
           animation: handheld 9s ease-in-out infinite; }
  /* pozadí je zvětšené o 10 %, aby pohyb nikdy neodhalil okraj */
  .bg { position:absolute; left:-5%; top:-5%; width:110%; height:110%; ${bg};
        animation: bg-${motion} var(--dur) linear both; }
  .vignette { position:absolute; inset:0; pointer-events:none;
    background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.22) 100%); }
  .grain { position:absolute; inset:0; pointer-events:none; opacity:.055; mix-blend-mode:overlay;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/></filter><rect width='180' height='180' filter='url(%23n)'/></svg>"); }

  /* výřez produktu = 3 vrstvy: slot drží pozici a naklonění, enter dělá nálet, img jemně dýchá */
  .slot { position:absolute; perspective:2200px;
          transform: translate(-50%,-50%) rotate(var(--rot)); }
  .slot img { display:block; width:100%; height:auto;
              transform: rotateX(var(--tilt));
              filter: drop-shadow(0 16px 20px rgba(0,0,0,.30)) drop-shadow(0 3px 4px rgba(0,0,0,.35)); }
  /* výřez položený do fotky: mírně teplejší a tlumenější, ať nesvítí jako nalepený obrázek */
  .slot img.on-photo { filter: drop-shadow(0 16px 20px rgba(0,0,0,.32)) drop-shadow(0 3px 4px rgba(0,0,0,.38))
                               brightness(.975) saturate(.97) sepia(.07); }
  .enter-none        { animation:none; }
  .enter-pop         { animation: enter-pop .62s cubic-bezier(.2,1.5,.4,1) var(--delay) both; }
  .enter-drop        { animation: enter-drop .78s cubic-bezier(.22,1.25,.36,1) var(--delay) both; }
  .enter-slide-left  { animation: enter-sl .66s cubic-bezier(.22,1.2,.36,1) var(--delay) both; }
  .enter-slide-right { animation: enter-sr .66s cubic-bezier(.22,1.2,.36,1) var(--delay) both; }
  .shot-card.idle    { animation: card-idle 4.4s ease-in-out .6s infinite alternate; }

  .cap { position:absolute; left:0; width:100%; text-align:center; padding:0 72px;
         font-family:${st.fontFamily}; font-weight:800; line-height:1.1;
         paint-order: stroke fill; text-shadow: 0 12px 34px rgba(0,0,0,.35);
         animation: cap-in .5s cubic-bezier(.2,1.4,.4,1) .18s both; }
  .cap-top    { top:360px; }
  .cap-center { top:50%; transform:translateY(-50%); }
  .cap-bottom { top:1180px; }
  .cap-main   { letter-spacing:-.5px; white-space:pre-line; }
  .sub { margin-top:24px; font-size:54px; font-weight:700; color:${st.text}; white-space:pre-line;
         line-height:1.18; -webkit-text-stroke:8px ${st.stroke}; }
  .credit { margin-top:16px; font-size:46px; font-weight:600; color:${st.text}; white-space:pre-line;
            line-height:1.18; -webkit-text-stroke:7px ${st.stroke}; }
  .stars { font-size:78px; color:${st.accent}; letter-spacing:10px; margin-bottom:18px;
           -webkit-text-stroke:6px ${st.stroke}; }

  @keyframes handheld {
    0%   { transform: translate(0,0) rotate(0deg); }
    25%  { transform: translate(-5px,3px) rotate(.12deg); }
    50%  { transform: translate(4px,-4px) rotate(-.1deg); }
    75%  { transform: translate(-3px,-2px) rotate(.08deg); }
    100% { transform: translate(0,0) rotate(0deg); }
  }
  @keyframes bg-in    { from { transform:scale(1.0); } to { transform:scale(1.07); } }
  @keyframes bg-out   { from { transform:scale(1.07); } to { transform:scale(1.0); } }
  @keyframes bg-left  { from { transform:scale(1.06) translateX(1.4%); } to { transform:scale(1.06) translateX(-1.4%); } }
  @keyframes bg-right { from { transform:scale(1.06) translateX(-1.4%); } to { transform:scale(1.06) translateX(1.4%); } }
  @keyframes bg-none  { from { transform:scale(1.02); } to { transform:scale(1.02); } }

  @keyframes enter-pop {
    0%   { opacity:0; transform: scale(.72); }
    70%  { opacity:1; transform: scale(1.04); }
    100% { opacity:1; transform: scale(1); }
  }
  @keyframes enter-drop {
    0%   { opacity:0; transform: translateY(-62%) rotate(-7deg) scale(1.07); }
    70%  { opacity:1; transform: translateY(2%) rotate(1.4deg) scale(1); }
    100% { opacity:1; transform: translateY(0) rotate(0deg) scale(1); }
  }
  @keyframes enter-sl {
    0%   { opacity:0; transform: translateX(-120%) rotate(-6deg); }
    100% { opacity:1; transform: translateX(0) rotate(0deg); }
  }
  @keyframes enter-sr {
    0%   { opacity:0; transform: translateX(120%) rotate(6deg); }
    100% { opacity:1; transform: translateX(0) rotate(0deg); }
  }
  @keyframes card-idle {
    from { transform: rotateX(var(--tilt)) translateY(0) rotate(0deg) scale(1); }
    to   { transform: rotateX(var(--tilt)) translateY(-1.1%) rotate(.6deg) scale(1.012); }
  }
  @keyframes cap-in {
    0%   { opacity:0; transform: translateY(26px) scale(.9); }
    65%  { opacity:1; transform: translateY(0) scale(1.03); }
    100% { opacity:1; transform: translateY(0) scale(1); }
  }
</style></head>
<body><div class="stage" style="--dur:${shot.dur}s">
  <div class="bg"></div>
  ${cards}
  <div class="vignette"></div>
  <div class="grain"></div>
  ${captionHtml(shot.caption, W, st)}
</div></body></html>`;
}

async function renderReel(cfg: ReelConfig, reel: Reel) {
  const W = cfg.width ?? 1080, H = cfg.height ?? 1920, fps = cfg.fps ?? 30;
  const total = reel.shots.reduce((s, x) => s + x.dur, 0);
  console.log(`\n🎬 ${reel.slug} — ${reel.shots.length} záběrů, ${total.toFixed(1)} s`);

  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), `reel-${reel.slug}-`));
  const htmlDir = path.join(cfg.outDir, '_html');
  fs.mkdirSync(htmlDir, { recursive: true });

  const st = resolveStyle(cfg);
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--font-render-hinting=none', `--window-size=${W},${H}`],
  });

  let frameNo = 0;
  for (const shot of reel.shots) {
    const htmlPath = path.join(htmlDir, `${reel.slug}_${shot.id}.html`);
    fs.writeFileSync(htmlPath, shotHtml(shot, W, H, st));

    // Každý záběr má vlastní stránku. Při dlouhém běhu puppeteer občas odpojí rám
    // („detached Frame"), takže záběr v takovém případě zopakujeme na čisté stránce.
    const shotFrames = probe ? 1 : Math.round(shot.dur * fps);
    const startFrame = frameNo;
    for (let attempt = 1; attempt <= 3; attempt++) {
      frameNo = startFrame;
      const page = await browser.newPage();
      try {
        await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
        await page.goto(`file://${path.resolve(htmlPath)}`, { waitUntil: 'networkidle0', timeout: 60000 });
        await page.evaluate(() => (document as any).fonts.ready);
        await new Promise(r => setTimeout(r, 300));
        await page.evaluate(() => document.getAnimations().forEach(a => a.pause()));

        // Kontrola bezpečné zóny Instagramu: žádný text nesmí skončit pod y=1450.
        const capBox = await page.evaluate(() => {
          const el = document.querySelector('.cap');
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return { top: Math.round(r.top), bottom: Math.round(r.bottom) };
        });
        if (capBox && capBox.bottom > 1450) {
          console.warn(`   ⚠️  ${shot.id}: titulek končí na y=${capBox.bottom} (limit 1450) — zvedni caption.top`);
        }

        for (let i = 0; i < shotFrames; i++) {
          const t = probe ? Math.min(shot.dur * 1000 * 0.75, 1800) : (i / fps) * 1000;
          await page.evaluate(ms => document.getAnimations().forEach(a => { a.currentTime = ms; }), t);
          if (probe) {
            const out = path.join(cfg.outDir, '_probe', `${reel.slug}_${shot.id}.png`);
            fs.mkdirSync(path.dirname(out), { recursive: true });
            await page.screenshot({ path: out, type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
          } else {
            // JPEG q95: po průchodu x264 nerozeznatelné od PNG, ale řádově rychlejší zápis.
            await page.screenshot({
              path: path.join(framesDir, `f_${String(frameNo).padStart(5, '0')}.jpg`),
              type: 'jpeg', quality: 95, clip: { x: 0, y: 0, width: W, height: H },
            });
          }
          frameNo++;
        }
        await page.close();
        break;
      } catch (err: any) {
        await page.close().catch(() => {});
        if (attempt === 3) throw err;
        console.warn(`   ↻ ${shot.id}: ${String(err.message).slice(0, 60)} — opakuji (${attempt}/3)`);
      }
    }
    process.stdout.write(`   ✓ ${shot.id} (${shotFrames} sn.)\n`);
  }
  await browser.close();

  if (probe) { fs.rmSync(framesDir, { recursive: true, force: true }); return; }

  const outFile = path.join(cfg.outDir, `reel_${reel.slug}_1080x1920.mp4`);
  execFileSync(ffmpegBin, [
    '-y', '-framerate', String(fps),
    '-i', path.join(framesDir, 'f_%05d.jpg'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', crf,
    '-r', String(fps), '-movflags', '+faststart', outFile,
  ], { stdio: ['ignore', 'ignore', 'inherit'] });
  fs.rmSync(framesDir, { recursive: true, force: true });

  const mb = (fs.statSync(outFile).size / 1024 / 1024).toFixed(1);
  console.log(`   ✅ ${outFile} (${mb} MB, ${total.toFixed(1)} s)`);
}

async function main() {
  const cfgPath = path.resolve('configs', `${configName}.ts`);
  if (!fs.existsSync(cfgPath)) { console.error(`Config nenalezen: ${cfgPath}`); process.exit(1); }
  const cfg = (await import(cfgPath)).default as ReelConfig;
  fs.mkdirSync(cfg.outDir, { recursive: true });

  console.log(`📼 ${cfg.name}`);
  if (cfg.scenes.length) { console.log('🖼  AI pozadí:'); await generateScenes(cfg); }
  if (scenesOnly) return;

  const reels = onlyArg ? cfg.reels.filter(r => onlyArg.split(',').includes(r.slug)) : cfg.reels;
  for (const reel of reels) await renderReel(cfg, reel);
  console.log('\n🏁 Hotovo.');
}

main().catch(e => { console.error('Chyba:', e); process.exit(1); });

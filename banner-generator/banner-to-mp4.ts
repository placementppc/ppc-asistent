/**
 * Převede animovaný HTML banner na MP4 video.
 *
 * Použití:
 *   npx tsx banner-to-mp4.ts <tvuj-klient>/<tvuj-soubor>.html
 *   (např. banners-muj-eshop/koncept_5_animated_1080x1350.html — ručně psané HTML, v appce žádné není)
 *
 * Parametry (volitelné):
 *   --duration=6    Délka videa v sekundách (default: 6)
 *   --fps=30        Snímků za sekundu (default: 30)
 */

import puppeteer from 'puppeteer';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const args = process.argv.slice(2);
const htmlFile = args.find(a => !a.startsWith('--'));

if (!htmlFile) {
  console.error('Použití: npx tsx banner-to-mp4.ts <cesta-k-html> [--duration=6] [--fps=30]');
  process.exit(1);
}

const duration = parseInt(args.find(a => a.startsWith('--duration='))?.split('=')[1] || '6');
const fps = parseInt(args.find(a => a.startsWith('--fps='))?.split('=')[1] || '30');

const htmlPath = path.resolve(htmlFile);
if (!fs.existsSync(htmlPath)) {
  console.error(`Soubor nenalezen: ${htmlPath}`);
  process.exit(1);
}

// Zjistíme rozměry z HTML
const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
const widthMatch = htmlContent.match(/width:\s*(\d+)px/);
const heightMatch = htmlContent.match(/height:\s*(\d+)px/);
const width = widthMatch ? parseInt(widthMatch[1]) : 1080;
const height = heightMatch ? parseInt(heightMatch[1]) : 1350;

const totalFrames = duration * fps;
const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), 'banner-frames-'));
const outputFile = htmlPath.replace('.html', '.mp4');

async function main() {
  console.log(`📐 Rozměry: ${width}x${height}`);
  console.log(`🎬 ${duration}s @ ${fps}fps = ${totalFrames} snímků`);
  console.log(`📁 Frames: ${framesDir}`);

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--font-render-hinting=none',
      `--window-size=${width},${height}`,
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });

  // Načteme stránku a počkáme na fonty + obrázky
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 2000));

  // Ověříme skutečný rozměr body
  const bodySize = await page.evaluate(() => {
    const body = document.body;
    return { w: body.scrollWidth, h: body.scrollHeight, cw: body.clientWidth, ch: body.clientHeight };
  });
  console.log(`📏 Body: ${bodySize.w}x${bodySize.h} (client: ${bodySize.cw}x${bodySize.ch})`);

  // Pauzujeme animace
  await page.evaluate(() => {
    document.getAnimations().forEach(a => a.pause());
  });

  console.log('📸 Nahrávám snímky...');

  for (let i = 0; i < totalFrames; i++) {
    const time = (i / fps) * 1000;

    await page.evaluate((t) => {
      document.getAnimations().forEach(a => {
        a.currentTime = t;
      });
    }, time);

    await new Promise(r => setTimeout(r, 10));

    const frameNum = String(i).padStart(5, '0');
    await page.screenshot({
      path: path.join(framesDir, `frame_${frameNum}.png`),
      type: 'png',
      clip: { x: 0, y: 0, width, height },
    });

    if (i % 30 === 0) {
      process.stdout.write(`  ${Math.round((i / totalFrames) * 100)}%\r`);
    }
  }

  console.log('  100%');
  await browser.close();

  // Složíme MP4 přes ffmpeg
  console.log('🎥 Skládám MP4...');
  const ffmpegBin = (() => {
    try {
      return execSync('which ffmpeg', { encoding: 'utf-8' }).trim();
    } catch {
      return 'ffmpeg';
    }
  })();

  const ffmpegCmd = [
    ffmpegBin, '-y',
    '-framerate', String(fps),
    '-i', path.join(framesDir, 'frame_%05d.png'),
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-preset', 'slow',
    '-crf', '18',
    // Meta Ads požaduje H.264, yuv420p, max 4GB
    '-movflags', '+faststart',
    `"${outputFile}"`,
  ].join(' ');

  execSync(ffmpegCmd, { stdio: 'inherit' });

  // Úklid
  fs.rmSync(framesDir, { recursive: true });

  const size = (fs.statSync(outputFile).size / 1024 / 1024).toFixed(1);
  console.log(`\n✅ Hotovo: ${outputFile} (${size} MB)`);
}

main().catch(err => {
  console.error('Chyba:', err);
  process.exit(1);
});

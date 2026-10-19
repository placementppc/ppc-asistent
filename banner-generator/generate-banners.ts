/**
 * Batch generátor bannerů přes Gemini API.
 *
 * Volá gemini-3.1-flash-image-preview pro každou kombinaci koncept × formát
 * definovanou ve `configs/{název}.ts`. Vygenerované PNG ukládá do cílové složky.
 *
 * Použití:
 *   npx tsx generate-banners.ts ukazka --format=1080x1080
 *
 * Parametry:
 *   [0] název config souboru bez přípony (např. "ukazka" → configs/ukazka.ts)
 *   --only=K1,K3   Vygenerovat jen vybrané koncepty
 *   --format=1080x1080  Vygenerovat jen jeden formát
 *   --retry=2      Počet retry při selhání (default 2)
 */

import * as fs from 'fs';
import * as path from 'path';
import sharp from 'sharp';
import { FORMATS, type Format, type Concept, type Config } from './banner-formats';
import { applyOverlays } from './lib/compose-overlays';

export { FORMATS, type Format, type Concept, type Config };

const args = process.argv.slice(2);
const configName = args.find(a => !a.startsWith('--'));
if (!configName) {
  console.error('Použití: npx tsx generate-banners.ts <config-název> [--only=K1,K3] [--format=1080x1080]');
  process.exit(1);
}

const onlyArg = args.find(a => a.startsWith('--only='))?.split('=')[1];
const formatArg = args.find(a => a.startsWith('--format='))?.split('=')[1];
const maxRetry = parseInt(args.find(a => a.startsWith('--retry='))?.split('=')[1] || '2');

// --relayout: Gemini se vůbec nevolá. Vezme se surový podklad z `_raw/` a jen se
// znovu složí text. Ladění sazby tak nestojí ani korunu za generování obrázku.
const relayout = args.includes('--relayout');

const onlyConcepts = onlyArg ? onlyArg.split(',').map(s => s.trim().toUpperCase()) : null;

// API klíč z .env.local
const envPath = path.resolve('.env.local');
if (!fs.existsSync(envPath)) {
  console.error('Chybí .env.local — zkopíruj .env.example a doplň GEMINI_API_KEY');
  process.exit(1);
}
const envText = fs.readFileSync(envPath, 'utf-8');
const apiKey = envText.match(/GEMINI_API_KEY\s*=\s*(.+)/)?.[1].trim().replace(/^["']|["']$/g, '');
if (!apiKey) {
  console.error('GEMINI_API_KEY nenalezen v .env.local');
  process.exit(1);
}

const MODEL = 'gemini-3.1-flash-image';
// Klíč jde v hlavičce x-goog-api-key, ne v URL — URL se objevuje v chybových hláškách a logu.
const ENDPOINT = `https://generativelanguage.googleapis.com/v1/models/${MODEL}:generateContent`;

async function loadConfig(name: string): Promise<Config> {
  const configPath = path.resolve('configs', `${name}.ts`);
  if (!fs.existsSync(configPath)) {
    console.error(`Config nenalezen: ${configPath}`);
    process.exit(1);
  }
  // @ts-ignore dynamický import
  const mod = await import(configPath);
  return mod.default as Config;
}

function mimeFor(file: string): string {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.webp') return 'image/webp';
  if (ext === '.png') return 'image/png';
  return 'image/jpeg';
}

/** Znovu složí text nad uloženým surovým podkladem. Nevolá žádné API. */
async function relayoutOne(concept: Concept, format: Format, outDir: string): Promise<boolean> {
  const fileName = `gemini_${concept.slug}_banner_${format.fileSuffix}.png`;
  const rawPath = path.join(outDir, '_raw', fileName);
  if (!fs.existsSync(rawPath)) {
    console.warn(`   ⚠️  ${concept.id} ${format.fileSuffix}: chybí podklad v _raw/ — nejdřív vygeneruj bez --relayout`);
    return false;
  }
  const isStories = format.width === 1080 && format.height === 1920;
  const out = await applyOverlays(fs.readFileSync(rawPath), {
    overlays: concept.overlays,
    logo: concept.logo,
    isStories,
  });
  const outPath = path.join(outDir, fileName);
  fs.writeFileSync(outPath, out);
  console.log(`   ✅ ${fileName} (přesazeno, bez generování)`);
  return true;
}

async function generateOne(concept: Concept, format: Format, outDir: string): Promise<boolean> {
  const fileName = `gemini_${concept.slug}_banner_${format.fileSuffix}.png`;
  const outPath = path.join(outDir, fileName);

  const prompt = concept.buildPrompt(format);
  const multiRefs = concept.getReferences?.(format);
  const singleRef = concept.getReference?.(format) ?? null;
  const refPaths = multiRefs && multiRefs.length > 0
    ? multiRefs
    : (singleRef ? [singleRef] : []);

  const parts: any[] = [];
  for (const refPath of refPaths) {
    if (refPath && fs.existsSync(refPath)) {
      const data = fs.readFileSync(refPath).toString('base64');
      parts.push({ inlineData: { mimeType: mimeFor(refPath), data } });
    }
  }
  parts.push({ text: prompt });

  const body = {
    contents: [{ parts }],
  };

  let lastErr: string = '';
  for (let attempt = 0; attempt <= maxRetry; attempt++) {
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const txt = await res.text();
        lastErr = `HTTP ${res.status}: ${txt.slice(0, 400)}`;
        console.warn(`   ⚠️  ${concept.id} ${format.fileSuffix} pokus ${attempt + 1}: ${lastErr}`);
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
        continue;
      }
      const json = await res.json();
      const partsOut = json?.candidates?.[0]?.content?.parts ?? [];
      const imgPart = partsOut.find((p: any) => p.inlineData?.data);
      if (!imgPart) {
        const finishReason = json?.candidates?.[0]?.finishReason;
        const textOut = partsOut.find((p: any) => p.text)?.text?.slice(0, 200);
        lastErr = `žádné image části (finish=${finishReason}, text="${textOut}")`;
        console.warn(`   ⚠️  ${concept.id} ${format.fileSuffix} pokus ${attempt + 1}: ${lastErr}`);
        await new Promise(r => setTimeout(r, 1500));
        continue;
      }
      const rawImage = Buffer.from(imgPart.inlineData.data, 'base64');
      // fit: 'cover' škáluje BEZ deformace (přebytek ořízne) — 'fill' by obraz roztáhl,
      // když Gemini vrátí jiný poměr stran. Obsah stejně skládáme kódem v safe zoně.
      let finalPng = await sharp(rawImage)
        .resize(format.width, format.height, { fit: 'cover', position: 'centre' })
        .png()
        .toBuffer();
      // Surový podklad (bez textu) si schováme. Ladění sazby pak nestojí další
      // generování — viz `--relayout`, které Gemini vůbec nevolá.
      const rawDir = path.join(outDir, '_raw');
      fs.mkdirSync(rawDir, { recursive: true });
      fs.writeFileSync(path.join(rawDir, fileName), finalPng);

      // Dvouvrstvý render: text a logo se skládají kódem (ne přes AI), viz lib/compose-overlays.
      const isStories = format.width === 1080 && format.height === 1920;
      finalPng = await applyOverlays(finalPng, {
        overlays: concept.overlays,
        logo: concept.logo,
        isStories,
      });
      fs.writeFileSync(outPath, finalPng);
      const sizeKb = Math.round(fs.statSync(outPath).size / 1024);
      console.log(`   ✅ ${fileName} (${sizeKb} KB)`);
      return true;
    } catch (e: any) {
      lastErr = e.message || String(e);
      console.warn(`   ⚠️  ${concept.id} ${format.fileSuffix} pokus ${attempt + 1}: ${lastErr}`);
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }

  console.error(`   ❌ ${fileName} selhal: ${lastErr}`);
  return false;
}

async function main() {
  const config = await loadConfig(configName!);
  const outDir = path.resolve(config.outDir);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const concepts = onlyConcepts
    ? config.concepts.filter(c => onlyConcepts.includes(c.id))
    : config.concepts;

  const formats = formatArg
    ? FORMATS.filter(f => f.fileSuffix === formatArg)
    : FORMATS;

  console.log(`🎨 Banner generator — Gemini`);
  console.log(relayout ? `   Režim: --relayout (jen přesazení textu, bez generování)` : `   Model: ${MODEL}`);
  console.log(`   Výstup: ${outDir}`);
  console.log(`   Koncepty: ${concepts.map(c => c.id).join(', ')}`);
  console.log(`   Formáty: ${formats.map(f => f.fileSuffix).join(', ')}`);
  console.log(`   Celkem k vygenerování: ${concepts.length * formats.length}\n`);

  let ok = 0;
  let failed = 0;
  for (const concept of concepts) {
    console.log(`\n▶  ${concept.id} — ${concept.slug}`);
    for (const format of formats) {
      const success = relayout
        ? await relayoutOne(concept, format, outDir)
        : await generateOne(concept, format, outDir);
      if (success) ok++; else failed++;
    }
  }

  console.log(`\n📊 Hotovo: ${ok} úspěch / ${failed} selhání`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch(e => {
  // Jen zpráva, ne celý objekt chyby (ten může nést URL požadavku a hlavičky).
  console.error(`Chyba: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});

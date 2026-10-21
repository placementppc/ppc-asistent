/**
 * Batch generátor bannerů přes OpenAI gpt-image-2 API.
 *
 * Sourozenec generate-banners.ts (Gemini). Sdílí stejné configs/<jméno>.ts —
 * tj. stejné koncepty, prompty a reference fotky. Liší se jen volaným API.
 *
 * Použití:
 *   npx tsx generate-banners-openai.ts ukazka
 *   npx tsx generate-banners-openai.ts ukazka --only=K1,K3
 *   npx tsx generate-banners-openai.ts ukazka --format=1080x1080
 *
 * Výstup jde do <config.outDir>/ s prefixem openai_, takže nepřepíše Gemini výstup (gemini_).
 *
 * Pozn. k rozměrům: gpt-image-2 vyžaduje rozměry dělitelné 16. Generujeme
 * v nejbližším vyšším násobku 16 (1088×1088, 1088×1920, 1088×1360) a sharp
 * downsamplujeme na finální 1080×1080 / 1080×1920 / 1080×1350.
 */

import * as fs from 'fs';
import * as path from 'path';
import sharp from 'sharp';
import { FORMATS, type Config, type Concept, type Format } from './banner-formats';
import { applyOverlays } from './lib/compose-overlays';

const args = process.argv.slice(2);
const configName = args.find(a => !a.startsWith('--'));
if (!configName) {
  console.error('Použití: npx tsx generate-banners-openai.ts <config-název> [--only=K1,K3] [--format=1080x1080]');
  process.exit(1);
}

const onlyArg = args.find(a => a.startsWith('--only='))?.split('=')[1];
const formatArg = args.find(a => a.startsWith('--format='))?.split('=')[1];
const maxRetry = parseInt(args.find(a => a.startsWith('--retry='))?.split('=')[1] || '2');
const qualityArg = args.find(a => a.startsWith('--quality='))?.split('=')[1] as
  | 'low' | 'medium' | 'high' | 'auto' | undefined;
const QUALITY = qualityArg || 'high';

const onlyConcepts = onlyArg ? onlyArg.split(',').map(s => s.trim().toUpperCase()) : null;

const envPath = path.resolve('.env.local');
if (!fs.existsSync(envPath)) {
  console.error('Chybí .env.local — zkopíruj .env.example a doplň OPENAI_API_KEY');
  process.exit(1);
}
const envText = fs.readFileSync(envPath, 'utf-8');
const apiKey = envText.match(/OPENAI_API_KEY\s*=\s*(.+)/)?.[1].trim().replace(/^["']|["']$/g, '');
if (!apiKey) {
  console.error('OPENAI_API_KEY nenalezen v .env.local — přidej řádek OPENAI_API_KEY="sk-..."');
  process.exit(1);
}

const MODEL = 'gpt-image-2';
const GENERATIONS_ENDPOINT = 'https://api.openai.com/v1/images/generations';
const EDITS_ENDPOINT = 'https://api.openai.com/v1/images/edits';

/**
 * Mapping cílový formát (1080×) → generační rozměr (násobek 16).
 * gpt-image-2 vyžaduje width i height dělitelné 16. 1080 není (1080/16=67.5),
 * tak generujeme v 1088 a downscalujeme na 1080.
 */
function generationSize(format: Format): { genWidth: number; genHeight: number; sizeStr: string } {
  const round16 = (n: number) => Math.round(n / 16) * 16;
  const genWidth = round16(format.width);
  const genHeight = round16(format.height);
  return { genWidth, genHeight, sizeStr: `${genWidth}x${genHeight}` };
}

function mimeFor(file: string): string {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.webp') return 'image/webp';
  if (ext === '.png') return 'image/png';
  return 'image/jpeg';
}

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

async function callGenerations(prompt: string, sizeStr: string): Promise<Buffer> {
  const body = {
    model: MODEL,
    prompt,
    n: 1,
    size: sizeStr,
    quality: QUALITY,
    output_format: 'png',
  };
  const res = await fetch(GENERATIONS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt.slice(0, 600)}`);
  }
  const json: any = await res.json();
  const b64 = json?.data?.[0]?.b64_json;
  if (!b64) throw new Error(`Žádná b64_json v odpovědi: ${JSON.stringify(json).slice(0, 300)}`);
  return Buffer.from(b64, 'base64');
}

async function callEdits(prompt: string, sizeStr: string, refPaths: string[]): Promise<Buffer> {
  // OpenAI image edits: multipart/form-data, image[] může být i víc souborů
  const form = new FormData();
  form.append('model', MODEL);
  form.append('prompt', prompt);
  form.append('n', '1');
  form.append('size', sizeStr);
  form.append('quality', QUALITY);
  form.append('output_format', 'png');

  for (const refPath of refPaths) {
    if (!fs.existsSync(refPath)) continue;
    const buf = fs.readFileSync(refPath);
    const blob = new Blob([buf], { type: mimeFor(refPath) });
    // Pokud je víc fotek, použijeme image[] (array forma); pro jednu jen image
    const field = refPaths.length > 1 ? 'image[]' : 'image';
    form.append(field, blob, path.basename(refPath));
  }

  const res = await fetch(EDITS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      // Content-Type nastavuje fetch sám (s boundary)
    },
    body: form,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt.slice(0, 600)}`);
  }
  const json: any = await res.json();
  const b64 = json?.data?.[0]?.b64_json;
  if (!b64) throw new Error(`Žádná b64_json v odpovědi: ${JSON.stringify(json).slice(0, 300)}`);
  return Buffer.from(b64, 'base64');
}

async function generateOne(concept: Concept, format: Format, outDir: string): Promise<boolean> {
  const fileName = `openai_${concept.slug}_banner_${format.fileSuffix}.png`;
  const outPath = path.join(outDir, fileName);

  const prompt = concept.buildPrompt(format);
  const multiRefs = concept.getReferences?.(format);
  const singleRef = concept.getReference?.(format) ?? null;
  const refPaths = (multiRefs && multiRefs.length > 0
    ? multiRefs
    : (singleRef ? [singleRef] : [])
  ).filter(p => p && fs.existsSync(p));

  const { genWidth, genHeight, sizeStr } = generationSize(format);

  let lastErr = '';
  for (let attempt = 0; attempt <= maxRetry; attempt++) {
    try {
      const rawPng = refPaths.length > 0
        ? await callEdits(prompt, sizeStr, refPaths)
        : await callGenerations(prompt, sizeStr);

      // Downscale 1088× na 1080× — fit: 'cover' škáluje bez deformace (shodné s Gemini runnerem)
      const needsResize = genWidth !== format.width || genHeight !== format.height;
      let finalPng = needsResize
        ? await sharp(rawPng)
            .resize(format.width, format.height, { fit: 'cover', position: 'centre' })
            .png()
            .toBuffer()
        : rawPng;

      // Dvouvrstvý render: text a logo se skládají kódem (ne přes AI), viz lib/compose-overlays.
      const isStories = format.width === 1080 && format.height === 1920;
      finalPng = await applyOverlays(finalPng, {
        overlays: concept.overlays,
        logo: concept.logo,
        isStories,
      });

      fs.writeFileSync(outPath, finalPng);
      const sizeKb = Math.round(fs.statSync(outPath).size / 1024);
      const refNote = refPaths.length > 0 ? ` [edit, ${refPaths.length} ref]` : ' [text-only]';
      console.log(`   ✅ ${fileName} (${sizeKb} KB)${refNote}`);
      return true;
    } catch (e: any) {
      lastErr = e.message || String(e);
      console.warn(`   ⚠️  ${concept.id} ${format.fileSuffix} pokus ${attempt + 1}: ${lastErr.slice(0, 200)}`);
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }

  console.error(`   ❌ ${fileName} selhal: ${lastErr}`);
  return false;
}

async function main() {
  const config = await loadConfig(configName!);
  // Stejná složka jako Gemini — soubory se liší prefixem `openai_` vs `gemini_`
  const outDir = path.resolve(config.outDir);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const concepts = onlyConcepts
    ? config.concepts.filter(c => onlyConcepts.includes(c.id))
    : config.concepts;

  const formats = formatArg
    ? FORMATS.filter(f => f.fileSuffix === formatArg)
    : FORMATS;

  console.log(`🎨 Banner generator — OpenAI`);
  console.log(`   Model: ${MODEL}`);
  console.log(`   Quality: ${QUALITY}`);
  console.log(`   Výstup: ${outDir}`);
  console.log(`   Koncepty: ${concepts.map(c => c.id).join(', ')}`);
  console.log(`   Formáty: ${formats.map(f => f.fileSuffix).join(', ')}`);
  console.log(`   Celkem k vygenerování: ${concepts.length * formats.length}\n`);

  let ok = 0;
  let failed = 0;
  for (const concept of concepts) {
    console.log(`\n▶  ${concept.id} — ${concept.slug}`);
    if (concept.podklad) {
      // Sdílený obrázek (`podklad`) umí jen runner Gemini, který ukládá `_raw/`.
      console.warn(`   ⚠️  ${concept.id}: má „podklad“, to umí jen generate:gemini — přeskočeno`);
      continue;
    }
    for (const format of formats) {
      const success = await generateOne(concept, format, outDir);
      if (success) ok++; else failed++;
    }
  }

  console.log(`\n📊 Hotovo: ${ok} úspěch / ${failed} selhání`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch(e => {
  console.error(e);
  process.exit(1);
});

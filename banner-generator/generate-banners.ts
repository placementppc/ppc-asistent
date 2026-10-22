/**
 * Batch generátor bannerů přes Gemini API.
 *
 * Volá Gemini (Nano Banana 2.1, pojistka v lib/modely.ts) pro každou kombinaci koncept × formát
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
import { FORMATS, overlaysFor, type Format, type Concept, type Config } from './banner-formats';
import { applyOverlays, renderLayers } from './lib/compose-overlays';
import { renderGrafik } from './lib/grafik';
import { GEMINI_MODELY, modelyZArgumentu, neznamyModel } from './lib/modely';

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
// --layers: vedle banneru uloží i vrstvy pro video do `_layers/` (podklad, nadpis, zbytek textu).
// animate-banner --layers je pak použije místo odmaskování textu přes Gemini → čisté hrany.
const layers = args.includes('--layers');

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

// Nejnovější model s pojistkou (lib/modely.ts); vynutit jiný: --model=…
const MODELY = modelyZArgumentu(args, GEMINI_MODELY);
let modelIdx = 0;
const model = () => MODELY[modelIdx];
// Klíč jde v hlavičce x-goog-api-key, ne v URL — URL se objevuje v chybových hláškách a logu.
// v1beta: Nano Banana 2.1 je k dispozici jen tady (v1 vrací 404), starší modely jedou taky.
const endpoint = () => `https://generativelanguage.googleapis.com/v1beta/models/${model()}:generateContent`;

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

/**
 * Chybí podklad v tomhle formátu (typicky Stories 1080×1920), ale stejný obrázek existuje v jiném
 * formátu → složí se z něj ořezem (cover: zvětšit na výšku, oříznout boky podle `fokusX`).
 * Žádné zrcadlení ani dokreslování okrajů (dělalo viditelné švy). AI se nevolá.
 */
async function deriveRaw(rawPath: string, concept: Concept): Promise<void> {
  const m = path.basename(rawPath).match(/^(.*_banner_)(\d+)x(\d+)\.png$/);
  if (!m) return;
  const [, prefix, w, h] = m;
  const src = ['1080x1350', '1080x1080', '1200x1200', '1080x1920']
    .map(s => path.join(path.dirname(rawPath), `${prefix}${s}.png`))
    .find(p => p !== rawPath && fs.existsSync(p));
  if (!src) return;
  const W = +w, H = +h;
  const meta = await sharp(src).metadata();
  const scale = Math.max(W / meta.width!, H / meta.height!);
  const sw = Math.round(meta.width! * scale), sh = Math.round(meta.height! * scale);
  const left = Math.round((sw - W) * (concept.fokusX ?? 0.5));
  const top = Math.round((sh - H) / 2);
  await sharp(src).resize(sw, sh).extract({ left, top, width: W, height: H }).png().toFile(rawPath);
  console.log(`   🧩 ${concept.id}: podklad ${W}×${H} složen ořezem ze stejného obrázku (${path.basename(src)})`);
}

/** Vrstvy pro video: `_layers/<banner>_plate.png` (bez textu), `_head.png` (nadpis), `_rest.png` (zbytek). */
async function writeLayers(concept: Concept, format: Format, outDir: string, fileName: string, raw: Buffer): Promise<void> {
  const dir = path.join(outDir, '_layers');
  fs.mkdirSync(dir, { recursive: true });
  const base = path.basename(fileName, '.png');
  const isStories = format.width === 1080 && format.height === 1920;
  const { head, rest } = await renderLayers(format.width, format.height, { overlays: overlaysFor(concept, format), logo: concept.logo, isStories });
  fs.writeFileSync(path.join(dir, `${base}_plate.png`), raw);
  fs.writeFileSync(path.join(dir, `${base}_head.png`), head);
  fs.writeFileSync(path.join(dir, `${base}_rest.png`), rest);
  console.log(`   🎞️  vrstvy pro video: _layers/${base}_{plate,head,rest}.png`);
}

/** Banner „od grafika“: podklad složí kód (lib/grafik.ts), uloží do `_raw/`, pak se vysází text. Bez AI. */
async function grafikOne(concept: Concept, format: Format, outDir: string): Promise<boolean> {
  const rawDir = path.join(outDir, '_raw');
  fs.mkdirSync(rawDir, { recursive: true });
  const spec = typeof concept.grafik === 'function' ? concept.grafik(format) : concept.grafik!;
  const raw = await renderGrafik(spec, format.width, format.height);
  fs.writeFileSync(path.join(rawDir, `gemini_${concept.slug}_banner_${format.fileSuffix}.png`), raw);
  return relayoutOne(concept, format, outDir);
}

/** Znovu složí text nad uloženým surovým podkladem. Nevolá žádné API. */
async function relayoutOne(concept: Concept, format: Format, outDir: string): Promise<boolean> {
  const fileName = `gemini_${concept.slug}_banner_${format.fileSuffix}.png`;
  // `podklad` = obrázek jiného konceptu (test claimů, Black Friday verze vítěze)
  const rawName = `gemini_${concept.podklad ?? concept.slug}_banner_${format.fileSuffix}.png`;
  const rawPath = path.join(outDir, '_raw', rawName);
  if (!fs.existsSync(rawPath)) await deriveRaw(rawPath, concept);
  if (!fs.existsSync(rawPath)) {
    console.warn(concept.podklad
      ? `   ⚠️  ${concept.id} ${format.fileSuffix}: chybí obrázek konceptu „${concept.podklad}“ — nejdřív vygeneruj ten koncept (stejný formát)`
      : `   ⚠️  ${concept.id} ${format.fileSuffix}: chybí podklad v _raw/ — nejdřív vygeneruj bez --relayout`);
    return false;
  }
  const isStories = format.width === 1080 && format.height === 1920;
  const out = await applyOverlays(fs.readFileSync(rawPath), {
    overlays: overlaysFor(concept, format),
    logo: concept.logo,
    isStories,
  });
  const outPath = path.join(outDir, fileName);
  fs.writeFileSync(outPath, out);
  if (layers) await writeLayers(concept, format, outDir, fileName, fs.readFileSync(rawPath));
  console.log(`   ✅ ${fileName} (${concept.podklad ? `obrázek z ${concept.podklad}` : 'přesazeno'}, bez generování)`);
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

  const body: any = {
    contents: [{ parts }],
  };
  // Stories/Reels: řekneme si rovnou o 9:16, jinak model vrátí skoro čtverec a ořez cover uřízne boky scény.
  if (format.height / format.width > 1.5) body.generationConfig = { imageConfig: { aspectRatio: '9:16' } };

  let lastErr: string = '';
  for (let attempt = 0; attempt <= maxRetry; attempt++) {
    try {
      const res = await fetch(endpoint(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const txt = await res.text();
        if (neznamyModel(res.status, txt) && modelIdx < MODELY.length - 1) {
          console.warn(`   ⚠️  Model ${model()} API nezná, přepínám na ${MODELY[modelIdx + 1]}.`);
          modelIdx++;
          attempt--;
          continue;
        }
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
      const rawPng = finalPng;
      finalPng = await applyOverlays(finalPng, {
        overlays: overlaysFor(concept, format),
        logo: concept.logo,
        isStories,
      });
      fs.writeFileSync(outPath, finalPng);
      if (layers) await writeLayers(concept, format, outDir, fileName, rawPng);
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
  console.log(relayout ? `   Režim: --relayout (jen přesazení textu, bez generování)` : `   Model: ${model()}`);
  console.log(`   Výstup: ${outDir}`);
  console.log(`   Koncepty: ${concepts.map(c => c.id).join(', ')}`);
  console.log(`   Formáty: ${formats.map(f => f.fileSuffix).join(', ')}`);
  console.log(`   Celkem k vygenerování: ${concepts.length * formats.length}\n`);

  let ok = 0;
  let failed = 0;
  for (const concept of concepts) {
    console.log(`\n▶  ${concept.id} — ${concept.slug}`);
    for (const format of formats) {
      const success = concept.grafik
        ? await grafikOne(concept, format, outDir)
        : relayout || concept.podklad
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

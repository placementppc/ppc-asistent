// Zmenší hotové bannery na rozměry pro Sklik (obsahová síť).
//
// Použití (ze složky banner-generator):
//   node resize-sklik.mjs <složka-s-bannery> [prefix-souboru]
//   node resize-sklik.mjs banners-ukazka            # vezme všechny gemini_*_banner_*.png
//   node resize-sklik.mjs banners-ukazka openai_    # jen výstupy z OpenAI
//
// Výstup: <složka>/sklik/<slug>_<šířka>x<výška>.png (nebo .jpg, když PNG přeroste ~250 KB).
// Rozměry a limit velikosti si před nahráním ověř v aktuální nápovědě Skliku.
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const SRC = process.argv[2];
const PREFIX = process.argv[3] || 'gemini_';
if (!SRC || !fs.existsSync(SRC)) {
  console.error('Použití: node resize-sklik.mjs <složka-s-bannery> [prefix-souboru]');
  process.exit(1);
}
const OUT = path.join(SRC, 'sklik');
fs.mkdirSync(OUT, { recursive: true });

// [zdrojový formát, cílová šířka, cílová výška]
const jobs = [
  ['1080x1080', 300, 300],
  ['1080x1080', 480, 480],
  ['1080x1920', 720, 1280],
];

const files = fs.readdirSync(SRC).filter(f => f.startsWith(PREFIX) && f.endsWith('.png'));
let done = 0;
for (const [suf, w, h] of jobs) {
  for (const f of files.filter(f => f.endsWith(`_banner_${suf}.png`))) {
    const src = path.join(SRC, f);
    const slug = f.replace(`_banner_${suf}.png`, '');
    const out = path.join(OUT, `${slug}_${w}x${h}.png`);
    await sharp(src).resize(w, h, { fit: 'cover' }).png({ compressionLevel: 9, quality: 90 }).toFile(out);
    let kb = Math.round(fs.statSync(out).size / 1024);
    if (kb > 250) {
      const outJ = out.replace(/\.png$/, '.jpg');
      await sharp(src).resize(w, h, { fit: 'cover' }).jpeg({ quality: 88 }).toFile(outJ);
      fs.unlinkSync(out);
      kb = Math.round(fs.statSync(outJ).size / 1024);
      console.log(`  ${outJ}  ${kb} KB (JPEG)`);
    } else {
      console.log(`  ${out}  ${kb} KB`);
    }
    done++;
  }
}
if (!done) console.log(`Žádné soubory ${PREFIX}*_banner_1080x1080.png / 1080x1920.png v ${SRC}`);

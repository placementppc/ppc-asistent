/**
 * Obrazové modely (ověřeno v dokumentaci Googlu a OpenAI 22. 10. 2026).
 *
 * První model v seznamu je nejnovější, další jsou pojistka: když API nový model nezná
 * (404, nebo 400 kvůli modelu), runner přepne na další a generování nespadne. Jiný model
 * jde vynutit parametrem `--model=…` (třeba `--model=gemini-3-pro-image` na prémiovou kvalitu
 * nebo `--model=gpt-image-2.5-flare` na rychlé a levnější generování).
 */

/** Nano Banana 2.1 (GA 6. 10. 2026), pak předchozí generace 3.1 Flash Image. */
export const GEMINI_MODELY = ['gemini-nano-banana-2.1', 'gemini-3.1-flash-image'];

/** GPT Image 2.5 Sunburst (9/2026, nejschopnější i na úpravy s referenční fotkou), pak GPT Image 2. */
export const OPENAI_MODELY = ['gpt-image-2.5-sunburst', 'gpt-image-2'];

/** Seznam modelů pro runner: `--model=…` z příkazové řádky, jinak výchozí seznam s pojistkou. */
export function modelyZArgumentu(args: string[], vychozi: string[]): string[] {
  const vynuceny = args.find(a => a.startsWith('--model='))?.split('=')[1]?.trim();
  return vynuceny ? [vynuceny] : vychozi;
}

/** Odmítlo API model jako neznámý (a má smysl zkusit další v seznamu)? */
export function neznamyModel(status: number, text: string): boolean {
  if (status === 404) return true;
  return status === 400 && /model/i.test(text) && /not found|does not exist|not supported|unsupported|invalid/i.test(text);
}

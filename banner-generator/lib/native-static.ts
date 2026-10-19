/**
 * Nereklamní statiky (native static) — znovupoužitelné prompt building blocky.
 *
 * Metodika a guardraily: viz `NEREKLAMNI-KREATIVY.md` (10 formátů NS1–NS10,
 * zdroj: PPC Brainfood — Markéta Kabátová) a DVANÁCTÉ ZLATÉ PRAVIDLO
 * v `BANNER-INSTRUCTIONS.md`.
 *
 * Použití v configu:
 *
 *   import { nativeStaticStyle, NATIVE_STATIC_RULES } from '../lib/native-static';
 *
 *   const K3: Concept = {
 *     id: 'K3', slug: 'koncept_3',
 *     buildPrompt: (f) => `${baseHeader(f)}
 *   CONCEPT: "Zvládnu to obsluhovat bez návodu?" — bariéra v nákupu, odpověď organicky.
 *   ${nativeStaticStyle('NS3', { palette: 'warm cream #F4ECE0 + dusty teal #4F7E7B' })}
 *   ${NATIVE_STATIC_RULES}`,
 *     overlays: [ ... ], // text skládá kód, ne AI
 *   };
 *
 * Žádné side effects — bezpečně importovatelné odkudkoli.
 */

export type NativeStaticKind =
  | 'NS1' // komunikace na mobilu (hovor / zpráva / toggle)
  | 'NS2' // reminder / připomínka
  | 'NS3' // Q&A sticker (komunikace se sítí)
  | 'NS4' // post-it / papírek
  | 'NS5' // autentická fotka + organický text
  | 'NS6' // text na obyčejném pozadí
  | 'NS6b' // informační karusel (jeden list)
  | 'NS7' // sdělení v reálném kontextu (plakát, billboard)
  | 'NS8' // zamazaný / začerněný obsah (rizikové)
  | 'NS9' // infografika / mem styl
  | 'NS10'; // jazyk cílovky (insider language)

export type NativeStaticOptions = {
  /** Varianta u formátů, které jich mají víc (NS1: 'call' | 'message' | 'toggle'). */
  variant?: 'call' | 'message' | 'toggle';
  /** Paleta pro tenhle koncept — volným textem, včetně hex hodnot. */
  palette?: string;
  /** Co má být na kreativě vidět z produktu (prázdné = bez produktu, viz guardrail 5). */
  product?: string;
  /** Doplňující instrukce ke scéně (rekvizity, prostředí, úhel). */
  scene?: string;
  /** Text sází kód přes `overlays` → AI má nechat čisté místo. Default true. */
  textByCode?: boolean;
};

/** Lidský název formátu — pro logy a komentáře v configu. */
export const NATIVE_STATIC_LABELS: Record<NativeStaticKind, string> = {
  NS1: 'komunikace na mobilu',
  NS2: 'reminder / připomínka',
  NS3: 'Q&A sticker (komunikace se sítí)',
  NS4: 'post-it / papírek',
  NS5: 'autentická fotka + organický text',
  NS6: 'text na obyčejném pozadí',
  NS6b: 'informační karusel (jeden list)',
  NS7: 'sdělení v reálném kontextu',
  NS8: 'zamazaný obsah (rizikové)',
  NS9: 'infografika / mem styl',
  NS10: 'jazyk cílovky (insider language)',
};

/**
 * Technická pravidla pro nereklamní koncepty.
 *
 * POZOR: cíleně změkčuje zákaz „NEVER render any social-media UI", který platí
 * u běžných konceptů — u native static je stylizovaný interface prvek smyslem
 * formátu. Zákaz UI konkrétní platformy (FB/IG/Messenger/WhatsApp) a nefunkčních
 * interaktivních prvků ale platí dál — je to Meta ad policy.
 */
export const NATIVE_STATIC_RULES = `
NATIVE-STATIC RULES (this concept must NOT look like an ad):
- The creative must read as ordinary CONTENT — a screenshot, a note, a snapshot, a printed poster — not as a designed banner.
- NO advertising polish: no glossy gradients, no drop shadows on text, no glow, no starbursts, no golden frames, no "premium" badges, no stock-ad composition.
- Flat, plain, everyday look. Slight imperfection (paper texture, natural light, off-center framing) is desirable.
- A stylized interface element (message bubble, question sticker, reminder card, toggle row) IS allowed and is the point of this format.
- FORBIDDEN — platform impersonation (Meta ad policy): no Facebook / Instagram / Messenger / WhatsApp / TikTok logos, icons, chrome or notification layouts; no fake play button, fake checkbox, fake progress bar, fake "swipe up", no fake unread-message badge. Build a NEUTRAL, unbranded version of the element instead.
- Keep the subject recognizable: a cold viewer must still tell in 1.5 s what this is about and who it is for.
`.trim();

const KIND_BLOCKS: Record<NativeStaticKind, (o: NativeStaticOptions) => string> = {
  NS1: (o) => {
    if (o.variant === 'toggle') {
      return `STYLE: "phone settings" native static. The product sits on a clean plain surface; beside it a vertical list of 3-4 short feature rows, each with a small rounded toggle switch shown in the ON position (accent-colored). Neutral unbranded UI styling — looks like a generic settings panel, not any real app. Clean, calm, product-forward.`;
    }
    if (o.variant === 'call') {
      return `STYLE: "incoming call" native static. Full-bleed simple screen that reads like a phone call arriving — large caller name area, plain background, generic round accept/decline affordances rendered as flat neutral circles (NOT any real OS or app design). The caller name is the message (e.g. the product speaking to the viewer). Minimal, plain, no advertising decoration.`;
    }
    return `STYLE: "text message screenshot" native static. A plain chat thread on a neutral background — one or two message bubbles, generic unbranded styling (rounded bubbles, plain sans-serif, no app header, no avatars from any real platform). It must look like a screenshot someone took of an ordinary conversation.`;
  },
  NS2: () =>
    `STYLE: "reminder" native static. One bold, simple reminder element — a stylized reminder card or a circled date on a plain calendar page. Neutral unbranded styling, flat colors, no device chrome, no OS notification design. The reminder itself is the whole creative; nothing else competes for attention.`,
  NS3: () =>
    `STYLE: "question sticker" native static, the format people know from stories Q&A. Background is an ordinary, almost incidental photo (slightly out of focus is fine). On top: a rounded question box and, below it, the answer written as an ordinary short human sentence — plainly typeset, as if typed by a person. Unbranded sticker shapes, NOT the visual identity of any real platform. The organic, unpolished feel of the answer is the point.`,
  NS4: () =>
    `STYLE: "post-it note" native static. A real-looking sticky note (paper grain, slight curl at one corner, soft natural shadow) either stuck to a plain surface or arranged next to the product. Handwritten-marker feel, large and legible. Everything else in the frame stays plain and quiet.`,
  NS5: () =>
    `STYLE: "authentic snapshot" native static. An ordinary, un-staged photo — phone-camera look, natural light, imperfect framing (a person's casual selfie, a laptop on a desk, the product held in a hand). NOT studio, NOT stock-ad styling, NO retouching. Any text is set plainly, like a caption someone typed, never like a designed headline.`,
  NS6: () =>
    `STYLE: "plain text on plain background" native static — deliberately the most ordinary creative possible. Background is a single flat color or an incidental texture (patterned tile, plain wall, simple repeating motif). No product hero shot, no illustration, no decoration around the text. The typography is plain and unstyled — no shadows, no gradients, no outlines.`,
  NS6b: () =>
    `STYLE: "informational carousel slide" native static. Looks like an organic educational post slide: generous white or muted space, a plain heading area, short informational blocks, calm restrained styling. Substance over decoration — the viewer must feel they are getting useful information, not a sales slide.`,
  NS7: () =>
    `STYLE: "message in the real world" native static. A photograph of a printed message existing in a real place — a flyer taped to a tree or lamp post, a poster in a metro corridor, a sheet in a shop window, a billboard shot from the street. Correct perspective and matching lighting, visible paper texture and small real-world imperfections (tape, slight wrinkle, passers-by blurred). It must read as a real photo, never as a flat mockup.`,
  NS8: () =>
    `STYLE: "obscured content" native static (use with care). The main content is deliberately blurred / blacked out, and the visible copy explains why. Deadpan, confident, restrained styling — the withheld content is the hook. Nothing decorative; the creative must still be instantly understandable despite what is hidden.`,
  NS9: () =>
    `STYLE: "meme-style infographic" native static. A simple, shareable layout carrying one clever idea — a two-panel comparison, a small decision tree, or a labeled diagram. Plain flat styling, clear type hierarchy, generous whitespace, hand-drawn arrows allowed. Humor is shared with the audience ("that's me"), never at their expense. No advertising polish whatsoever.`,
  NS10: () =>
    `STYLE: "insider language" native static. Visual is deliberately minimal — a plain background or one ordinary photo — and the short insider phrase carries the whole creative. Typography is bold, plain and confident. No explanation, no decoration; the people it is for recognize it instantly.`,
};

/**
 * Vrátí STYLE blok pro daný nereklamní formát.
 * Skládej ho do promptu spolu s `NATIVE_STATIC_RULES`.
 */
export function nativeStaticStyle(
  kind: NativeStaticKind,
  opts: NativeStaticOptions = {},
): string {
  const parts = [KIND_BLOCKS[kind](opts)];

  if (opts.palette) parts.push(`PALETTE: ${opts.palette}. Muted and ordinary, not "brand-glossy".`);
  if (opts.scene) parts.push(`SCENE DETAIL: ${opts.scene}`);

  if (opts.product) {
    parts.push(
      `PRODUCT: ${opts.product} — must stay clearly recognizable even in this understated styling.`,
    );
  }

  if (opts.textByCode !== false) {
    parts.push(
      `TEXT: do NOT render any headline, price or logo — the copy is composed in code afterwards. Leave clean, uncluttered space where the text block belongs, with even tone behind it.`,
    );
  }

  return parts.join('\n');
}

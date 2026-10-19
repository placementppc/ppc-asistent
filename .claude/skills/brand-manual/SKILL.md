---
name: brand-manual
description: Brand manuál klienta před bannery — převede dodaný manuál (PDF, odkaz, obrázky, export z Figmy) do jednotného BRAND-MANUAL.md, a když manuál není, sestaví ho z detailně načteného webu klienta (logo, barvy HEX, fonty, tón, claimy, fotostyl, CTA, zakázané věci, legislativa). Výsledek ukáže ke schválení. Použij VŽDY před prvními bannery pro klienta, a když uživatel řekne „brand manuál", „vytáhni brand z webu", „jaké má klient barvy a fonty", „připrav podklady na bannery", „nový klient na bannery". Skill bannery ho spouští sám, když manuál chybí.
---

# Brand manuál (povinný krok před bannery)

Bannery se dělají **až podle schváleného** `banner-generator/banners-<klient>/BRAND-MANUAL.md`.
Tenhle skill ho vyrobí. Šablona: `banner-generator/BRAND-MANUAL.template.md`.

`<klient>` = krátký slug bez diakritiky (`muj-eshop`). Stejný slug jako `clients/<klient>.md`, pokud existuje.

## Krok 0 — co už existuje

1. Existuje `banner-generator/banners-<klient>/BRAND-MANUAL.md` se stavem `SCHVÁLENO`?
   Řekni to uživateli jednou větou (kdo a kdy schválil) a zeptej se, jestli ho použít, nebo aktualizovat. Hotovo.
2. Existuje jen `NÁVRH`? Ukaž ho ke schválení (krok 4).
3. Podívej se do `clients/<klient>.md` (web, obor, zakázané věci, NDA). U klienta pod NDA platí
   `docs/nda-rezim.md` — do manuálu nepiš nic z účtu, jen veřejný brand.

## Krok 1 — zeptej se na manuál klienta

Jedna otázka, všechno najednou:

> Má klient brand manuál nebo grafické podklady? Stačí cokoli z tohohle: PDF manuálu, odkaz na něj,
> logo v PNG/SVG, obrázky, export z Figmy, soubory fontů. Vlož je do složky
> `banner-generator/banners-<klient>/brand/` a napiš „hotovo". Když nic nemá, napiš „nemá" a sestavím ho z webu.

Složku `brand/` založ předem (`mkdir -p`), ať ji uživatel najde.

### 1a — manuál existuje

1. Vypiš, co ve `brand/` leží. Přečti všechno:
   - PDF přes Read (u delších po 20 stranách, parametr `pages`),
   - obrázky a exporty z Figmy přes Read (vidíš je),
   - odkaz: stáhni do `brand/` (`curl -L -o …`). Když stažení nejde (přihlášení, Figma bez exportu),
     řekni to rovnou a požádej o PDF nebo PNG export. Nic si nedomýšlej.
2. Vytáhni do šablony: logo a varianty, barvy s HEX (u CMYK/Pantone bez HEX napiš `NEOVĚŘENO — v manuálu jen CMYK`),
   fonty, tón, claimy, fotostyl, zakázané věci. U každého údaje do sekce **Zdroje** stranu manuálu.
3. Co manuál neřeší (typicky tón, CTA, legislativa), doplň z webu podle kroku 2 a u zdroje napiš „web".
4. Pokračuj krokem 3.

### 1b — manuál není → krok 2

## Krok 2 — detailně načti web klienta

Adresu webu vezmi z `clients/<klient>.md`, jinak se zeptej.

### 2a — skript

```bash
python3 scripts/brand/nacti_web.py https://www.muj-eshop.cz --out banner-generator/banners-<klient>/brand/web.json
```

- Stáhne homepage a vybere 3–5 klíčových stránek (o nás, kontakt, kategorie, produkt), načte jejich CSS.
- Respektuje robots.txt, má timeout, pauzu mezi požadavky a strop 10 stránek.
- Když výběr stránek nesedí, přidej je ručně: `--stranky /o-nas/ /kategorie/kavovary/ /produkt/xyz/`.
- Exit 0 = OK, 1 = načteno částečně nebo web potřebuje prohlížeč (čti pole `upozorneni`), 2 = web nejde načíst.

Z JSON vezmi:

| Pole | Do manuálu |
|---|---|
| `barvy.tlacitka_pozadi` | akcent / barva CTA |
| `barvy.nejcastejsi_barevne`, `css_promenne`, `theme_color_meta` | primární a sekundární barva |
| `barvy.pozadi_stranky`, `text_stranky`, `nejcastejsi_neutralni` | pozadí a text |
| `fonty.*` (font-family, @font-face, Google Fonts) | typografie |
| `logo_kandidati`, `meta.og:image`, `meta.ikony` | logo |
| `texty.nadpisy`, `ukazky_odstavcu` | tón, citace, claimy, USP |
| `texty.cta` | CTA formulace |
| `texty.osloveni_odhad` | tykání / vykání (jen odhad, potvrď citací) |

Četnost barvy v CSS ≠ brandová barva (šedé rámečky bývají nejčastější). Rozhoduje logo a tlačítka.

### 2b — prohlížeč (vždy u webů na JS, jinak pro kontrolu)

Když JSON hlásí v `upozorneni` JavaScript, Next.js, Shoptet nebo málo textu, skript nestačí.
Otevři web ve vestavěném prohlížeči (Browser v aplikaci Claude, případně Claude in Chrome):

1. Screenshot homepage, jedné kategorie a jednoho produktu.
2. Přečti text stránky (oslovení, claimy, CTA).
3. Barvu hlavního tlačítka a pozadí zjisti z vykreslené stránky (`getComputedStyle` přes JavaScript
   nástroj prohlížeče), ne odhadem ze screenshotu.
4. Logo stáhni do `brand/` (URL z `logo_kandidati` nebo z prohlížeče). Inline SVG ulož ze zdrojového kódu.

Když prohlížeč nemáš, řekni uživateli, které údaje zůstaly neověřené, a nech je ve stavu `NEOVĚŘENO`.

### 2c — co vytáhnout (nic nevymýšlej)

- **Logo:** URL / soubor, varianty (barevné, bílé), na jakém pozadí stojí.
- **Barvy:** HEX primární / sekundární / akcent (CTA) / text / pozadí, odhad poměru podle webu.
- **Fonty:** rodina nadpisů a textu. Je-li to Google Font, stáhni .ttf do `brand/fonts/`
  (pro `fontFile` v configu). Placený font nestahuj, poznač ho a navrhni záložní.
- **Tón:** 3–5 doslovných citací typických formulací, tykání / vykání, co je pro značku typické.
- **Claimy a USP:** jen to, co na webu stojí (doprava, záruka, výroba, recenze s počtem). Každé s URL.
- **Fotostyl:** produkt na bílém / lifestyle / ilustrace; světlo, prostředí, lidé.
- **CTA:** jak web vyzývá k akci („Do košíku", „Vyzkoušet"…).
- **Zakázané věci:** co web nikdy neříká (superlativy, slevové výkřiky, srovnání), co je v `clients/<klient>.md`.
- **Legislativa podle oboru** (označ jako obecné pravidlo, ne právní radu):
  doplňky stravy → jen schválená zdravotní tvrzení EU (nařízení ES 1924/2006), žádné léčení;
  kosmetika → žádné léčebné účinky; zdravotnické prostředky, léky, alkohol, finance, hazard → přísnější
  pravidla reklamy a Meta / Google policy; dětské produkty → žádný tlak na děti.
  Když si nejsi jistý, napiš „ověřit u klienta".

## Krok 3 — zapiš BRAND-MANUAL.md

1. Zkopíruj `banner-generator/BRAND-MANUAL.template.md` do `banner-generator/banners-<klient>/BRAND-MANUAL.md`.
2. Vyplň všechny sekce. Co nevíš, nech `NEOVĚŘENO` (ne prázdné, ne odhad).
3. **Zdroje:** u každého údaje URL nebo strana manuálu a datum.
4. **Stav:** `NÁVRH`.
5. Když chybí `banners-<klient>/PROJECT.md` (produkty, cílovka, fotky), založ ho podle
   `banner-generator/banners-ukazka/PROJECT.md`. Brand do PROJECT.md neopisuj, odkaž na BRAND-MANUAL.md.

Vzor vyplněného manuálu: `banner-generator/banners-ukazka/BRAND-MANUAL.md` (smyšlená značka).

## Krok 4 — schválení (bez něj žádné bannery)

Ukaž uživateli krátké shrnutí, ne celý soubor:

- 3–5 barev s HEX a rolí, fonty, logo (cesta k souboru), oslovení, 2 citace tónu, hlavní USP, zakázané věci,
- seznam `NEOVĚŘENO` položek,
- otázka: **„Schvaluješ manuál, nebo co opravit?"**

Po „ano" doplň do sekce Stav: `SCHVÁLENO`, kdo schválil (zeptej se, jestli i klient) a dnešní datum.
Teprve pak předej zpět skillu `bannery`. Opravy zapiš do manuálu a ukaž znovu jen změněné řádky.

## Pravidla

- Nic nevymýšlej: žádné barvy „od oka", žádné claimy, které na webu nejsou, žádné recenze.
- Logo a fonty jsou soubory na disku, ne popis. Do AI promptu se logo nikdy neposílá (skládá ho kód).
- Web klienta jen čteš. Žádné formuláře, žádné přihlašování, žádné stahování mimo logo, fonty a obrázky produktu.
- Manuál je živý dokument: když klient změní brand, aktualizuj ho a znovu nech schválit.

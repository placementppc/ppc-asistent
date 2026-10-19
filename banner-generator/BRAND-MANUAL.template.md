# Brand manuál — <Název značky>

> Šablona. Zkopíruj do `banner-generator/banners-<klient>/BRAND-MANUAL.md` a vyplň.
> Vyplňuje ji skill `brand-manual` (z manuálu klienta, nebo z jeho webu).
> U každého údaje uveď zdroj v sekci **Zdroje**. Co nejde ověřit, označ `NEOVĚŘENO` a nevymýšlej.
> Bannery se dělají až po vyplnění sekce **Stav** (schváleno kým a kdy).

## 1. Značka v kostce

- **Co prodává:** <jedna věta, konkrétně>
- **Komu:** <hlavní zákazník a jeho situace, ne demografie>
- **Proč u nás:** <1–3 skutečné důvody z webu / manuálu>
- **Osobnost značky ve 3 slovech:** <např. věcná · klidná · odborná>
- **Web:** <https://…>

## 2. Logo

| Varianta | Soubor | Použití |
|---|---|---|
| hlavní (barevné) | `brand/logo.png` | světlé pozadí |
| negativ (bílé) | `brand/logo-bile.png` | tmavé pozadí, fotky |
| symbol / favicon | `brand/symbol.png` | malé plochy |

- **Formát pro bannery:** PNG s průhledností (nebo SVG převedené na PNG). Logo do banneru skládá kód (`logo` v configu), **nikdy AI**.
- **Ochranná zóna:** <např. výška písmene X kolem loga; když manuál neříká, napiš „manuál neuvádí, používáme 4 % šířky banneru">
- **Minimální velikost:** <px nebo % šířky banneru>
- **Na tmavém pozadí:** <která varianta>
- **Na světlém pozadí:** <která varianta>
- **Zakázané úpravy:** <deformace, jiné barvy, stín, obrys…>

## 3. Barvy

| Role | HEX | Kde se používá | Poměr v banneru |
|---|---|---|---|
| primární | `#______` | logo, nadpisy | ~60 % |
| sekundární | `#______` | plochy, pozadí | ~30 % |
| akcent (CTA) | `#______` | tlačítko, zvýraznění | ~10 % |
| text | `#______` | běžný text | — |
| pozadí | `#______` | světlé plochy | — |

- **Kontrast CTA:** text tlačítka vůči jeho barvě min. 4,5 : 1 (ověř nástrojem na kontrast).
- **Barvy, které značka nepoužívá:** <…>

## 4. Typografie

- **Nadpisy:** <rodina, řez> · soubor `brand/fonts/<…>.ttf` (pro `fontFile` v configu) · zdroj (Google Fonts / licence klienta)
- **Text:** <rodina, řez>
- **Záložní font:** <když soubor fontu nemáme, např. systémový sans-serif>
- **Pravidla:** <verzálky ano/ne, max. počet řezů, zarovnání>

## 5. Tón a slovník

- **Oslovení:** <vykání / tykání> — doklad: „<citace z webu>"
- **Tón:** <např. věcný, přátelský, bez superlativů>
- **Typické formulace (citace z webu / manuálu):**
  - „<…>"
  - „<…>"

| Ano (takhle mluvíme) | Ne (takhle nemluvíme) |
|---|---|
| <…> | <…> |
| <…> | <…> |

## 6. Claimy a USP

- **Hlavní claim / slogan:** „<…>" (zdroj)
- **USP, které jde doložit:** <doprava, záruka, výroba, počet recenzí…> — každé se zdrojem
- **Čísla, která smíme použít:** <jen ověřená, s datem ověření>
- **Ceny v reklamě:** <ano / ne / jen se souhlasem klienta>

## 7. Fotostyl

- **Produktové fotky:** <na bílém / v prostředí / obojí>
- **Lifestyle:** <ano/ne, jaké prostředí, světlo, lidé s tvářemi / bez>
- **Ilustrace / grafika:** <ano/ne, styl>
- **Čemu se vyhnout:** <stock klišé, studené světlo, …>
- **Kde leží fotky:** `banners-<klient>/` (produkt s průhledným pozadím jako `*_transparent.png`)

## 8. Kompozice bannerů

- **Logo:** <roh, velikost v % šířky>
- **CTA tlačítko:** <barva, tvar (zaoblení), umístění, typický text>
- **Nadpis:** <max. délka, pozice>
- **Co musí být na každém banneru:** <logo, produkt, CTA…>
- **Formáty:** výchozí 1080×1080; Stories 1080×1920 a 1080×1350 jen na vyžádání.

## 9. Zakázané věci a legislativa

- **Slova a sliby, které nepoužíváme:** <…>
- **Obor a jeho pravidla:** <např. doplňky stravy → jen schválená zdravotní tvrzení EU (nařízení 1924/2006); kosmetika → žádné léčebné účinky; finance → povinné údaje; alkohol → omezení cílení>
- **Srovnání s konkurencí:** <zakázané / jen …>
- **Další omezení klienta:** <…>

## 10. Zdroje

| Údaj | Zdroj (URL webu / strana manuálu / soubor) | Ověřeno |
|---|---|---|
| barvy | <…> | <datum> |
| fonty | <…> | <datum> |
| logo | <…> | <datum> |
| tón, citace | <…> | <datum> |
| claimy | <…> | <datum> |

Způsob vzniku: <z brand manuálu klienta (soubor …) / z webu (skript `scripts/brand/nacti_web.py` + vestavěný prohlížeč)>

## 11. Stav

- **Stav:** NÁVRH / SCHVÁLENO
- **Schválil:** <jméno a role (např. já za agenturu, klient)>
- **Datum schválení:** <YYYY-MM-DD>
- **Poznámky ke schválení:** <co uživatel opravil>

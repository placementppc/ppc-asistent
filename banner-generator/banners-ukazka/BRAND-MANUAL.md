# Brand manuál — Kávovar Ranní (UKÁZKA)

> **Smyšlená značka** pro výuku. Firma, web ani recenze neexistují. Ukazuje, jak má vypadat
> vyplněný manuál. Vlastní klient: šablona `../BRAND-MANUAL.template.md`, skill `brand-manual`.

## 1. Značka v kostce

- **Co prodává:** kompaktní pákové a automatické kávovary na doma + kávu do nich
- **Komu:** lidem, kteří chtějí dobrou kávu doma a nemají čas ani chuť se učit baristiku
- **Proč u nás:** návod a nastavení po telefonu zdarma, servis do 5 pracovních dnů, 30 dní na vrácení
- **Osobnost značky ve 3 slovech:** klidná · věcná · přátelská
- **Web:** https://kavovar-ranni.example (smyšlená doména)

## 2. Logo

| Varianta | Soubor | Použití |
|---|---|---|
| hlavní (espresso hnědá) | `brand/logo.png` | světlé a krémové pozadí |
| negativ (krémová) | `brand/logo-negativ.png` | tmavé pozadí, fotky |
| symbol (šálek) | `brand/symbol.png` | malé plochy, avatar |

- **Formát pro bannery:** PNG s průhledností. Do banneru ho skládá kód (`logo` v configu), nikdy AI.
- **Ochranná zóna:** výška symbolu šálku kolem celého loga
- **Minimální velikost:** 18 % šířky banneru
- **Na tmavém pozadí:** negativ · **Na světlém:** hlavní
- **Zakázané úpravy:** jiné barvy, stín, obrys, deformace, logo přes rušnou část fotky

## 3. Barvy

| Role | HEX | Kde se používá | Poměr v banneru |
|---|---|---|---|
| primární — espresso | `#3B2A20` | logo, nadpisy, tmavé plochy | ~30 % |
| sekundární — krém | `#F4ECE0` | pozadí, plochy | ~60 % |
| akcent — pomeranč | `#E8772E` | CTA tlačítko, jedno zvýraznění | ~10 % |
| text | `#2B2B2B` | běžný text | — |
| pozadí | `#FFFFFF` | produktové fotky | — |

- **Kontrast CTA:** bílý text na `#E8772E` — před použitím ověř nástrojem na kontrast (cíl 4,5 : 1;
  když nevyjde, použij tmavý text `#3B2A20`).
- **Barvy, které značka nepoužívá:** neonové, studená modrá, černá jako plocha.

## 4. Typografie

- **Nadpisy:** Inter ExtraBold · Google Fonts (licence OFL) · soubor `brand/fonts/Inter-ExtraBold.ttf`
- **Text:** Inter Regular / Medium
- **Záložní font:** systémový sans-serif (Arial, Helvetica)
- **Pravidla:** nadpisy větou (ne verzálkami), max 2 řezy na banneru, zarovnání vlevo

## 5. Tón a slovník

- **Oslovení:** vykání — doklad: „Zavolejte nám, kávovar s vámi nastavíme." (ukázková citace)
- **Tón:** klidný a věcný, jako soused, který se v kávě vyzná. Žádné výkřiky.
- **Typické formulace:**
  - „Dobrá káva doma, bez vědy."
  - „Nastavíme s vámi po telefonu."

| Ano (takhle mluvíme) | Ne (takhle nemluvíme) |
|---|---|
| „espresso za minutu" | „baristická revoluce" |
| „bez vědy", „jednoduše" | „profesionální výkon" |
| „vyzkoušejte 30 dní" | „KUPTE TEĎ!!!", „poslední kusy" |

## 6. Claimy a USP

- **Hlavní claim:** „Dobrá káva doma, bez vědy."
- **USP, které jde doložit:** nastavení po telefonu zdarma, servis do 5 pracovních dnů, 30 dní na vrácení
  (u skutečného klienta s URL obchodních podmínek)
- **Čísla, která smíme použít:** žádná bez zdroje
- **Ceny v reklamě:** jen se souhlasem klienta, ukázkový config je proto bez částek

## 7. Fotostyl

- **Produktové fotky:** na bílém (pro e-shop) + v kuchyni (pro bannery)
- **Lifestyle:** domácí kuchyně, ranní světlo z okna, ruce a šálek, tváře nevadí, ale nejsou nutné
- **Ilustrace:** ano, plochý styl v barvách značky
- **Čemu se vyhnout:** kavárenský pult s baristou (nejsme kavárna), studené studiové světlo, stock úsměvy
- **Kde leží fotky:** `banners-ukazka/` (`kavovar_transparent.png` = produkt bez pozadí)

## 8. Kompozice bannerů

- **Logo:** vlevo dole, 20 % šířky
- **CTA tlačítko:** pomerančový pruh (`#E8772E`), bílý text, vlevo dole nad logem nebo vedle
- **Nadpis:** nahoře vlevo, max 2 řádky, espresso hnědá na krému
- **Na každém banneru:** produkt (kromě nereklamních NS6), logo, CTA
- **Formáty:** výchozí 1080×1080; Stories a Portrait jen na vyžádání

## 9. Zakázané věci a legislativa

- **Slova a sliby:** „nejlepší", „revoluční", „profesionální kvalita", „zdravější káva", „nastartuje vás na celý den"
- **Obor:** spotřebič — žádná zdravotní tvrzení o kávě ani kofeinu; údaje o příkonu a tlaku jen z technického listu
- **Srovnání s konkurencí:** zakázané (jmenovitě i „lepší než značkové kávovary"); srovnání s kavárnou cestou smí
- **Další omezení:** žádné vymyšlené recenze; Q&A koncept jen s doslovnou recenzí z webu

## 10. Zdroje

| Údaj | Zdroj | Ověřeno |
|---|---|---|
| barvy | smyšlené pro ukázku (u klienta: CSS webu / strana manuálu) | — |
| fonty | smyšlené pro ukázku (u klienta: `fonty.*` z `brand/web.json`) | — |
| logo | smyšlené pro ukázku (soubory nejsou přiložené) | — |
| tón, citace | smyšlené pro ukázku (u klienta: doslovné citace s URL) | — |
| claimy | smyšlené pro ukázku (u klienta: obchodní podmínky, URL) | — |

Způsob vzniku: ukázka napsaná ručně. U klienta: z jeho manuálu, nebo z webu
(`python3 scripts/brand/nacti_web.py <web> --out banner-generator/banners-<klient>/brand/web.json` + vestavěný prohlížeč).

## 11. Stav

- **Stav:** SCHVÁLENO (jen jako ukázka)
- **Schválil:** autor ukázky
- **Datum schválení:** 2026-10-19
- **Poznámky:** u skutečného klienta sem patří jméno a role schvalovatele

# PPC Skills — Tvorba kampaní

Obecné know-how pro tvorbu PPC kampaní (primárně Sklik, principy platí i pro Google Ads).
Bez klientských dat — jen metodika, pravidla a ověřená praxe.

> Zatímco ostatní soubory v `knowledge/` řeší **optimalizaci běžících** kampaní, tenhle balíček
> řeší **tvorbu nových**.

## Obsah

| Soubor | Co obsahuje |
|---|---|
| `01-OBECNE-TVORBA-KAMPANI.md` | Workflow tvorby, typy kampaní, metriky (PNO × marže), povinná pravidla (obrázky, logo, zařízení, remarketing), bezpečnost zápisu přes API |
| `02-SRCH-VYHLEDAVACI-KAMPANE.md` | Vyhledávací kampaně — struktura, klíčová slova a shody, vylučující slova, texty inzerátů (ETA i RSA), sitelinky, bidding |
| `03-OBSAH-DISPLAY-KAMPANE.md` | Obsahové kampaně — remarketing vs. akvizice, struktura sestav (mobil/desktop, umístění), cílení a jeho kombinace, kombinovaná (nativní) reklama, texty a obrázky |
| `04-SKLIK-SPECIFIKA.md` | Sklik / DRAK API specifika — gotchas, limity, formáty, co API umí a neumí, verifikace po vytvoření |
| `05-KOMBINOVANA-REKLAMA-RECEPT.md` | **Exekuční postup** tvorby kombinované (responzivní) reklamy krok za krokem — od podkladů od klienta přes ořez a nahrání obrázků až po verifikaci a aktivaci |

## Jak balíček používat

- Soubory jsou psané jako instrukce pro AI asistenta (Claude apod.) i jako checklist pro člověka.
- Při tvorbě kampaně načíst `01` + soubor podle typu kampaně (`02` nebo `03`); při práci přes Sklik API vždy i `04`.
- Když se reálně **vyrábí kombinovaná reklama**, jet podle `05` — je to postup v pořadí, ve kterém se to dělá.
- Pravidla označená **POVINNÉ** se nikdy nepřeskakují.

## Vazby na zbytek `knowledge/`

| Když řešíš | Čti i |
|---|---|
| Sklik obsahovku pro konkrétního klienta | `../OBSAHOVE-SKLIK.md` — konkrétní weby Seznamu, kombinace cílení, co nedělat |
| Vyhodnocení a A/B testy reklam | `../reklamy-ab-testy.md` — prahy, policy checklist, zápis experimentu |
| Kreativní pokrytí (persona × úhel × formát) | `../coverage-matrix.md` — 6 úhlů sdělení, grid, kde leží prostor |
| Limity API a bezpečnost zápisu | `../api-limity-bezpecnost.md` — **závazné** |
| Sklik obecně (PNO, typy kampaní, API základ) | `../sklik.md` |

## Doplňky 28. 7. 2026

Přidáno k původní verzi. Vše ověřené proti API / nápovědě, ne z paměti:

- **Nový soubor `05`** — exekuční recept na kombinovanou reklamu (chyběl krok „jak se to reálně vyrobí")
- **`images.constraints.list` jako zdroj pravdy pro limity** — vrací i **toleranci poměru stran**,
  kterou nápověda vůbec neuvádí (čtverec ±1 %, landscape ±1,91 %, logo 4:1 ±4 %)
- **`images.create` bere veřejnou URL, ne lokální soubor ani base64** — a tři cesty, jak to obejít
- **Obrázky a loga lze předat přes ID už nahraných** (`imageId`, `imageSquareId`, `imageLogoId`,
  `imageLandscapeLogoId`) — nemusí se nahrávat znovu
- **Pole `colorMain` / `colorAccent`** (HEX bez mřížky) — v balíčku chyběla
- **Podklady od klienta:** vyžádat jeden master 2400×1600, ne hotové formáty + hotový text k odeslání
- **6 úhlů sdělení** jako checklist proti sadám, kde 4 reklamy říkají totéž
- **RSA vs. ETA** — v Google Ads už ETA vytvořit nejde (od 6/2022), soubor `02` to nerozlišoval
- **Zákaz telefonních čísel v textech** — po reálném zamítnutí sitelinku (16. 7. 2026)
- **Korekce:** branding 2000×1400 není mezi 12 bannerovými rozměry z API — je to samostatný `adType`

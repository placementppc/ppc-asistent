# Obsahové (display) kampaně — tvorba

Primárně Sklik obsahová síť, principy platí i pro GDN.

> Konkrétní weby Seznamu, kombinace cílení a „co nedělat" v obsahové síti Skliku jsou v `../OBSAHOVE-SKLIK.md`.

## Dva základní režimy

| | Remarketing | Akvizice |
|---|---|---|
| **Cílení** | Návštěvníci webu (publikum) | Zájmy, zájmy o koupi, umístění |
| **Očekávání** | Lepší CR, CTR, přijatelné CPC | Horší metriky, tvoří poptávku |
| **Texty** | Mohou být stejné jako akvizice — rozlišit CPC a rozpočtem | Obecnější, budují povědomí |

**POVINNÉ pro remarketing:** publikum přiřazené ke VŠEM sestavám, po vytvoření ověřit (nesmí být `null`). Bez publika je to neadresná display kampaň, ne remarketing.

**Před akvizicí se vždy ptát:** Co je cílem? Jaký rozpočet a doba běhu? Jaká cílová skupina (pohlaví, věk)?
- Menší rozpočet / kratší běh → úzké cílení (zájmy o koupi + kvalitní umístění)
- Větší rozpočet / dlouhodobě → volnější cílení, kvalitní weby jako základ

## Formáty reklam

| Formát | Charakteristika |
|---|---|
| **Banner** | Nejdražší CPC, vizuálně nejsilnější; pevné rozměry |
| **Kombinovaná / responzivní (nativní)** | Nejlevnější CPC; systém skládá texty + obrázky do všech slotů včetně nativních in-article pozic |
| **Dynamický remarketing** | Automaticky produkty z feedu, které uživatel viděl |
| **Video** | Drahé, silný branding |

- Benchmark CTR responzivních reklam: **0,3–0,6 %** (některá umístění i výrazně víc) — vždy porovnávat s historií účtu
- Doporučení: ke každé banner sestavě přidat i kombinovanou reklamu — pokrývá nativní pozice, kam bannery nemohou

## Struktura sestav — POVINNÝ princip mobil/desktop

**Vždy rozdělit sestavy na mobilní a desktopové.** Rozdělení výhradně korekcí **-100 %** (viz obecná pravidla):

- Mobilní sestava: desktop -100 % (tablet a ostatní se počítají k mobilu)
- Desktopová sestava: -100 % na mobil, tablet i ostatní

> 🔴 **Když je dělení po KAMPANÍCH (kampaň PC + kampaň Mobil), patří −100 % na úroveň kampaně**
> a na sestavy jen jako pojistka. Sklik: úprava na sestavě má přednost před kampaní, **výjimkou je
> −100 % na kampani, které platí vždy** (napoveda.sklik.cz → Cílení na zařízení). Nastavení jen na
> sestavách uživatel v kampani nevidí a později přidaná sestava by jela všude. (Doplněno 17. 9. 2026.)

> 🔴 **Každý remarketing vylučuje nakupující.** Není-li v účtu funkční publikum (zkontroluj `users`),
> založ ho na děkovací stránku se `useHistoricData: true` ve stejné stavbě — nepřeskakuj to.
> Shoptet: děkovací stránka je `/objednavka/dekujeme/` → podmínka `contains dekujeme`.

### Vzorová struktura (Sklik)

```
Kampaň: [Produkt] — Obsahová
├── Sestava: Prémiové weby — Mobil     (kvalitní portály provozovatele sítě)
├── Sestava: Prémiové weby — Desktop   (stejné weby)
├── Sestava: Mimo prémiové — Desktop   (vyloučit prémiové weby)
└── Sestava: Mimo prémiové — Mobil     (nízké CPC — riziko omylných kliků)
```

**Proč:** prémiové weby sítě mají lepší kvalitu kliknutí; zbytek sítě na mobilu nese riziko omylných kliků (pop-upy, reklamy v obrázcích) → tam jen minimální CPC. Různá CPC pro různá umístění a zařízení = lepší kontrola rozpočtu.

## Cílení — pravidla kombinací (KRITICKÉ)

| Kombinace na jedné sestavě | Logika | Efekt |
|---|---|---|
| Zájmy + zájmy | OR | Rozšíření |
| Zájmy o koupi + zájmy o koupi | OR | Rozšíření |
| **Zájmy + zájmy o koupi** | **AND** | Zúžení — musí splnit obojí |
| **Zájmy (o koupi) + umístění** | **AND** | Zúžení — zájem NA daném webu |
| Zájmy o koupi + retargeting | OR (výjimka) | Doplňují se |

**Best practices:**
- Nekombinovat různé typy cílení na jedné sestavě (pokud nechci záměrně zúžit) → místo toho **dvě sestavy**
- Více položek stejného typu = vždy OR
- Pozor na příliš úzké cílení (web + zájem + věk + pohlaví) — zásah bude minimální a reklama se nerozběhne
- Zájmy o koupi (in-market) > obecné zájmy: menší dosah, vyšší CTR i CR
- Bidding na umístění: méně kvalitní weby cca -30 %, prémiové plný bid

### Demografie

- Jen ženy → muži -100 % (a naopak); nerelevantní věkové skupiny -100 %
- Užitečná kombinace: **akviziční remarketing** — publikum 360 dní, vyloučit čerstvých 30–60 dní

## Retargetingová publika — tvorba (e-shop)

Princip **kategorie (množné číslo) + produkt (jednotné číslo)**: URL kategorie má typicky množné číslo (`/zahradni-hadice-…`), URL detailu produktu jednotné (`/zahradni-hadice-25m-…` nebo `/hadice-…`). Publikum musí pokrýt obojí:

1. Vzít URL hlavní kategorie (množné číslo)
2. Podívat se na pár produktů — jak vypadá URL detailu
3. Přidat kořen slova v jednotném čísle, pokud se liší
4. Podmínky publika jsou OR → bezpečné přidat víc variant

**Co nedělat:** neprocházet tisíce URL, nesnažit se o 100% pokrytí, nepoužívat příliš krátké kořeny (matchovaly by moc). Pokud kořen hrozí falešnými shodami s jinou kategorií → zeptat se uživatele.

Pozn.: URL fragmenty v podmínkách publika NEMUSÍ fungovat jako odkazy (substring match) — na rozdíl od `finalUrl` reklamy, která 404 mít nesmí.

## Kombinovaná (nativní) reklama — texty

Reklama se zobrazuje vedle redakčního obsahu → **musí vypadat jako titulek článku, ne jako reklama**.

> Exekuční postup (podklady → ořez → nahrání → `ads.create` → verifikace) je v **`05-KOMBINOVANA-REKLAMA-RECEPT.md`**.

### Pole a limity

| Pole | Max | Role |
|---|---|---|
| shortLine | 25 | Hlavní hook, zobrazuje se zvýrazněně |
| longLine | 90 | Hlavní titulek — konverzační, jako titulek článku |
| description | 90 | Doplněk: sociální důkaz, benefit, soft CTA |
| companyName | 25 | Značka (u loga) |

Všechna čtyři pole jsou povinná.

### Pravidla psaní

1. **Text musí dávat smysl celý** — nikdy neořezávat uprostřed věty; počítat znaky včetně mezer (`len()` v Pythonu), při přesahu přepsat kratší, ne oříznout
2. **NEKONČIT TEČKOU** — titulky článků tečkou nekončí; tečka jen uprostřed pro oddělení vět
3. **Diakritika vždy** — č, ř, ž, š…
4. Texty se v některých formátech **spojují** (shortLine + longLine, longLine + description) — musí fungovat samostatně I v kombinaci
5. Styl titulků zpravodajských/lifestyle portálů — click-worthy, ale poctivé

### 6 úhlů sdělení — checklist proti tomu, aby sada říkala pořád totéž

> Doplněno 28. 7. 2026 (zdroj: `../coverage-matrix.md`). Nejčastější slabina sady je, že 4 reklamy
> říkají jednu věc jinými slovy. Postav každou reklamu vědomě na **jednom** úhlu, nemíchat je uvnitř
> jedné reklamy.

| # | Úhel | Na co míří |
|---|---|---|
| 1 | **Pain-point** | problém, který produkt řeší |
| 2 | **Mechanism** | jak/proč to funguje |
| 3 | **Aspiration** | kým se zákazník stane, cílový stav |
| 4 | **Social-proof** | recenze, čísla, UGC |
| 5 | **Identity** | „tohle je pro lidi jako ty" |
| 6 | **Comparison** | proti alternativě / starému řešení |

Použitelné i jako checklist pro RSA v Google Ads a texty vyhledávacích kampaní.

### Vzory textů (zástupné příklady)

Příklady jsou smyšlené (cyklistika, zahrada) — jen ukazují tvar. Texty pro klienta piš z jeho
brand manuálu a webu.

| Vzor | shortLine (příklad) | longLine (příklad) |
|---|---|---|
| Storytelling / příběh | „Jak jsem dojel [cíl]" | „Příběh zákazníka, který s [produktem] zvládl [výsledek]" |
| Novinka | „Nové v nabídce" | „Nový [produkt] s [vlastností] pro [situaci použití]" |
| Cross-sell (remarketing) | „Doplňte výbavu" | „[Kategorie příslušenství] k vašemu [produktu]" |
| Dárek / balíček | „Sada s dárkem" | „Konkrétní nabídka v balíčku: [produkt] + [doplněk]" |
| Přímá otázka | „Píchli jste zase?" | „[Řešení] vás podrží i na [náročné situaci]" |
| Benefit + mechanismus | „Zalévá za vás" | „[Benefit] díky [jak to funguje] — bez [starosti]" |

**Co funguje:** storytelling (silný hook), konkrétní situace, otázky, benefit místo feature („suchá záda i v dešti", ne „materiál X"), sociální důkaz, fotky produktu v použití.
**Co nefunguje / systém odmítne:** AKCE!, SLEVA!, !!!, zavádějící zdravotní tvrzení, product-sheet výčty specifikací, tečka na konci, špatné navazování textů.

## Obrázky v obsahových reklamách

### Povinná pravidla (platforma jinak odmítne)

- Obrázek **pokrývá celou plochu** — žádné bílé dorovnávání okrajů (při resize NIKDY padding bílým pozadím → crop nebo zvětšit)
- Počítat s ořezem cca 7 % — důležité prvky mimo okraje, vycentrované
- Žádný umělý text v obrázku, žádné falešné CTA prvky, žádná animace
- Logo e-shopu NEPATŘÍ do ilustračního obrázku (logo jde zvlášť do polí pro logo)
- Obsah obrázku souvisí s textem reklamy i cílovou stránkou

### Co funguje

- **Lifestyle fotky s lidmi** > čistý packshot na bílém pozadí (v nativním feedu působí nepřirozeně)
- Produkt v kontextu použití, before/after (pokud reálné a povolené)
- **Jeden motiv = jedna reklama**: landscape + square vždy stejný motiv; více motivů = kopie reklamy se stejnými texty a jiným obrázkem (systém rotuje a vyhodnotí)

### Rozměry (kombinovaná reklama, Sklik)

> Doplněno 28. 7. 2026 — tolerance poměru, maxima a limit velikosti vytažené z `images.constraints.list`.
> Celý exekuční postup od podkladů k běžící reklamě je v **`05-KOMBINOVANA-REKLAMA-RECEPT.md`**.

| Pole (`ads.create`) | Poměr | Tolerance | Min | Max | Doporučeno | Max velikost |
|---|---|---|---|---|---|---|
| `image` (landscape) | 1,91:1 | ±0,0191 | 600×314 | 4096×4096 | 1200×628 | 1 MB |
| `imageSquare` | 1:1 | ±0,01 | 300×300 | 4096×4096 | 1200×1200 | 1 MB |
| `imageLogo` (čtverec) | 1:1 | ±0,01 | 128×128 | 4096×4096 | 1200×1200 | 1 MB |
| `imageLandscapeLogo` | 4:1 | ±0,04 | 512×128 | 4096×4096 | 1200×300 | 1 MB |

**Tolerance poměru je úzká** — čtverec musí sedět na ±1 %. Ořezávej na přesné pixely, „skoro čtverec" neprojde.
Formáty: jpg, png, gif. **Logo musí mít bílé nebo průhledné pozadí** a pokrývat plochu bez zbytečných okrajů.

**Podklady od klienta:** vyžádej si **jeden master min. 2400×1600 px**, ne hotové formáty — z něj vyřízneš
1:1 i 1,91:1 sám. Hotový text k odeslání klientovi je v `05`, §1.

### Bannery — core sady rozměrů (Sklik)

300×250, 300×600, 480×300, 970×310, 728×90, 320×100, 300×300 (rozšířené: 160×600, 480×480, 970×210, 500×200, interscroller 720×1280). Rozměr musí sedět **na pixel přesně**; max 250 KB (při přesahu snížit JPEG quality 85→75→65).

> ⚠️ Oprava 28. 7. 2026: **branding 2000×1400** byl v původním seznamu, ale v `images.constraints.list`
> v sekci `banner` není — branding je samostatný `adType`, ne banner. Limity si ověř zvlášť.

## Optimalizace obsahových kampaní

- Sledovat: CTR (cíl > 0,3 % v obsahové síti), CPC vs. strop, konverze (hlavní metrika remarketingu), frekvenci (banner blindness)
- CTR < 0,15 % po 1000+ impresích → přepsat text/kreativu
- 2–4 varianty reklam na sestavu; po 2–4 týdnech pausnout nejhorší, přidat novou
- Kreativní únava: klesající CTR v čase → výměna motivů

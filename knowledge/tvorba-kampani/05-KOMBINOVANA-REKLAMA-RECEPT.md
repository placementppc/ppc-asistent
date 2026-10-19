# Kombinovaná (responzivní) reklama — exekuční recept

> Soubory `03` a `04` říkají, JAK má reklama vypadat a na co si dát pozor.
> Tenhle soubor je postup od nuly k běžící reklamě — v pořadí, ve kterém se to reálně dělá.
> Všechny limity níže jsou **vytažené z API** (`images.constraints.list`, 28. 7. 2026), ne z dokumentace.

## Postup v kostce

```
1. Podklady od klienta   →  jeden master obrázek + logo (viz §1)
2. Ověřit limity z API   →  images.constraints.list (viz §2)
3. Připravit obrázky     →  ořez na 1:1 a 1,91:1, komprese pod 1 MB (viz §3)
4. Nahrát obrázky        →  images.create (bere VEŘEJNOU URL, ne soubor!) (viz §4)
5. Napsat texty          →  25/90/90/25, přes 6 úhlů sdělení (viz §5)
6. Vytvořit reklamu      →  ads.create, adType combined, status suspend (viz §6)
7. Verifikovat           →  ads.list — číst zpět, co tam reálně je (viz §7)
8. Aktivovat             →  až po kontrole člověkem
```

---

## §1 Podklady od klienta — co si vyžádat

Nejčastější zdržení není v API, ale v tom, že podklady od klienta jsou malé a ve špatném poměru.
Typický případ: e-shop pošle produktové fotky 500×339 px, protože přesně takové má na webu.
Na kombinovanou reklamu jsou nepoužitelné — jsou pod minimem i v jiném poměru.

**Chtěj JEDEN velký master, ne hotové formáty.** Ořez si uděláš sám a přesně:

| Co | Požadavek | Proč |
|---|---|---|
| Fotky | **min. 2400 × 1600 px**, JPG kvalita 90+ nebo PNG | Aby z jednoho souboru šel vyříznout čtverec 1200×1200 **i** landscape 1200×628 — kratší strana musí být ≥ 1200 px |
| Velikost souboru fotek | 1–3 MB klidně i víc | Limit 1 MB platí až na finální nahrávaný soubor, ten si vyrobíš sám |
| Logo | **PNG s průhledným nebo bílým pozadím**, min. 1200 px na výšku | Sklik jiné pozadí u loga odmítá |
| Logo — varianty | **čtverec (1:1) i na šířku (4:1)**, obojí | Bez obojího jde reklama ven bez loga v části formátů |

### Hotový text k odeslání klientovi

> Pro nové reklamy potřebuju obrázky ve větším rozlišení — ty současné jsou na formáty Skliku malé.
>
> **Fotky:** min. **2400 × 1600 px** (klidně větší), JPG v kvalitě 90+ nebo PNG. Velikost souboru
> 1–3 MB na kus je ideální, klidně i víc — čím míň komprese, tím líp, zmenšení si udělám sám.
> Ořez neřešte, ten si udělám podle formátů.
>
> **Logo:** samostatně, **PNG s průhledným pozadím**, min. 1200 px na výšku, ideálně ve dvou
> variantách — čtvercové (1:1) a na šířku (4:1). Bez bílých okrajů kolem.
>
> Pokud jsou originály na webu nebo v DAM/Dropboxu, stačí poslat odkaz.

**Nikdy nestahuj logo z internetu ani ho nevyráběj sám** — hrozí neaktuální verze. Když kvalitní
podklad není, radši reklamu nedělej a vyžádej si ho (viz povinná pravidla v `01`).

---

## §2 Limity — ptej se API, ne dokumentace

`images.constraints.list` vrátí **závazné limity přímo z účtu**, včetně tolerance poměru stran,
kterou nápověda vůbec neuvádí. Vyplatí se to volat před každou větší dávkou kreativ — limity se mění
a tohle je jediný zdroj, který nezastarává.

```python
r = cl.call("images.constraints.list", user_id=USER_ID)
# → {"constraints": {"banner": {...}, "combined": {...}}}
```

### Kombinovaná reklama — stav k 28. 7. 2026

| Pole v `ads.create` | Poměr | Tolerance | Min | Max | Doporučeno | Max velikost |
|---|---|---|---|---|---|---|
| `image` (landscape) | 1,91:1 | ±0,0191 | 600×314 | 4096×4096 | **1200×628** | 1 MB |
| `imageSquare` | 1:1 | ±0,01 | 300×300 | 4096×4096 | **1200×1200** | 1 MB |
| `imageLogo` | 1:1 | ±0,01 | 128×128 | 4096×4096 | 1200×1200 | 1 MB |
| `imageLandscapeLogo` | 4:1 | ±0,04 | 512×128 | 4096×4096 | 1200×300 | 1 MB |

**Tolerance poměru je klíčová** a nikde jinde ji nenajdeš: čtverec musí sedět na ±1 %, tj.
1200×1200 projde, 1200×1190 (0,99) taky, ale 1200×1180 (0,983) už ne. U landscape je tolerance
±1,91 % z hodnoty 1,91 → přípustné rozpětí zhruba 1,873–1,948. **Ořezávej na přesné pixely**,
nespoléhej na „skoro čtverec".

Formáty: **jpg, png, gif** (dle `images.create` i svg, ale u ilustračních fotek nemá smysl).

### Bannery — 12 podporovaných rozměrů, max 250 KB (256 000 B)

`300×300 · 160×600 · 728×90 · 300×250 · 300×600 · 970×310 · 320×100 · 970×210 · 480×300 · 480×480 · 720×1280 · 500×200`

Musí sedět **na pixel přesně** (jinak `invalid_size`), 336×280 podporovaný NENÍ.
Při přesahu 250 KB snižuj JPEG kvalitu 85 → 75 → 65.

> ⚠️ Pozn. k `03`: v seznamu „rozšířených" rozměrů byl uvedený **branding 2000×1400** — ten
> v `images.constraints.list` v sekci `banner` **není**. Branding je samostatný `adType`, ne banner.
> Před výrobou toho rozměru si limity ověř zvlášť, ať se nevyrábí naslepo.

---

## §3 Příprava obrázků

- **Ořez, nikdy padding.** Bílé dorovnání okrajů platforma odmítá. Když poměr nesedí → oříznout
  nebo zvětšit, ne dolepit pozadí.
- **Počítej s ořezem ~7 %** na okrajích u některých umístění → důležité prvky (obličej, produkt)
  drž vycentrované, ne u kraje.
- **Jeden motiv = jedna reklama.** Landscape i square musí být **stejný motiv**. Víc motivů =
  kopie reklamy se stejnými texty a jiným obrázkem; systém je rotuje a sám vyhodnotí.
- Lifestyle fotka s lidmi funguje v nativních pozicích líp než packshot na bílé.
- **Logo nepatří do ilustračního obrázku** — jde zvlášť do polí pro logo.

```bash
# ořez na přesné rozměry (ImageMagick), bez paddingu, s centrálním ořezem
magick master.jpg -resize 1200x1200^ -gravity center -extent 1200x1200 -quality 88 square.jpg
magick master.jpg -resize 1200x628^  -gravity center -extent 1200x628  -quality 88 landscape.jpg
# kontrola, že se vejdeš do 1 MB
ls -l square.jpg landscape.jpg
```

---

## §4 Nahrání obrázků — `images.create` bere URL, ne soubor

**Nejčastější slepá ulička.** `images.create` **nepřijímá lokální soubor ani base64** — chce
**veřejnou URL** (CDN) plus metadata (rozměry, velikost, typ). Vrací pole ID v pořadí vstupu.

Z toho plynou tři možné cesty — vyber podle situace:

| Situace | Cesta |
|---|---|
| Obrázky jsou už nahrané v účtu (z dřívějších reklam) | **Nejlepší.** Použij `imageId`, `imageSquareId`, `imageLogoId`, `imageLandscapeLogoId` — žádný upload |
| Obrázky jsou veřejně na webu klienta ve správných rozměrech | `images.create` s jejich URL |
| Máš je jen lokálně | Buď je někam veřejně nahostuj, nebo je nahraj **ručně ve Sklik UI** (má vestavěný crop nástroj, který poměry vyřeší sám) a pak je použij přes ID |

`ads.create` umí obrázky předat i **binárně** (pole `image`, `imageSquare`, `imageLogo`,
`imageLandscapeLogo`) — pro jednorázovku to je nejrychlejší cesta, jak obejít hostování.

**Logo se NEPŘEDVYPLŇUJE z účtu.** Reklama vytvořená bez polí pro logo jde ven bez loga, i když
logo v účtu je. Vždycky přilož obě varianty (nebo obě ID).

Užitečné: `images.list` v API existuje, ale nebere `{limit, offset}` jako ostatní list metody
(vrací 400) — signatura neověřená, počítej s tím, že si ID budeš muset dohledat jinak.

---

## §5 Texty — 25 / 90 / 90 / 25

| Pole | Max | Role |
|---|---|---|
| `shortLine` | **25** | Hook, zobrazuje se zvýrazněně |
| `longLine` | **90** | Hlavní titulek — jako titulek článku, konverzační |
| `description` | **90** | Sociální důkaz, benefit, soft CTA |
| `companyName` | **25** | Značka u loga |

Všechna čtyři jsou **povinná**.

### ⚠️ `shortLine` je hook, ne popisek sortimentu

Ve výpisu se `shortLine` a `longLine` zobrazují **složené do jednoho titulku, oddělené pomlčkou**:

```
Na kolo – Trailo je řada cyklistických brašen na každodenní dojíždění   ← špatně
Doprava zdarma – Brašny Trailo na kolo doručíme do druhého dne           ← správně
```

U remarketingu a e-shopů patří do `shortLine` **benefit, kvůli kterému člověk klikne** — doprava
zdarma, dodání do 24 hodin, vrácení do 365 dnů, záruka, platba na fakturu. Název produktové řady
nebo kategorie hooku nic neříká a benefity spadnou do `description`, kde je nikdo nečte.
Naučeno tvrdě: oprava znamená přepsat a znovu založit celou sadu reklam.

**Před nasazením si titulky vypiš složené (`shortLine – longLine`) a přečti nahlas.**

### Tvrdá pravidla

1. **Každé pole musí dávat smysl samostatně** — to je explicitní požadavek Skliku, protože formáty
   se liší v tom, co všechno zobrazí. Nikdy nepiš longLine jako pokračování věty ze shortLine.
2. **Zároveň musí fungovat i spojené** (shortLine + longLine, longLine + description) — v některých
   formátech se skládají za sebe. Přečti si obě kombinace nahlas.
3. **Nekončit tečkou** — titulky článků tečkou nekončí. Tečka jen uvnitř pro oddělení vět.
4. **Počítej znaky v kódu** (`len()` v Pythonu, včetně mezer a diakritiky). Při přesahu **přepiš
   kratší, neořezávej** — useknutá věta je horší než slabší formulace.
5. **Diakritika vždy.**
6. **Žádné telefonní číslo, e-mail ani URL v textech.** Naučeno tvrdě (Google zamítl sitelink
   „Zavolejte <číslo telefonu>", 16. 7. 2026). Kontakt patří do rozšíření, ne do textu reklamy.
7. Zakázané: `AKCE!`, `SLEVA!`, `!!!`, CAPS, zavádějící zdravotní tvrzení, výčty specifikací.

### Jak vyrobit sadu, která se opravdu liší

Slabina většiny sad je, že 4 reklamy říkají totéž jinými slovy. Projdi **6 úhlů sdělení**
(viz `../coverage-matrix.md`) a každou reklamu vědomě postav na jednom — nemíchat je uvnitř jedné reklamy:

| # | Úhel | Na co míří | Příklad shortLine |
|---|---|---|---|
| 1 | **Pain-point** | Problém, který produkt řeší | „Píchli jste zase?" |
| 2 | **Mechanism** | Jak/proč to funguje | „Kapková závlaha bez hadic" |
| 3 | **Aspiration** | Kým se zákazník stane | „Do práce na kole i v zimě" |
| 4 | **Social-proof** | Recenze, čísla, UGC | „Hodnotí [N] zákazníků" |
| 5 | **Identity** | „tohle je pro lidi jako ty" | „Pro každodenní dojíždění" |
| 6 | **Comparison** | Proti alternativě / starému řešení | „Místo konve jeden ventil" |

Příklady jsou smyšlené (cyklistika, zahrada) a ukazují jen tvar — texty pro klienta piš z jeho
brand manuálu a webu. Ke každému úhlu nejsilnější formáty titulku: **storytelling** („Jak jsem…"),
**přímá otázka**, **novinka**, **benefit + mechanismus**, **dárek/balíček**, **cross-sell** (u remarketingu).
Benefit vždycky před feature — „suchá záda i v dešti", ne „materiál X".

---

## §6 Vytvoření — `ads.create`

Kampaň i reklamy zakládej **`status: "suspend"`**, aktivace až po kontrole člověkem.

```python
ad = {
    "groupId": GROUP_ID,
    "adType": "combined",
    # texty
    "shortLine":   "Doprava zdarma do zítřka",        # ≤ 25
    "longLine":    "Brašny na kolo, které vydrží i celodenní liják cestou do práce",  # ≤ 90
    "description": "Vyzkoušejte 30 dní. Nesedne? Vrátíme peníze.",            # ≤ 90
    "companyName": "Nazev Firmy",                     # ≤ 25
    "finalUrl":    "https://…",                       # MUSÍ vracet HTTP 200
    # obrázky — buď ID už nahraných, nebo binárně
    "imageId":       123456,   # landscape 1,91:1   (nebo "image": <binárně>)
    "imageSquareId": 123457,   # čtverec 1:1        (nebo "imageSquare": <binárně>)
    # POVINNĚ obojí, jinak reklama jde ven bez loga
    "imageLogoId":          123458,   # 1:1
    "imageLandscapeLogoId": 123459,   # 4:1
    # volitelné, ale vyplatí se — sjednotí reklamu s brandem klienta
    "colorMain":   "000000",   # HEX BEZ mřížky — barvy z BRAND-MANUAL.md klienta
    "colorAccent": "FFFFFF",   # (zástupné hodnoty, nahraď barvami z brand manuálu)
    "status": "suspend",
}
r = cl.call("ads.create", [ad], user_id=USER_ID)
```

Další volitelná pole: `mobileFinalUrl`, `trackingTemplate`, `impressionTrackingTemplate`,
`impressionTrackingTemplate2`.

### Co čekat v odpovědi

- **status 200** = OK · **206** = vytvořeno s warningy (např. `consecutive_two_and_more_uppercase`
  u zkratek — neblokuje) · **[error]** = nevytvořeno
- **`ad_duplicate_in_db`** — příliš podobná reklama už v účtu je, a to **i pozastavená nebo smazaná**.
  Při náhradě textu měň **minimálně dvě pole**.
- **`ads.update` mění jen status**, ne obsah. Změna textu = `ads.remove` + `ads.create`.
  Totéž u bannerů — update neexistuje.

---

## §7 Verifikace — vždycky číst zpět

**Sklik tiše odstraňuje zakázané znaky** (ověřeno na pomlčce „—" v `longLine`) — bez varování,
bez warningu. Reklama pak běží s textem, který jsi nenapsal.

```python
ads = cl.call("ads.list", {"group": {"ids": [GROUP_ID]}},
              {"limit": 100, "offset": 0,
               "displayColumns": ["id", "adType", "shortLine", "longLine",
                                  "description", "companyName", "finalUrl", "status"]},
              user_id=USER_ID)
```

### Checklist před aktivací

- [ ] Texty v účtu se **znak po znaku** shodují s tím, co jsi poslal
- [ ] Logo je na reklamě vidět (obě varianty nahrané)
- [ ] Obrázek odpovídá produktu v textu **i** obsahu cílové stránky
- [ ] `finalUrl` vrací **HTTP 200** (404 = zamítnutí)
- [ ] Korekce zařízení sedí na **všech** sestavách (`devicesPriceRatio`, -100 pro vyloučení)
- [ ] U remarketingu je publikum přiřazené ke **všem** sestavám a není `null`
- [ ] Sestava má přiřazená umístění, pokud jsi necílil záměrně na celou síť
- [ ] Rozpočet a CPC jsou konzervativní, u akční kampaně je nastavený `endDate`
- [ ] **Texty prošel člověk** — AI-generovaný text bez kontroly je policy riziko

Teprve pak `status: "active"`.

---

## §8 Po spuštění

| Signál | Práh | Reakce |
|---|---|---|
| CTR | < 0,15 % po 1000+ impresích | přepsat text nebo vyměnit kreativu |
| CTR | benchmark 0,3–0,6 % | vždy poměřuj s historií účtu, ne s cizím číslem |
| Klesající CTR v čase | — | kreativní únava → výměna motivu, ne textu |
| Počet variant | 2–4 na sestavu | po 2–4 týdnech pausnout nejhorší, přidat novou |

Při vyhodnocování A/B varianty: **minimálně ~100 prokliků na variantu** a měň vždy **jen jeden
prvek**, jinak nepoznáš, co zabralo. Metodika a zápis experimentu: `../reklamy-ab-testy.md`.
Statistiky kombinovaných reklam se čtou přes report reklam (`adType: combined`).

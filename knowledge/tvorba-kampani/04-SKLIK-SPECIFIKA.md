# Sklik — specifika platformy a DRAK API

Ověřená praxe pro práci se Sklik DRAK API (v5, JSON) a odlišnosti od Google Ads.

> Konektor a příklady volání: `scripts/sklik/`. Závazné limity: `../api-limity-bezpecnost.md`.

## Rozdíly Sklik vs. Google Ads

| Oblast | Google Ads | Sklik |
|---|---|---|
| Longtail KW | Malý objem → nemusí zobrazit | Zobrazí data i na 1 zobrazení |
| Skóre reklamy | Sofistikovaný Ad Rank | Jednodušší skóre |
| Shopping | Nákupy / PMax | Zboží kampaně (typ `product`) |
| Model | Primárně CPC | CPC i CPT (cena za tisíc) |
| Obsahová síť | GDN globálně | Weby Seznamu + partnerské weby |
| Mobilní kliky v obsahu | Menší problém | Riziko omylných kliků (pop-upy, reklamy v obrázcích) → nízké CPC mimo prémiové weby |
| Reklamy ve vyhledávání | Jen **RSA** (ETA zrušené 6/2022) | Pořád **ETA** (`adType: eta`) |

## Základní API pravidla

- **Ceny a rozpočty v haléřích** (500 Kč = 50000, 3 Kč CPC = 300)
- Typ kampaně: `fulltext` (vyhledávání), `context` (obsah), `product` (Zboží)
- `startDate` / `endDate` na úrovni kampaně (`YYYY-MM-DD`) — u akčních kampaní VŽDY nastavit endDate
- Kampaně zakládat se `status: "suspend"`, aktivovat až po kontrole
- Před prací zavolat `api.limits` (minuteRequestLimit, dayRequestLimit, batchCallLimits, statsDataLimit) a respektovat
- Sériové requesty, dávky ~50, backoff na HTTP 429 (5→10→20→40 s, max 5 pokusů)
- Agenturní přístup: hlavní token → session, do datových metod user struct `{"session": ..., "userId": <klientský>}`

## ⚠️ Gotchas ověřené praxí

### Po vytvoření VŽDY verifikovat

- **`campaigns.create` spolehlivě nezapisuje budget/status** — po každém create ověřit `status` + `budget.dayBudget` přes `campaigns.list` s `displayColumns`, případně opravit přes `campaigns.update`
- Korekce zařízení, publika u remarketingu, finální texty — vše zkontrolovat čtením zpět

### Úprava reklam

- **`ads.update` mění jen status** (active/suspend), NE obsah → změna textu = `ads.remove` + `ads.create`
- **Duplicitní detekce (`ad_duplicate_in_db`)**: příliš podobná reklama (i vůči pozastaveným/smazaným) se odmítne → při náhradě změnit min. 2 pole
- **Sklik tiše odstraňuje zakázané znaky** (např. pomlčku „—" z longLine bez varování) → po vytvoření ověřit finální znění přes `ads.list`
- Warningy neblokují (`consecutive_two_and_more_uppercase` u zkratek OK), blokují jen `[error]` odpovědi; status 206 = vytvořeno s warningy

### Časově omezené kampaně, zařízení a token (ověřeno na podzim 2026)

- **`endDate` přes API = půlnoc na ZAČÁTKU dne.** Má-li kampaň běžet celý poslední den akce, pošli `endDate`
  o den později (napoveda.sklik.cz → Práce s API Drak). V rozhraní je to od 2/2020 naopak včetně — neplést.
  Kampaň s budoucím `startDate` musí být `active`, jinak se sama nespustí.
- **`devicesPriceRatio` jde nastavit i na kampani** (`campaigns.create` / `campaigns.update` + `type`).
  Při dělení PC / mobil po kampaních nastav −100 % tam i na sestavách — viz `03`, struktura sestav.
- **Obrázkové bannery:** `banners.create` (`groupId`, `name`, `clickthruUrl`, `status`, `file` binárně
  přes XML-RPC), čtení `banners.list` s filtrem `{"group": {"ids": [...]}}`, aktivace `banners.update`.
  Hotový skript: `scripts/sklik/apply_banner_campaign.py`.
- **Token se liší podle agentury.** Účet, ke kterému má přístup jiný agenturní účet, jde jen přes
  token toho účtu (např. `SKLIK_DRUHY_TOKEN`); výchozí `SKLIK_API_TOKEN` na něm vrací 403. Pro `fetch.py` přepiš proměnnou prostředí
  `SKLIK_API_TOKEN` hodnotou správného tokenu (env má přednost před `.env`).

### Klíčová slova

- **CPC neposílat u `keywords.create`** — cena jen na sestavě (default CPC); omylem nastavené KW CPC se ruší přes `keywords.update` s `cpc: null`
- Duplicita KW → status 406 `keyword_duplicate`
- **`keywords.negative.create` funguje jen s `groupId`** — kampaňová negativa se přidávají na všechny sestavy kampaně

### Cílení na zařízení — `devicesPriceRatio`

Na úrovni sestavy přes `groups.update`; -100 = nezobrazovat:

```python
# Mobilní sestava (mobil + tablet + ostatní)
{"desktop": -100, "mobile": 0, "tablet": 0, "other": 0}
# Desktopová sestava (jen desktop)
{"desktop": 0, "mobile": -100, "tablet": -100, "other": -100}
```

Nastavit IHNED po `groups.create`, před aktivací — bez toho se reklamy zobrazují všude.

### Retargeting — správné endpointy a field names

```python
# Include publikum na sestavě:
retargeting.group.lists.add      → {"listId": ..., "groupId": ...}
# Exclude publikum na sestavě:
retargeting.group.negative.add   → {"entityId": ..., "groupId": ...}
# Exclude publikum na kampani:
retargeting.campaign.negative.add → {"entityId": ..., "campaignId": ...}
```

NEFUNGUJE: `groups.update` s `retargetingListIds` ani `campaigns.update` s `retargetingNegativeListIds` — tato pole neexistují.

### Zájmy a zájmy o koupi

- Obecné zájmy: `interests.listCategories` / `interests.create` (na sestavě, hierarchické, parent pokryje children)
- Zájmy o koupi (in-market): `intends.getCategoryList` / `intends.create` (na sestavě)
- Více položek stejného typu = OR; **různé typy cílení na jedné sestavě = AND (zúžení!)** — viz pravidla kombinací v souboru 03

### Umístění (patterns)

- `patterns.*` namespace — pattern je doména nebo cesta (`"example.cz"`, `"www.example.cz/sekce"`), přiřazuje se na sestavu, volitelně vlastní CPC
- **Nová obsahová sestava NEMÁ žádná umístění = jede na celou síť** → při cílení na konkrétní weby přidat umístění PŘED aktivací

### Sitelinky a popisky

- Sitelinky: `sitelinks.create` (name max 25 znaků, url) → `sitelinks.campaign.set`; dedup podle názvu (406 `sitelink_duplicity`)
- **Popisky (callouts) = sitelink BEZ `url`** (`sitelinks.create` s jen `name`, pak `sitelinks.campaign.set` / `group.set`) —
  ověřeno na podzim 2026 (`scripts/sklik/apply_sitelink_changes.py`). `*.set` NAHRAZUJE celé přiřazení → posílat kompletní seznam.
  Telefon DRAK API nastavit neumí (žádná metoda) → knihovna rozšíření v UI (Nastavení).

### Bannery

- `banners.*` namespace pracuje **jen s obrázkovými bannery** (JPG/PNG/GIF, base64 v poli `file`)
- **HTML5 bannery (ZIP) přes API nelze** vytvářet, upravovat ani mazat — jen web UI; ve statistikách reklam se ale objevují (`adType: html5_banner`)
- Rozměr musí sedět **na pixel** (jinak `invalid_size`); 336×280 NENÍ podporován; max 250 KB (256 000 B)
- Podporovaných rozměrů je dle API **12**: `300×300 · 160×600 · 728×90 · 300×250 · 300×600 · 970×310 ·
  320×100 · 970×210 · 480×300 · 480×480 · 720×1280 · 500×200`. **Branding 2000×1400 mezi nimi NENÍ** —
  branding je samostatný `adType`, limity si ověř zvlášť (doplněno 28. 7. 2026)
- Neexistuje banner update — náhrada = remove + create

### Kombinovaná reklama a logo

- **Účtové logo se přes API NEPŘEDVYPLŇUJE** — reklama vytvořená přes `ads.create` bez polí pro logo jde ven BEZ loga
- Proto POVINNĚ přikládat obě loga do každého `ads.create` (adType `combined`)
- Sklik u loga vyžaduje **bílé nebo průhledné pozadí** (na rozdíl od ilustračních obrázků, kde se pozadí neřeší)

> Doplněno 28. 7. 2026 — ověřeno proti `ads.create` a `images.constraints.list`.
> Celý postup: **`05-KOMBINOVANA-REKLAMA-RECEPT.md`**.

**Obrázky lze předat DVĚMA způsoby** (vzájemně se vylučují):

| Binárně | Přes ID už nahraného obrázku |
|---|---|
| `image` (landscape 1,91:1) | `imageId` |
| `imageSquare` (1:1) | `imageSquareId` |
| `imageLogo` (1:1) | `imageLogoId` |
| `imageLandscapeLogo` (4:1) | `imageLandscapeLogoId` |

→ Když jsou obrázky nebo logo v účtu už z dřívějších reklam, **použij ID a nic nenahrávej**. To je
nejrychlejší cesta a řeší i situaci, kdy máš podklady jen lokálně.

**Další pole u `combined`, která stojí za to používat:**

- `colorMain`, `colorAccent` — HEX **bez mřížky**, lze `null`. Sjednotí reklamu s brandem klienta.
- `mobileFinalUrl`, `trackingTemplate`, `impressionTrackingTemplate`, `impressionTrackingTemplate2`
- Povinná textová pole: `shortLine` (25), `longLine` (90), `description` (90), `companyName` (25), `finalUrl`

Hodnoty `adType` u `ads.create`: **`eta`** (rozšířená textová), **`combined`**, **`branding`**, **`dynamicBanner`**.
→ **Sklik nemá RSA ve vyhledávání** — „responzivní" reklama = `combined` a patří do obsahové sítě.

### Obrázky — `images.*`

- **`images.create` bere VEŘEJNOU URL** (CDN) + metadata (rozměry, velikost, typ), **ne lokální soubor ani base64**.
  Vrací pole ID v pořadí vstupu. Kdo má podklady jen na disku: buď nahostovat, nebo nahrát ručně
  ve Sklik UI (má crop nástroj), nebo je poslat binárně přímo v `ads.create`.
- **`images.constraints.list` = zdroj pravdy pro limity** — vrátí min/max rozměry, doporučené rozměry,
  **toleranci poměru stran** (nikde v nápovědě není) a max velikost, zvlášť pro `banner` a `combined`.
  Volat před každou větší dávkou kreativ; nápověda zastarává, tohle ne.
- `images.list` existuje, ale nebere `{limit, offset}` jako ostatní list metody (vrací 400) — signatura neověřená.
- Diagnostiky, na které narazíš: `image_height_too_large`, `image_width_too_low`, `image_too_large`.

### Binární obrázky → XML-RPC, ne JSON (ověřeno v praxi na dávce desítek reklam)

`ads.create` umí obrázky binárně, ale „binary" je podle `usage.html` **XML-RPC base64 hodnota**.
Nejjistější cesta je proto `xmlrpc.client` se `Binary(...)` — žádné hádání JSON kódování.
Hotový skript: `scripts/sklik/apply_rmkt_res.py`.

- Endpoint je **`https://api.sklik.cz/drak/RPC2`**. `/drak/RPC2/v5` vrací **404**.
- `ServerProxy(url, allow_none=True)`, tečkové názvy metod fungují (`proxy.client.loginByToken`).
- Takhle jde nahrát lokální soubory bez hostování na CDN — `images.create` chce veřejnou URL.

### `ads.check` jako dry-run kombinovaných reklam — má tři pasti

1. **Pole `status` nepřijímá** (400 `not_allowed_struct_field`), i když ho `ads.create` vyžaduje.
2. `checkDuplicity` (default True) **se vylučuje s binárními obrázky**. Musíš poslat
   `{"checkDuplicity": False}` → tím ale server přepne na interní `fastCheck=True`…
3. …a **`fastCheck` se vylučuje i s `imageId` / `imageLogoId` / `imageLandscapeLogoId`**.
   `fastCheck` se přitom nastavit nedá (`options` ho jako pole nezná).

→ Jediná průchozí kombinace: `{"checkDuplicity": False}` + **všechny čtyři obrázky přes `*Meta`**
(`imageMeta`, `imageSquareMeta`, `imageLogoMeta`, `imageLandscapeLogoMeta`), struktura
`{width, height, size}` (size v **bajtech**). Ověří texty, URL, rozměry i poměry stran.
**Duplicitu vůči účtu tímhle neověříš** — to se pozná až při `ads.create`.

### Signatury, které se liší od zbytku API

| Metoda | Past |
|---|---|
| `campaigns.create` | `startDate` / `endDate` musí být **datetime**, string dá 400 `wrong_param_type` |
| `campaigns.update` | vyžaduje i **`type`**, jinak 400 `missing_struct_field` |
| `campaigns.list` | bez `{offset, limit}` v displayOptions vrací 400 |
| `groups.create` vs `groups.list` | zapisuje se `cpc` a `maxUserDailyImpression`, čte se **`maxCpc`** a **`maxUserDailyImpressions`** (plurál) |
| `retargeting.lists.list` | vrací **`listId`**, ne `id`; `retargeting.lists.get` přidá `users` = velikost publika |
| `retargeting.group.lists.list` | bere **pole ID** jako druhý parametr, ne restrictionFilter struct |
| `campaigns.createReport` | `dateFrom` / `dateTo` patří do **restrictionFilter** jako `YYYY-MM-DD` |
| `campaigns.readReport` | reportId posílat jako **string**. `displayColumns` **bere** (ověřeno 23. 9. 2026: `id, impressions, clicks, clickMoney, conversions, conversionValue, transactions` + `allowEmptyStatistics`). `clickMoney` je v haléřích, `conversionValue` v Kč. Starší záznam „nebere displayColumns“ platil pro jiné volání |
| `campaigns.update` (stav) | Vyžaduje i `type` (`fulltext`/`context`…), jinak 400 „Field campaigns[0].type must be present“. Pauza: `{"id": X, "type": "fulltext", "status": "suspend"}`. `campaigns.check` pole `status` nepřijímá (ověřeno 5. 10. 2026) |
| Negativa | `campaigns.list` negativa kampaní nevrací; čtou se přes `keywords.campaign.negative.createReport/readReport`. `campaigns.update` posílá celé pole `negativeKeywords` → bez přečtení hrozí přepsání. Sestavová negativa: `keywords.negative.create` (jen přidává), `keywords.negative.list` (filtr `group.ids`), `keywords.negative.remove(groupId, [{name, matchType}])`. `keywords.list` negativa NEvrací. Duplicity hlásí `keywords.negative.check` jako `keyword_duplicate`, `requestId` = 0-based index v dávce (ověřeno 5. 10. 2026) |
| `queries.createReport` | Dotazy k KW; `dateFrom/dateTo` v restrictionFilter, filtr `campaign.status: ["active"]`. `readReport` po 5 000, metriky ve `stats[0]`, `totalMoney` v haléřích |
| `campaigns.createReport` + zařízení | Filtr `"deviceType": ["deviceDesktop"]` (dále `devicePhone` / `deviceTablet` / `deviceOther`) v restrictionFilter, na každé zařízení jeden report. Metriky pak přijdou vnořené: `stats[i]["deviceDesktop"]["clicks"]`. S `allowEmptyStatistics` v displayOptions createReportu vrátil 400 (bez něj OK). Funguje i pro typ `zbozi` (ověřeno 23. 9. 2026) |
| `api.limits` | volá se **bez `userId`**, s ním vrací 400 |

### Logo bez podkladů od klienta

Když v účtu už běží nějaká kombinovaná reklama, přečti z ní `imageLogo.id` a `imageLandscapeLogo.id`
přes `ads.list` (displayColumns `imageLogo.id`, `imageLandscapeLogo.id`, …) a **použij stejná ID**.
Je to aktuální logo schválené klientem, na rozdíl od čehokoli staženého z webu. Ve stejném dotazu
vytáhneš i `colorMain` / `colorAccent` a sjednotíš tím vzhled s ostatními kampaněmi.

### Mrtvá retargetingová publika po změně URL webu

Publika s podmínkou na starou cestu (`basket`, `order1`) se po redesignu **tiše přestanou plnit** —
v UI vypadají živě, protože jsou `active`. Poznáš to jen podle `users` z `retargeting.lists.get`.
**Před stavbou remarketingu vždycky projeď velikosti publik** a podmínky porovnej se skutečnými
URL webu. Nové publikum zakládej s `useHistoricData: true`, doplní se ze zpětné historie.

### E-mailová publika

- `retargeting.emails.list` → přiřazení na sestavu přes `group.lists.add` s `emailId`

### Reporty a statistiky

- Stats requesty držet pod `statsDataLimit`; delší období nebo mnoho entit → rozdělit
- Statistiky bannerů/kombinovaných reklam jdou přes report reklam (`adType: banner | html5_banner | combined`)
- **Product sety:** `productSets.list` neexistuje → report flow (`productSets.createReport` → `readReport`).
  `readReport` **nebere `displayColumns`** (400 Bad arguments) — jen `offset` + `limit`

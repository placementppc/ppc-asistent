---
name: produktovy-report
description: >
  Produktový report katalogové (DPA / Advantage+ catalog) reklamy na Meta — spend vs. obrat
  po jednotlivých produktech, trend 30d vs. 7d a návrhy, které produkty vyloučit z katalogu.
  Použij vždy, když uživatel chce vidět výkon produktů v katalogové reklamě — např. „projdi
  produkty v katalogu u klienta X", „spend vs. obrat produktů", „které produkty vyloučit",
  „co se nám v katalogu neprodává", „produktový report za 30 dní", „které produkty jen žerou
  rozpočet", „mrkni na ROAS jednotlivých produktů", „DPA report". Read-only, per-klient,
  per-trh. NEJDŘÍV se ptá, jestli data smí do cloudu (NDA), pak teprve pracuje.
---

# Produktový report — katalogová reklama na Meta

Jsi **seniorní PPC specialista**. Tenhle skill vytáhne výkon **jednotlivých produktů v katalogové
reklamě** (DPA / Advantage+ catalog), porovná spend proti obratu, spočítá trend a navrhne, které
produkty vyřadit z produktového setu. Je **POUZE PRO ČTENÍ**. Navazuje na `ppc-fachman`; drž stejná
pravidla (cíle klienta, API limity, konzervativní senior úsudek, learning smyčka).

---

## 🔴 KROK 0 — Zeptej se na režim dat. Vždy. Než cokoliv stáhneš.

Někteří klienti mají **NDA**. Skript běží lokálně vždy, ale cokoliv, co si přečteš a napíšeš do
chatu, jde na servery poskytovatele modelu. **Tohle je blokující otázka** — nepokračuj, dokud
neznáš odpověď, a nehádej ji z kontextu.

Zeptej se přesně takhle:

> Než začnu: mají se data u tohohle klienta držet **jen lokálně** (NDA), nebo můžou jít do chatu?
> 1. **Jen lokálně** — skript sám napíše hotové PDF na disk, já do dat vůbec nekouknu
>    a název klienta se nedostane ani do reportu, ani do názvů souborů.
> 2. **Jen agregáty** — přečtu si součty a top 10 produktů, dlouhý ocas zůstane na disku.
> 3. **Vše** — přečtu celý report a napíšu doporučení k jednotlivým produktům.

Podle odpovědi:

| Režim | Jak pracuješ |
|---|---|
| **Jen lokálně** | Skripty spouštěj **vždy s `--quiet` a `--anonym`**. Výstup skriptu **nečti**. Ověřuj jen metadata (že soubor vznikl, kolik má řádků přes `wc -l`). Do chatu piš pouze cesty k souborům a co v nich uživatel najde. **Název klienta nepiš nikam** — ani do reportu, ani do názvů souborů, ani do svých odpovědí. Používej neutrální označení („klient", „účet"). |
| **Jen agregáty** | Čti souhrnné tabulky (sekce 1 a hlavičky sekcí) a maximálně top 10 řádků. Nikdy nevypisuj celé CSV. Název klienta v chatu je OK, pokud ho uživatel sám použil. |
| **Vše** | Běžná práce, čti report i CSV. |

**K anonymizaci názvu klienta v lokálním režimu — buď upřímný o tom, co to umí a co ne.**
`--anonym` zajistí, že název klienta nebude v reportu ani v PDF. **Název souboru řídí `--out`,
takže v anonymním režimu ho zadej bez jména klienta** (např. `data/reports/produkty-<datum>`), a ty ho
nezopakuješ ve svých odpovědích. **Co už zpětně nespravíš:** pokud uživatel klienta pojmenoval
sám ve své zprávě („projdi produkty u klienta Acme"), ta zpráva už odešla. Řekni mu to a nabídni,
ať příště píše „spusť produktový report pro účet act_XXXX" nebo si zavede interní kód.
Pozor i na to, že **názvy produktů klienta často prozradí** — v přísném režimu je do chatu nepiš.

Když uživatel řekne „je to jedno" nebo neodpoví jasně → **ber to jako režim 1** (nejpřísnější).
Rozhodnutí si u klienta poznamenej do `clients/<slug>.md` (sekce `ppc-config`, klíč `data_rezim`),
ať se příště ptát nemusíš — ale i tak ho na začátku běhu **zopakuj k potvrzení**.

Token a přístupy zůstávají v `.env` a do chatu **nepatří nikdy**, v žádném režimu.

---

## 🔴 Další neporušitelná pravidla

1. **Read-only.** Tenhle skill nikdy nezapisuje do účtu. Vyloučení produktu z katalogu = **návrh
   ke schválení**, ne provedená změna. Samotnou úpravu product setu řeší až `ppc-fachman` po
   explicitním odsouhlasení.
2. **Per-klient, per-trh.** Account ID **nikdy nehádej ani nedávej natvrdo** — vždy z
   `clients/<slug>.md`. Klient může mít víc účtů (jeden per země), každý s vlastním katalogem.
3. **Respektuj API limity** (`knowledge/api-limity-bezpecnost.md`). Sériově, s backoffem, nikdy
   víc běhů paralelně. 30denní okno s produktovým breakdownem **musíš krájet po týdnech** — Meta
   ho synchronně nevrátí (`code=2 / subcode=1504038`).
4. **Statistická významnost > prahy.** Práh je spouštěč pozornosti, ne rozsudek. U produktu
   s třemi kliky nerozhoduješ.
5. **Vždy zapiš a uč se** — vzorec u klienta do `clients/<slug>.md`, obecný do
   `knowledge/_learnings.md`.

---

## ⚠️ Tři pasti, na kterých se to dá pokazit

### 1. `breakdowns=product_id` NENÍ „co se zobrazilo v katalogové reklamě"

Meta vrací produktové řádky **i pro bannery a videa bez katalogu** — tam produkty pocházejí
z **pixelu** (`content_ids` z ViewContent/Purchase na webu), tedy „co si člověk po prokliku
prohlédl a koupil", ne „co mu reklama ukázala".

**Vždy** proto reklamy klasifikuj podle `creative{product_set_id}` na úrovni **reklamy** a do
reportu pusť jen ty katalogové. Název kampaně o tom neříká nic — v jedné ASC kampani běží katalog
i bannery vedle sebe. (V praxi bývá katalogových jen malá část reklam s produktovými řádky
a smíchané ROAS produktu se od čistě katalogového může lišit i několikanásobně.)

### 2. Zkontroluj, který `action_type` se v účtu reálně plní

V produktovém breakdownu umí Meta vracet `omni_purchase` / `purchase` / `offsite_conversion.
fb_pixel_purchase` jako **nuly** a plnit jen `onsite_web_purchase`. Kdo to nezkontroluje, přečte
report jako „nula konverzí".

**Nejdřív si vypiš, jaké action_type v datech jsou a které jsou nenulové**, teprve pak počítej.
Ber první nenulový v pořadí `onsite_web_purchase → omni_purchase → purchase →
offsite_conversion.fb_pixel_purchase`.

### 3. CTR a CPC ber **na odkaz**, ne ze všech kliknutí

- CTR na odkaz = `inline_link_clicks / impressions` (odpovídá Meta `inline_link_click_ctr`)
- CPC na odkaz = `spend / inline_link_clicks`

CTR všech kliknutí je zhruba o pětinu vyšší a prahy by pak neseděly. Po prvním běhu si shodu
s `inline_link_click_ctr` **ověř** na jedné reklamě.

---

## Prahy (sdílené pro všechny klienty)

| Co | Práh | Proč |
|---|---|---|
| Návrh na vyřazení | **3× CPA** utraceno, **nula nákupů** | Očekávané 3 nákupy, nula má p≈5 % (Poisson) |
| Watchlist | **ROAS < 1,1** a aspoň 1 nákup | Produkt prodává, ale nevydělává |
| Nezajímavý produkt | **CTR na odkaz < 1 %** | Lidi v katalogu neosloví |
| Drahý proklik | **CPC na odkaz > 1,5× průměru** katalogu | Žere rozpočet rychleji než ostatní |
| Minimum pro CTR/CPC | **500 impresí** | Pod tím je to šum |
| Tahoun | spend ≥ 2× CPA a ROAS ≥ 6 | Kandidát na posílení |
| Pravděpodobně vyprodáno | **spend za 7 d o 70 % nižší** než za předchozích 7 d, ≥ 500 impresí za 30 d | Stejně dlouhá okna → srovnatelné částky |
| Novinka | **nula spendu** v prvních 23 dnech, ≥ 100 impresí za 7 d | Rozběhlo se to až teď |

**Sekce 2g srovnává týden vs. týden** (posledních 7 dní proti předchozím 7). Obě okna jsou stejně
dlouhá, takže se porovnávají přímo částky — nemusíš přepočítávat na denní tempo. Kdybys srovnával
různě dlouhá okna (7 vs. 23 dní), musel bys počítat denní tempo, jinak vyjde „pokles" i u produktu,
který jede pořád stejně. Řaď podle spendu v **předchozím** týdnu — nahoře pak je to, kde zmizelo
nejvíc peněz, ne to, co ještě zbylo.

Tohle srovnání vyžaduje okno **`prev7d`** ve staženém `_raw.json`. Když ho tam nenajdeš, data
jsou ze staršího běhu — stáhni je znovu, nedopočítávej to z delšího okna.

**Obě sekce jsou domněnka, ne fakt, a musí to být v reportu napsané.** Z insights nepoznáš, jestli
produkt zmizel ze skladu, vypadl z feedu, změnil cenu, byl zamítnutý, nebo mu jen algoritmus ubral
rozpočet. Stejně tak „nula spendu dřív" neznamená „nebyl ve feedu" — mohl v něm ležet a Meta ho
nezobrazovala. Piš to jako **seznam k ověření proti katalogu** (pole `availability`).
U novinek navíc **nehodnoť ROAS** — pár dní dat nic neznamená.

**CPA počítej jako vážený průměr celého katalogu ve stejném 30denním okně**: spend katalogu ÷
nákupy katalogu, z dat na úrovni reklam **bez** produktového breakdownu. Ne průměr produktových CPA
(produkt s jedním nákupem by měl stejnou váhu jako tahoun) a ne CPA z jiného období.

**Sekce s prázdným výsledkem nechávej v reportu** a vždy k nim vypiš **rozložení hodnot**
(min / p10 / medián / p90 / max + počty pod několika prahy). Bez toho nepoznáš, jestli práh nic
nechytil proto, že je vše v pořádku, nebo proto, že je špatně nastavený. Typický případ: práh
CTR pod 1 % nechytí nic, protože medián katalogu je vysoko nad ním.

**Override prahů** jen s důvodem (jiná marže, jiná vertikála, brand kampaň) — přes CLI parametry,
a poznamenej ho do `clients/<slug>.md`.

---

## Workflow

### 1. Režim dat
Viz **KROK 0** výše. Blokující.

### 2. Klient a účet
- Ze zadání vytáhni **slug klienta** a **trh**. Když trh neřekne → default CZ.
- Z `clients/<slug>.md` vezmi `act_` pro daný trh, měnu účtu a **cílový ROAS / marži**, pokud tam
  je. Když je účtů víc a trh neupřesnil → **zeptej se**, nehádej.

### 3. Stáhni data
V našem repu:
```bash
python3 scripts/meta/product_report.py --account act_XXXX --out data/reports/produkty-<datum> --quiet
```
Skript stáhne čtyři okna (**30 dní**, **7 dní**, **předchozích 23 dní** na trend
a **předchozích 7 dní** na srovnání týden vs. týden), klasifikuje
reklamy podle `product_set_id` a uloží `_raw.json` + CSV. 30d krájí po týdnech automaticky.

**Bez našich skriptů** (cizí prostředí) je to Graph API `GET /{act_id}/insights` s:
- `level=ad`, `breakdowns=product_id`, `limit=500`, stránkovat přes `paging.next`
- `fields=ad_id,ad_name,campaign_name,spend,impressions,inline_link_clicks,actions,action_values`
- `time_range={"since":…,"until":…}` — **po max. 7denních blocích**, sečíst (Meta atribuuje
  konverze k datu imprese, takže součet dílů = celek)
- k tomu `GET /{campaign_id}/ads?fields=id,name,creative{product_set_id,object_type}` na
  klasifikaci (na úrovni účtu to padá na HTTP 500 — ptej se po kampaních)
- poslední den = **včerejšek**, dnešek je nekompletní

U feedu s variantami agreguj produkty po **modelech** — když `product_id` nese i variantu (např.
`retailer_id, název` s velikostí na konci), sluč varianty (utni od označení velikosti nebo podobného
přívlastku varianty), jinak máš stovky řádků po jednom kliku.
Skript to umí parametrem `--varianta-regex` (výchozí prázdné = neslučuje), např.
`--varianta-regex '\s+(velikost|size)\b.*$'` — výraz si nastav podle toho, jak varianty píše feed.

### 4. Vygeneruj report (PDF)
```bash
python3 scripts/meta/product_report_md.py --raw <prefix>_raw.json --out <prefix>.md --client "<Klient>" --quiet
python3 scripts/meta/report_pdf.py <prefix>.md <prefix>.pdf "Produktový report — katalogová reklama"
```
**Výstup je vždy PDF** (markdown a CSV jsou podklad). `report_pdf.py` sází přes headless Chrome —
A4 na šířku, žádné knihovny navíc. Bez Chrome PDF nevznikne; markdown a CSV ano, tak to řekni.

Volitelně `--watch-roas`, `--cpa-nasobek`, `--ctr-prah`, `--cpc-nasobek`, `--min-impresi`,
a v lokálním režimu **povinně `--anonym`**.
Přegenerování je **bez nového stahování** — data už jsou v `_raw.json`.


### 5. Struktura reportu
1. **Úroveň účtu** — spend účtu, spend katalogu, podíl, obrat, ROAS, PNO, nákupy, CPA; 30d i 7d
2. **Produkty katalogu**
   - 2a **Kam jdou peníze** — top 30 podle spendu, s podílem a kumulativním %
   - 2b **Tahouni** — kandidáti na posílení
   - 2c **Jen utrácejí, nula nákupů** — podle spendu, se značkou ⛔ vyloučit / ⚠️ zkontrolovat web / · málo dat
   - 2d **Watchlist** — ROAS pod prahem
   - 2e **Nezajímavé** — nízké CTR na odkaz + rozložení
   - 2f **Drahé prokliky** — CPC nad násobkem průměru + rozložení
   - 2g **Pravděpodobně vyprodané** — spend za 7 dní o 70 % nižší než předchozích 7 dní
   - 2h **Novinky** — spend až v posledních 7 dnech, předtím nula

**Sekce 2a je povinná a nesmí být výběr podle prahu.** Všechny ostatní sekce jsou seznamy výjimek
(nulové, ztrátové, drahé) — produkt s velkým spendem a **průměrným** ROAS nepadne do žádné z nich
a v reportu pak není vidět vůbec, přestože je v něm většina rozpočtu. V praxi se tak stalo, že
největší utrácející produkt katalogu s průměrným ROAS se neobjevil v žádné ze sekcí,
dokud tahle nepřibyla. Přidej k ní i **koncentraci** (top 10 / 25 / 50 = kolik % spendu).
3. **Metodika a omezení** — vždy, ať report obstojí i bez tebe

V markdownu **max 60 řádků na tabulku**, plný seznam do CSV, a u zkrácené tabulky **napiš, kolik
řádků a kolik spendu jsi neukázal**. Tiché ořezání vypadá jako úplnost.

### 6. Rozděl nulové produkty na dvě skupiny — mají jiné řešení
- **nula nákupů i nula přidání do košíku** → produkt v reklamě nefunguje → kandidát na vyloučení
- **nula nákupů, ale lidé ho do košíku dávali** → problém je **za proklikem** (cena, dostupnost
  variant, doprava, checkout) → vyloučením z katalogu bys léčil symptom; pošli to klientovi
  na kontrolu webu

### 7. Závěr a návrhy
Piš v rozsahu, který odpovídá zvolenému režimu dat. Vždy uveď:
- co je **statisticky obhajitelné** (nad prahem) a co je **dlouhý ocas** (pod prahem, nechat běžet)
- **kolik peněz** je v každé skupině, ne jen kolik produktů — 700 nulových produktů může být 11 %
  spendu a tedy skoro nic
- **průnik signálů** je silnější než jeden práh: drahé CPC **a zároveň** ROAS pod prahem je
  použitelnější seznam než kterákoli z těch dvou sekcí zvlášť
- návrh vždy jako **návrh ke schválení**, nikdy jako provedenou změnu

### 8. Zapiš a uč se
Vzorec u klienta („kategorie A drží ROAS, sezónní kategorie B padá po sezóně") → `clients/<slug>.md`.
Obecný → `knowledge/_learnings.md`. Schválené změny jdou standardní smyčkou `ppc-fachman`
(changelog s baseline → příští běh vyhodnotí).

---

## Co skript rozhodnout neumí — zeptej se

**Cílový ROAS nebo marže.** Bez nich je watchlist na hranici „aspoň se to zaplatí" (ROAS 1,1), což
není zisková hranice. Při marži 40 % je break-even ROAS 2,5 a watchlist může narůst z jednotek
produktů na polovinu katalogu. Když číslo nemáš, **řekni to nahlas v závěru reportu** a doplň ho
do `clients/<slug>.md`, jakmile ho klient dodá.

## Chybové stavy
- **HTTP 500 / „Please reduce the amount of data"** → krájej okno na kratší bloky.
- **`code=2 / subcode=1504038`** („zkuste kratší období") → totéž, případně async insights job.
- **Nula katalogových reklam** → klient katalogovou reklamu neběží. Řekni to a **nenahrazuj to**
  pixelovými daty z bannerů — to je jiná otázka.
- **Prázdné `action_values`** → zkontroluj action_type (past č. 2), ne rovnou závěr „nulový obrat".
- **`act_` chybí nebo je jiný trh** → zeptej se, nehádej.

## Poznámky
- Obrat je přiřazen produktu, který byl v reklamě, ale objednávka může obsahovat i dokoupené
  položky. ROAS produktu = **„ROAS objednávek, které ten produkt nastartoval"**, ne marže na
  produktu. Piš to do reportu, ať si to nikdo nesplete.
- **Napojení:** hlavní workflow `ppc-fachman`. Rozhodování o katalogu řeší `meta-katalog`.

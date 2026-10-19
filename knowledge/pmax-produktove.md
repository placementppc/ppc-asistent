# PMax a produktové kampaně — metodika

Cíl: u PMax / Shopping maximalizovat hodnotu při cíli (ROAS/CPA), řídit produkty a signály.

## Co kontrolovat
- **Strategie a cíl**: tROAS / max hodnota / tCPA — sedí na cíl klienta? Úpravy konzervativně (viz `strategie-biddingu.md`).
- **Top vs. ostatní produkty**: rozdělení dle obratu/ROAS. Paretovo pravidlo (pár produktů dělá většinu obratu).
- **Listing groups / segmentace**: dělení podle kategorií, marže, ROAS, značek.
- **Kde se PMax zobrazuje**: viz „Tři úrovně rozpadu" níže — je to povinný krok, ne doplněk.

## Tři úrovně rozpadu PMaxu (jak se dostat do „černé skříňky")

Agregované číslo za PMax kampaň nemá skoro žádnou vypovídací hodnotu — relativní metriky (CVR, CPC,
ROAS/PNO) jsou úplně jinde na Searchi než na YouTube nebo Discoveru. Hodnoť **každou úroveň zvlášť
a v čase**, ne jako celek.

| Úroveň | Report | Co odpoví |
|---|---|---|
| **1. Kanály** | `fetch.py <cid> pmax_channels --days N` | Kam reálně tečou peníze a kde vznikají konverze |
| **2. Asset groups** | `fetch.py <cid> pmax_asset_groups --days N` | Které skupiny podkladů vůbec servírují (a které jsou mrtvé) |
| **3. Podklady** | `fetch.py <cid> pmax_assets --days N` | Jestli se konkrétní texty/obrázky/videa vůbec zobrazují |

### Čtení úrovně 1 — kanály

`segments.ad_network_type`: `2` SEARCH · `3` SEARCH_PARTNERS · `4` CONTENT (Display) · `7` MIXED ·
`8` YOUTUBE · `9` GOOGLE_TV · `10` GOOGLE_OWNED_CHANNELS · `11` GMAIL · `12` DISCOVER · `13` MAPS.

⚠️ **Shopping reklamy spadají pod SEARCH.** „98 % na Searchi" tedy neznamená textovou search —
je to search + shopping dohromady. Na jejich rozdělení je potřeba `shopping_performance_view`.

Co hledat: neúměrný podíl mimo nákupní záměr při slabých KPI, kanál s vysokým CPC a mizernou CVR,
skokový přesun mezi kanály (viz pojistka níže).

### Čtení úrovně 3 — podklady

⚠️ **Imprese se přičítají každému podkladu v zobrazené kombinaci** → nesčítají se na součet kampaně.
Report je použitelný na otázku „zobrazuje se to vůbec", **ne** na dělení nákladů mezi podklady.

Typický nález: desítky nahraných videí s jednotkami impresí. **Než se zadá výroba dalších kreativ,
zjisti, kdo za současný výkon reálně může** — hodně času se v PMaxu utopí v podkladech, které
se skoro neservírují. (Reálný případ: přes sto nahraných YouTube videí a za 30 dní dohromady
zhruba stovka impresí a jediný proklik.)

## 🔴 Povinná pojistka po každé změně rozpočtu nebo tROAS

**Druhý den po změně zkontroluj rozpad podle kanálů.** Když Shopping vypadne a naskočí
YouTube/Display, příčina **není v biddingu, ale ve feedu** — typicky vypadly produkty z labelu nebo
se rozbil feed, PMax ztratil produktový inventář a algoritmus okamžitě přelil rozpočet do levných
kanálů. Bez konverzí a klidně za dvojnásobek denního rozpočtu.

Postup: opravit label/feed → utáhnout zpět rozpočet a cíl → ověřit návrat Shoppingu. Řešitelné
během jednoho dne, když se na to přijde hned; jinak to týden hoří.

## ⚠️ PMax reaguje na změny v JINÝCH kampaních

Když PMax „bez jakékoli změny" najednou zdraží nebo začne servírovat ve vyhledávání, hledej příčinu
**mimo něj**: omezená (rozpočtem nebo přísným cílem) Search kampaň nevstupuje do všech aukcí a PMax
tam nastoupí místo ní — obvykle s výrazně horší konverzností, protože bere i dotazy, na které
Search kampaň mířila přesně.

Nejčastější spouštěče: pauza nebo utažení brandové Search kampaně, zvýšení tROAS u exact-match
kampaně, vyčerpaný rozpočet. **Před diagnózou „PMax se zbláznil" se vždy podívej, co se dělo
s ostatními kampaněmi v účtu.** (Doloženo z praxe: po pauze brandové Search kampaně začaly
brandové dotazy téct do PMaxu.)

## Typické optimalizace (návrhy ke schválení)
- **Rozdělit TOP produkty od ostatních**: samostatná PMax/Shopping kampaň na top produkty s vlastním tROAS,
  zbytek do druhé kampaně. Lepší kontrola rozpočtu a cílů.
- **Kampaň na „zombie" produkty**: produkty bez zobrazení/prodejů — samostatná kampaň s agresivnějším cílem,
  oprava feedu (titulky, obrázky, kategorie), nižší ROAS cíl ať dostanou šanci.
- **Segmentace dle marže/ROAS**: vyšší tROAS na nízkomaržové, nižší na vysokomaržové (ať se prodávají).
- **Signály publika (audience signals)**: přidat kvalitní signály (zákazníci, návštěvníci, custom intent) — urychlí učení.
- **Podklady (assets)**: doplnit kvalitní texty/obrázky/videa do asset group → lepší dosah a kvalita.
- **Vyloučení**: značkové výrazy (brand exclusions), nevhodné URL, account-level negativa.
- **Feed jako páka**: titulky, GTIN, kategorie, custom labels (top/sezóna/marže) pro segmentaci — viz `zbozi-cz.md` analogie.

## Konzervativně
- PMax má omezenou viditelnost a delší učení — neměň cíl/strukturu zbrkle, dej učení 2–4 týdny.
- Custom labels ve feedu jsou nejčistší cesta k segmentaci top/zombie produktů.
- Vždy zapiš baseline (ROAS, hodnota, útrata, rozpad kanálů) před změnou.

## Feed-only PMax (prázdná asset group) = legitimní strategie
Záměrně prázdná asset group (0 assetů) omezí PMax jen na produktové inzeráty z feedu —
chová se jako Standard Shopping s PMax biddingem, bez expanze do display/video/search textů.
Hodí se, když chce správce čistě produktový výkon bez „ředění" do dalších kanálů.
**Neflagovat automaticky jako chybu:** jednou se zeptej, jestli je to záměr, odpověď zapiš
do `clients/<klient>.md` a dál to nenavrhuj. (Google může časem vynucovat assety — pak řešit,
až to reálně nastane, ne preventivně.)

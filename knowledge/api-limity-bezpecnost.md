# API limity & bezpečnost účtu (Google Ads + Sklik)

> **Proč to tu je:** abychom si nezablokovali ani neztratili klientský účet kvůli
> neopatrnému používání API. Tahle stránka je **závazná** — platí pro každý běh skillu
> i pro skripty v `scripts/`.
>
> Konkrétní čísla se mění → u sporných případů ověř aktuální dokumentaci přes Context7 MCP
> nebo přímo: Google Ads `developers.google.com/google-ads/api/docs/best-practices`,
> Sklik `api.sklik.cz/drak/api.limits.html` (resp. metoda `api.limits` za běhu).

## Co účet REÁLNĚ ohrožuje (a co ne)

**Reálné riziko:**
- Překročení **denní kvóty operací** nebo **rate limitu** → dočasné chyby
  (`RESOURCE_TEMPORARILY_EXHAUSTED` u Google, HTTP `429` u Sklik). Není to ban, ale
  zastaví nám to práci a opakované hamrování vypadá podezřele.
- **Zápisy bez lidské kontroly** → špatná změna, přečerpaný rozpočet, reklama porušující
  policy. Tohle je největší riziko, ne čtení dat.
- **Reklamní texty** vygenerované AI → po publikaci je stejně **schvaluje Google**
  (automaticky i lidsky). API schvalování NEobchází. Closený text musí před publikací
  projít člověkem (viz [[reklamy-ab-testy]]).

**Spíš mýtus (pro náš případ):**
- Read-only stahování dat účet nezablokuje. Klikací fraud sítě se nás netýkají
  (negenerujeme prokliky). Bany plynou z porušení policy / billingu / podezřelé aktivity,
  ne z rozumného čtení dat. → Panika typu „API tě vypne za měsíc" je nadsázka,
  **ale limity a lidská kontrola zápisů jsou skutečné a dodržujeme je.**

## Google Ads API — limity

**Denní kvóta operací (podle úrovně developer tokenu):**
| Úroveň tokenu | Produkční účty | Testovací účty |
|---|---|---|
| Explorer | **2 880 operací / den** | 15 000 / den |
| Basic | **15 000 operací / den** | 15 000 / den |
| Standard | bez zveřejněného denního stropu (platí jen systémové/QPS limity) | — |

- **Co se počítá jako operace:** jedna mutate operace = 1. Jeden `Search` / `SearchStream`
  request = **1 operace bez ohledu na počet řádků** (proto čteme přes streamy, ne po řádcích).
- **Stránkování** dalších stránek přes page token kvótu **nečerpá**.
- **Mutate dávka:** max **10 000 operací na request** (my držíme menší dávky, viz níže).
- **Keyword Planning / plánovací služby:** limit **1 QPS** na customer ID.

**Rate limiting (QPS):**
- Dynamický (token-bucket podle aktuální zátěže serveru), počítaný **per (customer ID +
  developer token)**. Pevné číslo Google nezveřejňuje.
- Překročení → chyba `RESOURCE_TEMPORARILY_EXHAUSTED`.

**Jak se chováme (povinné):**
1. **Žádný paralelní souběh requestů** napříč klienty/reporty. Jedeme sériově.
2. **Dávkuj** mutate operace do jednoho requestu (partial failure on), neposílej zápisy
   po jednom v cyklu.
3. **Exponenciální backoff s retry** na `RESOURCE_TEMPORARILY_EXHAUSTED` (např. 5s, 10s,
   20s, 40s, max ~5 pokusů) — nikdy ne tvrdé opakování ve smyčce.
4. **Mezi voláními drž rozumný odstup** (ideálně ≤ pár QPS na účet). U plánovacích služeb
   max 1 request/s.
5. **Standard token** preferuj pro produkci; na Basic (15 000/den) hlídej, ať velké
   read sweepy + zápisy nepřekročí kvótu (jeden běh analýzy = jednotky až desítky operací,
   takže pohodlně stačí, ale ne nekonečné re-fetche).

## Sklik API — limity

- JSON-RPC. Skutečné limity vrací metoda **`api.limits`** za běhu — **na začátku práce
  s účtem si je přečti**, nepředpokládej čísla z hlavy.
- `api.limits` vrací mj.: `minuteRequestLimit`, `dayRequestLimit` (max requestů za
  minutu / den), `batchCallLimits` (max entit na dávkovou metodu), `statsDataLimit`
  (max dat v jednom stats requestu), min/max CPC/CPM, min/max denní rozpočet.
- Překročení → HTTP **`429 Too Many Requests`**.

**Jak se chováme (povinné):**
1. Před prací zavolej `api.limits` a respektuj `minuteRequestLimit` / `dayRequestLimit`.
2. Dávkové metody drž pod `batchCallLimits`. Stats požadavky pod `statsDataLimit`
   (jinak rozděl období / entity).
3. Na `429` → backoff a zpomal (počkej do další minuty), neopakuj hned.
4. Sklik mívá menší objemy → o to víc sérií, méně requestů, delší okna.

## Tvrdá pravidla pro ZÁPISY (write přes API)

1. **Nikdy zápis bez explicitního schválení uživatele** (viz tři neporušitelná pravidla skillu).
2. **Vždy nejdřív DRY-RUN.** `apply_changes.py` běží defaultně jako dry-run; reálný zápis
   jen s `--apply`. Stejný princip platí pro každý budoucí write skript.
3. **AI-generované reklamní texty člověk zkontroluje před publikací.** Nikdy nepublikuj
   dávku vygenerovaných RSA/textů přímo bez náhledu — Google je stejně schvaluje a špatný
   text = policy problém.
4. **Žádné hromadné zápisy „naráz".** Konzervativní senior styl: postupné kroky,
   malé dávky, jedna změna → baseline → vyhodnocení (viz [[vyhodnoceni-zmen]]).
5. **Rozpočet/CPC stropy** ber jako tvrdou pojistku — nikdy nenastavuj neomezené/extrémní
   hodnoty (riziko přečerpání).

Viz též [[google-ads]], [[sklik]] a `scripts/README.md`.

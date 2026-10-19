# ChatGPT Ads: postup optimalizace účtu

> Vzniklo z dat několika účtů (podzim 2026, řádově tisíce eur a tisíce kliků celkem).
> Je to **pozorování, ne statistika**: každý účet má jiný obor, rozpočet i nastavení.
> Při nových datech tenhle soubor aktualizuj, ne jen výsledky v klientském souboru.
>
> Navazuje na: skill `/chatgpt-ads` (CLI, bezpečnostní pravidla, playbook
> `.claude/skills/chatgpt-ads/chatgpt-ads-campaign-playbook.md`),
> `chatgpt-ads/docs/api-notes.md` (chování API a gotchas) a `docs/napojeni/chatgpt-ads.md` (napojení).

## Pravidla, která platí vždy

- **Nic neměň bez schválení.** Návrh → schválení → dry-run → `--confirm`. Viz CLAUDE.md, pravidlo 1.
- **NDA:** u klienta zkontroluj `NDA:` v `clients/<klient>.md`. Ven (report, LinkedIn, webinář) jen anonymně.
- **Nesuď z jednoho týdne.** Doručování se mezi sestavami přelévá po dnech. A/B test hodnoť po 3–4 týdnech
  a ≥ 100 klicích na sestavu. Poslední 2 dny jsou neúplné (útrata i GA4 se zpožďují).
- **Konverze platformy nejsou prodeje.** Ověřuj v GA4 přes `oppref` ve vstupní URL. U jednoho
  e-shopu hlásila platforma několikanásobně víc nákupů než GA4.
- **Vyšší CTR zlevní klik, ale neznamená prodej.** Při vysoké CTR na všech sestavách se cena poptávky
  mezi sestavami lišila od rozumné až po „žádná poptávka“. Rozhoduje konkrétní záměr a stránka, kam reklama vede.

## Krok 0: Načti účet

1. Najdi CLI účet (`--account`). Klíč účtu je v konfiguraci appky `chatgpt-ads/` jako
   `OPENAI_ADS_API_KEY_<NAME>` (návod `docs/napojeni/chatgpt-ads.md`); hodnotu nikdy nevypisuj.
2. Přečti `clients/<klient>.md`: cíl (CPA / PNO / ROAS), NDA, changelog, co už se zkoušelo.
3. Data za **celou historii účtu po týdnech**: `insights --aggregation-level ad_group --granularity daily --all`
   a `conversion-insights --level ad_group --ids …`.

## Krok 1: Kontrola měření (než začneš optimalizovat)

Bez měření optimalizuješ jen kliky. Postupně:

| Kontrola | Jak | Co se nám už stalo |
|---|---|---|
| Pixel a událost připojená ke kampani | `conversion-check --events` | Kampaň bez připojené události hlásí jen kliky. |
| Pixel patří správnému účtu | `pid` v requestu na `bzr.openai.com` vs. `pixels` | Web posílal na pixel jiného účtu, vypadalo to v pořádku. |
| Nákup se nepočítá víckrát | `event_id` = číslo objednávky v tagu | U jednoho e-shopu: 1 objednávka = několik nákupů v platformě. |
| UTM na každé sestavě | `adgroup-detail --json` → `landing_page_configuration.query_string_template` (u nové kampaně dry-run `plan-apply` vypíše `utm=…`) | Bez UTM padaly návštěvy do (direct). |
| Návštěvy z reklam v GA4 | vstupní stránka obsahuje `oppref` = `chatgpt / cpc` | Na web dorazilo jen ~40 % prokliků. |

Chybí pixel nebo tag? Nasaď ho (např. přes GTM) a ověř příkazem `conversion-check --events` — viz skill `/chatgpt-ads`, scénář Conversions.

## Krok 2: Diagnostika

Pro každou sestavu: zobrazení, kliky, CTR, cena kliku, konverze (platforma) a GA4, cena za konverzi.

- **Kliky ≠ prodej:** seřaď sestavy podle ceny za konverzi, ne podle CTR. Hledej sestavy s vysokou CTR a nulou
  konverzí (u nás obecná sestava jednoho e-shopu: vysoká CTR, stovky kliků, žádná poptávka).
- **Noc:** podíl útraty 0–6 h (`insights --granularity hourly`, hodinu ber ze `start_time`). Bez stropu u nás
  šla v noci zhruba třetina až polovina rozpočtu za zhruba dvojnásobnou cenu kliku.
- **Strop ceny:** `adgroup-detail` → `max_bid`. Automatická nabídka = riziko drahé noci.
- **Texty:** délky (doporučeno titulek ~16, text ~32 znaků), cena nebo sleva v textu, „od výrobce“.
- **Produkty (feed):** stav produktů API nevrací. Ads Manager → Kampaně → Produkty → zrušit filtr „Imprese > 0“.

## Krok 3: Páky v pořadí, jak je zkoušet

| # | Páka | Co nám vyšlo |
|---|---|---|
| 1 | **Nízký pevný strop ceny za klik** (u nás jednotky Kč) | Feed bez stropu měl klik řádově dražší než se stropem. Vysoký strop = drahý klik. S nízkým stropem skoro zmizela noční útrata. I mírné zvýšení stropu zdražilo klik o desítky procent. |
| 2 | **Krátké nákupní fráze** místo dlouhých vět | Krátké fráze s nákupním záměrem (hledám, kde koupit, doporuč) měly nejvyšší CTR na velkém objemu zobrazení. Krátké klíčovky vs. dlouhé situace se stejnými reklamami: vyšší CTR a víc zobrazení (na dvou účtech). Otázky vs. klíčovky: nerozhodnuto, přelévá se po týdnech. |
| 3 | **Titulek s výhodou nebo doporučením** | Doporučení konkrétního produktu > samotný název produktu > materiál. Titulek s konkrétní vlastností produktu výrazně porazil obecné „od výrobce“. |
| 4 | **Konkrétní výhoda v textu, ne cena** | Konkrétní výhoda (třeba služba zdarma navíc) porazila text s cenou; texty se slevou patřily k nejhorším. |
| 5 | **Vypnout slabé reklamy** po ~100 klicích | Slabá reklama měla i několikanásobně dražší klik. |
| 6 | **Jedna sestava = jeden konkrétní záměr** | Obecná témata měla CTR pod 1 % a drahý klik. |

**Omezení, na která narazíš (ověřeno na API, podzim 2026):**
- Strop ceny kliku jde jen u kampaně placené za kliky. U kampaně optimalizované na konverze (`bidding_type: conversions`)
  je `max_bid` cena za konverzi a typ biddingu nejde změnit → potřebuješ druhou kampaň.
- Minimální denní rozpočet kampaně je 15 (v měně účtu, u nás €). Typ rozpočtu (denní / celkový) po založení nejde
  změnit. Test v druhé kampani proto přidá útratu, dokud jinou kampaň nevypneš.
- V některých kategoriích dostávají nové reklamy `policy_country_targeting_blocked` i se schváleným textem.
  Tam se páky 3–4 nedají otestovat, dokud to nevyřeší podpora.

Co **nefungovalo nebo není ověřené:** poradenské dotazy (návody „jak na to“) mají levný klik, ale skoro žádná zobrazení;
u zablokované kategorie úprava textů ve feedu schválení nepomohla (řeší podpora); B2B cílení
(rozhodovatelé jsou často na placených plánech ChatGPT, kde reklamy nejsou).

Cena kliku po třech týdnech ladění u několika e-shopů klesla zhruba na čtvrtinu až pětinu. Páky jsme ale měnili
najednou, takže nevíme, kolik udělala která.

### Doplněno z účtu se službami a vzděláváním

- **Páka 1 platí i tady:** nižší strop ceny za klik zhruba zpolovičil cenu kliku; sestavy s vysokým stropem zůstaly drahé.
- **Páka 2 nemusí platit u služeb a vzdělávání:** otázky dostaly několikanásobně víc zobrazení než krátké fráze
  (u e-shopů obráceně). Rozdíl v CTR byl neprůkazný → „nerozhodnuto“ platí dál.
- **Páka 4 platí silně:** texty s cenou nebo slevou skončily pod průměrem účtu, nejlepší text cenu neobsahoval.
- **Vzorec vítězného textu:** konkrétní problém, který reklama odstraní, v titulku + konkrétní nástroje nebo postup
  v textu. Obecný benefit bez konkrét vyšel nejhůř.
- **Samotné „doporučujeme“ nestačí:** musí následovat konkrétní předmět doporučení, jinak je to vata.
- **Nejlepší filtr na text:** *odpovídá reklama na otázku, kterou člověk právě píše do ChatGPT?* Obecná slova
  bez předmětu samy o sobě neslibují nic konkrétního.
- **Datum v textu je past:** termínové tvrzení drží CTR jen do termínu, pak reklama lže. Při prodlužování kampaně
  vždy nejdřív projdi texty na termínová tvrzení.
- **Gotcha:** `campaign-update --end` vrátí v inline ověření ještě starý `end_time`. Ověřuj `campaign-detail`, ne odpovědí zápisu.

## Krok 4: Testy

- **Jedna proměnná.** Stejné reklamy, jiné fráze (nebo naopak). Každá sestava vlastní `utm_content`.
- **Kontrolní sestava** s krátkými klíčovkami vždy běží dál.
- **Hodnotit** po 3–4 týdnech a ≥ 100 klicích na sestavu. Do changelogu klienta zapiš datum změny a baseline.

## Krok 5: Produktové kampaně

1. Pevný strop i tady, po kategoriích (`--product-filter`), ne celý katalog bez stropu.
2. Produkty neprošly schválením? Ruční testovací feed: vybrané produkty s čistým popisem (bez HTML a bez
   tvrzení, která reklamní pravidla omezují), nahrát jako samostatný feed a porovnat stav v záložce Produkty.
   Oddělí to „vadí texty“ od „vadí kategorie“. U jednoho e-shopu to byla kategorie.
3. Porovnej s textovými kampaněmi ve stejném účtu a dnech. U nás měly produktové zatím nižší CTR a stejný nebo
   dražší klik. Po spuštění produktové kampaně textové dostaly méně zobrazení (příčina nejasná).

## Krok 6: Výstup

- Report stručně: **nahoře rozhodnutí ano/ne**, pak 1–2 věty, detaily do `clients/<klient>.md`.
- Ke každé diagnóze i **růstová páka**, ne jen vypínání.
- Každý návrh: co, proč (čísla), očekávaný efekt, jak vrátit, kdy vyhodnotit.
- Po schválení a provedení: changelog v `clients/<klient>.md` se stavem 🟡 a datem vyhodnocení.

## Zadání pro Claude (zkopíruj)

```text
Načti knowledge/chatgpt-ads-optimalizace.md a skill /chatgpt-ads. Projdi ChatGPT Ads účet <klient>
(CLI --account <name>) podle kroků 0–6: nejdřív měření, pak diagnostika po sestavách za celou historii
po týdnech, pak návrhy podle pořadí pák. Konverze ověř v GA4 přes oppref. Nic neměň, jen navrhni.
Nahoře mi napiš rozhodnutí ano/ne, detaily dej do clients/<klient>.md.
```

# Sklik (Seznam.cz) — referenční přehled

> Sklik API je JSON-RPC. Ověř aktuální metody/limity v oficiální dokumentaci api.sklik.cz
> (a v `scripts/sklik/`). Funkce a strategie se mění.

## 🔴 Než začneš volat API — tohle už víme, neobjevuj to znovu (ověřeno 22. 9. 2026)

1. **Sklik v Context7 NENÍ.** Globální pravidlo „nejdřív dokumentace přes Context7" tady
   nejde splnit. Dokumentace je na **api.sklik.cz** a **napoveda.sklik.cz** (Práce s API Drak).
   Nehledej Sklik v Context7, ušetříš dvě volání a minutu.
2. **Jednotky se míchají.** V reportech je `clickMoney` / `totalMoney` v **haléřích**,
   ale `conversionValue` v **korunách**. Kdo to nepřepočítá, má PNO stokrát vedle.
3. **Rozpad podle zařízení u produktových kampaní (Seznam Nákupy) funguje** —
   `campaigns.createReport` s `restrictionFilter.deviceType`
   (`devicePhone` / `deviceDesktop` / `deviceTablet` / `deviceOther`). `deviceOther` bývá nula.
4. **Výkon po jednotlivých produktech Sklik nedává.** Statistiky jsou jen po produktových
   skupinách. Produktový a cenový rozpad ber z **GA4** (vstupní stránka × zařízení,
   filtr na kampaň Nákupů) a vždy napiš, že náklad na produkt je odhad.
5. **Filtr na konkrétní produkt (`item_id`) v produktové skupině API odmítá** (406).
   Nejhorší produkty se musí označit vlastním štítkem ve feedu a dát do vlastní skupiny.
6. **Seznam kampaní vrací 400 na špatné parametry**, ne prázdný výsledek. Když přijde 400,
   je chyba v tělu požadavku, ne v přístupech — podívej se do `scripts/sklik/fetch.py`,
   jak se volání skládají, a teprve pak do dokumentace.

## ⚠️ Limity API & bezpečnost účtu
Před prací s účtem zavolej metodu **`api.limits`** a respektuj `minuteRequestLimit`,
`dayRequestLimit`, `batchCallLimits`, `statsDataLimit`. Překročení → HTTP `429` → backoff.
Detail a tvrdá pravidla pro zápisy viz `api-limity-bezpecnost.md`.

## Základ
- **API**: JSON-RPC endpoint (`https://api.sklik.cz/drak/json/...`). Autentizace API tokenem,
  session přes `client.login` → vrací session, kterou posíláš v dalších voláních.
- **Agenturní přístup**: lze pracovat pod více účty (foreign account) — v requestu se předává
  identifikace cílového účtu (userId). Konkrétní klienti se zadávají per běh.

## Typy kampaní
- **Vyhledávací** (search) — textové reklamy ve výsledcích Seznamu.
- **Obsahová síť** (kontextová/display).
- **Produktové / Zboží.cz** — produktová inzerce řízená feedem. Viz `zbozi-cz.md`.
- **Kombinované / retargeting / video** dle aktuální nabídky.

## Bidding
Ruční CPC, automatické strategie (např. maximalizace prokliků/konverzí, cílový podíl, cílové PNO dle dostupnosti).
Konzervativní úpravy příhozů (±15–30 %), pozor na menší objemy → delší okna pro vyhodnocení.

## Metrika efektivity: PNO (ne ROAS)
Sklik používá **PNO** (podíl nákladů na obratu, v %) = náklady/obrat × 100. Chce se **dolů**,
je to převrácená hodnota ROASu (ROAS 400 % ≈ PNO 25 %). ROAS si nech pro Google Ads.

## Klíčové oblasti optimalizace (analogicky ke Google Ads)
- Rozpočty a pacing, příhozy/strategie, vyhledávací dotazy a negativa, reklamy, produktové kampaně.
- Specifika: kvalita feedu a párování na Zboží.cz, hodnocení nabídky, dostupnost, recenze.

## Pozn. k objemům
Sklik bývá menší objem než Google → větší důraz na statistickou významnost a opatrnost při závěrech.

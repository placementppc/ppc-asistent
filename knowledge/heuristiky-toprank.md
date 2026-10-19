# Heuristiky převzaté z toprank/AdsAgent (Google Ads skilly, MIT)

Zdroj: github.com/nowork-studio/toprank, adresář `google-ads/` (37 souborů), přečteno 14. 9. 2026.
Je to open-source sada instrukcí pro správu Google Ads přes Claude. Samotné napojení na účet
jde přes jejich hostovaný MCP server (cizí firma drží OAuth do účtu) — **to nepoužíváme**, viz
`api-limity-bezpecnost.md`. Tenhle soubor sbírá jen **metodiku**, která u nás chyběla nebo je
přesnější než naše dosavadní formulace. Kde máme vlastní pravidlo, odkazuje se na něj.

Pozor na zdroj čísel: jejich markdown reference univerzální prahy výslovně odmítají („no magic
sample threshold"), zatímco starší `policy-registry.json` a RSA best-practices je obsahují jako
„industry defaults". Čísla níž ber jako **výchozí hodnoty k ověření na účtu**, ne jako fakta.
Benchmarky CPA/CTR po oborech jsou US a pro CZ k ničemu, ty tu nejsou.

---

## 1. Podíl zobrazení: matice 2×2 a šest blokerů

Než navrhneš rozpočet, rozděl ztracený IS na **budget** a **rank**. Kombinované číslo nestačí.

| | Rank-lost IS NÍZKÝ | Rank-lost IS VYSOKÝ |
|---|---|---|
| **Budget-lost IS NÍZKÝ** | Zdravé — optimalizuj na okrajích | **Problém relevance** — QS / reklamy / LP. **Nepřidávat rozpočet** |
| **Budget-lost IS VYSOKÝ** | Problém kapitálu — přidat rozpočet, je-li ziskové; jinak zúžit geo / čas | Strukturální problém — špatná KW nebo publikum; přestavět |

Šest blokerů dodání (pojmenuj ten pravý, než něco měníš):
1. **Budget-constrained** — spend naráží na rozpočet + budget-lost IS materiální.
2. **Rank-constrained** — spend pod rozpočtem + rank-lost IS materiální → relevance / QS / LP / bid, ne rozpočet.
3. **Demand-constrained** — málo impresí a nízký lost IS obojího druhu → ověřit targeting, schválení, schedule, měření.
4. **Quality-constrained** — rank loss + slabé QS / LPX.
5. **Query-quality constrained** — budget-limited, ale marginální dotazy / search partners jsou odpad → „víc rozpočtu škáluje odpad".
6. **Tracking-constrained** — měření nespolehlivé → STOP, nejdřív oprava.

Pravidla: budget-lost IS ≈ 0 → navýšení nepomůže. **PMax vedle Search zkresluje Search IS** —
zkontroluj překryv, než řekneš „chybí poptávka". Rank-lost IS > 30 % → nejdřív relevance.
IS metriky jsou v GAQL jen 90 dní zpět. Navazuje na `rozpocty.md`.

## 2. Klasifikace klíčových slov do tierů (než cokoli pauzuješ)

| Tier | Definice | Důsledek |
|---|---|---|
| **1 Core** | KW přímo popisuje, co klient prodává | **Nikdy nepauzovat z krátkého okna.** Hledat příčinu |
| **2 Adjacent** | související, ne hlavní služba | hodnotit až po kontrole dostatečnosti dat |
| **3 Irrelevant** | jiný záměr / jiná služba | negativa bez okolků |

Signály bez byznys kontextu: název kampaně, sestavy, nadpis reklamy, URL LP —
**2+ shody = Tier 1, 1 = Tier 2, 0 = Tier 3.** Tier 1 podvýkon není „waste".
Diagnóza Tier 1: měření a zralost → hodnota pro byznys → srovnání se sourozenci a dotazy →
match type / hygiena dotazů → shoda reklama–LP → QS komponenta + IS. Ani core KW nechraň
věčně, když je zralé a prokazatelně neekonomické. Doplňuje pravidlo 4b (nesuď z krátkého okna).

## 3. Signály rozbitého měření (kontrola před každou analýzou)

- **CVR > 50 %** → konverzní tag pálí při načtení stránky.
- **0 konverzí za 30 dní při spendu > 5× účtového CPA** → tracking je rozbitý, ne kampaň.
- Všechny akce „Website" bez názvů → default tracking, nikdo to nenastavil.
- **Display síť zapnutá uvnitř Search kampaně** → strukturální únik, počítej jako waste.
- Počítání: **lead-gen ONE per click, e-shop EVERY** (MANY_PER_CLICK). Naopak = špatná data.
- Smart Bidding pod ~15 konv./měs. = hladoví (jejich orientační floor: 30+ tCPA, 50+ tROAS,
  shodné s `strategie-biddingu.md`).
- EU traffic bez Consent Mode v2, vypnuté enhanced conversions.
- **Cliff na nulu v konverzích = změna tagu / webu / formuláře**, ne trh.
- Když je měření materiálně rozbité: **zastav spend do opravy**, nic jiného nehodnoť.

## 4. Tři „pulzní" metriky místo skóre účtu

Audit nedává známku, ale tři čísla, která jdou po opravě přeměřit:
1. **Waste** — Kč/měs (extrapolace na 30 dní), % spendu, největší přispěvatel.
   Waste = KW waste (Tier 2/3, 0 konv., kliky nad prahem) + search-term waste (irelevantní
   záměr) + strukturální waste (Display v Search). Deduplikovat.
2. **Zachycená poptávka** — spend-vážený průměr search IS přes kampaně s ≥ 1 konverzí
   (s unit economics jen kampaně s CPA ≤ break-even).
3. **CPA / PNO** vs cíl klienta + největší strukturální příčina.
Brand a non-brand **vždy zvlášť** („účet má CPA X, ale brand Y a non-brand Z"). Nerozdělené = nález.
Re-audit = diff tří čísel („Waste 12 400 Kč/měs, bylo 31 000 — 3 opravy").

**Quick wins:** dopad ≥ [práh v Kč, u nás navrhuji 5 000 Kč/měs] **a** oprava < 15 min,
plus každá oprava měření / policy bez ohledu na částku. Max 5, seřadit podle Kč, měření nahoře.

## 5. Rozhodnutí zapsané před změnou (doplněk k learning loopu)

Ke každé změně v changelogu navíc:
- **hypotéza** (1 věta), **hlavní metrika s jmenovatelem** (ne „konverze", ale „CPA na
  primární akci X v kampani Y"), **guardrail metrika** s číselným stopem,
- **výsledkové stavy definované předem:** keep / hold / rollback s prahy.
- „Bez předem daného prahu žádný rollback verdikt" — když práh nebyl, výsledek je
  *inconclusive* a práh se doplní pro příště. Nikdy ho nevymýšlet až po vidění výsledku.
- Kontrolní body 3 / 7 / 14 dní jsou **monitoring**, ne důkaz. Zralost určuje konverzní cyklus.
- **Falsifikace:** u doporučení uveď, jaká data by ho vyvrátila. Vzor: „0 konverzí ze 47 kliků
  za 30 dní při účtovém CVR 4,2 % — očekáváno ~2, pozorováno 0." `kliky × baseline CVR` je
  diagnostika, ne test významnosti.
- Nulový jmenovatel: rate je „nedefinováno", cost-per-outcome „neomezené". Nikdy nedosazuj nulu.
Rozšiřuje `vyhodnoceni-zmen.md` a šablonu changelogu.

## 6. Denní operátorský report — formát

Pořadí **Vyhodnoceno → Změněno → Viděno (1–3 pozorování) → Návrh**. „Zatím žádný návrh" je
platný výstup. Každou položku klasifikuj: **no action / watch / recommend / needs approval**.
Pravidla:
- čistý traffic bez konverzí → nejdřív LP / formulář / tracking, ne bidy,
- rank-limited a hluboko pod rozpočtem → **nedoporučovat rozpočet**,
- budget-limited s dobrým CPA → nejdřív ověřit kvalitu marginálních dotazů a search partners,
- 1–3 kliky → watch podmínka, ne mutace (ledaže je záměr zjevně špatný),
- Maximize Clicks účty: levný traffic = objevování, ne úspěch.
Pacing: MTD spend, projekce konce měsíce, denní rozpočet vs včera vs 7d průměr; spike
porovnávej s rozdělením posledních kompletních dnů, ne s pevným %.

## 7. Vyhledávací dotazy — buckety a bezpečnostní pravidla

n-gram pipeline máme v `.claude/skills/perf_srch/SKILL.md`. Co doplnit:
- Výstup roztřiď do **šesti bucketů**: negativ / kandidát na KW / routing (stejný n-gram ve
  více sestavách s jiným CPA či CVR) / nesoulad reklama–LP / **watch** (věrohodný záměr, málo
  dat) / **winner** (zaslouží rozpočet, až prokáže ekonomiku). Watch a winner se běžně zapomínají.
- Drahé n-gramy bez konverzí jsou **spouštěč kontroly, ne automatický negativ**.
- Brand a core term nikdy nevylučovat bez potvrzení; před negativem zkontrolovat konflikt
  s aktivními pozitivy; exact/phrase negativ na úzký únik, broad negativ jen pro jednoznačně
  špatné pojmy; shared list = celoúčtové diskvalifikátory, kampaň/sestava = routing.
- Search-term report neukazuje všechny dotazy → uváděj pokrytí.
- Slova „zdarma", „kurz", „práce" nejsou univerzálně irelevantní — záleží na oboru.
Doplňuje `vyhledavaci-dotazy.md`.

## 8. Diagnostika propadů

- **Ztráta pozice má čtyři páky:** QS / relevance / LP; bid nebo cíl včetně zapomenutých bid
  adjustmentů po změně strategie; rozšíření cílení nebo match typu (mění mix aukcí); pokrytí assety.
- **QS trend:** *útes* = rozbité stránky, zamítnutí, tracking, nabídka; *pomalý pokles* = drift
  relevance nebo konkurence.
- **Propad konverzí = traffic × CVR**, pět os: objem trafficu / kvalita trafficu (dotazy, síť,
  match, geo, zařízení) / CVR (LP, tracking, formulář, nabídka, rychlost) / bidding (strategie,
  cíle, učení, stropy) / měření (akce, primary flag, tag, offline import). Vždy přes to přelož
  `change_event`.
- **Search partners:** srovnat Google Search vs Partners na cílové metrice; vypnout jen při
  materiálním objemu a horším výsledku. Nižší CTR partnerů může být ziskový.
- **Geo:** „X % mimo cílovou oblast" samo o sobě není waste — rozliš lokalitu uživatele vs
  lokalitu zájmu a nastavení advanced location.

## 9. RSA — pinování, A/B minima, čtení výsledků

Výchozí hodnoty k ověření (industry, ne Google):
- **Pinování:** kampaň s 50+ konv./měs → nepinovat; méně → zvážit pin 2–3 nejlepších H na
  pozice 1–2. Nikdy víc než 2 H na stejnou pozici; pinuješ-li pozici 1, dej tam 3+ H; celkem
  max 3 piny. Legal / brand / povinná cena → pin 1 (případně 2). Popisky pinovat méně než nadpisy.
- **Ad Strength ignoruj** u brand, single-product a pod 50 konv./měs; ber vážně u širokého
  mixu záměrů, nových kampaní a velkých spendů.
- **Metrika testu:** CVR > CTR > CPA > Ad Strength. E-shop: hodnota konverzí na impresi.
- **A/B minima:** 200 kliků/variantu (ideál 500+), 14 dní (ideál 30), 50 konverzí/variantu
  (ideál 100+). Minimum-read: < 100 kliků = brzy; ≥ 20 % relativní delta = směrový signál;
  2× CVR gap = silný, stále zkontroluj počet konverzí. Naše `reklamy-ab-testy.md` má 100
  kliků/variantu — to je spodní hranice pro „vůbec se dívat", ne pro verdikt.
- **Čtení:** CTR↑ CVR↑ nasadit; CTR↑ CVR flat nasadit, je-li CPA OK; **CTR↑ CVR↓ = špatné
  kliky → vrátit**; CTR↓ CVR↑ nechat, roste-li celkový počet konverzí; flat/flat → odvážnější varianta.
- **Co testovat (očekávaný dopad na CTR, min. délka):** benefit vs feature v nadpisu 15–30 % /
  14 d; CTA sloveso 10–20 % / 14 d; cena v textu vs bez 10–25 % / 14 d; urgence 5–15 % / 21 d;
  otázka vs tvrzení 5–15 % / 21 d; CTA v popisku 5–10 % / 21 d; display path 3–8 % / 14 d.
- Diverzita: min 8 unikátních H (11–15), 3+ úhly, 2 CTA, 2 H s čísly, mix délek.
  Popisek bez CTA má prý o 10–15 % nižší CTR. Před psaním RSA vytáhni dotazy sestavy a rozděl
  je na záměry; při materiálně různých záměrech **nejdřív split sestavy**, pak test.

## 10. Landing page — rubrika

Váhy: 25 % shoda sdělení, 25 % rychlost, 20 % mobil, 15 % důvěra, 15 % formulář a CTA.
- **Shoda sdělení:** H1 obsahuje slib z reklamy doslova nebo těsné synonymum, sloveso CTA
  shodné s tlačítkem, nabídka nad ohybem, do 3 s bez scrollu. Homepage nebo kategorie = propad.
- **Rychlost (PSI mobil):** výborné LCP < 2,0 s / INP < 100 ms / CLS < 0,05; slušné 2,0–2,5 /
  100–200 / 0,05–0,10; slabé 2,5–4,0 / 200–500 / 0,10–0,25; špatné nad 4 s.
- **Mobil:** tap cíle > 48 px, text ≥ 16 px, sticky CTA / telefon, žádné popupy (na placeném
  trafficu odložit na 30 s nebo scroll, jinak pryč).
- **Důvěra:** recenze se jmény, roky, adresa, telefon, reálné fotky; **copyright starší než
  loňský rok** a překlepy = propad.
- **Formulář:** CTA nad ohybem, akční text („Chci nezávaznou nabídku", ne „Odeslat"),
  **3–4 pole pro lead gen**, 5–6 OK, 9+ špatně, login = propad. Každé odebrané pole ≈ +10 % konverzí.
- Kalibrace: LP s LCP 3,5 s a shodou sdělení 95 konvertuje líp než LCP 1,5 s se shodou 60.
  Pořadí oprav: rozbitá shoda → chybějící důkaz → tření formuláře → mobil/rychlost → nejasná nabídka.
  Nepřestavovat celou stránku, když stačí změna nad ohybem.

## 11. Matematika pro leadgen s CRM daty (`ppc-math`)

Když jsou konverze ověřené až v CRM, drž „ledger" s pokrytím a mezemi:
- Pokrytí: extract / eligible; join coverage; duplicate rate; unresolved rate.
- **Meze:** worst case = potvrzené; best case = potvrzené + nerozhodnuté. CPA z obou. Rozhoduj,
  jen když obě meze leží na stejné straně cíle.
- **Zralost:** projected = observed / completion fraction (jen se zadaným CF).
- **Rozklad ceny vs míry:** `CPA při současném CPC a dřívějším CVR` vs `CPA při dřívějším CPC
  a současném CVR` — říká, jestli zdražil klik, nebo spadla konverze. Counterfactual, ne důkaz.
- Inkrement: `Incremental CPA = ΔSpend / ΔOutcomes`; break-even ROAS = 1 / contribution margin.
- IS příležitost: `revenue × (1/IS − 1)` je **horní mez**, nikdy forecast.
- MER (celkový obrat / celkový marketing spend) nikdy nesrovnávat s ROAS kampaně.
- Klouzavý baseline účtu: `rolling30d = 0,7 × předchozí + 0,3 × posledních7d × (30/7)`.

## 12. Nápady na strukturu, ne obsah

- **Registr předpokladů s volatilitou a datem ověření** (`{pravidlo, volatilita, ověřeno,
  zdroj, stale_after_days}`), skill přeskočí prošlé. Hodilo by se pro Sklik gotchas
  (`tvorba-kampani/04`) a pro Google změny typu 17. 8. 2026.
- **Oborové šablony** (marže, AOV, cílové CPA/PNO, min. konverzí pro Smart Bidding, očekávaný
  podíl brandu, PMax ano/ne, doporučené konverzní akce, sezóna, red flags, startovní negativa).
  Jejich hodnoty jsou US, ale struktura je dobrý model pro naše CZ šablony: e-shop, leadgen
  služby.
- **Persona z dotazů:** persona musí mít 5+ reálných vyhledávacích dotazů, jinak ji škrtni;
  pojmenovat podle chování („Srovnávač"), ne demografie.
- **Safe executor:** před zápisem zkontrolovat aktivní experimenty (zapsat do obou ramen, nebo
  vyžádat potvrzení); po zápisu **ověřit čerstvým čtením** entity; když ověření selže, hlásit
  „neověřeno", ne „hotovo". Bulk operace: nezamlčovat částečná selhání.
- **Klientský report:** Stav / Snapshot / Co jsme se naučili / Změny (jen ověřené) / Doporučuji
  s Proč–Riziko–Schválení / Sleduji / Potřebuji od vás. Formulace „nedoporučuji zvýšit rozpočet,
  protože omezením je rank, ne kapitál".

## Co z toho NEbrat

- Číselné benchmarky CPA a CTR po oborech (US). Multiplikátory QS → CPC („QS 10 = −50 %").
- Univerzální migrační žebřík Max konverze → tCPA → tROAS (jejich vlastní novější reference ho odmítá).
- Hostovaný MCP s OAuth do klientských účtů.

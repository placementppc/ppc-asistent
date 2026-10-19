# Vyhledávací kampaně (SRCH) — tvorba

Primárně Sklik, principy platí i pro Google Ads.

## Struktura

```
Kampaň (typ: fulltext, denní rozpočet)
└── Sestava (default CPC)
    ├── Klíčová slova (phrase + exact)
    ├── Vylučující klíčová slova (negativePhrase) — hned od začátku
    └── Inzeráty (2–3 varianty, hlavní KW v nadpisu)
Sitelinky + popisky (callouts) — úroveň kampaně nebo účtu
```

### Organizace kampaní

- Dělení podle: téma/produkt, landing page, sezónnost (sezónní nabídky zvlášť — snadno zapnout/vypnout), geografie, případně typ shody
- Naming: `[projekt] - [téma] - [typ]`, konzistentně napříč účtem, bez ampersandu (&)
- Rozpočet: nová kampaň konzervativně, zvyšovat po validaci; u akčních/sezónních kampaní VŽDY nastavit `endDate`

### Sestavy

- **1 sestava = 1 téma** — KW tematicky příbuzná, inzeráty odpovídají KW
- 5–20 KW na sestavu; SKAG (jedno KW = sestava) se nedoporučuje — výjimkou TOP konvertující KW
- **Neduplikovat KW mezi sestavami** (kanibalizace) — překryvy řešit cross-vylučujícími slovy

## Klíčová slova

### Typy KW

| Typ | Charakteristika |
|---|---|
| **Brand — jednoznačný** | Vlastní unikátní značka: vysoké CTR, nízké CPC, minimální konkurence; občas cílí konkurent → sledovat |
| **Brand — vendor** | Značka prodávaná i na jiných e-shopech: vyšší konkurence v aukcích, dražší CPC, jiná strategie nabídek; sledovat, kdo inzeruje a za kolik |
| **Generická** | Široké výrazy — větší objem, nižší CR; vhodné na objem |
| **Longtail** | Specifické, vysoce konverzní; Google je kvůli malému objemu nemusí zobrazovat, Sklik zobrazí data i na 1 zobrazení |

### Proces výběru

1. Brainstorm — co zákazník hledá
2. Suggest nástroj platformy (rozšíření o návrhy + hledanost + odhad CPC)
3. Třídění do tematických sestav
4. **Vylučující slova rovnou při návrhu** — ze suggestu vždy vypadne balast (jiný materiál, DIY / „jak vyrobit", recenze, nesouvisející významy) → hned zařadit jako negativa

### Shody — strategie

- **Preferovaná strategie: phrase + exact** s co nejvíce variacemi (skloňování, synonyma, pořadí slov, jednotné/množné číslo)
- **⚠️ Sklik broad = Google broad (sémantické matchování)** — dokumentace tvrdí „musí obsahovat všechna slova", v praxi to NEPLATÍ; broad matchuje i sémanticky vzdálené dotazy
- Broad POUZE pro krátkodobý discovery s nízkým CPC a monitoringem dotazů; po 2–4 týdnech dobré dotazy převést na phrase/exact a broad pausnout
- Phrase = slova ve správném pořadí + další slova okolo = sweet spot
- Exact pro TOP konvertující KW
- **Diakritiku přidávat** — Sklik ji rozlišuje
- **Skloňované varianty pokrýt explicitně** (phrase skloňování nerozlišuje dostatečně)

### CPC — KRITICKÉ pravidlo

- **CPC NIKDY na úrovni klíčového slova** — cena za proklik se řídí JEN default CPC sestavy
- Při vytváření KW parametr `cpc` vynechat → KW dědí cenu ze sestavy a bidding se ladí na jednom místě
- Start: 60–80 % doporučeného CPC ze suggestu, po týdnu upravit dle pozice a CTR; cíl pozice 1–3, ne za každou cenu

## Vylučující slova

- **Preferovat `negativePhrase`** (fráze i jednotlivá slova); `negativeExact` pro jednotlivá přesná slova
- **`negativeBroad` je nebezpečné** — jedno slovo vyloučí JAKÝKOLI dotaz, který ho obsahuje; nevhodné vyloučení může kampaň úplně omezit
- Diakritika se rozlišuje → přidat varianty s diakritikou i bez ní (např. „zdarma", „zadarmo", „free", „gratis")
- Úrovně: sestava / kampaň / účet
- Typická negativa: cenová (zdarma, levně), zaměstnanecká (práce, plat, kariéra), informační (co je, jak funguje, wiki), bazarová (bazar, použité), konkurence
- **Průběžně**: kontrolovat vyhledávací dotazy → nerelevantní přidávat jako negativa, dobré jako nová KW

> **Vzorec ověřený v praxi:** u lokálních služeb (řemeslníci, autoservisy) tečou peníze na
> **jména konkurentů** a na **„profese + vzdálené město"**. Vylučování jmen prokazatelně funguje
> (CTR i podíl zobrazení nahoru, stejný počet prokliků levněji), ale je to **nekonečná hra** —
> nová jména naskakují průběžně. Řeš to i strukturálně, ne jen dopisováním negativ.

## Texty inzerátů (ETA)

### Limity znaků

| Prvek | Limit | Povinné |
|---|---|---|
| Headline 1 / 2 / 3 | 30 znaků každý | H1, H2 ano; H3 volitelný |
| Description 1 / 2 | 90 znaků každý | D1 ano; D2 volitelný |
| Path 1 / 2 | 15 znaků každá | Ne (path2 vyžaduje path1) |

### Struktura textu

1. **Headline 1** = hlavní klíčové slovo sestavy — ale přirozeně, ne mechanicky nasypané; text musí dávat smysl a lákat
2. **Headline 2** = benefit / USP (ruční výroba, skladem, doprava zdarma…)
3. **Headline 3** = brand / doplněk / CTA
4. **Description 1** = konkrétní rozvedení nabídky (detaily, cena, termín)
5. **Description 2** = sociální důkaz / doprava / urgence
6. Jazyk inzerátu = jazyk klíčových slov; inzerát relevantní k landing page

### Zakázané v textech

- **Telefonní čísla, e-maily a URL** — patří výhradně do rozšíření (call asset, sitelinky), ne do textu.
  Doplněno 28. 7. 2026 po reálném zamítnutí: sitelink „Zavolejte <číslo telefonu>" Google zamítl a podklad
  se přestal zobrazovat. **Zamítnutý podklad stahuje výkon celé kampaně potichu** — řeš to opravou
  textu, ne odvoláním.
- Vykřičník v nadpisech (v popisu max 1), CELÁ VELKÁ SLOVA (výjimka běžné zkratky: AI, SEO, CRM), emoji
- Opakovaná interpunkce (!!!, ???, …)
- Superlativy bez doložení („nejlepší", „nejlevnější")
- Výzvy „klikněte zde" apod.
- Ampersand (&) v názvech kampaní a sestav

> Tenhle checklist je zapojený i jako **automatická kontrola ve write skriptech**
> (`scripts/lib/policy.py::check_ad_texts` — používá `create_rsa.py` a `create_search_campaign.py`).
> Skript se při nálezu zastaví ještě před zápisem do účtu.

### Počet variant a testování

- **2–3 inzeráty na sestavu** (min 2, ideál 3) — platforma rotuje a upřednostní lepší
- A/B test: měnit vždy jen 1 element, min ~100 kliků na variantu před vyhodnocením
- Po 2–4 týdnech pausnout nejhorší, přidat novou variantu

## ⚠️ Google Ads ≠ Sklik: RSA vs. ETA

> Doplněno 28. 7. 2026. Struktura výše popisuje **ETA** (rozšířený textový inzerát). Ve Skliku je to
> pořád aktuální formát (`adType: eta`). **V Google Ads už ETA vytvořit nejde** — od června 2022 se
> ve vyhledávání zakládají jen **RSA** (responzivní reklamy ve vyhledávání). Principy psaní platí,
> ale struktura a práce s nimi je jiná.

### RSA — jak se liší

| | ETA (Sklik) | RSA (Google Ads) |
|---|---|---|
| Nadpisy | 3 pevné, 30 znaků | **až 15**, 30 znaků, systém skládá 3 |
| Popisy | 2 pevné, 90 znaků | **až 4**, 90 znaků, systém skládá 2 |
| Pořadí | pevné | systém testuje kombinace |
| Kvalita | jednodušší skóre | **Ad Strength** + hodnocení jednotlivých podkladů |

### Pravidla pro RSA

- **Dodat opravdu 15 nadpisů a 4 popisy.** Nejčastější chyba v účtech: RSA se 3 nadpisy a 2 popisy —
  formát pak nemá co testovat a chová se hůř než pořádná ETA.
- **Rozmanitost, ne variace téhož.** Pokryj: hlavní KW sestavy, benefity/USP, CTA, cena/akce, brand,
  lokalita. Použij 6 úhlů sdělení jako checklist (viz `03`).
- **Nepřipínat všechno.** Pin jen tam, kde to má důvod (brand nebo právně povinná informace do pozice 1);
  jinak nech systém testovat — nadměrné pinování zabíjí smysl formátu.
- **Nemíchat množné a jednotné číslo o klientovi** — u sólo živnostníka („poskytujeme" vs. „poskytuji")
  působí AI-šablonově. Sjednotit napříč celou sadou.
- **Hodnocení podkladů (Best/Good/Low)** používej, ale u malých účtů čekej `NOT_APPLICABLE` — málo dat
  na asset. Pak posuzuj kvalitativně, ne podle štítku.
- Doplň **sitelinky, popisky a strukturované úryvky** — u RSA táhnou CTR ještě víc než u ETA.

### Landing page

- URL musí vracet HTTP 200 (reklama s 404 se zamítá / nezobrazuje)
- Obsah stránky musí odpovídat inzerátu, žádné přesměrování na jinou doménu, HTTPS

### Regulované produkty (léky, doplňky stravy)

- Povinné označení „Lék" / „Doplněk stravy" v textu, odkaz na příbalový leták, žádné superlativy o účinnosti

## Rozšíření — přidávat VŽDY

### Sitelinky (odkazy)

- Text max **25 znaků**, každý odkaz = jiná podstránka/kategorie
- Přidat **4–6**, zobrazí se 2–6; zvyšují CTR o 10–20 %
- Úroveň: účet (doporučeno) / kampaň / sestava — hierarchicky se doplňují

### Popisky (callouts)

- Max **25 znaků**, krátké benefity (Skladem, Doprava po celé ČR, Ruční výroba…)
- Ve Skliku se přidávají ručně v UI — DRAK API je nevystavuje

---
name: reklama-vs-stranka
description: >
  Senior kontrola souladu reklamy a vstupní stránky (message match) pro Google Ads, Sklik,
  Meta i ChatGPT Ads: jestli stránka plní slib z reklamy (nadpis, nabídka, cena, CTA), jestli
  reklama neposílá na homepage nebo kategorii, a kde se ztrácí konverze mezi proklikem
  a objednávkou. Použij, když uživatel řekne „proč to nekonvertuje", „drahý proklik a nic",
  „zkontroluj landing page", „kam ta reklama vede", „soulad reklamy a webu", nebo před
  spuštěním nové kampaně a u každé reklamy v ChatGPT Ads.
---

# Reklama vs. vstupní stránka

Kampaň s dobrým CTR a špatným konverzním poměrem má problém až za proklikem. Senior
**čte reklamu a stránku vedle sebe** a hledá, kde se slib láme. Nepřestavuje web, hledá
nejmenší změnu s největším efektem.

## 1. Co stáhnout

- Reklamy s největší útratou za 8 týdnů: titulky, popisy, finální URL, CTR, CVR, CPA
  (`scripts/google_ads/fetch.py <účet> ads`, Sklik `fetch.py`, Meta `scripts/meta/fetch.py`).
- Pro každou URL text stránky **přímo z HTML** (ne přes shrnutí, pomocný model přebírá
  i zbytky šablony), stavový kód, přesměrování.
- PageSpeed Insights mobil (LCP, INP, CLS).
- GA4: míra zapojení a konverze po vstupní stránce pro placený provoz.

## 2. Postup

1. **Seřaď reklamy podle útraty** a vezmi těch 10 až 20, které tvoří 80 % nákladů. Zbytek
   neřeš.
2. **Slib vs. stránka.** Pro každou dvojici: je slib z titulku na stránce doslova nebo
   těsným synonymem v H1 nebo nad ohybem? Cena v reklamě = cena na stránce? Sleva nebo akce
   v reklamě ještě platí? Sloveso CTA v reklamě = text tlačítka? Každé ne je nález.
3. **Kam to vede.** Homepage nebo obecná kategorie místo produktu nebo služby = propad.
   Přesměrování přes 2 skoky nebo na jinou doménu = nález. Zamítnuté reklamy kvůli
   nefunkční URL řeš dřív než cokoli jiného.
4. **Rubrika stránky** z `knowledge/heuristiky-toprank.md` § 10: shoda sdělení 25 %,
   rychlost 25 %, mobil 20 %, důvěra 15 %, formulář a CTA 15 %. Skóruj, ale pořadí oprav
   je dané: rozbitá shoda → chybějící důkaz → tření formuláře → mobil a rychlost → nejasná
   nabídka.
5. **Čísla ke každému nálezu.** CVR dané reklamy vs. medián účtu, útrata za 8 týdnů, kolik
   objednávek nebo poptávek chybí při mediánovém CVR. Bez čísla nález nepiš.
6. **ChatGPT Ads zvlášť.** Reklama je odpověď na otázku, stránka musí tu odpověď dát hned
   nad ohybem (doporučení, cena, dostupnost). Produkt z feedu vede na produkt, ne na
   kategorii. Ověř UTM podle `.claude/skills/chatgpt-ads/chatgpt-ads-campaign-playbook.md` § 5 (UTM convention).

## 3. Rozhodovací pravidla

- Reklama slibuje, co stránka nemá (cena, sleva, pobočka, parametr): **oprav reklamu dnes**,
  je to i riziko zamítnutí. Stránku měnit nemusíš.
- Stránka je správná, ale slib je schovaný pod ohybem: změna nadpisu nebo prvního bloku,
  ne redesign.
- Stránka pomalá (LCP nad 4 s na mobilu) a shoda sdělení v pořádku: hlas stránku, ale
  nejdřív zkontroluj, že CVR na desktopu není stejně špatné. Pak není rychlost příčina.
- Kalibrace: stránka s LCP 3,5 s a shodou 95 % konvertuje líp než LCP 1,5 s se shodou 60 %.

## 4. Výstup

Tabulka: reklama (titulek) | URL | útrata 8 týdnů | CVR vs. medián | slib vs. stránka
(sedí / neseď v čem) | skóre rubriky | oprava | kdo (reklama = my, web = klient) |
odhad efektu. Pod ní tři největší úniky a jedna věta pro klienta bez zkratek.

## 5. Pasti

- Texty reklam ověřuj proti webu, ne proti klíčovému slovu („pobočka ve vašem městě“ bývá
  nepravda, když tam firma pobočku nemá).
- Popupy na placeném provozu odlož na 30 s nebo scroll, jinak pryč.
- Login nebo registrace před objednávkou = propad, bez ohledu na zbytek stránky.
- Změnu na webu zapiš do changelogu s datem, jinak příští vyhodnocení nepozná, odkud
  se CVR hnul.

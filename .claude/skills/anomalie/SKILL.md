---
name: anomalie
description: >
  Senior postup pro náhlý skok nebo propad v účtu (útrata, zobrazení, prokliky, CPC, konverze,
  CPA, PNO) v Google Ads, Skliku a Metě: pozná, co je šum a co signál, a projde příčiny
  v pevném pořadí (měření → změny v účtu → web a nabídka → trh a sezóna → aukce). Použij,
  když uživatel řekne „něco se stalo", „spadly konverze", „utrácí to dvojnásobek", „co se
  změnilo", „proč to včera vyletělo", nebo jako ranní hlídač. Načti spolu s perf.
---

# Anomálie: skok nebo propad v účtu

Většina výkyvů má příčinu mimo kampaň: akce, e-mail, sklad, rozbitý web, změna měření.
Senior **nejdřív zjistí, jestli je to vůbec anomálie**, a pak jde po příčinách v pevném
pořadí. Nikdy nezačíná úpravou nabídek.

## 1. Je to anomálie?

1. Metriku porovnej se **stejným dnem v týdnu** za posledních 8 týdnů, ne s včerejškem.
   Pondělí vs. neděle není anomálie.
2. Práh: odchylka přes **2 směrodatné odchylky** od průměru stejných dnů, nebo přes 40 %
   u metrik s malým objemem. Pod tím je to šum, nepiš o tom.
3. Konverze za poslední 1 až 3 dny dobíhají (atribuce, GA4 zpracovává 24 až 72 h). Propad
   konverzí ze včerejška se **nevyhodnocuje**, jen se poznamená a zkontroluje za 3 dny.
4. Jeden den s malým objemem (pod 100 prokliků, pod 5 konverzí) není důkaz ničeho.

## 2. Pořadí příčin (nepřeskakovat)

1. **Měření.** Útes na nulu nebo skok nahoru k jednomu dni = tag, web, formulář, nová
   konverzní akce, změna atribuce. Pusť `mereni-audit`, než půjdeš dál.
2. **Změny v účtu.** Google Ads `change_event` za 14 dní (kdo, co, kdy), changelog klienta,
   automatická pravidla, skripty, doporučení aplikovaná Googlem („auto-apply“). Ve Skliku
   historie změn. Učící fáze po změně biddingu nebo rozpočtu trvá 7 až 14 dní.
3. **Web a nabídka.** Dostupnost webu a landing page (stavový kód, rychlost), zamítnuté
   reklamy (`DESTINATION_NOT_WORKING` umí potichu zastavit reklamy napříč účtem), feed v Merchant
   Center (zamítnuté položky), vyprodáno, změna ceny, konec akce, e-mail nebo promo.
4. **Trh a sezóna.** Svátky, počasí, zprávy, YoY stejný týden loni. Konkurent zlevnil nebo
   přišel nový (Temu). Google Trends na hlavní dotaz.
5. **Aukce.** Statistiky aukcí: podíl zobrazení, překryv, pozice nad. CPC roste bez změny
   v účtu = někdo přišel nebo přitlačil. Viz `aukce-konkurence`.
6. **Struktura a cílení.** Rozšíření shody, nový broad, zapnutí partnerů nebo Display
   v Search, změna geo. Propad konverzí rozlož na traffic × CVR podle pěti os
   v `knowledge/heuristiky-toprank.md` § 8.

## 3. Pravidla

- Každé tvrzení buď ověřené (API, changelog, screenshot), nebo označené jako domněnka.
  „Nejspíš trh“ bez ověření se nepíše.
- **Žádná změna v účtu jako reakce na jednodenní výkyv.** Výjimka: rozbitý web nebo měření,
  tam zastavit útratu do opravy.
- Když příčinu nenajdeš, napiš „nevím, hlídám“ a nastav kontrolu za 3 dny. To je platný
  výstup.
- PMax reaguje i na změny v jiných kampaních účtu a kanály se mění druhý den po zásahu
  (zkušenost z praxe).

## 4. Výstup

1. Metrika, kdy, o kolik proti průměru stejných dnů (s číslem a obdobím).
2. Prošlé příčiny v pořadí výše, u každé: vyloučeno / potvrzeno / nelze ověřit.
3. Závěr: příčina (ověřeno / domněnka), co udělat, co nedělat, kdy zkontrolovat znovu.

## 5. Ranní hlídač (automatizace)

Denní běh přes naplánovanou úlohu nebo cron: čerpání rozpočtu, propady zobrazení a jejich
důvod (rozpočet / rank / zamítnutí), výkyvy CTR a CPC, tempo 7 / 14 / 30 dní. Výstup do
Slacku nebo e-mailu jen pro účty, které mají problém. Pro PMax existuje hotový Google Ads skript
`scripts/google_ads_scripts/pmax_hlidac.js`. Kontrola každých pár minut stojí peníze a nic
nepřinese, denně stačí.

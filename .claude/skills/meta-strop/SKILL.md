---
name: meta-strop
description: >
  Senior postup pro Meta Ads: najde strop škálování, tedy týdenní útratu, nad kterou další
  peníze už nepřinášejí víc prodejů (marginální ROAS), a rozliší nasycení od dražší aukce.
  Použij, když uživatel řekne „můžu Metě přidat?", „kolik dát do Mety", „škálování Mety",
  „proč po navýšení rozpočtu klesl ROAS", „kde je strop". Načti spolu s perf a perf_meta.
---

# Meta: kde je strop škálování

Průměrný ROAS může vypadat dobře, i když každá přidaná koruna už prodělává. Senior se proto
neptá „jaký je ROAS", ale **„kolik přinesla poslední přidaná tisícovka"**.

## 1. Než otevřeš čísla

- Marže → hranice výnosnosti (ROAS = 1 / marže). Bez ní strop nespočítáš.
- Atribuční okno účtu a jestli hodnota z pixelu je s DPH, nebo bez.
- Akce, e-maily a sezóna. Týdny s akcí mají vyšší výkon při stejné útratě, označ je.

## 2. Postup

1. **Týdny** (po–ne) za 6–12 měsíců, zvlášť za účet, hlavní kampaň a ideálně **jednu reklamu
   beze změny kreativy**. To je nejčistší experiment, jaký účet nabízí.
2. Seřaď týdny podle útraty a rozděl do **3–5 pásem**. Nemíchej v jednom pásmu různé řády
   útraty. Pro každé pásmo: počet týdnů, průměrná útrata, **průměrná hodnota nákupů na týden**,
   ROAS, zisk po marži, CTR, CPM, dosah.
3. **Marginální ROAS** mezi sousedními pásmy = o kolik vzrostla hodnota ÷ o kolik vzrostla
   útrata. Strop je tam, kde klesne pod hranici výnosnosti.
4. **Proč:** roste CPM → dražší aukce (konkurence, sezóna). CPM stejné, dosah roste, CTR
   klesá → **nasycení**, reklama už oslovuje lidi, kteří nekupují.
5. Kontrola dlouhou řadou: měsíce za celou historii ve stejných pásmech.

## 3. Rozhodovací pravidla

- Pásmo pod 3 týdny = nespolehlivé, jen směr.
- Nasycení se neřeší rozpočtem, ale **novou kreativou, novým publikem nebo novým produktem**.
- Nasycenou kampaň drž pod stropem, přidávej jen na dny akcí a den po akci vrať.
- Po změně rozpočtu nesahej 14 dní, jinak nic nevyhodnotíš. Samotný počet změn ale výkon
  nekazí, rozhoduje výše útraty (ověřeno na testovaném účtu).

## 4. Výstup

Věta pro majitele: „Do X Kč týdně Meta vydělává, nad Y už ne." → tabulka pásem s marginálním
ROAS → vysvětlení (nasycení / aukce) → doporučená útrata + jak škálovat jinak → výhrada
k atribuci (Meta si připisuje víc než GA4, tvar křivky tím ale obvykle neovlivníš).

## 5. Pasti z praxe

- Na jednom účtu při zhruba dvojnásobné útratě zůstaly prodeje stejné, CPM se nezměnilo
  a dosah vzrostl zhruba úměrně útratě. Čisté nasycení.
- První verze analýzy ukázala strop příliš nízko, protože jedno pásmo míchalo týdny s velmi
  různou útratou. Po rozdělení pásma vyšel strop výrazně výš. Pásma vždy kontroluj.
- Meta si podle posledního prokliku připsala několikanásobně víc než GA4. Absolutní zisk
  z Meta čísel je optimistický.

## 6. Technická nápověda

`perf_meta` → vstupní data, atribuce. Týdenní data z Insights po týdnech na úrovni účtu,
kampaně i reklamy. Parametry ověř v dokumentaci Marketing API přes Context7.

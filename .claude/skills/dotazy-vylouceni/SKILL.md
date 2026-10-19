---
name: dotazy-vylouceni
description: >
  Senior postup pro čištění vyhledávacích dotazů v Google Ads i Skliku, včetně Performance Max:
  najde slova a témata, která dlouhodobě utrácí bez konverzí, zkontroluje je proti historii
  a feedu a navrhne vylučující slova se shodou a úrovní. Použij, když uživatel řekne
  „projdi vyhledávací dotazy", „navrhni negativa", „co vyloučit", „nerelevantní dotazy",
  „dotazy co kazí CTR / utrácí". Načti spolu s perf a perf_srch.
---

# Vyhledávací dotazy: co vyloučit, aniž bych zabil, co prodává

Junior vylučuje dotazy z posledních 7 dní. Senior bere 7 dní jen jako **spouštěč** a
rozhoduje podle **90 a 180 dní**. Nejdražší chyba není nevyloučit odpad, ale vyloučit slovo,
které prodává.

## 1. Než otevřeš čísla

- Cílové CPA / ROAS klienta a co je vlastní sortiment (feed): značky, které e-shop prodává,
  nesmí skončit v negativech.
- Sezóna (produkty mimo sezónu nekonvertují, ale nejsou nerelevantní) a výpadky skladu.
- Stávající negativa a seznamy: co je připojené, co jen leží v účtu, jaké mají shody.

## 2. Postup

1. Dotazy za 7, 90 a 180 dní napříč kampaněmi, **včetně PMax**.
2. **Rozlož dotazy na jednotlivá slova.** U PMax se útrata tříští na tisíce variant a žádný
   jednotlivý dotaz nepřekročí práh, přitom celé slovo spálí tisíce. Pro každé slovo:
   zobrazení, prokliky, útrata za 90 dní, konverze za 180 dní.
3. **Kandidáti:** slova s nulou konverzí za 180 dní a útratou nad prahem (malý účet ~60 Kč
   / 90 dní, velký účet úměrně víc). Seřaď podle útraty.
4. **Roztřiď do témat:** konkurenční značky a produkty, zboží, které e-shop neprodává,
   informační dotazy (co je, jak funguje, význam pojmu), práce / zdarma / návod, jiné země a jazyky.
5. **Zkontroluj každého kandidáta:**
   - 🔴 proti **existujícím klíčovým slovům** v kampaních (Sklik: v sestavách), kam negativum půjde —
     porovnávat bez diakritiky; při konfliktu slovo v té kampani/sestavě nevylučovat (pravidlo z praxe),
   - proti feedu (neprodává to e-shop?),
   - proti dotazům, které za 180 dní konvertovaly (nezablokuje negativum výnosnou variantu?),
   - proti sezóně a skladu.
6. **Navrhni formu:** co nejužší shoda, která ještě chytí varianty (obvykle frázová na
   konkrétní značku nebo produkt), do **sdíleného seznamu** podle tématu, připojit
   ke kampaním, kde dává smysl.

## 3. Rozhodovací pravidla

| Situace | Rozhodnutí |
|---|---|
| Konkurence nebo cizí zboží, 180 dní bez konverze, utrácí dlouhodobě | vyloučit |
| Konkurenční značka, na kterou se prodává vlastní produkt | nechat, vyloučit jen konkrétní nevýnosný produkt |
| Obecný výraz pro vlastní sortiment pod cílem | nevylučovat, řešit cenu, feed, sklad, CPC |
| Informační dotazy | vyloučit jen ty, co nikdy nekonvertovaly („co je", „jak funguje") |
| Malé občasné dotazy (1 proklik) | ignorovat, nejsou vzorec |
| Negativum by zablokovalo **existující klíčové slovo** (aktivní i pozastavené) | **nevylučovat ani bez konverzí** — to slovo tam někdo dal záměrně; o KW se rozhoduje zvlášť (pauza jen po samostatném schválení). Seznam nepřipojit k té kampani / slovo z ní vynechat |

- **CTR:** u produktových a PMax reklam zobrazení bez prokliku nic nestojí. Vylučuj kvůli
  penězům, ne kvůli CTR. U klasického searche nízké CTR u relevantních slov řeš textem
  reklamy, ne negativem.

## 4. Výstup

Tabulka: slovo / téma | útrata 90 dní | konverze 180 dní | návrh | shoda | seznam | důvod.
Pod ní „čeho se vyvarovat" (slova, která vypadají jako odpad, ale prodávají) a baseline
pro kontrolu za 14 a 28 dní (včetně „tohle nesmí spadnout").

## 5. Pasti z praxe

- Obecné `<značka>` by na testovaném účtu zablokovalo výnosnou variantu „<značka> <jiná řada>".
  Vyloučit šlo jen `<značka> <produktová řada>`.
- Hotový seznam „Značky" obsahoval značky, které e-shop sám prodává. Každý seznam
  otestuj dřív, než ho připojíš.
- Report dotazů u PMax pokrývá jen ~60–65 % útraty. Zbytek negativy neovlivníš.
- Konverze posledních 3 dnů dobíhají. Nula za 7 dní není důkaz.

## 6. Technická nápověda

`perf_srch` → Analýza search terms. U PMax jsou dotazy v samostatném pohledu na úrovni
kampaně. Ověř v dokumentaci Google Ads API přes Context7. Zápis jen po schválení,
nejdřív náhled.

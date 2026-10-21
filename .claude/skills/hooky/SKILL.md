---
name: hooky
description: >
  Hooky na situaci zákazníka pro bannery, reklamy a videa: zeptá se na produkt, zákazníka a chvíli,
  kdy problém nastává, a navrhne hooky po typech (situace, otázka, moment dne, námitka, výsledek, důkaz).
  Hlídá, aby nic nevymýšlel (ceny, slevy, čísla, zdravotní tvrzení). Použij, když uživatel řekne
  „hook", „hooky", „claim", „nadpis na banner", „co napsat na banner", „čím zaujmout", „test claimů",
  „úhel reklamy", „proč by to lidi koupili". Navazuje na skill bannery (test claimů → Black Friday verze).
---

# Hooky na situaci zákazníka

Hook = první věta, kvůli které člověk přestane scrollovat. Nejlíp funguje **situace, ve které se zákazník
pozná**, ne vlastnost produktu ani sleva. „Večer padáte únavou?“ místo „Hořčík 400 mg“ nebo „−20 %“.

## 1. Zeptej se (jedno kolo, všechno najednou)

1. **Produkt:** co to je, pro koho, cena. Odkaz na produkt, když je.
2. **Zákazník:** kdo to kupuje nejčastěji (věk, role, situace v životě). Klidně 2–3 typy.
3. **Chvíle:** kdy přesně problém nastává? Denní doba, místo, co člověk zrovna dělá, co cítí.
4. **Co už zkoušel** a proč to nestačilo.
5. **Námitka:** proč zatím nekoupil (cena, nedůvěra, složitost, „to nepotřebuju“).
6. **Důkaz:** recenze s hodnocením, počet zákazníků, ocenění, garance. Jen skutečné.
7. **Zákazy:** co se nesmí (zdravotní tvrzení, superlativy, srovnání s konkurencí, ceny bez souhlasu).

Když uživatel něco neví, podívej se na web produktu, recenze a `clients/<klient>.md`.
Co nenajdeš, nedomýšlej. Odpovědi zapiš do `banner-generator/banners-<klient>/PROJECT.md` (sekce Zákazník).

## 2. Navrhni hooky po typech

Ke každému typu 2–3 návrhy, max. 6 slov, česky, oslovení podle brand manuálu:

| Typ | Co dělá | Příklad (smyšlená kavárna na doma) |
|---|---|---|
| **Situace** | popíše chvíli, kdy problém nastane | „Kafe z automatu? Zase?“ |
| **Otázka na pocit** | zeptá se, co zákazník cítí | „Ráno bez energie?“ |
| **Moment dne** | konkrétní čas nebo místo | „Pondělí, 6:40, prázdná konvice.“ |
| **Námitka** | odpoví na důvod, proč nekoupil | „Bojíte se páky? Stačí tlačítko.“ |
| **Výsledek** | stav po použití, bez slibu, který nejde dokázat | „Espresso doma za minutu.“ |
| **Sebe-selekce** | osloví jednu skupinu | „Pracujete z domu?“ |
| **Důkaz** | třetí strana, ne vy | „4,8/5 od 1 200 zákazníků“ (jen skutečné) |

Pravidla:
- **Situace před vlastností.** Vlastnost patří do podnadpisu, ne do hooku.
- **Žádná sleva v hooku.** Sleva přijde až v Black Friday verzi vítěze (skill `bannery`).
- **Nic nevymýšlej:** čísla, recenze, ceny a garance jen ze zdroje (URL). Bez zdroje typ Důkaz vynech.
- **Legislativa:** doplňky stravy jen schválená zdravotní tvrzení EU, kosmetika bez léčebných účinků.
  Hook o situaci („Večer padáte únavou?“) je v pořádku, slib léčby ne.
- 1,5sekundový test: rozumí člověk, který značku nezná, co se prodává a komu?

## 3. Výběr do testu

Doporuč **3 hooky různých typů** (ne tři varianty jedné věty) a napiš proč. Ty jdou do testu claimů
ve skillu `bannery`: jeden obrázek, tři nadpisy, vyhodnocení po 5–7 dnech podle ceny za nákup.
Vítěz pak dostane Black Friday verzi se skutečnou nabídkou.

Výstup: tabulka typ / hook / pro koho / proč / zdroj (u důkazu). Nic negeneruj ani nenahrávej bez schválení.

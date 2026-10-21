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

| Typ | Co dělá | Příklad (hořčík a spánek, Království zdraví) |
|---|---|---|
| **Situace** | popíše chvíli, ve které se zákazník pozná | „Ve tři odpoledne vás vypne jako světlo?“ |
| **Moment** | konkrétní čas nebo místo | „Půlnoc. Tělo spí, hlava jede dál.“ |
| **Námitka** | řekne nahlas, co si zákazník myslí; odpověď je v podnadpisu | „Další doplněk, co nic nedělá?“ |
| **Pro koho** | osloví jednu skupinu, ostatní přeskočí | „Pro všechny, co jen přežívají pondělí.“ |
| **Výsledek** | stav po použití, bez slibu, který nejde dokázat | „Konečně odpoledne bez druhého kafe.“ |
| **Důkaz** | třetí strana, ne vy | „4,8 z 5. Hodnotí ti, co ho berou každý den.“ (jen skutečné) |
| **Takhle ne** | superlativ, který nejde doložit | „Nejlepší hořčík na trhu!“ (klamavá reklama) |

Dobrý hook zní jako věta, kterou by řekl kamarád, ne jako slogan. Kontrola: zastavil bych se u toho já?
Když hook jde vyměnit za jakýkoli jiný produkt v kategorii, je moc obecný.

Pravidla:
- **Situace před vlastností.** Vlastnost patří do podnadpisu, ne do hooku.
- **V testu před akcí bez slevy.** Testujeme důvod koupit. Sleva přijde v Black Friday verzi (níž).
- **Nic nevymýšlej:** čísla, recenze, ceny a garance jen ze zdroje (URL). Bez zdroje typ Důkaz vynech.
- **Legislativa:** doplňky stravy jen schválená zdravotní tvrzení EU, kosmetika bez léčebných účinků.
  Hook o situaci („Večer padáte únavou?“) je v pořádku, slib léčby ne.
- **Meta:** hook se nesmí ptát přímo na věk, diagnózu ani jiné osobní údaje („Je vám přes 50?“, „Trpíte nespavostí?“).
  Situace a pocit ano („Večer padáte únavou?“).
- 1,5sekundový test: rozumí člověk, který značku nezná, co se prodává a komu?

## 3. Výběr do testu

Doporuč **3 hooky různých typů** (ne tři varianty jedné věty) a napiš proč. Ty jdou do testu claimů
ve skillu `bannery`: jeden obrázek, tři nadpisy, vyhodnocení po 5–7 dnech podle ceny za nákup.
Vítěz pak dostane Black Friday verzi se skutečnou nabídkou.

Výstup: tabulka typ / hook / pro koho / proč / zdroj (u důkazu). Nic negeneruj ani nenahrávej bez schválení.

## 4. Black Friday a Vánoce: jiná situace zákazníka

Na Black Friday zákazník nakupuje do zásoby, hledá dárky, konečně koupí, co odkládal, a hlídá termín.
Navrhni k vítězi testu i tyhle typy (nabídku vždy jen skutečnou, se zeptáním):

| Situace | Příklad | Pro koho |
|---|---|---|
| **Vítěz + nabídka** | „Ve tři odpoledne vás vypne jako světlo? Teď o [__ %] levněji.“ | studené publikum: důvod z testu, sleva navrch |
| **Zásoba** | „Zásoba na zimu, dokud je Black Friday.“ | kdo produkt zná nebo používá |
| **Odkládání** | „Chtěli jste ho zkusit „někdy“? Někdy je do neděle.“ | kdo váhal, dostane termín |
| **Dárek** | „Dárek pro mámu, co jen přežívá pondělí.“ | od Black Friday do Vánoc |
| **Čistá sleva** | „Hořčík −50 %. Jen do neděle.“ | teplé publikum (remarketing, zákazníci) |

Sleva funguje, když je skutečná a má termín. Studenému publiku dej nejdřív důvod, pak slevu.
Superlativ („nejlepší na trhu“) bez důkazu nepoužívej ani na Black Friday.

# Obecná pravidla tvorby PPC kampaní

Platí pro Sklik i Google Ads, pro vyhledávací i obsahové kampaně.

## Workflow tvorby kampaně

1. **Brief / kontext** — co propagujeme, cílová URL, cílová skupina, rozpočet, doba běhu, cíl (konverze × povědomí × sezónní akce)
2. **Keyword research / výběr publik** — suggest nástroje platformy, hledanost, odhad CPC; u obsahu volba publik a umístění
3. **Návrh struktury** — kampaně → sestavy → KW/cílení → inzeráty, rozpočty a CPC s odůvodněním
4. **Schválení uživatelem** — struktura i texty inzerátů se VŽDY předkládají ke schválení PŘED vytvořením
5. **Vytvoření** — přes API/CLI, kampaň se zakládá **pozastavená** (suspend); aktivace až po finální kontrole
6. **Verifikace** — po vytvoření ověřit přes API, že vše sedí (status, rozpočet, korekce zařízení, publika, texty)

## Typy kampaní — přehled

| Typ | Charakteristika |
|---|---|
| **Vyhledávací (SRCH)** | Nejvýkonnější — uživatel aktivně hledá. Klíčová slova + textové inzeráty |
| **Obsahová (display)** | Remarketing (lepší CR/CTR) i akvizice (tvoří poptávku, horší metriky). Bannery, kombinované/nativní reklamy |
| **Produktová (shopping)** | Google Nákupy / PMax, Sklik Zboží. Produkt s fotkou a cenou přímo ve výsledcích |

Nikdy nemíchat vyhledávání a obsah do jedné kampaně.

## Klíčové metriky

| Metrika | Cíl |
|---|---|
| CTR | Čím vyšší, tím lépe — ovlivňuje skóre reklamy / Ad Rank |
| CPC | Čím nižší, tím lépe — v rovnováze s marží |
| Konverzní poměr (CR) | Čím vyšší, tím lépe — závisí na relevanci produktu a landing page |
| AOV (hodnota objednávky) | Čím vyšší, tím lépe |
| PNO | Čím nižší, tím lépe — ale VŽDY v kontextu marže |

### PNO × marže — klíčový vztah

```
PNO = (náklady na reklamu / obrat z reklamy) × 100
```

- Marže 55 % a cílové PNO 24 % → OK (zbývá 31 % ziskové marže)
- Marže 35 % a cílové PNO 24 % → problém (zbývá jen 11 % na provoz a zisk)
- **Vždy znát marži produktu/kategorie** — PNO cíl přizpůsobit marži, ne každá kategorie unese stejné PNO

## POVINNÁ pravidla (platí všude)

### Obrázky a logo v reklamách

- Používat **POUZE kvalitní, ostré fotky produktů** — nikdy rozmazané ani náhodné obrázky z internetu
- **Fotka MUSÍ odpovídat produktu v textu reklamy** — jiný produkt na fotce než v textu je zásadní chyba
- Pokud kvalitní fotka není k dispozici → **vyžádat si ji** — raději bez fotky než se špatnou
- **Logo klienta vždy přidat** — použít PŘESNĚ tu verzi, která je nahraná v účtu (typicky na bílém pozadí); nikdy nevymýšlet vlastní podklad ani nestahovat logo z internetu
- Logo nahrávat **v obou formátech: čtverec (1:1) I obdélník (4:1)** — nikdy jen jeden
- **Vždy více variant fotek** — stejné texty zduplikovat s různými obrázky, systém rotuje a vybere lepší
- Checklist před nasazením: (1) fotka ostrá? (2) odpovídá textu? (3) logo v obou formátech? (4) min. 2 varianty fotek na sestavu?

### Cílení na zařízení

- Cílení na jedno zařízení se dělá **VÝHRADNĚ vylučovacími korekcemi -100 %** na ostatní zařízení — NIKDY kladnou přirážkou (+100 % necílí, jen zdvojnásobí cenu!)
- Jen mobil → desktop -100 % (tablet a ostatní se počítají k mobilu)
- Jen desktop → -100 % na všechna ostatní zařízení (mobil, tablet, ostatní)
- Po vytvoření **VŽDY ověřit přes API**, že korekce sedí na všech sestavách

### Remarketing

- Každá remarketingová kampaň **MUSÍ mít přiřazené publikum ke VŠEM sestavám**
- Po vytvoření VŽDY ověřit, že publikum bylo přiřazeno (nesmí být `null`)
- Bez publika to není remarketing, ale neadresná display kampaň → pokud přiřazení selže, ZASTAVIT SE a upozornit uživatele

### Demografické cílení

- Cílení jen na ženy → u mužů korekce **-100 %** (a naopak)
- Nerelevantní věkové skupiny → korekce **-100 %**
- Stejný princip jako u zařízení: vylučovat, ne přirážet

## Bezpečnost práce přes API

### Čtení

- Sériové requesty — žádný paralelní souběh
- Před prací načíst limity platformy (Sklik: `api.limits`; Google: denní kvóta tokenu)
- Exponenciální backoff na rate-limit chybu (HTTP 429 / `RESOURCE_TEMPORARILY_EXHAUSTED`): 5 s → 10 s → 20 s → 40 s, max 5 pokusů

### Zápis — tvrdá pravidla

1. **Nikdy zápis bez explicitního schválení uživatele** — AI analyzuje a navrhuje, zapisuje až po odsouhlasení
2. **Vždy dry-run předem** — ukázat, co se provede
3. **AI-generované texty kontroluje člověk před publikací** — špatný text = policy problém
4. **Žádné hromadné zápisy naráz** — malé dávky, postupné kroky, po změně baseline a vyhodnocení
5. **Rozpočet / CPC stropy jako pojistka** — nikdy neomezené ani extrémní hodnoty; nová kampaň konzervativně
6. **Kampaň zakládat pozastavenou** — aktivace až po kontrole
7. **Žádné tokeny/credentials v gitu** — jen v lokálním `.env`

## Časové rámce vyhodnocování

| Období | K čemu |
|---|---|
| 1 den | Akutní problémy — výpadky, výkyvy CPC, nulové konverze |
| 7 dní | Krátkodobý trend po změnách |
| 30 dní | Standardní vyhodnocení — základ pro rozhodování |
| 60–90 dní | Dlouhodobý trend, sezónnost |
| Meziroční | Co běželo loni a letos ne? Sezónní příležitosti |

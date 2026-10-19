# Obsahové kampaně na Skliku — Kombinovaný responzivní formát

> **Tenhle soubor = cílení a struktura pro Sklik obsahovku** (konkrétní weby Seznamu, kombinace cílení).
> **Jak reklamu reálně vyrobit** (podklady, rozměry, `ads.create`, verifikace) je v
> `tvorba-kampani/05-KOMBINOVANA-REKLAMA-RECEPT.md`; API gotchas v `tvorba-kampani/04-SKLIK-SPECIFIKA.md`.

## Logo

Logo **není povinné**, ale je **extrémně doporučené** — zvyšuje viditelnost a rozpoznatelnost značky. Pravidla:

- Logo mít u reklamy **vždy**
- Buď musí být nahráno v účtu na Skliku, nebo musí být aktuální verze dostupná v klientské složce (`[klient]/logo/`)
- **Nikdy nestahovat logo z internetu** — hrozí neaktuální verze, špatná kvalita nebo cizí logo
- Před nasazením ověřit s klientem, že jde o aktuální logo

---

## Cílení — dva základní režimy

### 1. Remarketing

- Cílení na uživatele, kteří už web navštívili
- Lepší CR, CTR, přijatelné CPC
- Texty mohou být stejné jako u akvizice, rozlišit CPC a rozpočtem

### 2. Akvizice

Před tvorbou akvizičních kampaní **vždy se zeptej:**

- **Co je cílem kampaně?** (budování povědomí, konverze, sezónní akce…)
- **Jaký je rozpočet a doba běhu?**
- **Jaká je cílová skupina?** (muži/ženy/všichni, věková skupina)

#### Akvizice — menší rozpočet / kratší doba běhu

Cílení může být **úzké**:
- Zájmy o koupi + kvalitní umístění (weby Seznamu)
- Menší zásah, ale relevantnější

#### Akvizice — větší rozpočet / dlouhodobá kampaň

Volnější targeting:
- Weby Seznamu jako základ
- Rozdělení sestav na mobil a desktop
- Širší cílení pro budování poptávky

---

## Cílení — best practices

### Pohlaví

Pokud je známá cílová skupina (dámská/pánská):
- Rozdělit cílení podle pohlaví
- Pro cílení **pouze na ženy** → u mužů nastavit bidding modifikátor **-100 %** (vyloučení)
- Analogicky pro cílení pouze na muže

### Věk

Pokud je známá věková skupina:
- Nerelevantní věkové skupiny vyloučit pomocí bidding modifikátoru **-100 %**
- Příklad: cílová skupina 35+, věk 15–24 a 25–34 nechci → u těchto skupin dám **-100 %**

### Bidding na umístění

- Stáhnout si bidding na konkrétní umístění
- Na méně kvalitní umístění (např. novinky.cz) snížit bid o **-30 %**
- Weby Seznamu nechat na plném biddingu nebo zvýšit

---

## Struktura sestav — rozdělení mobil/desktop

Základní princip: **vždy rozdělit na mobilní a desktopové sestavy**.

```
Kampaň: [Produkt] — Obsahová akvizice
├── Sestava: Seznam — Mobile
│   (weby: seznam.cz, novinky.cz, prozeny.cz, super.cz, seznamzpravy.cz, kupi.cz, zbozi.cz)
├── Sestava: Seznam — Desktop
│   (stejné weby)
├── Sestava: Mimo Seznam — Desktop
│   (vyloučit seznam weby, cílit jen desktop)
└── Sestava: Mimo Seznam — Mobile
    (vyloučit seznam weby, CPC na 1 Kč — omylem kliky)
```

---

## Možné kombinace cílení v rámci sestav

Každou kombinaci rozdělit na **mobilní a desktopovou** verzi:

- Umístění weby Seznamu + mobil/desktop
- Umístění + zájmy
- Umístění + zájmy o koupi
- Umístění + věk
- Umístění + věk + pohlaví
- Umístění + zájmy + pohlaví
- Weby mimo Seznam + desktop
- **Akviziční remarketing** — publikum 360 dní, vyloučit 30–60 dní, aplikovat kombinace mobil/desktop nebo umístění

### Co NEDĚLAT

- **Nekombinovat pro akvizici** zájmy + retargeting + umístění najednou — publika tvoří průniky a zásah se zmenší
- **Pozor na příliš úzké cílení** — pokud je zadán jeden web + zájmy + věk + pohlaví, zásah bude velmi malý a reklama se nemusí rozběhnout
- **Rozdělit umístění** na weby Seznamu a mimo weby Seznamu — v rámci umístění vyloučit jednu nebo druhou skupinu

---

## Rozdělení umístění

| Skupina | Weby | Poznámka |
|---|---|---|
| **Weby Seznamu** | seznam.cz, novinky.cz, prozeny.cz, super.cz, seznamzpravy.cz, kupi.cz, zbozi.cz | Lepší kvalita kliknutí |
| **Mimo Seznam** | Vše ostatní (vyloučit seznam weby) | Na mobilu riziko omylných kliků → nízké CPC (1 Kč) |

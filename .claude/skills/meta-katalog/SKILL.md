---
name: meta-katalog
description: >
  Senior postup pro katalogové (Advantage+ catalog / DPA) kampaně na Metě: kam katalog posílá
  peníze po produktech, KOLIK KTERÝ PRODUKT SKUTEČNĚ PRODAL (nákupy po produktech jdou
  z API dostat, i když je Ads Manager neukazuje), co se opravdu prodává, komu se reklama zobrazuje (věk, pohlaví,
  umístění) a jak rozdělit produktové sady. Použij, když uživatel řekne „co propaguje katalog",
  „DABA po produktech", „vyřadit produkty z katalogu", „komu se zobrazuje reklama",
  „rozdělit produktovou sadu". Načti spolu s perf a perf_meta.
---

# Meta katalog: co propaguje a komu

Katalog si produkty vybírá podle toho, **na co se kliká**, ne podle toho, co vydělává.
Senior porovná, kam jdou peníze, s tím, co se opravdu prodává a s jakou marží.

## 1. Než otevřeš čísla

- Marže po produktech nebo rodinách (kus vs. sada, vlastní vs. cizí značka).
- Sklad. Katalog rád propaguje vyprodané nebo stažené zboží.
- Běží vedle katalogu jiné kampaně na stejné produkty? (Přičti je k ekonomice produktu.)

## 🔴 2. Nejdůležitější věc v tomhle skillu: nákupy po produktech Z META API DOSTAT JDOU

Ads Manager u rozpadu podle produktu ukáže jen útratu, zobrazení a prokliky. Většina
specialistů proto věří, že Meta konverze po produktech nedává, a ekonomiku katalogu počítá
naslepo. **Není to pravda.** Ověřeno na živém účtu (podzim 2026):

- Rozpad podle produktu **vrací i nákupy a jejich hodnotu**, ale jen v **novější rodině
  metrik**: `onsite_web_purchase`, `web_in_store_purchase`, `onsite_web_app_purchase`
  (hodnota je ve stejných názvech v poli s hodnotami akcí).
- **Klasické `purchase` a `offsite_conversion.fb_pixel_purchase` vrátí u tohoto rozpadu nulu.**
  Je to dokumentované omezení: u rozpadu podle produktu jsou offsite metriky omezené, takže
  „nula" neznamená „neprodalo se", ale „ptáš se na špatnou metriku". Na tomhle většina
  analýz ztroskotá.
- Ptej se na úrovni **kampaně nebo sestavy**, spolu s rozpadem akcí podle typu akce.
- **Povinná kontrola:** součet nákupů a hodnoty přes produkty se musí rovnat součtu za celou
  kampaň. Když nesedí, čteš špatnou metriku nebo ti chybí produkty bez zobrazení.
  (V praxi součet přes všechny produkty seděl na celou kampaň přesně, takže kontrola je spolehlivá.)
- **Past:** rozpad podle produktu vrací řádky **i pro nekatalogové reklamy** (bannery, videa).
  Tam produkty nepocházejí z reklamy, ale z pixelu (co si člověk po prokliku prohlédl a koupil).
  Proto reklamy nejdřív roztřiď podle toho, jestli mají `product_set_id`, a do reportu pusť jen
  katalogové. Název kampaně o tom neříká nic, v jedné kampani běží katalog i bannery vedle sebe.
- Výstupem je tabulka **produkt | útrata | nákupy | hodnota | ROAS | přidání do košíku**,
  tedy skutečná ekonomika katalogu po produktech, ne odhad z podílů.
- **Na hotový report tohohle typu je samostatný skill `produktovy-report`** (stahování po
  týdnech, prahy, sekce, PDF). Tenhle skill řeší rozhodování, `produktovy-report` výrobu reportu.

## 3. Zbytek postupu

1. **Útrata, nákupy a hodnota po produktech** za 8 týdnů (podle bodu 2). Sluč varianty do rodin.
2. **Prodeje po produktech z e-shopu nebo GA4** jako druhý pohled. Meta připisuje nákup
   produktu, na který člověk klikl, ne nutně tomu, co koupil (v košíku bývá něco jiného).
3. Tabulka: rodina | % útraty katalogu | % tržeb z Mety | % tržeb e-shopu | ROAS podle GA4.
   Hledej **přefinancované** produkty (hodně peněz, málo prodejů) a **podfinancované vítěze**.
4. **Hygiena:** vyprodané, stažené, neprodejné položky v sadě.
5. **Kdo to vidí:** věk × pohlaví a umístění. Segmenty s velkým podílem útraty a ROAS pod
   hranicí výnosnosti. Rozdíly ověř podle počtu nákupů, malé vzorky označ.

## 4. Rozhodovací pravidla

- **Nulové produkty rozděl na dvě skupiny:** nula nákupů **i** nula přidání do košíku = nefunguje
  reklama, kandidát na vyloučení. Nula nákupů, ale lidé ho do košíku dávali = problém je za
  proklikem (cena, dostupnost, doprava, checkout), vyloučením bys léčil symptom.
- Návrh na vyřazení dávej, až když produkt utratil **3× CPA a nemá nákup** (do té doby je nula
  statisticky běžná).
- Přefinancované produkty s vysokým PNO → vlastní sada s nízkým rozpočtem, nebo ven.
- Vítěze posil **vlastní kampaní a kreativou**, ne jen katalogem.
- Katalog tlačí levnou variantu a lidé kupují jinou → do hlavní sady dej to, co se opravdu prodává.
- Věk a pohlaví **nevylučuj natvrdo** (Advantage+ je bere jen jako signál). Přesměruj
  kreativou a produktovou sadou.
- Umístění s kliky bez nákupů (typicky Audience Network) vypnout.

## 5. Zkušenost týmu

- Top prodejce z katalogu převést do statických bannerů a nechat je běžet vedle katalogu.
- Samostatný katalog s malým rozpočtem optimalizovaný na přidání do košíku pro top
  produkty: hlavní katalog tak dostane víc dat.
- Sezónní zboží segmentovat do vlastních sad (léto / zima).

## 6. Výstup

Věta: „X produktů bere Y % peněz a prodává Z %." → tabulka rodin → hygiena → segmenty
publika → návrh sad (co do hlavní, co zvlášť, co ven) → test na 4 týdny a podle čeho ho vyhodnotit.

## 7. Pasti z praxe

- Běžný nález: dva tři produkty berou většinu rozpočtu katalogu, zatímco menší kategorie má zlomek peněz
  a nepoměrně velký podíl tržeb z Mety (podfinancovaný vítěz).
- V katalogu běžně visí produkty, které se už neprodávají (vyprodané, stažené).
- Vazba „segment ← produkt" (např. věková skupina Y ← produkt X) je z dat nepřímá. Označ ji jako domněnku.
- Dřívější tvrzení „Meta nákupy po produktech nevrací" bylo mylné. Vracelo nulu jen proto, že se
  četla špatná metrika nákupu.

## 8. Technická nápověda

`perf_meta` → vstupní data. Rozpad útraty po produktech a po věku / umístění z Insights.
Ověř parametry v dokumentaci Marketing API přes Context7.

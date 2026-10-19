# Nereklamní statiky (native static) — 10 prověřených formátů

Znalostní soubor. Zdroj: podcast **PPC Brainfood — „Dělej nereklamně vypadající kreativy, a budeš mít mnohem lepší výkon!"** (Markéta Kabátová, YouTube `HkU7CZ35Uok`), doplněno o guardraily tohoto repa (legislativa, Meta policy, cold-audience test).

V tomto repu je metodika závazná přes **DVANÁCTÉ ZLATÉ PRAVIDLO** v `BANNER-INSTRUCTIONS.md` a implementovaná jako prompt building blocky v `lib/native-static.ts`.

## Základní teze

> Statiky, které **nevypadají jako reklama**, mají výrazně lepší výkon než „načančané" bannery od jakékoli kreativní fermy. Testováno na CZ/SK účtech, funguje i v B2B — tam je efekt často největší, protože tamní kreativy vypadají nejreklamněji.

Kontext: po Andromedě (Meta 2025) je nutná diverzifikace kreativ. Videa vyhrávají, ale statiky pořád trhají výsledky — pokud vypadají jako **obsah**, ne jako banner.

**Proč to funguje:** divák scrolluje ve feedu mezi příspěvky kamarádů. Kreativa, která vypadá jako příspěvek, screenshot nebo poznámka, projde pod radarem „banner blindness" a získá pozornost dřív, než ji mozek zařadí do složky „reklama".

**Co to NENÍ:** není to výmluva pro nedbalou grafiku. Nereklamní ≠ ošklivé. Je to záměrná estetika „vypadá to, jako by to někdo poslal / nalepil / vyfotil".

---

## Taxonomie — 10 formátů

Každý formát dostane tag `NS1`–`NS10` (používá se v řádku `// BUŇKA:` v configu a v coverage gridu jako podtyp formátu `native-static`).

### NS1 — Komunikace na mobilu

**Co to je:** kreativa vypadá jako něco, co běžně vidíš na displeji telefonu.
Tři varianty:
- **Příchozí hovor** — „Volá vaše nová cyklistická přilba" (obrazovka volání, jméno volajícího = produkt/benefit)
- **Screenshot zprávy** — někdo ti píše zprávu; text zprávy = sdělení reklamy
- **Toggle / nastavení** — produkt + seznam featur s přepínači v poloze ON (zelené)

**Kdy použít:** toggle varianta je skvělá na čisté vizuální odkomunikování 3–4 výhod produktu. Zpráva/hovor na krátký emoční hook.
**Úhly, kterým sedí:** mechanism (toggle = featury), pain-point (zpráva), aspiration.
**Pozor:** ⚠️ NIKDY neimitovat UI Facebooku, Messengeru, Instagramu ani WhatsAppu (viz Guardraily). Generický systémový vzhled telefonu ano, brandované UI platformy ne.

### NS2 — Reminder / připomínka

**Co to je:** jednoduchý výrazný prvek připomínky — notifikace, upozornění v kalendáři, „nezapomeň".
**Kdy použít:** sezónnost, deadline, opakující se rituál (ranní káva, objednání dárku, konec slevy).
**Úhly:** pain-point (zapomínáš), identity, comparison (cena/termín).
**Pozor:** připomínka nesmí vypadat jako systémová notifikace zařízení ani platformy — jen jako *stylizovaná* karta připomínky.

### NS3 — Komunikace se sítí (Q&A sticker)

**Co to je:** formát, který každý zná z Instagram stories — nálepka s otázkou a pod ní odpověď. Pozadí je klidně náhodná fotka; nosné jsou prvky **otázky** a **organicky napsané odpovědi**.
**Kdy použít:** je to nejsilnější nástroj na **boření nákupních bariér** — otázka je přesně ta tíživá věc, kterou si zákazník klade („Vydrží to víc než rok?", „Zvládnu to obsluhovat bez návodu?"), odpověď ji odbourá.
**Úhly:** pain-point, mechanism, social-proof.
**Pozor:** odpověď musí být napsaná **organicky** — normální lidskou větou, ne marketingovým sloganem. Načančaná odpověď formát zabije. ⚠️ Nálepka musí být vlastní stylizace, ne 1:1 kopie IG UI.

### NS4 — Post-it / papírek

**Co to je:** hmatatelný prvek — nalepený post-it, ručně napsaná poznámka. Buď samotný lísteček, nebo naaranžovaný s produktem („produkt + žlutý papírek: teď −40 %").
**Kdy použít:** slevy, akce, krátká pobídka; taky „to nejdůležitější, co si musíš zapamatovat".
**Úhly:** comparison (cena), pain-point, identity.
**Pozor:** ručně psané písmo musí být čitelné i v malém náhledu. Text max 5–6 slov.

### NS5 — Autentická fotka + organický text

**Co to je:** obyčejná, nearanžovaná fotka — selfie zakladatele/CEO, fotka laptopu na stole, produkt v ruce — a k tomu text, který vypadá jako popisek, ne jako headline banneru.
**Kdy použít:** služby, kurzy, B2B, osobní brandy; kdekoli, kde prodává důvěra k člověku.
**Úhly:** identity, social-proof, aspiration.
**Pozor:** text nesmí být vysázený jako reklamní headline (žádné stíny, gradienty, zlaté rámečky). Jednoduchý sans-serif, plochý, jako by ho tam někdo dopsal v telefonu.

### NS6 — Text na obyčejném pozadí

**Co to je:** nejobyčejnější kreativa na světě — jednobarevné nebo náhodné pozadí (zdobená kachlička, zelené pozadí s vykukujícími čápy) a na něm text. Žádná grafika, žádný produkt.
**Kdy použít:** kurzy, tábory, služby, eventy, B2B — všude, kde nemáš dobrou fotku.
**KLÍČ (otestováno):** v **první větě vydefinuj cílovku, kterou oslovuješ** — „Jezdíš do práce na kole?", „Hledáme lidi v Česku, kteří…". Divák si okamžitě spočítá, jestli číst dál. Sebe-selekce publika = výrazně lepší výkon.
**Úhly:** identity (primárně), pain-point.
**Pozor:** v tomto repu se text u NS6 skládá přes `overlays` (viz `lib/compose-overlays.ts`), ne přes AI — obyčejný text musí být typograficky bezchybný, protože nic jiného na kreativě není.

### NS6b — Informační karusel

**Co to je:** vícelistý informační obsah, který působí jako organický edukační příspěvek; teprve na posledním listu přijde „a s tímhle ti pomůže náš produkt".
**Kdy použít:** složitější témata, MOF, B2B.
**Pozor:** musí být **informačně hutný** — divák musí mít pocit, že dostal hodnotu. Prázdný karusel s CTA na konci nefunguje. Repo generuje jednotlivé listy jako samostatné statiky (`slug` = `nsK_list1`…), skládání do karuselu je pak ruční v Ads Manageru.

### NS7 — Sdělení v reálném kontextu

**Co to je:** tvé sdělení vsazené do reálného světa — letáček nalepený na stromě/sloupu, plakát v metru, billboard, cedule ve výloze. Vyfotíš prostředí a „plácneš" tam svoje sdělení.
**Kdy použít:** lokální služby, nábor, eventy, provokativní claim.
**Úhly:** identity, pain-point, aspiration.
**Pozor:** perspektiva a světlo musí sedět, jinak to vypadá jako špatný fotomontáž. U AI generace explicitně žádej „photo of a real printed poster, correct perspective and lighting, slight paper texture".

### NS8 — Zamazaný / začerněný obsah ⚠️ pokročilé

**Co to je:** obsah kreativy je záměrně zamazaný/rozostřený a text říká, proč („tohle si nech pro svůj feed"). Používá Furioza.
**Kdy použít:** jen když to sedí k brandu s vyhraněným tónem.
**Pozor:** ⚠️ **Nejrizikovější formát ze seznamu.** Snadno vznikne něco nesrozumitelného nebo trapného. Používej jen s brandem, který má odvahu a jasný hlas — pro finanční služby, pojištění a jiná vážná témata **nedoporučeno**.

### NS9 — Infografika / mem styl

**Co to je:** chytrý humor, se kterým se cílovka ztotožní. Formáty: „Bohužel nemůžu jít, mám jiné plány" → *a teď moje plány: [produkt]*; rozhodovací strom „Jaká je tvoje ranní rutina?" → všechny větve vedou k produktu.
**Kdy použít:** TOF, mladší cílovky, brandy s lehčím tónem.
**Úhly:** identity, aspiration, comparison.
**Pozor:** vyžaduje promyšlenou pointu — není to rychlovka jako NS4/NS6. Humor musí být *sdílený* („to jsem já"), nikdy na účet cílovky.

### NS10 — Jazyk cílovky (insider language)

**Co to je:** použití specifického jazyka/zkratek, kterým rozumí jen tvá cílovka. Ověřený příklad: nábor brigádníků přes „**F1 IRL**" — pět písmen, mladí to chápou, rezonuje, a na zbytku kreativy pak už skoro nezáleží.
**Kdy použít:** nábor, komunity, subkultury, produkty s vyhraněnou cílovkou.
**Úhly:** identity (primárně).
**Pozor:** insider jazyk = **filtr**. Kdo mu nerozumí, odscrolluje — to je záměr, ne chyba. ⚠️ Ale nesmí kolidovat s cold-audience testem u produktů, kde je publikum široké. U produktů se širokou nebo starší cílovkou používej jen mírné formy (slang oboru, ne generační zkratky).

---

## Guardraily — co si u nereklamních statik ohlídat

### 1. Meta policy: žádné imitace UI a nefunkční prvky

Meta zakazuje kreativy, které napodobují funkce platformy nebo předstírají interaktivitu:
- ❌ fake play button, fake checkbox, fake progress bar, fake „swipe up"
- ❌ UI Facebooku / Instagramu / Messengeru / WhatsAppu (logo, ikony, layout notifikace platformy)
- ❌ falešný badge počtu zpráv / notifikací
- ✅ **vlastní stylizace** téhož principu — bublina zprávy, karta připomínky, nálepka otázky bez brandingu platformy

Tohle je zároveň hlavní rozdíl proti stávajícímu pravidlu v promptech tohoto repa (`NEVER render any social-media UI`). U native-static konceptů se toto pravidlo **cíleně změkčuje na: žádné UI konkrétní platformy, ale stylizovaný interface prvek ano.** Ve všech ostatních konceptech platí zákaz dál v plné síle.

### 2. Cold-audience test platí i tady

Nereklamní ≠ nesrozumitelné. ČTVRTÉ ZLATÉ PRAVIDLO (1,5 s scroll test) platí beze změny: divák musí poznat, **co to je, pro koho a co to řeší**. NS8 a NS10 tenhle test nejčastěji nesplní — proto jsou označené jako rizikové.

### 3. Legislativa se nezměkčuje

Formát je nereklamní, claim ne. Zákaz léčebných tvrzení, zákaz slibu výsledku, zakázané věci z `BRAND-MANUAL.md` a zákaz vymyšlených recenzí (ŠESTÉ ZLATÉ PRAVIDLO) platí **v plném rozsahu**. Zvlášť u NS3 (Q&A) a NS5 (selfie + text) je pokušení napsat „lidsky znějící" claim, který je fakticky medical slib — nedělej to.

### 4. Text na nereklamních statikách skládej kódem

Nereklamní estetika stojí a padá s tím, že text vypadá **obyčejně, ale bezchybně**. AI komolí českou diakritiku a u čistě textových kreativ (NS4, NS6, NS9) není za co schovat překlep. Použij `overlays` (dvouvrstvý render, `lib/compose-overlays.ts`) — AI vygeneruje jen pozadí, text složí kód.

### 5. Nereklamní neznamená bez produktu

U e-shopových produktů musí být produkt pořád poznatelný (ČTVRTÉ ZLATÉ PRAVIDLO). NS6 a NS10 bez produktu fungují hlavně u **služeb, kurzů a náboru** — u fyzického produktu je kombinuj s produktovým záběrem.

---

## Jak to používat v tomto repu

1. **Fáze 1 (návrh konceptů):** v sadě 6 konceptů navrhni **minimálně 2 v nereklamním provedení** a u každého uveď jeho tag `NS1`–`NS10` (DVANÁCTÉ ZLATÉ PRAVIDLO).
2. **Config:** v komentáři konceptu rozšiř řádek `// BUŇKA:` o podtyp — `… × native-static (NS3 Q&A)`.
3. **Prompt:** použij building blocky z `lib/native-static.ts` — `nativeStaticStyle('NS3', {...})` vrátí STYLE blok a `NATIVE_STATIC_RULES` správně změkčené technické zákazy.
4. **Text:** u textově nosných formátů dej text do `overlays`, ne do promptu.
5. **Coverage:** v `banners-<klient>/COVERAGE.md` se native-static buňky značí i s podtypem, aby bylo vidět, které z 10 formátů už klient testoval.

## Mapování NS formátů na úhly (kterou buňku pomáhají zaplnit)

| Úhel | Nejlépe sedící NS formáty |
|---|---|
| pain-point | NS1 (zpráva), NS2, NS3, NS7 |
| mechanism | NS1 (toggle), NS3, NS6b |
| aspiration | NS1 (hovor), NS5, NS7, NS9 |
| social-proof | NS3, NS5, NS6b |
| identity | NS6, NS9, NS10, NS5 |
| comparison | NS4 (cena), NS2, NS9 |

## Otevřené otázky / co ověřit vlastními daty

- Jak dlouho nereklamní statiky vydrží, než je publikum přečte jako reklamu (creative fatigue u nativního formátu zatím neměřeno).
- Jestli sebe-selekce cílovky v první větě (NS6) nezhoršuje CPM tím, že zúží publikum pod prah učení u malých budgetů.
- NS8 u finančních služeb a vážných témat — netestováno, riziko nesrozumitelnosti vysoké.

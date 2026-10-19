# Google Ads: jak získat přístupy

> Pět kroků, dvacet minut a máš to za sebou. Bez toho, aby ses zasekl.

Sklik i Meta jsou na dvě minuty, tam zkopíruješ jeden token a hotovo. Google to má složitější,
protože odděluje kdo se ptá (tvoje aplikace), čí data (účet) a kdo to povolil (ty). Není to
těžké, jen to má pět kroků. Projdi je popořadě.

**Co se změnilo 9. 9. 2026.** Google zrušil developer tokeny. Úroveň přístupu k API už nepatří
k MCC účtu v Google Ads, ale ke **Cloud projektu**, ze kterého pochází tvůj OAuth klient. Žádá
se o ni v Google Cloud Console (krok 4), stránka API Center v Google Ads už jen říká, že tam
se nic nespravuje. Pokud jsi návod prošel dřív, projdi znovu krok 4 a v `.env` nech
`GOOGLE_ADS_DEVELOPER_TOKEN` prázdný, skripty ho nepotřebují.

Nezačínej tímhle. Nejdřív si rozjeď Sklik nebo Metu, ať vidíš, že to funguje. Google si nech,
až budeš mít chuť pokračovat.

## Kde se to celé odehrává

Otevři si složku projektu v Claude Code a mluv na něj normálně česky. Kroky 1 až 4 jsou
klikání v prohlížeči, v kroku 5 spustíš jeden příkaz.

Jediné, co si připravíš ručně, je soubor s přístupy `.env`. **Zakládáš ho ty, ne Claude**
(Claude soubory s klíči nečte, nezakládá ani nevypisuje). V Claude Code napiš do řádku zprávy
(vykřičník na začátku = příkaz se spustí v terminálu, ne v konverzaci):

```
! cp .env.example .env
```

Pak do něj postupně vkládáš hodnoty z kroků níž. Otevři ho v textovém editoru, ne přes Clauda,
a hodnoty klíčů nikdy nevkládej do chatu.

**Po celou dobu buď v prohlížeči přihlášený jedním Google účtem**, tím, který má přístup do
vašeho Google Ads MCC. Ten účet bude vlastníkem Cloud projektu a stejným účtem se pak
přihlásíš v kroku 5. Když má Chrome víc profilů, otevři si ten správný a v něm zůstaň.

## Krok 1: Google Cloud projekt a zapnutí API

1. Otevři `console.cloud.google.com` a přihlas se účtem, který má přístup do vašeho Google Ads MCC.
2. Nahoře vlevo vedle loga Google Cloud klikni na výběr projektu a dej **New project**.
   Pojmenuj ho třeba `ppc-asistent`, organizaci nech, jak je, a potvrď **Create**.
3. Do vyhledávání nahoře napiš `Google Ads API`, otevři ji a dej **Enable**.

Tím projekt automaticky dostane úroveň přístupu **Test**. Ta pustí jen testovací účty, ostré
účty ještě ne. To vyřešíš v kroku 4.

## Krok 2: OAuth souhlas (tady je nejčastější past)

Cílem tohohle kroku je dostat aplikaci do stavu **In production**. Google tě tam nepustí,
dokud nemáš na stránce **Branding** vyplněné **čtyři** věci, ne dvě, jak se na první pohled zdá.

V menu jdi na **APIs & Services → OAuth consent screen**. Google tě přesměruje na stránku
**Google Auth Platform**, to je správně, tak se to dneska jmenuje.

### 2a. Branding: vyplň všechny čtyři věci najednou

V levém sloupci klikni na **Branding** a vyplň:

| Pole | Co tam dát |
|---|---|
| App name | název aplikace, např. `PPC asistent` |
| User support email | tvůj e-mail |
| Application home page | adresa tvého webu, např. `https://www.mojefirma.cz/` |
| Application privacy policy link | zásady ochrany osobních údajů na téže doméně, např. `https://www.mojefirma.cz/ochrana-osobnich-udaju` |

Pak sjeď níž na **Authorized domains**, dej `+ Add domain` a napiš svou doménu, např. `mojefirma.cz` (bez
`https://` a bez `www`). Google vyžaduje předregistrovat každou doménu, která se objeví
v odkazech výš. Kontroluje jen to, že doména v odkazech je v seznamu, ne že ji vlastníš.

**Application terms of service link**, **App logo** a zbytek nech prázdné, ty povinné nejsou.

Dej **Save**. Dole se ukáže potvrzení „Branding changes saved!".

> Do pole **App name** napiš jen ten název. Když si ho kopíruješ odsud, nevezmi s sebou číslo
> odrážky. V poli pak zůstane něco jako „1. PPC asistent", ten název vidí lidi na přihlašovací
> obrazovce a Google ho odmítne při ověření značky (krok 4b).

### 2b. Audience: publikuj aplikaci

1. V levém sloupci klikni na **Audience**. Tady je **User type: External** a hlavně
   **Publishing status**.
2. Zmáčkni tlačítko **Publish app** a potvrď. Stav se přepne na **In production**.

To je nejdůležitější věta celého návodu. Když necháš aplikaci ve stavu **Testing**, Google ti
vystaví refresh token s platností **7 dní** a přístup pak přestane fungovat. Nikdo ti to neřekne,
prostě to jednoho rána přestane.

> **Proč ta homepage a zásady ochrany osobních údajů.** Bez nich zůstane tlačítko **Publish app**
> šedivé a na stránce Audience svítí žlutá hláška „Your app's OAuth configuration is incomplete".
> Když na to šedivé tlačítko najedeš myší, Google sám napíše proč: *„Valid app name, support
> email, homepage url, and privacy policy url are required for switching the app to external
> production mode."* Na stránce Branding u těch dvou polí žádná hvězdička není, takže je člověk
> přeskočí a zasekne se o krok dál.

### 2c. Hláška „Your branding is not being shown to users"

Po publikování Google sám zkusí ověřit tvou značku a na stránce Branding se v sekci
**Verification status** objeví žlutý trojúhelník: *„Your branding is not being shown to users.
Resolve the following issues and verify again."* Pod **View issues** stojí, že doména
není ověřená tvým účtem a že název aplikace nesedí s webem.

**Tohle přístup k API neblokuje.** Znamená to jen, že se na přihlašovací obrazovce nezobrazí
logo a název, místo toho uvidíš obrazovku o neověřené aplikaci, kterou proklikneš (krok 5).
Token funguje normálně, protože aplikace je In production. Ověření značky potřebuješ až pro
úroveň Basic (krok 4b). Pokud ti stačí Explorer, dialog zavři přes **Cancel** a nevracej se k němu.

Nehledej položku „OAuth consent screen" jako samostatnou stránku. Google to rozdělil na
**Branding** (název, e-mail, odkazy), **Audience** (typ uživatele a publikování) a **Clients**
(přístupové údaje z kroku 3). Všechno je pod Google Auth Platform.

## Krok 3: OAuth klient (client ID + secret)

1. Ve stejné Google Auth Platform klikni v levém sloupci na **Clients** a dej **Create client**.
   Jde to i přes APIs & Services → Credentials → Create credentials. Tam se tě Google nejdřív
   zeptá, co chceš vytvořit: vyber **OAuth client ID** (ne „API key", ta neumí přístup k účtu,
   ani „Service account", ten je na server-to-server a tady by nefungoval).
2. Application type: **Desktop app**. (Ne „Web application". Přihlášení běží v prohlížeči na
   tvém počítači přes lokální smyčku a Google pro tenhle případ předepisuje Desktop app.)
3. Google ti ukáže **Client ID** a **Client secret**. Zkopíruj obojí do `.env`:

```
GOOGLE_ADS_CLIENT_ID=…
GOOGLE_ADS_CLIENT_SECRET=…
```

## Krok 4: Úroveň přístupu k API (nově v Cloud Console)

Tady se rozhoduje, jestli se dostaneš na ostré účty. Úroveň patří k projektu, ne k tobě ani
k MCC. Developer token už neexistuje, nikde ho nehledej.

### 4a. Požádej o Explorer

1. V Cloud Console otevři stránku **Google Ads API Overview**:
   `https://console.cloud.google.com/google/ads-apis/overview?project=ppc-asistent`
   (místo `ppc-asistent` dej ID svého projektu; ID vidíš ve výběru projektu nahoře).
   Ručně: menu vlevo nahoře → **APIs & Services → Enabled APIs & services → Google Ads API**.
2. Nahoře je **Current access level**. Po zapnutí API tam bude **Test**.
3. Rozbal sekci **Upgrade access level**. U **Next access level** má být **Explorer**.
4. Klikni **Apply for access**. Google podle dokumentace často povýší automaticky, bez čekání
   na schválení. Obnov stránku, dokud se u Current access level neukáže **Explorer**.

Tím máš hotovo. Do `.env` ještě přidej číslo MCC:

```
GOOGLE_ADS_LOGIN_CUSTOMER_ID=0000000000
```

`LOGIN_CUSTOMER_ID` je číslo správcovského (MCC) účtu vpravo nahoře v Google Ads, jen číslice,
bez pomlček. `GOOGLE_ADS_DEVELOPER_TOKEN` nech prázdný.

### Co která úroveň umí

| Úroveň | Ostré účty | Denní limit operací | Jak ji získáš |
|---|---|---|---|
| Test | ne | 15 000 (jen testovací účty) | automaticky po zapnutí API |
| Explorer | ano | 2 880 na ostrých účtech | Apply for access, obvykle hned |
| Basic | ano | 15 000 | ověřená značka (4b) + Apply for access |
| Standard | ano | bez limitu | manuální audit z úrovně Basic, cca 10 pracovních dní |

**Explorer stačí na všechno, co tahle aplikace dělá, kromě Keyword Planneru.** Umí čtení
reportů i zápisy na ostré účty: zakládání kampaní, sestav, klíčových slov, reklam, assetů,
změny rozpočtů a bidů, konverzní akce, publika. Zakázané jsou jen čtyři skupiny služeb:
zakládání účtů, správa uživatelů účtu, plánovací nástroje (Keyword Planner, Reach Planner,
Audience Insights) a fakturace. Z našich skriptů na to narazí jedině `keyword_ideas.py`.

Jak se počítají operace: jeden dotaz na report je jedna operace bez ohledu na velikost
výsledku, stránkování se nepočítá. Analýza jednoho klienta je řádově 10 až 20 dotazů. U zápisů
se počítá každá změna zvlášť, založení vyhledávací kampaně se třemi sestavami je řádově sto
operací. Limit 2 880 denně tedy vystačí na desítky účtů denně. Když ho přesáhneš, API vrátí
`RESOURCE_EXHAUSTED` a druhý den jede dál.

### 4b. Basic: jen když potřebuješ Keyword Planner nebo víc operací

Na stránce Google Ads API Overview se po získání Exploreru u **Next access level** ukáže
**Basic** a modrý rámeček: *„Brand Verification needs to be completed on your account to be
approved for Basic access."* Bez ověřené značky žádost neprojde, tak ji napřed vyřeš:

1. **Název aplikace.** Na stránce **Branding** oprav App name tak, aby byl přesně stejný jako
   název, pod kterým je aplikace popsaná na webu (viz bod 3). Bez odrážek, bez čísel.
2. **Vlastnictví domény.** Doménu z pole Application home page musí mít v **Google Search
   Console** ověřenou účet, který je v Cloud projektu **Owner** nebo **Editor**. Buď doménu ověř
   tímhle účtem (Search Console → Add property → Domain → TXT záznam v DNS), nebo v Cloud
   Console v **IAM** přidej jako Editora účet, který ji ověřenou už má.
3. **Stránka o aplikaci.** Domovská stránka musí aplikaci popisovat a nést stejný název jako
   App name. Běžná homepage firmy to nesplňuje, proto vytvoř stránku, třeba
   `https://www.mojefirma.cz/ppc-asistent`, a tu dej do pole Application home page.
4. Na stránce **Branding** klikni **View issues → I have fixed the issues → Proceed**. Google
   ověření zopakuje, výsledek uvidíš v sekci Verification status.
5. Až zmizí varování, vrať se na Google Ads API Overview a klikni **Apply for access**. Hláška
   *„Your application for basic level access is currently under review"* se vyřeší během minut.

**Klient bez vlastního webu** na Basic nedosáhne, protože nemá doménu, kterou by ověřil. Má
dvě možnosti: zůstat na Exploreru (pro běžnou práci stačí), nebo si pořídit doménu s jednou
stránkou o aplikaci a projít body 1 až 5. Přidávat cizí účet do svého Cloud projektu kvůli
ověřené doméně dává smysl jen u lidí z vlastní firmy, ne u externích klientů.

## Krok 5: Refresh token (spustíš sám jedním příkazem)

Teď máš v `.env` tři vyplněné hodnoty (client ID, client secret, MCC). Čtvrtou nemusíš nikde
hledat. Spusť sám v řádku zprávy Claude Code (proto ten vykřičník; skript otevře prohlížeč
a zapíše token do `.env`, takže ho nespouští Claude):

```
! .venv/bin/python scripts/google_ads/generate_refresh_token.py --write-env
```

Otevře se ti prohlížeč, přihlásíš se Google účtem, který má přístup do MCC, a odsouhlasíš
oprávnění. Protože značka není ověřená, ukáže se napřed obrazovka **„Google hasn't verified
this app"**. To je v pořádku, používáš ji jen ty: klikni na **Advanced** (Rozšířené) a pod ním
na **Go to PPC asistent (unsafe)**. Token se pak **sám zapíše do souboru** `.env` a nikde se
nevypíše. Nic nekopíruješ, nic nevkládáš. Stejný postup popisuje `docs/napojeni/google-ads.md`.

Ověř si, že to žije:

```
Vypiš mi účty pod MCC
```

Když Claude vrátí seznam účtů, máš hotovo a můžeš rovnou začít tvořit:

```
Založ mi vyhledávací kampaň pro účet 123-456-7890 na …
```

(místo `123-456-7890` dej číslo svého účtu z Google Ads, najdeš ho vpravo nahoře)

Claude si nejdřív účet projde, navrhne strukturu, klíčová slova i inzeráty a ukáže ti je ke
schválení. Do účtu nic nezapíše, dokud to neodsouhlasíš.

## Když to nejde

**Tlačítko „Publish app" je šedivé / hláška „Your app's OAuth configuration is incomplete"**
Na stránce Branding chybí **Application home page** nebo **Application privacy policy link**.
Nejsou označené hvězdičkou, ale bez nich se do produkce nedostaneš. Doplň je podle kroku 2a,
přidej doménu do Authorized domains, dej Save a vrať se na Audience.

**„Your branding is not being shown to users" / dialog „Branding verification issues"**
Neblokuje nic kromě loga na přihlašovací obrazovce a úrovně Basic. Zavři přes Cancel (krok 2c).
Řeš jen tehdy, když chceš Basic (krok 4b).

**V Google Ads v API Center píše „Přístup k rozhraní Google Ads API se změnil"**
Správně. Od 9. 9. 2026 se úroveň spravuje v Cloud Console, jdi na krok 4. Formulář, na který
odkazuje odstavec o App Conversion Tracking, je pro jiné API a Google Ads API přes něj nejde.

**Žádost o Basic „under review" a pak zamítnutá**
Značka není ověřená. Projdi krok 4b, body 1 až 4, a požádej znovu.

**„RESOURCE_EXHAUSTED"**
Vyčerpal jsi denní limit operací (2 880 na Exploreru). Počkej do dalšího dne, nebo přejdi na
Basic (krok 4b).

**Keyword Planner / `keyword_ideas.py` vrací chybu oprávnění**
Plánovací služby jsou na Exploreru zakázané. Potřebuješ Basic (krok 4b).

**„invalid_grant" nebo to přestalo fungovat po týdnu**
OAuth consent screen zůstal ve stavu Testing. Přepni na In production (krok 2b) a spusť
znovu příkaz z kroku 5 (`! .venv/bin/python scripts/google_ads/generate_refresh_token.py --write-env`).

**Prázdná data z ostrého účtu nebo chyba o úrovni přístupu**
Projekt je na úrovni Test. Požádej o Explorer (krok 4a). Pokud jsi projekt používal už před
9. 9. 2026 s developer tokenem, Google měl úroveň přenést automaticky. Přenesl ji jen
projektům, které v posledních 90 dnech přes API něco dělaly, a projekt bez provozu 90 dní
o úroveň zase přijde.

**„USER_PERMISSION_DENIED"**
Google účet, kterým ses přihlásil v kroku 5, nemá přístup do toho MCC. Odhlas se z něj
v prohlížeči, přihlas se tím správným a spusť příkaz z kroku 5 znovu.

**„CUSTOMER_NOT_FOUND"**
V `LOGIN_CUSTOMER_ID` máš pomlčky nebo číslo klienta místo čísla MCC.

**V Cloud Console „You need additional access to the project"**
Jsi přihlášený jiným Google účtem, než který projekt založil. Přepni profil v Chromu.

## Tři pravidla, která ti ušetří průšvih

1. `.env` nikdy nikam neposílej, ani do Gitu, ani na Disk, ani do chatu. Je v `.gitignore`, tak to
   tak nech.
2. **ID účtů klientů do .env nepatří.** Předávají se skriptům jako argument.
3. Token je heslo k účtu, kde tečou peníze. Když ti unikne, zruš ho na straně platformy
   a vygeneruj nový.

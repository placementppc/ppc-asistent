# Google Ads API: ověření značky a vyšší úroveň přístupu (Basic)

> Návod pro klienta. Tři kroky, klikání v prohlížeči, žádný terminál. Celou dobu buďte
> přihlášení **stejným Google účtem**, kterým jste zakládali projekt v Google Cloud.

Google od 9. 9. 2026 dává vyšší úroveň přístupu k Google Ads API (**Basic**) jen projektům,
které mají **ověřenou značku**. Ověření značky znamená, že Google ví, komu patří web uvedený
u aplikace, a že se název aplikace shoduje s tím, co je na webu. Bez toho zůstane projekt na
úrovni **Explorer** (2 880 operací denně, bez Keyword Planneru). Pro běžnou práci to stačí,
Basic řešte, až budete narážet na limit nebo potřebovat plánovač klíčových slov.

Budete potřebovat:

- **vlastní doménu** (web), ke které máte přístup do DNS nebo na FTP, a
- na tomto webu **jednu stránku o aplikaci** (viz krok 2, bod 3).

Bez vlastní domény ověření nejde udělat a projekt zůstane na Exploreru.

---

## Krok 1: Ověřte doménu v Google Search Console

1. Otevřete `https://search.google.com/search-console` a přihlaste se stejným účtem jako
   do Google Cloud.
2. Vlevo nahoře klikněte na výběr služby a dole na **Přidat službu**.
3. Zvolte typ **Doména** (vlevo, ne „Předpona adresy URL") a zadejte doménu bez `https://`
   a bez `www`, například `mojefirma.cz`. Potvrďte **Pokračovat**.
4. Google ukáže **TXT záznam** (řetězec začínající `google-site-verification=`). Zkopírujte ho.
5. Přihlaste se tam, kde spravujete DNS domény (registrátor domény, hosting, Active24,
   Wedos, Forpsi apod.), a do DNS přidejte nový záznam typu **TXT** s hodnotou z bodu 4.
   Název záznamu nechte na kořeni domény (obvykle `@` nebo prázdné pole).
6. Vraťte se do Search Console a klikněte **Ověřit**. DNS se může šířit i hodinu, když to
   napoprvé neprojde, zkuste to za chvíli znovu.

Hotovo, když Search Console ukáže „Vlastnictví ověřeno".

> Pokud doménu ověřil v Search Console jiný účet (třeba správce webu), je jednodušší přidat
> ten účet do projektu v Google Cloud: `https://console.cloud.google.com/iam-admin/iam` →
> **Udělit přístup** → e-mail účtu → role **Editor**. Google pak uzná jeho ověření.

---

## Krok 2: Doplňte údaje o aplikaci v Google Cloud

Otevřete `https://console.cloud.google.com/auth/branding` a nahoře ve výběru projektu
vyberte projekt, ve kterém máte Google Ads API. Na stránce **Branding** zkontrolujte a
doplňte:

1. **App name**: název aplikace, například `PPC asistent`. Jen název, bez čísel a odrážek.
   Přesně tenhle název musí být i na stránce z bodu 3.
2. **Application home page**: adresa stránky na vaší doméně, která aplikaci popisuje,
   například `https://www.mojefirma.cz/ppc-asistent`. Homepage webu nestačí, Google chce
   stránku, kde je aplikace popsaná.
3. **Ta stránka musí existovat.** Stačí pár vět: název aplikace stejný jako App name, k čemu
   slouží (správa a analýza reklamních kampaní v Google Ads přes API) a kdo ji provozuje.
4. **Application privacy policy link**: odkaz na zásady ochrany osobních údajů na téže
   doméně, například `https://www.mojefirma.cz/ochrana-osobnich-udaju`. Stránka musí
   existovat.
5. **Authorized domains**: níže na stránce musí být vaše doména bez `https://` a bez `www`,
   například `mojefirma.cz`. Když tam chybí, přidejte ji přes **+ Add domain**. Jiné domény,
   které tam případně zůstaly z dřívějšího nastavení, můžete smazat.
6. Dole klikněte **Save**.

Pak vpravo v sekci **Verification status**:

7. Klikněte **View issues**, zvolte **I have fixed the issues** a potvrďte **Proceed**.
8. Google ověření spustí sám. Výsledek se objeví na stejném místě, obvykle do několika minut,
   někdy do pár dnů. Hotovo, když žlutý trojúhelník s textem „Your branding is not being shown
   to users" zmizí.

Když ověření znovu selže, Google pod **View issues** napíše proč. Nejčastěji: doména není
ověřená účtem, který je v projektu Owner nebo Editor (krok 1), nebo název aplikace nesedí
s tím, co je na stránce (krok 2, body 1 a 3).

---

## Krok 3: Požádejte o úroveň Basic

1. Otevřete `https://console.cloud.google.com/google/ads-apis/overview` a nahoře vyberte
   stejný projekt.
2. Nahoře vidíte **Current access level**, teď **Explorer**.
3. Rozbalte **Upgrade access level**. U **Next access level** je **Basic**. Modrý rámeček
   o Brand Verification už by tam být neměl. Pokud tam je, ověření z kroku 2 ještě neprošlo,
   nežádejte, žádost by Google zamítl.
4. Klikněte **Apply for access**.
5. Objeví se „Your application for basic level access is currently under review". Za pár
   minut stránku obnovte. Hotovo, když u Current access level svítí **Basic**.

Přijde vám i e-mail s rozhodnutím. Zamítnutí s textem „Basic Access requires a successfully
verified OAuth brand profile" znamená, že ověření z kroku 2 ještě neprošlo. Dokončete ho a
požádejte znovu, na současný přístup to nemá vliv.

---

## Co se změní

- Denní limit stoupne z 2 880 na 15 000 operací.
- Začne fungovat Keyword Planner přes API (návrhy klíčových slov a hledanost).
- Nic dalšího nastavovat nemusíte, přístupy v `.env` zůstávají stejné.

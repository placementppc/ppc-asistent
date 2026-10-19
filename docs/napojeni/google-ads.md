# Napojení: Google Ads

> Pět kroků, asi 20 minut. Ověřeno v dokumentaci Google Ads API 19. 10. 2026
> (developers.google.com/google-ads/api/docs/api-policy/access-levels).
> Názvy položek v Google Cloud Console se mění, když nějakou nenajdeš, hledej podle smyslu.

## Co se změnilo 9. 9. 2026

Google **zrušil developer tokeny** („Developer tokens were sunset on September 9, 2026").
Úroveň přístupu k API už nepatří k MCC účtu, ale ke **Google Cloud projektu**, ze kterého
pochází tvůj OAuth klient. Proměnnou `GOOGLE_ADS_DEVELOPER_TOKEN` nech prázdnou, skripty
ji nepotřebují.

## Co potřebuješ

- Google účet s přístupem do **MCC** (správcovského účtu), pod kterým jsou účty klientů.
  Bez MCC to jde taky, pak je „MCC" přímo ten jeden účet.
- 2FA na tom Google účtu.
- Web s veřejnou stránkou zásad ochrany osobních údajů (vyžaduje ho publikování aplikace).

Celou dobu buď v prohlížeči přihlášený **jedním** Google účtem, tím s přístupem do MCC.

## Krok 1: Cloud projekt a zapnutí API

1. Otevři `console.cloud.google.com`, vlevo nahoře výběr projektu → **New project**.
   Pojmenuj ho třeba `ppc-asistent` → **Create**.
2. Do vyhledávání napiš `Google Ads API` → **Enable**.
   Projekt tím automaticky dostane úroveň **Test** (jen testovací účty).
3. Když budeš chtít GA4, zapni rovnou i **Google Analytics Data API** a
   **Google Analytics Admin API** (viz `docs/napojeni/ga4.md`).

## Krok 2: OAuth souhlas (nejčastější past)

**APIs & Services → OAuth consent screen** tě pošle do **Google Auth Platform**.

1. **Branding**: vyplň **všechny čtyři** pole, i když dvě nemají hvězdičku:
   App name (např. `PPC asistent`), User support email, **Application home page**,
   **Application privacy policy link**. Do **Authorized domains** přidej doménu z odkazů
   (bez `https://` a `www`). → **Save**.
2. **Audience**: User type **External** → **Publish app** → stav **In production**.

Proč na tom záleží: v režimu **Testing** vydá Google refresh token jen na **7 dní** a pak to
jednoho rána přestane fungovat. Tlačítko Publish je šedivé, dokud chybí homepage nebo zásady
ochrany údajů (podle hlášky v Cloud Console, kterou autor návodu viděl; neověřeno v dokumentaci).

Žlutá hláška „Your branding is not being shown to users" přístup k API **neblokuje**. Řeší se
jen kvůli úrovni Basic (krok 4).

## Krok 3: OAuth klient

1. Google Auth Platform → **Clients → Create client**.
2. Application type: **Desktop app** (ne Web application, ne Service account, ne API key).
3. Do `.env` vlož:
   ```
   GOOGLE_ADS_CLIENT_ID=
   GOOGLE_ADS_CLIENT_SECRET=
   ```

## Krok 4: úroveň přístupu (v Cloud Console)

Cloud Console → **APIs & Services → Enabled APIs & services → Google Ads API**, stránka
**Google Ads API Overview** → **Upgrade access level** → **Apply for access**.

| Úroveň | Ostré účty | Operací za den | Jak |
|---|---|---|---|
| Test | ne | 15 000 (jen testovací) | automaticky po zapnutí API |
| Explorer | ano | 2 880 | Apply for access, kontrola obvykle automatická |
| Basic | ano | 15 000 | nutné **ověření značky** projektu + Apply for access |
| Standard | ano | bez denního limitu | ruční audit Googlu, asi 10 pracovních dní |

**Explorer stačí na čtení reportů, hlídače i běžné zápisy.** Plánovací nástroje
(Keyword Planner → `scripts/google_ads/keyword_ideas.py`) na Exploreru nefungují, potřebuješ
Basic (podle zkušenosti autora; seznam omezených služeb ověř v dokumentaci access levels).
Jeden report = jedna operace bez ohledu na velikost, analýza klienta je řádově 10 až 20 operací.

Pak do `.env` číslo MCC, jen číslice bez pomlček:
```
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
```

## Krok 5: refresh token

Potřebuje vyplněné `GOOGLE_ADS_CLIENT_ID` a `GOOGLE_ADS_CLIENT_SECRET`. Spusť sám (otevře
prohlížeč a zapíše token do `.env`, proto ho nespouští Claude):

```
! .venv/bin/python scripts/google_ads/generate_refresh_token.py --write-env
```

Přihlas se účtem s přístupem do MCC. Obrazovku „Google hasn't verified this app" proklikni
přes **Advanced → Go to … (unsafe)**, aplikaci používáš jen ty. Token dostane oprávnění
`adwords` a `analytics.readonly` (GA4).

## Ověření (jen čte)

```bash
.venv/bin/python scripts/google_ads/fetch.py --list-clients
```

Vrátí seznam účtů pod MCC. Customer ID klientů si zapiš do `clients/<klient>.md`, ne do `.env`.

## Druhý MCC (volitelné)

Když máš účty pod dvěma MCC z různých Cloud projektů, přidej druhou sadu s vlastním názvem
profilu, např. `DRUHY`:

```
GOOGLE_ADS_DRUHY_CLIENT_ID=
GOOGLE_ADS_DRUHY_CLIENT_SECRET=
GOOGLE_ADS_DRUHY_REFRESH_TOKEN=
GOOGLE_ADS_DRUHY_LOGIN_CUSTOMER_ID=
```

Skripty ji použijí s `GOOGLE_ADS_PROFILE=druhy` před příkazem
(`GOOGLE_ADS_PROFILE=druhy .venv/bin/python scripts/google_ads/fetch.py --list-clients`),
refresh token vygeneruješ stejně. V `clients/hlidac-ucty.json` má takový účet pole
`"profil": "druhy"`. GA4 skript profily nezná, čte vždy výchozí `GOOGLE_ADS_*`.

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| `invalid_grant`, přestalo to po týdnu | aplikace zůstala v režimu Testing | krok 2 → Publish app, pak znovu krok 5 |
| Publish app je šedivé | chybí homepage nebo zásady ochrany údajů | krok 2, bod 1 |
| prázdná data / chyba úrovně přístupu | projekt je na úrovni Test | krok 4 → Explorer |
| `USER_PERMISSION_DENIED` | token je z účtu bez přístupu do MCC | přihlas se správným účtem, krok 5 znovu |
| `CUSTOMER_NOT_FOUND` | v `LOGIN_CUSTOMER_ID` jsou pomlčky nebo číslo klienta | jen číslice MCC |
| `RESOURCE_EXHAUSTED` | vyčerpaný denní limit operací | počkej do zítřka, nebo Basic |
| Keyword Planner hlásí oprávnění | plánovací služby na Exploreru nejedou | Basic (ověření značky) |
| „You need additional access to the project" | jiný Google účet v prohlížeči | přepni profil |

Projekt bez provozu přes API **90 dní** může o úroveň přístupu přijít (podle zkušenosti
autora s přechodem z developer tokenů; neověřeno v dokumentaci).

## Bezpečnost

- Client secret a refresh token jsou heslo k účtu, kde tečou peníze. Jen v `.env`.
- Únik: Google Auth Platform → Clients → klient → smaž secret / klienta a vytvoř nový,
  pak znovu krok 5. Odvolání přístupu aplikace: myaccount.google.com → Zabezpečení →
  aplikace třetích stran (přesný název položky neověřen).
- Limity API a pravidla zápisů: `knowledge/api-limity-bezpecnost.md`.

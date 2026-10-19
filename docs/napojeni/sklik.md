# Napojení: Sklik

> Jeden token, pár minut. Dokumentace API: api.sklik.cz/drak (ověřeno 19. 10. 2026:
> přihlášení metodou `client.loginByToken`, spravované účty přes `client.get` → `foreignAccounts`).

## Co potřebuješ

- Seznam účet s přístupem do Skliku. 2FA na Seznam účtu.
- Agentura: přístup ke klientským účtům (klient tě v Skliku pozve jako správce). Pak stačí
  **jeden** token tvého účtu a klientské účty se adresují číslem (`--user-id`).

## Krok za krokem

1. Přihlas se do Skliku tím účtem, přes který spravuješ klienty.
2. Najdi sekci pro **přístup k API** a vygeneruj **API token**.
   Přesnou cestu v menu jsme v oficiální dokumentaci nenašli; podle zkušenosti je
   v nastavení účtu (Nastavení → Přístup k API). **Neověřeno**, rozhraní se mění.
3. Token vlož do `.env`:
   ```
   SKLIK_API_TOKEN=
   ```
4. ID klientských účtů (userId) zjistíš ověřovacím příkazem níž a zapíšeš do
   `clients/<klient>.md`, ne do `.env`.

## Ověření (jen čte)

```bash
.venv/bin/python scripts/sklik/fetch.py --call client.get
```

Vrátí tvůj účet a v `foreignAccounts` účty, které spravuješ (jejich `userId` patří do
`clients/<klient>.md` a do `clients/hlidac-ucty.json` jako `id`). Kampaně konkrétního účtu:

```bash
.venv/bin/python scripts/sklik/fetch.py --user-id 123456 campaigns
```

## Víc tokenů (volitelné)

Když se některý účet čte jiným tokenem (jiná agentura, jiný Seznam účet), přidej do `.env`
druhou proměnnou s vlastním názvem, např. `SKLIK_DRUHY_TOKEN=`. Skriptu pak předáš jen
**název** proměnné, nikdy hodnotu:

```bash
SKLIK_TOKEN_VAR=SKLIK_DRUHY_TOKEN .venv/bin/python scripts/sklik/fetch.py --call client.get
```

V `clients/hlidac-ucty.json` má takový účet pole `"token_var": "SKLIK_DRUHY_TOKEN"`.

## NDA klient v režimu anonymizace

```bash
.venv/bin/python scripts/sklik/fetch.py --user-id 123456 campaigns --anon muj-eshop
```

Bez `--anon` skript NDA účet v aplikaci Claude nepustí (viz `docs/nda-rezim.md`).

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| HTTP 401 / chyba přihlášení | token neplatný nebo zrušený | vygeneruj nový, přepiš řádek v `.env` |
| 403 u konkrétního `--user-id` | tvůj token k účtu nemá přístup | ověř pozvánku od klienta, nebo použij správný token (`SKLIK_TOKEN_VAR`) |
| HTTP 429 | překročený limit dotazů | skripty čekají a zkusí znovu; neběž víc skriptů naráz |
| prázdný `foreignAccounts` | účty nejsou spravované tvým účtem | klient tě musí přidat jako správce |

Limity dotazů vrací metoda `api.limits` (minutový a denní limit, limity dávek; podle
`scripts/README.md`, v oficiální dokumentaci jsme to neověřovali). Pravidla
v `knowledge/api-limity-bezpecnost.md`. Kontrolní metody končící na `check` jsou podle
dokumentace levnější než zápisové, proto zápisové skripty jedou nejdřív přes ně (dry-run).

## Bezpečnost

- Token dává přístup ke všem účtům, které spravuješ, včetně zápisu. Jen v `.env`.
- Únik: v Skliku token zneplatni / vygeneruj nový (stejné místo jako krok 2) a přepiš `.env`.

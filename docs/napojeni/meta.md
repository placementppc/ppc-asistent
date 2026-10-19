# Napojení: Meta Ads (Facebook, Instagram)

> Token systémového uživatele v Business Manageru. Ověřeno v dokumentaci Meta Marketing API
> 19. 10. 2026 (developers.facebook.com/docs/marketing-api/system-users). Přesné názvy
> položek v Business Settings dokumentace neuvádí, proto jsou níž označené jako neověřené.

## Co potřebuješ

- **Business Manager** (Meta Business portfolio), ve kterém jsi admin. Podle dokumentace musí
  mít Business Manager jako admina skutečného člověka.
- **Aplikaci** na developers.facebook.com, která patří **stejnému** Business Manageru.
  Token systémového uživatele jde vydat jen pro aplikaci s přístupem k Marketing API
  na úrovni Standard (nebo po zařazení na allowlist).
- Reklamní účty klientů přidané do tvého Business Manageru (vlastní nebo partnerský přístup).
- 2FA na Facebook účtu a v Business Manageru.

## Krok za krokem

1. **Business Settings → Uživatelé → Systémoví uživatelé → Přidat** (cesta v menu neověřena).
   Vyber běžného systémového uživatele, ne admina. Dokumentace doporučuje admin systémového
   uživatele jen na správu a pro každý druh přístupu zvlášť běžného uživatele, ať únik
   jednoho tokenu nezasáhne všechno.
2. **Přiřaď prostředky**: reklamní účty klientů (na hlídače a analýzy stačí zobrazení výkonu,
   na zápisy správa kampaní). Na bannery a katalog i stránku a katalog (viz `knowledge/meta-ads.md`).
3. **Vygeneruj token** u systémového uživatele: vyber aplikaci a oprávnění.
   - jen čtení (hlídače, analýzy): `ads_read`
   - zápisy (zakládání kampaní, úpravy rozpočtů po schválení): `ads_management`
   - správa prostředků Business Manageru: `business_management` (jen když ji opravdu potřebuješ)
   Platnost: dokumentace nabízí token **bez expirace** nebo **60denní**, který je nutné obnovit,
   a jako bezpečnější doporučuje expirující. Na hlídače v cronu je praktičtější bez expirace,
   pak ho ale pravidelně ručně obměňuj.
4. Token vlož do `.env`:
   ```
   META_API_TOKEN=
   ```
   Volitelně `META_API_VERSION=` (výchozí ve skriptech `v21.0`; když Meta verzi vypne,
   doplň novější podle changelogu Graph API).

## Ověření (jen čte)

```bash
.venv/bin/python scripts/meta/fetch.py accounts
```

Vrátí reklamní účty, které token vidí (`act_…`, stav, měna). ID zapiš do `clients/<klient>.md`
a do `clients/hlidac-ucty.json`. Před stavbou kampaně v novém účtu projdi všechny předpoklady
najednou:

```bash
.venv/bin/python scripts/meta/preflight.py 1234567890   # číselné ID bez act_
```

## Typické chyby

| Hláška | Příčina | Co s tím |
|---|---|---|
| `accounts` vrací prázdno nebo účet chybí | systémový uživatel nemá účet přiřazený | krok 2 |
| chyba tokenu (neplatný, vypršel) | 60denní token vypršel nebo byl zneplatněn | krok 3, nový token (přesný kód chyby neověřen) |
| `#10` / `#200` permission | token nemá potřebné oprávnění nebo prostředek | doplň oprávnění (krok 3) nebo prostředek (krok 2) |
| zápis kreativy hlásí aplikaci ve vývoji | aplikace je v režimu Development | přepni aplikaci na Live (podle zkušenosti, `knowledge/meta-ads.md` § 15) |
| kódy 4 / 17 / 32 / 613, HTTP 429 | limit dotazů | skripty čekají a zkusí znovu; neběž víc skriptů naráz |

Víc chybových subkódů a co s nimi: `knowledge/meta-ads.md` (tabulka chyb při stavbě kampaní).

## Bezpečnost

- Na hlídače stačí `ads_read`. Token s `ads_management` umí měnit rozpočty a kampaně.
- Únik: v Business Settings u systémového uživatele token zneplatni (revoke) a vygeneruj nový.
  Jde i odebrat systémovému uživateli přiřazené účty.

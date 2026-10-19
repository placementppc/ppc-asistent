# Klient: <NÁZEV>

> Zdroj pravdy o klientovi. Aktualizuj při každém běhu. Skill se z tohoto souboru učí.

## 1. Profil
- **Web / e-shop:** <url>
- **Obor / sortiment:** <…>
- **Typ podnikání:** e-shop / leady / brand / lokální
- **TOP produkty / služby:** <…>
- **Marže / priority:** <…>
- **Sezónnost:** <kdy peak/útlum>
- **Konkurence / brand bidding:** <ano/ne, poznámky>
- **Čeho se vyvarovat:** <no-go, citlivé věci>

## 2. Cíle (KPI) — řídí všechna doporučení
- **Hlavní cíl:** <např. ROAS ≥ 800 % / CPA ≤ 250 Kč / max konverze v rozpočtu>
- **Vedlejší cíle:** <…>
- **Rozpočet:** <měsíční, flexibilita +/−>
- **Styl řízení:** senior konzervativní (default) | scaling | udržování
- **Aktualizováno:** <YYYY-MM-DD>

## 3. Účty a přístupy
- **NDA:** <true|false>
- **NDA režim:** <anonymizace | plna-data> (jen když NDA: true — viz `docs/nda-rezim.md`;
  plna-data = klientské soubory patří mimo repo do NDA složky a pracuje se jen v `./nda.sh`)
- **NDA účty:** <google:123-456-7890, sklik:…, meta:act_…, ga4:…> (jen NDA klienti; podle nich
  skripty poznají, že jde o NDA účet. Pokud musí zůstat tajná, patří do
  `clients/.secret/<klient>-account.json` jako klíče `*_id`.)
- **Google Ads customer ID:** <123-456-7890> (pod MCC)
- **Sklik account ID / userId:** <…>
- **Merchant Center / feed:** <…>
- **Měření konverzí:** <GA4 / Sklik konverze / import, poznámky k kvalitě dat>

## 4. Struktura účtu (aktuální obraz)
> Stručná mapa kampaní/sestav, strategie, rozpočtů. Aktualizuj při změnách.

| Kampaň | Typ | Strategie | Rozpočet | Cíl (tCPA/tROAS) | Pozn. |
|---|---|---|---|---|---|
| | | | | | |

## 5. Baseline výkonnost (snapshot)
> Referenční čísla pro srovnání. Doplň datum a období.

| Datum | Období | Útrata | Konverze | CPA | Hodnota | ROAS | Pozn. |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 6. Changelog změn (learning loop) 🧠
> Každá schválená změna sem. Status: 🟡 čeká na vyhodnocení / 🟢 vyhodnoceno / ⏳ málo dat.
> Při dalším běhu vyhodnocuj 🟡 položky dle `knowledge/vyhodnoceni-zmen.md`.

### YYYY-MM-DD — <krátký název změny>  [🟡 čeká na vyhodnocení]
- **Objekt:** <kampaň / sestava / KW / reklama>
- **Co provedeno:** <konkrétně>
- **Proč (hypotéza):** <datová opora + co čekám>
- **Očekávaný dopad:** <metrika a směr>
- **Baseline (před):** <útrata, CPA/ROAS, objem, podíl zobrazení…>
- **Vyhodnotit po:** <YYYY-MM-DD + min. objem dat>
- **Schválil:** <uživatel> dne <datum>
- **— Vyhodnocení (doplň později):** <skutečný dopad vs. očekávaný • závěr ✅/❌/➖ • poučení>

## 7. A/B testy a experimenty
> Hypotéza, varianty, úspěšná metrika, start, plán vyhodnocení, výsledek, závěr.

### YYYY-MM-DD — <název testu>  [stav]
- **Hypotéza:** <…>  • **Varianty:** A=<…> / B=<…>
- **Úspěšná metrika:** <CTR / konv. poměr / CPA>  • **Vyhodnotit po:** <…>
- **Baseline:** <…>  • **Výsledek / závěr / poučení:** <doplň>

## 8. Naučené vzorce u tohoto klienta (learnings)
> Co u TOHOTO klienta funguje / nefunguje. Obecné vzorce povyš do `knowledge/_learnings.md`.
- <datum — poučení (s čísly), jistota>

## 9. Otevřené úkoly / nápady do budoucna
- <…>

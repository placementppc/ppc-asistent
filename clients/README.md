# Klienti

**Tahle složka je soukromá.** Kromě tohoto README a šablon (`_TEMPLATE.md`) je celá v `.gitignore`
a do repozitáře nepatří nic z ní.

Pro každého klienta jeden soubor `clients/<slug>.md` vytvořený z `_TEMPLATE.md`.

- `<slug>` = krátký název bez diakritiky a mezer (např. `muj-eshop`).
- Soubor je **zdroj pravdy**: cíle, struktura účtu, baseline, changelog změn, A/B testy, learnings.
- Skill ho čte na začátku každého běhu a aktualizuje na konci.
- Index klientů (klient, slug, platformy, hlavní cíl, poslední běh) si veď v `clients/INDEX.md`.
  Je v `.gitignore` stejně jako profily klientů. **Do tohoto README nepiš nic o konkrétních klientech**,
  README se do repozitáře commituje.

## Než repo kamkoli pushneš

- Klientská data (ID účtů, cíle, rozpočty, changelogy, plány) **nikdy nesmí do veřejného repozitáře**.
- Repo s klienty drž jen jako **soukromé** (nový privátní repozitář, ne fork veřejného).
- Před každým `git push` zkontroluj `git status`, že ve staged souborech není nic z `clients/`
  kromě `README.md` a šablon. Když tam něco je, nepushuj a oprav `.gitignore`.

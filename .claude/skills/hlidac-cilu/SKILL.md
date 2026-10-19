---
name: hlidac-cilu
description: Hlídač cílů — denně nebo podle zvolené frekvence zkontroluje, jestli účty (Google Ads, Sklik, Meta) od poslední změny plní cíl klienta (PNO, ROAS, CPA, počet konverzí) a tempo měsíčního rozpočtu a obratu, a navrhne, co změnit. Použij, když uživatel řekne „plní účet cíle", „plníme cíle?", „jak jsme na tom s PNO", „od poslední změny", „vyhodnoť změnu", „drží se ROAS", „hlídač cílů", „co je potřeba změnit", nebo když ho spustí naplánovaná úloha. Jen čte, nic nemění.
---

# Hlídač cílů

Otázka: **„Plní účet od poslední změny cíl klienta? A když ne, co s tím?"**
Neodpovídá na „funguje účet?" — okno od změny je krátké a slouží jen k vyhodnocení té změny
(CLAUDE.md 4b). Proto report ke každému účtu přikládá 8 týdnů po týdnech.

**V účtech nic nemění.** Návrhy jsou pravidlové a konzervativní. Senior závěr z nich děláš ty.

## 1. Spuštění

```
python3 scripts/hlidac/cile.py                     # všechny účty s "cile" v poli hlidat
python3 scripts/hlidac/cile.py --klient muj-eshop  # jeden klient
python3 scripts/hlidac/cile.py --mesice 13         # + měsíční řada (sezóna, měřítko)
python3 scripts/hlidac/cile.py --json              # strojový výstup
python3 scripts/hlidac/cile.py --podle-planu       # pro cron: respektuje planovani.frekvence
```

- Konfigurace: `clients/hlidac-ucty.json` (skill `hlidac`, sekce 1). Účet potřebuje blok `cile`.
- Report: `reports/hlidac-cilu/<datum>.md`. Kód: 0 OK · 1 něco 🟡 · 2 něco 🔴 nebo chyba načtení.

## 2. Jak počítá

**Poslední změna:** `posledni_zmena` v konfiguraci → jinak nejnovější `### RRRR-MM-DD` v sekci
Changelog v `clients/<klient>.md` (sekce A/B testů se nepočítá) → jinak posledních 28 dní.
Proto: **každou schválenou změnu zapiš do changelogu klienta** (šablona `clients/_TEMPLATE.md`).

| Stav | Kdy |
|---|---|
| ⚪ málo dat | od změny < 7 dní (učící fáze) nebo < 30 konverzí — napíše, kolik dní počkat |
| 🟢 plní | KPI v cíli |
| 🟡 hraničně | do 10 % od cíle, nebo tempo rozpočtu/obratu mimo plán |
| 🔴 neplní | víc než 10 % od cíle, nula konverzí při 100+ proklicích, CPA: 3× cíl bez konverze |

Navíc: srovnání se stejně dlouhým obdobím **před** změnou (konverzní poměr se z-testem, p < 0,05
= významné) a tempo měsíce (`mesicni_rozpocet`, `mesicni_obrat`, lineární projekce).
Prahy: `scripts/hlidac/pravidla_cile.py` (`PRAHY`), podle `knowledge/vyhodnoceni-zmen.md`.

## 3. Z reportu senior návrh

1. **Zelené a bílé účty nerozebírej.** U ⚪ jen „počkej X dní".
2. **🔴 a 🟡 nejdřív ověř příčinu, pak navrhuj.** Pořadí jako ve skillu `anomalie`:
   měření (skill `mereni-audit`) → změny v účtu → web a nabídka → trh a sezóna → aukce.
   Report říká, kterým skillem to dořešit (`pmax-produkty`, `dotazy-vylouceni`,
   `tempo-rozpoctu`, `aukce-konkurence`, `reklama-vs-stranka`…). Spusť ho jen čtecími skripty.
3. **Když se cíl plnil před změnou a po ní ne**, vyhodnoť tu změnu podle
   `knowledge/vyhodnoceni-zmen.md` (keep / hold / rollback) a zapiš výsledek do changelogu.
4. **Nesuď účet z okna od změny.** Než navrhneš něco k rozpočtu nebo měřítku, podívej se na
   8 týdnů v reportu a dotáhni měsíční řadu za celou historii (`--mesice 13`, skill `perf`).
5. **Příčinu piš jen ověřenou.** Co nevíš, označ jako domněnku (CLAUDE.md tvrdé pravidlo 1).
6. **Každý zásah jen jako návrh**, s konkrétním číslem a dry-run příkazem apply skriptu.
   Bidding měň po krocích (tROAS / tCPA max ~10–15 %), nikdy víc věcí naráz.
7. **Když cíl plní s rezervou a rozpočet se nedočerpá**, nabídni růst: skill `hlidac-akci`.

## 4. Jak to poslat

Stručně: nahoře `🔴 1 · 🟡 2 · 🟢 5`, pod tím ke každému 🔴/🟡 účtu
2 řádky — co (číslo vs. cíl od data změny), ověřená příčina nebo „ověřuji", návrh jednou větou.
Detail a 8 týdnů nech v souboru reportu. Kam se report posílá: `docs/notifikace.md`.
Naplánování: `docs/nasazeni.md`, skill `nasazeni`.

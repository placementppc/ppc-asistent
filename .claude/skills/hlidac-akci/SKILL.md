---
name: hlidac-akci
description: Hlídač akcí — hledá prostor pro škálování v Google Ads, Skliku a Metě (kampaně a sady, které plní cíl s rezervou a brzdí je rozpočet), i v pátek večer a o víkendu, kdy už nikdo nepracuje. Ke každému návrhu řekne o kolik přidat v limitech, proč, riziko a hotový dry-run příkaz; o víkendu hlídá i riziko přečerpání. Použij, když uživatel řekne „kde přidat", „škálování", „prostor pro růst", „můžu přidat rozpočet", „co je omezené rozpočtem", „pátek večer", „víkendový hlídač", „pohlídej víkend", „hlídač akcí". Jen navrhuje a posílá, nic nemění.
---

# Hlídač akcí

Otázka: **„Kde teď necháváme peníze ležet — a je bezpečné přidat?"**
Hlídač **jen navrhuje a posílá**. Nic nezapisuje, apply skripty nespouští. Plány, které připraví,
jsou neschválené; zápis je vždy dry-run → schválení člověkem → `--apply` (CLAUDE.md #1).

## 1. Spuštění

```
python3 scripts/hlidac/akce.py              # posledních 14 dní do včerejška
python3 scripts/hlidac/akce.py --dnes       # ~18:00: kdo už dnes vyčerpal rozpočet a má výkon
python3 scripts/hlidac/akce.py --vikend     # pátek večer → pondělí: menší kroky + rizika
python3 scripts/hlidac/akce.py --vikend --dnes   # pátek 18:00: obojí
python3 scripts/hlidac/akce.py --klient muj-eshop --json
```

- Konfigurace: `clients/hlidac-ucty.json` (skill `hlidac`, sekce 1). Účet potřebuje `cile`,
  v `hlidat` hodnotu `akce` a ideálně `limity` a `cile.mesicni_rozpocet`.
- Report: `reports/hlidac-akci/<datum>.md` (`-vecer`, `-vikend`). Plány pro apply skripty:
  `reports/hlidac-akci/plany/`. Kód: 0 nic · 1 návrhy nebo víkendová rizika · 2 chyba načtení.
- Sklik se s `--dnes` nekontroluje (neověřené, jak rychle plní dnešní data).

## 2. Kdy navrhne navýšení (vše najednou)

1. **Brzdí ji rozpočet** (14 dní):
   - Google: `search_budget_lost_impression_share` ≥ 10 %, nebo stav kampaně omezený rozpočtem,
     nebo útrata ≥ 90 % rozpočtu aspoň v polovině dní;
   - Sklik: útrata ≥ 90 % denního rozpočtu aspoň v polovině dní (pole „ztráta kvůli rozpočtu"
     ve Sklik API není ověřené, proto se nepoužívá);
   - Meta: totéž u sady (nebo kampaně s rozpočtem kampaně) a frekvence za 7 dní ≤ 3.
2. **Plní cíl s rezervou ≥ 10 %** (PNO, ROAS, CPA; u cíle „konverze" CPA lepší než průměr účtu)
   při aspoň 15 konverzích za 14 dní.
3. **Limity pustí aspoň +5 %**: max krok `limity.max_navyseni_pct` (o víkendu max 10 %),
   týdenní strop `max_navyseni_tyden_pct` proti nejnižšímu rozpočtu za 7 dní (hlídač si rozpočty
   pamatuje v `reports/hlidac-akci/rozpocty.json`), strop součtu rozpočtů `max_denni_rozpocet`
   a zbytek `mesicni_rozpocet` na zbývající dny. Rezervu účtu dostanou nejdřív nejlepší kampaně.

Prahy: `scripts/hlidac/pravidla_akce.py` (`PRAHY`). Kampaně, které těsně neprošly, jsou
v reportu zvlášť (např. „brzdí ji rozpočet, ale PNO nad cílem" nebo „frekvence 3,6 → skill `meta-strop`").

**Víkend (`--vikend`)**: nikdo nebude reagovat, proto poloviční krok a navíc rizika do pondělí —
denní rozpočty × 3 dny proti zbytku měsíčního rozpočtu (Google může v jednom dni utratit až 2×
průměrného denního rozpočtu) a kampaně, které čerpají celý rozpočet a cíl neplní.

## 3. Jak se návrh provede (po schválení)

| Systém | Plán | Náhled (nic nezapíše) | Zápis |
|---|---|---|---|
| Google | `set_budget` pro `scripts/google_ads/apply_changes.py` | `apply_changes.py <id> <plán>` (+ `--validate`) | `--apply` |
| Meta | `changes[].params.daily_budget` pro `scripts/meta/apply.py`, `approval: pending` | `apply.py <plán>` (+ `--validate`) | `approval.status: approved` + `--apply` |
| Sklik | — (skript na rozpočty v repu není, apply skripty rozpočty záměrně odmítají) | — | ručně v Skliku |

Meta `daily_budget` je v nejmenší jednotce měny (CZK × 100); hlídač to přepočítá podle měny účtu.

## 4. Z reportu senior návrh

1. **Ověř, že brzdí opravdu rozpočet, ne pozice.** U Google search porovnej ztrátu kvůli
   rozpočtu a kvůli pořadí (skill `aukce-konkurence`, `knowledge/heuristiky-toprank.md`).
   Když je ztráta hlavně kvůli pořadí, přidání rozpočtu nepomůže.
2. **Ověř, že výkon není jen šum nebo atribuce.** Remarketing a katalog si umí výkon nafouknout
   (skill `konverze-vs-ga4`). U Mety strop škálování skillem `meta-strop`.
3. **Podívej se na 8 týdnů a sezónu** (skill `perf`), ne jen na 14 dní. Před výprodejem/svátkem
   je navýšení jiná otázka než v útlumu.
4. **Jeden krok, jedna změna.** Žádné navyšování všeho naráz. Po 7–14 dnech vyhodnotit
   (`knowledge/vyhodnoceni-zmen.md`) a zapsat do changelogu klienta.
5. **Pošli stručně:** „💡 Můj e-shop: Search obecné 1 000 → 1 200 Kč/den. PNO 8 % vs. cíl 15 %,
   ztrácí 23 % zobrazení kvůli rozpočtu. Riziko: … Schválit?" + dry-run příkaz. Kam se posílá:
   `docs/notifikace.md`. Naplánování (pátek 18:00, víkend): `docs/nasazeni.md`, skill `nasazeni`.
6. **Bez schválení nic nespouštěj — ani v pátek večer.** Když nikdo neodpoví, nic se neděje.

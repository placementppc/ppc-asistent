# Vyhodnocení změn — prahy a metodika (learning loop)

Cíl: poctivě poznat, jestli změna zafungovala. Bez dostatku dat **nevyhodnocuj** — počkej.

## 🔴 Pravidlo č. 0 — VŽDY hodnoť v kontextu změny (okno OD změny)
**Než cokoli vyhodnotíš, zjisti z changelogu datum poslední relevantní změny daného objektu
a hodnoť POUZE okno od té změny dál.** Nikdy neposuzuj dopad změny přes dlouhé/celé období,
které tu změnu zahrnuje — data před změnou a smíchaná s obdobím po ní jsou pro posouzení změny
bezcenná a zavádějící.
- Měnila se struktura (nové sestavy/kampaně, split, rozdělení produktů)? → „od spuštění/historie"
  je špatné okno. Relevantní je jen čas od změny (klidně jen pár dní — pak řekni „⏳ ještě málo dat").
- Než stáhneš data, vždy se zeptej sám sebe: *„Co a kdy se tu naposledy měnilo?"* a podle toho
  nastav období. Tohle je nejčastější chyba — pozor na ni.

## Kdy je změna připravená k vyhodnocení
Vyhodnocuj, až je splněno **oboje** (čas i objem):

| Strategie / cíl | Min. doba běhu | Min. objem dat |
|---|---|---|
| tCPA / max konverze (leady) | 14–21 dní | ≥ 30 konverzí v období po změně (ideálně 50) |
| tROAS / hodnota konverzí / e-shop | 14–28 dní | ≥ 50 konverzí nebo stabilní ROAS trend |
| Manual/eCPC, malý objem | 21–30 dní | dost prokliků, ať CTR/konv. poměr nejsou šum |
| Změna rozpočtu | 7–14 dní | po opuštění učící fáze |
| Vyloučení dotazů / negativa | 14 dní | porovnej podíl irelevantních dotazů a CPA |
| Reklama / A-B test (RSA, varianta) | 14–30 dní | ≥ 100 prokliků na variantu, ideálně konverze |

Pozn.: po zásahu do biddingu/rozpočtu počítej s **učící fází** (cca 7–14 dní) — data z ní neber jako finální.

## Jak vyhodnotit (postup)
> Výsledkové stavy keep/hold/rollback a guardrail definuj **před** změnou; bez předem daného prahu
> je výsledek „inconclusive", ne rollback. Falsifikační věta k návrhu. `heuristiky-toprank.md` § 5.

1. Vezmi z changelogu **baseline** (metriky před změnou) a **očekávaný dopad**.
2. Stáhni stejné metriky za období **po** změně (stejně dlouhé okno, pozor na sezónu/svátky).
3. Srovnej hlavní KPI dle cíle klienta:
   - Leady: CPA, počet konverzí, konv. poměr, útrata.
   - E-shop: ROAS, hodnota konverzí, PNO/náklady, počet objednávek.
   - Vždy kontext: objem (prokliky, imprese), podíl zobrazení, sezónnost.
4. Urči závěr: ✅ fungovalo / ❌ nefungovalo / ➖ neutrální / ⏳ ještě málo dat.
5. Napiš **poučení** (1–3 věty): co to znamená pro tohoto klienta / co příště.
6. Status změny v changelogu → `🟢 vyhodnoceno`. Learning případně povýš do `_learnings.md`.

## Na co dávat pozor (ať se neoklameš)
- **Atribuční zpoždění** — konverze dobíhají; krátké okno podhodnocuje.
- **Sezónnost a externí vlivy** — srovnávej s loňskem / předchozím obdobím, ne naslepo.
- **Souběžné změny** — když běží víc změn naráz, dopad nejde čistě přiřadit. Proto neměň vše najednou.
- **Statistická významnost** — malé rozdíly při malém objemu jsou šum. Konzervativně: bez dat nezávěruj.
- **Učící fáze** — nehodnoť strategii v prvních ~7–14 dnech po zásahu.

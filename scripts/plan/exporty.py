"""Převod ručních exportů z Google Ads, Mety, Skliku a GA4 na jeden formát pro forecast.

Pro ty, kdo nemají napojené API: stáhnou si denní report z rozhraní systému (CSV)
a tenhle skript ho převede na `datum, system, naklady, obrat, konverze, kliky`.
Jen čte soubory, na síť nesahá.

Co zvládne:
- české i anglické názvy sloupců (Den / Day, Náklady / Cost, Utracená částka / Amount spent…),
- úvodní řádky nad hlavičkou (název reportu, období) a komentáře `#` z GA4,
- řádky po kampaních → sečte je po dnech; řádky „Celkem“ přeskočí,
- datum 2025-11-28, 28. 11. 2025, 28.11.2025, 20251128 (GA4), 11/28/2025, Nov 28, 2025.

GA4 nemá náklady na reklamu (jen u napojeného Google Ads). Ukládá se jako systém `ga4`
a slouží jako křivka tržeb celého e-shopu (sezónnost), ne jako reklamní systém.

Použití:
  python3 scripts/plan/exporty.py --klient muj-eshop --google gads.csv --meta meta.csv --ga4 ga4.csv
  → plans/muj-eshop/historie.csv (reklamní systémy) + plans/muj-eshop/ga4.csv (e-shop celkem)
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
from model import Radek  # noqa: E402

# Kandidáti na sloupce po normalizaci (slug bez diakritiky, podtržítka). Pořadí = priorita.
SLOUPCE = {
    "datum": ["datum", "den", "day", "date", "zacatek_vykazovaneho_obdobi", "reporting_starts",
              "zacatek_reportovaciho_obdobi", "obdobi", "date_yyyymmdd"],
    "naklady": ["naklady", "cost", "cena", "celkova_cena", "utracena_castka_czk", "utracena_castka",
                "amount_spent_czk", "amount_spent", "spend", "naklady_na_reklamu", "ads_cost",
                "google_ads_cost", "naklady_czk", "cost_czk"],
    "obrat": ["hodnota_konv", "hodnota_konverzi", "conv_value", "conversion_value", "all_conv_value",
              "hodnota_konverze_nakupu", "purchases_conversion_value", "hodnota_konverzi_nakupu",
              "website_purchases_conversion_value", "hodnota_konverzi_czk", "obrat", "trzby",
              "celkove_vynosy", "total_revenue", "purchase_revenue", "vynosy_z_nakupu", "prijmy_z_nakupu",
              "vynosy", "revenue"],
    "konverze": ["konverze", "conversions", "nakupy", "purchases", "website_purchases", "transakce",
                 "transactions", "nakupy_na_webu", "klicove_udalosti", "key_events", "pocet_konverzi"],
    "kliky": ["prokliky", "kliky", "kliknuti", "clicks", "kliknuti_na_odkaz", "link_clicks", "relace",
              "sessions"],
}
MESICE_EN = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _norm(nazev: str) -> str:
    t = re.sub(r"\(.*?\)", lambda m: "_" + m.group(0)[1:-1], nazev or "")   # „(CZK)“ → „_CZK“
    return D.slug(t).replace("-", "_")


def parse_datum(text: str) -> date | None:
    """Datum v běžných formátech exportů. None, když to datum není (třeba řádek „Celkem“)."""
    t = (text or "").strip().strip('"')
    if not t:
        return None
    if re.fullmatch(r"\d{8}", t):
        try:
            return date(int(t[:4]), int(t[4:6]), int(t[6:]))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:                                 # Meta/Google v angličtině: MM/DD/YYYY
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", t)
    if m and m.group(1).lower() in MESICE_EN:
        return date(int(m.group(3)), MESICE_EN[m.group(1).lower()], int(m.group(2)))
    try:
        return datetime.fromisoformat(t[:10]).date()
    except ValueError:
        return None


def _cislo(text: str) -> float:
    t = re.sub(r"[^\d,.\-]", "", text or "")      # pryč měna, mezery, „%“
    if t in ("", "-", "--"):
        return 0.0
    return D._cislo(t)


def _dekoduj(cesta: Path) -> str:
    surove = cesta.read_bytes()
    for kod in ("utf-8-sig", "utf-16", "cp1250"):
        try:
            return surove.decode(kod)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"{cesta}: neznámé kódování (ulož jako CSV UTF-8).")


def najdi_sloupce(hlavicka: list[str]) -> dict[str, int]:
    norm = [_norm(h) for h in hlavicka]
    nalez: dict[str, int] = {}
    for cil, kandidati in SLOUPCE.items():
        for k in kandidati:                       # přesná shoda má přednost
            if k in norm:
                nalez[cil] = norm.index(k)
                break
        else:
            for k in kandidati:                   # pak začátek názvu („utracena_castka_eur“)
                idx = next((i for i, n in enumerate(norm) if n.startswith(k) and i not in nalez.values()), None)
                if idx is not None:
                    nalez[cil] = idx
                    break
    return nalez


def nacti_export(cesta: Path, system: str) -> list[Radek]:
    """Načte export jednoho systému a sečte ho po dnech."""
    if not cesta.exists():
        raise SystemExit(f"Soubor {cesta} neexistuje.")
    radky_textu = [r for r in _dekoduj(cesta).splitlines() if r.strip() and not r.lstrip().startswith("#")]
    if not radky_textu:
        raise SystemExit(f"{cesta}: prázdný soubor.")
    vzorek = "\n".join(radky_textu[:20])
    oddel = max([",", ";", "\t"], key=vzorek.count)
    tabulka = list(csv.reader(io.StringIO("\n".join(radky_textu)), delimiter=oddel))
    # hlavička = první řádek, ve kterém najdu sloupec s datem i aspoň jednu metriku
    for i, r in enumerate(tabulka[:30]):
        sl = najdi_sloupce(r)
        if "datum" in sl and len(sl) >= 2:
            hlavicka_idx, sloupce = i, sl
            break
    else:
        raise SystemExit(f"{cesta}: nenašel jsem hlavičku se dnem a čísly. Exportuj report „po dnech“ "
                         f"(sloupec Den / Day) se sloupci náklady, hodnota konverzí, konverze.")
    if system != "ga4" and "naklady" not in sloupce:
        raise SystemExit(f"{cesta}: chybí sloupec s náklady (Náklady / Cost / Utracená částka).")
    if "obrat" not in sloupce:
        raise SystemExit(f"{cesta}: chybí sloupec s hodnotou konverzí / tržbami. Přidej ho do reportu "
                         f"(Google: Hodnota konv., Meta: Hodnota konverze nákupů, GA4: Celkové výnosy).")
    po_dnech: dict[date, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for r in tabulka[hlavicka_idx + 1:]:
        if len(r) <= sloupce["datum"]:
            continue
        d = parse_datum(r[sloupce["datum"]])
        if d is None:                             # „Celkem“, „Total: Account“…
            continue
        for j, m in enumerate(("naklady", "obrat", "konverze", "kliky")):
            if m in sloupce and sloupce[m] < len(r):
                try:
                    po_dnech[d][j] += _cislo(r[sloupce[m]])
                except ValueError:
                    raise SystemExit(f"{cesta}: v řádku pro {d} není číslo ve sloupci {m}: {r[sloupce[m]]!r}")
    if not po_dnech:
        raise SystemExit(f"{cesta}: žádný řádek s datem. Je to report po dnech?")
    return [Radek(d, system, *v) for d, v in sorted(po_dnech.items())]


def sluc(stare: list[Radek], nove: list[Radek]) -> list[Radek]:
    """Nová data přepíšou stará pro stejný den a systém, zbytek zůstane."""
    klic = {(r.datum, r.system): r for r in stare}
    klic.update({(r.datum, r.system): r for r in nove})
    return sorted(klic.values(), key=lambda r: (r.datum, r.system))


def main() -> int:
    ap = argparse.ArgumentParser(description="Převede exporty z reklamních systémů a GA4 na historii pro forecast")
    ap.add_argument("--klient", required=True)
    ap.add_argument("--google", type=Path, help="CSV z Google Ads (report po dnech)")
    ap.add_argument("--meta", type=Path, help="CSV z Meta Ads Manageru (rozpad po dnech)")
    ap.add_argument("--sklik", type=Path, help="CSV ze Skliku (statistiky po dnech)")
    ap.add_argument("--ga4", type=Path, help="CSV z GA4 (datum + celkové výnosy + transakce)")
    a = ap.parse_args()
    zdroje = [(s, getattr(a, s)) for s in ("google", "meta", "sklik", "ga4") if getattr(a, s)]
    if not zdroje:
        ap.error("zadej aspoň jeden export (--google, --meta, --sklik, --ga4)")
    slozka = D.ROOT / "plans" / D.slug(a.klient)
    try:
        for system, cesta in zdroje:
            radky = nacti_export(cesta, system)
            cil = slozka / ("ga4.csv" if system == "ga4" else "historie.csv")
            stare = D.nacti_csv(cil) if cil.exists() else []
            D.uloz_csv(sluc(stare, radky), cil)
            print(f"{system}: {len(radky)} dní ({radky[0].datum} až {radky[-1].datum}), "
                  f"náklady {D_kc(sum(r.naklady for r in radky))}, obrat {D_kc(sum(r.obrat for r in radky))} "
                  f"→ {cil.relative_to(D.ROOT)}")
    except SystemExit as e:
        print(f"CHYBA: {e}", file=sys.stderr)
        return 2
    return 0


def D_kc(x: float) -> str:
    return f"{x:,.0f} Kč".replace(",", " ")


if __name__ == "__main__":
    sys.exit(main())

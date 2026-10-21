"""Testy plánu Black Friday (scripts/plan/bf_plan.py) a převodu exportů (scripts/plan/exporty.py). Bez sítě.

Spuštění: python3 -m pytest tests/test_bf_plan.py -q   (nebo bez pytestu: python3 tests/test_bf_plan.py)
"""
from __future__ import annotations

import math
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "plan"))
import bf_plan as B  # noqa: E402
import data as D  # noqa: E402
import exporty as E  # noqa: E402

UKAZKA = ROOT / "scripts" / "plan" / "ukazka-data.csv"


def _soubor(text: str, kodovani: str = "utf-8") -> Path:
    f = tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False)
    f.write(text.encode(kodovani))
    f.close()
    return Path(f.name)


def test_black_friday_data():
    assert B.black_friday(2025) == date(2025, 11, 28)
    assert B.black_friday(2026) == date(2026, 11, 27)
    assert B.black_friday(2027) == date(2027, 11, 26)


def test_export_google_cz_s_nadpisem_a_celkem():
    p = _soubor("Přehled kampaní\n1. listopadu 2025 - 2. listopadu 2025\n"
                "Den,Kampaň,Náklady,Hodnota konv.,Konverze,Prokliky\n"
                "2025-11-01,A,\"1 200,50\",\"8 000,00\",4,100\n"
                "2025-11-01,B,300,1000,1,20\n"
                "2025-11-02,A,500,2000,2,40\n"
                "Celkem: účet,,\"2 000,50\",11000,7,160\n")
    radky = E.nacti_export(p, "google")
    assert [r.datum for r in radky] == [date(2025, 11, 1), date(2025, 11, 2)]
    assert math.isclose(radky[0].naklady, 1500.5)
    assert radky[0].obrat == 9000 and radky[0].konverze == 5 and radky[0].kliky == 120


def test_export_meta_cz_strednik_a_cesky_datum():
    p = _soubor("Začátek vykazovaného období;Konec vykazovaného období;Název kampaně;Utracená částka (CZK);"
                "Nákupy;Hodnota konverze nákupů\n"
                "28. 11. 2025;28. 11. 2025;BF;1500,5;12;9600\n")
    r = E.nacti_export(p, "meta")[0]
    assert r.datum == date(2025, 11, 28) and math.isclose(r.naklady, 1500.5)
    assert r.konverze == 12 and r.obrat == 9600


def test_export_ga4_komentare_a_yyyymmdd():
    p = _soubor("# ----------------------------------------\n# Průzkumy\n# 20251101-20251102\n"
                "Datum,Celkové výnosy,Transakce\n20251101,15000,10\n20251102,\"12 500\",8\n")
    radky = E.nacti_export(p, "ga4")
    assert radky[1].datum == date(2025, 11, 2) and radky[1].obrat == 12500 and radky[1].naklady == 0


def test_export_bez_nakladu_u_reklamniho_systemu_je_chyba():
    p = _soubor("Den,Hodnota konv.\n2025-11-01,100\n")
    try:
        E.nacti_export(p, "google")
    except SystemExit as e:
        assert "náklady" in str(e)
    else:
        raise AssertionError("čekal jsem chybu")


def test_parse_datum_formaty():
    assert E.parse_datum("11/28/2025") == date(2025, 11, 28)
    assert E.parse_datum("Nov 28, 2025") == date(2025, 11, 28)
    assert E.parse_datum("Celkem") is None


def test_tydny_sedi_na_mesice_a_loni():
    radky = D.nacti_csv(UKAZKA)
    p = B.sestav(radky, [], 2026, date(2026, 10, 18), {"cil": {"pno": 25}})
    assert not p["obecny_profil"]
    for sc in B.SCENARE:
        for m in ("naklady", "obrat"):
            mesice = sum(info["cisla"][sc][m] for info in p["mesice"].values())
            tydny = sum(t[sc][m] for t in p["tydny"])
            assert math.isclose(mesice, tydny, rel_tol=1e-9)
    bf_tyden = next(t for t in p["tydny"] if t["od"] <= date(2026, 11, 27) <= t["do"])
    assert bf_tyden["faze"] == "bf_vikend"
    assert bf_tyden["realisticky"]["obrat"] == max(t["realisticky"]["obrat"] for t in p["tydny"])
    assert p["tydny"][0]["od"] == date(2026, 11, 1)          # useknutá neděle 1. 11. přidaná k týdnu
    assert len(p["tydny"]) == 9


def test_bez_lonska_obecny_profil_a_varovani():
    radky = [r for r in D.nacti_csv(UKAZKA) if r.datum >= date(2026, 1, 1)]
    p = B.sestav(radky, [], 2026, date(2026, 10, 18), {})
    assert p["obecny_profil"]
    assert any("obecný profil" in v for v in p["varovani"])


def test_zadany_rozpocet_se_propise():
    radky = D.nacti_csv(UKAZKA)
    p = B.sestav(radky, [], 2026, date(2026, 10, 18), {"rozpocet": {"2026-11": 150000}})
    assert math.isclose(p["mesice"][11]["cisla"]["realisticky"]["naklady"], 150000, rel_tol=1e-6)


def test_html_ma_graf_a_escapuje():
    radky = D.nacti_csv(UKAZKA)
    p = B.sestav(radky, [], 2026, date(2026, 10, 18), {"klient_nazev": "<script>x</script>"})
    out = B.html_dokument("x", p, B.markdown("x", p))
    assert "<svg" in out and "<script>x" not in out


if __name__ == "__main__":
    for nazev, fn in list(globals().items()):
        if nazev.startswith("test_"):
            fn()
            print("ok", nazev)

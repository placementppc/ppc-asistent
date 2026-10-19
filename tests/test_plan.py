"""Testy plánování (scripts/plan/model.py + výpočty krycího plánu a plnění). Bez sítě.

Spuštění: python3 -m pytest tests/test_plan.py -q   (nebo bez pytestu: python3 tests/test_plan.py)
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

try:
    import pytest
except ImportError:                      # běh bez pytestu: minimální náhrada approx/raises/parametrize
    import math
    import types

    class _Approx:
        def __init__(self, x, rel=1e-6, abs=1e-12):
            self.x, self.rel, self.abs = x, rel, abs

        def __eq__(self, o):
            return math.isclose(o, self.x, rel_tol=self.rel, abs_tol=self.abs)

    class _Raises:
        def __init__(self, typ):
            self.typ = typ

        def __enter__(self):
            return self

        def __exit__(self, t, e, tb):
            if t is None:
                raise AssertionError(f"čekal jsem {self.typ.__name__}")
            return issubclass(t, self.typ)

    def _parametrize(nazev, hodnoty):
        def obal(fn):
            fn._param = (nazev, hodnoty)
            return fn
        return obal

    pytest = types.SimpleNamespace(approx=_Approx, raises=_Raises,
                                   mark=types.SimpleNamespace(parametrize=_parametrize))

PLAN = Path(__file__).resolve().parents[1] / "scripts" / "plan"
sys.path.insert(0, str(PLAN))
import model as M  # noqa: E402
import kryci_plan as K  # noqa: E402
import plneni as P  # noqa: E402

VZOR = [1.2, 1.1, 1.0, 1.0, 0.9, 0.7, 1.1]   # po..ne


def historie(od: date, do: date, system: str = "google", zaklad: float = 1000.0,
             vzor: list[float] = VZOR, roas: float = 8.0) -> list[M.Radek]:
    out, d = [], od
    while d <= do:
        n = zaklad * vzor[d.weekday()]
        out.append(M.Radek(d, system, n, n * roas, n * roas / 1000))
        d += timedelta(days=1)
    return out


# ------------------------------------------------------------------ svátky
def test_velikonoce_2026_2027():
    assert M.velikonocni_nedele(2026) == date(2026, 4, 5)
    assert M.velikonocni_nedele(2027) == date(2027, 3, 28)
    s26, s27 = M.svatky_cr(2026), M.svatky_cr(2027)
    assert s26[date(2026, 4, 3)] == "Velký pátek"
    assert s26[date(2026, 4, 6)] == "Velikonoční pondělí"
    assert s27[date(2027, 3, 26)] == "Velký pátek"
    assert s27[date(2027, 3, 29)] == "Velikonoční pondělí"


def test_velikonoce_dalsi_roky():
    # známá data Velikonoční neděle
    assert M.velikonocni_nedele(2024) == date(2024, 3, 31)
    assert M.velikonocni_nedele(2025) == date(2025, 4, 20)
    assert M.velikonocni_nedele(2019) == date(2019, 4, 21)


def test_pevne_svatky_a_pocet():
    s = M.svatky_cr(2026)
    assert len(s) == 13
    for d in (date(2026, 1, 1), date(2026, 5, 1), date(2026, 5, 8), date(2026, 7, 5), date(2026, 7, 6),
              date(2026, 9, 28), date(2026, 10, 28), date(2026, 11, 17), date(2026, 12, 24),
              date(2026, 12, 25), date(2026, 12, 26)):
        assert d in s
    assert not M.je_svatek(date(2026, 11, 27))


# ------------------------------------------------------------------ váhy dnů
def test_vahy_dnu_z_historie():
    dny = M.po_dnech(historie(date(2026, 1, 5), date(2026, 5, 31)))
    vahy, tydnu = M.vahy_dnu(dny, date(2026, 5, 31))
    assert tydnu == 16
    prumer = sum(VZOR) / 7
    for v, ocek in zip(vahy, VZOR):
        assert v == pytest.approx(ocek / prumer, rel=1e-6)
    assert sum(vahy) / 7 == pytest.approx(1.0)


def test_vahy_dnu_kratka_historie_jsou_rovne():
    dny = M.po_dnech(historie(date(2026, 5, 1), date(2026, 5, 31)))
    vahy, tydnu = M.vahy_dnu(dny, date(2026, 5, 31))
    assert tydnu < M.MIN_TYDNU
    assert vahy == [1.0] * 7


def test_koeficient_svatku_neutralni_bez_dat():
    dny = M.po_dnech(historie(date(2026, 6, 1), date(2026, 6, 30)))
    k, n = M.koeficient_svatku(dny)
    assert (k, n) == (1.0, 0)


# ------------------------------------------------------------------ rozpad
@pytest.mark.parametrize("celkem", [30000, 45678, 99999.0, 7])
def test_soucet_denniho_planu_je_mesicni_cil(celkem):
    rozpad = M.rozpad_mesice(celkem, 2026, 11, VZOR, 0.8, {date(2026, 11, 27): 1.4})
    assert len(rozpad) == 30
    assert sum(c for _, c in rozpad) == pytest.approx(celkem)
    assert all(c == int(c) for _, c in rozpad)


def test_soucet_na_desetiny():
    rozpad = M.rozpad_mesice(123.45, 2026, 2, [1.0] * 7, mist=2)
    assert sum(c for _, c in rozpad) == pytest.approx(123.45)


def test_udalost_plus_40_procent():
    u = M.parse_udalost("2026-11-27:+40%")
    assert u == {date(2026, 11, 27): pytest.approx(1.4)}
    rozpad = dict(M.rozpad_mesice(1_000_000, 2026, 11, [1.0] * 7, 1.0, u, mist=2))
    # pátek 27. 11. proti obyčejnému pátku 20. 11.
    assert rozpad[date(2026, 11, 27)] / rozpad[date(2026, 11, 20)] == pytest.approx(1.4, rel=1e-4)
    assert sum(rozpad.values()) == pytest.approx(1_000_000)


def test_udalost_rozsah_a_minus():
    u = M.parse_udalost("2026-12-21..2026-12-31:-50%")
    assert len(u) == 11 and all(x == pytest.approx(0.5) for x in u.values())
    with pytest.raises(ValueError):
        M.parse_udalost("27.11.:+40")


def test_svatek_snizi_den():
    rozpad = dict(M.rozpad_mesice(10000, 2026, 11, [1.0] * 7, 0.5, mist=2))
    # 17. 11. 2026 je úterý a svátek; 10. 11. obyčejné úterý
    assert rozpad[date(2026, 11, 17)] == pytest.approx(rozpad[date(2026, 11, 10)] * 0.5, rel=1e-3)


def test_kryci_plan_sedi_na_cile_po_systemech():
    radky = (historie(date(2025, 6, 2), date(2026, 9, 30), "google", 1000)
             + historie(date(2025, 6, 2), date(2026, 9, 30), "sklik", 500, roas=6.0))
    plan = K.sestav_plan(radky, 2026, 10, date(2026, 9, 30), rozpocet=60000, obrat=400000,
                         udalosti={date(2026, 10, 16): 1.4})
    n = sum(r["plan_naklady"] for r in plan["radky"])
    o = sum(r["plan_obrat"] for r in plan["radky"])
    assert n == 60000 and o == 400000
    # podíl systémů z historie 2:1
    assert plan["rozpocet"]["google"] == 40000 and plan["rozpocet"]["sklik"] == 20000
    posledni_google = [r for r in plan["radky"] if r["system"] == "google"][-1]
    assert posledni_google["kum_plan_naklady"] == 40000
    assert len(plan["radky"]) == 31 * 2


def test_kryci_plan_bere_rozpocty_z_konfigurace():
    radky = historie(date(2025, 6, 2), date(2026, 9, 30), "google", 1000)
    cile = {"google": {"mesicni_rozpocet": 25000, "mesicni_obrat": 200000},
            "meta": {"mesicni_rozpocet": 5000}}
    plan = K.sestav_plan(radky, 2026, 10, date(2026, 9, 30), cile=cile)
    assert plan["rozpocet"] == {"google": 25000, "meta": 5000}
    assert plan["obrat"]["google"] == 200000


# ------------------------------------------------------------------ plnění
def test_semafor_prahy():
    assert M.semafor(0) == "zelena"
    assert M.semafor(9.9) == "zelena"
    assert M.semafor(-10) == "zelena"
    assert M.semafor(-15) == "zluta"
    assert M.semafor(25) == "zluta"
    assert M.semafor(-26) == "cervena"
    assert M.semafor(40) == "cervena"
    # obrat nad plánem je vždy zelený
    assert M.semafor(60, jen_dolu=True) == "zelena"
    assert M.semafor(-30, jen_dolu=True) == "cervena"
    assert M.horsi("zelena", "zluta", "zelena") == "zluta"


def test_prognoza_a_korekce():
    # 10 dní za sebou utrácí 80 % plánu, plán 1000/den, měsíc 30 dní
    assert M.prognoza_konce(8000, 20000, 5600, 7000) == pytest.approx(24000)
    assert M.denni_korekce(10000, 8000, 20) == pytest.approx(100)
    assert M.denni_korekce(10000, 8000, 0) == 0


def _plan_radky(rok, mesic, system, denne_n, denne_o):
    return [{"datum": d, "system": system, "naklady": denne_n, "obrat": denne_o, "konverze": denne_o / 1000}
            for d in M.dny_mesice(rok, mesic)]


def test_plneni_pod_planem_s_dobrym_pno_navrhne_navyseni():
    plan = _plan_radky(2026, 11, "sklik", 1000, 8000)
    skut = [M.Radek(d, "sklik", 700, 7000, 7) for d in M.dny_mesice(2026, 11)[:15]]
    v = P.vyhodnot_system(plan, skut, "sklik", date(2026, 11, 15), {"typ": "pno", "hodnota": 15})
    assert v["naklady"]["odchylka_kum_pct"] == pytest.approx(-30)
    assert v["semafor"] == "cervena"
    assert v["pno_skut"] == pytest.approx(10)
    t = P.navrh(v, 20)
    assert t.startswith("Sklik: zvednout denní rozpočty o ~200 Kč")


def test_plneni_pod_planem_se_spatnym_pno_nepridava():
    plan = _plan_radky(2026, 11, "google", 1000, 8000)
    skut = [M.Radek(d, "google", 800, 4000, 3) for d in M.dny_mesice(2026, 11)[:10]]
    v = P.vyhodnot_system(plan, skut, "google", date(2026, 11, 10), {"typ": "pno", "hodnota": 15})
    assert v["semafor"] == "cervena"
    assert "nepřidávat" in P.navrh(v)


def test_plneni_v_planu_je_zelene_bez_navrhu():
    plan = _plan_radky(2026, 11, "meta", 1000, 8000)
    skut = [M.Radek(d, "meta", 1050, 8500, 8) for d in M.dny_mesice(2026, 11)[:12]]
    v = P.vyhodnot_system(plan, skut, "meta", date(2026, 11, 12))
    assert v["semafor"] == "zelena"
    assert P.navrh(v) is None


def test_prvni_dny_mesice_nejvys_zluta():
    plan = _plan_radky(2026, 11, "google", 1000, 8000)
    skut = [M.Radek(date(2026, 11, 1), "google", 100, 500, 0)]
    v = P.vyhodnot_system(plan, skut, "google", date(2026, 11, 2))
    assert v["semafor"] == "zluta"


if __name__ == "__main__":
    for nazev, fn in list(globals().items()):
        if nazev.startswith("test_") and callable(fn):
            param = getattr(fn, "_param", None)
            for h in (param[1] if param else [None]):
                fn(**({param[0]: h} if param else {}))
            print("ok", nazev)

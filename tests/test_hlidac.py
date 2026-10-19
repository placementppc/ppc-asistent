"""Testy pravidel hlídače (scripts/hlidac/kontroly.py). Bez API.

Spuštění: python3 -m pytest tests/test_hlidac.py   (nebo python3 tests/test_hlidac.py)
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "hlidac"))
import kontroly as k  # noqa: E402

VCERA = "2026-10-18"


def historie(utrata=1000.0, zobrazeni=10000, prokliky=200, konverze=5.0, dni=28):
    start = date.fromisoformat(VCERA) - timedelta(days=dni)
    return [k.Den((start + timedelta(days=i)).isoformat(), utrata, zobrazeni, prokliky, konverze)
            for i in range(dni)]


def urovne(nalezy):
    return [n.uroven for n in nalezy]


def test_bezny_den_bez_nalezu():
    dny = historie() + [k.Den(VCERA, 1050, 10500, 210, 5)]
    assert k.vyhodnot_den(dny, VCERA) == []


def test_utrata_stoji_je_cervena():
    dny = historie() + [k.Den(VCERA, 100, 900, 20, 0)]
    nalezy = k.vyhodnot_den(dny, VCERA)
    assert k.CERVENA in urovne(nalezy)
    assert "spadla" in nalezy[0].text
    # propad zobrazení se při stojící útratě nehlásí podruhé
    assert not any("Zobrazení" in n.text for n in nalezy)


def test_chybejici_den_znamena_nulovou_utratu():
    nalezy = k.vyhodnot_den(historie(), VCERA)
    assert "spadla" in nalezy[0].text


def test_utrata_utika_je_cervena():
    nalezy = k.vyhodnot_den(historie() + [k.Den(VCERA, 1700, 17000, 340, 8)], VCERA)
    assert any("vyletěla" in n.text and n.uroven == k.CERVENA for n in nalezy)


def test_skok_cpc_je_zluty():
    # stejná útrata, polovina prokliků -> CPC dvojnásobné
    nalezy = k.vyhodnot_den(historie() + [k.Den(VCERA, 1000, 10000, 100, 5)], VCERA)
    assert urovne(nalezy) == [k.ZLUTA] and "Cena prokliku" in nalezy[0].text


def test_cpc_se_pri_malo_proklicich_nehodnoti():
    dny = historie(utrata=100, prokliky=10, konverze=0) + [k.Den(VCERA, 100, 10000, 3, 0)]
    assert k.vyhodnot_den(dny, VCERA) == []


def test_nula_konverzi_je_cervena():
    nalezy = k.vyhodnot_den(historie() + [k.Den(VCERA, 1000, 10000, 200, 0)], VCERA)
    assert any("Nula konverzí" in n.text and n.uroven == k.CERVENA for n in nalezy)


def test_nula_konverzi_u_maleho_uctu_se_nehlasi():
    dny = historie(konverze=0.5) + [k.Den(VCERA, 1000, 10000, 200, 0)]
    assert k.vyhodnot_den(dny, VCERA) == []


def test_jeden_vyprodejovy_den_nerozhodi_zaklad():
    dny = historie()
    dny[-1] = k.Den(dny[-1].datum, 10000, 10000, 200, 5)   # předevčírem výprodej
    assert k.vyhodnot_den(dny + [k.Den(VCERA, 1000, 10000, 200, 5)], VCERA) == []


def test_malo_historie():
    nalezy = k.vyhodnot_den(historie(dni=3) + [k.Den(VCERA, 1000, 1, 1, 0)], VCERA)
    assert urovne(nalezy) == [k.ZLUTA] and "Málo historie" in nalezy[0].text


def test_min_utrata_vypne_hlidani_maleho_uctu():
    dny = historie(utrata=50) + [k.Den(VCERA, 0, 0, 0, 0)]
    assert k.vyhodnot_den(dny, VCERA, min_utrata=100) == []


def test_dnes_utika_a_stoji():
    assert urovne(k.vyhodnot_dnes(1400, 1000, 15)) == [k.CERVENA]
    assert urovne(k.vyhodnot_dnes(100, 1000, 19)) == [k.ZLUTA]
    assert k.vyhodnot_dnes(100, 1000, 10) == []      # dopoledne nízká útrata je normální
    assert k.vyhodnot_dnes(500, 0, 20) == []


if __name__ == "__main__":
    for nazev, fn in list(globals().items()):
        if nazev.startswith("test_"):
            fn()
            print("ok", nazev)

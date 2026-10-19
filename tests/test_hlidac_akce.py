"""Testy hlídače akcí (prostor pro škálování). Bez sítě — zdroje se mockují.

Spuštění: python3 -m pytest tests/test_hlidac_akce.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOREN / "scripts" / "hlidac"))
import config  # noqa: E402
import kontroly as k  # noqa: E402
import pravidla_akce as pa  # noqa: E402

VCERA = date(2026, 10, 15)      # čtvrtek; dnes = pátek 16. 10.
OD = (VCERA - timedelta(days=13)).isoformat()
DO = VCERA.isoformat()
LIMITY = {"max_denni_rozpocet": None, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30}
CIL_PNO = {"typ": "pno", "hodnota": 15}


def kampan(nazev="Search", system="google", rozpocet=1000.0, utrata=1000.0, konverze=2.0, hodnota=10000.0,
           dni=14, **kw) -> pa.Kampan:
    start = VCERA - timedelta(days=dni - 1)
    d = [k.Den((start + timedelta(days=i)).isoformat(), utrata, 5000, 100, konverze, hodnota) for i in range(dni)]
    return pa.Kampan(system=system, id=kw.pop("id", nazev.lower()), nazev=nazev, rozpocet=rozpocet, dny=d,
                     rozpocet_id=kw.pop("rozpocet_id", "b-" + nazev.lower()), **kw)


# ------------------------------------------------------------------ signály
def test_omezeni_rozpoctem_podle_vycerpanych_dni():
    ano, duvody = pa.omezeni_rozpoctem(kampan(utrata=950), OD, DO)
    assert ano and "14 z 14 dní" in duvody[0]
    ne, _ = pa.omezeni_rozpoctem(kampan(utrata=600), OD, DO)
    assert not ne


def test_omezeni_rozpoctem_google_ztrata_is_a_stav():
    ano, duvody = pa.omezeni_rozpoctem(kampan(utrata=500, ztrata_is_rozpocet=0.9001), OD, DO)
    assert ano and "víc než 90 %" in duvody[0]
    ano, duvody = pa.omezeni_rozpoctem(kampan(utrata=500, duvody_stavu=["BUDGET_CONSTRAINED"]), OD, DO)
    assert ano and "omezení rozpočtem" in duvody[0]


@pytest.mark.parametrize("cile, hodnota, konverze, ok", [
    ({"typ": "pno", "hodnota": 15}, 10000, 2, True),     # PNO 10 % vs 15 → rezerva 33 %
    ({"typ": "pno", "hodnota": 15}, 7000, 2, False),     # PNO 14,3 % — rezerva jen 5 %
    ({"typ": "roas", "hodnota": 6}, 10000, 2, True),     # ROAS 10
    ({"typ": "cpa", "hodnota": 600}, 0, 2, True),        # CPA 500 vs 600 → 17 %
    ({"typ": "pno", "hodnota": 15}, 10000, 0.5, False),  # 7 konverzí < 15
])
def test_posud_vykon(cile, hodnota, konverze, ok):
    s = pa.soucet(kampan(hodnota=hodnota, konverze=konverze), OD, DO)
    assert pa.posud_vykon(s, cile)[0] is ok


def test_posud_vykon_typ_konverze_srovnava_s_cpa_uctu():
    s = pa.soucet(kampan(konverze=2), OD, DO)   # CPA 500
    assert pa.posud_vykon(s, {"typ": "konverze", "hodnota": 100}, ucet_cpa=700)[0]
    assert not pa.posud_vykon(s, {"typ": "konverze", "hodnota": 100}, ucet_cpa=520)[0]


# ------------------------------------------------------------------ limity
def test_navyseni_max_krok():
    nav, _ = pa.navrhni_navyseni(1000, LIMITY)
    assert (nav.novy, round(nav.pct)) == (1200, 20)


def test_navyseni_vikend_mensi_krok():
    nav, omez = pa.navrhni_navyseni(1000, LIMITY, vikend=True)
    assert nav.novy == 1100 and "víkend" in omez[0]


def test_navyseni_tydenni_strop():
    # před týdnem 900 → strop 900 × 1,3 = 1170
    nav, omez = pa.navrhni_navyseni(1100, LIMITY, rozpocet_tyden=900)
    assert nav.novy == 1170 and "týdenní strop" in omez[0]
    # už navýšeno na strop → nic
    nav, omez = pa.navrhni_navyseni(1170, LIMITY, rozpocet_tyden=900)
    assert nav is None and "nemá smysl" in omez[-1]


def test_navyseni_rezerva_uctu_a_zaokrouhleni():
    nav, omez = pa.navrhni_navyseni(1000, LIMITY, rezerva=137, popis_rezervy="strop účtu")
    assert nav.novy == 1130 and "strop účtu" in omez[-1]
    assert pa.navrhni_navyseni(1000, LIMITY, rezerva=-50, popis_rezervy="x")[0] is None


def test_rezerva_uctu_bere_prisnejsi_strop():
    dnes = date(2026, 10, 16)            # zbývá 16 dní včetně dneška
    r, popis = pa.rezerva_uctu({"max_denni_rozpocet": 3000}, 2500, {"mesicni_rozpocet": 40000},
                               utraceno_mesic=24000, denni_utrata=900, dnes=dnes)
    # strop účtu: 500; měsíc: 16 000 / 16 = 1000 − 900 = 100 → přísnější je měsíc
    assert r == pytest.approx(100) and "měsíční rozpočet" in popis
    assert pa.rezerva_uctu({}, 2500, {}, 0, 0, dnes) == (None, None)


def test_rozpocet_pred_tydnem_bere_nejnizsi_za_7_dni():
    hist = {"2026-10-01": 500, "2026-10-10": 800, "2026-10-14": 1000}
    assert pa.rozpocet_pred_tydnem(hist, date(2026, 10, 16), 1100) == 800
    assert pa.rozpocet_pred_tydnem({}, date(2026, 10, 16), 1100) == 1100


# ------------------------------------------------------------------ kandidáti
def test_kandidati_navrhne_jen_dobrou_brzdenou_kampan():
    dobra = kampan("Dobrá", utrata=990, hodnota=10000)        # PNO 9,9 %, čerpá celý rozpočet
    spatna = kampan("Drahá", utrata=990, hodnota=4000)        # PNO 24,8 %
    volna = kampan("Volná", utrata=500, hodnota=10000)        # nečerpá rozpočet
    navrhy, pozn = pa.kandidati("Můj e-shop", [dobra, spatna, volna], CIL_PNO, LIMITY, vcera=VCERA)
    assert [n.kampan.nazev for n in navrhy] == ["Dobrá"]
    assert navrhy[0].navyseni.novy == 1200
    assert any("PNO 9,9 %" in t for t in navrhy[0].proc)
    assert any("Drahá" in p for p in pozn) and not any("Volná" in p for p in pozn)


def test_kandidati_deli_rezervu_uctu_od_nejlepsi():
    a = kampan("A", utrata=990, hodnota=20000)   # PNO ~5 %
    b = kampan("B", utrata=990, hodnota=10000)   # PNO ~10 %
    navrhy, pozn = pa.kandidati("Účet", [b, a], CIL_PNO, LIMITY, vcera=VCERA, rezerva=250, popis_rezervy="strop")
    assert [(n.kampan.nazev, n.navyseni.novy) for n in navrhy] == [("A", 1200), ("B", 1050)]


def test_kandidati_meta_vysoka_frekvence_nenavrhne():
    sada = kampan("Prospecting", system="meta", utrata=990, frekvence_7d=3.6, uroven="sada")
    navrhy, pozn = pa.kandidati("Účet", [sada], CIL_PNO, LIMITY, vcera=VCERA)
    assert navrhy == [] and "`meta-strop`" in pozn[0]


def test_kandidati_vecer_jen_co_dnes_vycerpalo():
    rano = kampan("Ráno vyčerpaná", utrata=700, hodnota=10000, utrata_dnes=950)
    ne = kampan("Pomalá", utrata=990, hodnota=10000, utrata_dnes=300)
    navrhy, _ = pa.kandidati("Účet", [rano, ne], CIL_PNO, LIMITY, vcera=VCERA, dnes_hodina=17)
    assert [n.kampan.nazev for n in navrhy] == ["Ráno vyčerpaná"]
    assert "dnes už utratil 950" in navrhy[0].proc[1]


def test_rizika_navrhu_sdileny_rozpocet_google_a_vikend():
    navrhy, _ = pa.kandidati("Účet", [kampan(utrata=990, sdileny_rozpocet=True)], CIL_PNO, LIMITY,
                             vcera=VCERA, vikend=True)
    r = " ".join(navrhy[0].rizika)
    assert "sdílený" in r and "2×" in r and "víkend" in r


# ------------------------------------------------------------------ víkend
def test_rizika_vikend_preceprani_mesice_a_spatna_kampan():
    dobra = kampan("Dobrá", utrata=990, hodnota=10000)
    drahá = kampan("Drahá", utrata=990, hodnota=4000)
    r = pa.rizika_vikend("Účet", [dobra, drahá], CIL_PNO, vcera=VCERA, zbyva_mesic=4000)
    assert any("Víkend může měsíc vyčerpat" in x for x in r)       # 2 000 × 3 = 6 000 > 4 000
    assert any("Drahá" in x and "snížení rozpočtu" in x for x in r)
    assert not any("Dobrá" in x for x in r)


def test_rizika_vikend_bez_rizika():
    assert pa.rizika_vikend("Účet", [kampan(utrata=500)], CIL_PNO, vcera=VCERA, zbyva_mesic=100000) == []


# ------------------------------------------------------------------ plány pro apply skripty
def _navrh(system="google", mena=None):
    kmp = kampan("K", system=system, rozpocet_id="555", mena=mena)
    return pa.Navrh("Účet", kmp, pa.Navyseni(1000, 1200, 20), ["proč"], ["riziko"])


def test_plan_google_odpovida_schematu_apply_changes():
    plan = pa.plan_google([_navrh()], "2026-10-15")
    assert plan["set_budget"] == [{"budget_id": "555", "amount_micros": 1_200_000_000,
                                   "_popis": "K: 1 000 → 1 200 Kč/den"}]
    assert "NESCHVÁLENO" in plan["_popis"]


def test_plan_meta_v_nejmensich_jednotkach_a_neschvaleny():
    plan = pa.plan_meta([_navrh("meta", "CZK")], "muj-eshop", "2026-10-15")
    assert plan["approval"]["status"] == "pending"
    assert plan["changes"][0]["params"] == {"daily_budget": 120000}
    assert pa.plan_meta([_navrh("meta", "HUF")], "x", "d")["changes"][0]["params"]["daily_budget"] == 1200


def test_hlidac_akci_nic_nezapisuje_do_uctu():
    """Pojistka: hlídače nevolají zápisové metody API ani nespouští apply skripty."""
    for soubor in ("akce.py", "pravidla_akce.py", "zdroje.py", "cile.py", "pravidla_cile.py"):
        zdroj = (KOREN / "scripts" / "hlidac" / soubor).read_text(encoding="utf-8")
        for zakazane in ("mutate", "campaigns.update", "requests.post", "subprocess", "os.system"):
            assert zakazane not in zdroj, (soubor, zakazane)


# ------------------------------------------------------------------ celý běh bez sítě
def test_cely_beh_vikend(tmp_path, monkeypatch, capsys):
    import akce

    kampane = {
        "google": [kampan("Search brand", utrata=990, hodnota=12000, rozpocet_id="111"),
                   kampan("PMax", utrata=990, hodnota=4000, rozpocet_id="222")],
        "sklik": [kampan("Sklik search", system="sklik", utrata=990, hodnota=12000, id="9")],
        "meta": [kampan("Prospecting", system="meta", utrata=990, hodnota=12000, uroven="sada",
                        frekvence_7d=1.8, mena="CZK", id="2384", rozpocet_id="2384")],
    }

    def kampane_fn(u, od, do, dnes):
        return kampane[u["system"]]

    def dny_fn(u, od, do):
        start = date.fromisoformat(od)
        n = (date.fromisoformat(do) - start).days + 1
        return [k.Den((start + timedelta(days=i)).isoformat(), 1800, 1, 1, 1, 1) for i in range(n)], []

    import types
    monkeypatch.setitem(sys.modules, "zdroje", types.SimpleNamespace(ucet_kampane=kampane_fn, ucet_dny=dny_fn))
    monkeypatch.setattr(akce, "ROOT", tmp_path)
    monkeypatch.setattr(akce, "VYSTUP", tmp_path / "reports" / "hlidac-akci")
    monkeypatch.setattr(akce, "HISTORIE", tmp_path / "reports" / "hlidac-akci" / "rozpocty.json")
    cesta = tmp_path / "ucty.json"
    zaklad = {"klient": "muj-eshop", "hlidat": ["akce"], "cile": {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 60000},
              "limity": {"max_denni_rozpocet": 5000, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30}}
    cesta.write_text(json.dumps({"ucty": [
        dict(zaklad, nazev="Můj e-shop", system="google", id="123-456-7890"),
        dict(zaklad, nazev="Můj e-shop", system="sklik", id=123456),
        dict(zaklad, nazev="Můj e-shop", system="meta", id="act_1234567890"),
    ]}), encoding="utf-8")

    kod = akce.main(["--ucty", str(cesta), "--datum", VCERA.isoformat(), "--vikend"])
    text = capsys.readouterr().out
    assert kod == 1
    assert "Search brand (kampaň): 990 → 1 080 Kč/den" not in text   # rozpočet 1000, ne útrata
    assert "Search brand (kampaň): 1 000 → 1 100 Kč/den (+10 %)" in text   # víkend = max 10 %
    assert "PMax" in text and "snížení rozpočtu" in text                # víkendové riziko
    assert "scripts/google_ads/apply_changes.py 123-456-7890 reports/hlidac-akci/plany/" in text
    assert "scripts/meta/apply.py reports/hlidac-akci/plany/" in text
    assert "ručně v rozhraní Skliku" in text
    plany = tmp_path / "reports" / "hlidac-akci" / "plany"
    g = json.loads((plany / "2026-10-15-muj-eshop-google.json").read_text(encoding="utf-8"))
    assert g["set_budget"][0] == {"budget_id": "111", "amount_micros": 1_100_000_000,
                                  "_popis": "Search brand: 1 000 → 1 100 Kč/den"}
    m = json.loads((plany / "2026-10-15-muj-eshop-meta.json").read_text(encoding="utf-8"))
    assert m["approval"]["status"] == "pending" and m["changes"][0]["params"]["daily_budget"] == 110000
    assert (tmp_path / "reports" / "hlidac-akci" / "2026-10-15-vikend.md").exists()
    hist = json.loads((tmp_path / "reports" / "hlidac-akci" / "rozpocty.json").read_text(encoding="utf-8"))
    assert hist["google:123-456-7890"]["search brand"] == {"2026-10-16": 1000}


def test_bez_cilu_je_exit_0_s_poznamkou(tmp_path, capsys):
    import akce
    import cile
    cesta = tmp_path / "ucty.json"
    cesta.write_text(json.dumps({"ucty": [{"nazev": "A", "system": "sklik", "id": 1}]}), encoding="utf-8")
    assert akce.main(["--ucty", str(cesta)]) == 0
    assert cile.main(["--ucty", str(cesta)]) == 0
    assert capsys.readouterr().err.count("Žádný účet nemá nastavené cíle") == 2


def test_config_limity_vychozi():
    cfg = config.rozparsuj({"ucty": [{"nazev": "A", "system": "sklik", "id": 1, "cile": {"typ": "cpa", "hodnota": 200}}]})
    assert cfg["ucty"][0]["limity"] == {"max_denni_rozpocet": None, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30}

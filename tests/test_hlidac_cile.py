"""Testy hlídače cílů a konfigurace hlídačů. Bez sítě — zdroje se mockují.

Spuštění: python3 -m pytest tests/test_hlidac_cile.py
"""
from __future__ import annotations

import json
import re
import sys
import types
from datetime import date, timedelta
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOREN / "scripts" / "hlidac"))
import config  # noqa: E402
import kontroly as k  # noqa: E402
import pravidla_cile as pc  # noqa: E402

VCERA = date(2026, 10, 18)


def dny(od: date, pocet: int, utrata=1000.0, konverze=2.0, hodnota=8000.0, prokliky=100):
    return [k.Den((od + timedelta(days=i)).isoformat(), utrata, 5000, prokliky, konverze, hodnota)
            for i in range(pocet)]


# ------------------------------------------------------------------ changelog
CHANGELOG = """# Klient: Můj e-shop

## 6. Changelog změn (learning loop) 🧠
> Status: 🟡 čeká na vyhodnocení

### YYYY-MM-DD — <krátký název změny>  [🟡 čeká na vyhodnocení]
### 2026-09-12 — snížení tROAS
- **Objekt:** PMax
### 2026-10-01 — nové negativní KW  [🟡 čeká na vyhodnocení]
### 2026-11-30 — plán do budoucna

## 7. A/B testy a experimenty
### 2026-10-10 — test RSA  [běží]
"""


def test_posledni_zmena_z_changelogu_ignoruje_ab_testy_a_budoucnost():
    assert pc.najdi_posledni_zmenu(CHANGELOG, VCERA) == "2026-10-01"


def test_posledni_zmena_bez_sekce_changelog_bere_dvojite_i_trojite_mrizky():
    text = "# Poznámky\n## 2026-09-01\n### 2026-09-20 — změna\nnic"
    assert pc.najdi_posledni_zmenu(text, VCERA) == "2026-09-20"
    assert pc.najdi_posledni_zmenu("bez dat", VCERA) is None


def test_okno_vychozi_28_dni_a_obdobi_pred():
    o = pc.okno_od_zmeny(None, "changelog", VCERA)
    assert (o.dni, o.zdroj, o.od, o.do) == (28, "výchozí", "2026-09-21", "2026-10-18")
    assert o.pred_do == "2026-09-20" and o.pred_od == "2026-08-24"


def test_okno_stare_zmeny_se_zkrati_na_90_dni():
    o = pc.okno_od_zmeny("2026-01-01", "config", VCERA)
    assert o.dni == 90 and o.zkraceno


# ------------------------------------------------------------------ posudek
def _posud(po_dny, pred_dny, cile, zmena="2026-09-21"):
    o = pc.okno_od_zmeny(zmena, "config", VCERA)
    vse = po_dny + pred_dny
    return pc.posud_cil(pc.soucet(vse, o.od, o.do), pc.soucet(vse, o.pred_od, o.pred_do), cile, o)


def test_kratce_po_zmene_je_bila_a_rika_kolik_pockat():
    p = _posud(dny(date(2026, 10, 15), 4), [], {"typ": "pno", "hodnota": 15}, zmena="2026-10-15")
    assert p.stav == pc.BILA and "ještě 3 dny" in p.shrnuti


def test_malo_konverzi_je_bila_s_odhadem_dni():
    # 28 dní × 0,5 konverze = 14 konverzí; do 30 chybí 16 → při tempu 0,5/den 32 dní
    p = _posud(dny(date(2026, 9, 21), 28, konverze=0.5), [], {"typ": "pno", "hodnota": 15})
    assert p.stav == pc.BILA and "~32 dní" in p.shrnuti and "Předběžně PNO" in p.shrnuti


def test_pno_plni_cil_zelena():
    # PNO = 1000 / 8000 = 12,5 % < 15 %
    p = _posud(dny(date(2026, 9, 21), 28), [], {"typ": "pno", "hodnota": 15})
    assert p.stav == pc.ZELENA and "12,5 %" in p.shrnuti


def test_pno_tesne_nad_cilem_zluta_a_nic_nemenit():
    p = _posud(dny(date(2026, 9, 21), 28, hodnota=6250), [], {"typ": "pno", "hodnota": 15})  # 16 %
    assert p.stav == pc.ZLUTA and "nic neměň" in " ".join(p.navrhy)


def test_pno_vysoko_nad_cilem_cervena_s_odkazy_na_skilly():
    p = _posud(dny(date(2026, 9, 21), 28, hodnota=4545), [], {"typ": "pno", "hodnota": 15})  # 22 %
    assert p.stav == pc.CERVENA
    text = " ".join(p.navrhy)
    assert "`anomalie`" in text and "`pmax-produkty`" in text and "`dotazy-vylouceni`" in text


def test_zhorseni_po_zmene_navrhne_vyhodnotit_zmenu():
    pred = dny(date(2026, 8, 24), 28)                       # PNO 12,5 % — plnil
    po = dny(date(2026, 9, 21), 28, hodnota=4545)           # PNO 22 %
    p = _posud(po, pred, {"typ": "pno", "hodnota": 15})
    assert p.stav == pc.CERVENA and "Před změnou 21. 9. se cíl plnil" in p.navrhy[0]
    assert any("Před změnou" in d for d in p.detaily)


def test_cpa_nula_konverzi_pri_vysoke_utrate_je_cervena():
    p = _posud(dny(date(2026, 9, 21), 28, konverze=0, prokliky=2), [], {"typ": "cpa", "hodnota": 250})
    assert p.stav == pc.CERVENA and "Nula konverzí" in p.shrnuti and "`mereni-audit`" in p.navrhy[0]


def test_konverze_tempo_mesicne():
    # 2 konverze denně → 60,8 za měsíc vs. cíl 100 → červená
    p = _posud(dny(date(2026, 9, 21), 28), [], {"typ": "konverze", "hodnota": 100})
    assert p.stav == pc.CERVENA and "Tempo 61" in p.shrnuti


def test_roas_lepsi_o_hodne_navrhne_hlidac_akci():
    p = _posud(dny(date(2026, 9, 21), 28, hodnota=10000), [], {"typ": "roas", "hodnota": 6})  # ROAS 10
    assert p.stav == pc.ZELENA and "akce.py" in " ".join(p.navrhy)


def test_z_test():
    assert pc.z_test_podilu(50, 1000, 50, 1000) == pytest.approx(1.0)
    assert pc.z_test_podilu(80, 1000, 40, 1000) < 0.01
    assert pc.z_test_podilu(1, 0, 1, 10) is None


# ------------------------------------------------------------------ tempo
def test_tempo_precerpa_a_zacatek_mesice():
    d = dny(date(2026, 10, 1), 18, utrata=1500)
    t = pc.tempo_mesice(d, {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 30000}, VCERA)
    assert t.stav == pc.CERVENA and "Výrazně přečerpá" in t.texty[0]   # 1500 × 31 = 46 500 = 155 %
    t2 = pc.tempo_mesice(d[:3], {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 30000}, date(2026, 10, 3))
    assert t2.stav == pc.BILA
    assert pc.tempo_mesice(d, {"typ": "pno", "hodnota": 15}, VCERA) is None


def test_tydny_vraci_8_bloku_od_nejstarsiho():
    t = pc.tydny(dny(date(2026, 8, 1), 79), VCERA, "pno")
    assert len(t) == 8 and t[-1]["do"] == "2026-10-18" and t[0]["od"] == "2026-08-24"
    assert t[-1]["utrata"] == 7000


# ------------------------------------------------------------------ config
def test_config_stary_format_funguje():
    cfg = config.rozparsuj({"ucty": [{"nazev": "A", "system": "sklik", "id": 1}]})
    assert cfg["planovani"]["frekvence"] == "denne"
    assert [u["nazev"] for u in config.ucty_pro(cfg, "vykyvy")] == ["A"]
    assert config.ucty_pro(cfg, "cile") == []     # bez cíle nic k hodnocení


def test_config_respektuje_hlidat():
    cfg = config.rozparsuj({"ucty": [
        {"nazev": "Jen cíle", "system": "google", "id": "123-456-7890", "hlidat": ["cile"],
         "cile": {"typ": "pno", "hodnota": 15}},
        {"nazev": "Vše", "system": "meta", "id": "act_1", "cile": {"typ": "roas", "hodnota": 600}},
        {"nazev": "Vypnutý", "system": "meta", "id": "act_2", "vypnuto": True},
    ]})
    assert [u["nazev"] for u in config.ucty_pro(cfg, "vykyvy")] == ["Vše"]
    assert [u["nazev"] for u in config.ucty_pro(cfg, "cile")] == ["Jen cíle", "Vše"]
    assert cfg["ucty"][1]["cile"]["hodnota"] == 6      # 600 % → násobek 6
    assert cfg["ucty"][0]["limity"]["max_navyseni_pct"] == 20


@pytest.mark.parametrize("data, hlaska", [
    ({"ucty": [{"nazev": "A", "system": "bing", "id": 1}]}, "neznámý system"),
    ({"ucty": [{"nazev": "A", "system": "sklik", "id": 1, "cile": {"typ": "marze", "hodnota": 1}}]}, "cile.typ"),
    ({"ucty": [{"nazev": "A", "system": "sklik", "id": 1, "hlidat": ["akce"]}]}, "potřebuje blok „cile“"),
    ({"ucty": [{"nazev": "A", "system": "sklik", "id": 1, "posledni_zmena": "1. 10."}]}, "RRRR-MM-DD"),
    ({"planovani": {"frekvence": "hodinove"}, "ucty": []}, "frekvence"),
    ({"planovani": {"akce_casy": ["patek 18:00"]}, "ucty": []}, "akce_casy"),
    ({"ucty": [{"nazev": "A", "system": "sklik", "id": 1, "limity": {"max_navyseni_pct": 150}}]}, "100 %"),
])
def test_config_chyby_jsou_cesky(data, hlaska):
    with pytest.raises(SystemExit) as e:
        config.rozparsuj(data)
    assert hlaska in str(e.value)


def test_config_chybejici_soubor(tmp_path):
    with pytest.raises(SystemExit) as e:
        config.nacti(tmp_path / "neni.json")
    assert "Zkopíruj vzor" in str(e.value)


def test_vzorovy_config_je_platny():
    cfg = config.nacti(KOREN / "scripts" / "hlidac" / "ucty.example.json")
    assert len(config.ucty_pro(cfg, "akce")) == 3


def test_ma_bezet_podle_frekvence():
    patek, sobota, pondeli = date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 19)
    assert config.ma_bezet({"frekvence": "pracovni-dny"}, patek)
    assert not config.ma_bezet({"frekvence": "pracovni-dny"}, sobota)
    assert config.ma_bezet({"frekvence": "tydne"}, pondeli) and not config.ma_bezet({"frekvence": "tydne"}, patek)
    assert config.ma_bezet({"frekvence": "tydne", "den": "fri"}, patek)


def test_hlidac_vykyvu_preskoci_ucet_bez_vykyvy(tmp_path):
    import hlidac
    cesta = tmp_path / "ucty.json"
    cesta.write_text(json.dumps({"ucty": [
        {"nazev": "A", "system": "sklik", "id": 1, "hlidat": ["cile"], "cile": {"typ": "pno", "hodnota": 10}},
        {"nazev": "B", "system": "sklik", "id": 2}]}), encoding="utf-8")
    assert [u["nazev"] for u in hlidac.nacti_ucty(cesta)] == ["B"]


# ------------------------------------------------------------------ celý běh bez sítě
@pytest.fixture
def falesne_zdroje(monkeypatch):
    def ucet_dny(u, od, do):
        return dny(date.fromisoformat(od), (date.fromisoformat(do) - date.fromisoformat(od)).days + 1,
                   hodnota=4545 if u["system"] == "google" else 8000), []
    modul = types.SimpleNamespace(ucet_dny=ucet_dny)
    monkeypatch.setitem(sys.modules, "zdroje", modul)
    return modul


def test_cely_beh_report_json_a_exit_kod(tmp_path, monkeypatch, falesne_zdroje, capsys):
    import cile
    (tmp_path / "clients").mkdir()
    (tmp_path / "clients" / "muj-eshop.md").write_text(CHANGELOG, encoding="utf-8")
    cesta = tmp_path / "ucty.json"
    cesta.write_text(json.dumps({"ucty": [
        {"nazev": "Můj e-shop", "klient": "muj-eshop", "system": "google", "id": "123-456-7890",
         "hlidat": ["cile"], "cile": {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 31000}},
        {"nazev": "Můj e-shop", "system": "sklik", "id": 123456, "hlidat": ["cile"],
         "cile": {"typ": "pno", "hodnota": 15}},
        {"nazev": "Bez cílů", "system": "meta", "id": "act_1", "hlidat": ["vykyvy"]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(cile, "ROOT", tmp_path)
    kod = cile.main(["--ucty", str(cesta), "--datum", "2026-10-18", "--json"])
    vystup = json.loads(capsys.readouterr().out)
    assert kod == 2                                         # Google: PNO 22 % → červená
    stavy = {(u["system"], u["stav"]) for u in vystup["ucty"]}
    assert stavy == {("google", "cervena"), ("sklik", "zelena")}
    google = next(u for u in vystup["ucty"] if u["system"] == "google")
    assert google["okno"]["zdroj"] == "changelog" and google["okno"]["od"] == "2026-10-01"
    report = (tmp_path / "reports" / "hlidac-cilu" / "2026-10-18.md").read_text(encoding="utf-8")
    assert "🔴 Můj e-shop (Google Ads)" in report and "8 týdnů po týdnech" in report


def test_podle_planu_o_vikendu_nebezi(tmp_path, monkeypatch, falesne_zdroje):
    import cile
    cesta = tmp_path / "ucty.json"
    cesta.write_text(json.dumps({"planovani": {"frekvence": "pracovni-dny"}, "ucty": [
        {"nazev": "A", "system": "sklik", "id": 1, "cile": {"typ": "pno", "hodnota": 15}}]}), encoding="utf-8")
    monkeypatch.setattr(cile, "ROOT", tmp_path)
    assert cile.main(["--ucty", str(cesta), "--datum", "2026-10-16", "--podle-planu"]) == 0  # sobota
    assert not (tmp_path / "reports").exists()


def test_odkazovane_skilly_existuji():
    """Každý skill, na který návrhy odkazují, musí v appce existovat."""
    zdroj = (KOREN / "scripts" / "hlidac" / "pravidla_cile.py").read_text(encoding="utf-8")
    zdroj += (KOREN / "scripts" / "hlidac" / "pravidla_akce.py").read_text(encoding="utf-8")
    skilly = set(re.findall(r"skill(?:em)? `([a-z0-9_-]+)`", zdroj))
    assert skilly, "návrhy mají odkazovat na skilly"
    for s in skilly:
        assert (KOREN / ".claude" / "skills" / s / "SKILL.md").exists(), s

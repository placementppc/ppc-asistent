"""Testy začernění tokenů v chybových hláškách (scripts/lib/redact.py + Meta klienti + hlídač).

Bez sítě — requests se mockuje. Spuštění: python3 -m pytest tests/test_redact.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

KOREN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOREN / "scripts"))

from lib.redact import redact, redact_exc  # noqa: E402

TOKEN = "EAAB" + "x" * 40  # smyšlený token, jen pro test


def _nacti(nazev: str, cesta: Path):
    spec = importlib.util.spec_from_file_location(nazev, cesta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_redact_url_parametr():
    url = f"https://graph.facebook.com/v21.0/act_1234567890/insights?fields=spend&access_token={TOKEN}&limit=5"
    out = redact(f"429 Client Error: Too Many Requests for url: {url}")
    assert TOKEN not in out
    assert "access_token=***" in out
    assert "limit=5" in out and "fields=spend" in out


def test_redact_dalsi_tajne_parametry_a_bearer():
    out = redact(f"refresh_token={TOKEN} client_secret=abc123 Authorization: Bearer {TOKEN}")
    assert TOKEN not in out and "abc123" not in out
    assert "refresh_token=***" in out and "client_secret=***" in out and "Bearer ***" in out


def test_redact_url_encoded_a_bez_tokenu():
    assert TOKEN not in redact(f"next=...%26access_token%3D{TOKEN}")
    assert redact("Účet nešel načíst: HTTP 500") == "Účet nešel načíst: HTTP 500"


def test_redact_exc_nazev_vyjimky():
    out = redact_exc(ValueError(f"bad url ?access_token={TOKEN}"))
    assert out.startswith("ValueError: ") and TOKEN not in out


def test_meta_client_sitova_chyba_bez_tokenu():
    requests = pytest.importorskip("requests")
    client = _nacti("meta_client_test", KOREN / "scripts" / "meta" / "client.py")
    mc = client.MetaClient(token=TOKEN)
    chyba = requests.ConnectionError(
        f"HTTPSConnectionPool(host='graph.facebook.com'): Max retries exceeded with url: "
        f"/v21.0/act_1/ads?access_token={TOKEN}"
    )
    with mock.patch.object(client.requests, "get", side_effect=chyba):
        with pytest.raises(SystemExit) as e:
            mc.get("act_1/ads")
    assert TOKEN not in str(e.value)
    assert "access_token=***" in str(e.value)


def test_meta_fetch_rate_limit_bez_tokenu():
    pytest.importorskip("requests")
    fetch = _nacti("meta_fetch_test", KOREN / "scripts" / "meta" / "fetch.py")

    class Odpoved:
        status_code = 429
        text = f'{{"error": {{"message": "limit", "code": 17}}, "url": "?access_token={TOKEN}"}}'

        def json(self):
            return {"error": {"message": f"User request limit reached ?access_token={TOKEN}",
                              "code": 17, "error_subcode": 2446079}}

    with mock.patch.object(fetch.requests, "get", return_value=Odpoved()), \
            mock.patch.object(fetch.time, "sleep"):
        with pytest.raises(SystemExit) as e:
            fetch.api_get("act_1/insights", {}, TOKEN)
    assert TOKEN not in str(e.value)


def test_hlidac_report_bez_tokenu(tmp_path, monkeypatch):
    """Chyba konektoru s tokenem v URL nesmí skončit v reportu hlídače."""
    sys.path.insert(0, str(KOREN / "scripts" / "hlidac"))
    hlidac = _nacti("hlidac_test", KOREN / "scripts" / "hlidac" / "hlidac.py")

    def spadne(*_a, **_k):
        raise RuntimeError(f"500 Server Error for url: https://graph.facebook.com/x?access_token={TOKEN}")

    ucet = {"nazev": "Můj e-shop", "system": "meta", "id": "act_1234567890", "min_utrata": 0}
    monkeypatch.setattr(hlidac, "nacti_ucty", lambda _p: [ucet])
    monkeypatch.setattr(hlidac, "zkontroluj", spadne)
    monkeypatch.setattr(hlidac, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["hlidac.py", "--datum", "2026-10-18"])
    hlidac.main()
    report = (tmp_path / "reports" / "hlidac" / "2026-10-18.md").read_text(encoding="utf-8")
    assert "Účet nešel načíst" in report
    assert TOKEN not in report and "access_token=***" in report


def test_meta_resolve_identity_sitova_chyba_bez_tokenu(monkeypatch):
    requests = pytest.importorskip("requests")
    ri = _nacti("meta_resolve_identity_test", KOREN / "scripts" / "meta" / "resolve_identity.py")
    chyba = requests.ConnectionError(
        f"HTTPSConnectionPool(host='graph.facebook.com'): Max retries exceeded with url: "
        f"/v21.0/act_1234567890/adcreatives?access_token={TOKEN}&limit=5"
    )
    monkeypatch.setattr(ri, "require", lambda *_a: {"META_API_TOKEN": TOKEN})
    monkeypatch.setattr(sys, "argv", ["resolve_identity.py", "1234567890"])
    with mock.patch.object(ri.requests, "get", side_effect=chyba):
        with pytest.raises(SystemExit) as e:
            ri.main()
    assert TOKEN not in str(e.value)
    assert "access_token=***" in str(e.value)


def test_meta_resolve_identity_http_chyba_bez_tokenu(monkeypatch):
    pytest.importorskip("requests")
    ri = _nacti("meta_resolve_identity_test2", KOREN / "scripts" / "meta" / "resolve_identity.py")

    class Odpoved:
        status_code = 400
        text = f'{{"error": {{"message": "bad"}}, "url": "?access_token={TOKEN}"}}'

    monkeypatch.setattr(ri, "require", lambda *_a: {"META_API_TOKEN": TOKEN})
    monkeypatch.setattr(sys, "argv", ["resolve_identity.py", "1234567890"])
    with mock.patch.object(ri.requests, "get", return_value=Odpoved()):
        with pytest.raises(SystemExit) as e:
            ri.main()
    assert TOKEN not in str(e.value)


def test_sklik_fetch_vystup_bez_session():
    sys.path.insert(0, str(KOREN / "scripts" / "sklik"))
    pytest.importorskip("requests")
    fetch = _nacti("sklik_fetch_test", KOREN / "scripts" / "sklik" / "fetch.py")
    odpoved = {"status": 200, "session": "tajna-session-123",
               "campaigns": [{"id": 1, "name": "Kampaň", "session": "x"}]}
    out = fetch.strip_secrets(odpoved)
    assert "session" not in out and "session" not in out["campaigns"][0]
    assert out["campaigns"][0]["name"] == "Kampaň"


def test_sanitize_zahodi_session():
    import sanitize as san
    assert "session" in san.DROP_KEYS


def test_lib_strip_secrets_rekurzivne():
    from lib.redact import strip_secrets
    odpoved = {"status": 400, "session": "tajna-session-123",
               "diagnostics": [{"session": "y", "msg": "chyba"}], "limits": ({"session": "z"},)}
    out = strip_secrets(odpoved)
    assert "tajna-session-123" not in str(out) and "session" not in str(out)
    assert out["diagnostics"][0]["msg"] == "chyba" and out["status"] == 400
    assert odpoved["session"] == "tajna-session-123"  # originál zůstal beze změny


def test_sklik_update_product_set_bids_chyba_bez_session(tmp_path, monkeypatch):
    pytest.importorskip("requests")
    sys.path.insert(0, str(KOREN / "scripts" / "sklik"))
    mod = _nacti("sklik_upsb_test", KOREN / "scripts" / "sklik" / "update_product_set_bids.py")

    class FalesneApi:
        def __init__(self, user_id):
            pass

        def call(self, method, *params, managed=True):
            return {"status": 401, "statusMessage": "Unauthorized", "session": "tajna-session-123"}

    plan = tmp_path / "plan.json"
    plan.write_text('{"user_id": 1, "changes": [{"id": 1, "to_cpc_halers": 100}]}', encoding="utf-8")
    monkeypatch.setattr(mod, "Api", FalesneApi)
    monkeypatch.setattr(sys, "argv", ["update_product_set_bids.py", str(plan)])
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "tajna-session-123" not in str(e.value)
    assert "Unauthorized" in str(e.value)

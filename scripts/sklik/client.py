"""Sklik API klient (JSON-RPC / "drak"). Read-only orientovaný.

Pozn.: Sklik API se vyvíjí — názvy metod a tvar parametrů ověř v aktuální
dokumentaci https://api.sklik.cz/ . Tento klient je obecný JSON-RPC wrapper:
posílá POST na <base>/<method> s tělem = pole parametrů.

ENV: SKLIK_API_TOKEN (token z účtu), volitelně SKLIK_API_URL. Agenturní token: SKLIK_TOKEN_VAR=SKLIK_DRUHY_TOKEN
(název proměnné, hodnotu si klient načte sám).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402

DEFAULT_URL = "https://api.sklik.cz/drak/json"


class SklikError(RuntimeError):
    pass


class SklikClient:
    def __init__(self) -> None:
        # SKLIK_TOKEN_VAR = NÁZEV proměnné s tokenem (např. SKLIK_DRUHY_TOKEN pro agenturní přístup).
        # Hodnotu si skript načte z .env sám — v příkazu se předává jen název, nikdy token.
        var = os.environ.get("SKLIK_TOKEN_VAR", "SKLIK_API_TOKEN")
        self.token = require(var)[var]
        self.base = os.environ.get("SKLIK_API_URL", DEFAULT_URL)
        self.session: str | None = None

    def _post(self, method: str, params: list) -> dict:
        url = f"{self.base}/{method}"
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        # Sklik vrací status 200 + pole "status"/"statusMessage"
        if isinstance(payload, dict) and payload.get("status") not in (200, None):
            raise SklikError(f"{method}: {payload.get('status')} {payload.get('statusMessage')}")
        return payload

    def login(self) -> "SklikClient":
        """Přihlášení tokenem -> uloží session."""
        resp = self._post("client.loginByToken", [self.token])
        self.session = resp.get("session")
        if not self.session:
            raise SklikError("Login selhal: nevrácena session. Ověř SKLIK_API_TOKEN a metodu API.")
        return self

    def call(self, method: str, *params, user_id: int | None = None) -> dict:
        """Volání metody se session. Pro agenturní (cizí) účet předej user_id."""
        if not self.session:
            self.login()
        ctx: dict = {"session": self.session}
        if user_id is not None:
            from lib.nda import guard
            guard(user_id, getattr(self, "nda_kind", "any"))
            ctx["userId"] = int(user_id)
        return self._post(method, [ctx, *params])

    # ---- limity dávek ----------------------------------------------------
    # Sklik říká přes `api.limits`, kolik položek smí jít v jedné dávce. Dosud
    # to četl jen `apply_sitelink_changes.py`; ostatní zápisové skripty dávku
    # posílaly naslepo a při překročení spadly uprostřed. Tohle to sjednocuje.
    _limits: dict | None = None

    def limits(self, refresh: bool = False) -> dict:
        """Načte (a zapamatuje si) limity API."""
        if self._limits is None or refresh:
            self._limits = self.call("api.limits", user_id=None)
        return self._limits

    def batch_limit(self, name: str, default: int = 100) -> int:
        """Maximální počet položek v jedné dávce pro danou metodu.

        `name` je klíč ze Skliku, např. `global.create` nebo `global.check`.
        Když ho Sklik nezná, vrátí se konzervativní `default`.
        """
        for item in (self.limits().get("batchCallLimits") or []):
            if item.get("name") == name:
                return int(item.get("limit", default))
        return default

    def chunks(self, items: list, method: str, default: int = 100):
        """Rozseká seznam na dávky, které Sklik ještě přijme.

        Použití:
            for davka in api.chunks(operace, "global.create"):
                api.call(..., davka)
        """
        size = max(1, self.batch_limit(method, default))
        for i in range(0, len(items), size):
            yield items[i:i + size]

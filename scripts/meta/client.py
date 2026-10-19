#!/usr/bin/env python3
"""Meta Graph API — READ-ONLY klient pro produktový report.

Tenhle modul potřebuje `product_report.py`. Drží stejná pravidla jako `fetch.py`:
- **jen čtení**, žádné zápisy do účtu,
- token z `META_API_TOKEN` v `.env` (system-user token s `ads_read`),
- na rate-limit (kódy 4/17/32/613 nebo HTTP 429) čeká a zkouší znovu (backoff),
- stránkuje přes `paging.next`, nikdy neběží paralelně.

Verze API se bere z `META_API_VERSION` (default v21.0).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402
from lib.redact import redact  # noqa: E402

RATE_LIMIT_CODES = (4, 17, 32, 613)


def normalize_account_id(account: str | int) -> str:
    """`123`, `act_123`, `ACT_123` i `act_ 123` → `act_123`."""
    a = str(account).strip().replace(" ", "")
    if not a:
        raise SystemExit("Chybí ID účtu (--account act_XXXX).")
    a = a.lower()
    if a.startswith("act_"):
        a = a[4:]
    if not a.isdigit():
        raise SystemExit(f"ID účtu má být číslo nebo act_<číslo>, dostal jsem: {account}")
    return f"act_{a}"


class MetaClient:
    """Minimální čtecí klient nad Graph API."""

    def __init__(self, token: str | None = None, version: str | None = None) -> None:
        self.token = token or require("META_API_TOKEN")["META_API_TOKEN"]
        self.version = version or os.environ.get("META_API_VERSION", "v21.0")
        self.base = f"https://graph.facebook.com/{self.version}"

    # --- vnitřní ---------------------------------------------------------
    def _is_rate_limit(self, r: requests.Response) -> bool:
        try:
            return r.json().get("error", {}).get("code") in RATE_LIMIT_CODES
        except ValueError:
            return False

    def _die(self, r: requests.Response) -> None:
        try:
            err = r.json().get("error", {})
            raise SystemExit(redact(
                f"Meta API chyba (HTTP {r.status_code}, code {err.get('code')}/"
                f"{err.get('error_subcode')}): {err.get('message', r.text)}"
            ))
        except ValueError:
            raise SystemExit(redact(f"Meta API chyba (HTTP {r.status_code}): {r.text[:400]}"))

    @staticmethod
    def _request(url: str, params: dict | None = None) -> requests.Response:
        """GET s tokenem v URL. Síťová chyba nese URL i s tokenem → zpráva se začerní."""
        try:
            return requests.get(url, params=params, timeout=90)
        except requests.RequestException as e:
            raise SystemExit(f"Meta API nedostupné: {redact(e)}") from None

    # --- veřejné ---------------------------------------------------------
    def get(self, path: str, **params) -> dict:
        """Jedno volání bez stránkování. Vrací celou odpověď."""
        url = f"{self.base}/{str(path).lstrip('/')}"
        params = {k: v for k, v in params.items() if v is not None}
        params["access_token"] = self.token
        backoff = 2
        while True:
            r = self._request(url, params)
            if r.status_code == 429 or (r.status_code >= 400 and self._is_rate_limit(r)):
                if backoff > 64:
                    self._die(r)
                time.sleep(backoff)
                backoff *= 2
                continue
            if r.status_code >= 400:
                self._die(r)
            return r.json()

    def get_all(self, path: str, **params) -> list[dict]:
        """Projde všechny stránky a vrátí seznam řádků z `data`."""
        payload = self.get(path, **params)
        out: list[dict] = list(payload.get("data", []))
        nxt = payload.get("paging", {}).get("next")
        backoff = 2
        while nxt:
            r = self._request(nxt)  # 'next' už nese token i kurzor
            if r.status_code == 429 or (r.status_code >= 400 and self._is_rate_limit(r)):
                if backoff > 64:
                    self._die(r)
                time.sleep(backoff)
                backoff *= 2
                continue
            if r.status_code >= 400:
                self._die(r)
            payload = r.json()
            out.extend(payload.get("data", []))
            nxt = payload.get("paging", {}).get("next")
            backoff = 2
        return out

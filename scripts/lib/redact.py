"""Začernění tajných hodnot v chybových hláškách (tokeny v URL apod.).

Proč: Meta Graph API bere token jako parametr `access_token` v URL. Výjimky z `requests`
(HTTPError, ConnectionError, Timeout) mají URL i s tokenem ve zprávě — a hlídače tu zprávu
tisknou do reportu, do e-mailu nebo do konverzace s AI. Každou chybu, která může nést URL,
proto před výpisem proženeme přes `redact()`.
"""
from __future__ import annotations

import re

# Názvy parametrů, jejichž hodnota se nikdy nesmí objevit ve výpisu.
_SECRET_PARAMS = (
    "access_token",
    "fb_exchange_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "appsecret_proof",
)

_PARAM_RE = re.compile(
    r"(?<![A-Za-z_])(?P<name>(?:" + "|".join(_SECRET_PARAMS) + r"))(?P<sep>=|%3D)(?P<val>[^&\s\"'<>]+)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(?P<pre>\bBearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact(text: object) -> str:
    """Vrátí text se začerněnými tokeny: `access_token=abc` → `access_token=***`."""
    s = str(text)
    s = _PARAM_RE.sub(lambda m: f"{m.group('name')}{m.group('sep')}***", s)
    s = _BEARER_RE.sub(lambda m: f"{m.group('pre')}***", s)
    return s


def redact_exc(e: BaseException) -> str:
    """Čitelný popis výjimky bez tajných hodnot (pro výpis do reportu)."""
    if isinstance(e, SystemExit):
        return redact(e)
    return redact(f"{type(e).__name__}: {e}")


# Pole odpovědí API, která se nikdy nevypisují: `session` je přihlašovací token Skliku
# (vrací se v každé odpovědi a dá se s ním volat API za uživatele).
SECRET_KEYS = frozenset({"session"})


def strip_secrets(obj):
    """Vrátí kopii odpovědi bez tajných polí (rekurzivně přes slovníky a seznamy)."""
    if isinstance(obj, dict):
        return {k: strip_secrets(v) for k, v in obj.items() if k not in SECRET_KEYS}
    if isinstance(obj, (list, tuple)):
        return [strip_secrets(v) for v in obj]
    return obj

"""Načítání konfigurace z .env (kořen projektu). Bez externích závislostí."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def load_env() -> dict[str, str]:
    """Načte .env do os.environ (pokud existuje) a vrátí dict hodnot.

    Nepřepisuje už nastavené proměnné prostředí (ty mají přednost).
    """
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            values[key] = val
            os.environ.setdefault(key, val)
    return values


def require(*keys: str) -> dict[str, str]:
    """Vrátí požadované klíče nebo srozumitelně selže s návodem."""
    load_env()
    out, missing = {}, []
    for k in keys:
        v = os.environ.get(k)
        if not v:
            missing.append(k)
        else:
            out[k] = v
    if missing:
        raise SystemExit(
            "Chybí proměnné v .env: " + ", ".join(missing) +
            f"\nDoplň je do {ENV_PATH} (vzor viz .env.example)."
        )
    return out

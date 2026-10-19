#!/usr/bin/env python3
"""Jednorázové vygenerování GOOGLE_ADS_REFRESH_TOKEN (OAuth2 Installed App flow).

Spustíš JEDNOU. Otevře prohlížeč, přihlásíš se Google účtem, který má přístup do MCC,
odsouhlasíš oprávnění a skript zapíše refresh token rovnou do souboru s přístupy (.env).
Token se NEVYPISUJE: příkaz se spouští přes `!` v Claude Code a všechno, co skript vypíše,
by skončilo v konverzaci.

Potřebuje v .env vyplněné GOOGLE_ADS_CLIENT_ID a GOOGLE_ADS_CLIENT_SECRET
(OAuth client typu "Desktop app" z Google Cloud Console). Soubor zakládáš ty sám
(`cp .env.example .env`), skript do něj jen doplní nebo přepíše řádek s tokenem.

Použití:
  ! .venv/bin/python scripts/google_ads/generate_refresh_token.py                # zapíše do .env (výchozí)
  .venv/bin/python scripts/google_ads/generate_refresh_token.py --print-token    # jen vypíše token

--print-token spouštěj jen v obyčejném terminálu MIMO Claude Code (token se objeví
na obrazovce a v historii terminálu). Volba --write-env zůstala kvůli zpětné
kompatibilitě a dělá totéž co výchozí chování.

Druhý MCC (jiný Cloud projekt): GOOGLE_ADS_PROFILE=druhy před příkaz → čte a zapisuje
GOOGLE_ADS_DRUHY_*; výchozí GOOGLE_ADS_* se nedotkne.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402

# adwords = Google Ads API; analytics.readonly = GA4 Data API (read-only reporty)
SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def _print_token(px: str, token: str) -> None:
    """Výpis tokenu na obrazovku — jen na výslovné přání (--print-token)."""
    print("\n" + "=" * 60)
    print("⚠️  Refresh token je tajný údaj. Nevkládej ho do chatu s AI ani nikam nesdílej.")
    print("   Pokud tohle běží uvnitř Claude Code, token je teď v konverzaci: odvolej přístup")
    print("   aplikace v účtu Google (Zabezpečení → Aplikace třetích stran) a vygeneruj nový")
    print("   bez --print-token.")
    print("Vlož tuto hodnotu do souboru s přístupy:")
    print(f"\n{px}REFRESH_TOKEN={token}\n")
    print("=" * 60)


def _write_env(px: str, token: str) -> None:
    """Doplní / přepíše řádek <px>REFRESH_TOKEN v souboru s přístupy. Hodnotu nevypisuje."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        raise SystemExit(
            "Soubor s přístupy (.env) neexistuje. Založ ho sám (`cp .env.example .env`), "
            f"doplň {px}CLIENT_ID a {px}CLIENT_SECRET a spusť skript znovu."
        )
    text = env_path.read_text(encoding="utf-8")
    new_line = f"{px}REFRESH_TOKEN={token}"
    pattern = rf"^{re.escape(px)}REFRESH_TOKEN=.*$"
    if re.search(pattern, text, flags=re.M):
        text = re.sub(pattern, lambda _m: new_line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + new_line + "\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"\n✓ Hotovo. Nový {px}REFRESH_TOKEN (scopes: adwords + analytics.readonly) "
          "zapsán do .env. Hodnotu záměrně nevypisuju.")


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise SystemExit(
            "Chybí google-auth-oauthlib. Nainstaluj: .venv/bin/pip install -r requirements.txt"
        ) from e

    profile = (os.environ.get("GOOGLE_ADS_PROFILE") or "").strip().upper()
    px = f"GOOGLE_ADS_{profile}_" if profile else "GOOGLE_ADS_"
    cfg = require(px + "CLIENT_ID", px + "CLIENT_SECRET")
    client_config = {
        "installed": {
            "client_id": cfg[px + "CLIENT_ID"],
            "client_secret": cfg[px + "CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    # Otevře prohlížeč a poslouchá na localhostu na callback.
    creds = flow.run_local_server(port=0, prompt="consent")

    if "--print-token" in sys.argv:
        _print_token(px, creds.refresh_token)
    else:
        _write_env(px, creds.refresh_token)


if __name__ == "__main__":
    main()

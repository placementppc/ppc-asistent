"""Google Ads API klient sestavený z .env (MCC + OAuth)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402


def env_prefix() -> str:
    """Prefix proměnných podle profilu (druhý MCC / druhý Cloud projekt).

    Bez GOOGLE_ADS_PROFILE se čtou výchozí GOOGLE_ADS_* (hlavní MCC). S profilem,
    např. GOOGLE_ADS_PROFILE=druhy, se čtou GOOGLE_ADS_DRUHY_* — výchozí sada zůstává nedotčená.
    """
    profile = (os.environ.get("GOOGLE_ADS_PROFILE") or "").strip().upper()
    return f"GOOGLE_ADS_{profile}_" if profile else "GOOGLE_ADS_"


def build_client():
    """Vytvoří GoogleAdsClient z proměnných v .env.

    Vyžaduje: GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN,
    GOOGLE_ADS_LOGIN_CUSTOMER_ID (MCC).

    GOOGLE_ADS_DEVELOPER_TOKEN je od 9. 9. 2026 nepovinný: Google developer tokeny zrušil,
    úroveň přístupu určuje Cloud projekt, ze kterého pochází OAuth klient. Knihovna google-ads
    klíč v konfiguraci pořád vyžaduje, API ho ignoruje, proto se bez hodnoty posílá zástupný text.
    """
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as e:
        raise SystemExit(
            "Chybí knihovna google-ads. Nainstaluj: pip install -r requirements.txt"
        ) from e

    px = env_prefix()
    cfg = require(
        px + "CLIENT_ID",
        px + "CLIENT_SECRET",
        px + "REFRESH_TOKEN",
        px + "LOGIN_CUSTOMER_ID",
    )
    config = {
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN") or "UNUSED",
        "client_id": cfg[px + "CLIENT_ID"],
        "client_secret": cfg[px + "CLIENT_SECRET"],
        "refresh_token": cfg[px + "REFRESH_TOKEN"],
        # MCC login customer id — jen číslice, bez pomlček
        "login_customer_id": cfg[px + "LOGIN_CUSTOMER_ID"].replace("-", ""),
        "use_proto_plus": True,
    }
    return GoogleAdsClient.load_from_dict(config)


def normalize_cid(customer_id: str, nda_kind: str = "any") -> str:
    """ID klienta -> jen číslice (123-456-7890 -> 1234567890).

    Zároveň NDA pojistka (scripts/lib/nda.py): u NDA klienta v nepovolené relaci
    skript zastaví dřív, než cokoli stáhne nebo zapíše.
    """
    cid = customer_id.replace("-", "").strip()
    from lib.nda import guard
    guard(cid, nda_kind)
    return cid

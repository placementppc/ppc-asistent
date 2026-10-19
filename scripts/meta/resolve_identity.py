#!/usr/bin/env python3
"""Najde Facebook Page a Instagram identitu z existující Meta kreativy.

Použití:
  .venv/bin/python scripts/meta/resolve_identity.py 0000000000

Čte jen prvních pět kreativ a jen jejich identity. Nečte výkon, útratu ani
stav kampaní a nic nezapisuje.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402
from lib.redact import redact  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Meta Page/Instagram identity")
    parser.add_argument("ad_account_id", help="Číselné ID účtu, bez act_")
    args = parser.parse_args()

    account = str(args.ad_account_id).strip()
    if account.lower().startswith("act_"):
        account = account[4:]
    if not account.isdigit():
        raise SystemExit("ID účtu musí být číslo (bez act_).")

    # NDA pojistka jako u ostatních Meta čtecích skriptů.
    from lib.nda import guard
    guard(f"act_{account}", "read-raw")

    token = require("META_API_TOKEN")["META_API_TOKEN"]
    try:
        response = requests.get(
            f"https://graph.facebook.com/v21.0/act_{account}/adcreatives",
            params={
                "access_token": token,
                "fields": "id,name,object_story_spec,instagram_actor_id",
                "limit": 5,
            },
            timeout=60,
        )
    except requests.RequestException as e:
        # výjimka z requests nese URL i s access_token → začernit
        raise SystemExit(f"Meta API nedostupné: {redact(e)}") from None
    if response.status_code >= 400:
        raise SystemExit(redact(f"Meta API {response.status_code}: {response.text[:500]}"))

    for creative in response.json().get("data", []):
        spec = creative.get("object_story_spec") or {}
        page_id = spec.get("page_id")
        instagram_id = spec.get("instagram_user_id") or creative.get("instagram_actor_id")
        if page_id:
            print(json.dumps({
                "page_id": page_id,
                "instagram_user_id": instagram_id,
                "source_creative_id": creative.get("id"),
                "source_creative_name": creative.get("name"),
            }, ensure_ascii=False, indent=2))
            return

    raise SystemExit(
        "V prvních pěti kreativách není object_story_spec.page_id. "
        "Teprve nyní vyžádej Page ID nebo rozšiř bezpečně limit po malých dávkách."
    )


if __name__ == "__main__":
    main()

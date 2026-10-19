#!/usr/bin/env python3
"""Nahraje obrázky do Meta Ads a vypíše jejich image hash.

Použití:
  .venv/bin/python scripts/meta/upload_images.py act_123 /abs/cesta/banner.png [...]

Vyžaduje META_API_TOKEN v .env. Zápis je záměrný: obrázky se uloží pouze do
obrazové knihovny uvedeného reklamního účtu; nic se nezveřejňuje ani nespouští.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload Meta Ads images")
    parser.add_argument("ad_account", help="act_<id>")
    parser.add_argument("images", nargs="+", type=Path)
    args = parser.parse_args()

    token = require("META_API_TOKEN")["META_API_TOKEN"]
    out: list[dict[str, str]] = []
    for image in args.images:
        if not image.is_file():
            raise SystemExit(f"Soubor neexistuje: {image}")
        with image.open("rb") as handle:
            response = requests.post(
                f"https://graph.facebook.com/v21.0/{args.ad_account}/adimages",
                data={"access_token": token, "name": image.name},
                files={"filename": (image.name, handle, "image/png")},
                timeout=90,
            )
        if response.status_code >= 400:
            raise SystemExit(f"Meta API {response.status_code}: {response.text[:500]}")
        images = response.json().get("images", {})
        info = images.get(image.name)
        if not info or not info.get("hash"):
            raise SystemExit(f"Meta nevrátila hash obrázku: {response.text[:500]}")
        out.append({"file": str(image), "hash": info["hash"]})
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Změna final_urls u existujících reklam (AdService.MutateAds) podle plánu (JSON).

Typické použití: oprava 404 / http → https a vyvolání nové kontroly zamítnuté reklamy
(změna URL spustí nové posouzení). Výkon reklamy zůstává, ID se nemění.

BEZPEČNOST:
- Výchozí režim DRY-RUN: dávka jde s validate_only=True — Google ji zkontroluje, nic nezapíše.
- Zápis jen s --apply. partial_failure=True: neměnitelné typy reklam se vypíšou a zbytek projde.
- Skript před plánem ověří, že každá nová URL odpovídá HTTP 200 bez přesměrování.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/update_ad_urls.py clients/<plan>.json [--apply]

Schéma plánu:
{"customer_id": "0000000000",
 "ads": [{"ad_id": "123", "from": "http://…", "to": "https://…/"}]}
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None


def check_url(url: str) -> int:
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "AdsBot-Google (+http://www.google.com/adsbot.html)"})
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> None:
    p = argparse.ArgumentParser(description="Změna final_urls reklam (dry-run bez --apply)")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    cid = normalize_cid(plan["customer_id"], "write")
    bad = {row["to"]: code for row in plan["ads"] if (code := check_url(row["to"])) != 200}
    if bad:
        raise SystemExit(f"Nová URL neodpovídá 200 bez přesměrování: {bad}")

    client = build_client()
    svc = client.get_service("AdService")
    ops = []
    for row in plan["ads"]:
        op = client.get_type("AdOperation")
        op.update.resource_name = f"customers/{cid}/ads/{row['ad_id']}"
        op.update.final_urls.append(row["to"])
        op.update_mask.paths.append("final_urls")
        ops.append(op)

    req = client.get_type("MutateAdsRequest")
    req.customer_id = cid
    req.operations.extend(ops)
    req.partial_failure = True
    req.validate_only = not args.apply
    resp = svc.mutate_ads(request=req)

    failed = set()
    if resp.partial_failure_error.code:
        failure = client.get_type("GoogleAdsFailure")
        for detail in resp.partial_failure_error.details:
            failure = type(failure).deserialize(detail.value)
            for err in failure.errors:
                idx = err.location.field_path_elements[0].index
                failed.add(idx)
                print(f"✗ reklama {plan['ads'][idx]['ad_id']}: {err.message}")
    for i, row in enumerate(plan["ads"]):
        if i not in failed:
            mode = "ZAPSÁNO" if args.apply else "OK (validate_only)"
            print(f"✓ {mode} reklama {row['ad_id']}: {row['from']} → {row['to']}")
    print(f"Celkem {len(ops)}, chyb {len(failed)}" + ("" if args.apply else " — DRY-RUN, nic nezapsáno"))


if __name__ == "__main__":
    main()

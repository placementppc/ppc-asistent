#!/usr/bin/env python3
"""Pozastavení / zapnutí kampaní (jen status, nic jiného).

BEZPEČNOST: výchozí DRY-RUN (validate_only), zápis jen s --apply. Rozpočty ani nastavení nemění.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/set_campaign_status.py <customer_id> PAUSED <campaign_id> [...] [--apply]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Status kampaní (dry-run bez --apply)")
    p.add_argument("customer_id")
    p.add_argument("status", choices=["PAUSED", "ENABLED"])
    p.add_argument("campaign_ids", nargs="+")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id, "write")
    client = build_client()
    ops = []
    for camp in args.campaign_ids:
        op = client.get_type("CampaignOperation")
        op.update.resource_name = f"customers/{cid}/campaigns/{camp}"
        op.update.status = getattr(client.enums.CampaignStatusEnum, args.status)
        op.update_mask.paths.append("status")
        ops.append(op)
    req = client.get_type("MutateCampaignsRequest")
    req.customer_id = cid
    req.operations.extend(ops)
    req.validate_only = not args.apply
    client.get_service("CampaignService").mutate_campaigns(request=req)
    mode = "ZAPSÁNO" if args.apply else "DRY-RUN OK (validate_only)"
    print(f"{cid}: {mode} — {args.status}: {', '.join(args.campaign_ids)}")


if __name__ == "__main__":
    main()

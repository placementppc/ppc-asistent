#!/usr/bin/env python3
"""Úprava textů existujících RSA a zakládání nových RSA podle plánu (JSON).

BEZPEČNOST:
- Výchozí režim DRY-RUN: validate_only=True, nic se nezapíše.
- Zápis jen s --apply. partial_failure=True — zamítnutá operace se vypíše, ostatní projdou.
- Texty musí předem schválit člověk (pravidlo projektu); skript hlídá jen limity (30/90 znaků,
  3–15 titulků, 2–4 popisky) a že finální URL nových reklam vrací 200 bez přesměrování.
- U existující RSA se mění jen titulky a popisky (ID i statistiky zůstávají). Připnutí
  u ponechaných titulků se zachová.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/apply_rsa_texts.py clients/<plan>.json [--apply]

Schéma plánu: {"<customer_id>": {
  "update": [{"ad_id": "…", "final_headlines": [{"text": "…", "pinnedField": 2?}], "final_descriptions": [{"text": "…"}]}],
  "create": [{"ad_group_id": "…", "final_url": "https://…", "headlines": ["…"], "descriptions": ["…"]}]}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402
from update_ad_urls import check_url  # noqa: E402


def check_texts(heads: list[str], descs: list[str], label: str) -> None:
    if not 3 <= len(heads) <= 15 or not 2 <= len(descs) <= 4:
        raise SystemExit(f"{label}: počet titulků {len(heads)} / popisků {len(descs)} mimo limit")
    for h in heads:
        if len(h) > 30:
            raise SystemExit(f"{label}: titulek > 30 znaků: {h}")
    for d in descs:
        if len(d) > 90:
            raise SystemExit(f"{label}: popisek > 90 znaků: {d}")


def add_assets(client, repeated, items) -> None:
    for it in items:
        asset = client.get_type("AdTextAsset")
        asset.text = it["text"]
        if it.get("pinnedField"):
            asset.pinned_field = it["pinnedField"]
        repeated.append(asset)


def main() -> None:
    p = argparse.ArgumentParser(description="RSA texty: úprava + nové (dry-run bez --apply)")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    client = build_client()
    svc = client.get_service("GoogleAdsService")

    for raw_cid, acc in plan.items():
        if not raw_cid.isdigit():
            continue
        cid = normalize_cid(raw_cid, "write")
        urls = {c["final_url"] for c in acc.get("create", [])}
        bad = {u: code for u in urls if (code := check_url(u)) != 200}
        if bad:
            raise SystemExit(f"{cid}: URL nevrací 200 bez přesměrování: {bad}")

        ops, labels = [], []
        for u in acc.get("update", []):
            heads, descs = u["final_headlines"], u["final_descriptions"]
            check_texts([h["text"] for h in heads], [d["text"] for d in descs], f"ad {u['ad_id']}")
            op = client.get_type("MutateOperation")
            ad = op.ad_operation.update
            ad.resource_name = f"customers/{cid}/ads/{u['ad_id']}"
            add_assets(client, ad.responsive_search_ad.headlines, heads)
            add_assets(client, ad.responsive_search_ad.descriptions, descs)
            op.ad_operation.update_mask.paths.extend(
                ["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
            ops.append(op)
            labels.append(f"úprava RSA {u['ad_id']} ({len(heads)} T / {len(descs)} P)")
        for c in acc.get("create", []):
            check_texts(c["headlines"], c["descriptions"], f"nová RSA v {c['ad_group_id']}")
            op = client.get_type("MutateOperation")
            aga = op.ad_group_ad_operation.create
            aga.ad_group = f"customers/{cid}/adGroups/{c['ad_group_id']}"
            aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
            aga.ad.final_urls.append(c["final_url"])
            add_assets(client, aga.ad.responsive_search_ad.headlines, [{"text": h} for h in c["headlines"]])
            add_assets(client, aga.ad.responsive_search_ad.descriptions, [{"text": d} for d in c["descriptions"]])
            ops.append(op)
            labels.append(f"nová RSA v sestavě {c['ad_group_id']} ({c.get('ad_group', '')})")

        req = client.get_type("MutateGoogleAdsRequest")
        req.customer_id = cid
        req.mutate_operations.extend(ops)
        req.partial_failure = True
        req.validate_only = not args.apply
        resp = svc.mutate(request=req)

        failed = {}
        if resp.partial_failure_error.code:
            for detail in resp.partial_failure_error.details:
                failure = type(client.get_type("GoogleAdsFailure")).deserialize(detail.value)
                for err in failure.errors:
                    idx = err.location.field_path_elements[0].index
                    failed.setdefault(idx, []).append(err.message)
        for i, lab in enumerate(labels):
            if i in failed:
                print(f"✗ {cid} {lab}: {failed[i]}")
        mode = "ZAPSÁNO" if args.apply else "DRY-RUN (validate_only)"
        print(f"{cid}: {mode} — operací {len(ops)}, chyb {len(failed)}")


if __name__ == "__main__":
    main()

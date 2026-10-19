#!/usr/bin/env python3
"""Založení podkladů reklamy (rozšíření + texty PMax) podle schváleného plánu.

Proti jednorázovým skriptům s texty natvrdo v kódu:
  - texty se berou z plánu JSON → auditovatelné, znovupoužitelné,
  - umí KAMPAŇOVÁ rozšíření (sitelink / callout / structured snippet),
  - umí texty ASSET GROUP u PMax (nadpis / popis) a jejich odebrání,
  - délky se kontrolují PŘED odesláním (Google je jinak odmítne až v mutaci),
  - po zápisu si stav přečte zpátky a vypíše, co reálně vzniklo.

BEZPEČNOST: výchozí režim je DRY-RUN. Zápis jen s `--apply` a jen u plánu
s `approval.status = approved`.

Plán (JSON):
{
  "customer_id": "0000000000",
  "approval": {"status": "approved", ...},
  "campaign_assets": [
    {"campaign_id": "0000000000",
     "sitelinks":  [{"text": "...", "desc1": "...", "desc2": "...", "url": "https://..."}],
     "callouts":   ["...", "..."],
     "snippet":    {"header": "Types", "values": ["...", "..."]}}
  ],
  "asset_group_assets": [
    {"asset_group_id": "0000000000",
     "add_headlines": ["..."], "add_descriptions": ["..."],
     "remove_asset_ids": ["123456"]}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client import build_client, normalize_cid  # noqa: E402

# Limity Google Ads. Přetečení Google odmítne až při mutaci a chyba je nečitelná,
# proto se kontroluje předem.
LIMITS = {"headline": 30, "description": 90, "sitelink_text": 25,
          "sitelink_desc": 35, "callout": 25, "snippet_value": 25}


def _check(label: str, text: str, limit_key: str, errs: list) -> None:
    lim = LIMITS[limit_key]
    if len(text) > lim:
        errs.append(f"{label}: {len(text)} znaků > limit {lim} — „{text}“")


def validate(plan: dict) -> list:
    errs: list = []
    for blk in plan.get("campaign_assets", []):
        for s in blk.get("sitelinks", []):
            _check("sitelink text", s["text"], "sitelink_text", errs)
            for k in ("desc1", "desc2"):
                if s.get(k):
                    _check(f"sitelink {k}", s[k], "sitelink_desc", errs)
            if not str(s.get("url", "")).startswith("https://"):
                errs.append(f"sitelink „{s['text']}“ nemá https URL")
        for c in blk.get("callouts", []):
            _check("callout", c, "callout", errs)
        for v in (blk.get("snippet") or {}).get("values", []):
            _check("snippet hodnota", v, "snippet_value", errs)
    for blk in plan.get("asset_group_assets", []):
        for h in blk.get("add_headlines", []):
            _check("nadpis", h, "headline", errs)
        for d in blk.get("add_descriptions", []):
            _check("popis", d, "description", errs)
    return errs


def main() -> None:
    p = argparse.ArgumentParser(description="Podklady reklam podle plánu (dry-run default)")
    p.add_argument("plan", type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    cid = normalize_cid(str(plan["customer_id"]))

    errs = validate(plan)
    print("PLÁN:")
    for blk in plan.get("campaign_assets", []):
        print(f"  kampaň {blk['campaign_id']}")
        for s in blk.get("sitelinks", []):
            print(f"    [+ SITELINK] {s['text']} | {s.get('desc1','')} / {s.get('desc2','')} → {s['url']}")
        if blk.get("callouts"):
            print(f"    [+ CALLOUTS] {', '.join(blk['callouts'])}")
        if blk.get("snippet"):
            print(f"    [+ SNIPPET ] {blk['snippet']['header']}: {', '.join(blk['snippet']['values'])}")
    for blk in plan.get("asset_group_assets", []):
        print(f"  asset group {blk['asset_group_id']}")
        for h in blk.get("add_headlines", []):
            print(f"    [+ NADPIS ] ({len(h):2d}) {h}")
        for d in blk.get("add_descriptions", []):
            print(f"    [+ POPIS  ] ({len(d):2d}) {d}")
        for a in blk.get("remove_asset_ids", []):
            print(f"    [− ODEBRAT] asset {a}")

    if errs:
        print("\n❌ Plán neprošel kontrolou délek — oprav ho, nic se neodeslalo:")
        for e in errs:
            print(f"   • {e}")
        raise SystemExit(1)
    print("\n✅ Délky v pořádku.")

    if not args.apply:
        print("🟡 DRY-RUN — nic nezaloženo. Pro provedení přidej --apply")
        return
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: plán nemá approval.status=approved.")

    client = build_client()
    from lib.policy import check_ad_texts
    texts = []
    for blk in plan.get("campaign_assets", []):
        for s in blk.get("sitelinks", []):
            texts += [s["text"], s.get("desc1", ""), s.get("desc2", "")]
        texts += list(blk.get("callouts", []))
        texts += list((blk.get("snippet") or {}).get("values", []))
    for blk in plan.get("asset_group_assets", []):
        texts += list(blk.get("add_headlines", [])) + list(blk.get("add_descriptions", []))
    check_ad_texts([t for t in texts if t], context="podklady reklam")

    ft = client.enums.AssetFieldTypeEnum
    asset_svc = client.get_service("AssetService")

    def make_assets(ops_specs):
        """ops_specs: list (field_type, AssetOperation) → list (field_type, resource_name)."""
        req = client.get_type("MutateAssetsRequest")
        req.customer_id = cid
        req.operations = [op for _, op in ops_specs]
        req.partial_failure = True
        resp = asset_svc.mutate_assets(request=req)
        if resp.partial_failure_error.code:
            print(f"  ⚠️ část podkladů selhala: {resp.partial_failure_error.message}")
        return [(f, r.resource_name) for (f, _), r in zip(ops_specs, resp.results) if r.resource_name]

    # --- kampaňová rozšíření ---
    for blk in plan.get("campaign_assets", []):
        camp_rn = f"customers/{cid}/campaigns/{blk['campaign_id']}"
        specs = []
        for s in blk.get("sitelinks", []):
            op = client.get_type("AssetOperation")
            sl = op.create.sitelink_asset
            sl.link_text = s["text"]
            if s.get("desc1"):
                sl.description1 = s["desc1"]
            if s.get("desc2"):
                sl.description2 = s["desc2"]
            op.create.final_urls.append(s["url"])
            specs.append((ft.SITELINK, op))
        for c in blk.get("callouts", []):
            op = client.get_type("AssetOperation")
            op.create.callout_asset.callout_text = c
            specs.append((ft.CALLOUT, op))
        if blk.get("snippet"):
            op = client.get_type("AssetOperation")
            ss = op.create.structured_snippet_asset
            ss.header = blk["snippet"]["header"]
            ss.values.extend(blk["snippet"]["values"])
            specs.append((ft.STRUCTURED_SNIPPET, op))
        if not specs:
            continue
        made = make_assets(specs)
        link_ops = []
        for field_type, rn in made:
            lop = client.get_type("CampaignAssetOperation")
            lop.create.campaign = camp_rn
            lop.create.asset = rn
            lop.create.field_type = field_type
            link_ops.append(lop)
        req = client.get_type("MutateCampaignAssetsRequest")
        req.customer_id = cid
        req.operations = link_ops
        req.partial_failure = True
        resp = client.get_service("CampaignAssetService").mutate_campaign_assets(request=req)
        ok = sum(1 for r in resp.results if r.resource_name)
        print(f"  ✓ kampaň {blk['campaign_id']}: napojeno {ok}/{len(link_ops)} rozšíření"
              + (f" | ⚠️ {resp.partial_failure_error.message}" if resp.partial_failure_error.code else ""))

    # --- texty asset group (PMax) ---
    for blk in plan.get("asset_group_assets", []):
        ag_rn = f"customers/{cid}/assetGroups/{blk['asset_group_id']}"
        specs = []
        for h in blk.get("add_headlines", []):
            op = client.get_type("AssetOperation")
            op.create.text_asset.text = h
            specs.append((ft.HEADLINE, op))
        for d in blk.get("add_descriptions", []):
            op = client.get_type("AssetOperation")
            op.create.text_asset.text = d
            specs.append((ft.DESCRIPTION, op))
        link_ops = []
        if specs:
            for field_type, rn in make_assets(specs):
                lop = client.get_type("AssetGroupAssetOperation")
                lop.create.asset_group = ag_rn
                lop.create.asset = rn
                lop.create.field_type = field_type
                link_ops.append(lop)
        for aid in blk.get("remove_asset_ids", []):
            lop = client.get_type("AssetGroupAssetOperation")
            lop.remove = f"{ag_rn}~customers/{cid}/assets/{aid}~HEADLINE"
            link_ops.append(lop)
        if not link_ops:
            continue
        req = client.get_type("MutateAssetGroupAssetsRequest")
        req.customer_id = cid
        req.operations = link_ops
        req.partial_failure = True
        resp = client.get_service("AssetGroupAssetService").mutate_asset_group_assets(request=req)
        ok = sum(1 for r in resp.results if r.resource_name)
        print(f"  ✓ asset group {blk['asset_group_id']}: {ok}/{len(link_ops)} operací"
              + (f" | ⚠️ {resp.partial_failure_error.message}" if resp.partial_failure_error.code else ""))

    # --- zpětné čtení ---
    print("\nZPĚTNÉ ČTENÍ:")
    svc = client.get_service("GoogleAdsService")
    for blk in plan.get("campaign_assets", []):
        # POZOR: pole, na které se filtruje, MUSÍ být i v SELECT — jinak GAQL vrátí
        # EXPECTED_REFERENCED_FIELD_IN_SELECT_CLAUSE (spadlo na tom 8. 9. 2026 až
        # po úspěšném zápisu, takže to vypadalo jako chyba mutace; nebyla).
        q = ("SELECT campaign.id, campaign_asset.field_type, asset.id FROM campaign_asset "
             f"WHERE campaign.id = {blk['campaign_id']} AND campaign_asset.status != 'REMOVED'")
        cnt: dict = {}
        for b in svc.search_stream(customer_id=cid, query=q):
            for r in b.results:
                k = r.campaign_asset.field_type.name
                cnt[k] = cnt.get(k, 0) + 1
        print(f"  kampaň {blk['campaign_id']}: {cnt}")
    for blk in plan.get("asset_group_assets", []):
        q = ("SELECT asset_group.id, asset_group_asset.field_type, asset.id FROM asset_group_asset "
             f"WHERE asset_group.id = {blk['asset_group_id']}")
        cnt = {}
        for b in svc.search_stream(customer_id=cid, query=q):
            for r in b.results:
                k = r.asset_group_asset.field_type.name
                cnt[k] = cnt.get(k, 0) + 1
        print(f"  asset group {blk['asset_group_id']}: {cnt}")


if __name__ == "__main__":
    main()

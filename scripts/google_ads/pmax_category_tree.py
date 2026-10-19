#!/usr/bin/env python3
"""Strom produktů PMax podle Google kategorií produktu (+ volitelné vyřazení vlastního štítku).

Režimy:
- "exclude": uvedené kategorie VYŘADIT, vše ostatní zahrnout (hlavní kampaň).
- "include": zahrnout JEN uvedené kategorie, vše ostatní vyřadit (např. „lowcost“ kampaň).

Strom se v API nedá upravovat po částech → starý se smaže a nový vytvoří v JEDNOM atomickém
mutate (viz update_pmax_listing_groups.py a dokumentace performance-max/listing-groups).

BEZPEČNOST: bez přepínače jen vypíše plán; --validate = kontrola Googlem (validate_only);
--apply = zápis (jen plán s approval.status = approved); po zápisu strom přečte zpět.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/pmax_category_tree.py clients/<plan>.json [--validate|--apply]

Plán:
{"customer_id": "…", "campaign_id": "…", "asset_group_id": "…", "mode": "exclude",
 "paths": [[1, 2], [1, 3, 4]],          # smyšlená ukázka; skutečná Google category ID L1 > L2 > L3 vezmi z taxonomie
 "exclude_custom_attribute": {"index": "INDEX1", "value": "sezona-vyprodej"},   # volitelné, smyšlený štítek
 "approval": {"status": "approved", …}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402
from update_pmax_listing_groups import read_tree, removal_order  # noqa: E402

LEVELS = ["LEVEL1", "LEVEL2", "LEVEL3", "LEVEL4", "LEVEL5"]


def tree_ops(client, cid: str, ag_id: str, mode: str, paths: list, excl_custom: dict | None,
             tmp_start: int = -100) -> list:
    """Operace vytvářející celý strom (rodič vždy před dítětem). ag_id může být dočasné (záporné)."""
    lgf = client.enums.ListingGroupFilterTypeEnum
    src = client.enums.ListingGroupFilterListingSourceEnum
    lvl = client.enums.ListingGroupFilterProductCategoryLevelEnum
    idx = client.enums.ListingGroupFilterCustomAttributeIndexEnum
    ag_rn = f"customers/{cid}/assetGroups/{ag_id}"
    leaf_t = lgf.UNIT_EXCLUDED if mode == "exclude" else lgf.UNIT_INCLUDED
    other_t = lgf.UNIT_INCLUDED if mode == "exclude" else lgf.UNIT_EXCLUDED
    ops, counter = [], [tmp_start]

    def node(type_, parent, setter=None):
        rn = f"customers/{cid}/assetGroupListingGroupFilters/{ag_id}~{counter[0]}"
        counter[0] -= 1
        op = client.get_type("MutateOperation")
        n = op.asset_group_listing_group_filter_operation.create
        n.resource_name = rn
        n.asset_group = ag_rn
        n.type_ = type_
        n.listing_source = src.SHOPPING
        if parent:
            n.parent_listing_group_filter = parent
        if setter:
            setter(n.case_value)
        ops.append(op)
        return rn

    root = node(lgf.SUBDIVISION, None)
    cat_parent = root
    if excl_custom:
        def set_custom(value):
            def s(cv):
                cv.product_custom_attribute.index = getattr(idx, excl_custom["index"])
                if value:
                    cv.product_custom_attribute.value = value
            return s
        node(lgf.UNIT_EXCLUDED, root, set_custom(excl_custom["value"]))
        cat_parent = node(lgf.SUBDIVISION, root, set_custom(None))

    trie: dict = {}
    for p in paths:
        cur = trie
        for cat in p:
            cur = cur.setdefault(int(cat), {})

    def set_cat(level, cat_id=None):
        def s(cv):
            cv.product_category.level = getattr(lvl, LEVELS[level])
            if cat_id is not None:
                cv.product_category.category_id = cat_id
        return s

    def build(parent, sub, level):
        for cat_id, children in sub.items():
            if children:
                build(node(lgf.SUBDIVISION, parent, set_cat(level, cat_id)), children, level + 1)
            else:
                node(leaf_t, parent, set_cat(level, cat_id))
        node(other_t, parent, set_cat(level))

    build(cat_parent, trie, 0)
    return ops


def print_tree(client, cid, ag_id):
    svc = client.get_service("GoogleAdsService")
    q = ("SELECT asset_group_listing_group_filter.id, asset_group_listing_group_filter.type, "
         "asset_group_listing_group_filter.parent_listing_group_filter, "
         "asset_group_listing_group_filter.case_value.product_category.category_id, "
         "asset_group_listing_group_filter.case_value.product_category.level, "
         "asset_group_listing_group_filter.case_value.product_custom_attribute.value, asset_group.id "
         f"FROM asset_group_listing_group_filter WHERE asset_group.id = {ag_id}")
    rows = [r.asset_group_listing_group_filter for b in svc.search_stream(customer_id=cid, query=q) for r in b.results]
    kids = {}
    for f in rows:
        kids.setdefault(f.parent_listing_group_filter or "", []).append(f)

    def walk(parent, depth):
        for f in kids.get(parent, []):
            cv = f.case_value
            if cv.product_category.level:
                label = f"kategorie {cv.product_category.level.name} {cv.product_category.category_id or '(ostatní)'}"
            elif cv.product_custom_attribute.value or depth:
                label = f"štítek {cv.product_custom_attribute.value or '(ostatní)'}"
            else:
                label = "kořen"
            print("  " * depth + f"- {f.type_.name} {label}")
            walk(f.resource_name, depth + 1)
    walk("", 0)
    print(f"Uzlů: {len(rows)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Strom PMax podle kategorií")
    p.add_argument("plan")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    if args.apply and (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Plán není schválený (approval.status).")
    cid = normalize_cid(plan["customer_id"], "write")
    client = build_client()
    existing = read_tree(client, cid, plan["asset_group_id"])
    if any(n["campaign_id"] != str(plan["campaign_id"]) for n in existing):
        raise SystemExit("Asset group nepatří uvedené kampani.")
    ops = []
    for rn in removal_order(existing):
        op = client.get_type("MutateOperation")
        op.asset_group_listing_group_filter_operation.remove = rn
        ops.append(op)
    new = tree_ops(client, cid, plan["asset_group_id"], plan["mode"], plan["paths"],
                   plan.get("exclude_custom_attribute"))
    ops += new
    print(f"Smazat {len(existing)} uzlů, vytvořit {len(new)} uzlů (režim {plan['mode']}, {len(plan['paths'])} kategorií).")
    if not (args.validate or args.apply):
        print("DRY-RUN: nic neodesláno (použij --validate nebo --apply).")
        return
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = cid
    req.mutate_operations.extend(ops)
    req.partial_failure = False
    req.validate_only = not args.apply
    client.get_service("GoogleAdsService").mutate(request=req)
    print("ZAPSÁNO" if args.apply else "VALIDACE OK (nic nezapsáno)")
    if args.apply:
        print_tree(client, cid, plan["asset_group_id"])


if __name__ == "__main__":
    main()

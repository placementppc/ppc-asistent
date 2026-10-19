#!/usr/bin/env python3
"""Přestavba stromu listing group filtrů u PMax asset group (vyloučení produktů).

PROČ SAMOSTATNÝ SKRIPT: `apply_changes.py` listing group filtry neumí a nejde je
doplnit jako další operaci — strom se v Google Ads API **nedá upravit**. Existující
uzly se musí smazat a nový strom vytvořit v JEDNOM atomickém `mutate`, jinak zůstane
asset group bez kořene a přestane doručovat. Ověřeno v dokumentaci:
https://developers.google.com/google-ads/api/docs/performance-max/listing-groups

BEZPEČNOST:
- Výchozí režim je DRY-RUN — jen vypíše, co by poslal. NIC nezapíše.
- `--validate` nechá request zkontrolovat Googlem (validate_only), taky nic nezapíše.
- Reálný zápis jen s `--apply` a jen u plánu s approval.status = approved.
- Zápis je atomický (partial_failure=False) — buď projde celý strom, nebo nic.
- Po zápisu si strom přečte zpátky z API a vypíše ho.

Použití:
  python scripts/google_ads/update_pmax_listing_groups.py clients/<plan>.json
  python scripts/google_ads/update_pmax_listing_groups.py clients/<plan>.json --validate
  python scripts/google_ads/update_pmax_listing_groups.py clients/<plan>.json --apply

Schéma plánu (JSON):
{
  "change_id": "klient-YYYY-MM-DD-popis",
  "client": "klient",
  "customer_id": "0000000000",
  "campaign_id": "0000000000",          # kontrola, že asset group patří té kampani
  "asset_group_id": "0000000000",
  "exclude_item_ids": ["produkt-a", "produkt-b"],
  "approval": {"status": "approved", "approved_by": "user", "approved_at": "YYYY-MM-DD"}
}

Výsledný strom:
  kořen (SUBDIVISION, bez case_value)
  ├── UNIT_EXCLUDED  product_item_id = <každé z exclude_item_ids>
  └── UNIT_INCLUDED  product_item_id = (prázdné) → „všechno ostatní"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

# Dočasná ID pro nové uzly. Musí být záporná a v rámci requestu unikátní.
ROOT_TEMP_ID = -1


def res_listing_group_filter(cid: str, asset_group_id: str, filter_id) -> str:
    return f"customers/{cid}/assetGroupListingGroupFilters/{asset_group_id}~{filter_id}"


def res_asset_group(cid: str, asset_group_id: str) -> str:
    return f"customers/{cid}/assetGroups/{asset_group_id}"


def read_tree(client, cid: str, asset_group_id: str):
    """Existující uzly stromu → seznam dictů (resource_name, parent, type, item_id)."""
    svc = client.get_service("GoogleAdsService")
    query = (
        "SELECT asset_group_listing_group_filter.resource_name, "
        "asset_group_listing_group_filter.id, "
        "asset_group_listing_group_filter.type, "
        "asset_group_listing_group_filter.parent_listing_group_filter, "
        "asset_group_listing_group_filter.case_value.product_item_id.value, "
        "asset_group.id, campaign.id "
        "FROM asset_group_listing_group_filter "
        f"WHERE asset_group.id = {asset_group_id}"
    )
    nodes = []
    for batch in svc.search_stream(customer_id=cid, query=query):
        for row in batch.results:
            f = row.asset_group_listing_group_filter
            nodes.append(
                {
                    "resource_name": f.resource_name,
                    "parent": f.parent_listing_group_filter or "",
                    "type": f.type_.name,
                    "item_id": f.case_value.product_item_id.value or "",
                    "campaign_id": str(row.campaign.id),
                }
            )
    return nodes


def removal_order(nodes):
    """Resource names v pořadí pro mazání: děti dřív než rodiče (post-order)."""
    children = {}
    for n in nodes:
        children.setdefault(n["parent"], []).append(n["resource_name"])
    roots = [n["resource_name"] for n in nodes if not n["parent"]]
    ordered = []

    def walk(rn):
        for child in children.get(rn, []):
            walk(child)
        ordered.append(rn)

    for r in roots:
        walk(r)
    # Pojistka: uzly, na které se přes kořen nedošlo (osiřelé), smaž taky.
    seen = set(ordered)
    for n in nodes:
        if n["resource_name"] not in seen:
            ordered.insert(0, n["resource_name"])
    return ordered


def build_operations(client, cid: str, asset_group_id: str, existing, exclude_item_ids):
    """Mutate operace: smazání starého stromu + vytvoření nového. Atomicky."""
    ops = []
    lgf_type = client.enums.ListingGroupFilterTypeEnum
    listing_source = client.enums.ListingGroupFilterListingSourceEnum
    asset_group_res = res_asset_group(cid, asset_group_id)

    for rn in removal_order(existing):
        op = client.get_type("MutateOperation")
        op.asset_group_listing_group_filter_operation.remove = rn
        ops.append(op)

    # Kořen — SUBDIVISION, bez case_value a bez rodiče.
    root_res = res_listing_group_filter(cid, asset_group_id, ROOT_TEMP_ID)
    op = client.get_type("MutateOperation")
    root = op.asset_group_listing_group_filter_operation.create
    root.resource_name = root_res
    root.asset_group = asset_group_res
    root.type_ = lgf_type.SUBDIVISION
    root.listing_source = listing_source.SHOPPING
    ops.append(op)

    temp_id = ROOT_TEMP_ID - 1

    # Vyloučené produkty.
    for item_id in exclude_item_ids:
        op = client.get_type("MutateOperation")
        node = op.asset_group_listing_group_filter_operation.create
        node.resource_name = res_listing_group_filter(cid, asset_group_id, temp_id)
        node.asset_group = asset_group_res
        node.parent_listing_group_filter = root_res
        node.type_ = lgf_type.UNIT_EXCLUDED
        node.listing_source = listing_source.SHOPPING
        node.case_value.product_item_id.value = item_id
        ops.append(op)
        temp_id -= 1

    # „Všechno ostatní" — sourozenci musí mít stejnou dimenzi, takže product_item_id
    # bez hodnoty. Typ je vnořená třída ListingGroupFilterDimension.ProductItemId,
    # kterou client.get_type() nezná (ProductItemIdInfo je jiná zpráva, pro
    # ad_group_criterion). Přítomnost prázdné zprávy se označí přes SetInParent();
    # bez toho by pole zůstalo nenastavené a uzel „ostatní" by nevznikl.
    op = client.get_type("MutateOperation")
    other = op.asset_group_listing_group_filter_operation.create
    other.resource_name = res_listing_group_filter(cid, asset_group_id, temp_id)
    other.asset_group = asset_group_res
    other.parent_listing_group_filter = root_res
    other.type_ = lgf_type.UNIT_INCLUDED
    other.listing_source = listing_source.SHOPPING
    other.case_value.product_item_id._pb.SetInParent()
    ops.append(op)

    return ops


def print_tree(nodes, header):
    print(f"\n{header}")
    if not nodes:
        print("  (prázdný strom)")
        return
    children = {}
    for n in nodes:
        children.setdefault(n["parent"], []).append(n)
    roots = [n for n in nodes if not n["parent"]]

    def walk(node, depth):
        label = node["type"]
        if node["item_id"]:
            label += f'  product_item_id = "{node["item_id"]}"'
        elif node["type"] == "SUBDIVISION":
            pass
        elif not node["parent"]:
            label += "  (kořen bez dělení → všechny produkty)"
        else:
            label += "  product_item_id = (prázdné) → všechno ostatní"
        print(f'  {"    " * depth}└─ {label}   [{node["resource_name"].split("/")[-1]}]')
        for c in children.get(node["resource_name"], []):
            walk(c, depth + 1)

    for r in roots:
        walk(r, 0)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("plan", help="cesta k JSON plánu")
    p.add_argument("--apply", action="store_true", help="reálný zápis (jinak dry-run)")
    p.add_argument("--validate", action="store_true",
                   help="nechat request zkontrolovat Googlem (validate_only), nezapisuje")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    cid = normalize_cid(str(plan["customer_id"]))
    asset_group_id = str(plan["asset_group_id"])
    campaign_id = str(plan["campaign_id"])
    exclude = list(plan["exclude_item_ids"])

    if not exclude:
        raise SystemExit("Plán nemá žádné exclude_item_ids — není co dělat.")

    approval = (plan.get("approval") or {}).get("status")
    if args.apply and approval != "approved":
        raise SystemExit(
            f"ODMÍTNUTO: plán nemá approval.status=approved (je '{approval}'). "
            "Bez schválení uživatele se nezapisuje."
        )

    client = build_client()

    print(f"=== {plan.get('change_id', args.plan)} ===")
    print(f"účet {cid} | kampaň {campaign_id} | asset group {asset_group_id}")
    print(f"vyloučit: {', '.join(exclude)}")

    existing = read_tree(client, cid, asset_group_id)
    if not existing:
        raise SystemExit(
            f"Asset group {asset_group_id} nemá žádný listing group filtr — "
            "buď je to špatné ID, nebo to není maloobchodní PMax. Nepokračuju."
        )

    wrong = {n["campaign_id"] for n in existing} - {campaign_id}
    if wrong:
        raise SystemExit(
            f"POJISTKA: asset group {asset_group_id} patří kampani {wrong}, "
            f"ne {campaign_id}. Zkontroluj plán."
        )

    print_tree(existing, "Současný strom:")

    ops = build_operations(client, cid, asset_group_id, existing, exclude)
    n_remove = sum(1 for o in ops
                   if o.asset_group_listing_group_filter_operation._pb.HasField("remove"))
    n_create = len(ops) - n_remove
    print(f"\nOperace: {n_remove}× remove + {n_create}× create, atomicky v jednom mutate.")

    planned = [{"parent": "", "type": "SUBDIVISION", "item_id": "",
                "resource_name": res_listing_group_filter(cid, asset_group_id, ROOT_TEMP_ID)}]
    tid = ROOT_TEMP_ID - 1
    root_res = planned[0]["resource_name"]
    for item_id in exclude:
        planned.append({"parent": root_res, "type": "UNIT_EXCLUDED", "item_id": item_id,
                        "resource_name": res_listing_group_filter(cid, asset_group_id, tid)})
        tid -= 1
    planned.append({"parent": root_res, "type": "UNIT_INCLUDED", "item_id": "",
                    "resource_name": res_listing_group_filter(cid, asset_group_id, tid)})
    print_tree(planned, "Cílový strom (dočasná ID, Google přidělí skutečná):")

    if not args.apply and not args.validate:
        print("\nDRY-RUN — nic se neodeslalo. Kontrola u Googlu: --validate, zápis: --apply")
        return

    svc = client.get_service("GoogleAdsService")
    request = client.get_type("MutateGoogleAdsRequest")
    request.customer_id = cid
    request.mutate_operations = ops
    request.partial_failure = False  # atomicky: buď celý strom, nebo nic
    request.validate_only = not args.apply

    try:
        response = svc.mutate(request=request)
    except Exception as e:  # GoogleAdsException má čitelný detail
        print("\nCHYBA — nic se nezapsalo (mutate je atomický).", file=sys.stderr)
        failure = getattr(e, "failure", None)
        if failure is not None:
            for err in failure.errors:
                loc = ".".join(str(el.field_name) for el in err.location.field_path_elements)
                print(f"  • {err.message}  [{loc}]", file=sys.stderr)
        else:
            print(f"  • {e}", file=sys.stderr)
        raise SystemExit(1)

    if args.validate:
        print("\n✅ VALIDACE PROŠLA — Google request přijal jako platný. Nic nezapsáno.")
        return

    created = [r.asset_group_listing_group_filter_result.resource_name
               for r in response.mutate_operation_responses
               if r.asset_group_listing_group_filter_result.resource_name]
    print(f"\n✅ ZAPSÁNO. Vrácených resource names: {len(created)}")

    print("\n--- ZPĚTNÉ ČTENÍ Z API ---")
    after = read_tree(client, cid, asset_group_id)
    print_tree(after, "Strom po zápisu:")

    excluded_now = {n["item_id"] for n in after if n["type"] == "UNIT_EXCLUDED"}
    missing = set(exclude) - excluded_now
    if missing:
        print(f"\n⚠️  NEDOKONČENO — chybí vyloučení: {', '.join(sorted(missing))}",
              file=sys.stderr)
        raise SystemExit(1)
    has_other = any(n["type"] == "UNIT_INCLUDED" and not n["item_id"] for n in after)
    if not has_other:
        print("\n⚠️  NEDOKONČENO — chybí uzel „všechno ostatní“, kampaň by nedoručovala!",
              file=sys.stderr)
        raise SystemExit(1)
    print("\n✅ Ověřeno zpětným čtením: vyloučení sedí a uzel „všechno ostatní“ existuje.")


if __name__ == "__main__":
    main()

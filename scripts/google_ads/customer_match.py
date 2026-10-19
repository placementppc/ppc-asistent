#!/usr/bin/env python3
"""Customer Match — vytvoření CRM user listu + nahrání hashovaných e-mailů.

⚠️ ZÁPIS S OSOBNÍMI DATY. Do Googlu jdou POUZE SHA-256 hashe (syrové e-maily
nikdy neopouštějí lokál). I tak: spouštěj až po schválení a jen s daty, k nimž
má inzerent souhlas pro Customer Match. Dry-run default, reálně až --apply.

Použití:
  # náhled (nic nenahraje):
  python scripts/google_ads/customer_match.py <customer_id> --csv <path> --name "Kupci all-time"
  # reálné vytvoření listu + upload:
  python scripts/google_ads/customer_match.py <customer_id> --csv <path> --name "Kupci all-time" --apply
  # do existujícího listu (přeskočí create):
  python scripts/google_ads/customer_match.py <customer_id> --csv <path> --list-id 123 --apply

CSV: musí mít sloupec 'Email' (syrové e-maily). Normalizace = trim+lower, pak SHA-256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_hashed_emails(csv_path: str) -> tuple[list[str], int]:
    seen, bad = set(), 0
    with open(csv_path, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        if "Email" not in (r.fieldnames or []):
            raise SystemExit(f"CSV nemá sloupec 'Email' (má: {r.fieldnames})")
        for row in r:
            e = (row.get("Email") or "").strip().lower()
            if not e or not EMAIL_RE.match(e):
                bad += 1
                continue
            seen.add(hashlib.sha256(e.encode("utf-8")).hexdigest())
    return sorted(seen), bad


def create_user_list(client, cid, name, life_span) -> str:
    svc = client.get_service("UserListService")
    op = client.get_type("UserListOperation")
    ul = op.create
    ul.name = name
    ul.membership_life_span = life_span
    ul.crm_based_user_list.upload_key_type = (
        client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
    )
    ul.crm_based_user_list.data_source_type = (
        client.enums.UserListCrmDataSourceTypeEnum.FIRST_PARTY
    )
    resp = svc.mutate_user_lists(customer_id=cid, operations=[op])
    return resp.results[0].resource_name


def upload(client, cid, list_resource, hashes) -> None:
    svc = client.get_service("OfflineUserDataJobService")
    job = client.get_type("OfflineUserDataJob")
    job.type_ = client.enums.OfflineUserDataJobTypeEnum.CUSTOMER_MATCH_USER_LIST
    job.customer_match_user_list_metadata.user_list = list_resource
    job_resource = svc.create_offline_user_data_job(
        customer_id=cid, job=job
    ).resource_name

    ops = []
    for h in hashes:
        op = client.get_type("OfflineUserDataJobOperation")
        ui = client.get_type("UserIdentifier")
        ui.hashed_email = h
        op.create.user_identifiers.append(ui)
        ops.append(op)

    # dávkuj po 10 000 (limit add operací na request)
    for i in range(0, len(ops), 10000):
        chunk = ops[i : i + 10000]
        resp = svc.add_offline_user_data_job_operations(
            resource_name=job_resource,
            operations=chunk,
            enable_partial_failure=True,
        )
        if resp.partial_failure_error and resp.partial_failure_error.code:
            print(f"  ⚠️ partial failure: {resp.partial_failure_error.message}")
        print(f"  ✓ přidáno {len(chunk)} operací")

    svc.run_offline_user_data_job(resource_name=job_resource)
    print(f"  ✓ job spuštěn: {job_resource}")
    print("  ⏳ matchování běží na straně Googlu (hodiny). Velikost uvidíš v UI za ~24–48 h.")


def main() -> None:
    p = argparse.ArgumentParser(description="Customer Match upload (dry-run default)")
    p.add_argument("customer_id")
    p.add_argument("--csv", required=True, help="CSV se sloupcem 'Email'")
    p.add_argument("--name", help="název nového user listu")
    p.add_argument("--list-id", help="ID existujícího user listu (přeskočí create)")
    p.add_argument("--life-span", type=int, default=540, help="membership_life_span dní (max 540)")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ nahraje (jinak dry-run)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    hashes, bad = load_hashed_emails(args.csv)
    print(f"CUSTOMER MATCH — účet {args.customer_id}")
    print(f"  zdroj: {args.csv}")
    print(f"  unikátních validních e-mailů (SHA-256): {len(hashes)}  (přeskočeno neplatných: {bad})")
    if args.list_id:
        print(f"  cíl: existující list {args.list_id}")
    else:
        print(f"  cíl: NOVÝ list '{args.name}' (life span {args.life_span} d)")

    if not args.apply:
        print("\n🟡 DRY-RUN — nic nenahráno. Reálně přidej --apply.")
        return
    if not args.list_id and not args.name:
        raise SystemExit("Pro create listu zadej --name (nebo --list-id pro existující).")

    client = build_client()
    print("\n🔴 --apply: nahrávám...")
    if args.list_id:
        list_resource = f"customers/{cid}/userLists/{args.list_id}"
    else:
        list_resource = create_user_list(client, cid, args.name, args.life_span)
        print(f"  ✓ list vytvořen: {list_resource}")
    upload(client, cid, list_resource, hashes)
    print("\n✅ Hotovo. Signál na PMax asset groupy = druhý krok (potřebuje ID listu).")


if __name__ == "__main__":
    main()

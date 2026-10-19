#!/usr/bin/env python3
"""Bezpečný dry-run/apply pro schválené Sklik odkazy a popisky (url: null) a jejich přiřazení.

Plán musí uvést `allowed_domains` (např. ["www.example.cz", "example.cz"]) — URL nových
odkazů mimo tyto domény skript odmítne (pojistka proti překlepu nebo cizímu webu).

POZOR: sitelinks.campaign.set / group.set NAHRAZUJE celé přiřazení — v plánu vždy uveď
kompletní seznam (stávající ponechané + nové).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
from client import SklikClient  # noqa: E402
from lib.redact import strip_secrets  # noqa: E402


FORBIDDEN_KEYS = {"budget", "dayBudget", "totalBudget", "cpc", "maxCpc", "phone"}


class Api:
    def __init__(self, user_id: int) -> None:
        self.client = SklikClient().login()
        self.user_id = int(user_id)

    def call(self, method: str, *params: object, managed: bool = True) -> dict:
        for attempt in range(5):
            context = {"session": self.client.session}
            if managed:
                context["userId"] = self.user_id
            request = urllib.request.Request(
                f"{self.client.base}/{method}",
                data=json.dumps([context, *params]).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 4:
                    time.sleep(2**attempt)
                    continue
                raise
            if payload.get("session"):
                self.client.session = payload["session"]
            if payload.get("status") == 429 and attempt < 4:
                time.sleep(2**attempt)
                continue
            return payload
        raise RuntimeError(f"{method}: vyčerpány pokusy po rate limitu")


def ensure_ok(method: str, response: dict) -> None:
    diagnostics = response.get("diagnostics") or []
    diagnostic_items = diagnostics.values() if isinstance(diagnostics, dict) else diagnostics
    errors = [
        item
        for item in diagnostic_items
        if isinstance(item, dict) and item.get("type") == "error"
    ]
    if response.get("status") not in (200, 206) or errors:
        raise SystemExit(
            f"{method} selhalo: {response.get('status')} {response.get('statusMessage')} "
            f"diagnostics={diagnostics}"
        )


def fail_on_forbidden_keys(value: object, path: str = "plan") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_KEYS:
                raise SystemExit(f"Odmítám plán: zakázané pole {path}.{key}.")
            fail_on_forbidden_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            fail_on_forbidden_keys(nested, f"{path}[{index}]")


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: approval.status není approved.")
    guardrails = plan.get("guardrails") or {}
    for key in ("allow_budget_changes", "allow_cpc_changes", "allow_phone_changes"):
        if guardrails.get(key) is not False:
            raise SystemExit(f"Odmítám plán: guardrail {key} musí být false.")
    if guardrails.get("remove_old_entities") is not False:
        raise SystemExit("Odmítám plán: staré entity se v této dávce nesmí mazat.")
    fail_on_forbidden_keys({key: value for key, value in plan.items() if key != "guardrails"})

    allowed = {d.strip().lower() for d in plan.get("allowed_domains") or [] if d.strip()}
    sitelinks = plan.get("new_sitelinks") or []
    if any(row.get("url") for row in sitelinks) and not allowed:
        raise SystemExit("Odmítám plán: chybí allowed_domains (domény webu klienta).")
    keys = [row["key"] for row in sitelinks]
    if len(keys) != len(set(keys)):
        raise SystemExit("Plán obsahuje duplicitní key nového odkazu.")
    for row in sitelinks:
        if not 1 <= len(row["name"]) <= 25:
            raise SystemExit(f"Neplatná délka odkazu: {row['name']!r}.")
        if row.get("url") is None:
            # popisek = sitelink bez URL (DRAK sitelinks.create: url je optional)
            continue
        parsed = urlparse(row["url"])
        if parsed.scheme != "https" or parsed.netloc not in allowed:
            raise SystemExit(f"Odmítám ne-HTTPS nebo cizí URL: {row['url']}")
    known_keys = set(keys)
    for assignment in (plan.get("campaign_assignments") or []) + (plan.get("group_assignments") or []):
        for reference in assignment.get("sitelinks") or []:
            if "key" in reference and reference["key"] not in known_keys:
                raise SystemExit(f"Neznámý sitelink key: {reference['key']}")
            if ("key" in reference) == ("id" in reference):
                raise SystemExit("Každý sitelink reference musí mít právě key nebo id.")
    return plan


def batch_limit(limits: dict, name: str) -> int:
    for item in limits.get("batchCallLimits") or []:
        if item.get("name") == name:
            return int(item["limit"])
    raise SystemExit(f"API nevrátilo dávkový limit {name}.")


def resolve_ids(assignment: dict, key_to_id: dict[str, int]) -> list[int]:
    ids = [
        int(reference["id"]) if "id" in reference else int(key_to_id[reference["key"]])
        for reference in assignment["sitelinks"]
    ]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"Duplicitní odkaz v přiřazení {assignment['id']}.")
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Sklik sitelink changes (dry-run default)")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    api = Api(int(plan["user_id"]))
    limits = api.call("api.limits", managed=False)
    ensure_ok("api.limits", limits)

    all_sitelinks_response = api.call("sitelinks.list")
    ensure_ok("sitelinks.list", all_sitelinks_response)
    all_sitelinks = all_sitelinks_response.get("sitelinks") or []
    active_by_pair = {
        (row["name"].casefold(), row.get("url")): int(row["id"])
        for row in all_sitelinks
        if not row.get("deleted")
    }
    active_ids = {int(row["id"]) for row in all_sitelinks if not row.get("deleted")}

    key_to_id: dict[str, int] = {}
    missing = []
    missing_keys = []
    for row in plan["new_sitelinks"]:
        existing_id = active_by_pair.get((row["name"].casefold(), row.get("url")))
        if existing_id:
            key_to_id[row["key"]] = existing_id
        else:
            missing.append({"name": row["name"], **({"url": row["url"]} if row.get("url") else {})})
            missing_keys.append(row["key"])

    referenced_existing_ids = {
        int(reference["id"])
        for assignment in (plan.get("campaign_assignments") or []) + (plan.get("group_assignments") or [])
        for reference in assignment.get("sitelinks") or []
        if "id" in reference
    }
    unknown_ids = sorted(referenced_existing_ids - active_ids)
    if unknown_ids:
        raise SystemExit(f"Plán odkazuje na neaktivní/neexistující sitelink IDs: {unknown_ids}")

    if len(missing) > min(batch_limit(limits, "global.check"), batch_limit(limits, "global.create")):
        raise SystemExit("Dávka nových odkazů překračuje API limit.")
    validation = {"status": 200, "statusMessage": "No new sitelinks to create", "diagnostics": []}
    if missing:
        checked = api.call("sitelinks.check", missing)
        ensure_ok("sitelinks.check", checked)
        validation = {
            "status": checked.get("status"),
            "statusMessage": checked.get("statusMessage"),
            "diagnostics": checked.get("diagnostics") or [],
        }

    result = {
        "mode": "apply" if args.apply else "dry-run",
        "change_id": plan.get("change_id"),
        "guardrails": plan["guardrails"],
        "counts": {
            "new_sitelinks_requested": len(plan["new_sitelinks"]),
            "new_sitelinks_missing": len(missing),
            "campaign_assignments": len(plan.get("campaign_assignments") or []),
            "group_assignments": len(plan.get("group_assignments") or []),
        },
        "validation": validation,
        "reused": key_to_id.copy(),
    }

    if not args.apply:
        result["preview"] = {
            "campaigns": plan.get("campaign_assignments") or [],
            "groups": plan.get("group_assignments") or [],
        }
        result["note"] = "DRY-RUN: sitelinks.create/campaign.set/group.set nebyly zavolány."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if missing:
        created = api.call("sitelinks.create", missing)
        ensure_ok("sitelinks.create", created)
        created_ids = [int(value) for value in created.get("ids") or []]
        if len(created_ids) != len(missing_keys):
            raise SystemExit(
                f"sitelinks.create vrátil neočekávaný počet ID: "
                f"{strip_secrets(created)}")
        key_to_id.update(dict(zip(missing_keys, created_ids)))
        result["created"] = dict(zip(missing_keys, created_ids))

    campaign_payload = [
        {"id": int(row["id"]), "sitelinkIds": resolve_ids(row, key_to_id)}
        for row in plan.get("campaign_assignments") or []
    ]
    group_payload = [
        {"id": int(row["id"]), "sitelinkIds": resolve_ids(row, key_to_id)}
        for row in plan.get("group_assignments") or []
    ]
    writes = {}
    if campaign_payload:
        response = api.call("sitelinks.campaign.set", campaign_payload)
        ensure_ok("sitelinks.campaign.set", response)
        writes["sitelinks.campaign.set"] = {
            "status": response.get("status"),
            "statusMessage": response.get("statusMessage"),
            "diagnostics": response.get("diagnostics") or [],
        }
    if group_payload:
        response = api.call("sitelinks.group.set", group_payload)
        ensure_ok("sitelinks.group.set", response)
        writes["sitelinks.group.set"] = {
            "status": response.get("status"),
            "statusMessage": response.get("statusMessage"),
            "diagnostics": response.get("diagnostics") or [],
        }
    result["writes"] = writes
    result["resolved_ids"] = key_to_id
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

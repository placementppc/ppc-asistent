#!/usr/bin/env python3
"""Bezpečná dávková úprava CPC produktových skupin Skliku.

Výchozí režim je DRY-RUN: načte plán, ověří limity a zavolá pouze
``productSets.check``. Reálný zápis proběhne jen s ``--apply`` a pouze u plánu,
který obsahuje explicitní schválení.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
from client import SklikClient  # noqa: E402
from lib.redact import strip_secrets  # noqa: E402


class Api:
    def __init__(self, user_id: int) -> None:
        self.client = SklikClient().login()
        self.user_id = int(user_id)

    def call(self, method: str, *params, managed: bool = True) -> dict:
        for attempt in range(5):
            ctx = {"session": self.client.session}
            if managed:
                ctx["userId"] = self.user_id
            req = urllib.request.Request(
                f"{self.client.base}/{method}",
                data=json.dumps([ctx, *params]).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise
            if payload.get("session"):
                self.client.session = payload["session"]
            if payload.get("status") == 429 and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            return payload
        raise RuntimeError(f"{method}: vyčerpány pokusy po rate limitu")


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    changes = plan.get("changes") or []
    if not changes:
        raise SystemExit("Plán neobsahuje žádné změny.")
    ids = [int(change["id"]) for change in changes]
    if len(ids) != len(set(ids)):
        raise SystemExit("Plán obsahuje duplicitní productSet ID.")
    return plan


def batch_limit(limits: dict, name: str) -> int:
    for item in limits.get("batchCallLimits") or []:
        if item.get("name") == name:
            return int(item["limit"])
    raise SystemExit(f"API nevrátilo dávkový limit {name}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sklik productSet CPC update (dry-run default)")
    parser.add_argument("plan", type=Path, help="JSON plán schválených změn")
    parser.add_argument("--apply", action="store_true", help="Provede zápis; bez volby pouze dry-run")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    if args.apply and (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: plán nemá approval.status=approved.")

    changes = plan["changes"]
    payload = [
        {"id": int(change["id"]), "cpc": int(change["to_cpc_halers"])}
        for change in changes
    ]
    api = Api(int(plan["user_id"]))
    limits = api.call("api.limits", managed=False)
    if limits.get("status") != 200:
        raise SystemExit(f"api.limits selhalo: {strip_secrets(limits)}")

    cpc_min = int(limits["limits"]["CpcMin"])
    cpc_max = int(limits["limits"]["CpcMax"])
    invalid = [row for row in payload if not cpc_min <= row["cpc"] <= cpc_max]
    if invalid:
        raise SystemExit(f"CPC mimo povolený rozsah {cpc_min}–{cpc_max} hal.: {invalid}")
    if len(payload) > min(batch_limit(limits, "global.check"), batch_limit(limits, "global.update")):
        raise SystemExit("Plán překračuje povolenou velikost dávky.")

    checked = api.call("productSets.check", payload)
    if checked.get("status") != 200:
        raise SystemExit(
            f"productSets.check selhal: {checked.get('status')} {checked.get('statusMessage')} "
            f"{checked.get('diagnostics')}"
        )

    result = {
        "mode": "apply" if args.apply else "dry-run",
        "change_id": plan.get("change_id"),
        "user_id": plan["user_id"],
        "campaign_id": plan.get("campaign_id"),
        "group_id": plan.get("group_id"),
        "count": len(payload),
        "cpc_range_halers": {"min": cpc_min, "max": cpc_max},
        "validation": {"status": checked.get("status"), "statusMessage": checked.get("statusMessage")},
        "changes": changes,
    }

    if args.apply:
        updated = api.call("productSets.update", payload)
        if updated.get("status") != 200:
            raise SystemExit(
                f"productSets.update selhal: {updated.get('status')} {updated.get('statusMessage')} "
                f"{updated.get('diagnostics')}"
            )
        result["update"] = {
            "status": updated.get("status"),
            "statusMessage": updated.get("statusMessage"),
        }
    else:
        result["note"] = "DRY-RUN: productSets.update nebylo zavoláno."

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

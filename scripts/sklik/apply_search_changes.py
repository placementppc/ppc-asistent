#!/usr/bin/env python3
"""Bezpečně ověří a aplikuje schválená Sklik KW, negativa a ETA reklamy.

Výchozí režim je pouze dry-run přes API ``*.check``. Reálné create operace se
provedou jen s ``--apply``, schváleným plánem a explicitními guardrails, které
zakazují změny rozpočtů a CPC.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.policy import check_ad_texts  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import SklikClient  # noqa: E402


ALLOWED_MATCH_TYPES = {"broad", "phrase", "exact"}
ALLOWED_NEGATIVE_MATCH_TYPES = {"negativeBroad", "negativePhrase", "negativeExact"}
FORBIDDEN_KEYS = {"budget", "dayBudget", "totalBudget", "cpc", "maxCpc"}


class Api:
    def __init__(self, user_id: int) -> None:
        self.client = SklikClient().login()
        self.user_id = int(user_id)

    def call(self, method: str, *params: object, managed: bool = True) -> dict:
        for attempt in range(5):
            ctx = {"session": self.client.session}
            if managed:
                ctx["userId"] = self.user_id
            request = urllib.request.Request(
                f"{self.client.base}/{method}",
                data=json.dumps([ctx, *params]).encode("utf-8"),
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


def fail_on_forbidden_keys(value: object, path: str = "plan") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_KEYS:
                raise SystemExit(f"Odmítám plán: zakázané pole {path}.{key}.")
            fail_on_forbidden_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            fail_on_forbidden_keys(nested, f"{path}[{index}]")


def ensure_unique(rows: list[dict], label: str) -> None:
    keys = [(int(row["groupId"]), row["name"].casefold(), row["matchType"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit(f"Plán obsahuje duplicitní položku v sekci {label}.")


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    approval = plan.get("approval") or {}
    guardrails = plan.get("guardrails") or {}
    if approval.get("status") != "approved":
        raise SystemExit("Odmítám plán: approval.status není approved.")
    if guardrails.get("allow_budget_changes") is not False:
        raise SystemExit("Odmítám plán: musí výslovně zakázat změny rozpočtů.")
    if guardrails.get("allow_cpc_changes") is not False:
        raise SystemExit("Odmítám plán: musí výslovně zakázat změny CPC.")
    fail_on_forbidden_keys({key: value for key, value in plan.items() if key != "guardrails"})

    keywords = plan.get("keywords") or []
    negatives = plan.get("negative_keywords") or []
    ads = plan.get("ads") or []
    if not keywords and not negatives and not ads:
        raise SystemExit("Plán neobsahuje žádné změny.")
    ensure_unique(keywords, "keywords")
    ensure_unique(negatives, "negative_keywords")
    if any(row.get("matchType") not in ALLOWED_MATCH_TYPES for row in keywords):
        raise SystemExit("Plán obsahuje nepovolený typ shody klíčového slova.")
    if any(row.get("matchType") not in ALLOWED_NEGATIVE_MATCH_TYPES for row in negatives):
        raise SystemExit("Plán obsahuje nepovolený typ shody negativního slova.")

    headlines = [ad.get(key, "") for ad in ads for key in ("headline1", "headline2", "headline3")]
    descriptions = [ad.get(key, "") for ad in ads for key in ("description", "description2")]
    check_ad_texts(headlines, context="nadpisy Sklik")
    check_ad_texts(descriptions, context="popisy Sklik")
    return plan


def batch_limit(limits: dict, name: str) -> int:
    for item in limits.get("batchCallLimits") or []:
        if item.get("name") == name:
            return int(item["limit"])
    raise SystemExit(f"API nevrátilo dávkový limit {name}.")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sklik search changes (dry-run default)")
    parser.add_argument("plan", type=Path, help="JSON plán schválených změn")
    parser.add_argument("--apply", action="store_true", help="Provede create operace")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    keywords = plan.get("keywords") or []
    negatives = plan.get("negative_keywords") or []
    ads = plan.get("ads") or []

    api = Api(int(plan["user_id"]))
    limits = api.call("api.limits", managed=False)
    ensure_ok("api.limits", limits)
    check_limit = batch_limit(limits, "global.check")
    create_limit = batch_limit(limits, "global.create")
    for label, rows in (("keywords", keywords), ("negative_keywords", negatives), ("ads", ads)):
        if len(rows) > min(check_limit, create_limit):
            raise SystemExit(f"Sekce {label} překračuje dávkový limit API.")

    validations = {}
    ad_checks = [{key: value for key, value in ad.items() if key != "status"} for ad in ads]
    for method, rows in (
        ("keywords.check", keywords),
        ("keywords.negative.check", negatives),
        ("ads.check", ad_checks),
    ):
        if not rows:
            continue
        response = api.call(method, rows)
        ensure_ok(method, response)
        validations[method] = {
            "status": response.get("status"),
            "statusMessage": response.get("statusMessage"),
            "diagnostics": response.get("diagnostics") or [],
        }

    result = {
        "mode": "apply" if args.apply else "dry-run",
        "change_id": plan.get("change_id"),
        "user_id": plan["user_id"],
        "guardrails": plan["guardrails"],
        "counts": {"keywords": len(keywords), "negative_keywords": len(negatives), "ads": len(ads)},
        "validation": validations,
    }

    if args.apply:
        writes = {}
        for method, rows, id_key in (
            ("keywords.create", keywords, "positiveKeywordIds"),
            ("keywords.negative.create", negatives, "negativeKeywordIds"),
            ("ads.create", ads, "adIds"),
        ):
            if not rows:
                continue
            response = api.call(method, rows)
            ensure_ok(method, response)
            writes[method] = {
                "status": response.get("status"),
                "statusMessage": response.get("statusMessage"),
                "ids": response.get(id_key) or [],
                "diagnostics": response.get("diagnostics") or [],
            }
        result["writes"] = writes
    else:
        result["note"] = "DRY-RUN: nebyla zavolána žádná create metoda."

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

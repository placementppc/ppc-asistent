#!/usr/bin/env python3
"""Založí novou Sklik vyhledávací (fulltext) kampaň ze schváleného plánu.

Výchozí režim je DRY-RUN: lokální validace + `campaigns.check`. Reálný zápis až
s ``--apply`` a jen se schváleným plánem. Vše se zakládá jako ``suspend`` —
aktivace patří do UI po lidské kontrole.

Použití:
  python scripts/sklik/create_search_campaign.py clients/<plan>.json
  python scripts/sklik/create_search_campaign.py clients/<plan>.json --apply

Skript je idempotentní: kampaň i sestavy se dohledávají podle názvu, takže
přerušený běh jde bezpečně zopakovat.
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


ETA_LIMITS = {
    "headline1": 30, "headline2": 30, "headline3": 30,
    "description": 90, "description2": 90, "path1": 15, "path2": 15,
}
MATCH_TYPES = {"broad", "phrase", "exact"}
NEGATIVE_MATCH_TYPES = {"negativeBroad", "negativePhrase", "negativeExact"}


class Api:
    """JSON-RPC klient se sériovými requesty a backoffem na 429."""

    def __init__(self, user_id: int) -> None:
        self.client = SklikClient().login()
        self.user_id = int(user_id)

    def call(self, method: str, *params: object, managed: bool = True) -> dict:
        for attempt in range(5):
            ctx: dict = {"session": self.client.session}
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
                    time.sleep(5 * 2**attempt)
                    continue
                raise
            if payload.get("session"):
                self.client.session = payload["session"]
            if payload.get("status") == 429 and attempt < 4:
                time.sleep(5 * 2**attempt)
                continue
            return payload
        raise RuntimeError(f"{method}: vyčerpány pokusy po rate limitu")


def ensure_ok(method: str, response: dict) -> dict:
    """Status 200/206 projde (206 = vytvořeno s warningy), [error] diagnostika ne."""
    diagnostics = response.get("diagnostics") or []
    items = diagnostics.values() if isinstance(diagnostics, dict) else diagnostics
    errors = [i for i in items if isinstance(i, dict) and i.get("type") == "error"]
    if response.get("status") not in (200, 206) or errors:
        raise SystemExit(
            f"❌ {method}: {response.get('status')} {response.get('statusMessage')}\n"
            f"   diagnostics={json.dumps(diagnostics, ensure_ascii=False)[:2000]}"
        )
    return response


def batch_limit(limits: dict, name: str) -> int:
    for item in limits.get("batchCallLimits") or []:
        if item.get("name") == name:
            return int(item["limit"])
    raise SystemExit(f"API nevrátilo dávkový limit {name}.")


def chunked(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


# --------------------------------------------------------------- validace plánu
def load_plan(path: Path, apply_mode: bool) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    guardrails = plan.get("guardrails") or {}
    approval = plan.get("approval") or {}

    if apply_mode and approval.get("status") != "approved":
        raise SystemExit("Odmítám zápis: approval.status není approved.")
    if guardrails.get("force_suspend") is not True:
        raise SystemExit("Odmítám plán: guardrails.force_suspend musí být true.")
    if guardrails.get("allow_changes_to_existing_campaigns") is not False:
        raise SystemExit("Odmítám plán: zásahy do existujících kampaní musí být zakázané.")

    campaign = plan["campaign"]
    if campaign.get("type") != "fulltext":
        raise SystemExit("Tenhle skript zakládá jen kampaně typu fulltext.")
    max_budget = int(guardrails["max_day_budget_haleru"])
    if int(campaign["dayBudget"]) > max_budget:
        raise SystemExit(f"Rozpočet {campaign['dayBudget']} h překračuje strop {max_budget} h.")

    max_cpc = int(guardrails["max_cpc_haleru"])
    problems: list[str] = []
    seen_kw: dict[tuple, str] = {}
    for group in plan["groups"]:
        if int(group["cpc"]) > max_cpc:
            problems.append(f"{group['name']}: CPC {group['cpc']} h > strop {max_cpc} h")
        for kw in group["keywords"]:
            if kw["matchType"] not in MATCH_TYPES:
                problems.append(f"{group['name']}: nepovolený typ shody {kw['matchType']}")
            if "cpc" in kw:
                problems.append(f"{group['name']} / {kw['name']}: CPC patří na sestavu, ne na KW")
            key = (kw["name"].casefold(), kw["matchType"])
            if key in seen_kw:
                problems.append(f"duplicitní KW „{kw['name']}\" ({kw['matchType']}) — "
                                f"{seen_kw[key]} × {group['name']}")
            seen_kw[key] = group["name"]
        for index, ad in enumerate(group["ads"], 1):
            for field, limit in ETA_LIMITS.items():
                text = ad.get(field) or ""
                if len(text) > limit:
                    problems.append(f"{group['name']} / reklama {index} / {field}: "
                                    f"{len(text)} znaků > {limit}")
            if ad.get("path2") and not ad.get("path1"):
                problems.append(f"{group['name']} / reklama {index}: path2 bez path1")
            if not ad.get("finalUrl", "").startswith("https://"):
                problems.append(f"{group['name']} / reklama {index}: finalUrl není https")

    for negative in plan.get("campaign_negatives") or []:
        if negative["matchType"] not in NEGATIVE_MATCH_TYPES:
            problems.append(f"negativum {negative['name']}: nepovolený typ shody")

    if problems:
        raise SystemExit("❌ Validace plánu:\n  - " + "\n  - ".join(problems))

    headlines = [ad.get(f, "") for g in plan["groups"] for ad in g["ads"]
                 for f in ("headline1", "headline2", "headline3")]
    descriptions = [ad.get(f, "") for g in plan["groups"] for ad in g["ads"]
                    for f in ("description", "description2")]
    check_ad_texts(headlines, context="nadpisy Sklik")
    check_ad_texts(descriptions, context="popisy Sklik")
    return plan


# ------------------------------------------------------------------------ zápis
def campaign_struct(plan: dict) -> dict:
    campaign = plan["campaign"]
    return {
        "name": campaign["name"],
        "type": "fulltext",
        "status": "suspend",  # guardrail: nikdy se nezakládá aktivní
        "dayBudget": int(campaign["dayBudget"]),
        "adSelection": campaign.get("adSelection", "weighted"),
        "devicesPriceRatio": campaign.get("devicesPriceRatio")
        or {"desktop": 0, "mobile": 0, "tablet": 0, "other": 0},
        "negativeKeywords": plan.get("campaign_negatives") or [],
    }


def find_campaign(api: Api, name: str) -> int | None:
    response = ensure_ok("campaigns.list", api.call(
        "campaigns.list", {"isDeleted": False},
        {"offset": 0, "limit": 1000, "displayColumns": ["id", "name"]}))
    for campaign in response.get("campaigns", []):
        if campaign["name"] == name:
            return campaign["id"]
    return None


def existing_groups(api: Api, campaign_id: int) -> dict[str, int]:
    response = ensure_ok("groups.list", api.call(
        "groups.list", {"campaign": {"ids": [campaign_id]}, "isDeleted": False},
        {"offset": 0, "limit": 500, "displayColumns": ["id", "name"]}))
    return {g["name"]: g["id"] for g in response.get("groups", [])}


def apply_plan(api: Api, plan: dict, limits: dict) -> dict:
    create_limit = batch_limit(limits, "global.create")
    result: dict = {"campaign_id": None, "groups": {}, "counts": {}}

    name = plan["campaign"]["name"]
    campaign_id = find_campaign(api, name)
    if campaign_id:
        print(f"[kampaň] „{name}\" už existuje → id {campaign_id}")
    else:
        response = ensure_ok("campaigns.create",
                             api.call("campaigns.create", [campaign_struct(plan)]))
        campaign_id = response["campaignIds"][0]
        print(f"[kampaň] založena → id {campaign_id}")
    result["campaign_id"] = campaign_id

    # campaigns.create spolehlivě nezapisuje budget/status → verifikace a případná oprava
    check = ensure_ok("campaigns.list", api.call(
        "campaigns.list", {"ids": [campaign_id]},
        {"offset": 0, "limit": 1, "displayColumns": ["id", "name", "status", "budget.dayBudget"]}))
    actual = check["campaigns"][0]
    want_budget = int(plan["campaign"]["dayBudget"])
    if actual["status"] != "suspend" or actual["budget"]["dayBudget"] != want_budget:
        print(f"[kampaň] oprava: status={actual['status']} "
              f"budget={actual['budget']['dayBudget']} → suspend / {want_budget}")
        ensure_ok("campaigns.update", api.call("campaigns.update", [{
            "id": campaign_id, "type": "fulltext",
            "status": "suspend", "dayBudget": want_budget,
        }]))

    done = existing_groups(api, campaign_id)
    keywords: list[dict] = []
    ads: list[dict] = []
    for group in plan["groups"]:
        if group["name"] in done:
            group_id = done[group["name"]]
            print(f"[sestava] „{group['name']}\" už existuje → id {group_id}")
        else:
            response = ensure_ok("groups.create", api.call("groups.create", [{
                "campaignId": campaign_id,
                "name": group["name"],
                "cpc": int(group["cpc"]),
                "status": "suspend",
            }]))
            group_id = response["groupIds"][0]
            print(f"[sestava] „{group['name']}\" → id {group_id} (CPC {group['cpc'] / 100:.2f} Kč)")
        result["groups"][group["name"]] = group_id
        # CPC se posílá jen na sestavě — u KW se vynechává schválně
        keywords += [{"groupId": group_id, "name": k["name"], "matchType": k["matchType"]}
                     for k in group["keywords"]]
        ads += [dict(ad, groupId=group_id) for ad in group["ads"]]

    for batch in chunked(keywords, create_limit):
        response = api.call("keywords.create", batch)
        if response.get("status") == 406:  # keyword_duplicate — už založeno dřívějším během
            print(f"[KW] dávka {len(batch)}: duplicity přeskočeny ({response.get('statusMessage')})")
            continue
        ensure_ok("keywords.create", response)
        print(f"[KW] +{len(batch)}")
    result["counts"]["keywords"] = len(keywords)

    for batch in chunked(ads, create_limit):
        ensure_ok("ads.check", api.call(
            "ads.check", [{k: v for k, v in ad.items() if k != "status"} for ad in batch]))
        response = api.call("ads.create", batch)
        if response.get("status") == 406:
            print(f"[reklamy] dávka {len(batch)}: duplicity přeskočeny "
                  f"({response.get('statusMessage')})")
            continue
        ensure_ok("ads.create", response)
        print(f"[reklamy] +{len(batch)}")
    result["counts"]["ads"] = len(ads)

    sitelink_ids = plan.get("sitelink_ids") or []
    if sitelink_ids:
        ensure_ok("sitelinks.campaign.set", api.call(
            "sitelinks.campaign.set", [{"id": campaign_id, "sitelinkIds": sitelink_ids}]))
        print(f"[sitelinky] přiřazeno {len(sitelink_ids)}")
    return result


def verify(api: Api, campaign_id: int) -> dict:
    campaign = ensure_ok("campaigns.list", api.call(
        "campaigns.list", {"ids": [campaign_id]},
        {"offset": 0, "limit": 1,
         "displayColumns": ["id", "name", "status", "type", "budget.dayBudget"]}))["campaigns"][0]
    groups = ensure_ok("groups.list", api.call(
        "groups.list", {"campaign": {"ids": [campaign_id]}, "isDeleted": False},
        {"offset": 0, "limit": 500,
         "displayColumns": ["id", "name", "status", "maxCpc"]}))["groups"]
    out = {"campaign": campaign, "groups": []}
    for group in groups:
        kw = ensure_ok("keywords.list", api.call(
            "keywords.list", {"group": {"ids": [group["id"]]}, "isDeleted": False},
            {"offset": 0, "limit": 500, "displayColumns": ["id", "name", "matchType", "cpc"]}
        ))["keywords"]
        ads = ensure_ok("ads.list", api.call(
            "ads.list", {"group": {"ids": [group["id"]]}, "isDeleted": False},
            {"offset": 0, "limit": 100,
             "displayColumns": ["id", "status", "headline1", "headline2", "headline3",
                                "description", "description2", "finalUrl"]}))["ads"]
        stray_cpc = [k["name"] for k in kw if k.get("cpc")]
        out["groups"].append({
            "id": group["id"], "name": group["name"], "status": group["status"],
            "maxCpc": group.get("maxCpc"), "keywords": len(kw), "ads": len(ads),
            "kw_s_vlastnim_cpc": stray_cpc,
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Sklik: nová vyhledávací kampaň (dry-run default)")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--apply", action="store_true", help="Provede zápis do účtu")
    parser.add_argument("--verify-only", action="store_true",
                        help="Jen načte hotovou kampaň z účtu a vypíše kontrolu")
    args = parser.parse_args()

    plan = load_plan(args.plan, apply_mode=args.apply)
    api = Api(int(plan["user_id"]))
    limits = ensure_ok("api.limits", api.call("api.limits", managed=False))

    if args.verify_only:
        campaign_id = find_campaign(api, plan["campaign"]["name"])
        if not campaign_id:
            raise SystemExit("Kampaň v účtu neexistuje.")
        print(json.dumps(verify(api, campaign_id), ensure_ascii=False, indent=2))
        return

    day_min = int(limits["limits"]["dayBudgetMin"])
    cpc_min = int(limits["limits"]["CpcMin"])
    if int(plan["campaign"]["dayBudget"]) < day_min:
        raise SystemExit(f"Rozpočet pod minimem API ({day_min} h).")
    for group in plan["groups"]:
        if int(group["cpc"]) < cpc_min:
            raise SystemExit(f"{group['name']}: CPC pod minimem API ({cpc_min} h).")

    if not args.apply:
        # campaigns.check pole `status` nepřijímá (not_allowed_struct_field), i když ho
        # campaigns.create bere — stejná past jako u ads.check.
        ensure_ok("campaigns.check", api.call("campaigns.check", [
            {k: v for k, v in campaign_struct(plan).items() if k != "status"}]))
        print(json.dumps({
            "mode": "dry-run",
            "change_id": plan.get("change_id"),
            "account": plan.get("account"),
            "campaign": plan["campaign"]["name"],
            "dayBudget_Kc": int(plan["campaign"]["dayBudget"]) / 100,
            "groups": [{"name": g["name"], "cpc_Kc": g["cpc"] / 100,
                        "keywords": len(g["keywords"]), "ads": len(g["ads"])}
                       for g in plan["groups"]],
            "campaign_negatives": len(plan.get("campaign_negatives") or []),
            "sitelinks": len(plan.get("sitelink_ids") or []),
            "validace": "lokální limity ETA + policy + campaigns.check prošly",
            "note": "DRY-RUN: žádná create metoda nezavolána. Reklamy se ověří přes ads.check "
                    "až při --apply (ads.check vyžaduje existující groupId).",
        }, ensure_ascii=False, indent=2))
        return

    result = apply_plan(api, plan, limits)
    print("\n== VERIFIKACE (čteno zpět z účtu) ==")
    print(json.dumps(verify(api, result["campaign_id"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

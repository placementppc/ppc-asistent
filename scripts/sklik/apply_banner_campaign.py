#!/usr/bin/env python3
"""Založení časově omezené bannerové RMKT kampaně ve Skliku (obrázkové bannery).

Čte plán z JSON (clients/<klient>-plan-*.json) a zakládá:
  kampaně (se startDate / endDate) → sestavy → cílení na zařízení → publika → bannery.

Vše se zakládá se `status: suspend`. Spuštění je samostatný krok `--activate` — kampaň
pak čeká na `startDate` a po `endDate` se sama zastaví.

⚠️ `endDate` přes API = půlnoc na ZAČÁTKU dne. Má-li kampaň běžet celý den 21. 9.,
   patří do plánu `endDate: 2026-09-22` (napoveda.sklik.cz → Práce s API Drak).

Bannery jdou binárně (`file`), proto XML-RPC — stejně jako apply_rmkt_res.py.

Použití:
    python scripts/sklik/apply_banner_campaign.py PLAN.json              # dry-run
    python scripts/sklik/apply_banner_campaign.py PLAN.json --apply
    python scripts/sklik/apply_banner_campaign.py PLAN.json --verify
    python scripts/sklik/apply_banner_campaign.py PLAN.json --activate

--apply a --activate projdou jen s plánem, který má `"approval": {"status": "approved", ...}`.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import xmlrpc.client
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_rmkt_res import Api  # noqa: E402
from lib.env import require  # noqa: E402

MAX_BANNER_BYTES = 256_000
# images.constraints.list, sekce banner (viz knowledge/tvorba-kampani/04-SKLIK-SPECIFIKA.md)
ALLOWED_SIZES = {(300, 300), (160, 600), (728, 90), (300, 250), (300, 600), (970, 310),
                 (320, 100), (970, 210), (480, 300), (480, 480), (720, 1280), (500, 200)}


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:32]
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    raise SystemExit(f"Neznámý formát obrázku (čekám PNG/GIF): {path}")


def check_files(plan: dict) -> None:
    """Rozměr na pixel a velikost — Sklik jinak vrací invalid_size / image_too_large."""
    problems = []
    for b in plan["bannery"]:
        p = Path(b["file"])
        if not p.exists():
            problems.append(f"chybí soubor: {p}")
            continue
        size, dims = p.stat().st_size, image_size(p)
        ok = dims in ALLOWED_SIZES and size <= MAX_BANNER_BYTES
        print(f"  [banner] {b['key']:<8} {dims[0]}×{dims[1]} | {size / 1000:.0f} kB | "
              f"{'OK' if ok else 'NEPROJDE'}")
        if dims not in ALLOWED_SIZES:
            problems.append(f"{p.name}: rozměr {dims} Sklik nepodporuje")
        if size > MAX_BANNER_BYTES:
            problems.append(f"{p.name}: {size} B > {MAX_BANNER_BYTES} B")
    if problems:
        raise SystemExit("STOP:\n- " + "\n- ".join(problems))


def final_url(plan: dict, camp: dict, group: dict) -> str:
    return f"{plan['finalUrl']}&utm_content={camp['utmDevice']}_{group['utmSegment']}"


def xml_date(day: str) -> xmlrpc.client.DateTime:
    return xmlrpc.client.DateTime(day.replace("-", "") + "T00:00:00")


# --------------------------------------------------------------------- dry-run
def dry_run(plan: dict) -> None:
    print("== DRY-RUN — v účtu se nic nezmění ==\n")
    check_files(plan)
    total = 0
    for camp in plan["kampane"]:
        total += camp["dayBudget"]
        print(f"\n[kampaň] {camp['name']} | {camp['type']} | {camp['paymentMethod']} | "
              f"{camp['dayBudget'] / 100:.0f} Kč/den | {camp['startDate']} → {camp['endDate']} "
              f"(API konec = půlnoc na začátku dne) | {camp['status']}")
        for g in camp["groups"]:
            print(f"  [sestava] {g['name']} | CPC {g['cpc'] / 100:.2f} Kč | "
                  f"frekvence {g['maxUserDailyImpression']}/den | {g['devicesPriceRatio']}")
            print(f"      publika +{g['retargetingInclude']} −{g['retargetingExclude'] or '—'}")
            print(f"      URL {final_url(plan, camp, g)}")
            print(f"      bannerů {len(plan['bannery'])}")
    print(f"\nDenní rozpočet celkem: {total / 100:.0f} Kč")


# ----------------------------------------------------------------------- apply
def apply(api: Api, plan: dict) -> None:
    print("== APPLY — zakládám v účtu (vše jako suspend) ==\n")
    check_files(plan)
    existing = api.call("campaigns.list", {"isDeleted": False},
                        {"offset": 0, "limit": 1000, "displayColumns": ["id", "name"]})
    existing_camps = {c["name"]: c["id"] for c in existing.get("campaigns", [])}

    for camp in plan["kampane"]:
        if camp["name"] in existing_camps:
            camp_id = existing_camps[camp["name"]]
            print(f"\n[kampaň] {camp['name']} už existuje → id {camp_id}")
        else:
            r = api.call("campaigns.create", [{
                "name": camp["name"],
                "type": camp["type"],
                "paymentMethod": camp["paymentMethod"],
                "adSelection": camp["adSelection"],
                "dayBudget": camp["dayBudget"],
                "status": "suspend",
                "startDate": xml_date(camp["startDate"]),
                "endDate": xml_date(camp["endDate"]),
            }])
            camp_id = r["campaignIds"][0]
            print(f"\n[kampaň] {camp['name']} → id {camp_id}")
            # campaigns.create spolehlivě nezapisuje budget/status → doplnit updatem
            # zařízení patří i na kampaň: −100 % tam platí vždy a uživatel ho vidí v nastavení
            api.call("campaigns.update", [{"id": camp_id, "type": camp["type"],
                                           "dayBudget": camp["dayBudget"], "status": "suspend",
                                           "devicesPriceRatio": camp["devicesPriceRatio"]}])

        done = {g["name"]: g["id"] for g in api.call(
            "groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
            {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]}).get("groups", [])}
        for g in camp["groups"]:
            if g["name"] in done:
                gid = done[g["name"]]
                print(f"  [sestava] {g['name']} už existuje → id {gid}")
            else:
                r = api.call("groups.create", [{
                    "campaignId": camp_id,
                    "name": g["name"],
                    "cpc": g["cpc"],
                    "status": "suspend",
                    "maxUserDailyImpression": g["maxUserDailyImpression"],
                    "devicesPriceRatio": g["devicesPriceRatio"],
                }])
                gid = r["groupIds"][0]
                print(f"  [sestava] {g['name']} → id {gid}")
                api.call("groups.update", [{"id": gid,
                                            "devicesPriceRatio": g["devicesPriceRatio"]}])
                for lid in g["retargetingInclude"]:
                    api.call("retargeting.group.lists.add", [{"listId": lid, "groupId": gid}])
                for lid in g["retargetingExclude"]:
                    api.call("retargeting.group.negative.add",
                             [{"entityId": lid, "groupId": gid}])
                print(f"      publika +{g['retargetingInclude']} −{g['retargetingExclude'] or '—'}")

            have = {b.get("bannerName") for b in api.call(
                "banners.list", {"group": {"ids": [gid]}, "isDeleted": False},
                {"offset": 0, "limit": 100, "displayColumns": ["id", "bannerName"]}
            ).get("banners", [])}
            todo = [b for b in plan["bannery"] if f"{plan['bannerPrefix']} {b['key']}" not in have]
            if not todo:
                print("      bannery už existují → přeskakuji")
                continue
            url = final_url(plan, camp, g)
            r = api.call("banners.create", [{
                "requestId": i,
                "groupId": gid,
                "name": f"{plan['bannerPrefix']} {b['key']}",
                "clickthruUrl": url,
                "status": "suspend",
                "file": xmlrpc.client.Binary(Path(b["file"]).read_bytes()),
            } for i, b in enumerate(todo)])
            print(f"      bannery → {len(r.get('bannerIds', []))} ks")

    print("\nHotovo. Ověření: --verify")


# ---------------------------------------------------------------------- verify
def verify(api: Api, plan: dict) -> list[tuple[dict, int, list[dict]]]:
    print("== VERIFIKACE — čtu zpět, co je reálně v účtu ==\n")
    r = api.call("campaigns.list", {"isDeleted": False},
                 {"offset": 0, "limit": 1000,
                  "displayColumns": ["id", "name", "status", "budget.dayBudget",
                                     "startDate", "endDate", "paymentMethod",
                                     "devicesPriceRatio"]})
    by_name = {c["name"]: c for c in r.get("campaigns", [])}
    problems, found = [], []
    for camp in plan["kampane"]:
        c = by_name.get(camp["name"])
        if not c:
            problems.append(f"kampaň chybí: {camp['name']}")
            continue
        budget = (c.get("budget") or {}).get("dayBudget")
        print(f"[kampaň] {camp['name']} | id {c['id']} | {c.get('status')} | "
              f"rozpočet {budget} | {c.get('startDate')} → {c.get('endDate')}")
        if budget != camp["dayBudget"]:
            problems.append(f"{camp['name']}: rozpočet {budget} != {camp['dayBudget']}")
        if c.get("devicesPriceRatio") != camp["devicesPriceRatio"]:
            problems.append(f"{camp['name']}: zařízení na kampani {c.get('devicesPriceRatio')}")
        for key in ("startDate", "endDate"):
            if camp[key].replace("-", "") not in str(c.get(key)).replace("-", ""):
                problems.append(f"{camp['name']}: {key} {c.get(key)} != {camp[key]}")

        gr = api.call("groups.list", {"campaign": {"ids": [c["id"]]}, "isDeleted": False},
                      {"offset": 0, "limit": 100,
                       "displayColumns": ["id", "name", "maxCpc", "status",
                                          "devicesPriceRatio", "maxUserDailyImpressions"]})
        groups = gr.get("groups", [])
        found.append((camp, c["id"], groups))
        names = {g["name"] for g in groups}
        for plan_g in camp["groups"]:
            if plan_g["name"] not in names:
                problems.append(f"sestava chybí: {camp['name']} / {plan_g['name']}")
        for g in groups:
            plan_g = next((x for x in camp["groups"] if x["name"] == g["name"]), None)
            if not plan_g:
                continue
            if g.get("maxCpc") != plan_g["cpc"]:
                problems.append(f"{g['name']}: CPC {g.get('maxCpc')} != {plan_g['cpc']}")
            if g.get("devicesPriceRatio") != plan_g["devicesPriceRatio"]:
                problems.append(f"{g['name']}: cílení na zařízení nesedí "
                                f"{g.get('devicesPriceRatio')}")
            lr = api.call("retargeting.group.lists.list", [g["id"]])
            inc = sorted(x["listId"] for x in lr.get("groupLists", lr.get("lists", [])))
            if inc != sorted(plan_g["retargetingInclude"]):
                problems.append(f"{g['name']}: publika {inc} != {plan_g['retargetingInclude']}")
            n = api.call("retargeting.group.negative.count", [g["id"]])
            n_neg = n.get("counts", n.get("count"))
            if isinstance(n_neg, list):
                n_neg = (n_neg[0] or {}).get("count") if isinstance(n_neg[0], dict) else n_neg[0]
            if n_neg != len(plan_g["retargetingExclude"]):
                problems.append(f"{g['name']}: vyloučených publik {n_neg} != "
                                f"{len(plan_g['retargetingExclude'])}")
            br = api.call("banners.list", {"group": {"ids": [g["id"]]}, "isDeleted": False},
                          {"offset": 0, "limit": 100,
                           "displayColumns": ["id", "bannerName", "width", "height", "status",
                                              "adStatus", "clickthruUrl"]})
            banners = br.get("banners", [])
            url = final_url(plan, camp, plan_g)
            bad_url = [b["id"] for b in banners if b.get("clickthruUrl") != url]
            if len(banners) != len(plan["bannery"]):
                problems.append(f"{g['name']}: bannerů {len(banners)} != {len(plan['bannery'])}")
            if bad_url:
                problems.append(f"{g['name']}: URL nesedí u bannerů {bad_url}")
            print(f"  [sestava] {g['name']} | {g.get('status')} | CPC {g.get('maxCpc')} | "
                  f"frekvence {g.get('maxUserDailyImpressions')} | publika +{inc} "
                  f"−{n.get('counts', n.get('count'))} | bannerů {len(banners)} "
                  f"{sorted({b.get('adStatus') for b in banners})}")

    print("\n" + ("VŠE SEDÍ." if not problems else "NÁLEZY:\n- " + "\n- ".join(problems)))
    if problems:
        raise SystemExit(1)
    return found


def activate(api: Api, plan: dict) -> None:
    """Aktivuje bannery, sestavy i kampaně. Kampaň pak čeká na startDate."""
    for camp, camp_id, groups in verify(api, plan):
        for g in groups:
            br = api.call("banners.list", {"group": {"ids": [g["id"]]}, "isDeleted": False},
                          {"offset": 0, "limit": 100, "displayColumns": ["id"]})
            ids = [b["id"] for b in br.get("banners", [])]
            if ids:
                api.call("banners.update", [{"id": i, "status": "active"} for i in ids])
            api.call("groups.update", [{"id": g["id"], "status": "active"}])
            print(f"  {camp['name']} / {g['name']}: sestava + {len(ids)} bannerů active")
        api.call("campaigns.update", [{"id": camp_id, "type": camp["type"], "status": "active"}])
        print(f"[kampaň] {camp['name']} → active (běží {camp['startDate']} → {camp['endDate']})")



def require_approval(plan: dict) -> None:
    """Zápis jen se schváleným plánem — stejně jako ostatní apply skripty."""
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: approval.status v plánu není \"approved\". "
                         "Nech plán schválit člověkem a doplň "
                         "\"approval\": {\"status\": \"approved\", \"by\": \"…\", \"date\": \"YYYY-MM-DD\"}.")


def main() -> None:
    p = argparse.ArgumentParser(description="Sklik — bannerová RMKT kampaň s datem od–do")
    p.add_argument("plan", help="cesta k plan JSON")
    p.add_argument("--apply", action="store_true", help="skutečně založí (vše jako suspend)")
    p.add_argument("--verify", action="store_true", help="přečte zpět a porovná s plánem")
    p.add_argument("--activate", action="store_true",
                   help="po verifikaci aktivuje kampaně, sestavy i bannery")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if not (args.apply or args.verify or args.activate):
        dry_run(plan)
        return
    if args.apply or args.activate:
        require_approval(plan)

    token = require(plan["tokenEnv"])[plan["tokenEnv"]]
    api = Api(token, plan["userId"])
    limits = api.call("api.limits", managed=False)
    print("[API limity]", json.dumps(limits.get("limits", {}), ensure_ascii=False))
    if args.apply:
        apply(api, plan)
    elif args.activate:
        activate(api, plan)
    else:
        verify(api, plan)


if __name__ == "__main__":
    main()

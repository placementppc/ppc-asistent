#!/usr/bin/env python3
"""Založení remarketingových kampaní s kombinovanými (responzivními) reklamami ve Skliku.

Čte plán z JSON (viz clients/<klient>-plan-*.json) a zakládá:
  publika → kampaně → sestavy → cílení na zařízení → přiřazení publik → reklamy.

Vše se zakládá se `status: suspend`. Aktivaci spouští člověk až po kontrole, a to ručně
v Skliku, nebo tímhle skriptem s přepínačem `--activate` (aktivuje kampaně, sestavy i reklamy
z plánu). Bez `--activate` skript nic nespouští.

Volitelně `"nahradyTextu": {"<znak nebo řetězec>": "<náhrada>"}` v plánu: náhrady v popisku
reklamy před odesláním (a stejně i při --verify). Výchozí je prázdná mapa. Hodí se na znaky,
které Sklik tiše vypouští (speciální symboly → rozepsat slovem). Ověř po --apply přes --verify.

Proč XML-RPC a ne JSON endpoint: `ads.create` bere obrázky v poli typu `binary`.
Dokumentace (api.sklik.cz/drak/usage.html) říká, že binary = XML-RPC base64 hodnota,
což `xmlrpc.client.Binary` umí nativně. `images.create` by chtěl veřejnou URL na CDN,
kterou pro lokální soubory nemáme.

Použití:
    python scripts/sklik/apply_rmkt_res.py PLAN.json --dry-run
    python scripts/sklik/apply_rmkt_res.py PLAN.json --apply
    python scripts/sklik/apply_rmkt_res.py PLAN.json --verify
    python scripts/sklik/apply_rmkt_res.py PLAN.json --activate   # až po kontrole člověkem

Zápisové přepínače (--apply, --activate, --add-negative, --replace-ads, --repair) projdou jen
s plánem, který má `"approval": {"status": "approved", ...}`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import xmlrpc.client
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402

API_URL = "https://api.sklik.cz/drak/RPC2"   # /RPC2/v5 vrací 404, ověřeno 13. 8. 2026
TOKEN_ENV = "SKLIK_API_TOKEN"    # ověřený token s přístupem k účtu; klientský účet se předává přes userId
PAUSE = 0.4                      # sekundy mezi voláními (limit je 300 req/min)


class Api:
    def __init__(self, token: str, user_id: int) -> None:
        self.proxy = xmlrpc.client.ServerProxy(API_URL, allow_none=True)
        self.user_id = user_id
        r = self.proxy.client.loginByToken(token)
        if r.get("status") != 200:
            raise SystemExit(f"Login selhal: {r.get('status')} {r.get('statusMessage')}")
        self.session = r["session"]

    def call(self, method: str, *params, managed: bool = True):
        fn = self.proxy
        for part in method.split("."):
            fn = getattr(fn, part)
        user = {"session": self.session}
        if managed:
            user["userId"] = self.user_id
        for attempt in range(5):
            r = fn(user, *params)
            if r.get("status") == 429:
                wait = 5 * 2 ** attempt
                print(f"    ! 429, čekám {wait} s")
                time.sleep(wait)
                continue
            break
        if r.get("session"):
            self.session = r["session"]
        time.sleep(PAUSE)
        if r.get("status") not in (200, 206):
            raise SystemExit(f"{method}: {r.get('status')} {r.get('statusMessage')}\n"
                             f"  diagnostics: {json.dumps(r.get('diagnostics'), ensure_ascii=False)[:1500]}")
        if r.get("status") == 206:
            print(f"    ~ {method}: 206 s warningy: "
                  f"{json.dumps(r.get('diagnostics'), ensure_ascii=False)[:600]}")
        return r


def binary(path: str) -> xmlrpc.client.Binary:
    return xmlrpc.client.Binary(Path(path).read_bytes())


def jpeg_meta(path: str) -> dict:
    """Rozměry a velikost JPEG souboru pro pole *Meta v ads.check (bez uploadu)."""
    data = Path(path).read_bytes()
    i = 2
    w = h = None
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            break
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    if not w or not h:
        raise SystemExit(f"Nepodařilo se přečíst rozměry z {path}")
    return {"width": w, "height": h, "size": len(data)}


# Náhrady v popisku reklamy z plánu (`nahradyTextu`), výchozí žádné. Nastaví main().
TEXT_REPLACEMENTS: dict[str, str] = {}


def nahrad(text: str) -> str:
    """Použije náhrady z plánu (např. znak, který Sklik tiše vypouští → slovo)."""
    for co, cim in TEXT_REPLACEMENTS.items():
        text = text.replace(co, cim)
    return text


def ad_payload(ad: dict, group_id: int, req_id: int, for_check: bool = False) -> dict:
    """`ads.check` pole `status` nepřijímá (400 not_allowed_struct_field), `ads.create` ano."""
    payload = {
        "requestId": req_id,
        "groupId": group_id,
        "adType": "combined",
        "shortLine": ad["shortLine"],
        "longLine": ad["longLine"],
        # Sklik některé znaky tiše vypouští → náhrady z plánu (`nahradyTextu`).
        "description": nahrad(ad["description"]),
        "companyName": ad["companyName"],
        "finalUrl": ad["finalUrl"],
        "image": binary(ad["imageFile"]),
        "imageSquare": binary(ad["imageSquareFile"]),
        "imageLogoId": ad["imageLogoId"],
        "imageLandscapeLogoId": ad["imageLandscapeLogoId"],
        "colorMain": ad["colorMain"],
        "colorAccent": ad["colorAccent"],
        "status": "suspend",
    }
    if for_check:
        # ads.check binární obrázky nepřijme (fastCheck se s nimi vylučuje a nastavit nejde),
        # ale umí je ověřit z metadat — rozměry, poměr stran a velikost souboru
        # ads.check s checkDuplicity=False jede v režimu fastCheck, který se vylučuje
        # jak s binárními obrázky, tak s ID obrázků → všechno musí jít přes *Meta
        payload.pop("status")
        payload.pop("image")
        payload.pop("imageSquare")
        payload.pop("imageLogoId")
        payload.pop("imageLandscapeLogoId")
        payload["imageMeta"] = jpeg_meta(ad["imageFile"])
        payload["imageSquareMeta"] = jpeg_meta(ad["imageSquareFile"])
        payload["imageLogoMeta"] = ad["imageLogoMeta"]
        payload["imageLandscapeLogoMeta"] = ad["imageLandscapeLogoMeta"]
    return payload


# --------------------------------------------------------------------- dry-run
def dry_run(api: Api, plan: dict, check_group_id: int | None) -> None:
    print("== DRY-RUN — v účtu se nic nezmění ==\n")
    for lst in plan["novaPublika"]:
        conds = [c for g in lst["conditionGroups"] for c in g["conditions"]]
        print(f"[publikum] {lst['name']} | {lst['membership']} dnů | "
              f"historie={lst['useHistoricData']} | {conds}")
    for camp in plan["kampane"]:
        print(f"\n[kampaň] {camp['name']} | {camp['type']} | {camp['paymentMethod']} | "
              f"{camp['dayBudget'] / 100:.0f} Kč/den | {camp['status']}")
        for g in camp["groups"]:
            print(f"  [sestava] {g['name']} | CPC {g['cpc'] / 100:.2f} Kč | "
                  f"frekvence {g['maxUserDailyImpression']}/den | {g['devicesPriceRatio']}")
            print(f"      publika +{g['retargetingInclude'] or [g['retargetingIncludeNew']]} "
                  f"−{g['retargetingExclude'] or '—'}")
            for a in g["ads"]:
                print(f"      · {a['kolekce']:<12} {a['shortLine']!r} / {a['longLine']!r} / "
                      f"{a['description']!r}")

    if not check_group_id:
        print("\n(bez --check-group-id se texty a obrázky neověřují proti API)")
        return

    print(f"\n== ads.check proti sestavě {check_group_id} (jen validace, nic se nezakládá) ==")
    for camp in plan["kampane"]:
        for g in camp["groups"]:
            payload = [ad_payload(a, check_group_id, i, for_check=True)
                       for i, a in enumerate(g["ads"])]
            # checkDuplicity se vylučuje s binárními obrázky (ověřeno 400 exclusive_struct_field),
            # takže tenhle check ověří texty, obrázky a URL — ne duplicitu vůči účtu
            r = api.call("ads.check", payload, {"checkDuplicity": False})
            print(f"  {camp['name']} / {g['name']}: status {r.get('status')} "
                  f"({len(payload)} reklam)")


# ----------------------------------------------------------------------- apply
def apply(api: Api, plan: dict) -> None:
    print("== APPLY — zakládám v účtu (vše jako suspend) ==\n")

    # Idempotence: co už existuje, se přeskočí — skript jde bezpečně pustit znovu
    existing = api.call("campaigns.list", {"isDeleted": False},
                        {"offset": 0, "limit": 1000, "displayColumns": ["id", "name"]})
    existing_camps = {c["name"]: c["id"] for c in existing.get("campaigns", [])}

    # 1) nová publika (idempotentně — po přerušeném běhu už můžou existovat)
    existing_lists = {l["name"]: l["listId"] for l in
                      api.call("retargeting.lists.list").get("lists", [])
                      if not l.get("deleted")}
    list_ids: dict[str, int] = {}
    for lst in plan["novaPublika"]:
        if lst["name"] in existing_lists:
            list_ids[lst["key"]] = existing_lists[lst["name"]]
            print(f"[publikum] {lst['name']} už existuje → id {existing_lists[lst['name']]}")
            continue
        r = api.call("retargeting.lists.create", [{
            "attributes": {
                "name": lst["name"],
                "membership": lst["membership"],
                "useHistoricData": lst["useHistoricData"],
                "takeAllUsers": lst["takeAllUsers"],
                "description": lst["description"],
            },
            "conditionGroups": lst["conditionGroups"],
        }])
        new_id = (r.get("listIds") or r.get("ids") or [None])[0]
        list_ids[lst["key"]] = new_id
        print(f"[publikum] {lst['name']} → id {new_id}")

    # 2) kampaně, sestavy, cílení, publika, reklamy
    for camp in plan["kampane"]:
        if camp["name"] in existing_camps:
            camp_id = existing_camps[camp["name"]]
            print(f"\n[kampaň] {camp['name']} už existuje → id {camp_id}")
            done_groups = {g["name"] for g in api.call(
                "groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
                {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]}).get("groups", [])}
            _create_groups(api, camp, camp_id, list_ids, done_groups)
            continue
        r = api.call("campaigns.create", [{
            "name": camp["name"],
            "type": camp["type"],
            "paymentMethod": camp["paymentMethod"],
            "adSelection": camp["adSelection"],
            "dayBudget": camp["dayBudget"],
            "status": camp["status"],
            # XML-RPC chce datetime, ne string (400 wrong_param_type)
            "startDate": xmlrpc.client.DateTime(camp["startDate"].replace("-", "") + "T00:00:00")
                         if camp["startDate"] else None,
            "endDate": xmlrpc.client.DateTime(camp["endDate"].replace("-", "") + "T00:00:00")
                       if camp["endDate"] else None,
        }])
        camp_id = r["campaignIds"][0]
        print(f"\n[kampaň] {camp['name']} → id {camp_id}")

        # campaigns.create spolehlivě nezapisuje budget/status → doplnit updatem
        # (update vyžaduje i `type`, jinak 400 missing_struct_field)
        api.call("campaigns.update", [{
            "id": camp_id,
            "type": camp["type"],
            "dayBudget": camp["dayBudget"],
            "status": camp["status"],
        }])

        _create_groups(api, camp, camp_id, list_ids, set())

    print("\nHotovo. Ověření: --verify")


def _create_groups(api: Api, camp: dict, camp_id: int, list_ids: dict,
                   done_groups: set) -> None:
    for g in camp["groups"]:
        if g["name"] in done_groups:
            print(f"  [sestava] {g['name']} už existuje → přeskakuji")
            continue
        r = api.call("groups.create", [{
            "campaignId": camp_id,
            "name": g["name"],
            "cpc": g["cpc"],
            "status": g["status"],
            "maxUserDailyImpression": g["maxUserDailyImpression"],
            "devicesPriceRatio": g["devicesPriceRatio"],
        }])
        gid = r["groupIds"][0]
        print(f"  [sestava] {g['name']} → id {gid}")

        # cílení na zařízení potvrdit updatem (create ho neuloží vždy)
        api.call("groups.update", [{
            "id": gid,
            "devicesPriceRatio": g["devicesPriceRatio"],
        }])

        includes = list(g["retargetingInclude"])
        if g["retargetingIncludeNew"]:
            includes.append(list_ids[g["retargetingIncludeNew"]])
        for lid in includes:
            api.call("retargeting.group.lists.add", [{"listId": lid, "groupId": gid}])
        excludes = list(g["retargetingExclude"])
        excludes += [list_ids[key] for key in g.get("retargetingExcludeNew", [])]
        for lid in excludes:
            api.call("retargeting.group.negative.add", [{"entityId": lid, "groupId": gid}])
        print(f"      publika +{includes} −{excludes or '—'}")

        payload = [ad_payload(a, gid, i) for i, a in enumerate(g["ads"])]
        r = api.call("ads.create", payload)
        print(f"      reklamy → {len(r.get('adIds', []))} ks")


# ------------------------------------------------------- vyloučení a aktivace
def _plan_campaign_ids(api: Api, plan: dict) -> list[tuple[dict, int]]:
    r = api.call("campaigns.list", {"isDeleted": False},
                 {"offset": 0, "limit": 1000, "displayColumns": ["id", "name"]})
    by_name = {c["name"]: c["id"] for c in r.get("campaigns", [])}
    out = []
    for camp in plan["kampane"]:
        if camp["name"] not in by_name:
            raise SystemExit(f"Kampaň '{camp['name']}' v účtu není — nejdřív --apply.")
        out.append((camp, by_name[camp["name"]]))
    return out


def add_negative(api: Api, plan: dict, list_id: int) -> None:
    """Přidá vylučující publikum na všechny sestavy z plánu."""
    info = api.call("retargeting.lists.get", [list_id]).get("lists", [])
    if not info:
        raise SystemExit(f"Publikum {list_id} neexistuje.")
    a = info[0]["attributes"]
    conds = [(c["type"], c["value"]) for g in info[0].get("conditionGroups", [])
             for c in g.get("conditions", [])]
    print(f"[publikum] {a['name']} | {a.get('users')} uživatelů | "
          f"takeAllUsers={a.get('takeAllUsers')} | podmínky {conds}")
    if a.get("takeAllUsers"):
        raise SystemExit("STOP: publikum má takeAllUsers=True, tedy sbírá všechny návštěvníky. "
                         "Vyloučit ho by zabilo doručování celé kampaně.")

    for camp, camp_id in _plan_campaign_ids(api, plan):
        gr = api.call("groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
                      {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]})
        for g in gr.get("groups", []):
            api.call("retargeting.group.negative.add",
                     [{"entityId": list_id, "groupId": g["id"]}])
            n = api.call("retargeting.group.negative.count", [g["id"]])
            print(f"  {camp['name']} / {g['name']} → vyloučených publik: "
                  f"{n.get('counts', n.get('count'))}")


def replace_ads(api: Api, plan: dict, status: str) -> None:
    """Vymění texty reklam. `ads.update` obsah měnit neumí → remove + create."""
    for camp, camp_id in _plan_campaign_ids(api, plan):
        gr = api.call("groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
                      {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]})
        for g in gr.get("groups", []):
            plan_g = next((x for x in camp["groups"] if x["name"] == g["name"]), None)
            if not plan_g:
                continue
            ar = api.call("ads.list", {"group": {"ids": [g["id"]]}, "isDeleted": False},
                          {"offset": 0, "limit": 100, "displayColumns": ["id"]})
            old = [a["id"] for a in ar.get("ads", [])]
            if old:
                api.call("ads.remove", old)
            payload = [ad_payload(a, g["id"], i) for i, a in enumerate(plan_g["ads"])]
            for a in payload:
                a["status"] = status
            r = api.call("ads.create", payload)
            print(f"  {camp['name']} / {g['name']}: smazáno {len(old)}, "
                  f"vytvořeno {len(r.get('adIds', []))} ({status})")


def repair(api: Api, plan: dict) -> None:
    """Doplní jen chybějící publika a reklamy po přerušeném create běhu."""
    known_lists = {l["name"]: l["listId"] for l in api.call("retargeting.lists.list").get("lists", [])
                   if not l.get("deleted")}
    list_ids = {item["key"]: known_lists[item["name"]] for item in plan["novaPublika"]
                if item["name"] in known_lists}
    for camp, camp_id in _plan_campaign_ids(api, plan):
        current = api.call("groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
                           {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]})
        by_name = {g["name"]: g["id"] for g in current.get("groups", [])}
        for group in camp["groups"]:
            group_id = by_name[group["name"]]
            linked = api.call("retargeting.group.lists.list", [group_id])
            linked_lists = linked.get("groupLists", linked.get("lists", []))
            if not linked_lists:
                includes = list(group["retargetingInclude"])
                includes.append(list_ids[group["retargetingIncludeNew"]])
                for list_id in includes:
                    api.call("retargeting.group.lists.add", [{"listId": list_id, "groupId": group_id}])
                excludes = list(group["retargetingExclude"])
                excludes += [list_ids[key] for key in group.get("retargetingExcludeNew", [])]
                for list_id in excludes:
                    api.call("retargeting.group.negative.add", [{"entityId": list_id, "groupId": group_id}])
                print(f"  {group['name']}: doplněna publika")
            ads = api.call("ads.list", {"group": {"ids": [group_id]}, "isDeleted": False},
                           {"offset": 0, "limit": 100, "displayColumns": ["id"]}).get("ads", [])
            if not ads:
                payload = [ad_payload(ad, group_id, index) for index, ad in enumerate(group["ads"])]
                api.call("ads.create", payload)
                print(f"  {group['name']}: doplněny {len(payload)} reklamy")


def activate(api: Api, plan: dict) -> None:
    """Aktivuje kampaně, sestavy i reklamy z plánu."""
    for camp, camp_id in _plan_campaign_ids(api, plan):
        gr = api.call("groups.list", {"campaign": {"ids": [camp_id]}, "isDeleted": False},
                      {"offset": 0, "limit": 100, "displayColumns": ["id", "name"]})
        for g in gr.get("groups", []):
            ar = api.call("ads.list", {"group": {"ids": [g["id"]]}, "isDeleted": False},
                          {"offset": 0, "limit": 100, "displayColumns": ["id", "status"]})
            ad_ids = [x["id"] for x in ar.get("ads", [])]
            if ad_ids:
                # bez adType si ads.update myslí, že jde o `eta`, a spadne
                # na 406 not_allowed_for_campaign_type v obsahové kampani
                api.call("ads.update", [{"id": i, "adType": "combined", "status": "active"}
                                        for i in ad_ids])
            api.call("groups.update", [{"id": g["id"], "status": "active"}])
            print(f"  {camp['name']} / {g['name']}: sestava + {len(ad_ids)} reklam aktivní")
        api.call("campaigns.update", [{"id": camp_id, "type": camp["type"], "status": "active"}])
        print(f"[kampaň] {camp['name']} → active")


# ---------------------------------------------------------------------- verify
def verify(api: Api, plan: dict) -> None:
    print("== VERIFIKACE — čtu zpět, co je reálně v účtu ==\n")
    r = api.call("campaigns.list", {"isDeleted": False},
                 {"offset": 0, "limit": 1000,
                  "displayColumns": ["id", "name", "status", "budget.dayBudget", "context"]})
    by_name = {c["name"]: c for c in r.get("campaigns", [])}
    problems = []

    wanted = {a["shortLine"]: a for camp in plan["kampane"]
              for g in camp["groups"] for a in g["ads"]}

    for camp in plan["kampane"]:
        c = by_name.get(camp["name"])
        if not c:
            problems.append(f"kampaň chybí: {camp['name']}")
            continue
        budget = (c.get("budget") or {}).get("dayBudget")
        ok_b = budget == camp["dayBudget"]
        ok_s = c.get("status") == "suspend"
        print(f"[kampaň] {camp['name']} | id {c['id']} | rozpočet {budget} "
              f"({'OK' if ok_b else 'NESEDÍ'}) | status {c.get('status')} "
              f"({'OK' if ok_s else 'NESEDÍ'})")
        if not ok_b:
            problems.append(f"{camp['name']}: rozpočet {budget} != {camp['dayBudget']}")
        if not ok_s:
            problems.append(f"{camp['name']}: status {c.get('status')} != suspend")

        gr = api.call("groups.list", {"campaign": {"ids": [c["id"]]}, "isDeleted": False},
                      {"offset": 0, "limit": 100,
                       "displayColumns": ["id", "name", "maxCpc", "status",
                                          "devicesPriceRatio", "maxUserDailyImpressions"]})
        for g in gr.get("groups", []):
            plan_g = next((x for x in camp["groups"] if x["name"] == g["name"]), None)
            if not plan_g:
                continue
            dev_ok = g.get("devicesPriceRatio") == plan_g["devicesPriceRatio"]
            cpc_ok = g.get("maxCpc") == plan_g["cpc"]
            print(f"  [sestava] {g['name']} | CPC {g.get('maxCpc')} "
                  f"({'OK' if cpc_ok else 'NESEDÍ'}) | zařízení "
                  f"{g.get('devicesPriceRatio')} ({'OK' if dev_ok else 'NESEDÍ'}) | "
                  f"frekvence {g.get('maxUserDailyImpressions')}")
            if not dev_ok:
                problems.append(f"{g['name']}: cílení na zařízení nesedí")
            if not cpc_ok:
                problems.append(f"{g['name']}: CPC {g.get('maxCpc')} != {plan_g['cpc']}")

            # metoda bere pole groupIds jako druhý parametr, ne restrictionFilter struct
            lr = api.call("retargeting.group.lists.list", [g["id"]])
            n_lists = len(lr.get("groupLists", lr.get("lists", [])))
            if n_lists == 0:
                problems.append(f"{g['name']}: NEMÁ přiřazené publikum")
            print(f"      přiřazených publik: {n_lists}")

            ar = api.call("ads.list", {"group": {"ids": [g["id"]]}, "isDeleted": False},
                          {"offset": 0, "limit": 100,
                           "displayColumns": ["id", "adType", "shortLine", "longLine",
                                              "description", "companyName", "finalUrl",
                                              "status", "adStatus", "image.id",
                                              "imageSquare.id", "imageLogo.id",
                                              "imageLandscapeLogo.id"]})
            for ad in ar.get("ads", []):
                w = wanted.get(ad.get("shortLine"))
                if not w:
                    continue
                for field in ("shortLine", "longLine", "description", "companyName"):
                    expected = nahrad(w[field]) if field == "description" else w[field]
                    if ad.get(field) != expected:
                        problems.append(f"TEXT NESEDÍ [{ad['id']}] {field}: "
                                        f"{ad.get(field)!r} != {expected!r}")
                if not (ad.get("imageLogo") or {}).get("id"):
                    problems.append(f"reklama {ad['id']} nemá logo")
                if not (ad.get("imageSquare") or {}).get("id"):
                    problems.append(f"reklama {ad['id']} nemá čtvercový obrázek")
            print(f"      reklam: {len(ar.get('ads', []))}")

    print("\n" + ("VŠE SEDÍ." if not problems else "NÁLEZY:\n- " + "\n- ".join(problems)))



def require_approval(plan: dict) -> None:
    """Zápis jen se schváleným plánem — stejně jako ostatní apply skripty."""
    if (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: approval.status v plánu není \"approved\". "
                         "Nech plán schválit člověkem a doplň "
                         "\"approval\": {\"status\": \"approved\", \"by\": \"…\", \"date\": \"YYYY-MM-DD\"}.")


def main() -> None:
    p = argparse.ArgumentParser(description="Sklik — založení RMKT kampaní s kombinovanými reklamami")
    p.add_argument("plan", help="cesta k plan JSON")
    p.add_argument("--dry-run", action="store_true", help="jen vypíše, co by udělal (výchozí)")
    p.add_argument("--check-group-id", type=int,
                   help="ID existující sestavy, proti které se pustí ads.check (validace textů a obrázků)")
    p.add_argument("--apply", action="store_true", help="skutečně založí (vše jako suspend)")
    p.add_argument("--verify", action="store_true", help="přečte zpět a porovná s plánem")
    p.add_argument("--add-negative", type=int, metavar="LIST_ID",
                   help="přidá vylučující publikum na všechny sestavy z plánu")
    p.add_argument("--replace-ads", choices=["active", "suspend"], metavar="STATUS",
                   help="smaže reklamy v sestavách a vytvoří je znovu podle plánu")
    p.add_argument("--repair", action="store_true",
                   help="doplní chybějící publika a reklamy po přerušeném create běhu")
    p.add_argument("--activate", action="store_true",
                   help="aktivuje kampaně, sestavy i reklamy (až po kontrole člověkem)")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if args.apply or args.activate or args.add_negative or args.replace_ads or args.repair:
        require_approval(plan)
    TEXT_REPLACEMENTS.clear()
    TEXT_REPLACEMENTS.update({str(k): str(v) for k, v in (plan.get("nahradyTextu") or {}).items()})
    token = require(TOKEN_ENV)[TOKEN_ENV]
    api = Api(token, plan["userId"])
    limits = api.call("api.limits", managed=False)
    print("[API limity]", json.dumps(limits.get("limits", {}), ensure_ascii=False))

    if args.apply:
        apply(api, plan)
    elif args.add_negative:
        add_negative(api, plan, args.add_negative)
    elif args.replace_ads:
        replace_ads(api, plan, args.replace_ads)
    elif args.repair:
        repair(api, plan)
    elif args.activate:
        activate(api, plan)
    elif args.verify:
        verify(api, plan)
    else:
        dry_run(api, plan, args.check_group_id)


if __name__ == "__main__":
    main()

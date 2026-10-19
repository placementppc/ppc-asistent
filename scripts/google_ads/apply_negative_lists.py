#!/usr/bin/env python3
"""Sdílené seznamy vylučujících slov + změny CPC klíčových slov podle plánu (JSON).

BEZPEČNOST:
- Výchozí režim je DRY-RUN: celá dávka se pošle s validate_only=True — Google ji
  zkontroluje, ale NIC nezapíše.
- Reálný zápis jen s --apply. Dávka je atomická (partial_failure=False): buď projde
  celá, nebo nic.
- Seznam se stejným názvem, který už v účtu existuje, skript odmítne (žádné duplicity).
- Rozpočty ani stav kampaní skript neumí měnit (umí jen pozastavit klíčová slova — pause_keywords).

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/apply_negative_lists.py clients/<plan>.json
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/apply_negative_lists.py clients/<plan>.json --apply

Schéma plánu:
{
  "<customer_id>": {
    "lists": [{"name": "...", "keywords": ["zdarma", ...], "campaigns": ["123", ...], "match": "PHRASE"}],
    "bids":  [{"ad_group_id": "...", "criterion_id": "...", "text": "...", "from": 11.1, "to": 8.0}],
    "remove_shared_criteria": ["customers/.../sharedCriteria/...~..."],
    "campaign_negatives": [{"campaign_id": "...", "text": "bazar", "match": "PHRASE"}],
    "add_shared_criteria": [{"shared_set_id": "...", "text": "návod", "match": "PHRASE"}],   # do EXISTUJÍCÍHO seznamu
    "link_shared_sets": [{"shared_set_id": "...", "campaign_id": "..."}],   # připojit EXISTUJÍCÍ seznam ke kampani
    "pause_keywords": [{"ad_group_id": "...", "criterion_id": "...", "text": "..."}]
  }
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

MAX_BID_CHANGE = 0.60  # pojistka: žádná změna CPC větší než ±60 % v jednom kroku


def existing_list_names(client, cid: str) -> set[str]:
    svc = client.get_service("GoogleAdsService")
    q = ("SELECT shared_set.name FROM shared_set "
         "WHERE shared_set.type = 'NEGATIVE_KEYWORDS' AND shared_set.status = 'ENABLED'")
    return {r.shared_set.name for b in svc.search_stream(customer_id=cid, query=q) for r in b.results}


def build_operations(client, cid: str, plan: dict) -> list:
    ops = []
    match_enum = client.enums.KeywordMatchTypeEnum
    for i, lst in enumerate(plan.get("lists", []), start=1):
        temp = f"customers/{cid}/sharedSets/-{i}"
        op = client.get_type("MutateOperation")
        ss = op.shared_set_operation.create
        ss.resource_name = temp
        ss.name = lst["name"]
        ss.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
        ops.append(op)
        for kw in lst["keywords"]:
            op = client.get_type("MutateOperation")
            sc = op.shared_criterion_operation.create
            sc.shared_set = temp
            sc.keyword.text = kw
            sc.keyword.match_type = getattr(match_enum, lst.get("match", "PHRASE"))
            ops.append(op)
        for camp_id in lst["campaigns"]:
            op = client.get_type("MutateOperation")
            css = op.campaign_shared_set_operation.create
            css.campaign = f"customers/{cid}/campaigns/{camp_id}"
            css.shared_set = temp
            ops.append(op)

    for rn in plan.get("remove_shared_criteria", []):
        op = client.get_type("MutateOperation")
        op.shared_criterion_operation.remove = rn
        ops.append(op)

    for neg in plan.get("campaign_negatives", []):
        op = client.get_type("MutateOperation")
        cc = op.campaign_criterion_operation.create
        cc.campaign = f"customers/{cid}/campaigns/{neg['campaign_id']}"
        cc.negative = True
        cc.keyword.text = neg["text"]
        cc.keyword.match_type = getattr(match_enum, neg.get("match", "PHRASE"))
        ops.append(op)

    for sc_plan in plan.get("add_shared_criteria", []):
        op = client.get_type("MutateOperation")
        sc = op.shared_criterion_operation.create
        sc.shared_set = f"customers/{cid}/sharedSets/{sc_plan['shared_set_id']}"
        sc.keyword.text = sc_plan["text"]
        sc.keyword.match_type = getattr(match_enum, sc_plan.get("match", "PHRASE"))
        ops.append(op)

    for ln in plan.get("link_shared_sets", []):
        op = client.get_type("MutateOperation")
        css = op.campaign_shared_set_operation.create
        css.campaign = f"customers/{cid}/campaigns/{ln['campaign_id']}"
        css.shared_set = f"customers/{cid}/sharedSets/{ln['shared_set_id']}"
        ops.append(op)

    for kw in plan.get("pause_keywords", []):
        op = client.get_type("MutateOperation")
        agc = op.ad_group_criterion_operation.update
        agc.resource_name = f"customers/{cid}/adGroupCriteria/{kw['ad_group_id']}~{kw['criterion_id']}"
        agc.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
        op.ad_group_criterion_operation.update_mask.paths.append("status")
        ops.append(op)

    for b in plan.get("bids", []):
        if b["from"] and abs(b["to"] - b["from"]) / b["from"] > MAX_BID_CHANGE:
            raise SystemExit(f"Změna CPC nad {MAX_BID_CHANGE:.0%}: {b}")
        op = client.get_type("MutateOperation")
        agc = op.ad_group_criterion_operation.update
        agc.resource_name = f"customers/{cid}/adGroupCriteria/{b['ad_group_id']}~{b['criterion_id']}"
        agc.cpc_bid_micros = int(round(b["to"] * 1_000_000))
        op.ad_group_criterion_operation.update_mask.paths.append("cpc_bid_micros")
        ops.append(op)
    return ops


def main() -> None:
    p = argparse.ArgumentParser(description="Sdílená negativa + CPC (dry-run bez --apply)")
    p.add_argument("plan")
    p.add_argument("--apply", action="store_true", help="Reálně zapsat (jinak validate_only)")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    client = build_client()
    svc = client.get_service("GoogleAdsService")

    for raw_cid, acc_plan in plan.items():
        if not raw_cid.isdigit():  # _meta / approval apod.
            continue
        cid = normalize_cid(raw_cid, "write")
        clash = {lst["name"] for lst in acc_plan.get("lists", [])} & existing_list_names(client, cid)
        if clash:
            raise SystemExit(f"{cid}: seznam už existuje: {sorted(clash)}")
        ops = build_operations(client, cid, acc_plan)
        for lst in acc_plan.get("lists", []):
            print(f"{cid} seznam „{lst['name']}“: {len(lst['keywords'])} slov, {len(lst['campaigns'])} kampaní")
        for b in acc_plan.get("bids", []):
            print(f"{cid} CPC {b['text']!r}: {b['from']} → {b['to']} (měna účtu)")
        for rn in acc_plan.get("remove_shared_criteria", []):
            print(f"{cid} odebrat ze seznamu: {rn}")
        for neg in acc_plan.get("campaign_negatives", []):
            print(f"{cid} negativum kampaně {neg['campaign_id']}: {neg['text']!r}")
        for sc_plan in acc_plan.get("add_shared_criteria", []):
            print(f"{cid} do seznamu {sc_plan['shared_set_id']}: {sc_plan['text']!r}")
        for ln in acc_plan.get("link_shared_sets", []):
            print(f"{cid} připojit seznam {ln['shared_set_id']} → kampaň {ln['campaign_id']}")
        for kw in acc_plan.get("pause_keywords", []):
            print(f"{cid} pozastavit KW {kw['ad_group_id']}~{kw['criterion_id']}: {kw.get('text', '')!r}")
        req = client.get_type("MutateGoogleAdsRequest")
        req.customer_id = cid
        req.mutate_operations.extend(ops)
        req.partial_failure = False
        req.validate_only = not args.apply
        resp = svc.mutate(request=req)
        mode = "ZAPSÁNO" if args.apply else "DRY-RUN OK (validate_only, nic nezapsáno)"
        print(f"{cid}: {mode} — {len(ops)} operací"
              + (f", výsledků {len(resp.mutate_operation_responses)}" if args.apply else ""))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Aplikace schválených změn v Google Ads podle plánu (JSON).

BEZPEČNOST:
- Ve výchozím stavu běží jako DRY-RUN: jen vypíše, co by provedl. NIC nezapíše.
- Reálný zápis proběhne POUZE s přepínačem --apply. To je tvoje potvrzení.
- Plán změn je čitelný JSON soubor (auditovatelné) — vznikl po schválení návrhů.

Použití:
  # náhled (nic nemění):
  python scripts/google_ads/apply_changes.py <customer_id> clients/<plan>.json
  # reálné provedení:
  python scripts/google_ads/apply_changes.py <customer_id> clients/<plan>.json --apply

Schéma plánu (JSON):
{
  "campaign_id": "0000000000",
  "ad_group_id": "0000000000",
  "add_negative_keywords": [{"text": "zdarma", "match": "BROAD"}, ...],   # negativa na úrovni KAMPANĚ
  "add_keywords":          [{"text": "služba město", "match": "PHRASE"}, ...],
  "pause_keywords":        ["návod", "bazar", ...],   # podle textu (v dané sestavě)
  "remove_keywords":       ["služba město|BROAD", ...],  # text|MATCH (volitelně match)
  "remove_ad_group_negatives": ["levná služba|PHRASE", ...],  # odebrání NEGATIVNÍCH KW ze sestavy
  "set_keyword_bids": [{"text": "služba město", "match": "PHRASE", "cpc_bid_micros": 20000000}, ...],
  "set_ad_group_bid":  {"ad_group_id": "...", "cpc_bid_micros": 25000000},   # nebo [{...}, {...}]
  "set_ad_status":     [{"ad_group_id": "...", "ad_id": "...", "status": "PAUSED"}],
  "update_rsa":        [{"ad_id": "...", "headlines": [...], "descriptions": [...]}],   # ID reklamy zůstane
  "add_structured_snippets": [{"campaign_id": "...", "header": "Služby", "values": [...]}],
  "update_sitelinks":  [{"asset_id": "...", "description1": "…≤35", "description2": "…≤35"}],
  "add_callouts":      [{"text": "…≤25"}],   # + "callout_campaign_ids": ["...", "..."]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402


def res_campaign(cid, camp_id):
    return f"customers/{cid}/campaigns/{camp_id}"


def res_ad_group(cid, ag_id):
    return f"customers/{cid}/adGroups/{ag_id}"


def existing_criteria(client, cid, ag_id, negative=False):
    """Mapa {(text_lower, match_name): resource_name} pro KW v sestavě.

    Default pozitivní (negative=False) — negativní KW nejdou pozastavit/upravit
    (CANT_UPDATE_NEGATIVE), ale jdou ODEBRAT (negative=True pro remove operace).
    """
    svc = client.get_service("GoogleAdsService")
    q = (
        "SELECT ad_group_criterion.resource_name, ad_group_criterion.keyword.text, "
        "ad_group_criterion.keyword.match_type, ad_group_criterion.negative "
        f"FROM ad_group_criterion WHERE ad_group.id = {ag_id} "
        "AND ad_group_criterion.type = 'KEYWORD' "
        f"AND ad_group_criterion.negative = {'true' if negative else 'false'} "
        "AND ad_group_criterion.status != 'REMOVED'"
    )
    out = {}
    for batch in svc.search_stream(customer_id=cid, query=q):
        for r in batch.results:
            kw = r.ad_group_criterion.keyword
            out[(kw.text.lower(), kw.match_type.name)] = r.ad_group_criterion.resource_name
    return out


def find_rn(crit_map, text, match=None):
    """Najde resource_name podle textu (a volitelně shody)."""
    text = text.lower()
    if match:
        return crit_map.get((text, match.upper()))
    # bez shody: vezmi první nalezenou variantu
    for (t, _m), rn in crit_map.items():
        if t == text:
            return rn
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="Aplikace plánu změn do Google Ads")
    p.add_argument("customer_id")
    p.add_argument("plan", help="Cesta k plán JSON")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ provede změny (jinak dry-run)")
    p.add_argument("--validate", action="store_true",
                   help="Nechá plán ověřit přímo Googlem (validate_only). Nic nezapíše, "
                        "ale odhalí chybná pole a hodnoty dřív než --apply.")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    client = build_client()

    mt_enum = client.enums.KeywordMatchTypeEnum
    status_enum = client.enums.AdGroupCriterionStatusEnum

    # campaign_id je povinné jen pro operace nad KW/sestavou; plány, které mění
    # jen nastavení kampaní (např. set_target_roas), si ID nesou u sebe.
    camp_rn = res_campaign(cid, plan["campaign_id"]) if plan.get("campaign_id") else None
    ag_rn = res_ad_group(cid, plan["ad_group_id"]) if plan.get("ad_group_id") else None

    # --- Sestavení operací ---
    neg_ops, add_ops, ag_update_ops, ag_remove_ops = [], [], [], []
    summary = []

    # 1) Negativa na úrovni kampaně
    for n in plan.get("add_negative_keywords", []):
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = camp_rn
        c.negative = True
        c.keyword.text = n["text"]
        c.keyword.match_type = getattr(mt_enum, n.get("match", "BROAD"))
        neg_ops.append(op)
        summary.append(f"  [+ NEG] {n['text']}  ({n.get('match','BROAD')})")

    # 2) Přidání klíčových slov do sestavy
    for k in plan.get("add_keywords", []):
        op = client.get_type("AdGroupCriterionOperation")
        c = op.create
        c.ad_group = ag_rn
        c.status = status_enum.ENABLED
        c.keyword.text = k["text"]
        c.keyword.match_type = getattr(mt_enum, k.get("match", "PHRASE"))
        add_ops.append(op)
        summary.append(f"  [+ KW ] {k['text']}  ({k.get('match','PHRASE')})")

    crit_map = None
    if plan.get("pause_keywords") or plan.get("remove_keywords"):
        crit_map = existing_criteria(client, cid, plan["ad_group_id"])

    # 3) Pozastavení klíčových slov (reversibilní)
    for text in plan.get("pause_keywords", []):
        rn = find_rn(crit_map, text)
        if not rn:
            summary.append(f"  [! PAUSE] '{text}' — NENALEZENO (přeskakuji)")
            continue
        op = client.get_type("AdGroupCriterionOperation")
        op.update.resource_name = rn
        op.update.status = status_enum.PAUSED
        op.update_mask.paths.append("status")
        ag_update_ops.append(op)
        summary.append(f"  [~ PAUSE] {text}")

    # 4) Odebrání klíčových slov (např. broad → nahrazeno frázovou)
    for spec in plan.get("remove_keywords", []):
        text, _, match = spec.partition("|")
        rn = find_rn(crit_map, text, match or None)
        if not rn:
            summary.append(f"  [! REMOVE] '{spec}' — NENALEZENO (přeskakuji)")
            continue
        op = client.get_type("AdGroupCriterionOperation")
        op.remove = rn
        ag_remove_ops.append(op)
        summary.append(f"  [- KW ] {spec}")

    # 4b) Odebrání NEGATIVNÍCH KW ze sestavy (odblokování dotazů)
    if plan.get("remove_ad_group_negatives"):
        neg_map = existing_criteria(client, cid, plan["ad_group_id"], negative=True)
        for spec in plan["remove_ad_group_negatives"]:
            text, _, match = spec.partition("|")
            rn = find_rn(neg_map, text, match or None)
            if not rn:
                summary.append(f"  [! -NEG] '{spec}' — NENALEZENO (přeskakuji)")
                continue
            op = client.get_type("AdGroupCriterionOperation")
            op.remove = rn
            ag_remove_ops.append(op)
            summary.append(f"  [- NEG sestavy] {spec}")

    # 4c) Změna CPC bidů klíčových slov (manual CPC)
    for kb in plan.get("set_keyword_bids", []):
        if crit_map is None:
            crit_map = existing_criteria(client, cid, plan["ad_group_id"])
        rn = find_rn(crit_map, kb["text"], kb.get("match"))
        if not rn:
            summary.append(f"  [! BID] '{kb['text']}' — NENALEZENO (přeskakuji)")
            continue
        op = client.get_type("AdGroupCriterionOperation")
        op.update.resource_name = rn
        op.update.cpc_bid_micros = int(kb["cpc_bid_micros"])
        op.update_mask.paths.append("cpc_bid_micros")
        ag_update_ops.append(op)
        summary.append(f"  [~ BID] {kb['text']} ({kb.get('match','?')}) → {int(kb['cpc_bid_micros'])/1e6:.1f} Kč")

    # 4d) Změna výchozího CPC bidu sestavy (manual CPC).
    # dict = jedna sestava (původní formát), list = víc sestav v jednom plánu.
    agb = plan.get("set_ad_group_bid")
    adgroup_bid_ops = []
    for it in (agb if isinstance(agb, list) else [agb]) if agb else []:
        op = client.get_type("AdGroupOperation")
        op.update.resource_name = res_ad_group(cid, it.get("ad_group_id") or plan["ad_group_id"])
        op.update.cpc_bid_micros = int(it["cpc_bid_micros"])
        op.update_mask.paths.append("cpc_bid_micros")
        adgroup_bid_ops.append(op)
        popis = f" ({it['_popis']})" if it.get("_popis") else ""
        summary.append(f"  [~ SESTAVA BID] {it.get('ad_group_id') or plan['ad_group_id']} "
                       f"→ {int(it['cpc_bid_micros'])/1e6:.1f} Kč{popis}")

    # 4e) Změna stavu sestavy (ENABLED/PAUSED) — např. spuštění nové sestavy
    ags = plan.get("set_ad_group_status")
    adgroup_status_ops = []
    if ags:
        items = ags if isinstance(ags, list) else [ags]
        for it in items:
            st = it["status"].upper()
            if st not in ("ENABLED", "PAUSED"):
                raise SystemExit(f"set_ad_group_status: neplatný stav {st!r} (jen ENABLED/PAUSED)")
            op = client.get_type("AdGroupOperation")
            op.update.resource_name = res_ad_group(cid, it.get("ad_group_id") or plan["ad_group_id"])
            op.update.status = getattr(client.enums.AdGroupStatusEnum, st)
            op.update_mask.paths.append("status")
            adgroup_status_ops.append(op)
            summary.append(f"  [~ SESTAVA STAV] {it.get('ad_group_id') or plan['ad_group_id']} → {st}")

    # 5) Změna denního rozpočtu (dict = jeden, list = víc kampaní najednou)
    budget_ops = []
    sb = plan.get("set_budget")
    if sb:
        for item in (sb if isinstance(sb, list) else [sb]):
            op = client.get_type("CampaignBudgetOperation")
            op.update.resource_name = f"customers/{cid}/campaignBudgets/{item['budget_id']}"
            op.update.amount_micros = int(item["amount_micros"])
            op.update_mask.paths.append("amount_micros")
            budget_ops.append(op)
            popis = f" ({item['_popis']})" if item.get("_popis") else ""
            summary.append(f"  [~ ROZPOČET] {item['budget_id']} → {int(item['amount_micros'])/1e6:.0f} Kč/den{popis}")

    # 6) Pozastavení kampaní
    campaign_ops = []
    for camp_id in plan.get("pause_campaign_ids", []):
        op = client.get_type("CampaignOperation")
        op.update.resource_name = res_campaign(cid, camp_id)
        op.update.status = client.enums.CampaignStatusEnum.PAUSED
        op.update_mask.paths.append("status")
        campaign_ops.append(op)
        summary.append(f"  [~ PAUSE KAMPAŇ] {camp_id}")

    # 6b) Změna bidovací strategie na Maximalizaci prokliků (TargetSpend)
    sbid = plan.get("set_bidding")
    if sbid and sbid.get("strategy") == "MAXIMIZE_CLICKS":
        op = client.get_type("CampaignOperation")
        op.update.resource_name = res_campaign(cid, sbid["campaign_id"])
        cap = sbid.get("cpc_bid_ceiling_micros")
        # API neumí masku na celé 'target_spend' (FIELD_HAS_SUBFIELDS) → nastav leaf pole.
        # Strop je povinný; vysoká hodnota = funkčně bez limitu (rozpočet je stejně tvrdá pojistka).
        op.update.target_spend.cpc_bid_ceiling_micros = int(cap or 25000000)
        op.update_mask.paths.append("target_spend.cpc_bid_ceiling_micros")
        campaign_ops.append(op)
        summary.append(f"  [~ STRATEGIE] Maximalizace prokliků, strop CPC {int(cap or 25000000)/1e6:.0f} Kč")

    # 6b-2) Cílový ROAS — u PMax / Max. hodnoty konverzí. Bez cíle nakupuje kampaň
    # konverze za jakoukoli cenu; cíl je jediná brzda. Zvyšovat po krocích (max ~+30 %),
    # skok zadusí objem. `set_target_roas`: {"campaign_id": "...", "target_roas": 1.2}
    troas = plan.get("set_target_roas")
    if troas:
        items = troas if isinstance(troas, list) else [troas]
        # Pole se liší podle strategie kampaně — zjisti ji z účtu, ať se netrefuje naslepo:
        #   TARGET_ROAS            → target_roas.target_roas
        #   MAXIMIZE_CONVERSION_VALUE → maximize_conversion_value.target_roas
        # Na jiných typech (Shopping/Manual CPC) API vrátí OPERATION_NOT_PERMITTED_FOR_CONTEXT.
        svc = client.get_service("GoogleAdsService")
        ids = ",".join(str(i["campaign_id"]) for i in items)
        strat = {}
        for batch in svc.search_stream(customer_id=cid, query=(
                "SELECT campaign.id, campaign.name, campaign.bidding_strategy_type "
                f"FROM campaign WHERE campaign.id IN ({ids})")):
            for r in batch.results:
                strat[str(r.campaign.id)] = (r.campaign.bidding_strategy_type.name, r.campaign.name)
        for item in items:
            cid_s = str(item["campaign_id"])
            st, nazev = strat.get(cid_s, (None, "?"))
            if st == "TARGET_ROAS":
                field = "target_roas.target_roas"
            elif st == "MAXIMIZE_CONVERSION_VALUE":
                field = "maximize_conversion_value.target_roas"
            else:
                summary.append(f"  [! tROAS] {nazev} ({cid_s}) má strategii {st} — cílový ROAS na ni nelze nastavit, PŘESKAKUJI")
                continue
            op = client.get_type("CampaignOperation")
            op.update.resource_name = res_campaign(cid, cid_s)
            root, leaf = field.split(".")
            setattr(getattr(op.update, root), leaf, float(item["target_roas"]))
            op.update_mask.paths.append(field)
            campaign_ops.append(op)
            summary.append(
                f"  [~ tROAS] {nazev} ({cid_s}, {st}) → cílový ROAS {float(item['target_roas']):.2f}"
                f" (= PNO {100/float(item['target_roas']):.0f} %)")

    # 6b-3) Cílová CPA — brzda pro strategii MAXIMIZE_CONVERSIONS (obdoba tROAS
    # pro strategie optimalizující na POČET konverzí). `set_target_cpa`:
    # {"campaign_id": "...", "target_cpa_micros": 190000000}
    tcpa = plan.get("set_target_cpa")
    if tcpa:
        items = tcpa if isinstance(tcpa, list) else [tcpa]
        svc2 = client.get_service("GoogleAdsService")
        ids2 = ",".join(str(i["campaign_id"]) for i in items)
        strat2 = {}
        for batch in svc2.search_stream(customer_id=cid, query=(
                "SELECT campaign.id, campaign.name, campaign.bidding_strategy_type "
                f"FROM campaign WHERE campaign.id IN ({ids2})")):
            for r in batch.results:
                strat2[str(r.campaign.id)] = (r.campaign.bidding_strategy_type.name, r.campaign.name)
        for item in items:
            cs = str(item["campaign_id"])
            st, nazev = strat2.get(cs, (None, "?"))
            if st == "MAXIMIZE_CONVERSIONS":
                field = "maximize_conversions.target_cpa_micros"
            elif st == "TARGET_CPA":
                field = "target_cpa.target_cpa_micros"
            else:
                summary.append(f"  [! tCPA] {nazev} ({cs}) má strategii {st} — cílovou CPA nastavit nelze, PŘESKAKUJI")
                continue
            op = client.get_type("CampaignOperation")
            op.update.resource_name = res_campaign(cid, cs)
            root, leaf = field.split(".")
            setattr(getattr(op.update, root), leaf, int(item["target_cpa_micros"]))
            op.update_mask.paths.append(field)
            campaign_ops.append(op)
            summary.append(f"  [~ tCPA] {nazev} ({cs}, {st}) → cílová CPA "
                           f"{int(item['target_cpa_micros'])/1e6:.0f} Kč")

    # 6b-4) Přepnutí na hodnotovou strategii (MAXIMIZE_CONVERSION_VALUE + tROAS).
    # `set_target_roas` výše umí jen změnit cíl u UŽ hodnotové strategie; tohle
    # přepíná i z MAXIMIZE_CONVERSIONS. Nastavením pole z oneof
    # `campaign_bidding_strategy` se strategie přepne sama.
    # POZOR: přepnutí resetuje fázi učení kampaně.
    # `set_bidding_maximize_value`: {"campaign_id": "...", "target_roas": 1.0}
    val_ops = plan.get("set_bidding_maximize_value")
    if val_ops:
        items = val_ops if isinstance(val_ops, list) else [val_ops]
        svc3 = client.get_service("GoogleAdsService")
        ids3 = ",".join(str(i["campaign_id"]) for i in items)
        strat3 = {}
        for batch in svc3.search_stream(customer_id=cid, query=(
                "SELECT campaign.id, campaign.name, campaign.bidding_strategy_type "
                f"FROM campaign WHERE campaign.id IN ({ids3})")):
            for r in batch.results:
                strat3[str(r.campaign.id)] = (r.campaign.bidding_strategy_type.name, r.campaign.name)
        for item in items:
            cs = str(item["campaign_id"])
            st, nazev = strat3.get(cs, (None, "?"))
            op = client.get_type("CampaignOperation")
            op.update.resource_name = res_campaign(cid, cs)
            op.update.maximize_conversion_value.target_roas = float(item["target_roas"])
            op.update_mask.paths.append("maximize_conversion_value.target_roas")
            campaign_ops.append(op)
            summary.append(
                f"  [~ STRATEGIE] {nazev} ({cs}) {st} → MAXIMIZE_CONVERSION_VALUE, "
                f"tROAS {float(item['target_roas']):.2f} (= PNO {100/float(item['target_roas']):.0f} %)")

    # 6b-5) Sejmutí cílového ROAS (strategie zůstane hodnotová, ale bez stropu).
    # Prázdná hodnota v update_mask pole vyčistí. Používej uvážlivě — kampaň bez
    # cíle nakupuje konverze za libovolnou cenu (reálně už to vedlo ke ztrátě).
    # `clear_target_roas`: [{"campaign_id": "..."}]
    for item in plan.get("clear_target_roas", []) or []:
        cs = str(item["campaign_id"])
        op = client.get_type("CampaignOperation")
        op.update.resource_name = res_campaign(cid, cs)
        op.update_mask.paths.append("maximize_conversion_value.target_roas")
        campaign_ops.append(op)
        summary.append(f"  [~ tROAS] kampaň {cs} → cíl SEJMUT (hodnotová strategie bez stropu)")

    # 6c) Typ geo cílení (PRESENCE = jen přítomní v oblasti, ne „zájem")
    gt = plan.get("set_geo_target_type")
    if gt:
        op = client.get_type("CampaignOperation")
        op.update.resource_name = res_campaign(cid, gt["campaign_id"])
        op.update.geo_target_type_setting.positive_geo_target_type = getattr(
            client.enums.PositiveGeoTargetTypeEnum, gt.get("positive", "PRESENCE"))
        op.update_mask.paths.append("geo_target_type_setting.positive_geo_target_type")
        campaign_ops.append(op)
        summary.append(f"  [~ GEO TYP] pozitivní = {gt.get('positive','PRESENCE')}")

    # 7) Geo: přidání lokalit / okruhu + odebrání stávajících kritérií
    geo_ops = []
    prox = plan.get("add_proximity")
    if prox:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = res_campaign(cid, prox["campaign_id"])
        op.create.proximity.radius = float(prox["radius"])
        op.create.proximity.radius_units = client.enums.ProximityRadiusUnitsEnum.KILOMETERS
        op.create.proximity.address.city_name = prox["city"]
        op.create.proximity.address.country_code = prox.get("country", "CZ")
        if prox.get("postal_code"):
            op.create.proximity.address.postal_code = prox["postal_code"]
        geo_ops.append(op)
        summary.append(f"  [+ OKRUH] {prox['radius']} km kolem {prox['city']} → kampaň {prox['campaign_id']}")
    geo = plan.get("add_campaign_geo")
    if geo:
        for gid in geo["geo_constant_ids"]:
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = res_campaign(cid, geo["campaign_id"])
            op.create.location.geo_target_constant = f"geoTargetConstants/{gid}"
            geo_ops.append(op)
            summary.append(f"  [+ GEO] {gid} → kampaň {geo['campaign_id']}")
    for rn in plan.get("remove_campaign_criteria", []):
        op = client.get_type("CampaignCriterionOperation")
        op.remove = rn
        geo_ops.append(op)
        summary.append(f"  [- KRITÉRIUM] {rn}")

    # 7b) Vyloučení URL z rozšiřování cílových URL u PMax.
    # Dělá se NEGATIVNÍM kritériem typu WEBPAGE na úrovni kampaně — viz
    # developers.google.com/google-ads/api/performance-max/create-campaign-criteria
    # („Negative WEBPAGE criteria can be used to exclude specific URLs from final
    # URL expansion"). Pole `campaign.url_expansion_opt_out` ve v24 už neexistuje.
    # `exclude_urls`: [{"campaign_id": "...", "contains": "/neco", "name": "popis"}]
    for ex in plan.get("exclude_urls", []) or []:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = res_campaign(cid, ex["campaign_id"])
        op.create.negative = True
        op.create.webpage.criterion_name = ex.get("name", ex["contains"])
        cond = client.get_type("WebpageConditionInfo")
        cond.operand = client.enums.WebpageConditionOperandEnum.URL
        cond.operator = client.enums.WebpageConditionOperatorEnum.CONTAINS
        cond.argument = ex["contains"]
        op.create.webpage.conditions.append(cond)
        geo_ops.append(op)
        summary.append(f"  [− URL] kampaň {ex['campaign_id']} nebude cílit na URL obsahující "
                       f"„{ex['contains']}“")

    # 7) Stav reklam (ENABLED/PAUSED) — např. pauza prohrané varianty A/B testu
    # `set_ad_status`: [{"ad_group_id": "...", "ad_id": "...", "status": "PAUSED"}]
    ad_status_ops = []
    for it in plan.get("set_ad_status", []) or []:
        st = it["status"].upper()
        if st not in ("ENABLED", "PAUSED"):
            raise SystemExit(f"set_ad_status: neplatný stav {st!r} (jen ENABLED/PAUSED)")
        op = client.get_type("AdGroupAdOperation")
        op.update.resource_name = f"customers/{cid}/adGroupAds/{it['ad_group_id']}~{it['ad_id']}"
        op.update.status = getattr(client.enums.AdGroupAdStatusEnum, st)
        op.update_mask.paths.append("status")
        ad_status_ops.append(op)
        summary.append(f"  [~ REKLAMA STAV] {it['ad_id']} → {st}")

    # 8) Úprava textů EXISTUJÍCÍ RSA (AdService.mutate_ads + update mask) — reklama
    # si ponechá ID. Posílá se VŽDY kompletní sada nadpisů/popisů (nahrazuje původní).
    # Ověřeno: developers.google.com/google-ads/api/docs/ads/mutate-ads
    # `update_rsa`: [{"ad_id": "...", "headlines": [...], "descriptions": [...]}]
    rsa_update_ops = []
    for it in plan.get("update_rsa", []) or []:
        hs, ds = it["headlines"], it["descriptions"]
        errs = []
        if not 3 <= len(hs) <= 15: errs.append(f"nadpisů 3–15, je {len(hs)}")
        if not 2 <= len(ds) <= 4: errs.append(f"popisů 2–4, je {len(ds)}")
        errs += [f"nadpis {len(h)}>30: {h!r}" for h in hs if len(h) > 30]
        errs += [f"popis {len(d)}>90: {d!r}" for d in ds if len(d) > 90]
        if errs:
            raise SystemExit(f"update_rsa {it['ad_id']}: " + "; ".join(errs))
        from lib.policy import check_ad_texts
        check_ad_texts(hs, context=f"nadpisy RSA {it['ad_id']}")
        check_ad_texts(ds, context=f"popisky RSA {it['ad_id']}")
        op = client.get_type("AdOperation")
        op.update.resource_name = f"customers/{cid}/ads/{it['ad_id']}"
        for h in hs:
            a = client.get_type("AdTextAsset"); a.text = h
            op.update.responsive_search_ad.headlines.append(a)
        for d in ds:
            a = client.get_type("AdTextAsset"); a.text = d
            op.update.responsive_search_ad.descriptions.append(a)
        op.update_mask.paths.extend(["responsive_search_ad.headlines",
                                     "responsive_search_ad.descriptions"])
        rsa_update_ops.append(op)
        summary.append(f"  [~ RSA TEXTY] {it['ad_id']}: {len(hs)} nadpisů, {len(ds)} popisů")
        for h in hs: summary.append(f"        H {len(h):2}/30  {h}")
        for d in ds: summary.append(f"        D {len(d):2}/90  {d}")

    # 9) Strukturované úryvky na úrovni kampaně (asset + propojení s kampaní)
    # Hlavička musí být z předdefinovaného seznamu v jazyce reklam — česky „Služby"
    # (developers.google.com/google-ads/api/data/structured-snippet-headers).
    # `add_structured_snippets`: [{"campaign_id": "...", "header": "Služby", "values": [...]}]
    snippet_specs = []
    for it in plan.get("add_structured_snippets", []) or []:
        vals = it["values"]
        if not 3 <= len(vals) <= 10:
            raise SystemExit(f"úryvek: hodnot musí být 3–10, je {len(vals)}")
        long_ = [v for v in vals if len(v) > 25]
        if long_:
            raise SystemExit(f"úryvek: hodnoty nad 25 znaků: {long_}")
        snippet_specs.append(it)
        summary.append(f"  [+ ÚRYVEK] kampaň {it['campaign_id']} — {it['header']}: {', '.join(vals)}")

    # 10) Doplnění popisků k EXISTUJÍCÍM sitelinkům (asset jde upravit na místě —
    # ověřeno v dokumentaci: AssetService podporuje update u sitelinků i popisků,
    # developers.google.com/google-ads/api/docs/assets/working-with-assets).
    # Úpravou se neztratí historie podkladu. Limit: popis 35 znaků.
    # `update_sitelinks`: [{"asset_id": "...", "description1": "...", "description2": "..."}]
    sitelink_ops = []
    for it in plan.get("update_sitelinks", []) or []:
        d1, d2 = it["description1"], it["description2"]
        dlouhe = [d for d in (d1, d2) if len(d) > 35]
        if dlouhe:
            raise SystemExit(f"sitelink {it['asset_id']}: popis nad 35 znaků: {dlouhe}")
        from lib.policy import check_ad_texts
        check_ad_texts([d1, d2], context=f"popisky sitelinku {it['asset_id']}")
        op = client.get_type("AssetOperation")
        op.update.resource_name = f"customers/{cid}/assets/{it['asset_id']}"
        op.update.sitelink_asset.description1 = d1
        op.update.sitelink_asset.description2 = d2
        op.update_mask.paths.extend(["sitelink_asset.description1", "sitelink_asset.description2"])
        sitelink_ops.append(op)
        summary.append(f"  [~ SITELINK] {it.get('_popis', it['asset_id'])}")
        summary.append(f"        {len(d1):2}/35  {d1}")
        summary.append(f"        {len(d2):2}/35  {d2}")

    # 11) Nové popisky (callouts) — vytvoří asset a připojí ho ke kampaním. Limit: 25 znaků.
    # `add_callouts`: [{"text": "..."}], cílové kampaně z `callout_campaign_ids` nebo `campaign_id`
    callout_specs = []
    for it in plan.get("add_callouts", []) or []:
        t = it["text"]
        if len(t) > 25:
            raise SystemExit(f"popisek nad 25 znaků ({len(t)}): {t!r}")
        from lib.policy import check_ad_texts
        check_ad_texts([t], context="popisky (callouts)")
        callout_specs.append(t)
        summary.append(f"  [+ POPISEK] {len(t):2}/25  {t}")

    # --- Výpis plánu ---
    print(f"PLÁN ZMĚN pro účet {args.customer_id} (kampaň {plan.get('campaign_id','—')}, sestava {plan.get('ad_group_id','—')}):\n")
    print("\n".join(summary) if summary else "  (žádné operace)")
    print(f"\nSouhrn: {len(neg_ops)} negativ, {len(add_ops)} nových KW, "
          f"{len(ag_update_ops)} pozastavení, {len(ag_remove_ops)} odebrání.")

    if not args.apply and not args.validate:
        print("\n🟡 DRY-RUN — nic nezapsáno. Pro reálné provedení přidej --apply")
        print("   Tip: `--validate` nechá plán zkontrolovat přímo Googlem, aniž by cokoli vzniklo.")
        return

    # `validate_only` je vlastnost Google Ads API: požadavek projde celou
    # validací na jejich straně a vrátí přesnou chybu, ale NIC nezapíše.
    # Náš dry-run jen tiskne, co bychom poslali — tohle se ptá Googlu.
    VALIDATE = args.validate and not args.apply
    if VALIDATE:
        print("\n🔍 --validate: nechávám plán zkontrolovat Googlem (nic se nezapíše)...")
    else:
        # --- Reálný zápis (partial_failure: vadný řádek neshodí celou dávku) ---
        print("\n🔴 --apply: provádím změny...")
    if budget_ops:
        req = client.get_type("MutateCampaignBudgetsRequest")
        req.customer_id = cid
        req.operations = budget_ops
        req.validate_only = VALIDATE
        client.get_service("CampaignBudgetService").mutate_campaign_budgets(request=req)
        akce = "ověřeno" if VALIDATE else "změněno"
        print(f"  ✓ rozpočty: {len(budget_ops)} {akce}")
    if campaign_ops:
        req = client.get_type("MutateCampaignsRequest")
        req.customer_id = cid
        req.operations = campaign_ops
        req.validate_only = VALIDATE
        client.get_service("CampaignService").mutate_campaigns(request=req)
        print(f"  ✓ {len(campaign_ops)} úprav kampaně (pauza/strategie) "
              + ("ověřeno" if VALIDATE else "provedeno"))
    cc_ops = neg_ops + geo_ops
    if cc_ops:
        req = client.get_type("MutateCampaignCriteriaRequest")
        req.customer_id = cid
        req.operations = cc_ops
        # partial_failure a validate_only nejdou dohromady — při ověřování
        # chceme naopak vidět každou chybu, ne aby se vadné řádky tiše přeskočily.
        req.partial_failure = not VALIDATE
        req.validate_only = VALIDATE
        resp = client.get_service("CampaignCriterionService").mutate_campaign_criteria(request=req)
        ok = sum(1 for r in resp.results if r.resource_name)
        if VALIDATE:
            print(f"  ✓ kritéria kampaně (negativa+geo): {len(cc_ops)} operací ověřeno")
        else:
            print(f"  ✓ kritéria kampaně (negativa+geo): {ok}/{len(cc_ops)} OK"
                  + (f" | ⚠️ {resp.partial_failure_error.message}" if resp.partial_failure_error.code else ""))
    ag_meta_ops = adgroup_bid_ops + adgroup_status_ops
    if ag_meta_ops:
        req = client.get_type("MutateAdGroupsRequest")
        req.customer_id = cid
        req.operations = ag_meta_ops
        req.validate_only = VALIDATE
        client.get_service("AdGroupService").mutate_ad_groups(request=req)
        akce = "ověřeno" if VALIDATE else "provedeno"
        print(f"  ✓ úpravy sestav (bid/stav): {len(ag_meta_ops)} {akce}")
    ag_ops = add_ops + ag_update_ops + ag_remove_ops
    if ag_ops:
        req = client.get_type("MutateAdGroupCriteriaRequest")
        req.customer_id = cid
        req.operations = ag_ops
        req.partial_failure = not VALIDATE
        req.validate_only = VALIDATE
        resp = client.get_service("AdGroupCriterionService").mutate_ad_group_criteria(request=req)
        ok = sum(1 for r in resp.results if r.resource_name)
        if VALIDATE:
            print(f"  ✓ sestava: {len(ag_ops)} operací ověřeno")
        else:
            print(f"  ✓ sestava: {ok}/{len(ag_ops)} operací OK"
                  + (f" | ⚠️ {resp.partial_failure_error.message}" if resp.partial_failure_error.code else ""))
    if ad_status_ops:
        req = client.get_type("MutateAdGroupAdsRequest")
        req.customer_id = cid
        req.operations = ad_status_ops
        req.validate_only = VALIDATE
        client.get_service("AdGroupAdService").mutate_ad_group_ads(request=req)
        print(f"  ✓ stav reklam: {len(ad_status_ops)} " + ("ověřeno" if VALIDATE else "provedeno"))
    if rsa_update_ops:
        req = client.get_type("MutateAdsRequest")
        req.customer_id = cid
        req.operations = rsa_update_ops
        req.validate_only = VALIDATE
        client.get_service("AdService").mutate_ads(request=req)
        print(f"  ✓ texty RSA: {len(rsa_update_ops)} " + ("ověřeno" if VALIDATE else "upraveno (jde znovu do schválení Googlem)"))
    for it in snippet_specs:
        aop = client.get_type("AssetOperation")
        aop.create.structured_snippet_asset.header = it["header"]
        aop.create.structured_snippet_asset.values.extend(it["values"])
        areq = client.get_type("MutateAssetsRequest")
        areq.customer_id = cid
        areq.operations.append(aop)
        areq.validate_only = VALIDATE
        ares = client.get_service("AssetService").mutate_assets(request=areq)
        if VALIDATE:
            # Propojení s kampaní nejde ověřit bez skutečného assetu — ověřen jen asset.
            print(f"  ✓ úryvek pro kampaň {it['campaign_id']}: asset ověřen (propojení se ověří až při --apply)")
            continue
        asset_rn = ares.results[0].resource_name
        lop = client.get_type("CampaignAssetOperation")
        lop.create.campaign = res_campaign(cid, it["campaign_id"])
        lop.create.asset = asset_rn
        lop.create.field_type = client.enums.AssetFieldTypeEnum.STRUCTURED_SNIPPET
        client.get_service("CampaignAssetService").mutate_campaign_assets(customer_id=cid, operations=[lop])
        print(f"  ✓ úryvek {asset_rn} připojen ke kampani {it['campaign_id']}")
    if sitelink_ops:
        req = client.get_type("MutateAssetsRequest")
        req.customer_id = cid
        req.operations = sitelink_ops
        req.validate_only = VALIDATE
        client.get_service("AssetService").mutate_assets(request=req)
        print(f"  ✓ popisky sitelinků: {len(sitelink_ops)} "
              + ("ověřeno" if VALIDATE else "doplněno (jde znovu do schválení Googlem)"))
    if callout_specs:
        camp_ids = plan.get("callout_campaign_ids") or ([plan["campaign_id"]] if plan.get("campaign_id") else [])
        if not camp_ids:
            raise SystemExit("add_callouts: chybí callout_campaign_ids ani campaign_id")
        for t in callout_specs:
            aop = client.get_type("AssetOperation")
            aop.create.callout_asset.callout_text = t
            areq = client.get_type("MutateAssetsRequest")
            areq.customer_id = cid
            areq.operations.append(aop)
            areq.validate_only = VALIDATE
            ares = client.get_service("AssetService").mutate_assets(request=areq)
            if VALIDATE:
                print(f"  ✓ popisek ověřen: {t}")
                continue
            asset_rn = ares.results[0].resource_name
            for camp_id in camp_ids:
                lop = client.get_type("CampaignAssetOperation")
                lop.create.campaign = res_campaign(cid, camp_id)
                lop.create.asset = asset_rn
                lop.create.field_type = client.enums.AssetFieldTypeEnum.CALLOUT
                client.get_service("CampaignAssetService").mutate_campaign_assets(
                    customer_id=cid, operations=[lop])
            print(f"  ✓ popisek „{t}“ připojen ke {len(camp_ids)} kampaním")
    print("\n✅ Plán je podle Googlu v pořádku — nic nezapsáno." if VALIDATE else "\n✅ Hotovo.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Založení nové responzivní reklamy (RSA) do sestavy podle plánu (JSON).

Typické použití: A/B test — přidat 2. RSA vedle stávající (kontrola) a porovnat.

BEZPEČNOST:
- Default DRY-RUN: jen vypíše, co by založil + zkontroluje délky. NIC nezapíše.
- Reálný zápis jen s --apply.
- Validace: nadpis ≤ 30 znaků, popis ≤ 90 znaků, 3–15 nadpisů, 2–4 popisy.
  Při překročení limitů se NEzapíše ani s --apply (ochrana proti vadné reklamě).

Plán (JSON):
{
  "ad_group_id": "0000000000",
  "final_url": "https://www.example.cz/",
  "path1": "",            # volitelně (zobrazená cesta /path1/path2), max 15 znaků
  "path2": "",
  "headlines":   ["...", ...],   # 3–15, každý ≤ 30 znaků
  "descriptions":["...", ...]    # 2–4, každý ≤ 90 znaků
}

Plán může obsahovat i víc reklam najednou: {"ads": [ {…jako výše…}, … ]}.

Použití:
  python scripts/google_ads/create_rsa.py <customer_id> <plan.json>                    # náhled
  python scripts/google_ads/create_rsa.py <customer_id> <plan.json> --validate         # kontrola Googlem
  python scripts/google_ads/create_rsa.py <customer_id> <plan.json> --apply --paused   # zápis, pozastavené
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import build_client, normalize_cid  # noqa: E402

H_MAX, D_MAX, PATH_MAX = 30, 90, 15


def validate(plan: dict) -> list[str]:
    errs = []
    h = plan.get("headlines", [])
    d = plan.get("descriptions", [])
    if not (3 <= len(h) <= 15):
        errs.append(f"nadpisů musí být 3–15 (je {len(h)})")
    if not (2 <= len(d) <= 4):
        errs.append(f"popisů musí být 2–4 (je {len(d)})")
    for t in h:
        if len(t) > H_MAX:
            errs.append(f"nadpis {len(t)}>{H_MAX}: '{t}'")
    for t in d:
        if len(t) > D_MAX:
            errs.append(f"popis {len(t)}>{D_MAX}: '{t}'")
    for k in ("path1", "path2"):
        if len(plan.get(k, "") or "") > PATH_MAX:
            errs.append(f"{k} > {PATH_MAX} znaků")
    # POLICY (telefonní čísla apod.) — SystemExit při nálezu
    from lib.policy import check_ad_texts
    check_ad_texts(h, context="nadpisy RSA")
    check_ad_texts(d, context="popisky RSA")
    return errs


def main() -> None:
    p = argparse.ArgumentParser(description="Založení nové RSA do sestavy")
    p.add_argument("customer_id")
    p.add_argument("plan", help="Cesta k plán JSON")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ založí (jinak dry-run)")
    p.add_argument("--validate", action="store_true",
                   help="Nechá plán zkontrolovat Googlem (validate_only), nic nezaloží")
    p.add_argument("--paused", action="store_true",
                   help="Založí reklamu jako PAUSED (texty ke kontrole před spuštěním)")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    # Plán je buď jedna reklama (původní formát), nebo {"ads": [ ... ]}.
    plans = raw["ads"] if "ads" in raw else [raw]

    any_err = False
    for plan in plans:
        print(f"PLÁN: nová RSA → sestava {plan['ad_group_id']} {plan.get('_sestava','')} (účet {args.customer_id})")
        print(f"  URL: {plan['final_url']}  cesta: /{plan.get('path1','')}/{plan.get('path2','')}")
        print(f"  NADPISY ({len(plan.get('headlines', []))}):")
        for t in plan.get("headlines", []):
            flag = "  ⚠️ PŘES LIMIT" if len(t) > H_MAX else ""
            print(f"    [{len(t):2}/{H_MAX}] {t}{flag}")
        print(f"  POPISY ({len(plan.get('descriptions', []))}):")
        for t in plan.get("descriptions", []):
            flag = "  ⚠️ PŘES LIMIT" if len(t) > D_MAX else ""
            print(f"    [{len(t):2}/{D_MAX}] {t}{flag}")
        errs = validate(plan)
        if errs:
            any_err = True
            print("  🔴 CHYBY:")
            for e in errs:
                print(f"    - {e}")
        print()
    if any_err:
        raise SystemExit("🔴 Plán má chyby — nezapíšu ani s --apply.")

    if not args.apply and not args.validate:
        print("🟡 DRY-RUN — nic nezaloženo. Dál: --validate (kontrola Googlem) nebo --apply.")
        return

    client = build_client()
    status = (client.enums.AdGroupAdStatusEnum.PAUSED if args.paused
              else client.enums.AdGroupAdStatusEnum.ENABLED)
    vo = args.validate and not args.apply
    print("🔍 --validate: ptám se Googlu, nic se nezaloží..." if vo
          else f"🔴 --apply: zakládám {len(plans)} RSA ({'PAUSED' if args.paused else 'ENABLED'})...")

    for plan in plans:
        op = client.get_type("AdGroupAdOperation")
        aga = op.create
        aga.ad_group = f"customers/{cid}/adGroups/{plan['ad_group_id']}"
        aga.status = status
        ad = aga.ad
        ad.final_urls.append(plan["final_url"])
        rsa = ad.responsive_search_ad
        for h in plan["headlines"]:
            a = client.get_type("AdTextAsset"); a.text = h; rsa.headlines.append(a)
        for d in plan["descriptions"]:
            a = client.get_type("AdTextAsset"); a.text = d; rsa.descriptions.append(a)
        if plan.get("path1"):
            rsa.path1 = plan["path1"]
        if plan.get("path2"):
            rsa.path2 = plan["path2"]
        req = client.get_type("MutateAdGroupAdsRequest")
        req.customer_id = cid
        req.operations.append(op)
        req.validate_only = vo
        # Sériově, jedna reklama = jeden požadavek; při chybě se zastaví a vypíše, co už vzniklo.
        resp = client.get_service("AdGroupAdService").mutate_ad_group_ads(request=req)
        if vo:
            print(f"  ✓ ověřeno: sestava {plan['ad_group_id']} {plan.get('_sestava','')}")
        else:
            print(f"  ✓ JIZ_VYTVORENO {resp.results[0].resource_name} {plan.get('_sestava','')}")

    if vo:
        print("\n✅ VALIDATE: Google plán přijal. Nic nezaloženo.")
    else:
        print("\n✅ Hotovo. Reklamy jdou do schvalování Googlem (běžně hodiny až 1 den).")


if __name__ == "__main__":
    main()

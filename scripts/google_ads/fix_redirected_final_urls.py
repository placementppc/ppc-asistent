#!/usr/bin/env python3
"""Oprava cílových adres reklam, které web přesměrovává a přitom zahazuje parametry (gclid).

Pro každou aktivní responzivní reklamu v zadaných kampaních:
  1) projde přesměrování staré adresy a zjistí novou cestu,
  2) složí novou adresu = nová cesta + původní parametry (např. utm_*),
  3) ověří, že nová adresa vrací 200 bez dalšího přesměrování a že `gclid` zůstane,
  4) přepíše `final_urls` reklamy na místě (ID reklamy i statistiky zůstávají).

BEZPEČNOST: výchozí běh je náhled (nic nezapíše). `--validate` nechá změny ověřit Googlem,
`--apply` je provede. Adresy se nevypisují (ať se do výstupu nedostanou adresy webu klienta) — jen počty a ID reklam. Mapa stará → nová
adresa pro případný návrat se ukládá do tajné složky klienta.

Použití:
  GOOGLE_ADS_PROFILE=druhy python scripts/google_ads/fix_redirected_final_urls.py <customer_id> \
      --client <klient> --campaigns 111,222 [--validate | --apply]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from client import build_client, normalize_cid  # noqa: E402
import sanitize as san  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0"}
TEST = "gclid=TESTgclid123"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def walk(url: str) -> tuple[object, int, str]:
    """Projde přesměrování ručně. Vrací (konečný HTTP kód, počet přesměrování, konečná adresa)."""
    cur, hops = url, 0
    while hops < 6:
        try:
            r = _opener.open(urllib.request.Request(cur, headers=UA), timeout=20)
            return r.status, hops, cur
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                cur = urllib.parse.urljoin(cur, loc)
                hops += 1
                continue
            return e.code, hops, cur
        except Exception:
            return "chyba", hops, cur
    return "smyčka", hops, cur


def fixed_url(old: str) -> tuple[str | None, str]:
    """Nová adresa pro starou, nebo (None, důvod)."""
    with_test = old + ("&" if "?" in old else "?") + TEST
    code, hops, end = walk(with_test)
    if hops == 0 and code == 200 and TEST in end:
        return None, "v pořádku (bez přesměrování)"
    o = urllib.parse.urlsplit(old)
    code, hops, end = walk(urllib.parse.urlunsplit((o.scheme, o.netloc, o.path, "", "")))
    if code != 200:
        return None, f"cíl vrací {code}"
    e = urllib.parse.urlsplit(end)
    if e.path.strip("/") == "":
        return None, "přesměrování vede na úvodní stránku"
    new = urllib.parse.urlunsplit((e.scheme, e.netloc, e.path, o.query, ""))
    code, hops, end2 = walk(new + ("&" if "?" in new else "?") + TEST)
    if not (code == 200 and hops == 0 and TEST in end2):
        return None, "nová adresa neprošla kontrolou (přesměrování nebo ztráta gclid)"
    return new, "opravit"


def main() -> None:
    p = argparse.ArgumentParser(description="Oprava přesměrovaných cílových adres reklam")
    p.add_argument("customer_id")
    p.add_argument("--client", required=True, help="Slug klienta (kvůli uložení mapy pro návrat)")
    p.add_argument("--campaigns", required=True, help="ID kampaní oddělená čárkou")
    p.add_argument("--apply", action="store_true", help="REÁLNĚ provede změny")
    p.add_argument("--validate", action="store_true", help="Ověří změny Googlem (validate_only), nic nezapíše")
    args = p.parse_args()

    cid = normalize_cid(args.customer_id)
    client = build_client()
    ga = client.get_service("GoogleAdsService")
    ids = ",".join(str(int(x)) for x in args.campaigns.split(","))
    rows = list(ga.search(customer_id=cid, query=(
        "SELECT campaign.id, ad_group.id, ad_group_ad.ad.id, ad_group_ad.ad.type, "
        "ad_group_ad.ad.final_urls, ad_group_ad.ad.final_mobile_urls "
        f"FROM ad_group_ad WHERE campaign.id IN ({ids}) AND ad_group_ad.status = 'ENABLED' "
        "AND ad_group.status = 'ENABLED'")))

    cache: dict[str, tuple[str | None, str]] = {}
    ops, mapping = [], []
    stats = collections.defaultdict(collections.Counter)
    for r in rows:
        ad = r.ad_group_ad.ad
        camp = str(r.campaign.id)
        if ad.type_.name != "RESPONSIVE_SEARCH_AD":
            stats[camp][f"přeskočeno: typ {ad.type_.name} nejde upravit na místě"] += 1
            continue
        new_urls, changed, reason = [], False, "v pořádku (bez přesměrování)"
        for u in ad.final_urls:
            if u not in cache:
                cache[u] = fixed_url(u)
                time.sleep(0.3)
            nu, why = cache[u]
            if nu:
                new_urls.append(nu); changed = True; reason = "opravit"
            else:
                new_urls.append(u)
                if why != "v pořádku (bez přesměrování)":
                    reason = why
        if ad.final_mobile_urls:
            stats[camp]["pozor: reklama má i mobilní adresy (neměněny)"] += 1
        stats[camp][reason if not changed else "opravit"] += 1
        if not changed:
            continue
        op = client.get_type("AdOperation")
        op.update.resource_name = client.get_service("AdService").ad_path(cid, ad.id)
        op.update.final_urls.extend(new_urls)
        op.update_mask.paths.append("final_urls")
        ops.append(op)
        mapping.append({"campaign_id": camp, "ad_group_id": str(r.ad_group.id), "ad_id": str(ad.id),
                        "old": list(ad.final_urls), "new": new_urls})

    print(f"Reklam načteno: {len(rows)} | různých adres: {len(cache)} | k opravě: {len(ops)}")
    for camp, c in stats.items():
        print(f"  kampaň {camp}: {dict(c)}")
    if not ops:
        print("Není co měnit.")
        return
    if not args.apply and not args.validate:
        print("\nNÁHLED — nic nezapsáno. `--validate` ověří změny Googlem, `--apply` je provede.")
        return

    san.SECRET_DIR.mkdir(parents=True, exist_ok=True)
    back = san.SECRET_DIR / f"{args.client}-final-urls-{date.today().isoformat()}.json"
    if args.apply:
        back.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
        print("Mapa stará → nová adresa uložena do tajné složky klienta (pro návrat).")

    svc = client.get_service("AdService")
    done = 0
    for i in range(0, len(ops), 50):          # malé dávky, sériově
        req = client.get_type("MutateAdsRequest")
        req.customer_id = cid
        req.operations.extend(ops[i:i + 50])
        req.validate_only = bool(args.validate and not args.apply)
        svc.mutate_ads(request=req)
        done += len(ops[i:i + 50])
        time.sleep(1)
    print(f"{'✅ Provedeno' if args.apply else '🔍 Ověřeno Googlem (nic nezapsáno)'}: {done} reklam.")


if __name__ == "__main__":
    main()

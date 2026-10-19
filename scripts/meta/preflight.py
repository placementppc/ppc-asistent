#!/usr/bin/env python3
"""Meta Ads — preflight kontrola PŘED stavbou kampaně (READ-ONLY).

Proč existuje: Meta vrací vždy jen JEDNU chybu. Když se kampaň staví naslepo,
zjišťuješ chybějící práva po jednom a mezi každým zjištěním posíláš člověka do
Business Settings. Tenhle skript projde všechny předpoklady najednou a vypíše
kompletní seznam toho, co chybí.

Typický případ: stavba katalogové kampaně narazí postupně na několik různých
překážek (práva, katalog, stránka, pixel) a každá se zjistí zvlášť.

Použití:
  python scripts/meta/preflight.py <ad_account_id> [--catalog <id>] [--page <id>] [--token-env META_API_TOKEN]

Nic nezapisuje. Výstup = tabulka OK / CHYBÍ + co s tím.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402

API_VERSION = "v21.0"


def get(path: str, params: dict, token: str) -> tuple[int, dict]:
    q = urllib.parse.urlencode({**params, "access_token": token})
    url = f"https://graph.facebook.com/{API_VERSION}/{path}?{q}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def row(ok: bool | None, label: str, detail: str = "") -> None:
    mark = {True: "  OK  ", False: "CHYBÍ ", None: "  ?   "}[ok]
    print(f"[{mark}] {label:<42} {detail}")


def main() -> None:
    p = argparse.ArgumentParser(description="Meta preflight (read-only)")
    p.add_argument("ad_account_id", help="číselné ID bez act_")
    p.add_argument("--catalog", help="ID katalogu (u katalogových kampaní)")
    p.add_argument("--page", help="ID stránky, ze které poběží reklamy")
    p.add_argument("--token-env", default="META_API_TOKEN")
    args = p.parse_args()

    _id = str(args.ad_account_id).strip().lower()
    _id = _id[4:] if _id.startswith("act_") else _id
    if not _id.isdigit():
        raise SystemExit("ID účtu musí být číslo (bez act_).")
    acct = f"act_{_id}"
    # NDA pojistka jako u ostatních Meta čtecích skriptů (fetch.py).
    from lib.nda import guard
    guard(acct, "read-raw")

    token = require(args.token_env)[args.token_env]
    print(f"\n=== PREFLIGHT {acct} (token {args.token_env}) ===\n")

    # 1) token: aplikace, scopes, system user
    _, dbg = get("debug_token", {"input_token": token}, token)
    d = dbg.get("data", {})
    scopes = d.get("scopes", [])
    row(bool(d.get("app_id")), "token platný", f"app: {d.get('application')} (id {d.get('app_id')})")
    for need in ("ads_management", "business_management"):
        row(need in scopes, f"scope {need}")
    if args.catalog:
        row("catalog_management" in scopes, "scope catalog_management")
    _, me = get("me", {"fields": "id,name"}, token)
    row(bool(me.get("id")), "system user", f"{me.get('name')} ({me.get('id')})")
    print("  ⚠️  Režim aplikace (Vývoj/Live) z API zjistit NELZE. Aplikace v režimu vývoje")
    print("      NESMÍ vytvořit obsah reklamy (subcode 1885183) — pozná se až při zápisu.\n")

    # 2) ad účet
    st, acc = get(acct, {"fields": "name,currency,account_status,business"}, token)
    biz = (acc.get("business") or {})
    row(st == 200, "čtení ad účtu", f"{acc.get('name')} | {acc.get('currency')} | status {acc.get('account_status')}")
    row(bool(biz.get("id")), "business ad účtu", f"{biz.get('name')} ({biz.get('id')})")

    # 3) katalog
    if args.catalog:
        st, cat = get(args.catalog, {"fields": "name,product_count,business"}, token)
        cbiz = (cat.get("business") or {})
        row(st == 200, "čtení katalogu", f"{cat.get('name')} | {cat.get('product_count')} produktů")
        row(cbiz.get("id") == biz.get("id"), "katalog a ad účet ve stejném businessu",
            f"katalog: {cbiz.get('name')}")
        st, ps = get(f"{args.catalog}/product_sets", {"fields": "id,name,product_count", "limit": 25}, token)
        sets = ps.get("data", [])
        row(st == 200, "čtení product setů", f"{len(sets)} setů")
        for s in sets:
            print(f"           • {s['id']}  {s['name']}  ({s.get('product_count')} produktů)")
        # zdraví feedu
        st, prods = get(f"{args.catalog}/products",
                        {"fields": "availability,visibility,url", "limit": 100}, token)
        items = prods.get("data", [])
        if items:
            bad = [i for i in items if i.get("availability") != "in stock"
                   or i.get("visibility") != "published"]
            doms = {str(i.get("url", "")).split("/")[2] for i in items if "//" in str(i.get("url", ""))}
            row(not bad, "feed: dostupnost + viditelnost",
                f"{len(items) - len(bad)}/{len(items)} in stock & published")
            row(len(doms) == 1, "feed: jednotná doména", ", ".join(sorted(doms)) or "?")

    # 4) stránka — právo Ads pro system usera je nejčastější zádrhel
    if args.page:
        st, pg = get(args.page, {"fields": "name"}, token)
        row(st == 200, "čtení stránky", pg.get("name") or f"HTTP {st} (nemusí vadit)")
        print("  ⚠️  Právo 'Ads' system usera na stránce nejde spolehlivě přečíst.")
        print("      Ověřuje se až zápisem (chyba #10, subcode 1341012).\n")

    # 5) pixely
    st, px = get(f"{acct}/adspixels", {"fields": "id,name,last_fired_time"}, token)
    pix = px.get("data", [])
    row(bool(pix), "pixely účtu", f"{len(pix)}")
    for x in pix:
        print(f"           • {x['id']}  {x.get('name')}  poslední event: {x.get('last_fired_time')}")

    print("""
=== CO Z API OVĚŘIT NEJDE (a projeví se až při zápisu) ===
  1. Režim aplikace Vývoj/Live  → subcode 1885183 při tvorbě kreativy
  2. Právo 'Ads' na stránce     → subcode 1341012 (#10)
  3. Přístup účtu k IG profilu  → subcode 1815199
  4. Povolení účtu pro Ads MCP  → 'This ad account is not enabled for the Ads MCP'
  → Když stavíš přes API poprvé v novém účtu, počítej s tím a ověř je NAJEDNOU
    (zkusit vytvořit kreativu jako první krok, ne jako poslední).
""")


if __name__ == "__main__":
    main()

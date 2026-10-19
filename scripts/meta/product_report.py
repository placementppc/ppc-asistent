#!/usr/bin/env python3
"""Read-only produktový report: účet → katalogová reklama → obsahová reklama (bannery/videa).

Rozdíl proti naivnímu `breakdowns=product_id`: ten vrací řádky i pro NEkatalogové reklamy —
tam produkty pocházejí z pixelu (co si člověk po prokliku prohlédl/koupil), ne z reklamy.
Proto reklamy klasifikujeme podle `creative{product_set_id}` a segmenty držíme oddělené.

Použití:
  python scripts/meta/product_report.py --account act_XXX --out data/reports/nazev
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import MetaClient, normalize_account_id  # noqa: E402

# Některé účty plní jen onsite_web_*; omni_purchase/purchase pak vracejí v breakdownu nuly.
# Bereme první typ, který je v datech reálně naplněný.
PURCH_TYPES = ("onsite_web_purchase", "omni_purchase", "purchase",
               "offsite_conversion.fb_pixel_purchase")
ATC_TYPES = ("onsite_web_add_to_cart", "omni_add_to_cart", "add_to_cart")

INS_FIELDS = "ad_id,ad_name,campaign_name,spend,impressions,inline_link_clicks,actions,action_values"


def pick(rows, types):
    """Vrátí hodnotu prvního action_type z `types`, který je v datech přítomný a nenulový."""
    vals = {r.get("action_type"): float(r.get("value") or 0) for r in rows or []}
    for t in types:
        if vals.get(t):
            return vals[t]
    return 0.0


def window(days: int, offset: int = 0):
    end = date.today() - timedelta(days=1 + offset)
    return end - timedelta(days=days - 1), end


def fetch(c, acct, since, until, breakdown=True, level="ad", chunk_days=7):
    """Insights za období. Delší okna krájí po `chunk_days` — 30 dní × product_id breakdown
    Meta synchronně nevrátí (code=2/subcode=1504038 „zkuste kratší období").
    Konverze Meta atribuuje k datu imprese/prokliku, takže součet dílů = celek."""
    kw = {"breakdowns": "product_id"} if breakdown else {}
    out, s = [], since
    while s <= until:
        e = min(s + timedelta(days=chunk_days - 1), until)
        out += c.get_all(f"{acct}/insights", fields=INS_FIELDS, level=level,
                         time_range=json.dumps({"since": s.isoformat(), "until": e.isoformat()}),
                         limit=500, **kw)
        s = e + timedelta(days=1)
    return out


def ad_catalog_map(c, acct, since, until):
    """ad_id → product_set_id (None = nekatalogová). Ads tahá po kampaních (účet naráz = HTTP 500)."""
    camp_rows = fetch(c, acct, since, until, breakdown=False, level="campaign")
    ids = set()
    for r in c.get_all(f"{acct}/campaigns", fields="id,name", limit=500):
        if any(cr.get("campaign_name") == r["name"] for cr in camp_rows):
            ids.add(r["id"])
    out: dict[str, str | None] = {}
    for cid in ids:
        for a in c.get_all(f"{cid}/ads", fields="id,name,creative{product_set_id,object_type}",
                           limit=500):
            out[a["id"]] = (a.get("creative") or {}).get("product_set_id")
    return out


def agg_products(rows, varianta_re: re.Pattern | None = None):
    """Řádky → agregace po modelu.

    `varianta_re` (volitelně) odstřihne z názvu část, která označuje variantu
    (např. velikost nebo barvu), aby se varianty jednoho modelu sloučily.
    Bez něj se produkty slučují jen podle ID před podtržítkem a celého názvu.
    """
    out: dict[tuple, dict] = {}
    for r in rows:
        raw = r.get("product_id") or ""
        rid, _, name = raw.partition(", ")
        # Feed má v názvech zalomení řádků (a může mít `|`) — bez očištění to rozbije
        # řádek markdown tabulky v reportu. Sjednoť bílé znaky hned u zdroje.
        name = " ".join(name.replace("|", "/").split())
        model = varianta_re.sub("", name) if varianta_re else name
        key = (rid.split("_")[0], model.strip() or "(bez názvu)")
        e = out.setdefault(key, {"id": key[0], "produkt": key[1], "spend": 0.0, "obrat": 0.0,
                                 "nakupy": 0.0, "atc_hodnota": 0.0, "imprese": 0, "prokliky": 0,
                                 "varianty": set()})
        e["spend"] += float(r.get("spend") or 0)
        e["obrat"] += pick(r.get("action_values"), PURCH_TYPES)
        e["nakupy"] += pick(r.get("actions"), PURCH_TYPES)
        e["atc_hodnota"] += pick(r.get("action_values"), ATC_TYPES)
        e["imprese"] += int(r.get("impressions") or 0)
        e["prokliky"] += int(r.get("inline_link_clicks") or 0)
        e["varianty"].add(raw)
    for e in out.values():
        e["varianty"] = len(e["varianty"])
        e["roas"] = round(e["obrat"] / e["spend"], 2) if e["spend"] else None
    return out


def totals(rows):
    t = {"spend": 0.0, "obrat": 0.0, "nakupy": 0.0, "imprese": 0, "prokliky": 0}
    for r in rows:
        t["spend"] += float(r.get("spend") or 0)
        t["obrat"] += pick(r.get("action_values"), PURCH_TYPES)
        t["nakupy"] += pick(r.get("actions"), PURCH_TYPES)
        t["imprese"] += int(r.get("impressions") or 0)
        t["prokliky"] += int(r.get("inline_link_clicks") or 0)
    t["roas"] = round(t["obrat"] / t["spend"], 2) if t["spend"] else None
    return t


def write_csv(path: Path, data: list[dict], cols: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for e in data:
            w.writerow([round(e[c], 1) if isinstance(e.get(c), float) else e.get(c, "")
                        for c in cols])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--account", required=True)
    p.add_argument("--out", required=True, help="prefix výstupních souborů")
    p.add_argument("--quiet", action="store_true",
                   help="nevypisuj data na stdout, jen cesty k souborům "
                        "(pro běh, kdy data nemají opustit počítač)")
    p.add_argument("--varianta-regex", default="",
                   help="regulární výraz, který z názvu produktu odstřihne označení varianty "
                        "(např. r'\\s+(size|velikost)\\b.*$'), aby se varianty sloučily do modelu; "
                        "prázdné = vypnuto")
    a = p.parse_args()
    try:
        varianta_re = re.compile(a.varianta_regex, re.I) if a.varianta_regex else None
    except re.error as e:
        p.error(f"--varianta-regex není platný regulární výraz: {e}")

    acct = normalize_account_id(a.account)
    # NDA pojistka jako u ostatních Meta čtecích skriptů (fetch.py).
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib.nda import guard
    guard(acct, "read-raw")
    c = MetaClient()
    w30_s, w30_e = window(30)
    w7_s, w7_e = window(7)
    w23_s, w23_e = window(23, offset=7)  # předchozích 23 dní = 30d bez posledních 7
    wp7_s, wp7_e = window(7, offset=7)   # předchozí týden — na srovnání týden vs. týden

    print(f"# okna: 30d {w30_s}..{w30_e} | 7d {w7_s}..{w7_e} | předchozí 23d {w23_s}..{w23_e}"
          f" | předchozí 7d {wp7_s}..{wp7_e}",
          file=sys.stderr)

    catmap = ad_catalog_map(c, acct, w30_s, w30_e)
    print(f"# reklam v mapě: {len(catmap)}, z toho katalogových: "
          f"{sum(1 for v in catmap.values() if v)}", file=sys.stderr)

    data = {}
    for tag, (s, e) in (("30d", (w30_s, w30_e)), ("7d", (w7_s, w7_e)),
                        ("prev23d", (w23_s, w23_e)), ("prev7d", (wp7_s, wp7_e))):
        prod = fetch(c, acct, s, e, breakdown=True)
        flat = fetch(c, acct, s, e, breakdown=False)
        kat = [r for r in prod if catmap.get(r["ad_id"])]
        obs = [r for r in prod if not catmap.get(r["ad_id"])]
        data[tag] = {
            "range": [s.isoformat(), e.isoformat()],
            "ucet": totals(fetch(c, acct, s, e, breakdown=False, level="account")),
            "katalog": totals([r for r in flat if catmap.get(r["ad_id"])]),
            "obsah": totals([r for r in flat if not catmap.get(r["ad_id"])]),
            "neznama": totals([r for r in flat if r["ad_id"] not in catmap]),
            "prod_katalog": agg_products(kat, varianta_re),
            "prod_obsah": agg_products(obs, varianta_re),
        }
        print(f"# {tag}: produkt. řádků {len(prod)} (katalog {len(kat)} / obsah {len(obs)})",
              file=sys.stderr)

    out = Path(a.out)
    cols = ["id", "produkt", "spend", "obrat", "roas", "nakupy", "atc_hodnota",
            "imprese", "prokliky", "varianty"]
    for tag in ("30d", "7d"):
        for seg in ("katalog", "obsah"):
            rows = sorted(data[tag][f"prod_{seg}"].values(), key=lambda x: -x["spend"])
            write_csv(Path(f"{out}_{seg}_{tag}.csv"), rows, cols)

    # JSON pro navazující analýzu (sety převedeny na počty už v agg_products)
    dump = {t: {k: (v if not k.startswith("prod_") else list(v.values()))
                for k, v in d.items()} for t, d in data.items()}
    Path(f"{out}_raw.json").write_text(json.dumps(dump, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    if a.quiet:
        print(f"Data zapsána lokálně: {out}_raw.json + CSV (katalog/obsah × 30d/7d)")
    else:
        print(json.dumps({t: {k: d[k] for k in ("range", "ucet", "katalog", "obsah", "neznama")}
                          for t, d in data.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

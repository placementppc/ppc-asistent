#!/usr/bin/env python3
"""Z `product_report.py --out X` (soubor X_raw.json) udělá markdown report + návrhy.

Report je POUZE za katalogovou reklamu (reklamy s `creative{product_set_id}`).
Obsahová reklama (bannery, videa) se do něj nedostane — její produktové řádky pocházejí
z pixelu, ne z reklamy, a míchat je dohromady dává zavádějící čísla.

Prahy: nepoužíváme fixní „spend > N Kč“, ale násobek průměrné CPA katalogu. Když produkt
utratil 3× CPA a nemá nákup, je pravděpodobnost, že jde o náhodu, ~5 % (Poisson, e^-3).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CZK = lambda x: f"{x:,.0f}".replace(",", " ")  # noqa: E731
DES = lambda x: f"{x:g}".replace(".", ",")     # noqa: E731  desetinná čárka do textu

# Výchozí prahy — sdílené pro všechny klienty. Override jen přes CLI (viz --help)
# a jen s důvodem (jiná marže, brand kampaň, jiná vertikála).
MD_LIMIT = 60       # max řádků tabulky v markdownu; plný seznam jde vždy do CSV
MIN_IMPR_DEF = 500  # pod tímhle je CTR/CPC šum, ne signál
WATCH_ROAS_DEF = 1.1  # pod tímhle ROAS produkt nevydělává
CPA_NASOBEK = 3.0   # kolik× CPA bez nákupu = statisticky obhajitelné vyřazení (p≈5 %)
CTR_PRAH_DEF = 1.0  # % — nezajímavý produkt
CPC_NASOBEK = 1.5   # kolik× nad průměrné CPC na odkaz už je proklik drahý
VYPRODANO_POKLES = 0.7  # spend za 7 dní o 70 % nižší než předchozích 7 dní
NOVINKY_MIN_IMPR = 100  # méně impresí za 7 dní = zatím se ani pořádně nerozběhlo


def roas(e):
    return e["obrat"] / e["spend"] if e["spend"] else 0.0


def ctr(e):
    """CTR na odkaz — ověřeno proti Meta `inline_link_click_ctr` (shoda na 2 des. místa)."""
    return 100 * e["prokliky"] / e["imprese"] if e["imprese"] else 0.0


def cpc(e):
    """CPC na odkaz = spend / inline_link_clicks."""
    return e["spend"] / e["prokliky"] if e["prokliky"] else 0.0


def clean(name: str) -> str:
    """Feed má v názvech zalomení řádků (a může mít `|`) — to rozbije řádek markdown tabulky."""
    return " ".join(str(name).replace("|", "/").split())


def idx(products):
    """Klíč (id, očištěný název). Názvy lišící se jen bílými znaky slučuje, ať se spend neztratí."""
    out: dict[tuple, dict] = {}
    for p in products:
        p = {**p, "produkt": clean(p["produkt"])}
        key = (p["id"], p["produkt"])
        if key in out:
            cur = out[key]
            for f in ("spend", "obrat", "nakupy", "atc_hodnota", "imprese", "prokliky", "varianty"):
                cur[f] = cur.get(f, 0) + p.get(f, 0)
            cur["roas"] = round(cur["obrat"] / cur["spend"], 2) if cur["spend"] else None
        else:
            out[key] = p
    return out


def trend_arrow(cur, prev, eps=0.15):
    if prev == 0 and cur == 0:
        return "–"
    if prev == 0:
        return "🆕"
    d = (cur - prev) / prev
    return "↑" if d > eps else ("↓" if d < -eps else "→")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--client", default="klient")
    p.add_argument("--quiet", action="store_true",
                   help="nevypisuj souhrn na stdout, jen cestu k reportu")
    p.add_argument("--ctr-prah", type=float, default=CTR_PRAH_DEF,
                   help=f"hranice nízkého CTR na odkaz v %% (default {CTR_PRAH_DEF}). Report vždy "
                        "vypíše i reálné rozložení, ať je vidět, jestli práh něco chytá.")
    p.add_argument("--cpc-nasobek", type=float, default=CPC_NASOBEK,
                   help=f"kolikrát nad průměrné CPC na odkaz je produkt drahý (default {CPC_NASOBEK})")
    p.add_argument("--watch-roas", type=float, default=WATCH_ROAS_DEF,
                   help=f"pod tímhle ROAS jde produkt na watchlist (default {WATCH_ROAS_DEF}). "
                        "Při známé marži nastav reálný break-even, ne 1.0.")
    p.add_argument("--cpa-nasobek", type=float, default=CPA_NASOBEK,
                   help=f"kolik× CPA bez nákupu = návrh na vyřazení (default {CPA_NASOBEK}, p≈5 %%)")
    p.add_argument("--min-impresi", type=int, default=MIN_IMPR_DEF,
                   help=f"minimum impresí pro hodnocení CTR/CPC (default {MIN_IMPR_DEF})")
    p.add_argument("--vyprodano-pokles", type=float, default=VYPRODANO_POKLES,
                   help=f"o kolik musí spend za 7 dní klesnout proti předchozím 7 dnům, aby šlo "
                        f"o pravděpodobné vyprodání (default {VYPRODANO_POKLES} = pokles o 70 %%)")
    p.add_argument("--anonym", action="store_true",
                   help="vynech název klienta z reportu (titulek i názvy souborů v patičce). "
                        "Povinné v lokálním režimu dat u klientů pod NDA.")
    a = p.parse_args()
    CTR_PRAH, CTR_MIN_IMPR, WATCH_ROAS = a.ctr_prah, a.min_impresi, a.watch_roas

    D = json.loads(Path(a.raw).read_text(encoding="utf-8"))
    d30, d7, dprev = D["30d"], D["7d"], D["prev23d"]
    dp7 = D.get("prev7d")  # starší _raw.json tohle okno nemá — sekce 2g to pozná a řekne
    k30, k7, kprev = (idx(d[k]) for d, k in ((d30, "prod_katalog"), (d7, "prod_katalog"),
                                             (dprev, "prod_katalog")))
    kp7 = idx(dp7["prod_katalog"]) if dp7 else {}

    cpa = d30["katalog"]["spend"] / d30["katalog"]["nakupy"] if d30["katalog"]["nakupy"] else 0
    t_out, t_watch = a.cpa_nasobek * cpa, 2 * cpa

    # --- doplnění 7d hodnot a trendu ------------------------------------------
    prazdny = {"spend": 0, "obrat": 0, "nakupy": 0, "imprese": 0, "prokliky": 0}
    for key, e in k30.items():
        cur = {**prazdny, **k7.get(key, {})}
        prev = {**prazdny, **kprev.get(key, {})}
        e["_cur7"], e["_prev"] = cur, prev
        # denní tempo spendu — okna mají různou délku (7 vs. 23 dní), absolutní čísla nelze srovnat
        e["_den7"] = cur["spend"] / 7
        e["_denprev"] = prev["spend"] / 23
        # Hlavní srovnání pro sekci 2g: stejně dlouhá okna, 7 dní vs. předchozích 7 dní.
        p7 = {**prazdny, **kp7.get(key, {})}
        e["_p7"] = p7
        e["_zmena7"] = ((cur["spend"] - p7["spend"]) / p7["spend"]) if p7["spend"] else None
        e["_s7"], e["_o7"] = cur["spend"], cur["obrat"]
        e["_roas7"] = roas(cur) if cur["spend"] else None
        # trend porovnává denní průměr ROAS: posledních 7 dní vs. předchozích 23
        e["_trend"] = trend_arrow(roas(cur) if cur["spend"] else 0,
                                  roas(prev) if prev["spend"] else 0)

    vse = sorted(k30.values(), key=lambda e: -e["spend"])
    # Podíl na spendu katalogu + kumulativní součet — bez toho report ukazuje jen výjimky
    # a největší utrácející produkty (s průměrným ROAS) v něm nejsou nikde vidět.
    _tot_spend = d30["katalog"]["spend"] or 1
    _kum = 0.0
    for e in vse:
        e["_podil"] = 100 * e["spend"] / _tot_spend
        _kum += e["_podil"]
        e["_kumul"] = _kum
    top = vse[:30]
    hvezdy = sorted([e for e in vse if e["spend"] >= t_watch and roas(e) >= 6],
                    key=lambda e: -e["obrat"])
    bez_nakupu = [e for e in vse if e["nakupy"] == 0]
    watch = [e for e in vse if e["nakupy"] > 0 and roas(e) < WATCH_ROAS]
    nizke_ctr = sorted([e for e in vse if e["imprese"] >= CTR_MIN_IMPR and ctr(e) < CTR_PRAH],
                       key=lambda e: -e["spend"])
    # Průměrné CPC na odkaz za celý katalog (vážené, ne průměr produktových CPC).
    _kat = d30["katalog"]
    cpc_prumer = _kat["spend"] / _kat["prokliky"] if _kat.get("prokliky") else 0.0
    cpc_limit = a.cpc_nasobek * cpc_prumer
    drahe_cpc = sorted([e for e in vse if e["imprese"] >= CTR_MIN_IMPR and cpc(e) > cpc_limit],
                       key=lambda e: -e["spend"])
    # Pravděpodobně vyprodané: běžely v prvních 23 dnech, v posledních 7 tempo spadlo.
    # Gate na imprese drží pryč produkty, které se nikdy pořádně nezobrazovaly.
    vyprodane = sorted([e for e in vse if e["imprese"] >= CTR_MIN_IMPR
                        and e["_zmena7"] is not None and e["_zmena7"] <= -a.vyprodano_pokles],
                       key=lambda e: -e["_p7"]["spend"])
    # Novinky: spend až v posledních 7 dnech, předtím nula.
    novinky = sorted([e for e in vse if e["_prev"]["spend"] == 0
                      and e["_cur7"]["imprese"] >= NOVINKY_MIN_IMPR],
                     key=lambda e: -e["_s7"])

    # Rozložení CTR — bez něj se nedá poznat, jestli zvolený práh vůbec něco chytá.
    mer = sorted(ctr(e) for e in vse if e["imprese"] >= CTR_MIN_IMPR)
    if mer:
        q = lambda f: mer[min(int(f * len(mer)), len(mer) - 1)]  # noqa: E731
        pasma = " · ".join(f"pod {t:g} %: **{sum(1 for c in mer if c < t)}**"
                           for t in (1, 1.5, 2, 2.5, 3))
        ctr_rozlozeni = (
            f"**Rozložení CTR** ({len(mer)} produktů s ≥ {CTR_MIN_IMPR} impresemi): "
            f"min {mer[0]:.2f} % · p10 {q(0.10):.2f} % · medián {q(0.50):.2f} % · "
            f"p90 {q(0.90):.2f} % · max {mer[-1]:.2f} %.\n\n"
            f"Počty pod jednotlivými prahy — {pasma}.\n")
    else:
        ctr_rozlozeni = f"_Žádný produkt nemá alespoň {CTR_MIN_IMPR} impresí._\n"

    mcpc = sorted(cpc(e) for e in vse if e["imprese"] >= CTR_MIN_IMPR and e["prokliky"])
    if mcpc and cpc_prumer:
        qc = lambda f: mcpc[min(int(f * len(mcpc)), len(mcpc) - 1)]  # noqa: E731
        pasma_cpc = " · ".join(
            f"nad {n:g}×: **{sum(1 for c in mcpc if c > n * cpc_prumer)}**"
            for n in (1.2, 1.5, 2, 3))
        cpc_rozlozeni = (
            f"**Rozložení CPC na odkaz** ({len(mcpc)} produktů): min {mcpc[0]:.2f} Kč · "
            f"p10 {qc(0.10):.2f} Kč · medián {qc(0.50):.2f} Kč · p90 {qc(0.90):.2f} Kč · "
            f"max {mcpc[-1]:.2f} Kč.\n\nPočty nad násobky průměru — {pasma_cpc}.\n")
    else:
        cpc_rozlozeni = "_Nedost dat pro rozložení CPC._\n"

    def znacka(e):
        if e["spend"] >= t_out:
            return "⚠️ web" if e["atc_hodnota"] > 0 else "⛔ vyloučit"
        return "· málo dat"

    # --- tabulky ---------------------------------------------------------------
    def ptable(rows, cols, limit=MD_LIMIT):
        head = {"produkt": ("Produkt", "---"), "spend": ("Spend 30d", "---:"),
                "obrat": ("Obrat 30d", "---:"), "roas": ("ROAS 30d", "---:"),
                "nakupy": ("Nákupy", "---:"), "ctr": ("CTR na odkaz", "---:"),
                "cpc": ("CPC na odkaz", "---:"), "vs_cpc": ("vs. průměr", "---:"),
                "podil": ("% spendu", "---:"), "kumul": ("kumul.", "---:"),
                "sp7": ("Spend předch. 7d", "---:"), "zmena7": ("Změna WoW", "---:"),
                "den_prev": ("Ø/den (23 d)", "---:"), "den7": ("Ø/den (7 d)", "---:"), "impr7": ("Imprese 7d", "---:"),
                "obrat7": ("Obrat 7d", "---:"), "nakupy7": ("Nákupy 7d", "---:"),
                "ctr7": ("CTR na odkaz 7d", "---:"),
                "atc": ("Hodnota ATC", "---:"), "impr": ("Imprese", "---:"),
                "s7": ("Spend 7d", "---:"), "roas7": ("ROAS 7d", "---:"),
                "trend": ("Trend", ":--:"), "znacka": ("Doporučení", "---")}
        out = ["| " + " | ".join(head[c][0] for c in cols) + " |",
               "|" + "|".join(head[c][1] for c in cols) + "|"]
        for e in rows[:limit]:
            v = {"produkt": e["produkt"], "spend": CZK(e["spend"]), "obrat": CZK(e["obrat"]),
                 "roas": f"{roas(e):.2f}", "nakupy": f"{e['nakupy']:.0f}",
                 "ctr": f"{ctr(e):.2f} %", "cpc": f"{cpc(e):.2f} Kč",
                 "vs_cpc": f"{cpc(e) / cpc_prumer:.2f}×" if cpc_prumer else "–",
                 "podil": f"{e.get('_podil', 0):.1f} %", "kumul": f"{e.get('_kumul', 0):.0f} %",
                 "den_prev": f"{e.get('_denprev', 0):.0f} Kč",
                 "den7": f"{e.get('_den7', 0):.0f} Kč",
                 "sp7": CZK(e["_p7"]["spend"]),
                 "zmena7": ("zastaveno" if e["_s7"] == 0 else
                            f"{100 * e['_zmena7']:+.0f} %" if e["_zmena7"] is not None else "–"),
                 "impr7": CZK(e["_cur7"]["imprese"]), "obrat7": CZK(e["_cur7"]["obrat"]),
                 "ctr7": (f"{100 * e['_cur7']['prokliky'] / e['_cur7']['imprese']:.2f} %"
                          if e["_cur7"]["imprese"] else "–"),
                 "nakupy7": f"{e['_cur7']['nakupy']:.0f}",
                 "atc": CZK(e["atc_hodnota"]),
                 "impr": CZK(e["imprese"]), "s7": CZK(e["_s7"]),
                 "roas7": f"{e['_roas7']:.2f}" if e["_roas7"] is not None else "–",
                 "trend": e["_trend"], "znacka": znacka(e)}
            out.append("| " + " | ".join(v[c] for c in cols) + " |")
        if len(rows) > limit:
            zbytek = rows[limit:]
            out.append(f"\n_Zobrazeno {limit} z {len(rows)} — zbývajících {len(zbytek)} "
                       f"za {CZK(sum(x['spend'] for x in zbytek))} Kč spendu je v CSV._")
        return "\n".join(out)

    def dump_csv(path, rows):
        with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["id", "produkt", "spend_30d", "obrat_30d", "roas_30d", "nakupy",
                        "ctr_na_odkaz_%", "cpc_na_odkaz", "cpc_vs_prumer", "imprese", "prokliky",
                        "hodnota_ATC", "spend_7d", "spend_predch_7d", "zmena_wow_%", "roas_7d",
                        "trend", "doporuceni"])
            for e in rows:
                w.writerow([e["id"], e["produkt"], round(e["spend"], 1), round(e["obrat"], 1),
                            round(roas(e), 2), int(e["nakupy"]), round(ctr(e), 2),
                            round(cpc(e), 2),
                            round(cpc(e) / cpc_prumer, 2) if cpc_prumer else "", e["imprese"],
                            e["prokliky"], round(e["atc_hodnota"], 1), round(e["_s7"], 1),
                            round(e["_p7"]["spend"], 1),
                            round(100 * e["_zmena7"], 1) if e["_zmena7"] is not None else "",
                            round(e["_roas7"], 2) if e["_roas7"] is not None else "",
                            e["_trend"], znacka(e)])

    base = str(Path(a.out).with_suffix(""))
    dump_csv(f"{base}_bez-nakupu.csv", bez_nakupu)
    dump_csv(f"{base}_watchlist.csv", watch)
    dump_csv(f"{base}_nizke-ctr.csv", nizke_ctr)
    dump_csv(f"{base}_drahe-cpc.csv", drahe_cpc)
    dump_csv(f"{base}_vyprodane.csv", vyprodane)
    dump_csv(f"{base}_novinky.csv", novinky)
    dump_csv(f"{base}_vse.csv", vse)

    # --- report ----------------------------------------------------------------
    u, k = d30["ucet"], d30["katalog"]
    nadpis = ("# Produktový report — katalogová reklama (Meta)" if a.anonym
              else f"# Produktový report (katalogová reklama) — {a.client}")
    L = [nadpis,
         f"\n**Období:** 30 dní {d30['range'][0]} – {d30['range'][1]} · "
         f"7 dní {d7['range'][0]} – {d7['range'][1]} · "
         f"srovnávací okno {dprev['range'][0]} – {dprev['range'][1]} (23 dní)",
         "\nRead-only, žádná změna v účtu neproběhla. "
         "Report je **pouze za katalogovou reklamu** — obsahová (bannery, videa) v něm není.\n",
         "## 1. Úroveň účtu\n",
         "| Období | Spend účtu | Spend katalogu | Podíl | Obrat katalogu | ROAS | PNO | "
         "Nákupy | CPA |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for tag, d in (("30 dní", d30), ("7 dní", d7)):
        uu, kk = d["ucet"], d["katalog"]
        r = kk["roas"] or 0
        L.append(f"| {tag} | {CZK(uu['spend'])} Kč | {CZK(kk['spend'])} Kč | "
                 f"{100 * kk['spend'] / uu['spend']:.0f} % | {CZK(kk['obrat'])} Kč | {r:.2f} | "
                 f"{100 / r:.1f} % | {kk['nakupy']:.0f} | "
                 f"{CZK(kk['spend'] / kk['nakupy']) if kk['nakupy'] else '–'} Kč |")

    L += ["\n## 2. Katalogová reklama — produkty\n",
          f"- Produktů se spendem: **{len(k30)}** modelů "
          f"({sum(e['varianty'] for e in k30.values())} variant) za 30 dní, "
          f"**{len(k7)}** za 7 dní.",
          f"- Průměrná CPA katalogu: **{CZK(cpa)} Kč** = spend katalogu za 30 dní "
          f"({CZK(_kat['spend'])} Kč) ÷ nákupy katalogu za 30 dní ({_kat['nakupy']:.0f}). "
          "Je to vážený průměr za celý katalog ve stejném 30denním okně, ne průměr CPA "
          "jednotlivých produktů a ne hodnota z jiného období. Bere se z dat na úrovni reklam "
          "bez produktového breakdownu, aby ji nezkreslily řádky, kde Meta produkt nepřiřadí.",
          f"- Práh pro vyřazení = **{DES(a.cpa_nasobek)}× CPA = {CZK(t_out)} Kč** utraceno bez "
          "jediného nákupu. "
          f"Očekávaný počet nákupů při průměrné CPA: {DES(a.cpa_nasobek)}. Že nepřijde ani jeden, "
          f"má pravděpodobnost ~{100 * 2.718281828 ** -a.cpa_nasobek:.0f} % (Poisson). "
          "Pod tímhle prahem jsou data na rozhodnutí příliš tenká.",
          f"- Bez jediného nákupu: **{len(bez_nakupu)}** modelů za "
          f"{CZK(sum(e['spend'] for e in bez_nakupu))} Kč "
          f"({100 * sum(e['spend'] for e in bez_nakupu) / k['spend']:.0f} % spendu katalogu).",
          "\n### 2a. Kam jdou peníze — top produkty podle spendu\n",
          "Tahle tabulka není výběr podle prahu, je to prostě **největší utrácející produkty "
          "katalogu**. Ostatní sekce ukazují jen výjimky (nulové, ztrátové, drahé), takže produkt "
          "s velkým spendem a průměrným ROAS by se v reportu jinak neobjevil vůbec — a přitom "
          "je v něm většina rozpočtu.\n",
          f"Koncentrace: **top 10** modelů = {top[min(9, len(top) - 1)]['_kumul']:.0f} % spendu katalogu, "
          f"**top 25** = {top[min(24, len(top) - 1)]['_kumul']:.0f} %, "
          f"**top 50** = {vse[min(49, len(vse) - 1)]['_kumul']:.0f} %.\n",
          ptable(top, ["produkt", "spend", "podil", "kumul", "obrat", "roas", "nakupy",
                       "ctr", "cpc", "s7", "roas7", "trend"], 30),
          "\n### 2b. Tahouni (spend ≥ 2× CPA, ROAS ≥ 6)\n",
          ptable(hvezdy, ["produkt", "spend", "obrat", "roas", "nakupy", "s7", "roas7", "trend"],
                 15) if hvezdy else "_Žádný produkt._",
          "\n### 2c. Produkty, které jen utrácejí — nula nákupů\n",
          "Seřazeno podle spendu. Značka: **⛔ vyloučit** = nad prahem 3× CPA a nikdo si produkt "
          "ani nedal do košíku. **⚠️ web** = nad prahem, ale lidé ho do košíku dávali → problém "
          "je nejspíš za proklikem (cena, velikosti, doprava, checkout), ne v reklamě. "
          "**· málo dat** = pod prahem, nechat běžet.\n",
          ptable(bez_nakupu, ["produkt", "spend", "impr", "ctr", "atc", "s7", "znacka"])
          if bez_nakupu else "_Žádný produkt._",
          f"\n### 2d. Watchlist — ROAS pod {DES(WATCH_ROAS)}\n",
          "Produkty, které nákupy mají, ale nevydělávají. Seřazeno podle spendu.\n",
          ptable(watch, ["produkt", "spend", "obrat", "roas", "nakupy", "ctr", "s7", "roas7",
                         "trend"]) if watch else "_Žádný produkt._",
          f"\n### 2e. Nezajímavé produkty — CTR na odkaz pod {DES(CTR_PRAH)} %\n",
          f"Jen produkty s alespoň {CTR_MIN_IMPR} impresemi (pod tím je CTR šum). Nízké CTR "
          "znamená, že produkt lidi v katalogu neosloví — kandidát na vyřazení bez ohledu na to, "
          "jestli náhodou pár nákupů má, protože žere imprese lepším produktům.\n",
          ctr_rozlozeni,
          ptable(nizke_ctr, ["produkt", "spend", "impr", "ctr", "cpc", "obrat", "roas", "nakupy",
                             "trend"]) if nizke_ctr else
          f"_Práh {DES(CTR_PRAH)} % nechytil žádný produkt — viz rozložení výše._",
          f"\n### 2f. Drahé prokliky — CPC na odkaz nad {DES(a.cpc_nasobek)}× průměru\n",
          f"Průměrné CPC na odkaz v katalogu: **{cpc_prumer:.2f} Kč** → hranice "
          f"**{cpc_limit:.2f} Kč**. Opět jen produkty s ≥ {CTR_MIN_IMPR} impresemi. "
          "Drahý proklik sám o sobě není problém, pokud se produkt dobře prodává — čti tuhle "
          "tabulku spolu se sloupcem ROAS.\n",
          cpc_rozlozeni,
          ptable(drahe_cpc, ["produkt", "spend", "impr", "ctr", "cpc", "vs_cpc", "obrat",
                             "roas", "nakupy", "trend"])
          if drahe_cpc else "_Žádný produkt._",
          "\n### 2g. Pravděpodobně vyprodané / vypadlé z feedu\n",
          (f"Srovnání **týden vs. týden**: posledních 7 dní ({d7['range'][0]} – "
           f"{d7['range'][1]}) proti předchozím 7 dnům ({dp7['range'][0]} – {dp7['range'][1]}). "
           f"V tabulce jsou produkty, kterým spend klesl o "
           f"**{DES(round(100 * a.vyprodano_pokles))} % a víc**, a které mají alespoň "
           f"{CTR_MIN_IMPR} impresí za 30 dní. Okna jsou stejně dlouhá, takže se porovnávají "
           "přímo částky. Seřazeno podle spendu v předchozím týdnu — nahoře je to, kde zmizelo "
           "nejvíc peněz.\n"
           if dp7 else
           "⚠️ **Sekci nelze spočítat** — v `_raw.json` chybí okno `prev7d`. Data jsou "
           "ze staršího běhu; stáhni je znovu přes `product_report.py`.\n"),
          "⚠️ **Tohle je domněnka, ne fakt.** Meta neříká, proč přestala produkt zobrazovat. "
          "Kromě vyprodání to může být vypadnutí z feedu, změna ceny, zamítnutí produktu, nebo "
          "prosté přerozdělení rozpočtu algoritmem. Ber to jako **seznam k ověření proti feedu** "
          "(pole `availability` v katalogu), ne jako závěr. U položek dole v tabulce jsou částky "
          "malé — tam bývá pokles jen šum.\n",
          ((ptable(vyprodane, ["produkt", "sp7", "s7", "zmena7", "spend", "impr",
                               "obrat", "roas", "nakupy"])
            if vyprodane else "_Žádný produkt nesplnil práh._") if dp7 else ""),
          "\n### 2h. Novinky — začaly utrácet až posledních 7 dní\n",
          "Produkty **bez jediné koruny spendu v prvních 23 dnech**, které se rozběhly až "
          f"v posledním týdnu. Typicky nové zboží ve feedu nebo něco, co se vrátilo skladem. "
          f"Jen produkty s alespoň {NOVINKY_MIN_IMPR} impresemi za těch 7 dní — pod tím se to "
          "ještě ani nerozběhlo. Seřazeno podle spendu za 7 dní.\n",
          "⚠️ Vidím **spend, ne obsah feedu**. Že produkt neutrácel, neznamená, že ve feedu "
          "nebyl — mohl v něm ležet a algoritmus ho jen nezobrazoval. Na skutečné novinky se "
          "podívej do katalogu. A protože jde o pár dní dat, **ROAS tady zatím nic neznamená** — "
          "sekce slouží k tomu, abys o nových produktech věděl a pohlídal je, ne abys je "
          "hned hodnotil.\n",
          ptable(novinky, ["produkt", "s7", "impr7", "ctr7", "obrat7", "roas7", "nakupy7"])
          if novinky else "_Žádný nový produkt._",
          "\n## 3. Metodika a omezení\n",
          "- Segmentace podle `creative{product_set_id}` na úrovni reklamy, ne podle názvu "
          "kampaně — v ASC kampani běží katalog i bannery/videa vedle sebe.",
          "- **CTR na odkaz** = `inline_link_clicks / impressions`, **CPC na odkaz** = "
          "`spend / inline_link_clicks`. Ověřeno proti Meta `inline_link_click_ctr` — shoda "
          "na dvě desetinná místa. Není to CTR/CPC všech kliknutí (ta jsou zhruba o pětinu vyšší).",
          "- Sekce 2d a 2e zůstávají v reportu i prázdné — ať je při dalším běhu a u jiných "
          "klientů vidět, kde prahy leží. Rozložení hodnot je vypsané vždy.",
          "- Konverze se čtou z prvního naplněného typu (`onsite_web_purchase` → `omni_purchase` → "
          "`purchase`); některé účty vrací v produktovém breakdownu u ostatních typů nuly.",
          "- Obrat je přiřazen produktu, který byl v reklamě — objednávka ale může obsahovat "
          "i dokoupené položky. ROAS produktu = „ROAS objednávek, které ten produkt "
          "nastartoval“, ne marže na produktu.",
          "- Trend porovnává ROAS posledních 7 dní vs. předchozích 23; ↑/↓ při změně nad 15 %.",
          "- Sekce 2g srovnává **posledních 7 dní proti předchozím 7 dnům** — stejně dlouhá "
          "okna, takže se porovnávají přímo částky.",
          "- Sekce 2g i 2h jsou **signál k ověření proti feedu, ne závěr**: z insights se nedá "
          "poznat, jestli produkt zmizel ze skladu, z feedu, změnil cenu, byl zamítnutý, nebo mu "
          "jen algoritmus ubral rozpočet. Týdenní srovnání je navíc citlivé na sezónu, víkendy "
          "a výkyvy rozpočtu — u produktů s malým spendem ber pokles s rezervou.",
          "- 30denní okno taháno po týdnech a sečteno (Meta synchronně 30 dní × product_id "
          "nevrátí). Konverze atribuuje k datu imprese, takže součet dílů = celek.",
          "- Poslední den je včerejšek, dnešek je nekompletní.",
          f"\n**Plné seznamy:** `{'<report>' if a.anonym else Path(base).name}_vse.csv`, "
          f"`_bez-nakupu.csv`, `_watchlist.csv`, `_nizke-ctr.csv`, `_drahe-cpc.csv`, "
          f"`_vyprodane.csv`, `_novinky.csv`"]

    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"zapsáno: {a.out}")
    if not a.quiet:
        print(f"CPA {cpa:.0f} | bez nákupu {len(bez_nakupu)} | watchlist {len(watch)} | "
              f"nízké CTR {len(nizke_ctr)} | tahouni {len(hvezdy)}")


if __name__ == "__main__":
    main()

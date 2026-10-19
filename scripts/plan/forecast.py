#!/usr/bin/env python3
"""Forecast útraty, obratu a konverzí na měsíc (nebo víc měsíců) z historie účtu. Jen čte.

Použití:
    python3 scripts/plan/forecast.py --klient muj-eshop                  # příští měsíc, data z API
    python3 scripts/plan/forecast.py --klient muj-eshop --mesic 2026-11 --mesicu 2
    python3 scripts/plan/forecast.py --klient muj-eshop --rozpocet 80000  # „co když dáme 80 tisíc"
    python3 scripts/plan/forecast.py --klient ukazka --csv scripts/plan/ukazka-data.csv   # bez API

Data: účty klienta z clients/hlidac-ucty.json (pole "klient"), stahuje se přes konektory
hlídače (scripts/hlidac/zdroje.py). Nebo --csv se sloupci datum, system, naklady, obrat, konverze.

Metoda (detail v .claude/skills/forecast/SKILL.md):
1. Nesuď z krátkého okna: tempo z posledních 8 celých týdnů, kontext z měsíční řady celé historie.
2. Historie aspoň 13 měsíců → loňský stejný měsíc × meziroční trend (8 týdnů letos / stejných
   8 týdnů loni, zarovnáno na dny v týdnu). Tím je v odhadu sezóna i Black Friday.
3. Kratší historie → tempo posledních 8 týdnů × skladba dnů v měsíci. Sezónu to nezná — pásmo je širší.
4. Scénáře konzervativní / realistický / ambiciózní = pásmo z kolísání týdnů, ne jedno číslo.
5. „Co když rozpočet +X %": obrat ~ útrata^b (b < 1 = každá další koruna vydělá míň). Odhad, ne slib.

Výstup: plans/<klient>/forecast-<YYYY-MM>.md a .csv (YYYY-MM = první forecastovaný měsíc).
Návratový kód: 0 OK, 1 forecast je, ale se slabší oporou (krátká historie, bez loňska), 2 chyba.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import model as M  # noqa: E402

ROOT = D.ROOT
METRIKY = ("naklady", "obrat", "konverze")
ZMENY_ROZPOCTU = (-20, 10, 20, 30, 50)
NAZVY_METRIK = {"naklady": "náklady", "obrat": "obrat", "konverze": "konverze"}
NAZVY_MESICU = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen",
                "září", "říjen", "listopad", "prosinec"]


def nazev_mesice(rok: int, mesic: int) -> str:
    return f"{NAZVY_MESICU[mesic - 1]} {rok}"


def _pokryti(dny: dict, od: date, do: date) -> float:
    n = (do - od).days + 1
    return sum(1 for i in range(n) if (od + timedelta(days=i)) in dny) / n if n > 0 else 0.0


def forecast_systemu(dny: dict, rok: int, mesic: int, do: date, mesicu_dopredu: int) -> dict:
    """Realistický odhad jednoho systému na jeden měsíc + nejistota a popis metody."""
    varovani: list[str] = []
    tydnu = M.pocet_celych_tydnu(dny, do)
    if tydnu < M.MIN_TYDNU:
        raise ValueError(f"jen {tydnu} celých týdnů historie, minimum je {M.MIN_TYDNU} "
                         f"(nesuď z krátkého okna)")
    tydny = M.cele_tydny(dny, do, 8)
    okno_od, okno_do = tydny[0][0].datum, tydny[-1][-1].datum
    ly_od, ly_do = okno_od - timedelta(days=364), okno_do - timedelta(days=364)
    ly_rok, ly_mesic = rok - 1, mesic
    ly_dny = M.dny_mesice(ly_rok, ly_mesic)
    dni_cil = len(M.dny_mesice(rok, mesic))

    yoy = (_pokryti(dny, ly_od, ly_do) >= 0.9 and _pokryti(dny, ly_dny[0], ly_dny[-1]) >= 0.9
           and min(dny) <= ly_od)
    out: dict = {"realisticky": {}, "nejistota": {}, "trend": {}, "okno": [okno_od, okno_do]}

    if yoy:
        out["metoda"] = "loňský stejný měsíc × meziroční trend posledních 8 týdnů"
        for m in METRIKY:
            letos = M.soucet(dny, okno_od, okno_do, m)
            loni = M.soucet(dny, ly_od, ly_do, m)
            zaklad = M.soucet(dny, ly_dny[0], ly_dny[-1], m) * dni_cil / len(ly_dny)
            if loni <= 0:
                out["realisticky"][m] = None
                continue
            trend = letos / loni
            if not 0.4 <= trend <= 2.5:
                varovani.append(f"{NAZVY_METRIK[m]}: meziroční trend {M.cislo(trend, 2)}× je extrémní, omezen na pásmo 0,4–2,5×. "
                                f"Ověř, jestli se účet mezitím zásadně nezměnil (nový systém, jiné měření).")
                trend = min(2.5, max(0.4, trend))
            out["trend"][m] = trend
            out["realisticky"][m] = zaklad * trend
            pomery = []
            for tyden in tydny:
                t_letos = sum(M.hodnota(r, m) for r in tyden)
                t_loni = M.soucet(dny, tyden[0].datum - timedelta(days=364),
                                  tyden[-1].datum - timedelta(days=364), m)
                if t_loni > 0:
                    pomery.append(t_letos / t_loni)
            out["nejistota"][m] = min(0.35, max(0.08, M.relativni_rozptyl(pomery)))
    if not yoy or any(out["realisticky"].get(m) is None for m in METRIKY):
        out["metoda"] = "tempo posledních 8 týdnů × skladba dnů v měsíci (bez loňska — sezónu nezná)"
        varovani.append("Historie nepokrývá loňský stejný měsíc → odhad nezná sezónu. U listopadu "
                        "a prosince může být realita úplně jinde; pásmo je proto širší.")
        out["trend"] = {}
        for m in METRIKY:
            vahy, _ = M.vahy_dnu(dny, do, m)
            prumer = M.soucet(dny, okno_od, okno_do, m) / 56
            out["realisticky"][m] = prumer * sum(vahy[d.weekday()] for d in M.dny_mesice(rok, mesic))
            tydenni = [sum(M.hodnota(r, m) for r in t) for t in tydny]
            out["nejistota"][m] = min(0.45, max(0.15, M.relativni_rozptyl(tydenni) + 0.10))
    rozsireni = 0.03 * max(0, mesicu_dopredu - 1)
    if rozsireni:
        out["nejistota"] = {m: u + rozsireni for m, u in out["nejistota"].items()}
    out["yoy"] = yoy and "loňský" in out["metoda"]

    t26 = M.cele_tydny(dny, do, min(26, tydnu))
    b, b_popis = M.elasticita([sum(r.naklady for r in t) for t in t26], [sum(r.obrat for r in t) for t in t26])
    out["elasticita"], out["elasticita_popis"] = b, b_popis
    out["varovani"] = varovani
    return out


def scenare(fc: dict) -> dict[str, dict[str, float]]:
    """Konzervativní / realistický / ambiciózní při STEJNÉ útratě — liší se obrat a konverze."""
    r = fc["realisticky"]
    u_o, u_k = fc["nejistota"]["obrat"], fc["nejistota"]["konverze"]
    return {
        "konzervativni": {"naklady": r["naklady"], "obrat": r["obrat"] * (1 - u_o), "konverze": r["konverze"] * (1 - u_k)},
        "realisticky": dict(r),
        "ambiciozni": {"naklady": r["naklady"], "obrat": r["obrat"] * (1 + u_o), "konverze": r["konverze"] * (1 + u_k)},
    }


def spocti_forecast(radky: list[M.Radek], mesice: list[tuple[int, int]], do: date,
                    rozpocet: float | None = None) -> dict:
    """Forecast pro všechny systémy a měsíce. Vrací strukturu pro MD/CSV/JSON i pro krycí plán."""
    radky = [r for r in radky if r.datum <= do]
    vysledek: dict = {"do": do, "mesice": [], "varovani": [], "systemy": M.systemy(radky)}
    for i, (rok, mesic) in enumerate(mesice):
        dopredu = (rok * 12 + mesic) - (do.year * 12 + do.month)
        if dopredu <= 0:
            vysledek["varovani"].append(f"{rok}-{mesic:02d} už běží nebo je pryč — forecast nepočítá "
                                        f"se skutečností od začátku měsíce (na to je plneni.py).")
        po_sys = {}
        for s in vysledek["systemy"]:
            dny = M.po_dnech(radky, s)
            try:
                fc = forecast_systemu(dny, rok, mesic, do, max(1, dopredu))
            except ValueError as e:
                if i == 0:
                    vysledek["varovani"].append(f"{M.NAZVY_SYSTEMU.get(s, s)}: forecast nejde — {e}.")
                continue
            fc["scenare"] = scenare(fc)
            for v in fc["varovani"]:
                text = f"{M.NAZVY_SYSTEMU.get(s, s)}: {v}"
                if text not in vysledek["varovani"]:
                    vysledek["varovani"].append(text)
            po_sys[s] = fc
        if not po_sys:
            raise SystemExit("Forecast nejde spočítat: žádný systém nemá aspoň 8 celých týdnů historie.")
        celkem = {sc: {m: sum(f["scenare"][sc][m] for f in po_sys.values()) for m in METRIKY}
                  for sc in ("konzervativni", "realisticky", "ambiciozni")}
        r = celkem["realisticky"]
        zmeny = {}
        for x in ZMENY_ROZPOCTU:
            agg = {"naklady": 0.0, "obrat": 0.0, "konverze": 0.0}
            for f in po_sys.values():
                fr = f["realisticky"]
                sc = M.scenar_rozpoctu(fr["naklady"], fr["obrat"], fr["konverze"], x, f["elasticita"])
                for m in agg:
                    agg[m] += sc[m]
            d_o = agg["obrat"] - r["obrat"]
            zmeny[x] = dict(agg, pno=M.pno(agg["naklady"], agg["obrat"]),
                            marginalni_pno=(agg["naklady"] - r["naklady"]) / d_o * 100 if d_o else None)
        pri_rozpoctu = None
        if rozpocet and r["naklady"] > 0:
            x = (rozpocet / r["naklady"] - 1) * 100
            agg = {"naklady": 0.0, "obrat": 0.0, "konverze": 0.0}
            for f in po_sys.values():
                fr = f["realisticky"]
                sc = M.scenar_rozpoctu(fr["naklady"], fr["obrat"], fr["konverze"], x, f["elasticita"])
                for m in agg:
                    agg[m] += sc[m]
            u = max(f["nejistota"]["obrat"] for f in po_sys.values())
            pri_rozpoctu = dict(agg, zmena_pct=x, pno=M.pno(agg["naklady"], agg["obrat"]),
                                obrat_od=agg["obrat"] * (1 - u), obrat_do=agg["obrat"] * (1 + u))
            if abs(x) > 50:
                vysledek["varovani"].append(f"Rozpočet {M.kc(rozpocet)} je {x:+.0f} % proti obvyklé útratě. "
                                            f"Tak velký skok model klesajícího výnosu jen hádá — "
                                            f"navyšujte po krocích 15–30 % a vyhodnocujte.")
        vysledek["mesice"].append({"rok": rok, "mesic": mesic, "systemy": po_sys, "celkem": celkem,
                                   "zmeny_rozpoctu": zmeny, "pri_rozpoctu": pri_rozpoctu})
    return vysledek


# ---------------------------------------------------------------- výstupy
def tabulka_tydnu(radky: list[M.Radek], do: date) -> list[str]:
    dny = M.po_dnech(radky)
    out = ["| Týden (po–ne) | Náklady | Obrat | PNO | Konverze |", "|---|---:|---:|---:|---:|"]
    for t in M.cele_tydny(dny, do, 8):
        n = sum(r.naklady for r in t)
        o = sum(r.obrat for r in t)
        k = sum(r.konverze for r in t)
        out.append(f"| {t[0].datum:%d. %m.} – {t[-1].datum:%d. %m. %Y} | {M.kc(n)} | {M.kc(o)} | "
                   f"{M.pct(M.pno(n, o))} | {M.cislo(k)} |")
    return out


def tabulka_mesicu(radky: list[M.Radek], do: date) -> list[str]:
    rada = M.mesicni_rada(radky)
    out = ["| Měsíc | Náklady | Obrat | PNO | Konverze | Obrat YoY |", "|---|---:|---:|---:|---:|---:|"]
    for (rok, mesic), v in rada.items():
        dni = len(M.dny_mesice(rok, mesic))
        necely = v["dni"] < dni or (rok, mesic) == (do.year, do.month)
        loni = rada.get((rok - 1, mesic))
        yoy = M.pct(M.odchylka_pct(v["obrat"], loni["obrat"]), True) if loni and not necely else "–"
        out.append(f"| {rok}-{mesic:02d}{' (neúplný)' if necely else ''} | {M.kc(v['naklady'])} | "
                    f"{M.kc(v['obrat'])} | {M.pct(M.pno(v['naklady'], v['obrat']))} | "
                    f"{M.cislo(v['konverze'])} | {yoy} |")
    return out


def markdown(klient: str, radky: list[M.Radek], v: dict) -> str:
    do = v["do"]
    prvni = v["mesice"][0]
    nadpis = nazev_mesice(prvni["rok"], prvni["mesic"])
    if len(v["mesice"]) > 1:
        posl = v["mesice"][-1]
        nadpis += f" až {nazev_mesice(posl['rok'], posl['mesic'])}"
    L = [f"# Forecast — {klient} — {nadpis}", "",
         f"Data do {do:%d. %m. %Y}, od {min(r.datum for r in radky):%d. %m. %Y}. "
         f"Systémy: {', '.join(M.NAZVY_SYSTEMU.get(s, s) for s in v['systemy'])}.", ""]
    for mes in v["mesice"]:
        c = mes["celkem"]
        r, k, a = c["realisticky"], c["konzervativni"], c["ambiciozni"]
        L += [f"## {nazev_mesice(mes['rok'], mes['mesic']).capitalize()}", "",
              f"**Při útratě kolem {M.kc(r['naklady'])} čekej obrat {M.kc(k['obrat'])} až {M.kc(a['obrat'])}, "
              f"nejspíš kolem {M.kc(r['obrat'])} (PNO {M.pct(M.pno(r['naklady'], a['obrat']))} až "
              f"{M.pct(M.pno(r['naklady'], k['obrat']))}).**", "",
              "| Scénář | Náklady | Obrat | Konverze | PNO |", "|---|---:|---:|---:|---:|"]
        for sc, nazev in (("konzervativni", "Konzervativní"), ("realisticky", "Realistický"), ("ambiciozni", "Ambiciózní")):
            x = c[sc]
            L.append(f"| {nazev} | {M.kc(x['naklady'])} | {M.kc(x['obrat'])} | {M.cislo(x['konverze'])} | "
                     f"{M.pct(M.pno(x['naklady'], x['obrat']))} |")
        L += ["", "Po systémech (realistický scénář, pásmo obratu):", "",
              "| Systém | Náklady | Obrat | Pásmo obratu | Konverze | PNO | Metoda |", "|---|---:|---:|---:|---:|---:|---|"]
        for s, f in mes["systemy"].items():
            x, u = f["realisticky"], f["nejistota"]["obrat"]
            L.append(f"| {M.NAZVY_SYSTEMU.get(s, s)} | {M.kc(x['naklady'])} | {M.kc(x['obrat'])} | "
                     f"{M.kc(x['obrat'] * (1 - u))} – {M.kc(x['obrat'] * (1 + u))} | {M.cislo(x['konverze'])} | "
                     f"{M.pct(M.pno(x['naklady'], x['obrat']))} | {'YoY' if f['yoy'] else 'tempo 8 týdnů'} |")
        if mes["pri_rozpoctu"]:
            p = mes["pri_rozpoctu"]
            L += ["", f"**Při rozpočtu {M.kc(p['naklady'])}** ({M.pct(p['zmena_pct'], True)} proti realistické útratě): "
                      f"obrat kolem {M.kc(p['obrat'])} (pásmo {M.kc(p['obrat_od'])} – {M.kc(p['obrat_do'])}), "
                      f"PNO {M.pct(p['pno'])}. Odhad z modelu klesajícího výnosu, ne slib."]
        L += ["", "### Co když změníte rozpočet", "",
              "| Rozpočet | Náklady | Obrat | PNO celkem | Marginální PNO* |", "|---|---:|---:|---:|---:|"]
        for x, z in mes["zmeny_rozpoctu"].items():
            L.append(f"| {x:+d} % | {M.kc(z['naklady'])} | {M.kc(z['obrat'])} | {M.pct(z['pno'])} | "
                     f"{M.pct(z['marginalni_pno'])} |")
        L += ["", "*Marginální PNO = kolik korun útraty stojí koruna obratu NAVÍC (nebo ušetří při ubrání). "
                  "Model: obrat roste pomaleji než útrata (obrat ~ útrata^b). Je to zjednodušení — skutečný "
                  "strop poznáš až z navýšení po krocích, ne z tabulky.", ""]
    L += ["## Z čeho to vychází", ""]
    for s, f in v["mesice"][0]["systemy"].items():
        tr = ", ".join(f"{NAZVY_METRIK[m]} {M.cislo(t, 2)}×" for m, t in f["trend"].items()) or "–"
        L.append(f"- **{M.NAZVY_SYSTEMU.get(s, s)}:** {f['metoda']}. Okno tempa {f['okno'][0]:%d. %m.} – "
                 f"{f['okno'][1]:%d. %m. %Y}. Meziroční trend: {tr}. Nejistota obratu ±{f['nejistota']['obrat'] * 100:.0f} %. "
                 f"Klesající výnos b = {M.cislo(f['elasticita'], 2)} — {f['elasticita_popis']}.")
    L += ["", "### Posledních 8 týdnů po týdnech (všechny systémy)", ""] + tabulka_tydnu(radky, do)
    L += ["", "### Měsíční řada celé historie", ""] + tabulka_mesicu(radky, do)
    L += ["", "## Nejistota a co forecast neví", "",
          "- Pásmo konzervativní–ambiciózní je odhad z kolísání týdnů (letos proti loňsku), **ne statistický "
          "interval**. Zhruba: realita padne dovnitř, pokud se nestane nic mimořádného.",
          "- Forecast neví o akcích, výpadcích skladu, změně cen, nových kampaních ani změně měření. Ty doplň ručně "
          "(v krycím plánu přes `--udalost`).",
          "- Konverze z posledních ~3 dnů ještě dobíhají (zpoždění atribuce), poslední týden v tabulce může být podhodnocený.",
          "- Obrat je ten, který si připisují reklamní systémy (atribuce platforem), ne účetní tržba e-shopu."]
    if v["varovani"]:
        L += ["", "## Upozornění", ""] + [f"- {x}" for x in v["varovani"]]
    return "\n".join(L).rstrip() + "\n"


def uloz_csv(cesta: Path, v: dict) -> None:
    cesta.parent.mkdir(parents=True, exist_ok=True)
    with cesta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mesic", "system", "scenar", "naklady", "obrat", "konverze", "pno_pct"])
        for mes in v["mesice"]:
            ym = f"{mes['rok']}-{mes['mesic']:02d}"
            for s, fc in mes["systemy"].items():
                for sc, x in fc["scenare"].items():
                    w.writerow([ym, s, sc, round(x["naklady"]), round(x["obrat"]), round(x["konverze"], 1),
                                round(M.pno(x["naklady"], x["obrat"]) or 0, 2)])
            for sc, x in mes["celkem"].items():
                w.writerow([ym, "celkem", sc, round(x["naklady"]), round(x["obrat"]), round(x["konverze"], 1),
                            round(M.pno(x["naklady"], x["obrat"]) or 0, 2)])
            for zm, x in mes["zmeny_rozpoctu"].items():
                w.writerow([ym, "celkem", f"rozpocet_{zm:+d}%", round(x["naklady"]), round(x["obrat"]),
                            round(x["konverze"], 1), round(x["pno"] or 0, 2)])
            if mes["pri_rozpoctu"]:
                x = mes["pri_rozpoctu"]
                w.writerow([ym, "celkem", "pri_zadanem_rozpoctu", round(x["naklady"]), round(x["obrat"]),
                            round(x["konverze"], 1), round(x["pno"] or 0, 2)])


def do_json(v: dict) -> dict:
    def r(x):
        return round(x, 2) if isinstance(x, float) else x
    out = {"do": v["do"].isoformat(), "varovani": v["varovani"], "mesice": []}
    for mes in v["mesice"]:
        out["mesice"].append({
            "mesic": f"{mes['rok']}-{mes['mesic']:02d}",
            "celkem": {sc: {m: r(x) for m, x in d.items()} for sc, d in mes["celkem"].items()},
            "systemy": {s: {"metoda": f["metoda"], "scenare": {sc: {m: r(x) for m, x in d.items()}
                                                                for sc, d in f["scenare"].items()},
                            "nejistota": {m: r(x) for m, x in f["nejistota"].items()},
                            "trend": {m: r(x) for m, x in f["trend"].items()},
                            "elasticita": r(f["elasticita"])}
                        for s, f in mes["systemy"].items()},
            "zmeny_rozpoctu": {f"{k:+d}%": {m: r(x) for m, x in d.items()} for k, d in mes["zmeny_rozpoctu"].items()},
            "pri_rozpoctu": ({m: r(x) for m, x in mes["pri_rozpoctu"].items()} if mes["pri_rozpoctu"] else None),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Forecast útraty a obratu z historie účtu (jen čte)")
    ap.add_argument("--klient", required=True, help="slug klienta (pole \"klient\" v hlidac-ucty.json)")
    ap.add_argument("--mesic", help="první forecastovaný měsíc YYYY-MM (výchozí příští měsíc)")
    ap.add_argument("--mesicu", type=int, default=1, help="kolik měsíců dopředu (výchozí 1)")
    ap.add_argument("--rozpocet", type=float, help="měsíční rozpočet celkem — dopočítá obrat při této útratě")
    ap.add_argument("--csv", type=Path, help="CSV export místo API (datum, system, naklady, obrat, konverze)")
    ap.add_argument("--ucty", type=Path, default=D.VYCHOZI_UCTY)
    ap.add_argument("--do", help="poslední den historie YYYY-MM-DD (výchozí včera / konec dat)")
    ap.add_argument("--json", action="store_true", help="strojový výstup na stdout")
    a = ap.parse_args()

    try:
        dnes = date.today()
        if a.mesic:
            rok, mesic = M.parse_mesic(a.mesic)
        else:
            rok, mesic = M.posun_mesic(dnes.year, dnes.month, 1)
        mesice = [M.posun_mesic(rok, mesic, i) for i in range(max(1, a.mesicu))]
        do = date.fromisoformat(a.do) if a.do else dnes - timedelta(days=1)
        od = date(do.year - 2, do.month, 1) - timedelta(days=31)   # ~25 měsíců: loňsko + 8 týdnů před ním
        radky, varovani = D.nacti_data(a.klient, a.csv, a.ucty, od, do)
        if not radky:
            raise SystemExit("Žádná data — účty nic nevrátily.")
        do = min(do, max(r.datum for r in radky))
        v = spocti_forecast(radky, mesice, do, a.rozpocet)
        v["varovani"] = varovani + v["varovani"]
    except (SystemExit, ValueError) as e:
        print(f"CHYBA: {e}", file=sys.stderr)
        if a.json:
            print(json.dumps({"chyba": str(e)}, ensure_ascii=False))
        return 2

    slozka = ROOT / "plans" / D.slug(a.klient)
    nazev = f"forecast-{mesice[0][0]}-{mesice[0][1]:02d}"
    md = markdown(a.klient, radky, v)
    (slozka).mkdir(parents=True, exist_ok=True)
    (slozka / f"{nazev}.md").write_text(md, encoding="utf-8")
    uloz_csv(slozka / f"{nazev}.csv", v)
    if a.json:
        print(json.dumps(do_json(v), ensure_ascii=False, indent=2))
    else:
        print(md)
    print(f"[uloženo] {(slozka / nazev).relative_to(ROOT)}.md + .csv", file=sys.stderr)
    slabsi = any(not f["yoy"] for mes in v["mesice"] for f in mes["systemy"].values())
    return 1 if slabsi or any("nejde" in x for x in v["varovani"]) else 0


if __name__ == "__main__":
    sys.exit(main())

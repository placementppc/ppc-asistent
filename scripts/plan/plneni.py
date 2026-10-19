#!/usr/bin/env python3
"""Plnění krycího plánu: skutečnost vs. plán k dnešku. Jen čte, nic v účtech nemění.

Použití:
    python3 scripts/plan/plneni.py --klient muj-eshop             # k dnešku (vyhodnotí do včerejška)
    python3 scripts/plan/plneni.py --klient muj-eshop --datum 2026-11-15
    python3 scripts/plan/plneni.py                                # všichni klienti s "kryci-plan" v hlidat
    python3 scripts/plan/plneni.py --klient ukazka --csv scripts/plan/ukazka-data.csv --datum 2026-10-19

Potřebuje krycí plán plans/<klient>/kryci-plan-<YYYY-MM>.csv (kryci_plan.py).
Skutečnost: API přes konektory hlídače (účty z clients/hlidac-ucty.json), nebo --csv.

Pro každý systém i celkem: kumulativ od 1. dne a včerejšek proti plánu, odchylka v %,
prognóza konce měsíce při současném tempu, kolik denně dohnat / ubrat, semafor
(🟢 do ±10 %, 🟡 do ±25 %, 🔴 víc; obrat a konverze nad plánem jsou vždy 🟢) a návrh.
Návrh je JEN návrh — rozpočty v účtech se mění po schválení člověkem.

Report: reports/kryci-plan/<datum>.md (s --klient <datum>-<klient>.md). --json = strojový výstup.
Návratový kód: 0 vše 🟢, 1 něco 🟡, 2 něco 🔴 nebo chyba (chybí plán, účet nešel načíst).
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
from data import _redact, _redact_exc  # noqa: E402  (začernění tokenů v chybách)

ROOT = D.ROOT
MIN_DNI_NA_CERVENOU = 5      # první dny měsíce jsou šum → nejvýš 🟡
MALY_SYSTEM_PODIL = 0.10     # systém pod 10 % rozpočtu klienta → nejvýš 🟡 za klienta
VYCHOZI_MAX_NAVYSENI = 20    # % za krok, když konfigurace neříká jinak (limity.max_navyseni_pct)


def nacti_plan(cesta: Path) -> list[dict]:
    with cesta.open(encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            out.append({"datum": date.fromisoformat(r["datum"]), "system": r["system"],
                        "naklady": float(r["plan_naklady"] or 0), "obrat": float(r["plan_obrat"] or 0),
                        "konverze": float(r["plan_konverze"] or 0)})
    return out


def _soucet(radky, od: date, do: date, system: str | None, metrika: str) -> float:
    return sum((r[metrika] if isinstance(r, dict) else getattr(r, metrika)) for r in radky
               if od <= (r["datum"] if isinstance(r, dict) else r.datum) <= do
               and (system is None or (r["system"] if isinstance(r, dict) else r.system) == system))


def cil_pno(cile: dict, plan_pno: float | None) -> tuple[float | None, str]:
    typ, h = cile.get("typ"), cile.get("hodnota")
    if typ == "pno" and h:
        return float(h), "cíl z konfigurace"
    if typ == "roas" and h:
        return 100 / float(h), "cíl ROAS z konfigurace"
    return plan_pno, "PNO krycího plánu"


def vyhodnot_system(plan: list[dict], skut: list[M.Radek], system: str | None, vcera: date,
                    cile: dict | None = None) -> dict:
    """Čísla plnění pro jeden systém (None = celkem). Čistá funkce nad seznamy."""
    cile = cile or {}
    prvni = date(vcera.year, vcera.month, 1)
    posledni = M.dny_mesice(vcera.year, vcera.month)[-1]
    uplynulo = (vcera - prvni).days + 1
    zbyva = (posledni - vcera).days
    tempo_od = max(prvni, vcera - timedelta(days=6))
    out: dict = {"system": system or "celkem", "uplynulo_dni": uplynulo, "zbyva_dni": zbyva}
    for m in ("naklady", "obrat", "konverze"):
        p_mes = _soucet(plan, prvni, posledni, system, m)
        p_kum = _soucet(plan, prvni, vcera, system, m)
        s_kum = _soucet(skut, prvni, vcera, system, m)
        p_vc = _soucet(plan, vcera, vcera, system, m)
        s_vc = _soucet(skut, vcera, vcera, system, m)
        p_7 = _soucet(plan, tempo_od, vcera, system, m)
        s_7 = _soucet(skut, tempo_od, vcera, system, m)
        out[m] = {"plan_mesic": p_mes, "plan_kum": p_kum, "skut_kum": s_kum,
                  "odchylka_kum_pct": M.odchylka_pct(s_kum, p_kum),
                  "plan_vcera": p_vc, "skut_vcera": s_vc, "odchylka_vcera_pct": M.odchylka_pct(s_vc, p_vc),
                  "prognoza_konec": M.prognoza_konce(s_kum, p_mes - p_kum, s_7, p_7),
                  "denni_korekce": M.denni_korekce(p_kum, s_kum, zbyva),
                  "plan_denne_zbytek": (p_mes - p_kum) / zbyva if zbyva else 0.0}
    n, o = out["naklady"], out["obrat"]
    out["pno_skut"] = M.pno(n["skut_kum"], o["skut_kum"])
    out["pno_plan"] = M.pno(n["plan_mesic"], o["plan_mesic"])
    out["pno_cil"], out["pno_cil_zdroj"] = cil_pno(cile, out["pno_plan"])
    barva = M.horsi(M.semafor(n["odchylka_kum_pct"]), M.semafor(o["odchylka_kum_pct"], jen_dolu=True))
    if uplynulo < MIN_DNI_NA_CERVENOU and barva == "cervena":
        barva = "zluta"
    out["semafor"] = barva
    return out


def navrh(v: dict, max_navyseni_pct: float = VYCHOZI_MAX_NAVYSENI) -> str | None:
    """Jedna věta, co s tím. Jen návrh — nic se neprovádí."""
    nazev = M.NAZVY_SYSTEMU.get(v["system"], "celý účet" if v["system"] == "celkem" else v["system"])
    n, o = v["naklady"], v["obrat"]
    if v["zbyva_dni"] <= 0:
        return None
    kor = n["denni_korekce"]
    denne = n["plan_denne_zbytek"]
    strop = denne * max_navyseni_pct / 100
    krok = min(abs(kor), strop) if strop > 0 else abs(kor)
    pno_s, pno_c = v["pno_skut"], v["pno_cil"]
    pno_txt = f"PNO {M.pct(pno_s)} (cíl {M.pct(pno_c)} — {v['pno_cil_zdroj']})"
    pod_cilem = pno_s is not None and pno_c is not None and pno_s <= pno_c
    if M.semafor(n["odchylka_kum_pct"]) != "zelena":
        if kor > 0:
            if pod_cilem:
                t = (f"{nazev}: zvednout denní rozpočty o ~{M.kc(krok)} (z ~{M.kc(denne)} na ~{M.kc(denne + krok)} "
                     f"denně) — nedočerpává a {pno_txt} je pod cílem.")
                if abs(kor) > strop > 0:
                    t += (f" Celý rozdíl ({M.kc(kor)}/den) najednou nedoženeš bez rozhození biddingu "
                          f"(max +{max_navyseni_pct:.0f} % za krok); zbytek přesunout jinam, nebo nechat nedočerpané.")
                return t
            return (f"{nazev}: nedočerpává, ale {pno_txt} je nad cílem — nepřidávat. Nedočerpaný rozpočet je "
                    f"lepší než drahé konverze. Nejdřív zjistit proč (skill tempo-rozpoctu, anomalie).")
        if pod_cilem:
            return (f"{nazev}: utrácí rychleji než plán, ale {pno_txt} drží. Buď s klientem domluvit vyšší "
                    f"měsíční rozpočet (prognóza {M.kc(n['prognoza_konec'])} proti plánu {M.kc(n['plan_mesic'])}), "
                    f"nebo ubrat ~{M.kc(krok)} denně, ať měsíc vyjde.")
        return (f"{nazev}: ubrat denní rozpočty o ~{M.kc(krok)} — utrácí nad plán a {pno_txt} je nad cílem.")
    if M.semafor(o["odchylka_kum_pct"], jen_dolu=True) != "zelena":
        return (f"{nazev}: čerpá podle plánu, ale obrat zaostává ({M.pct(o['odchylka_kum_pct'], True)}) → PNO roste. "
                f"Rozpočet to nespraví — hledat příčinu (skill anomalie, konverze-vs-ga4); konverze z posledních "
                f"~3 dnů ještě dobíhají.")
    return None


def vyhodnot_klienta(klient: str, vcera: date, csv_cesta: Path | None, ucty_cesta: Path) -> dict:
    ym = f"{vcera.year}-{vcera.month:02d}"
    cesta = ROOT / "plans" / D.slug(klient) / f"kryci-plan-{ym}.csv"
    if not cesta.exists():
        raise SystemExit(f"Chybí krycí plán {cesta.relative_to(ROOT)}. Nejdřív: "
                         f"python3 scripts/plan/kryci_plan.py --klient {D.slug(klient)} --mesic {ym}")
    plan = nacti_plan(cesta)
    prvni = date(vcera.year, vcera.month, 1)
    skut, varovani = D.nacti_data(klient, csv_cesta, ucty_cesta, prvni, vcera, ulozit_historii=False)
    skut = [r for r in skut if prvni <= r.datum <= vcera]
    if not skut:
        varovani.append("Za tento měsíc nepřišla žádná skutečnost (účty nic nevrátily, nebo CSV končí dřív).")
    konf = D.nacti_konfiguraci(ucty_cesta)
    cile = D.cile_systemu(D.ucty_klienta(konf, klient))
    systemy = sorted({r["system"] for r in plan})
    celkovy_rozpocet = _soucet(plan, prvni, M.dny_mesice(vcera.year, vcera.month)[-1], None, "naklady")
    vysl_sys, navrhy = {}, []
    barvy = []
    for s in systemy:
        v = vyhodnot_system(plan, skut, s, vcera, cile.get(s))
        vysl_sys[s] = v
        b = v["semafor"]
        if celkovy_rozpocet and v["naklady"]["plan_mesic"] / celkovy_rozpocet < MALY_SYSTEM_PODIL and b == "cervena":
            b = "zluta"
        barvy.append(b)
        limit = float(((cile.get(s) or {}).get("_limity") or {}).get("max_navyseni_pct") or VYCHOZI_MAX_NAVYSENI)
        t = navrh(v, limit)
        if t:
            navrhy.append(t)
    celkem_cile = {}
    vsechny_pno = {c.get("hodnota") for c in cile.values() if c.get("typ") == "pno"}
    if len(vsechny_pno) == 1:
        celkem_cile = {"typ": "pno", "hodnota": vsechny_pno.pop()}
    celkem = vyhodnot_system(plan, skut, None, vcera, celkem_cile)
    barvy.append(celkem["semafor"])
    if varovani:
        barvy.append("zluta")
    return {"klient": klient, "mesic": ym, "vcera": vcera, "semafor": M.horsi(*barvy),
            "celkem": celkem, "systemy": vysl_sys, "navrhy": navrhy, "varovani": varovani}


# ---------------------------------------------------------------- výstupy
def _radek(nazev: str, v: dict) -> list[str]:
    n, o, k = v["naklady"], v["obrat"], v["konverze"]
    zn = M.SEMAFOR[v["semafor"]]
    return [f"| {zn} {nazev} | {M.kc(n['skut_kum'])} / {M.kc(n['plan_kum'])} ({M.pct(n['odchylka_kum_pct'], True)}) | "
            f"{M.kc(o['skut_kum'])} / {M.kc(o['plan_kum'])} ({M.pct(o['odchylka_kum_pct'], True)}) | "
            f"{M.cislo(k['skut_kum'], 1)} / {M.cislo(k['plan_kum'], 1)} | {M.pct(v['pno_skut'])} / {M.pct(v['pno_cil'])} | "
            f"{M.kc(n['skut_vcera'])} / {M.kc(n['plan_vcera'])} | {M.kc(o['skut_vcera'])} / {M.kc(o['plan_vcera'])} |"]


def markdown_klienta(r: dict) -> list[str]:
    c = r["celkem"]
    n, o = c["naklady"], c["obrat"]
    L = [f"## {M.SEMAFOR[r['semafor']]} {r['klient']} — {r['mesic']}, den {c['uplynulo_dni']} "
         f"(zbývá {c['zbyva_dni']})", "",
         f"Náklady {M.pct(n['odchylka_kum_pct'], True)} proti plánu, obrat {M.pct(o['odchylka_kum_pct'], True)}. "
         f"Při současném tempu konec měsíce: náklady {M.kc(n['prognoza_konec'])} (plán {M.kc(n['plan_mesic'])}), "
         f"obrat {M.kc(o['prognoza_konec'])} (plán {M.kc(o['plan_mesic'])}).", "",
         "| Systém | Náklady skut. / plán (kum.) | Obrat skut. / plán (kum.) | Konverze | PNO skut. / cíl | "
         "Včera náklady | Včera obrat |", "|---|---:|---:|---:|---:|---:|---:|"]
    for s, v in r["systemy"].items():
        L += _radek(M.NAZVY_SYSTEMU.get(s, s), v)
    L += _radek("**Celkem**", c)
    L += ["", "| Systém | Prognóza náklady | Prognóza obrat | Denně dohnat (+) / ubrat (−) náklady | Denně obrat dohnat (+) |",
          "|---|---:|---:|---:|---:|"]
    for s, v in list(r["systemy"].items()) + [("celkem", c)]:
        L.append(f"| {M.NAZVY_SYSTEMU.get(s, s)} | {M.kc(v['naklady']['prognoza_konec'])} | "
                 f"{M.kc(v['obrat']['prognoza_konec'])} | {M.kc(v['naklady']['denni_korekce'])} | "
                 f"{M.kc(v['obrat']['denni_korekce'])} |")
    L += ["", "**Návrh (jen návrh, nic se neprovedlo):**", ""]
    L += [f"- {t}" for t in r["navrhy"]] or ["- Nic neměnit, měsíc jde podle plánu."]
    if r["varovani"]:
        L += [""] + [f"- ⚠️ {x}" for x in r["varovani"]]
    return L + [""]


def do_json(vysledky: list[dict], chyby: list[dict], datum: date) -> dict:
    def ciste(x):
        if isinstance(x, dict):
            return {k: ciste(v) for k, v in x.items()}
        if isinstance(x, list):
            return [ciste(v) for v in x]
        if isinstance(x, float):
            return None if x != x or x in (float("inf"), float("-inf")) else round(x, 2)
        if isinstance(x, date):
            return x.isoformat()
        return x
    return {"datum": datum.isoformat(), "klienti": ciste(vysledky), "chyby": chyby}


def main() -> int:
    ap = argparse.ArgumentParser(description="Skutečnost vs. krycí plán (jen čte)")
    ap.add_argument("--klient", help="slug klienta; bez něj všichni s \"kryci-plan\" v hlidat")
    ap.add_argument("--datum", help="den hodnocení YYYY-MM-DD (vyhodnotí se do předchozího dne; výchozí dnes)")
    ap.add_argument("--csv", type=Path, help="CSV se skutečností (datum, system, naklady, obrat, konverze)")
    ap.add_argument("--ucty", type=Path, default=D.VYCHOZI_UCTY)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    datum = date.fromisoformat(a.datum) if a.datum else date.today()
    vcera = datum - timedelta(days=1)
    if a.klient:
        klienti = [a.klient]
    else:
        if a.csv:
            print("CHYBA: --csv jde jen s --klient.", file=sys.stderr)
            return 2
        klienti = D.klienti_s_kryci_planem(D.nacti_konfiguraci(a.ucty))
        if not klienti:
            print(f"CHYBA: v {a.ucty} není žádný účet s \"kryci-plan\" v poli hlidat. Použij --klient.", file=sys.stderr)
            return 2

    vysledky, chyby = [], []
    for k in klienti:
        try:
            vysledky.append(vyhodnot_klienta(k, vcera, a.csv, a.ucty))
        except SystemExit as e:
            chyby.append({"klient": k, "chyba": _redact(e)})
        except Exception as e:      # jeden klient nesmí shodit ostatní
            chyby.append({"klient": k, "chyba": _redact_exc(e)})

    barvy = [r["semafor"] for r in vysledky] + ["cervena"] * len(chyby)
    celkova = M.horsi(*barvy) if barvy else "zelena"
    L = [f"# Krycí plán — plnění k {datum:%d. %m. %Y} (data do {vcera:%d. %m.})", "",
         f"Celkově {M.SEMAFOR[celkova]} · " + (", ".join(f"{M.SEMAFOR[r['semafor']]} {r['klient']}" for r in vysledky) or "–"), ""]
    for r in sorted(vysledky, key=lambda x: -M.PORADI[x["semafor"]]):
        L += markdown_klienta(r)
    for ch in chyby:
        L += [f"## 🔴 {ch['klient']}", "", f"- {ch['chyba']}", ""]
    L += ["Semafor: 🟢 do ±10 % od plánu, 🟡 do ±25 %, 🔴 víc (obrat nad plánem je vždy 🟢; první 4 dny měsíce "
          "nejvýš 🟡). Konverze a obrat z posledních ~3 dnů ještě dobíhají. Prognóza = skutečnost + zbytek plánu "
          "× tempo posledních 7 dnů proti plánu.",
          "Zápis rozpočtů do účtů jen po schválení (skill kryci-plan, sekce Změny v účtu)."]
    text = "\n".join(L).rstrip() + "\n"

    nazev = f"{datum.isoformat()}{'-' + D.slug(a.klient) if a.klient else ''}.md"
    out = ROOT / "reports" / "kryci-plan" / nazev
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    if a.json:
        print(json.dumps(do_json(vysledky, chyby, datum), ensure_ascii=False, indent=2))
    else:
        print(text)
    print(f"[uloženo] {out.relative_to(ROOT)}", file=sys.stderr)
    return M.PORADI[celkova]


if __name__ == "__main__":
    sys.exit(main())

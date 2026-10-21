"""Plán Black Friday a Vánoc po týdnech: forecast listopadu a prosince rozpadnutý podle loňské sezóny.

Jen čte. Navazuje na `forecast.py` (stejný výpočet měsíců) a přidává:
- týdenní rozpad listopadu a prosince podle toho, jak loni běžela sezóna
  (zarovnáno na den Black Friday, prosinec podle kalendáře),
- fáze sezóny s úkoly a kreativami (co spustit, kdy přidat, kdy ubrat),
- kontrolu proti cíli (PNO) a zadanému rozpočtu,
- výstup MD + HTML + PDF (PDF přes Chrome/Edge v režimu bez okna, když je v počítači).

Zdroj tvaru sezóny (v tomhle pořadí):
1. loňský listopad a prosinec z reklamních systémů (API nebo historie.csv),
2. loňský listopad a prosinec z GA4 (`--ga4`, tržby celého e-shopu),
3. obecný profil sezóny (když loňská data nejsou; ve výstupu je to napsané).

Zadání z rozhovoru (cíle, akce, grafika, poslední doručení…) bere z JSON `--zadani`,
vzor: scripts/plan/bf-zadani.example.json.

Použití:
  python3 scripts/plan/bf_plan.py --klient muj-eshop                      # API
  python3 scripts/plan/bf_plan.py --klient muj-eshop --csv plans/muj-eshop/historie.csv \
      --ga4 plans/muj-eshop/ga4.csv --zadani plans/muj-eshop/bf-zadani.json
  python3 scripts/plan/bf_plan.py --klient ukazka --csv scripts/plan/ukazka-data.csv   # vyzkoušení

Výstup: plans/<klient>/bf-plan-<rok>.md + .html (+ .pdf). Návratový kód 0 OK, 1 plán je,
ale bez loňské sezóny (obecný profil), 2 chyba.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import forecast as F  # noqa: E402
import model as M  # noqa: E402

ROOT = D.ROOT
SCENARE = ("konzervativni", "realisticky", "ambiciozni")


def black_friday(rok: int) -> date:
    """Pátek po čtvrtém listopadovém čtvrtku (Den díkůvzdání)."""
    prvni = date(rok, 11, 1)
    ctvrtek = prvni + timedelta(days=(3 - prvni.weekday()) % 7 + 21)
    return ctvrtek + timedelta(days=1)


# ---------------------------------------------------------------- fáze sezóny
def faze(d: date, bf: date, posledni_doruceni: date) -> str:
    o = (d - bf).days
    if d.month == 12 and d > posledni_doruceni:
        return "po_doruceni" if d.day <= 24 else "po_vanocich"
    if o <= -25:
        return "priprava"
    if o <= -8:
        return "rozjezd"
    if o <= -1:
        return "black_week"
    if o <= 3:
        return "bf_vikend"
    return "vanoce"


FAZE = {
    "priprava": {
        "nazev": "Příprava",
        "co": ["Otestujte 2–3 nové hooky a kreativy teď, ať na Black Friday víte, co funguje.",
               "Zkontrolujte měření (nákupy v GA4 i v systémech) a feed produktů.",
               "Plňte publika: newsletter, remarketing, návštěvníci top produktů."],
        "kreativy": "Běžné kreativy + test nových hooků. Žádné „BLACK FRIDAY“ ještě ne.",
        "rozpocet": "Běžný rozpočet, vyhodnocujte testy po 7 dnech.",
    },
    "rozjezd": {
        "nazev": "Rozjezd",
        "co": ["Teaser akce a sběr kontaktů (early access pro newsletter).",
               "Připravte a nechte schválit všechny BF kreativy a texty dopředu.",
               "Navyšujte rozpočty po krocích 15–30 % u kampaní, které drží cíl."],
        "kreativy": "Teasery: „Black Friday u nás začne dřív“, early access, odpočet.",
        "rozpocet": "Mírně nad běžným, navyšujte jen tam, kde je PNO v cíli.",
    },
    "black_week": {
        "nazev": "Black Week",
        "co": ["Spusťte nabídku a kreativy s konkrétní nabídkou a termínem konce.",
               "Zpřísněte hlídání: denní kontrola útraty, zamítnutých reklam a konverzí.",
               "Remarketing na lidi z rozjezdu, vyšší rozpočet na nejlepší produkty."],
        "kreativy": "Konkrétní nabídka (co, o kolik, do kdy). Problém zákazníka, ne jen „sleva“.",
        "rozpocet": "Výrazně nad běžným, podle tabulky níž.",
    },
    "bf_vikend": {
        "nazev": "Black Friday až Cyber Monday",
        "co": ["Hlídejte rozpočty i večer a o víkendu, ať nejlepší kampaně nedojedou v půlce dne.",
               "Kde výkon drží cíl, přidejte (hlídač akcí navrhne kde).",
               "V neděli večer připravte Cyber Monday a poslední den akce."],
        "kreativy": "Odpočet, „poslední den“, Stories a krátká videa.",
        "rozpocet": "Vrchol sezóny. Rozpočty nastavte předem s rezervou.",
    },
    "vanoce": {
        "nazev": "Vánoční nákupy",
        "co": ["Přepněte z „slevy“ na „dárek“: tipy na dárek podle ceny a pro koho.",
               "Komunikujte termín doručení do Vánoc, hlídejte sklad u top produktů.",
               "Pozor na únavu publika: obměňte kreativy po Black Friday."],
        "kreativy": "Dárkové kreativy, „doručíme do Vánoc“, sady a balení.",
        "rozpocet": "Nad běžným až do posledního dne doručení.",
    },
    "po_doruceni": {
        "nazev": "Po posledním doručení",
        "co": ["Ubírejte rozpočty na produkty, které už nedorazí.",
               "Propagujte osobní odběr, výdejní místa a dárkové poukazy (e-mailem hned)."],
        "kreativy": "Dárkový poukaz, osobní odběr, „stihnete ještě dnes“.",
        "rozpocet": "Ubrat. Výkon padá i při stejné útratě.",
    },
    "po_vanocich": {
        "nazev": "Po Vánocích",
        "co": ["Povánoční výprodej a nákupy pro sebe, prodej za poukazy.",
               "Vyhodnoťte sezónu, ať máte data na příští rok."],
        "kreativy": "Výprodej, „utraťte poukaz“, novinky na nový rok.",
        "rozpocet": "Pod běžným, mezi svátky lidé nakupují méně.",
    },
}
PORADI_FAZI = list(FAZE)

# Obecný profil (násobek běžného dne), když nejsou loňská data. Hrubý odhad, ne měření.
PROFIL = {"priprava": 1.0, "rozjezd": 1.1, "black_week": 1.35, "vanoce": 1.25,
          "po_doruceni": 0.7, "po_vanocich": 0.5}
PROFIL_BF = {0: 2.6, 1: 1.8, 2: 1.6, 3: 1.9}      # pátek, so, ne, Cyber Monday


def loni_den(d: date, bf: date, bf_loni: date) -> date:
    """Den loni, se kterým se den letos srovnává: do týdne po Cyber Monday podle BF, dál podle kalendáře."""
    if d <= bf + timedelta(days=10):
        return bf_loni + (d - bf)
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d - timedelta(days=365)


def vahy_dnu_sezony(dny: dict[date, M.Radek] | None, rok: int, bf: date, posl: date,
                    metrika: str) -> tuple[dict[date, float], str]:
    """Váha každého dne listopadu a prosince. Vrací (váhy, zdroj)."""
    sezona = [date(rok, 11, 1) + timedelta(days=i) for i in range(61)]
    bf_loni = black_friday(rok - 1)
    if dny:
        mapa = {d: loni_den(d, bf, bf_loni) for d in sezona}
        pokryti = sum(1 for x in mapa.values() if x in dny) / len(mapa)
        if pokryti >= 0.9:
            hodnoty = [M.hodnota(dny[x], metrika) for x in mapa.values() if x in dny]
            nahrada = sum(hodnoty) / len(hodnoty) if hodnoty else 1.0
            return ({d: (M.hodnota(dny[x], metrika) if x in dny else nahrada) for d, x in mapa.items()},
                    "loni")
    vahy = {}
    for d in sezona:
        o = (d - bf).days
        vahy[d] = PROFIL_BF[o] if o in PROFIL_BF else PROFIL[faze(d, bf, posl)]
        if d.month == 12 and 24 <= d.day <= 26:
            vahy[d] = 0.3
    return vahy, "profil"


# ---------------------------------------------------------------- výpočet
def sestav(radky: list[M.Radek], ga4: list[M.Radek], rok: int, do: date, zadani: dict) -> dict:
    bf = date.fromisoformat(zadani["black_friday"]) if zadani.get("black_friday") else black_friday(rok)
    posl = (date.fromisoformat(zadani["posledni_doruceni"]) if zadani.get("posledni_doruceni")
            else date(rok, 12, 18))
    rozpocty = zadani.get("rozpocet") or {}
    varovani: list[str] = []

    mesice = {}
    for mes in (11, 12):
        klic = f"{rok}-{mes:02d}"
        roz = rozpocty.get(klic)
        v = F.spocti_forecast(radky, [(rok, mes)], do, float(roz) if roz else None)
        varovani += [x for x in v["varovani"] if x not in varovani]
        m = v["mesice"][0]
        cisla = {sc: dict(m["celkem"][sc]) for sc in SCENARE}
        if m["pri_rozpoctu"]:                     # zadaný rozpočet: posun všech scénářů na tuhle útratu
            pr = m["pri_rozpoctu"]
            r = cisla["realisticky"]
            for sc in SCENARE:
                k = cisla[sc]["obrat"] / r["obrat"] if r["obrat"] else 1
                cisla[sc] = {"naklady": pr["naklady"], "obrat": pr["obrat"] * k, "konverze": pr["konverze"] * k}
        mesice[mes] = {"cisla": cisla, "metoda": sorted({f["metoda"] for f in m["systemy"].values()}),
                       "rozpocet": roz, "zmeny": m["zmeny_rozpoctu"]}

    reklamy = M.po_dnech([r for r in radky if r.system != "ga4"])
    vahy_n, zdroj_n = vahy_dnu_sezony(reklamy, rok, bf, posl, "naklady")
    vahy_o, zdroj_o = vahy_dnu_sezony(reklamy, rok, bf, posl, "obrat")
    if zdroj_o == "profil" and ga4:
        vahy_o, zdroj_o = vahy_dnu_sezony(M.po_dnech(ga4), rok, bf, posl, "obrat")
        if zdroj_o == "loni":
            zdroj_o = "ga4"
            if zdroj_n == "profil":               # tvar útraty podle GA4 je lepší než obecný profil
                vahy_n, zdroj_n = vahy_o, "ga4"
    zdroj = {"loni": "loňská sezóna v reklamních systémech", "ga4": "loňská sezóna v GA4 (tržby e-shopu)",
             "profil": "obecný profil sezóny (loňská data chybí)"}
    if zdroj_o == "profil":
        varovani.append("Tvar sezóny je obecný profil, ne vaše loňská data. Týdny ber jako orientační; "
                        "doplň loňský listopad a prosinec (export z Ads, Mety nebo GA4).")

    # rozpad měsíců na dny a pak na týdny
    dny_plan: dict[date, dict] = {}
    for mes, info in mesice.items():
        dny_m = [d for d in vahy_n if d.month == mes]
        sn = sum(vahy_n[d] for d in dny_m) or 1
        so = sum(vahy_o[d] for d in dny_m) or 1
        for d in dny_m:
            dny_plan[d] = {sc: {"naklady": info["cisla"][sc]["naklady"] * vahy_n[d] / sn,
                                "obrat": info["cisla"][sc]["obrat"] * vahy_o[d] / so,
                                "konverze": info["cisla"][sc]["konverze"] * vahy_o[d] / so}
                           for sc in SCENARE}
    tydny = []
    d = min(dny_plan)
    while d <= max(dny_plan):
        konec = d + timedelta(days=6 - d.weekday())
        dny_t = [x for x in sorted(dny_plan) if d <= x <= konec]
        souhrn = {sc: {m: sum(dny_plan[x][sc][m] for x in dny_t) for m in ("naklady", "obrat", "konverze")}
                  for sc in SCENARE}
        tydny.append({"dny": dny_t, **souhrn})
        d = konec + timedelta(days=1)
    if len(tydny) > 1 and len(tydny[0]["dny"]) < 3:     # useknutý první týden (1. 11. v neděli) přidej k dalšímu
        prvni = tydny.pop(0)
        tydny[0]["dny"] = prvni["dny"] + tydny[0]["dny"]
        for sc in SCENARE:
            for m in ("naklady", "obrat", "konverze"):
                tydny[0][sc][m] += prvni[sc][m]
    for t in tydny:
        f_t = [faze(x, bf, posl) for x in t["dny"]]
        t["od"], t["do"] = t["dny"][0], t["dny"][-1]
        t["faze"] = ("bf_vikend" if bf in t["dny"]
                     else max(set(f_t), key=lambda f: (f_t.count(f), PORADI_FAZI.index(f))))
        t["cyber_monday"] = bf + timedelta(days=3) in t["dny"] and bf not in t["dny"]
        del t["dny"]

    cil_pno = (zadani.get("cil") or {}).get("pno")
    for t in tydny:
        r = t["realisticky"]
        t["pno"] = M.pno(r["naklady"], r["obrat"])
        t["nad_cilem"] = bool(cil_pno and t["pno"] and t["pno"] > cil_pno)
    return {"rok": rok, "bf": bf, "posledni_doruceni": posl, "mesice": mesice, "tydny": tydny,
            "zdroj": zdroj[zdroj_o], "obecny_profil": zdroj_o == "profil", "varovani": varovani,
            "zadani": zadani, "do": do, "cil_pno": cil_pno}


# ---------------------------------------------------------------- výstupy
def _datum(d: date) -> str:
    return f"{d.day}. {d.month}."


def markdown(klient: str, p: dict) -> str:
    z = p["zadani"]
    nazev = z.get("klient_nazev") or klient
    out = [f"# Plán Black Friday a Vánoc {p['rok']}: {nazev}", "",
           f"Black Friday **{_datum(p['bf'])}**, Cyber Monday **{_datum(p['bf'] + timedelta(days=3))}**, "
           f"poslední doručení do Vánoc **{_datum(p['posledni_doruceni'])}** · "
           f"Data do {_datum(p['do'])} {p['do'].year}. Tvar sezóny: {p['zdroj']}.", ""]
    nalez = [("Cíl", _cil_text(z)), ("Akce", _akce_text(z)), ("Top produkty", ", ".join(z.get("top_produkty") or [])),
             ("Kreativy a grafika", z.get("grafika")), ("Loni", z.get("loni")), ("Poznámky", z.get("poznamky"))]
    if any(v for _, v in nalez):
        out += ["## Zadání", ""] + [f"- **{k}:** {v}" for k, v in nalez if v] + [""]
    out += ["## Měsíce", "", "| Měsíc | Útrata | Obrat konzervativně | Obrat realisticky | Obrat ambiciózně | PNO |",
            "|---|---:|---:|---:|---:|---:|"]
    for mes, info in p["mesice"].items():
        c = info["cisla"]
        out.append(f"| {F.nazev_mesice(p['rok'], mes)} | {M.kc(c['realisticky']['naklady'])} | "
                   f"{M.kc(c['konzervativni']['obrat'])} | **{M.kc(c['realisticky']['obrat'])}** | "
                   f"{M.kc(c['ambiciozni']['obrat'])} | {M.pct(M.pno(c['realisticky']['naklady'], c['realisticky']['obrat']))} |")
    out += ["", "## Týden po týdnu", "",
            "| Týden | Fáze | Útrata | Obrat (realisticky) | PNO | Konverze |", "|---|---|---:|---:|---:|---:|"]
    for t in p["tydny"]:
        r = t["realisticky"]
        znak = " ⚠️" if t["nad_cilem"] else ""
        nazev_faze = "Black Week a Black Friday" if t["faze"] == "bf_vikend" else FAZE[t["faze"]]["nazev"]
        if t["cyber_monday"]:
            nazev_faze = "Cyber Monday, pak " + nazev_faze.lower()
        out.append(f"| {_datum(t['od'])}–{_datum(t['do'])} | {nazev_faze} | {M.kc(r['naklady'])} | "
                   f"{M.kc(r['obrat'])} | {M.pct(t['pno'])}{znak} | {M.cislo(r['konverze'])} |")
    if p["cil_pno"]:
        out += ["", f"⚠️ = týden, kde odhad PNO přesahuje cíl {M.pct(p['cil_pno'])}. Tam nenavyšovat naslepo."]
    out += ["", "## Co dělat v které fázi", ""]
    for f in PORADI_FAZI:
        info = FAZE[f]
        out += [f"### {info['nazev']}", ""] + [f"- {x}" for x in info["co"]] + \
               [f"- **Kreativy:** {info['kreativy']}", f"- **Rozpočet:** {info['rozpocet']}", ""]
    out += ["## Na co si dát pozor", "",
            "- Je to odhad z historie, ne slib. Pásmo konzervativně–ambiciózně není statistický interval.",
            "- Forecast neví o slevách, skladu, cenách ani nových kampaních, pokud nejsou v zadání.",
            "- Obrat je to, co si připisují reklamní systémy, ne účetní tržba e-shopu.",
            "- Rozpočty se podle plánu v účtech nemění samy. Navyšujte po krocích a vyhodnocujte."]
    out += [f"- {v}" for v in p["varovani"]]
    return "\n".join(out) + "\n"


def _cil_text(z: dict) -> str:
    c = z.get("cil") or {}
    casti = []
    if c.get("pno"):
        casti.append(f"PNO do {M.pct(c['pno'])}")
    if c.get("obrat"):
        casti.append(f"obrat {M.kc(c['obrat'])}")
    if z.get("marze_pct"):
        casti.append(f"marže {M.pct(z['marze_pct'])}")
    return ", ".join(casti)


def _akce_text(z: dict) -> str:
    a = z.get("akce") or {}
    if not a:
        return ""
    termin = (f" ({_datum(date.fromisoformat(a['od']))} až {_datum(date.fromisoformat(a['do']))})"
              if a.get("od") and a.get("do") else "")
    return f"{a.get('popis', '')}{termin}".strip()


def _graf_svg(tydny: list[dict]) -> str:
    """Sloupce útraty a obratu po týdnech, ať je na první pohled vidět vrchol sezóny."""
    w, h, okraj = 720, 220, 30
    maxv = max(t["realisticky"]["obrat"] for t in tydny) or 1
    sirka = (w - 2 * okraj) / len(tydny)
    prvky = []
    for i, t in enumerate(tydny):
        x = okraj + i * sirka
        for j, (m, barva) in enumerate((("naklady", "#c7b4ed"), ("obrat", "#5924c6"))):
            v = t["realisticky"][m]
            vys = (h - 2 * okraj) * v / maxv
            prvky.append(f'<rect x="{x + 4 + j * (sirka - 8) / 2:.1f}" y="{h - okraj - vys:.1f}" '
                         f'width="{(sirka - 8) / 2 - 1:.1f}" height="{vys:.1f}" rx="2" fill="{barva}">'
                         f'<title>{html.escape(_datum(t["od"]))}: {m} {M.kc(v)}</title></rect>')
        prvky.append(f'<text x="{x + sirka / 2:.1f}" y="{h - 10}" font-size="10" text-anchor="middle" '
                     f'fill="#5b5670">{_datum(t["od"])}</text>')
    legenda = ('<rect x="30" y="4" width="10" height="10" fill="#c7b4ed"/><text x="44" y="13" font-size="11" '
               'fill="#16121f">útrata</text><rect x="100" y="4" width="10" height="10" fill="#5924c6"/>'
               '<text x="114" y="13" font-size="11" fill="#16121f">obrat (realisticky)</text>')
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Útrata a obrat po týdnech" '
            f'style="width:100%;height:auto">{legenda}{"".join(prvky)}</svg>')


def html_dokument(klient: str, p: dict, md: str) -> str:
    """Jednoduché HTML k tisku do PDF. Tabulky a odrážky z MD převádí ručně (bez knihoven)."""
    telo, v_tabulce, v_seznamu = [], False, False
    for radek in md.splitlines():
        def inline(t: str) -> str:
            t = html.escape(t)
            casti = t.split("**")
            return "".join(f"<strong>{c}</strong>" if i % 2 else c for i, c in enumerate(casti))
        if radek.startswith("|"):
            bunky = [c.strip() for c in radek.strip("|").split("|")]
            if set("".join(bunky)) <= set("-:"):
                continue
            if not v_tabulce:
                telo.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in bunky) + "</tr>")
                v_tabulce = True
            else:
                tr = ' class="varovani"' if "⚠️" in radek else ""
                telo.append(f"<tr{tr}>" + "".join(
                    f'<td class="cislo">{inline(c)}</td>' if re.search(r"\d.*(Kč|%)|^\*?\*?[\d ]+(,\d+)?$", c)
                    else f"<td>{inline(c)}</td>" for c in bunky) + "</tr>")
            continue
        if v_tabulce:
            telo.append("</table>")
            v_tabulce = False
        if radek.startswith("- "):
            if not v_seznamu:
                telo.append("<ul>")
                v_seznamu = True
            telo.append(f"<li>{inline(radek[2:])}</li>")
            continue
        if v_seznamu:
            telo.append("</ul>")
            v_seznamu = False
        if radek.startswith("### "):
            telo.append(f"<h3>{inline(radek[4:])}</h3>")
        elif radek.startswith("## "):
            telo.append(f"<h2>{inline(radek[3:])}</h2>")
            if radek[3:] == "Týden po týdnu":
                telo.append(_graf_svg(p["tydny"]))
        elif radek.startswith("# "):
            telo.append(f"<h1>{inline(radek[2:])}</h1>")
        elif radek.strip():
            telo.append(f"<p>{inline(radek)}</p>")
    if v_tabulce:
        telo.append("</table>")
    if v_seznamu:
        telo.append("</ul>")
    return f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>{html.escape(md.splitlines()[0][2:])}</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: Montserrat, "Segoe UI", Helvetica, Arial, sans-serif; color: #16121f; font-size: 11pt;
       line-height: 1.45; max-width: 820px; margin: 24px auto; padding: 0 16px; background: #fff; }}
h1 {{ color: #5924c6; font-size: 22pt; margin: 0 0 8px; letter-spacing: -0.01em; }}
h2 {{ color: #5924c6; font-size: 14pt; margin: 22px 0 8px; border-bottom: 3px solid #f3f3ff; padding-bottom: 4px; }}
h3 {{ color: #3e178f; font-size: 11.5pt; margin: 14px 0 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9.5pt; }}
th {{ background: #5924c6; color: #fff; text-align: left; padding: 5px 7px; }}
td {{ padding: 4px 7px; border-bottom: 1px solid #e9d2f2; }}
td.cislo {{ text-align: right; white-space: nowrap; }} th:not(:first-child) {{ text-align: right; }}
th:nth-child(2):not(:last-child) {{ text-align: left; }}
tr.varovani td {{ background: #fff0fd; }}
ul {{ margin: 4px 0 8px 18px; padding: 0; }}
h2, h3 {{ break-after: avoid; }} table, svg {{ break-inside: avoid; }}
footer {{ margin-top: 28px; color: #5b5670; font-size: 8.5pt; }}
</style></head><body>
{chr(10).join(telo)}
<footer>Vytvořeno v PPC asistentovi z webináře PLACEMENT.cz · vzdelavani.placement.cz</footer>
</body></html>"""


def najdi_prohlizec() -> str | None:
    kandidati = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for k in kandidati:
        if Path(k).exists():
            return k
    for jmeno in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        if shutil.which(jmeno):
            return shutil.which(jmeno)
    return None


def uloz_pdf(html_cesta: Path, pdf_cesta: Path) -> bool:
    prohlizec = najdi_prohlizec()
    if not prohlizec:
        return False
    try:
        subprocess.run([prohlizec, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_cesta}", html_cesta.resolve().as_uri()],
                       check=True, capture_output=True, timeout=90)
    except (subprocess.SubprocessError, OSError):
        return False
    return pdf_cesta.exists() and pdf_cesta.stat().st_size > 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Plán Black Friday a Vánoc po týdnech (jen čte)")
    ap.add_argument("--klient", required=True)
    ap.add_argument("--csv", type=Path, help="historie reklamních systémů (datum, system, naklady, obrat, konverze)")
    ap.add_argument("--ga4", type=Path, help="tržby e-shopu z GA4 po dnech (z exporty.py → plans/<klient>/ga4.csv)")
    ap.add_argument("--zadani", type=Path, help="JSON s odpověďmi z rozhovoru (vzor bf-zadani.example.json)")
    ap.add_argument("--rok", type=int, help="rok sezóny (výchozí letošní)")
    ap.add_argument("--ucty", type=Path, default=D.VYCHOZI_UCTY)
    ap.add_argument("--do", help="poslední den historie YYYY-MM-DD (výchozí včera / konec dat)")
    ap.add_argument("--bez-pdf", action="store_true")
    a = ap.parse_args()
    try:
        zadani = json.loads(a.zadani.read_text(encoding="utf-8")) if a.zadani else {}
        dnes = date.today()
        rok = a.rok or dnes.year
        do = date.fromisoformat(a.do) if a.do else dnes - timedelta(days=1)
        od = date(do.year - 2, do.month, 1) - timedelta(days=31)
        radky, varovani = D.nacti_data(a.klient, a.csv, a.ucty, od, do)
        radky = [r for r in radky if r.system != "ga4"]
        if not radky:
            raise SystemExit("Žádná data z reklamních systémů.")
        do = min(do, max(r.datum for r in radky))
        ga4 = D.nacti_csv(a.ga4) if a.ga4 else []
        p = sestav(radky, ga4, rok, do, zadani)
        p["varovani"] = varovani + p["varovani"]
    except (SystemExit, ValueError, json.JSONDecodeError) as e:
        print(f"CHYBA: {e}", file=sys.stderr)
        return 2

    slozka = ROOT / "plans" / D.slug(a.klient)
    slozka.mkdir(parents=True, exist_ok=True)
    zaklad = slozka / f"bf-plan-{rok}"
    md = markdown(a.klient, p)
    zaklad.with_suffix(".md").write_text(md, encoding="utf-8")
    zaklad.with_suffix(".html").write_text(html_dokument(a.klient, p, md), encoding="utf-8")
    print(md)
    hotovo = [".md", ".html"]
    if not a.bez_pdf:
        if uloz_pdf(zaklad.with_suffix(".html"), zaklad.with_suffix(".pdf")):
            hotovo.append(".pdf")
        else:
            print("PDF se nepovedlo (nenašel jsem Chrome ani Edge). Otevři .html a dej Tisk → Uložit jako PDF.",
                  file=sys.stderr)
    print(f"[uloženo] {zaklad.relative_to(ROOT)} {' + '.join(hotovo)}", file=sys.stderr)
    return 1 if p["obecny_profil"] else 0


if __name__ == "__main__":
    sys.exit(main())

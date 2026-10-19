"""Pravidla hlídače cílů — čistá logika bez API, ať se dá otestovat.

Otázka hlídače: „Plní účet od poslední změny cíl klienta?“ Ne „funguje účet?“.
Okno od změny je krátké okno a slouží jen k vyhodnocení té změny (CLAUDE.md 4b).
Proto ke každému verdiktu přikládá kontext 8 týdnů po týdnech a návrh vždy začíná
ověřením příčiny, ne zásahem.

Prahy vychází z knowledge/vyhodnoceni-zmen.md a skillu perf:
- učící fáze po zásahu do biddingu/rozpočtu 7–14 dní → dřív než za 7 dní nehodnotit,
- tCPA ≥ 30 konverzí po změně, tROAS ideálně ≥ 50 → pod 30 konverzí jen „předběžně“,
- vzorek ~100 prokliků, jinak šum.
"""
from __future__ import annotations

import calendar
import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from kontroly import Den, _fmt

ZELENA, ZLUTA, CERVENA, BILA = "zelena", "zluta", "cervena", "bila"
IKONY = {ZELENA: "🟢", ZLUTA: "🟡", CERVENA: "🔴", BILA: "⚪"}
_PORADI = {ZELENA: 0, BILA: 1, ZLUTA: 2, CERVENA: 3}

PRAHY = {
    "min_dni": 7,             # učící fáze — dřív nehodnotit
    "min_konverzi": 30,       # pod tím jen předběžný odhad
    "min_prokliku": 100,      # vzorek pro konverzní poměr
    "tolerance": 0.10,        # do 10 % od cíle = hraničně
    "vychozi_okno": 28,       # když není známá poslední změna
    "max_okno": 90,           # starší změnu hodnotit jen za posledních 90 dní
    "cpa_bez_konverzi_nasobek": 3.0,  # utratil 3× cílové CPA bez konverze = 🔴
    "tempo_min_dni": 5,       # tempo měsíce hodnotit od 5. dne
    "tempo_precerpa": 1.10,
    "tempo_precerpa_cervena": 1.25,
    "tempo_nedocerpa": 0.85,
    "rezerva_rust": 0.20,     # o 20 % lepší než cíl = prostor pro růst
}

NAZVY_KPI = {"pno": "PNO", "roas": "ROAS", "cpa": "CPA", "konverze": "Konverze"}


def horsi(a: str, b: str) -> str:
    return a if _PORADI[a] >= _PORADI[b] else b


# ------------------------------------------------------------------ poslední změna
_RADEK_DATUM = re.compile(r"^#{2,3}\s+(\d{4}-\d{2}-\d{2})\b")


def najdi_posledni_zmenu(text_md: str, dnes: date) -> str | None:
    """Nejnovější datum změny z changelogu klientského souboru.

    Hledá řádky `### YYYY-MM-DD …` (formát šablony clients/_TEMPLATE.md) nebo `## YYYY-MM-DD`.
    Když soubor má sekci „Changelog“, bere jen ji — v sekci A/B testů jsou taky data
    s `###` a to nejsou změny účtu. Data v budoucnosti a zástupné „YYYY-MM-DD“ ignoruje.
    """
    radky = text_md.splitlines()
    zacatek = next((i for i, r in enumerate(radky)
                    if r.startswith("## ") and "changelog" in r.lower()), None)
    if zacatek is not None:
        konec = next((i for i in range(zacatek + 1, len(radky))
                      if radky[i].startswith("## ") and not _RADEK_DATUM.match(radky[i])), len(radky))
        radky = radky[zacatek + 1:konec]
    data = []
    for r in radky:
        m = _RADEK_DATUM.match(r.strip())
        if not m:
            continue
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if d <= dnes:
            data.append(d)
    return max(data).isoformat() if data else None


@dataclass
class Okno:
    od: str            # první den po změně (včetně)
    do: str            # poslední celý den (včera)
    dni: int
    zmena: str | None  # datum změny, když je známé
    zdroj: str         # "config" | "changelog" | "výchozí"
    pred_od: str
    pred_do: str
    zkraceno: bool = False


def okno_od_zmeny(posledni_zmena: str | None, zdroj: str, vcera: date) -> Okno:
    """Okno od změny do včerejška a stejně dlouhé období těsně před změnou.

    Den změny se do okna počítá (změna se obvykle dělá přes den a ten den už ji ovlivní).
    """
    p = PRAHY
    if posledni_zmena:
        od = date.fromisoformat(posledni_zmena)
    else:
        od = vcera - timedelta(days=p["vychozi_okno"] - 1)
        zdroj = "výchozí"
    zkraceno = False
    if (vcera - od).days + 1 > p["max_okno"]:
        od = vcera - timedelta(days=p["max_okno"] - 1)
        zkraceno = True
    dni = max((vcera - od).days + 1, 0)
    pred_do = od - timedelta(days=1)
    pred_od = pred_do - timedelta(days=max(dni, 1) - 1)
    return Okno(od.isoformat(), vcera.isoformat(), dni, posledni_zmena, zdroj,
                pred_od.isoformat(), pred_do.isoformat(), zkraceno)


# ------------------------------------------------------------------ výpočty
def soucet(dny: list[Den], od: str, do: str) -> dict:
    vyber = [d for d in dny if od <= d.datum <= do]
    return {
        "utrata": sum(d.utrata for d in vyber),
        "konverze": sum(d.konverze for d in vyber),
        "hodnota": sum(d.hodnota for d in vyber),
        "prokliky": sum(d.prokliky for d in vyber),
        "zobrazeni": sum(d.zobrazeni for d in vyber),
        "dni_s_daty": len(vyber),
    }


def kpi(s: dict, typ: str) -> float | None:
    """PNO v %, ROAS jako násobek, CPA v měně účtu, konverze jako počet."""
    if typ == "pno":
        return s["utrata"] / s["hodnota"] * 100 if s["hodnota"] else None
    if typ == "roas":
        return s["hodnota"] / s["utrata"] if s["utrata"] else None
    if typ == "cpa":
        return s["utrata"] / s["konverze"] if s["konverze"] else None
    return s["konverze"]


def fmt_kpi(hodnota: float | None, typ: str) -> str:
    if hodnota is None:
        return "–"
    if typ == "pno":
        return f"{hodnota:.1f} %".replace(".", ",")
    if typ == "roas":
        return f"{hodnota * 100:.0f} %"
    if typ == "cpa":
        return f"{_fmt(hodnota)} Kč"
    return f"{hodnota:.0f}"


def z_test_podilu(k1: float, n1: float, k2: float, n2: float) -> float | None:
    """Dvouvýběrový z-test podílů (konverzní poměr). Vrací p-hodnotu, nebo None bez dat."""
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) if 0 < p < 1 else 0
    if se == 0:
        return None
    z = abs(p1 - p2) / se
    return math.erfc(z / math.sqrt(2))


def _stav_podle_cile(hodnota: float, cil: float, typ: str) -> str:
    t = PRAHY["tolerance"]
    if typ in ("pno", "cpa"):        # nižší je lepší
        if hodnota <= cil:
            return ZELENA
        return ZLUTA if hodnota <= cil * (1 + t) else CERVENA
    if hodnota >= cil:               # roas, konverze: vyšší je lepší
        return ZELENA
    return ZLUTA if hodnota >= cil * (1 - t) else CERVENA


def _rezerva(hodnota: float, cil: float, typ: str) -> float:
    """O kolik je výsledek lepší než cíl (0,2 = o 20 %). Záporné = horší."""
    if typ in ("pno", "cpa"):
        return (cil - hodnota) / cil
    return (hodnota - cil) / cil


@dataclass
class Posudek:
    stav: str
    shrnuti: str
    detaily: list[str] = field(default_factory=list)
    navrhy: list[str] = field(default_factory=list)
    kpi: float | None = None
    kpi_pred: float | None = None


def _c(x: float) -> str:
    """2.345 -> '2,35' (česká desetinná čárka)."""
    return f"{x:.2f}".replace(".", ",")


def _datum_cz(iso: str | None) -> str:
    if not iso:
        return "?"
    d = date.fromisoformat(iso)
    return f"{d.day}. {d.month}."


def posud_cil(po: dict, pred: dict, cile: dict, okno: Okno) -> Posudek:
    """Verdikt plnění cíle v okně od změny + srovnání se stejně dlouhým obdobím před ní."""
    p = PRAHY
    typ, cil = cile["typ"], float(cile["hodnota"])
    nazev = NAZVY_KPI[typ]
    od_kdy = (f"od změny {_datum_cz(okno.zmena)}" if okno.zmena and not okno.zkraceno
              else f"za posledních {okno.dni} dní")
    zdroj = {"config": "datum z konfigurace", "changelog": "datum z changelogu klienta",
             "výchozí": "poslední změna není známá, beru 28 dní"}.get(okno.zdroj, okno.zdroj)

    if okno.dni < p["min_dni"]:
        zbyva = p["min_dni"] - okno.dni
        return Posudek(BILA, f"Od změny {_datum_cz(okno.zmena)} uběhlo {okno.dni} dní. Počkej ještě "
                             f"{zbyva} {'den' if zbyva == 1 else 'dny' if zbyva < 5 else 'dní'} "
                             "(učící fáze po zásahu trvá 7–14 dní).",
                       detaily=[zdroj])

    hodnota = kpi(po, typ)
    if typ == "konverze":
        # Cíl je měsíční počet: přepočet tempa od změny na 30,4 dne.
        hodnota = po["konverze"] / okno.dni * 30.4

    detaily = [f"Okno {od_kdy} ({okno.dni} dní, {zdroj}): útrata {_fmt(po['utrata'])} Kč, "
               f"konverze {po['konverze']:.0f}, hodnota {_fmt(po['hodnota'])} Kč, prokliky {_fmt(po['prokliky'])}."]
    if okno.zkraceno:
        detaily.append(f"Změna je starší než {p['max_okno']} dní, hodnotím jen posledních {p['max_okno']} dní.")

    # Nula konverzí: u CPA je jasný signál, když útrata přerostla několik cílových CPA.
    if po["konverze"] == 0:
        if typ == "cpa" and po["utrata"] >= p["cpa_bez_konverzi_nasobek"] * cil:
            return Posudek(CERVENA, f"Nula konverzí {od_kdy} při útratě {_fmt(po['utrata'])} Kč "
                                    f"(= {po['utrata'] / cil:.1f}× cílové CPA {_fmt(cil)} Kč).",
                           detaily, ["Nejdřív ověř měření (skill `mereni-audit`), pak projdi příčiny skillem `anomalie`."])
        if po["prokliky"] >= p["min_prokliku"]:
            return Posudek(CERVENA, f"Nula konverzí {od_kdy} při {_fmt(po['prokliky'])} proklicích.",
                           detaily, ["Nejdřív ověř měření (skill `mereni-audit`): funguje pokladna/formulář a konverzní kód?",
                                     "Pak projdi změny v účtu a na webu skillem `anomalie`."])

    malo_dat = typ != "konverze" and (po["konverze"] < p["min_konverzi"] or hodnota is None)
    if malo_dat:
        tempo = po["konverze"] / okno.dni if okno.dni else 0
        if tempo > 0:
            dni = math.ceil((p["min_konverzi"] - po["konverze"]) / tempo)
            cekat = f"při dnešním tempu za ~{dni} dní"
        else:
            cekat = "zatím nepřišla žádná konverze"
        predbezne = f" Předběžně {nazev} {fmt_kpi(hodnota, typ)} vs. cíl {fmt_kpi(cil, typ)}." if hodnota is not None else ""
        return Posudek(BILA, f"Málo dat: {po['konverze']:.0f} konverzí {od_kdy}, pro závěr je potřeba "
                             f"aspoň {p['min_konverzi']} ({cekat}).{predbezne}",
                       detaily, [], kpi=hodnota)

    stav = _stav_podle_cile(hodnota, cil, typ)
    if typ == "konverze":
        shrnuti = (f"Tempo {hodnota:.0f} konverzí/měsíc {od_kdy} vs. cíl {cil:.0f} "
                   f"({(hodnota / cil - 1) * 100:+.0f} %).")
    else:
        shrnuti = f"{nazev} {fmt_kpi(hodnota, typ)} {od_kdy} vs. cíl {fmt_kpi(cil, typ)} (n={po['konverze']:.0f} konverzí)."

    # Srovnání s obdobím před změnou (stejná délka)
    kpi_pred = kpi(pred, typ)
    if typ == "konverze" and pred["dni_s_daty"]:
        kpi_pred = pred["konverze"] / okno.dni * 30.4
    zhorseni_po_zmene = False
    if pred["dni_s_daty"] and kpi_pred is not None:
        radek = (f"Před změnou ({_datum_cz(okno.pred_od)}–{_datum_cz(okno.pred_do)}): {nazev} "
                 f"{fmt_kpi(kpi_pred, typ)} → teď {fmt_kpi(hodnota, typ)}")
        pv = z_test_podilu(po["konverze"], po["prokliky"], pred["konverze"], pred["prokliky"])
        if pv is not None and min(po["prokliky"], pred["prokliky"]) >= p["min_prokliku"]:
            cvr_po = po["konverze"] / po["prokliky"] * 100
            cvr_pred = pred["konverze"] / pred["prokliky"] * 100
            vyznamne = "významné" if pv < 0.05 else "nevýznamné, může to být šum"
            radek += (f"; konverzní poměr {_c(cvr_pred)} % → {_c(cvr_po)} % "
                      f"(n={_fmt(pred['prokliky'])} vs. {_fmt(po['prokliky'])} prokliků; p={_c(pv)}, {vyznamne})")
        detaily.append(radek + ".")
        if okno.zmena and _stav_podle_cile(kpi_pred, cil, typ) == ZELENA and stav != ZELENA:
            zhorseni_po_zmene = True
    elif okno.zmena:
        detaily.append("Před změnou nejsou data ke srovnání.")

    navrhy = _navrhy(stav, typ, hodnota, cil, okno, zhorseni_po_zmene)
    return Posudek(stav, shrnuti, detaily, navrhy, kpi=hodnota, kpi_pred=kpi_pred)


def _navrhy(stav: str, typ: str, hodnota: float, cil: float, okno: Okno, po_zmene: bool) -> list[str]:
    """Pravidlové, konzervativní návrhy. Vždy začínají ověřením, ne zásahem."""
    out: list[str] = []
    if po_zmene:
        out.append(f"Před změnou {_datum_cz(okno.zmena)} se cíl plnil, po ní ne. Vyhodnoť tu změnu "
                   "(postup v knowledge/vyhodnoceni-zmen.md) a zvaž návrat, když jiná příčina nevyjde.")
    if stav == CERVENA:
        out.append("Nejdřív ověř měření a jednorázové vlivy (výpadek webu, sklad, akce konkurence): skill `anomalie`.")
        if typ in ("pno", "roas"):
            out.append("Najdi, kde náklady rostou bez tržeb: produkty v PMax/nákupních kampaních (skill `pmax-produkty`), "
                       "vyhledávací dotazy (skill `dotazy-vylouceni`).")
            out.append("Když je to strukturální, zvaž zpřísnění cílového ROAS o jeden krok (max ~+10–15 %, "
                       "větší skok zadusí objem). Jen po schválení, dry-run přes apply skript.")
        elif typ == "cpa":
            out.append("Projdi dotazy, které utrácí bez konverzí (skill `dotazy-vylouceni`), a sedí-li reklama "
                       "na vstupní stránku (skill `reklama-vs-stranka`).")
            out.append("Když je to strukturální, zvaž snížení cílového CPA o jeden krok (max ~10–15 %). Jen po schválení.")
        else:
            out.append("Ověř, jestli účet neztrácí zobrazení kvůli rozpočtu nebo pozici (skill `aukce-konkurence`) "
                       "a jestli čerpá rozpočet (skill `tempo-rozpoctu`).")
    elif stav == ZLUTA:
        out.append("Hraniční výsledek: nic neměň, sleduj další týden. Když se zhorší, postup jako u 🔴.")
    elif stav == ZELENA and _rezerva(hodnota, cil, typ) >= PRAHY["rezerva_rust"]:
        out.append(f"Výsledek je o {_rezerva(hodnota, cil, typ) * 100:.0f} % lepší než cíl. Prostor pro růst: "
                   "pusť hlídač akcí (`python3 scripts/hlidac/akce.py`) a skill `tempo-rozpoctu`; "
                   "u Mety strop škálování skillem `meta-strop`.")
    return out


# ------------------------------------------------------------------ tempo měsíce
@dataclass
class Tempo:
    stav: str
    texty: list[str]
    nedocerpa: bool = False


def tempo_mesice(dny: list[Den], cile: dict, vcera: date) -> Tempo | None:
    """Tempo čerpání měsíčního rozpočtu a obratu k včerejšku (lineární projekce)."""
    rozpocet, obrat = cile.get("mesicni_rozpocet"), cile.get("mesicni_obrat")
    if not rozpocet and not obrat:
        return None
    p = PRAHY
    zacatek = vcera.replace(day=1).isoformat()
    s = soucet(dny, zacatek, vcera.isoformat())
    uplynulo = vcera.day
    dni_mesice = calendar.monthrange(vcera.year, vcera.month)[1]
    if uplynulo < p["tempo_min_dni"]:
        return Tempo(BILA, [f"Začátek měsíce ({uplynulo}. den), tempo zatím nehodnotím."])
    stav, texty, nedocerpa = ZELENA, [], False
    if rozpocet:
        projekce = s["utrata"] / uplynulo * dni_mesice
        pomer = projekce / rozpocet
        txt = (f"Rozpočet: utraceno {_fmt(s['utrata'])} z {_fmt(rozpocet)} Kč "
               f"({s['utrata'] / rozpocet * 100:.0f} % za {uplynulo}/{dni_mesice} dní), "
               f"při tomto tempu {_fmt(projekce)} Kč ({pomer * 100:.0f} %).")
        if pomer > p["tempo_precerpa_cervena"]:
            stav = horsi(stav, CERVENA)
            txt += " Výrazně přečerpá — skill `tempo-rozpoctu`."
        elif pomer > p["tempo_precerpa"]:
            stav = horsi(stav, ZLUTA)
            txt += " Přečerpá — skill `tempo-rozpoctu`."
        elif pomer < p["tempo_nedocerpa"]:
            stav = horsi(stav, ZLUTA)
            txt += " Nedočerpá — zjisti proč (rozpočet vs. pozice), skill `tempo-rozpoctu`."
            nedocerpa = True
        texty.append(txt)
    if obrat:
        projekce_o = s["hodnota"] / uplynulo * dni_mesice
        pomer_o = projekce_o / obrat
        txt = (f"Obrat z reklam: {_fmt(s['hodnota'])} z {_fmt(obrat)} Kč, při tomto tempu "
               f"{_fmt(projekce_o)} Kč ({pomer_o * 100:.0f} %).")
        if pomer_o < 1 - p["tolerance"]:
            stav = horsi(stav, ZLUTA)
            txt += " Pod plánem."
        texty.append(txt)
    return Tempo(stav, texty, nedocerpa)


def navrh_z_tempa(posudek: Posudek, tempo: Tempo | None) -> None:
    """Cíl se plní a rozpočet se nedočerpá → růstová páka, ne jen hlášení."""
    if tempo and tempo.nedocerpa and posudek.stav == ZELENA and not any("akce.py" in n for n in posudek.navrhy):
        posudek.navrhy.append("Cíl se plní a měsíční rozpočet zůstane nedočerpaný: hledej, kam přidat "
                              "(`python3 scripts/hlidac/akce.py`). Nejdřív ověř, jestli kampaně brzdí rozpočet, "
                              "nebo pozice v aukci (skill `aukce-konkurence`) — při ztrátě kvůli pozici "
                              "přidání rozpočtu nepomůže.")


# ------------------------------------------------------------------ 8 týdnů kontextu
def tydny(dny: list[Den], konec: date, typ: str, pocet: int = 8) -> list[dict]:
    """Posledních `pocet` celých 7denních bloků končících dnem `konec` (od nejstaršího)."""
    out = []
    for i in range(pocet - 1, -1, -1):
        do = konec - timedelta(days=7 * i)
        od = do - timedelta(days=6)
        s = soucet(dny, od.isoformat(), do.isoformat())
        s.update(od=od.isoformat(), do=do.isoformat(), kpi=kpi(s, typ) if typ != "konverze" else s["konverze"])
        out.append(s)
    return out


def mesice(dny: list[Den], typ: str) -> list[dict]:
    """Měsíční řada ze všech dodaných dní (kontext měřítka a sezóny)."""
    skup: dict[str, list[Den]] = {}
    for d in dny:
        skup.setdefault(d.datum[:7], []).append(d)
    out = []
    for m in sorted(skup):
        s = soucet(skup[m], "0000", "9999")
        s.update(mesic=m, kpi=kpi(s, typ) if typ != "konverze" else s["konverze"])
        out.append(s)
    return out


def tabulka_tydnu(rady: list[dict], typ: str) -> list[str]:
    nazev = NAZVY_KPI[typ]
    radky = [f"| Týden | Útrata | Konverze | Hodnota | {nazev} |", "|---|---:|---:|---:|---:|"]
    for t in rady:
        radky.append(f"| {_datum_cz(t['od'])}–{_datum_cz(t['do'])} | {_fmt(t['utrata'])} | {t['konverze']:.0f} | "
                     f"{_fmt(t['hodnota'])} | {fmt_kpi(t['kpi'], typ)} |")
    return radky

"""Plánování rozpočtů a obratu — čistá logika bez API, ať se dá otestovat.

Co tu je:
- státní svátky ČR včetně Velikonoc (výpočet bez externí knihovny),
- váhy dnů v týdnu z historie (kolik procent běžného dne dělá pondělí, sobota…),
- koeficient svátku z historie,
- rozpad měsíční částky na dny tak, aby součet seděl přesně na korunu,
- podíly systémů, semafor plnění, prognóza konce měsíce,
- jednoduchý model klesajícího výnosu z navýšení rozpočtu.

Nic tu nesahá na síť ani na soubory. Načítání dat je v `data.py`.
"""
from __future__ import annotations

import calendar
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median, pstdev
from typing import Iterable

DNY = ["po", "út", "st", "čt", "pá", "so", "ne"]
NAZVY_SYSTEMU = {"google": "Google Ads", "sklik": "Sklik", "meta": "Meta"}


@dataclass
class Radek:
    """Jeden den jednoho systému (součet účtu)."""
    datum: date
    system: str
    naklady: float
    obrat: float
    konverze: float
    kliky: float = 0.0


# ------------------------------------------------------------------ svátky ČR
def velikonocni_nedele(rok: int) -> date:
    """Velikonoční neděle (gregoriánský kalendář, anonymní algoritmus Meeus/Jones/Butcher)."""
    a = rok % 19
    b, c = divmod(rok, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    mesic, den = divmod(h + l - 7 * m + 114, 31)
    return date(rok, mesic, den + 1)


def svatky_cr(rok: int) -> dict[date, str]:
    """Státní svátky a ostatní svátky ČR, kdy je volno (zákon č. 245/2000 Sb.)."""
    vn = velikonocni_nedele(rok)
    s = {
        date(rok, 1, 1): "Nový rok / Den obnovy samostatného českého státu",
        vn - timedelta(days=2): "Velký pátek",
        vn + timedelta(days=1): "Velikonoční pondělí",
        date(rok, 5, 1): "Svátek práce",
        date(rok, 5, 8): "Den vítězství",
        date(rok, 7, 5): "Cyril a Metoděj",
        date(rok, 7, 6): "Jan Hus",
        date(rok, 9, 28): "Den české státnosti",
        date(rok, 10, 28): "Vznik Československa",
        date(rok, 11, 17): "Den boje za svobodu a demokracii",
        date(rok, 12, 24): "Štědrý den",
        date(rok, 12, 25): "1. svátek vánoční",
        date(rok, 12, 26): "2. svátek vánoční",
    }
    return s


def je_svatek(d: date) -> bool:
    return d in svatky_cr(d.year)


def dny_mesice(rok: int, mesic: int) -> list[date]:
    return [date(rok, mesic, i) for i in range(1, calendar.monthrange(rok, mesic)[1] + 1)]


def parse_mesic(text: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", text.strip())
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise ValueError(f"Měsíc „{text}“ není ve tvaru YYYY-MM.")
    return int(m.group(1)), int(m.group(2))


def posun_mesic(rok: int, mesic: int, o: int) -> tuple[int, int]:
    i = rok * 12 + (mesic - 1) + o
    return i // 12, i % 12 + 1


# ----------------------------------------------------------------- události
def parse_udalost(text: str) -> dict[date, float]:
    """`2026-11-27:+40%` → {27. 11.: 1.40}. Rozsah: `2026-12-21..2026-12-31:-50%`.

    Násobí váhu dne PŘED přepočtem na měsíc — měsíční částka se nemění, den si jen
    vezme větší (menší) díl na úkor ostatních dnů.
    """
    m = re.fullmatch(r"\s*(\d{4}-\d{2}-\d{2})(?:\.\.(\d{4}-\d{2}-\d{2}))?\s*:\s*([+-]?\d+(?:[.,]\d+)?)\s*%?\s*",
                     text)
    if not m:
        raise ValueError(f"Událost „{text}“ — čekám tvar 2026-11-27:+40% nebo 2026-12-21..2026-12-31:-50%.")
    od = date.fromisoformat(m.group(1))
    do = date.fromisoformat(m.group(2)) if m.group(2) else od
    if do < od:
        raise ValueError(f"Událost „{text}“: konec je před začátkem.")
    nasobek = 1 + float(m.group(3).replace(",", ".")) / 100
    if nasobek < 0:
        raise ValueError(f"Událost „{text}“: víc než −100 % nejde.")
    out = {}
    d = od
    while d <= do:
        out[d] = nasobek
        d += timedelta(days=1)
    return out


def sluc_udalosti(texty: Iterable[str]) -> dict[date, float]:
    out: dict[date, float] = {}
    for t in texty:
        for d, n in parse_udalost(t).items():
            out[d] = out.get(d, 1.0) * n
    return out


# ------------------------------------------------------------- agregace dat
def po_dnech(radky: Iterable[Radek], system: str | None = None) -> dict[date, Radek]:
    """Sečte řádky po dnech (volitelně jen jeden systém)."""
    out: dict[date, Radek] = {}
    for r in radky:
        if system and r.system != system:
            continue
        a = out.get(r.datum)
        if a is None:
            out[r.datum] = Radek(r.datum, system or "celkem", r.naklady, r.obrat, r.konverze, r.kliky)
        else:
            a.naklady += r.naklady
            a.obrat += r.obrat
            a.konverze += r.konverze
            a.kliky += r.kliky
    return out


def systemy(radky: Iterable[Radek]) -> list[str]:
    return sorted({r.system for r in radky})


def hodnota(r: Radek, metrika: str) -> float:
    return float(getattr(r, metrika))


def cele_tydny(dny: dict[date, Radek], do: date, pocet: int) -> list[list[Radek]]:
    """Posledních `pocet` celých týdnů po–ne, které končí nejpozději `do`. Chybějící den = nula."""
    konec = do - timedelta(days=(do.weekday() + 1) % 7)  # poslední neděle <= do
    tydny = []
    for t in range(pocet, 0, -1):
        start = konec - timedelta(days=7 * t - 1)
        tyden = [dny.get(start + timedelta(days=i)) or Radek(start + timedelta(days=i), "", 0, 0, 0)
                 for i in range(7)]
        tydny.append(tyden)
    return tydny


def pocet_celych_tydnu(dny: dict[date, Radek], do: date) -> int:
    """Kolik celých týdnů po–ne historie souvisle pokrývá (do `do`)."""
    if not dny:
        return 0
    prvni = min(dny)
    konec = do - timedelta(days=(do.weekday() + 1) % 7)
    if konec < prvni:
        return 0
    return max(0, ((konec - prvni).days + 1) // 7)


# ------------------------------------------------------ váhy dnů v týdnu
MIN_TYDNU = 8


def vahy_dnu(dny: dict[date, Radek], do: date, metrika: str = "naklady",
             tydnu: int = 16) -> tuple[list[float], int]:
    """Index dne v týdnu (průměr = 1,0) z posledních celých týdnů.

    Každý den se dělí průměrem SVÉHO týdne (tím zmizí trend a sezóna), pak medián
    přes týdny (jeden výprodejový den váhu nerozhodí). Svátky se vynechají.
    Vrací (7 vah po–ne, počet použitých týdnů). Pod 8 týdnů vrací rovné váhy.
    """
    k_dispozici = min(tydnu, pocet_celych_tydnu(dny, do))
    if k_dispozici < MIN_TYDNU:
        return [1.0] * 7, k_dispozici
    pomery: dict[int, list[float]] = defaultdict(list)
    for tyden in cele_tydny(dny, do, k_dispozici):
        prumer = mean(hodnota(r, metrika) for r in tyden)
        if prumer <= 0:
            continue
        for i, r in enumerate(tyden):
            if not je_svatek(r.datum):
                pomery[i].append(hodnota(r, metrika) / prumer)
    vahy = [median(pomery[i]) if pomery[i] else 1.0 for i in range(7)]
    s = mean(vahy)
    return ([v / s for v in vahy] if s > 0 else [1.0] * 7), k_dispozici


def koeficient_svatku(dny: dict[date, Radek], metrika: str = "naklady",
                      min_pozorovani: int = 3) -> tuple[float, int]:
    """Kolik dělá svátek proti stejnému dni v týdnu okolo (±3 týdny). Medián přes svátky v historii.

    Pod `min_pozorovani` svátků v historii vrací 1,0 (neutrální) — nehádáme.
    Vánoce (24.–26. 12.) vynechává: chovají se jinak než ostatní svátky, na ně je `--udalost`.
    """
    if not dny:
        return 1.0, 0
    roky = range(min(dny).year, max(dny).year + 1)
    pomery = []
    for rok in roky:
        for d in svatky_cr(rok):
            if d.month == 12 or d not in dny:
                continue
            okoli = [dny[x] for x in (d + timedelta(days=7 * t) for t in (-3, -2, -1, 1, 2, 3))
                     if x in dny and not je_svatek(x)]
            if len(okoli) < 3:
                continue
            bezne = median(hodnota(r, metrika) for r in okoli)
            if bezne > 0:
                pomery.append(hodnota(dny[d], metrika) / bezne)
    if len(pomery) < min_pozorovani:
        return 1.0, len(pomery)
    return min(1.5, max(0.3, median(pomery))), len(pomery)


# ------------------------------------------------------ rozpad na dny
def rozdel_zaokrouhlene(celkem: float, vahy: list[float], mist: int = 0) -> list[float]:
    """Rozdělí `celkem` podle vah a zaokrouhlí tak, aby součet seděl přesně (metoda největších zbytků)."""
    if not vahy:
        return []
    s = sum(vahy)
    if s <= 0:
        vahy, s = [1.0] * len(vahy), float(len(vahy))
    jednotka = 10 ** mist
    cil = round(celkem * jednotka)
    presne = [celkem * jednotka * v / s for v in vahy]
    dolu = [math.floor(p) for p in presne]
    zbyva = int(cil - sum(dolu))
    poradi = sorted(range(len(vahy)), key=lambda i: presne[i] - dolu[i], reverse=True)
    for i in poradi[:max(0, zbyva)]:
        dolu[i] += 1
    return [x / jednotka for x in dolu]


def vahy_mesice(rok: int, mesic: int, vahy_tyden: list[float], koef_svatek: float = 1.0,
                udalosti: dict[date, float] | None = None) -> list[tuple[date, float]]:
    """Surová váha každého dne v měsíci: den v týdnu × svátek × událost."""
    udalosti = udalosti or {}
    out = []
    for d in dny_mesice(rok, mesic):
        v = vahy_tyden[d.weekday()]
        if je_svatek(d):
            v *= koef_svatek
        v *= udalosti.get(d, 1.0)
        out.append((d, v))
    return out


def rozpad_mesice(celkem: float, rok: int, mesic: int, vahy_tyden: list[float],
                  koef_svatek: float = 1.0, udalosti: dict[date, float] | None = None,
                  mist: int = 0) -> list[tuple[date, float]]:
    """Měsíční částka → dny. Součet = `celkem` přesně (na `mist` desetinných míst)."""
    vm = vahy_mesice(rok, mesic, vahy_tyden, koef_svatek, udalosti)
    castky = rozdel_zaokrouhlene(celkem, [v for _, v in vm], mist)
    return [(d, c) for (d, _), c in zip(vm, castky)]


def rozdel_mezi_systemy(celkem: float, podily: dict[str, float], mist: int = 0) -> dict[str, float]:
    klice = sorted(podily)
    castky = rozdel_zaokrouhlene(celkem, [podily[k] for k in klice], mist)
    return dict(zip(klice, castky))


def podily_systemu(radky: Iterable[Radek], od: date, do: date, metrika: str = "naklady") -> dict[str, float]:
    """Podíl systémů na metrice v okně (součet = 1). Systém s nulou dostane 0."""
    souc: dict[str, float] = defaultdict(float)
    for r in radky:
        if od <= r.datum <= do:
            souc[r.system] += hodnota(r, metrika)
    s = sum(souc.values())
    if s <= 0:
        return {k: 1 / len(souc) for k in souc} if souc else {}
    return {k: v / s for k, v in souc.items()}


# ------------------------------------------------------ plnění
SEMAFOR = {"zelena": "🟢", "zluta": "🟡", "cervena": "🔴"}
PRAH_ZELENA = 10.0
PRAH_ZLUTA = 25.0
PORADI = {"zelena": 0, "zluta": 1, "cervena": 2}


def odchylka_pct(skutecnost: float, plan: float) -> float | None:
    if plan == 0:
        return None if skutecnost == 0 else math.inf
    return (skutecnost - plan) / plan * 100


def semafor(odchylka: float | None, jen_dolu: bool = False) -> str:
    """🟢 do ±10 %, 🟡 do ±25 %, 🔴 víc. `jen_dolu`: nad plánem je vždy zelená (obrat, konverze)."""
    if odchylka is None:
        return "zelena"
    if jen_dolu and odchylka >= 0:
        return "zelena"
    a = abs(odchylka)
    if a <= PRAH_ZELENA:
        return "zelena"
    if a <= PRAH_ZLUTA:
        return "zluta"
    return "cervena"


def horsi(*barvy: str) -> str:
    return max(barvy, key=lambda b: PORADI[b]) if barvy else "zelena"


def prognoza_konce(skut_kum: float, plan_zbytek: float, skut_posledni: float, plan_posledni: float) -> float:
    """Konec měsíce při současném tempu: co už je + zbytek plánu × (skutečnost/plán za posledních ~7 dní).

    Tempo se bere proti PLÁNU, ne lineárně — plán už v sobě má víkendy, svátky a akce.
    """
    if plan_posledni > 0:
        tempo = min(3.0, max(0.0, skut_posledni / plan_posledni))
    else:
        tempo = 1.0
    return skut_kum + plan_zbytek * tempo


def denni_korekce(plan_kum: float, skut_kum: float, zbyva_dni: int) -> float:
    """O kolik denně utratit / vydělat víc (+) nebo míň (−) než plán, aby měsíc vyšel."""
    if zbyva_dni <= 0:
        return 0.0
    return (plan_kum - skut_kum) / zbyva_dni


# ------------------------------------------------------ forecast pomůcky
def mesicni_rada(radky: Iterable[Radek]) -> dict[tuple[int, int], dict[str, float]]:
    out: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: {"naklady": 0.0, "obrat": 0.0,
                                                                         "konverze": 0.0, "dni": 0})
    dny_videne: dict[tuple[int, int], set] = defaultdict(set)
    for r in radky:
        k = (r.datum.year, r.datum.month)
        out[k]["naklady"] += r.naklady
        out[k]["obrat"] += r.obrat
        out[k]["konverze"] += r.konverze
        dny_videne[k].add(r.datum)
    for k in out:
        out[k]["dni"] = len(dny_videne[k])
    return dict(sorted(out.items()))


def soucet(dny: dict[date, Radek], od: date, do: date, metrika: str) -> float:
    s, d = 0.0, od
    while d <= do:
        r = dny.get(d)
        if r:
            s += hodnota(r, metrika)
        d += timedelta(days=1)
    return s


def relativni_rozptyl(hodnoty: list[float]) -> float:
    """Směrodatná odchylka / průměr. Prázdné nebo nulové → 0."""
    h = [x for x in hodnoty if x is not None]
    if len(h) < 2 or mean(h) == 0:
        return 0.0
    return pstdev(h) / abs(mean(h))


def elasticita(tydny_naklady: list[float], tydny_obrat: list[float],
               vychozi: float = 0.6) -> tuple[float, str]:
    """Jak rychle roste obrat s útratou: obrat ~ útrata^b. b < 1 = každá další koruna vydělá míň.

    Zkusí odhad z log-log regrese po týdnech. Ten je zkreslený sezónou (v sezóně se víc utrácí
    i víc prodává), proto ho bere jen v rozumném pásmu 0,3–0,9 a při dost velkém rozptylu útraty.
    Jinak vrátí `vychozi` (0,6 = obecný předpoklad, ne změřený).
    """
    pary = [(math.log(n), math.log(o)) for n, o in zip(tydny_naklady, tydny_obrat) if n > 0 and o > 0]
    if len(pary) < 12 or relativni_rozptyl([n for n in tydny_naklady if n > 0]) < 0.15:
        return vychozi, "výchozí předpoklad (málo dat nebo útrata se skoro neměnila)"
    mx = mean(x for x, _ in pary)
    my = mean(y for _, y in pary)
    sxx = sum((x - mx) ** 2 for x, _ in pary)
    if sxx == 0:
        return vychozi, "výchozí předpoklad (útrata se neměnila)"
    b = sum((x - mx) * (y - my) for x, y in pary) / sxx
    if 0.3 <= b <= 0.9:
        return b, f"odhad z {len(pary)} týdnů historie (zkreslený sezónou, ber orientačně)"
    return vychozi, f"výchozí předpoklad (odhad z historie vyšel {b:.2f}, mimo věrohodné pásmo 0,3–0,9)"


def scenar_rozpoctu(naklady: float, obrat: float, konverze: float, zmena_pct: float,
                    b: float) -> dict[str, float]:
    """Útrata × (1+x) → obrat × (1+x)^b. Marginální PNO = kolik stojí koruna obratu NAVÍC."""
    f = 1 + zmena_pct / 100
    n2 = naklady * f
    o2 = obrat * (f ** b) if f > 0 else 0.0
    k2 = konverze * (f ** b) if f > 0 else 0.0
    d_o = o2 - obrat
    marg = (n2 - naklady) / d_o * 100 if d_o != 0 else None
    return {"naklady": n2, "obrat": o2, "konverze": k2,
            "pno": n2 / o2 * 100 if o2 else None, "marginalni_pno": marg}


def pno(naklady: float, obrat: float) -> float | None:
    return naklady / obrat * 100 if obrat else None


# ------------------------------------------------------ formát
def kc(x: float | None) -> str:
    if x is None:
        return "–"
    return f"{x:,.0f}".replace(",", " ") + " Kč"


def cislo(x: float | None, mist: int = 0) -> str:
    if x is None:
        return "–"
    return f"{x:,.{mist}f}".replace(",", " ").replace(".", ",")


def pct(x: float | None, znamenko: bool = False) -> str:
    if x is None:
        return "–"
    if math.isinf(x):
        return "∞"
    s = f"{x:+.1f}" if znamenko else f"{x:.1f}"
    return s.replace(".", ",") + " %"

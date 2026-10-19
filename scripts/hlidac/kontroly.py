"""Pravidla hlídače — čistá logika bez API, ať se dá otestovat.

Hlídač nehodnotí, jestli účet „funguje" (na to je krátké okno málo, viz CLAUDE.md 4b).
Hledá jen náhlé výkyvy proti běžnému dni: kampaně, které přestaly utrácet nebo utíkají,
propad zobrazení, skok ceny prokliku a nulové konverze tam, kde běžně jsou.

Běžný den = medián posledních 28 dní před hodnoceným dnem. Medián, ne průměr:
jeden výprodejový den by průměr vytáhl nahoru a hlídač by pak týden hlásil „propad".
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median

CERVENA = "cervena"
ZLUTA = "zluta"

# Prahy. Záměrně volné — hlídač, který píská každý den, lidi přestanou číst.
PRAHY = {
    "utrata_stoji": 0.20,       # včera pod 20 % běžné útraty
    "utrata_utika": 1.60,       # včera přes 160 % běžné útraty
    "zobrazeni_propad": 0.50,   # zobrazení pod 50 % běžného dne
    "cpc_skok": 1.40,           # CPC o 40 % dráž než běžně
    "cpc_min_prokliku": 20,     # pod tolik prokliků CPC nehodnotit (šum)
    "konverze_min_bezne": 2.0,  # nulu hlásit jen tam, kde běžně padají aspoň 2 denně
    "konverze_propad": 0.40,    # propad pod 40 % běžného dne…
    "konverze_propad_min": 5.0, # …hlídat jen u účtů s aspoň 5 konverzemi denně
    "min_historie_dni": 7,
    "dnes_utika": 1.30,         # dnes už utratil víc než 130 % běžného celého dne
    "dnes_stoji": 0.20,         # večer pořád pod 20 % běžného dne
    "dnes_stoji_od_hodiny": 18,
}


@dataclass
class Den:
    datum: str          # YYYY-MM-DD
    utrata: float       # v měně účtu
    zobrazeni: int
    prokliky: int
    konverze: float
    hodnota: float = 0.0


@dataclass
class Nalez:
    uroven: str         # CERVENA | ZLUTA
    text: str


def _fmt(x: float) -> str:
    """1234.5 -> '1 235' (české tisíce, bez desetin)."""
    return f"{x:,.0f}".replace(",", " ")


def bezny_den(dny: list[Den], datum: str) -> dict | None:
    """Mediány z 28 dní před `datum`. None, když je historie moc krátká."""
    hist = sorted((d for d in dny if d.datum < datum), key=lambda d: d.datum)[-28:]
    if len(hist) < PRAHY["min_historie_dni"]:
        return None
    prokliky = sum(d.prokliky for d in hist)
    return {
        "utrata": median(d.utrata for d in hist),
        "zobrazeni": median(d.zobrazeni for d in hist),
        # CPC z celku, ne medián denních CPC (dny s 1 proklikem by ho rozhodily)
        "cpc": (sum(d.utrata for d in hist) / prokliky) if prokliky else 0.0,
        # konverze průměrem: u malých účtů je medián často 0
        "konverze": mean(d.konverze for d in hist),
        "dni": len(hist),
    }


def vyhodnot_den(dny: list[Den], datum: str, min_utrata: float = 0.0) -> list[Nalez]:
    """Najde výkyvy dne `datum` proti běžnému dni."""
    p = PRAHY
    den = next((d for d in dny if d.datum == datum), None)
    zaklad = bezny_den(dny, datum)
    if zaklad is None:
        return [Nalez(ZLUTA, "Málo historie (méně než 7 dní) — hlídač zatím nemá s čím porovnat.")]
    if den is None:
        den = Den(datum, 0.0, 0, 0, 0.0)
    if zaklad["utrata"] <= max(min_utrata, 0.0):
        return []  # účet běžně skoro neutrácí, není co hlídat

    out: list[Nalez] = []
    bu = zaklad["utrata"]
    if den.utrata < p["utrata_stoji"] * bu:
        out.append(Nalez(CERVENA,
            f"Útrata spadla na {_fmt(den.utrata)} (běžně {_fmt(bu)}). Zkontroluj platbu nebo kredit, "
            "zamítnuté reklamy a pozastavené kampaně."))
    elif den.utrata > p["utrata_utika"] * bu:
        out.append(Nalez(CERVENA,
            f"Útrata vyletěla na {_fmt(den.utrata)} (běžně {_fmt(bu)}, +{(den.utrata / bu - 1):.0%}). "
            "Zkontroluj změny rozpočtů a cílů a nové kampaně."))

    bz = zaklad["zobrazeni"]
    utrata_hlasena = any(n.uroven == CERVENA for n in out)
    if bz and den.zobrazeni < p["zobrazeni_propad"] * bz and not utrata_hlasena:
        out.append(Nalez(ZLUTA,
            f"Zobrazení spadla na {_fmt(den.zobrazeni)} (běžně {_fmt(bz)})."))

    if den.prokliky >= p["cpc_min_prokliku"] and zaklad["cpc"]:
        cpc = den.utrata / den.prokliky
        if cpc > p["cpc_skok"] * zaklad["cpc"]:
            out.append(Nalez(ZLUTA,
                f"Cena prokliku {cpc:.2f} (běžně {zaklad['cpc']:.2f}, +{(cpc / zaklad['cpc'] - 1):.0%})."))

    bk = zaklad["konverze"]
    if bk >= p["konverze_min_bezne"] and den.konverze == 0:
        out.append(Nalez(CERVENA,
            f"Nula konverzí (běžně {bk:.1f} denně). Nejdřív ověř měření: funguje pokladna a kód?"))
    elif bk >= p["konverze_propad_min"] and den.konverze < p["konverze_propad"] * bk:
        out.append(Nalez(ZLUTA,
            f"Konverze spadly na {den.konverze:.0f} (běžně {bk:.1f} denně). Systémy je ještě "
            "pár dní dopočítávají, potvrdí to až zítřejší běh."))
    return out


def vyhodnot_dnes(utrata_dnes: float, bezna_utrata: float, hodina: int) -> list[Nalez]:
    """Večerní kontrola: utíká dnešek, nebo skoro stojí?"""
    p = PRAHY
    if bezna_utrata <= 0:
        return []
    if utrata_dnes > p["dnes_utika"] * bezna_utrata:
        return [Nalez(CERVENA,
            f"Dnes už utraceno {_fmt(utrata_dnes)}, víc než běžný celý den ({_fmt(bezna_utrata)}).")]
    if hodina >= p["dnes_stoji_od_hodiny"] and utrata_dnes < p["dnes_stoji"] * bezna_utrata:
        return [Nalez(ZLUTA,
            f"Do {hodina}:00 utraceno jen {_fmt(utrata_dnes)} (běžný den {_fmt(bezna_utrata)}). "
            "Reklamy možná nejedou.")]
    return []

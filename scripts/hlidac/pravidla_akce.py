"""Pravidla hlídače akcí — čistá logika bez API, ať se dá otestovat.

Hlídač akcí hledá prostor pro škálování: kampaně, které plní cíl s rezervou a brzdí je
rozpočet. Ke každé navrhne, o kolik přidat (v limitech z konfigurace), proč, jaké je
riziko a jak to po schválení provést. **Sám nic nemění.**

Signály „brzdí ho rozpočet“ (ověřené zdroje viz scripts/hlidac/zdroje.py):
- Google: `metrics.search_budget_lost_impression_share` (0–0,9; nad 0,9 vrací 0,9001),
  stav `campaign.primary_status_reasons` obsahující BUDGET_CONSTRAINED (název hodnoty
  enumu neověřený, proto jen doplňkový signál), a dny s útratou ≥ 90 % rozpočtu.
- Sklik: jen dny s útratou ≥ 90 % denního rozpočtu. Pole „ztráta zobrazení kvůli
  rozpočtu“ jsme v API neověřili, proto ho nepoužíváme.
- Meta: dny s útratou ≥ 90 % denního rozpočtu sady (nebo kampaně s rozpočtem kampaně)
  a frekvence za 7 dní pod prahem (jinak je strop v publiku, ne v rozpočtu).

Limity navýšení (z `limity` v konfiguraci): max krok v % (`max_navyseni_pct`), týdenní
strop (`max_navyseni_tyden_pct` proti nejnižšímu rozpočtu za 7 dní), strop součtu denních
rozpočtů účtu (`max_denni_rozpocet`) a zbytek měsíčního rozpočtu (`cile.mesicni_rozpocet`).
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from kontroly import Den, _fmt

PRAHY = {
    "okno_dni": 14,             # výkon kampaně za posledních 14 dní
    "min_konverzi": 15,         # pod tím výkon kampaně nehodnotit (šum)
    "rezerva_cile": 0.10,       # výkon aspoň o 10 % lepší než cíl
    "vycerpano_pct": 0.90,      # den s útratou ≥ 90 % rozpočtu = vyčerpaný
    "vycerpano_podil_dni": 0.5, # …aspoň polovina dní v okně
    "ztrata_is_min": 0.10,      # Google: ≥ 10 % zobrazení ztraceno kvůli rozpočtu
    "meta_max_frekvence": 3.0,  # frekvence za 7 dní; nad tím strop v publiku
    "min_krok_pct": 5,          # menší navýšení nemá smysl navrhovat
    "vikend_krok_pct": 10,      # o víkendu nikdo nereaguje → max +10 %
    "vikend_dni": 3,            # pátek večer → pondělí ráno, počítáno 3 dny útraty
    "google_denni_limit_nasobek": 2.0,  # Google: den může utratit až 2× průměrného denního rozpočtu
    "dnes_vycerpano": 0.90,     # večer: dnes už ≥ 90 % rozpočtu…
    "dnes_do_hodiny": 18,       # …a je teprve 18:00 nebo dřív
    "spatny_vykon_nasobek_cpa": 3.0,    # útrata 3× cílové CPA bez konverze = propaluje
}

MENY_OFFSET_1 = {"CLP", "COP", "CRC", "HUF", "ISK", "IDR", "JPY", "KRW", "PYG", "TWD", "VND"}


@dataclass
class Kampan:
    """Kampaň (Google, Sklik) nebo sada reklam / kampaň s rozpočtem kampaně (Meta)."""
    system: str                     # google | sklik | meta
    id: str
    nazev: str
    rozpocet: float | None          # denní rozpočet v měně účtu; None = neznámý / doživotní
    dny: list[Den] = field(default_factory=list)
    uroven: str = "kampaň"          # kampaň | sada
    rozpocet_id: str | None = None  # Google campaign_budget.id; Meta id objektu, který nese rozpočet
    sdileny_rozpocet: bool = False
    ztrata_is_rozpocet: float | None = None
    duvody_stavu: list[str] = field(default_factory=list)
    frekvence_7d: float | None = None
    utrata_dnes: float | None = None
    mena: str | None = None


@dataclass
class Navyseni:
    soucasny: float
    novy: float
    pct: float
    omezeni: list[str] = field(default_factory=list)


@dataclass
class Navrh:
    ucet: str
    kampan: Kampan
    navyseni: Navyseni
    proc: list[str]
    rizika: list[str]


def _c(x: float) -> str:
    """9.9 -> '9,9', 15.0 -> '15' (česká desetinná čárka, bez zbytečné nuly)."""
    return f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",")


# ------------------------------------------------------------------ výkon
def soucet(k: Kampan, od: str, do: str) -> dict:
    vyber = [d for d in k.dny if od <= d.datum <= do]
    return {"utrata": sum(d.utrata for d in vyber), "konverze": sum(d.konverze for d in vyber),
            "hodnota": sum(d.hodnota for d in vyber), "prokliky": sum(d.prokliky for d in vyber),
            "dni": len(vyber)}


def posud_vykon(s: dict, cile: dict, ucet_cpa: float | None = None) -> tuple[bool, str, float]:
    """Plní kampaň cíl s rezervou? Vrací (ano, popis, rezerva 0–1)."""
    p = PRAHY
    typ, cil = cile["typ"], float(cile["hodnota"])
    if s["konverze"] < p["min_konverzi"]:
        return False, f"jen {s['konverze']:.0f} konverzí za {p['okno_dni']} dní (potřeba {p['min_konverzi']})", 0.0
    if typ == "pno":
        if not s["hodnota"]:
            return False, "bez hodnoty konverzí nejde PNO spočítat", 0.0
        h = s["utrata"] / s["hodnota"] * 100
        rez = (cil - h) / cil
        popis = f"PNO {_c(h)} % vs. cíl {_c(cil)} %"
    elif typ == "roas":
        if not s["utrata"]:
            return False, "bez útraty", 0.0
        h = s["hodnota"] / s["utrata"]
        rez = (h - cil) / cil
        popis = f"ROAS {h * 100:.0f} % vs. cíl {cil * 100:.0f} %"
    else:
        h = s["utrata"] / s["konverze"]
        if typ == "cpa":
            cil_cpa, co = cil, "cíl"
        else:  # konverze: cíl je počet, efektivitu měříme proti průměrnému CPA účtu
            if not ucet_cpa:
                return False, "chybí průměrné CPA účtu pro srovnání", 0.0
            cil_cpa, co = ucet_cpa, "průměr účtu"
        rez = (cil_cpa - h) / cil_cpa
        popis = f"CPA {_fmt(h)} Kč vs. {co} {_fmt(cil_cpa)} Kč"
    popis += f" (n={s['konverze']:.0f} konv.)"
    return rez >= p["rezerva_cile"], popis, rez


def omezeni_rozpoctem(k: Kampan, od: str, do: str) -> tuple[bool, list[str]]:
    """Brzdí kampaň rozpočet? Vrací (ano, důvody s čísly)."""
    p = PRAHY
    duvody: list[str] = []
    dny = [d for d in k.dny if od <= d.datum <= do]
    if k.rozpocet and dny:
        vycerpane = sum(1 for d in dny if d.utrata >= p["vycerpano_pct"] * k.rozpocet)
        if vycerpane / len(dny) >= p["vycerpano_podil_dni"]:
            duvody.append(f"vyčerpal ≥ 90 % denního rozpočtu {vycerpane} z {len(dny)} dní")
    if k.ztrata_is_rozpocet is not None and k.ztrata_is_rozpocet >= p["ztrata_is_min"]:
        hodnota = "víc než 90" if k.ztrata_is_rozpocet > 0.9 else f"{k.ztrata_is_rozpocet * 100:.0f}"
        duvody.append(f"ve vyhledávání ztrácí {hodnota} % zobrazení kvůli rozpočtu")
    if any("BUDGET_CONSTRAINED" in str(r) for r in k.duvody_stavu):
        duvody.append("Google u kampaně hlásí omezení rozpočtem")
    return bool(duvody), duvody


# ------------------------------------------------------------------ limity
def rozpocet_pred_tydnem(historie: dict[str, float], dnes: date, aktualni: float) -> float:
    """Nejnižší zaznamenaný rozpočet objektu za posledních 7 dní (včetně dneška).

    `historie` = {datum: rozpočet} ze snímků, které si hlídač ukládá při každém běhu.
    Bez historie vrací aktuální rozpočet (týdenní strop pak = jeden krok).
    """
    od = (dnes - timedelta(days=7)).isoformat()
    hodnoty = [v for d, v in historie.items() if od <= d <= dnes.isoformat()]
    return min(hodnoty + [aktualni])


def rezerva_uctu(limity: dict, soucet_rozpoctu: float, cile: dict | None, utraceno_mesic: float,
                 denni_utrata: float, dnes: date) -> tuple[float | None, str | None]:
    """Kolik Kč/den smí účet celkem přidat. (None, None) = bez stropu.

    - `max_denni_rozpocet`: strop součtu denních rozpočtů účtu,
    - `cile.mesicni_rozpocet`: (zbytek měsíce / zbývající dny) − dnešní tempo útraty.
    """
    rezervy: list[tuple[float, str]] = []
    if limity.get("max_denni_rozpocet"):
        rezervy.append((float(limity["max_denni_rozpocet"]) - soucet_rozpoctu,
                        f"strop účtu {_fmt(limity['max_denni_rozpocet'])} Kč/den (součet rozpočtů teď {_fmt(soucet_rozpoctu)})"))
    if cile and cile.get("mesicni_rozpocet"):
        dni_mesice = calendar.monthrange(dnes.year, dnes.month)[1]
        zbyva_dni = dni_mesice - dnes.day + 1
        mozno = (float(cile["mesicni_rozpocet"]) - utraceno_mesic) / zbyva_dni
        rezervy.append((mozno - denni_utrata,
                        f"měsíční rozpočet {_fmt(cile['mesicni_rozpocet'])} Kč (utraceno {_fmt(utraceno_mesic)}, "
                        f"zbývá {zbyva_dni} dní → max {_fmt(mozno)} Kč/den, tempo teď {_fmt(denni_utrata)} Kč/den)"))
    if not rezervy:
        return None, None
    return min(rezervy, key=lambda x: x[0])


def _zaokrouhli_dolu(castka: float) -> float:
    return math.floor(castka / 10) * 10 if castka >= 100 else math.floor(castka)


def navrhni_navyseni(rozpocet: float, limity: dict, *, rezerva: float | None = None,
                     popis_rezervy: str | None = None, rozpocet_tyden: float | None = None,
                     vikend: bool = False) -> tuple[Navyseni | None, list[str]]:
    """Nový denní rozpočet v limitech. Vrací (návrh, nebo None; seznam omezení)."""
    p = PRAHY
    pct = float(limity.get("max_navyseni_pct", 20))
    omezeni: list[str] = []
    if vikend and pct > p["vikend_krok_pct"]:
        pct = p["vikend_krok_pct"]
        omezeni.append(f"víkend: krok snížen na {pct:.0f} % (nikdo nebude reagovat)")
    novy = rozpocet * (1 + pct / 100)
    if rozpocet_tyden:
        strop = rozpocet_tyden * (1 + float(limity.get("max_navyseni_tyden_pct", 30)) / 100)
        if novy > strop:
            novy = strop
            omezeni.append(f"týdenní strop +{float(limity.get('max_navyseni_tyden_pct', 30)):.0f} % "
                           f"proti {_fmt(rozpocet_tyden)} Kč před týdnem")
    if rezerva is not None and novy - rozpocet > rezerva:
        novy = rozpocet + max(rezerva, 0.0)
        omezeni.append(f"strop: {popis_rezervy}")
    novy = _zaokrouhli_dolu(novy)
    skutecne = (novy / rozpocet - 1) * 100 if rozpocet else 0.0
    if skutecne < p["min_krok_pct"]:
        return None, omezeni + [f"limity pustí jen +{max(skutecne, 0):.0f} %, to nemá smysl měnit"]
    return Navyseni(rozpocet, novy, skutecne, omezeni), omezeni


# ------------------------------------------------------------------ kandidáti
def kandidati(ucet: str, kampane: list[Kampan], cile: dict, limity: dict, *, vcera: date,
              rezerva: float | None = None, popis_rezervy: str | None = None,
              historie: dict[str, dict[str, float]] | None = None, vikend: bool = False,
              dnes_hodina: int | None = None) -> tuple[list[Navrh], list[str]]:
    """Najde kampaně pro navýšení. Vrací (návrhy, poznámky ke kampaním, které těsně neprošly).

    Rezerva účtu se rozděluje postupně: nejdřív kampaně s největší rezervou proti cíli.
    `dnes_hodina` zapne večerní režim: kandidát musí mít dnes už ≥ 90 % rozpočtu utraceno.
    """
    p = PRAHY
    historie = historie or {}
    od = (vcera - timedelta(days=p["okno_dni"] - 1)).isoformat()
    do = vcera.isoformat()
    vsechny = [soucet(k, od, do) for k in kampane]
    konv = sum(s["konverze"] for s in vsechny)
    ucet_cpa = sum(s["utrata"] for s in vsechny) / konv if konv else None

    zajemci, poznamky = [], []
    for k, s in zip(kampane, vsechny):
        if not k.rozpocet:
            continue
        brzdi, duvody = omezeni_rozpoctem(k, od, do)
        if dnes_hodina is not None:
            if k.utrata_dnes is None or k.utrata_dnes < p["dnes_vycerpano"] * k.rozpocet:
                continue
            kdy = "už" if dnes_hodina <= p["dnes_do_hodiny"] else f"do {dnes_hodina}:00"
            duvody = [f"dnes {kdy} utratil {_fmt(k.utrata_dnes)} z {_fmt(k.rozpocet)} Kč "
                      f"({k.utrata_dnes / k.rozpocet * 100:.0f} %) a je teprve {dnes_hodina}:00"] + duvody
            brzdi = True
        if not brzdi:
            continue
        ok, popis, rez = posud_vykon(s, cile, ucet_cpa)
        if not ok:
            poznamky.append(f"{k.nazev}: brzdí ho rozpočet, ale {popis} — nenavrhuji.")
            continue
        if k.system == "meta" and k.frekvence_7d is not None and k.frekvence_7d > p["meta_max_frekvence"]:
            poznamky.append(f"{k.nazev}: frekvence {k.frekvence_7d:.1f} za 7 dní — strop je spíš v publiku "
                            "než v rozpočtu (skill `meta-strop`).")
            continue
        zajemci.append((rez, k, s, popis, duvody))

    navrhy: list[Navrh] = []
    zbyva = rezerva
    for rez, k, s, popis, duvody in sorted(zajemci, key=lambda x: -x[0]):
        tyden = rozpocet_pred_tydnem(historie.get(k.id, {}), vcera + timedelta(days=1), k.rozpocet)
        nav, omez = navrhni_navyseni(k.rozpocet, limity, rezerva=zbyva, popis_rezervy=popis_rezervy,
                                     rozpocet_tyden=tyden, vikend=vikend)
        if nav is None:
            poznamky.append(f"{k.nazev}: {popis}, brzdí ho rozpočet, ale {omez[-1]}.")
            continue
        if zbyva is not None:
            zbyva -= nav.novy - nav.soucasny
        proc = [popis + f" za {p['okno_dni']} dní, útrata {_fmt(s['utrata'])} Kč"] + duvody
        navrhy.append(Navrh(ucet, k, nav, proc, rizika_navrhu(k, rez, vikend)))
    return navrhy, poznamky


def rizika_navrhu(k: Kampan, rezerva: float, vikend: bool) -> list[str]:
    out = ["Další koruna nese méně než průměrná (marginální výnos klesá). Po 7 dnech porovnej "
           "výkon s obdobím před navýšením."]
    if rezerva < 0.2:
        out.append(f"Rezerva proti cíli je jen {rezerva * 100:.0f} %, navýšení ji může spotřebovat.")
    if k.sdileny_rozpocet:
        out.append("Rozpočet je sdílený: navýšení dostanou všechny kampaně, které ho sdílí.")
    if k.system == "google":
        out.append(f"Google může v jednom dni utratit až {PRAHY['google_denni_limit_nasobek']:.0f}× průměrného "
                   "denního rozpočtu (měsíčně max 30,4×).")
    if k.system == "meta":
        out.append("U Mety může výraznější změna rozpočtu vrátit sadu do fáze učení (přesný práh neověřený).")
        if k.frekvence_7d is not None and k.frekvence_7d > PRAHY["meta_max_frekvence"] * 0.8:
            out.append(f"Frekvence {k.frekvence_7d:.1f} za 7 dní se blíží prahu {PRAHY['meta_max_frekvence']:.0f}.")
    if vikend:
        out.append("Přes víkend to nikdo neuvidí — proto menší krok. V pondělí ráno vyhodnoť.")
    return out


# ------------------------------------------------------------------ víkendová rizika
def rizika_vikend(ucet: str, kampane: list[Kampan], cile: dict, *, vcera: date,
                  zbyva_mesic: float | None) -> list[str]:
    """Co může přes víkend utéct: zbytek měsíčního rozpočtu a kampaně, které čerpají a neplní cíl."""
    p = PRAHY
    out: list[str] = []
    rozpocty = sum(k.rozpocet or 0 for k in kampane)
    if zbyva_mesic is not None and rozpocty:
        bezne = rozpocty * p["vikend_dni"]
        if bezne > zbyva_mesic:
            out.append(f"{ucet}: denní rozpočty ({_fmt(rozpocty)} Kč) za {p['vikend_dni']} dny = {_fmt(bezne)} Kč, "
                       f"z měsíčního rozpočtu zbývá {_fmt(max(zbyva_mesic, 0))} Kč. Víkend může měsíc vyčerpat.")
        if any(k.system == "google" for k in kampane):
            g = sum(k.rozpocet or 0 for k in kampane if k.system == "google")
            nejhur = g * p["google_denni_limit_nasobek"] * p["vikend_dni"]
            if nejhur > zbyva_mesic and bezne <= zbyva_mesic:
                out.append(f"{ucet}: Google může v jednom dni utratit až 2× denní rozpočet; v nejhorším případě "
                           f"{_fmt(nejhur)} Kč přes víkend vs. zbývajících {_fmt(max(zbyva_mesic, 0))} Kč.")
    od = (vcera - timedelta(days=p["okno_dni"] - 1)).isoformat()
    for k in kampane:
        if not k.rozpocet:
            continue
        brzdi, _ = omezeni_rozpoctem(k, od, vcera.isoformat())
        if not brzdi:
            continue
        s = soucet(k, od, vcera.isoformat())
        typ, cil = cile["typ"], float(cile["hodnota"])
        vikend_kc = k.rozpocet * p["vikend_dni"]
        if s["konverze"] == 0:
            if typ == "cpa" and s["utrata"] >= p["spatny_vykon_nasobek_cpa"] * cil:
                out.append(f"{ucet} / {k.nazev}: čerpá celý rozpočet a za {p['okno_dni']} dní nemá konverzi "
                           f"(útrata {_fmt(s['utrata'])} Kč). Přes víkend utratí ~{_fmt(vikend_kc)} Kč. "
                           "Zvaž snížení rozpočtu do pondělí (jen po schválení).")
            continue
        if s["konverze"] < p["min_konverzi"]:
            continue
        ok, popis, rez = posud_vykon(s, cile)
        if rez < -p["rezerva_cile"]:
            out.append(f"{ucet} / {k.nazev}: čerpá celý rozpočet, ale {popis}. Přes víkend utratí "
                       f"~{_fmt(vikend_kc)} Kč. Zvaž snížení rozpočtu do pondělí (jen po schválení).")
    return out


# ------------------------------------------------------------------ plány pro apply skripty
def plan_google(navrhy: list[Navrh], datum: str) -> dict:
    """Vstup pro scripts/google_ads/apply_changes.py (klíč `set_budget`)."""
    return {
        "_popis": f"Návrh hlídače akcí {datum}. NESCHVÁLENO. Dry-run: bez --apply nic nezapíše.",
        "set_budget": [{"budget_id": n.kampan.rozpocet_id,
                        "amount_micros": int(round(n.navyseni.novy * 1_000_000)),
                        "_popis": f"{n.kampan.nazev}: {_fmt(n.navyseni.soucasny)} → {_fmt(n.navyseni.novy)} Kč/den"}
                       for n in navrhy if n.kampan.system == "google" and n.kampan.rozpocet_id],
    }


def meta_jednotky(castka: float, mena: str | None) -> int:
    """Meta `daily_budget` je v nejmenší jednotce měny (CZK/EUR: offset 100, HUF/JPY…: 1)."""
    offset = 1 if (mena or "").upper() in MENY_OFFSET_1 else 100
    return int(round(castka * offset))


def plan_meta(navrhy: list[Navrh], klient: str, datum: str) -> dict:
    """Vstup pro scripts/meta/apply.py. Stav schválení „pending“ — `--apply` ho odmítne."""
    return {
        "change_id": f"{klient}-meta-hlidac-akci-{datum}",
        "client": klient,
        "approval": {"status": "pending", "approved_by": None, "approved_at": None},
        "changes": [{"object_id": n.kampan.rozpocet_id or n.kampan.id,
                     "note": f"{n.kampan.nazev}: denní rozpočet {_fmt(n.navyseni.soucasny)} → "
                             f"{_fmt(n.navyseni.novy)} ({'; '.join(n.proc[:2])})",
                     "params": {"daily_budget": meta_jednotky(n.navyseni.novy, n.kampan.mena)}}
                    for n in navrhy if n.kampan.system == "meta"],
    }

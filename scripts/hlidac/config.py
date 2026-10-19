"""Společné načítání konfigurace hlídačů (`clients/hlidac-ucty.json`). Jen čte, nic nevolá.

Používají ho všechny tři hlídače:
- `hlidac.py`  — náhlé výkyvy (hlídá účty s "vykyvy" v poli `hlidat`),
- `cile.py`    — plnění cílů od poslední změny ("cile"),
- `akce.py`    — prostor pro škálování ("akce").

Zpětně kompatibilní: starý formát `{"ucty": [...]}` bez `hlidat` dál funguje.
Účet bez pole `hlidat` hlídají všechny hlídače, které pro něj mají data
(hlídač cílů a akcí potřebují blok `cile`).

Chyby hlásí přes SystemExit česky, ať je student pochopí bez čtení kódu.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VYCHOZI_UCTY = ROOT / "clients" / "hlidac-ucty.json"
VZOR_UCTY = Path(__file__).resolve().parent / "ucty.example.json"

SYSTEMY = {"sklik": "Sklik", "meta": "Meta", "google": "Google Ads"}
HLIDACE = ("vykyvy", "cile", "akce", "kryci-plan")
TYPY_CILU = ("pno", "roas", "cpa", "konverze")
FREKVENCE = ("denne", "pracovni-dny", "tydne", "vlastni")
DNY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

VYCHOZI_PLANOVANI = {"frekvence": "denne", "casy": ["07:30", "19:00"],
                     "akce_casy": ["fri 18:00", "sat 10:00", "sun 10:00"],
                     "timezone": "Europe/Prague"}
VYCHOZI_LIMITY = {"max_denni_rozpocet": None, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30}

_CAS = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ChybaConfigu(SystemExit):
    """Chyba v konfiguraci. Dědí ze SystemExit, ať skript skončí s čitelnou hláškou."""


def _chyba(text: str) -> ChybaConfigu:
    return ChybaConfigu(f"Chyba v konfiguraci hlídačů: {text}")


def _cislo(hodnota, kde: str, kladne: bool = True) -> float:
    if isinstance(hodnota, bool) or not isinstance(hodnota, (int, float)):
        raise _chyba(f"{kde} musí být číslo, je tam {hodnota!r}.")
    if kladne and hodnota <= 0:
        raise _chyba(f"{kde} musí být větší než 0, je tam {hodnota}.")
    return float(hodnota)


def _datum(hodnota, kde: str) -> str:
    try:
        return date.fromisoformat(str(hodnota)).isoformat()
    except ValueError:
        raise _chyba(f"{kde} musí být datum ve tvaru RRRR-MM-DD, je tam {hodnota!r}.") from None


def _planovani(p: dict | None) -> dict:
    out = dict(VYCHOZI_PLANOVANI)
    out.update(p or {})
    if out["frekvence"] not in FREKVENCE:
        raise _chyba(f"planovani.frekvence „{out['frekvence']}“ neznám (povolené: {', '.join(FREKVENCE)}).")
    for c in out.get("casy") or []:
        if not _CAS.match(str(c)):
            raise _chyba(f"planovani.casy: „{c}“ není čas HH:MM (např. 07:30).")
    for c in out.get("akce_casy") or []:
        casti = str(c).split()
        if len(casti) != 2 or casti[0].lower() not in DNY or not _CAS.match(casti[1]):
            raise _chyba(f"planovani.akce_casy: „{c}“ musí být den a čas, např. „fri 18:00“ "
                         f"(dny: {', '.join(DNY)}).")
    return out


def _cile(c: dict, kde: str) -> dict:
    if not isinstance(c, dict):
        raise _chyba(f"{kde}.cile musí být objekt, např. {{\"typ\": \"pno\", \"hodnota\": 15}}.")
    typ = c.get("typ")
    if typ not in TYPY_CILU:
        raise _chyba(f"{kde}.cile.typ „{typ}“ neznám (povolené: {', '.join(TYPY_CILU)}).")
    out = dict(c)
    out["hodnota"] = _cislo(c.get("hodnota"), f"{kde}.cile.hodnota")
    if typ == "pno" and out["hodnota"] >= 100:
        raise _chyba(f"{kde}.cile.hodnota: PNO se zadává v procentech (15 = 15 %), {out['hodnota']} je moc.")
    if typ == "roas" and out["hodnota"] >= 50:
        # ROAS se zadává jako násobek (6 = 600 %). 600 je skoro jistě míněno v procentech.
        out["hodnota"] = out["hodnota"] / 100
    for pole in ("mesicni_rozpocet", "mesicni_obrat"):
        if c.get(pole) is not None:
            out[pole] = _cislo(c[pole], f"{kde}.cile.{pole}")
    return out


def _limity(lim: dict | None, kde: str) -> dict:
    out = dict(VYCHOZI_LIMITY)
    out.update(lim or {})
    if out["max_denni_rozpocet"] is not None:
        out["max_denni_rozpocet"] = _cislo(out["max_denni_rozpocet"], f"{kde}.limity.max_denni_rozpocet")
    for pole in ("max_navyseni_pct", "max_navyseni_tyden_pct"):
        out[pole] = _cislo(out[pole], f"{kde}.limity.{pole}")
        if out[pole] > 100:
            raise _chyba(f"{kde}.limity.{pole}: víc než 100 % najednou hlídač nenavrhne, je tam {out[pole]}.")
    return out


def _ucet(u: dict, i: int) -> dict:
    if not isinstance(u, dict):
        raise _chyba(f"ucty[{i}] musí být objekt.")
    kde = f"účet „{u.get('nazev') or i + 1}“"
    if not u.get("nazev"):
        raise _chyba(f"ucty[{i}] nemá „nazev“.")
    if u.get("system") not in SYSTEMY:
        raise _chyba(f"{kde}: neznámý system „{u.get('system')}“ (povolené: {', '.join(SYSTEMY)}).")
    if u.get("id") in (None, ""):
        raise _chyba(f"{kde}: chybí „id“ (Sklik userId, Meta act_…, Google 123-456-7890).")
    out = dict(u)
    hlidat = u.get("hlidat")
    if hlidat is None:
        out["hlidat"] = list(HLIDACE)
        out["_hlidat_vychozi"] = True
    else:
        if not isinstance(hlidat, list):
            raise _chyba(f"{kde}: „hlidat“ musí být seznam, např. [\"vykyvy\", \"cile\"].")
        for h in hlidat:
            if h not in HLIDACE:
                raise _chyba(f"{kde}: v „hlidat“ je „{h}“ (povolené: {', '.join(HLIDACE)}).")
    if u.get("cile") is not None:
        out["cile"] = _cile(u["cile"], kde)
    elif hlidat is not None and ("cile" in hlidat or "akce" in hlidat):
        raise _chyba(f"{kde}: hlídač cílů a akcí potřebuje blok „cile“ (typ a hodnota).")
    out["limity"] = _limity(u.get("limity"), kde)
    if u.get("posledni_zmena"):
        out["posledni_zmena"] = _datum(u["posledni_zmena"], f"{kde}.posledni_zmena")
    if u.get("min_utrata") is not None:
        _cislo(u["min_utrata"], f"{kde}.min_utrata", kladne=False)
    return out


def rozparsuj(data: dict) -> dict:
    """Ověří a doplní výchozí hodnoty. Vrací {"planovani", "notifikace", "ucty"}."""
    if not isinstance(data, dict) or not isinstance(data.get("ucty"), list):
        raise _chyba('soubor musí obsahovat {"ucty": [...]}.')
    ucty = [_ucet(u, i) for i, u in enumerate(data["ucty"])]
    return {
        "planovani": _planovani(data.get("planovani")),
        "notifikace": dict(data.get("notifikace") or {"kanal": "zadny"}),
        "ucty": [u for u in ucty if not u.get("vypnuto")],
    }


def nacti(cesta: Path | str = VYCHOZI_UCTY) -> dict:
    cesta = Path(cesta)
    if not cesta.exists():
        try:
            vzor = VZOR_UCTY.relative_to(ROOT)
            cil = VYCHOZI_UCTY.relative_to(ROOT)
        except ValueError:
            vzor, cil = VZOR_UCTY, VYCHOZI_UCTY
        raise ChybaConfigu(f"Chybí seznam účtů {cesta}. Zkopíruj vzor {vzor} do {cil} a doplň svoje účty.")
    try:
        data = json.loads(cesta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise _chyba(f"{cesta.name} není platný JSON (řádek {e.lineno}, sloupec {e.colno}: {e.msg}).") from None
    return rozparsuj(data)


def ucty_pro(config: dict, hlidac: str) -> list[dict]:
    """Účty, které má daný hlídač projít (podle pole `hlidat`)."""
    if hlidac not in HLIDACE:
        raise ValueError(hlidac)
    out = []
    for u in config["ucty"]:
        if hlidac not in u["hlidat"]:
            continue
        # Výchozí „všechno“ u starého formátu: cíle a akce jen tam, kde je zadaný cíl.
        if u.get("_hlidat_vychozi") and hlidac in ("cile", "akce", "kryci-plan") and not u.get("cile"):
            continue
        out.append(u)
    return out


def ma_bezet(planovani: dict, den: date) -> bool:
    """Podle `planovani.frekvence`: běží se v daný den? (Plánovač může spouštět denně.)

    denne → vždy · pracovni-dny → po–pá · tydne → jen v pondělí (nebo `planovani.den`,
    např. "fri") · vlastni → vždy (rozhoduje plánovač).
    """
    f = planovani.get("frekvence", "denne")
    if f == "pracovni-dny":
        return den.weekday() < 5
    if f == "tydne":
        return den.weekday() == DNY.get(str(planovani.get("den", "mon")).lower(), 0)
    return True

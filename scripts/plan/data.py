"""Načtení denních dat pro plánování: CSV export, nebo API přes konektory hlídače.

Konektory se nevymýšlejí znovu — volají se `sklik_dny`, `meta_dny`, `google_dny`
ze `scripts/hlidac/zdroje.py` (stejné účty a přístupy jako hlídač). Jen čte.

CSV pro studenty bez API: sloupce `datum, system, naklady, obrat, konverze`
(volitelně `kliky`). Oddělovač čárka nebo středník, desetinná čárka i tečka.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from model import Radek

# sdílené pomocné moduly ze scripts/lib (append → nepřebijí moduly plánu)
sys.path.append(str(Path(__file__).resolve().parents[1]))
from lib.redact import redact as _redact, redact_exc as _redact_exc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HLIDAC = ROOT / "scripts" / "hlidac"
VYCHOZI_UCTY = ROOT / "clients" / "hlidac-ucty.json"
VZOR_UCTY = HLIDAC / "ucty.example.json"
SYSTEMY = ("google", "sklik", "meta")
ALIASY = {"google ads": "google", "gads": "google", "adwords": "google", "seznam": "sklik",
          "facebook": "meta", "fb": "meta", "meta ads": "meta", "instagram": "meta"}


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def normalizuj_system(s: str) -> str:
    s = (s or "").strip().lower()
    return ALIASY.get(s, s)


def _cislo(text: str) -> float:
    t = (text or "").strip().replace("\xa0", "").replace(" ", "")
    if not t:
        return 0.0
    if "," in t and "." in t:          # 1.234,56 nebo 1,234.56
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    else:
        t = t.replace(",", ".")
    return float(t)


def _datum(text: str) -> date:
    t = text.strip()
    m = re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return date.fromisoformat(t[:10])


def nacti_csv(cesta: Path) -> list[Radek]:
    """Načte CSV export. Neznámé sloupce ignoruje, chybějící povinný sloupec = srozumitelná chyba."""
    if not cesta.exists():
        raise SystemExit(f"CSV {cesta} neexistuje.")
    surove = cesta.read_bytes()
    for kod in ("utf-8-sig", "utf-16", "cp1250"):
        try:
            text = surove.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"CSV {cesta}: neznámé kódování (zkus uložit jako UTF-8).")
    prvni = text.splitlines()[0] if text else ""
    oddel = ";" if prvni.count(";") > prvni.count(",") else ","
    ctecka = csv.DictReader(io.StringIO(text), delimiter=oddel)
    sloupce = {slug(c).replace("-", "_"): c for c in (ctecka.fieldnames or [])}
    povinne = ["datum", "system", "naklady", "obrat", "konverze"]
    chybi = [p for p in povinne if p not in sloupce]
    if chybi:
        raise SystemExit(f"CSV {cesta}: chybí sloupce {', '.join(chybi)} "
                         f"(potřebuju {', '.join(povinne)}, volitelně kliky).")
    radky = []
    for i, r in enumerate(ctecka, start=2):
        try:
            radky.append(Radek(
                _datum(r[sloupce["datum"]]), normalizuj_system(r[sloupce["system"]]),
                _cislo(r[sloupce["naklady"]]), _cislo(r[sloupce["obrat"]]),
                _cislo(r[sloupce["konverze"]]),
                _cislo(r[sloupce["kliky"]]) if "kliky" in sloupce else 0.0))
        except (ValueError, KeyError) as e:
            raise SystemExit(f"CSV {cesta}, řádek {i}: {e}")
    if not radky:
        raise SystemExit(f"CSV {cesta} je prázdné.")
    return radky


def uloz_csv(radky: list[Radek], cesta: Path) -> None:
    cesta.parent.mkdir(parents=True, exist_ok=True)
    with cesta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["datum", "system", "naklady", "obrat", "konverze", "kliky"])
        for r in sorted(radky, key=lambda x: (x.datum, x.system)):
            w.writerow([r.datum.isoformat(), r.system, round(r.naklady, 2), round(r.obrat, 2),
                        round(r.konverze, 2), round(r.kliky, 2)])


# ------------------------------------------------------------ konfigurace
def nacti_konfiguraci(cesta: Path) -> dict:
    if not cesta.exists():
        return {"ucty": []}
    data = json.loads(cesta.read_text(encoding="utf-8"))
    if isinstance(data, list):           # úplně stará podoba: jen seznam účtů
        data = {"ucty": data}
    data.setdefault("ucty", [])
    return data


def ucty_klienta(konfigurace: dict, klient: str) -> list[dict]:
    """Účty klienta podle pole `klient` (když chybí, podle slugu `nazev`)."""
    k = slug(klient)
    return [u for u in konfigurace.get("ucty", [])
            if not u.get("vypnuto") and slug(u.get("klient") or u.get("nazev") or "") == k]


def klienti_s_kryci_planem(konfigurace: dict) -> list[str]:
    out = []
    for u in konfigurace.get("ucty", []):
        if u.get("vypnuto") or "kryci-plan" not in (u.get("hlidat") or []):
            continue
        k = slug(u.get("klient") or u.get("nazev") or "")
        if k and k not in out:
            out.append(k)
    return out


def cile_systemu(ucty: list[dict]) -> dict[str, dict]:
    """{system: cile} z konfigurace. Víc účtů v jednom systému → rozpočty a obraty se sečtou."""
    out: dict[str, dict] = {}
    for u in ucty:
        s = normalizuj_system(u.get("system", ""))
        c = dict(u.get("cile") or {})
        if s in out:
            for klic in ("mesicni_rozpocet", "mesicni_obrat"):
                if c.get(klic) is not None:
                    out[s][klic] = (out[s].get(klic) or 0) + c[klic]
        else:
            out[s] = c
        if u.get("limity"):
            out[s].setdefault("_limity", u["limity"])
    return out


# ------------------------------------------------------------ API
def _zdroje():
    sys.path.insert(0, str(HLIDAC))
    import warnings
    warnings.simplefilter("ignore")      # knihovny Googlu na Pythonu 3.9 sypou varování o verzi
    import zdroje  # noqa: E402
    return zdroje


def _stahni_ucet(z, u: dict, od: str, do: str):
    s = normalizuj_system(u.get("system", ""))
    if s == "sklik":
        return z.sklik_dny(int(u["id"]), od, do, u.get("token_var"))
    if s == "meta":
        return z.meta_dny(str(u["id"]), od, do)
    if s == "google":
        return z.google_dny(str(u["id"]), od, do, u.get("profil"))
    raise SystemExit(f"Účet „{u.get('nazev')}“: neznámý system „{u.get('system')}“ (sklik | meta | google).")


def stahni(ucty: list[dict], od: date, do: date, okno_dni: int = 92) -> tuple[list[Radek], list[str]]:
    """Denní součty všech účtů klienta. Po oknech ~3 měsíce, postupně (žádný souběh — API limity).

    Vrací (řádky, varování). Účet, který nejde načíst, se nahlásí a zbytek běží dál.
    """
    z = _zdroje()
    radky: list[Radek] = []
    varovani: list[str] = []
    for u in ucty:
        s = normalizuj_system(u.get("system", ""))
        print(f"  · stahuju {u.get('nazev')} ({s}) {od} → {do}", file=sys.stderr)
        start = od
        try:
            while start <= do:
                konec = min(do, start + timedelta(days=okno_dni - 1))
                dny, _ = _stahni_ucet(z, u, start.isoformat(), konec.isoformat())
                for d in dny:
                    radky.append(Radek(date.fromisoformat(str(d.datum)[:10]), s, float(d.utrata),
                                       float(d.hodnota or 0), float(d.konverze or 0), float(d.prokliky or 0)))
                start = konec + timedelta(days=1)
        except SystemExit as e:
            varovani.append(f"Účet {u.get('nazev')} ({s}) nešel načíst: {_redact(e)}")
        except Exception as e:  # jeden účet nesmí shodit celý plán
            varovani.append(f"Účet {u.get('nazev')} ({s}) nešel načíst: {_redact_exc(e)}")
    return radky, varovani


def nacti_data(klient: str, csv_cesta: Path | None, ucty_cesta: Path, od: date, do: date,
               ulozit_historii: bool = True) -> tuple[list[Radek], list[str]]:
    """CSV, nebo API podle `clients/hlidac-ucty.json`. Stažená data uloží do plans/<klient>/historie.csv."""
    if csv_cesta:
        return nacti_csv(csv_cesta), []
    konf = nacti_konfiguraci(ucty_cesta)
    ucty = ucty_klienta(konf, klient)
    if not ucty:
        raise SystemExit(
            f"Klient „{klient}“ nemá v {ucty_cesta.name} žádný účet (pole \"klient\"). "
            f"Doplň účty podle {VZOR_UCTY.relative_to(ROOT)}, nebo použij --csv s exportem "
            f"(sloupce datum, system, naklady, obrat, konverze).")
    radky, varovani = stahni(ucty, od, do)
    if ulozit_historii and radky:
        cil = ROOT / "plans" / slug(klient) / "historie.csv"
        uloz_csv(radky, cil)
        print(f"  [uloženo] {cil.relative_to(ROOT)} — příště můžeš použít --csv s touto cestou.", file=sys.stderr)
    return radky, varovani

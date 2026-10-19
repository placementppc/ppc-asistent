#!/usr/bin/env python3
"""Hlídač účtů — denně projde vybrané účty (Sklik, Meta, Google Ads) a nahlásí jen ty, které svítí.

Jen čte. V účtech nic nemění.

Použití:
    python3 scripts/hlidac/hlidac.py                 # ráno: vyhodnotí včerejšek
    python3 scripts/hlidac/hlidac.py --dnes          # večer: utíká dnešek, nebo stojí?
    python3 scripts/hlidac/hlidac.py --ucty cesta.json --datum 2026-10-18

Seznam účtů: clients/hlidac-ucty.json (vzor: scripts/hlidac/ucty.example.json).
Hlídá jen účty, které mají v poli `hlidat` hodnotu "vykyvy" (nebo pole nemají vůbec).
Report: vypíše na výstup a uloží do reports/hlidac/<datum>.md (večer <datum>-vecer.md).
Návratový kód: 0 = vše v pořádku, 1 = něco žluté, 2 = něco červené nebo účet nešel načíst.

Metodika a co dělat s nálezy: .claude/skills/hlidac/SKILL.md
"""
from __future__ import annotations

import argparse
import sys
import warnings

# Knihovny Googlu na Pythonu 3.9 sypou varování o verzi; do reportu nepatří.
warnings.simplefilter("ignore")
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import kontroly as k  # noqa: E402
# sdílené pomocné moduly ze scripts/lib (append → nepřebijí moduly hlídače)
sys.path.append(str(Path(__file__).resolve().parents[1]))
from lib.redact import redact, redact_exc  # noqa: E402

ROOT = config.ROOT
VYCHOZI_UCTY = config.VYCHOZI_UCTY
NAZVY_SYSTEMU = config.SYSTEMY


def nacti_ucty(cesta: Path) -> list[dict]:
    """Účty pro hlídač výkyvů: jen ty, které mají v `hlidat` hodnotu „vykyvy“.

    Starý formát {"ucty": [...]} bez `hlidat` dál funguje (hlídá se všechno).
    Validace a srozumitelné chyby: scripts/hlidac/config.py.
    """
    return config.ucty_pro(config.nacti(cesta), "vykyvy")


def stahni(u: dict, od: str, do: str):
    import zdroje
    s = u["system"]
    if s == "sklik":
        return zdroje.sklik_dny(int(u["id"]), od, do, u.get("token_var"))
    if s == "meta":
        return zdroje.meta_dny(str(u["id"]), od, do)
    return zdroje.google_dny(str(u["id"]), od, do, u.get("profil"))


def utrata_dnes(u: dict) -> float | None:
    """Dnešní útrata. Sklik None: neověřili jsme, jak rychle Sklik plní dnešní statistiky."""
    import zdroje
    if u["system"] == "meta":
        return zdroje.meta_dnes(str(u["id"]))
    if u["system"] == "google":
        return zdroje.google_dnes(str(u["id"]), u.get("profil"))
    return None


def zkontroluj(u: dict, den: str, dnes: bool) -> list[k.Nalez]:
    od = (date.fromisoformat(den) - timedelta(days=29)).isoformat()
    dny, nalezy = stahni(u, od, den)
    if dnes:
        zaklad = k.bezny_den(dny, den)
        utraceno = utrata_dnes(u)
        if zaklad and utraceno is not None:
            nalezy += k.vyhodnot_dnes(utraceno, zaklad["utrata"], datetime.now().hour)
        return nalezy
    return nalezy + k.vyhodnot_den(dny, den, float(u.get("min_utrata", 0)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Hlídač účtů (jen čte)")
    ap.add_argument("--ucty", type=Path, default=VYCHOZI_UCTY)
    ap.add_argument("--datum", help="hodnocený den YYYY-MM-DD (výchozí včera, s --dnes dnes)")
    ap.add_argument("--dnes", action="store_true", help="večerní kontrola dnešní útraty")
    a = ap.parse_args()

    den = a.datum or (date.today() if a.dnes else date.today() - timedelta(days=1)).isoformat()
    ucty = nacti_ucty(a.ucty)

    svitici, v_poradku, preskoceno = [], [], []
    for u in ucty:
        jmeno = f"{u['nazev']} ({NAZVY_SYSTEMU[u['system']]})"
        if a.dnes and u["system"] == "sklik":
            preskoceno.append(jmeno)
            continue
        try:
            nalezy = zkontroluj(u, den, a.dnes)
        except SystemExit as e:          # konektory hlásí chyby přes SystemExit
            nalezy = [k.Nalez(k.CERVENA, f"Účet nešel načíst: {redact(e)}")]
        except Exception as e:           # hlídač nesmí kvůli jednomu účtu spadnout celý
            nalezy = [k.Nalez(k.CERVENA, f"Účet nešel načíst: {redact_exc(e)}")]
        (svitici if nalezy else v_poradku).append((jmeno, nalezy))
        print(f"  {'!' if nalezy else '·'} {jmeno}", file=sys.stderr)

    cervene = sum(1 for _, n in svitici if any(x.uroven == k.CERVENA for x in n))
    nadpis = f"Hlídač — {'dnes večer' if a.dnes else 'včera'} {den}"
    if not svitici:
        souhrn = f"✅ Všech {len(v_poradku)} účtů v pořádku."
    else:
        souhrn = f"{'🔴' if cervene else '🟡'} Svítí {len(svitici)} z {len(svitici) + len(v_poradku)} účtů."
    radky = [f"# {nadpis}", "", souhrn, ""]
    for jmeno, nalezy in sorted(svitici, key=lambda x: -sum(n.uroven == k.CERVENA for n in x[1])):
        radky.append(f"## {jmeno}")
        radky += [f"- {'🔴' if n.uroven == k.CERVENA else '🟡'} {n.text}" for n in nalezy]
        radky.append("")
    if v_poradku:
        radky.append("V pořádku: " + ", ".join(j for j, _ in v_poradku) + ".")
    if preskoceno:
        radky.append("Večer nekontrolováno (u Skliku zatím není ověřené, jak rychle plní dnešní data): " + ", ".join(preskoceno) + ".")
    text = "\n".join(radky).rstrip() + "\n"

    out = ROOT / "reports" / "hlidac" / f"{den}{'-vecer' if a.dnes else ''}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"[uloženo] {out.relative_to(ROOT)}", file=sys.stderr)
    return 2 if cervene else (1 if svitici else 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):   # srozumitelná chyba (konfigurace, chybějící účty) → kód 2
            print(redact(e.code), file=sys.stderr)
            sys.exit(2)
        raise

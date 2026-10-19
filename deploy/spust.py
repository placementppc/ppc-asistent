#!/usr/bin/env python3
"""Spouštěč hlídačů pro běh v cronu (GitHub Actions, Vercel, launchd, naplánovaná úloha).

Jen spouští čtecí hlídače ze scripts/ — v účtech nic nemění.

Režimy:
  rano    hlídač výkyvů (včerejšek) + hlídač cílů + krycí plán u klientů, kteří ho mají
  vecer   hlídač výkyvů --dnes (utíká dnešek?)
  akce    hlídač akcí --vikend --dnes (pátek večer: prostor pro škálování přes víkend)
  vikend  hlídač akcí --vikend (sobota, neděle)
  auto    vybere režim podle času v Europe/Prague (pro launchd a ruční spuštění)

Použití:
  python3 deploy/spust.py --rezim rano
  python3 deploy/spust.py --rezim auto --json

Návratový kód: nejhorší z hlídačů (0 OK, 1 žlutá, 2 červená/chyba).
Hlídač, který v appce ještě není, se přeskočí s poznámkou (nepočítá se jako chyba).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
VYCHOZI_UCTY = ROOT / "clients" / "hlidac-ucty.json"
CASOVE_PASMO = "Europe/Prague"
LIMIT_KROKU_S = 600  # jeden hlídač déle než 10 minut = něco visí


def ted() -> datetime:
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo(CASOVE_PASMO))
    return datetime.now()


def rezim_podle_casu(t: datetime) -> str:
    """auto: launchd po probuzení spustí zmeškaný běh jednou, proto rozhoduje čas, ne plán."""
    vikend = t.weekday() >= 5
    if t.hour < 9:
        return "rano"
    if t.hour < 14:
        return "vikend" if vikend else "rano"
    if t.weekday() == 4 and 17 <= t.hour < 19:
        return "akce"
    if t.hour >= 17:
        return "vecer"
    return "rano"


def nacti_klienty_s_planem(ucty: Path) -> list[str]:
    """Klienti, kteří mají v konfiguraci hlídat 'kryci-plan'."""
    try:
        data = json.loads(ucty.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    klienti: list[str] = []
    for u in data.get("ucty", []):
        if u.get("vypnuto"):
            continue
        if "kryci-plan" in (u.get("hlidat") or []) and u.get("klient"):
            if u["klient"] not in klienti:
                klienti.append(u["klient"])
    return klienti


def kroky(rezim: str, ucty: Path) -> list[list[str]]:
    u = ["--ucty", str(ucty)]
    if rezim == "rano":
        seznam = [
            ["scripts/hlidac/hlidac.py", *u],
            ["scripts/hlidac/cile.py", *u],
        ]
        for k in nacti_klienty_s_planem(ucty):
            seznam.append(["scripts/plan/plneni.py", "--klient", k, *u])
        return seznam
    if rezim == "vecer":
        return [["scripts/hlidac/hlidac.py", "--dnes", *u]]
    if rezim == "akce":
        # pátek večer: dnešní tempo + opatrnější víkendový režim (nikdo nebude reagovat do pondělí)
        return [["scripts/hlidac/akce.py", "--vikend", "--dnes", *u]]
    if rezim == "vikend":
        return [["scripts/hlidac/akce.py", "--vikend", *u]]
    raise ValueError(f"neznámý režim: {rezim}")


def spust_krok(argv: list[str]) -> dict:
    skript = ROOT / argv[0]
    vysledek: dict = {"prikaz": "python3 " + " ".join(argv), "exit": 0, "poznamka": ""}
    if not skript.exists():
        vysledek["poznamka"] = "přeskočeno: skript v appce zatím není"
        return vysledek
    if argv[0] == "scripts/plan/plneni.py":
        klient = argv[argv.index("--klient") + 1]
        if not (ROOT / "plans" / klient).exists():
            vysledek["poznamka"] = f"přeskočeno: chybí plans/{klient}/ (nejdřív kryci_plan.py)"
            return vysledek
    try:
        p = subprocess.run(
            [sys.executable, str(skript), *argv[1:]],
            cwd=str(ROOT), capture_output=True, text=True, timeout=LIMIT_KROKU_S,
        )
        vysledek["exit"] = p.returncode
        vysledek["vystup"] = p.stdout[-20000:]
        if p.returncode not in (0, 1, 2):
            vysledek["exit"] = 2
        if p.stderr.strip():
            vysledek["chyby"] = p.stderr[-4000:]
    except subprocess.TimeoutExpired:
        vysledek["exit"] = 2
        vysledek["poznamka"] = f"přerušeno po {LIMIT_KROKU_S} s"
    return vysledek


def nove_reporty(od: float) -> list[str]:
    slozka = ROOT / "reports"
    if not slozka.exists():
        return []
    return sorted(
        str(p.relative_to(ROOT)) for p in slozka.rglob("*.md")
        if p.is_file() and p.stat().st_mtime >= od - 1
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Spouštěč hlídačů pro cron (jen čte)")
    ap.add_argument("--rezim", default="auto", choices=["auto", "rano", "vecer", "akce", "vikend"])
    ap.add_argument("--ucty", type=Path, default=VYCHOZI_UCTY)
    ap.add_argument("--json", action="store_true", help="strojový výstup")
    a = ap.parse_args()

    rezim = rezim_podle_casu(ted()) if a.rezim == "auto" else a.rezim
    ucty = a.ucty if a.ucty.is_absolute() else (Path.cwd() / a.ucty)
    if not ucty.exists():
        msg = f"Chybí konfigurace {ucty} — vzor je ve scripts/hlidac/ucty.example.json."
        if a.json:
            print(json.dumps({"rezim": rezim, "exit": 2, "chyba": msg}, ensure_ascii=False))
        else:
            print("🔴 " + msg)
        return 2

    start = time.time()
    vysledky = [spust_krok(k) for k in kroky(rezim, ucty)]
    nejhorsi = max([v["exit"] for v in vysledky] or [0])
    reporty = nove_reporty(start)

    if a.json:
        print(json.dumps({"rezim": rezim, "exit": nejhorsi, "kroky": vysledky, "reporty": reporty},
                         ensure_ascii=False, indent=2))
    else:
        znacka = {0: "✅", 1: "🟡", 2: "🔴"}.get(nejhorsi, "🔴")
        print(f"{znacka} Režim {rezim} · {ted():%Y-%m-%d %H:%M} ({CASOVE_PASMO})")
        for v in vysledky:
            print(f"- {v['prikaz']} → exit {v['exit']} {v['poznamka']}".rstrip())
            if v.get("vystup"):
                print(v["vystup"].rstrip())
            if v.get("chyby") and v["exit"]:
                print(v["chyby"].rstrip())
        if reporty:
            print("Reporty: " + ", ".join(reporty))
    return nejhorsi


if __name__ == "__main__":
    sys.exit(main())

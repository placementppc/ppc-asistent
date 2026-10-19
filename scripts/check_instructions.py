#!/usr/bin/env python3
"""Kontrola, že instrukce pro AI drží pohromadě.

Proč to existuje: když instrukce pro agenta (`AGENTS.md`, `CLAUDE.md`) odkazují na
soubor nebo adresář, který v repu není, agent hlavní pravidla nenajde, vymyslí si
vlastní postup a začne třeba klikat v administraci místo práce přes skripty.

Rozbitý odkaz v instrukcích je tichá chyba: nic nespadne, jen se AI chová hloupě.
Tenhle skript ji udělá hlasitou.

Co kontroluje:
  1. Existují všechny soubory, na které se v instrukcích odkazuje?
  2. Nevznikla druhá kopie skillů, která by se mohla rozejít s tou pravou?

Použití:
    python3 scripts/check_instructions.py        # vypíše nálezy
    python3 scripts/check_instructions.py --ci   # nenulový návratový kód při chybě
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Soubory, ze kterých se odkazy vytahují.
ENTRY_POINTS = ["AGENTS.md", "CLAUDE.md", ".claude/skills/ppc-fachman/SKILL.md",
                ".claude/skills/start/SKILL.md"]

# Skill musí být fyzicky na jednom místě. Cokoli dalšího je čekající drift.
CANONICAL_SKILLS = ".claude/skills"
FORBIDDEN_SKILL_DIRS = [".agents/skills", ".Codex/skills", ".codex/skills"]

# Odkaz musí obsahovat lomítko, aby šlo o cestu — ne o holý název souboru
# zmíněný ve větě ("spusť pak apply.py"). Ten se ověřit nedá a hlásil by šum.
LINK = re.compile(r"`([A-Za-z0-9_.][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]*)+)`")

# Cesty, které jsou jen příklad, ne skutečný soubor.
PLACEHOLDERS = ("<", "klient", "YYYY", "*", "act_", "_TEMPLATE")

# Cesty, o kterých instrukce ZÁMĚRNĚ píšou, že neexistují (varování pro agenta).
INTENTIONALLY_ABSENT = {".agents/", ".agents/skills", ".Codex/", ".Codex/skills"}

# Cesty, které vznikají až při používání — v čerstvé instalaci chybět MAJÍ.
CREATED_LATER = {
    ".venv/bin/python",   # vytvoří `python3 -m venv .venv`
    "clients/.secret/",   # jen u NDA klientů, gitignorováno
    ".env",               # vytvoří `cp .env.example .env`
    "chatgpt-ads/.env",   # vytvoří `chatgpt-ads/setup.sh`
    "banner-generator/.env.local",  # založí člověk podle docs/napojeni/bannery-ai.md
    "clients/hlidac-ucty.json",     # založí průvodce /start (vzor scripts/hlidac/ucty.example.json)
    "reports/",           # výstupy hlídačů
    "plans/",             # forecast a krycí plány
}


def is_placeholder(path: str) -> bool:
    known = {x.rstrip("/") for x in INTENTIONALLY_ABSENT | CREATED_LATER}
    return any(p in path for p in PLACEHOLDERS) or path.rstrip("/") in known


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []

    # --- 1. rozbité odkazy -------------------------------------------------
    for entry in ENTRY_POINTS:
        f = ROOT / entry
        if not f.exists():
            problems.append(f"chybí vstupní soubor {entry}")
            continue
        for raw in sorted(set(LINK.findall(f.read_text(encoding="utf-8")))):
            if is_placeholder(raw):
                continue
            target = ROOT / raw.rstrip("/")
            if not target.exists():
                problems.append(f"{entry} odkazuje na {raw} — NEEXISTUJE")

    # --- 2. druhá kopie skillů --------------------------------------------
    for d in FORBIDDEN_SKILL_DIRS:
        if (ROOT / d).exists():
            problems.append(
                f"existuje {d} — druhá kopie skillů se rozejde s {CANONICAL_SKILLS}. "
                f"Smaž ji a odkazuj jen na {CANONICAL_SKILLS}."
            )

    if not (ROOT / CANONICAL_SKILLS).is_dir():
        problems.append(f"chybí {CANONICAL_SKILLS} — projekt nemá mozek")

    # --- výpis -------------------------------------------------------------
    if problems:
        print("❌ Instrukce pro AI mají díry:\n")
        for p in problems:
            print(f"   • {p}")
    if notes:
        print("\n⚠️  Doporučení:\n")
        for n in notes:
            print(f"   • {n}")
    if not problems and not notes:
        skills = sorted(p.name for p in (ROOT / CANONICAL_SKILLS).iterdir() if p.is_dir())
        print(f"✅ Instrukce drží. Jedno umístění skillů ({len(skills)}): {', '.join(skills)}")

    if "--ci" in sys.argv and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

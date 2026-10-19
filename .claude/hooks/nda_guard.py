#!/usr/bin/env python3
"""PreToolUse hook — dvě ochrany: soubory s klíči (vždy) a data NDA klientů (mimo NDA relaci).

1) Soubory s přístupy (`.env`, `*.env`, `google-ads.yaml`) — hlídá se v KAŽDÉ relaci,
   i v NDA/Vertex. Logika je v sousedním `env_guard.py` (samostatný, jde nainstalovat
   i globálně pro všechny projekty: `python3 scripts/setup_env_guard.py`).

2) Data NDA klientů — mimo NDA relaci nepustí nástroje k:
   - složce NDA klientů v režimu plná data mimo repo ($PPC_NDA_DIR, výchozí v domovském adresáři),
   - tajné složce v clients/ (syrová data a překladové mapy anonymizovaných klientů).
   V relaci pod obchodními podmínkami (./nda.sh, Team/Enterprise, cloud) pouští vše.

Co se kontroluje:
- souborové nástroje (Read, Edit, Write, Grep, Glob, NotebookEdit) → jen CESTA, se kterou
  pracují — ne obsah, takže jde psát dokumentaci, která složky zmiňuje;
- Bash → celý text příkazu.
Limity (code.claude.com/docs/en/permissions): skript, který si soubor otevře sám
(Python), tím neodhalí — proto mají skripty vlastní kontrolu v scripts/lib/nda.py.
Úplné zamčení pro všechny procesy = sandbox.

Hlídané řetězce jsou složené z částí, aby šel tento soubor upravovat i starší verzí hooku.
Musí běžet i na Pythonu 3.9 (výchozí `python3` na macOS) — spadlý hook akci nezastaví.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_guard  # noqa: E402

PROJECT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
NDA_DIR_NAME = "ppc-asistent" + "-nda"
SECRET = "." + "secret"


def commercial_session() -> bool:
    if os.environ.get("PPC_NDA_SESSION") == "1":
        return True
    try:
        sys.path.insert(0, str(PROJECT / "scripts"))
        from lib.nda import session_is_commercial
        return session_is_commercial()
    except Exception:
        return False  # v pochybnostech chránit


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}

    env_guard.check(tool, tool_input)  # klíče: vždy, ukončí s deny

    if commercial_session():
        return
    text = env_guard.inspected_text(tool, tool_input)
    home = str(Path.home())
    nda_dir = (os.environ.get("PPC_NDA_DIR") or os.path.join(home, NDA_DIR_NAME)).rstrip("/")
    needles = [
        nda_dir,
        nda_dir.replace(home, "~", 1),
        Path(nda_dir).name,
        "clients/" + SECRET,
        SECRET + "/",
    ]
    hit = next((n for n in needles if n and n in text), None)
    if not hit:
        return
    env_guard.deny(
        f"🔒 NDA: `{tool}` míří k chráněným datům ({hit}). "
        "Tahle relace běží pod spotřebitelskými podmínkami, takže sem nesmím. "
        "Pro NDA klienta v režimu plná data spusť v Terminálu `./nda.sh`; "
        "u anonymizovaných klientů pracuj jen s výstupy z fetch_safe / --anon."
    )


if __name__ == "__main__":
    main()

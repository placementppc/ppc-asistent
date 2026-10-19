#!/usr/bin/env python3
"""PreToolUse hook — Claude nesmí číst ani vypisovat soubory s klíči. Platí v každé relaci.

Samostatný, bez závislostí: dá se nakopírovat do ~/.claude/hooks/ a zapnout v uživatelském
nastavení (~/.claude/settings.json), aby platil ve VŠECH projektech na počítači, i budoucích.
Instalace jedním příkazem: `python3 scripts/setup_env_guard.py` (viz docs/nda-rezim.md).
Projektový hook nda_guard.py tenhle soubor importuje — jeden zdroj pravdy.

Co hlídá:
- název souboru s klíči: `.env`, `.env.<cokoli>`, `<cokoli>.env`, `google-ads.yaml`;
  výjimka: vzory končící na .example / .sample / .template / .dist (hodnoty v nich nejsou);
- jen v Bashi navíc okliky: `printenv`, samotné `env`, `os.environ`, `load_dotenv`, `lib.env`.
Souborové nástroje se posuzují podle cesty, Bash podle textu příkazu.

Je to druhá vrstva k `permissions.deny` (Read .env …), které pokrývá nástroj Read a příkazy
cat/head/sed. Tahle vrstva chytí i jednořádkovky (`python -c "open('.env')"`, `source .env`).
Nepokryje skript, který si soubor otevře sám — to je záměr, skripty klíče potřebují pro API.
Cena: Claude neumí ani vytvořit/kopírovat `.env` — to dělá člověk.

Musí běžet i na Pythonu 3.9 (výchozí `python3` na macOS). Když hook spadne, Claude Code akci
PUSTÍ — proto `from __future__ import annotations` a žádná syntaxe z 3.10+.
"""
from __future__ import annotations

import json
import re
import sys

PATH_FIELDS = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Grep": ("path", "glob"),
    "Glob": ("path", "pattern"),
}

# Kandidát na soubor s klíči. Nesmí být kusem delšího slova (`.venv`, `.envrc`, `--env` neplatí).
TOKEN_RE = re.compile(
    r"(?<![\w.\-])(?:\.env(?:\.[\w\-]+)*|[\w\-]+\.env|google-ads\.yaml)(?![\w.\-])"
)
SAFE_SUFFIXES = (".example", ".sample", ".template", ".dist")

# Jen v Bashi: pokusy vypsat prostředí nebo klíče oklikou.
ENV_DUMP_RE = re.compile(
    r"lib[./]env\b|load_dotenv|os\.environ|printenv|(?:^|[;&|(]\s*)env\s*(?:$|[;&|)])",
    re.MULTILINE,
)


def inspected_text(tool: str, tool_input: dict) -> str:
    """Bash → text příkazu; souborové nástroje → jen cesty; ostatní → celý vstup."""
    if tool == "Bash":
        return str(tool_input.get("command") or "")
    fields = PATH_FIELDS.get(tool)
    if fields is None:
        return json.dumps(tool_input, ensure_ascii=False)
    return " ".join(str(tool_input.get(f) or "") for f in fields)


def secret_file(text: str) -> str | None:
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0)
        if not tok.endswith(SAFE_SUFFIXES):
            return tok
    return None


def secrets_hit(tool: str, text: str) -> str | None:
    hit = secret_file(text)
    if hit:
        return hit
    if tool == "Bash":
        m = ENV_DUMP_RE.search(text)
        if m:
            return m.group(0).strip()
    return None


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    sys.exit(2)


def check(tool: str, tool_input: dict) -> None:
    hit = secrets_hit(tool, inspected_text(tool, tool_input))
    if hit:
        deny(
            f"🔐 Klíče: `{tool}` míří na přístupy ({hit}). Soubory s klíči (.env, google-ads.yaml) "
            "do relace nepatří v žádném režimu — skripty si je načtou samy. Když chybí proměnná, "
            "řekni uživateli, ať ji doplní do .env podle .env.example; hodnotu nikdy nevypisuj."
        )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    check(data.get("tool_name") or "", data.get("tool_input") or {})


if __name__ == "__main__":
    main()

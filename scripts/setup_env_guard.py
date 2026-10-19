#!/usr/bin/env python3
"""Zapne zákaz čtení souborů s klíči pro VŠECHNY projekty na tomhle počítači — i budoucí.

Jednorázově (bezpečně opakovatelné, nic cizího nepřepíše):
    python3 scripts/setup_env_guard.py            # provede
    python3 scripts/setup_env_guard.py --dry-run  # jen ukáže, co by změnil

Co udělá v uživatelském nastavení Claude Code (~/.claude/settings.json, případně
$CLAUDE_CONFIG_DIR/settings.json), které platí pro každý projekt, v CLI i v aplikaci Claude
(obě čtou stejné soubory — dokumentace code.claude.com/docs/en/settings):
1. doplní `permissions.deny` pro Read .env, .env.*, *.env, google-ads.yaml
   (výjimky .env.example a .env.*.example) — pokrývá nástroj Read i cat/head/sed v Bashi;
2. nakopíruje .claude/hooks/env_guard.py do ~/.claude/hooks/ a zaregistruje ho jako
   PreToolUse hook (Read|Edit|Write|Grep|Glob|NotebookEdit|Bash) — chytí i okliky v Bashi.
Ostatní klíče v souboru nechá; před zápisem udělá zálohu settings.json.bak.

Nepokryje: cloudové relace (claude.ai/code) — ty uživatelské nastavení nevidí, tam platí
jen .claude/settings.json uvnitř repa (v tomhle repu už je).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_SRC = ROOT / ".claude" / "hooks" / "env_guard.py"
MATCHER = "Read|Edit|Write|Grep|Glob|NotebookEdit|Bash"
# Pořadí je důležité: výjimka (`!`) vyjímá jen z relativních pravidel uvedených PŘED ní.
# Relativní pravidla platí pod složkou, ve které relace běží (= aktuální projekt).
# Pravidla s `//` platí kdekoli na disku (i soubor jiného projektu); výjimku `!` na ně
# udělat nejde, proto jen přesné názvy, které vzorem nikdy nejsou.
DENY_RULES = [
    "Read(.env)",
    "Read(.env.*)",
    "Read(!.env.example)",
    "Read(!.env.*.example)",
    "Read(*.env)",
    "Read(google-ads.yaml)",
    "Read(//**/.env)",
    "Read(//**/*.env)",
    "Read(//**/google-ads.yaml)",
]
# Samotest: stejný `python3`, jaký použije Claude Code. Blokovaný vstup musí skončit 2, běžný 0.
_TEST_BLOCK = {"tool_name": "Bash", "tool_input": {"command": "cat " + "." + "env"}}
_TEST_OK = {"tool_name": "Read", "tool_input": {"file_path": "README.md"}}


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        sys.exit(f"⛔ {path} není platný JSON ({e}). Oprav ho ručně, nic jsem neměnil.")
    if not isinstance(data, dict):
        sys.exit(f"⛔ {path} nemá na nejvyšší úrovni objekt. Nic jsem neměnil.")
    return data


def merge_deny(settings: dict) -> bool:
    perms = settings.setdefault("permissions", {})
    deny = perms.get("deny") or []
    if not isinstance(deny, list):
        sys.exit("⛔ permissions.deny není seznam. Nic jsem neměnil.")
    merged = [r for r in deny if r not in DENY_RULES] + DENY_RULES
    if merged == deny:
        return False
    perms["deny"] = merged
    return True


def hook_registered(settings: dict) -> bool:
    for entry in (settings.get("hooks") or {}).get("PreToolUse") or []:
        for h in entry.get("hooks") or []:
            if HOOK_SRC.name in str(h.get("command") or ""):
                return True
    return False


def register_hook(settings: dict, hook_path: Path) -> bool:
    if hook_registered(settings):
        return False
    pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    pre.append({
        "matcher": MATCHER,
        "hooks": [{
            "type": "command",
            "command": f'python3 "{hook_path}"',
            "timeout": 10,
            "statusMessage": "Kontrola klíčů",
        }],
    })
    return True


def self_test(hook: Path) -> bool:
    """Spustí nainstalovaný hook tím `python3`, který najde PATH — jako Claude Code."""
    py = shutil.which("python3")
    if not py:
        print("⚠️  Nenašel jsem `python3` v PATH — hook se nespustí a ochranu drží jen permissions.deny.")
        return False
    ver = subprocess.run([py, "--version"], capture_output=True, text=True).stdout.strip()
    results = []
    for payload, want in ((_TEST_BLOCK, 2), (_TEST_OK, 0)):
        p = subprocess.run([py, str(hook)], input=json.dumps(payload), capture_output=True, text=True)
        results.append((p.returncode, want, p.stderr.strip()))
    if all(code == want for code, want, _ in results):
        print(f"✅ Samotest hooku prošel ({ver}): soubor s klíči zablokuje, běžný soubor pustí.")
        return True
    print(f"⛔ Samotest hooku SELHAL ({ver}) — hook by akce nezastavil:")
    for code, want, err in results:
        print(f"   exit {code} (čekal jsem {want})" + (f": {err.splitlines()[-1]}" if err else ""))
    print("   Pošli tenhle výpis Claudovi. Pravidla permissions.deny platí i tak.")
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Globální zákaz čtení souborů s klíči v Claude Code.")
    ap.add_argument("--dry-run", action="store_true", help="jen vypsat, co by se změnilo")
    args = ap.parse_args()

    cfg = config_dir()
    settings_path = cfg / "settings.json"
    hook_dst = cfg / "hooks" / HOOK_SRC.name
    settings = load_settings(settings_path)

    changes = []
    if merge_deny(settings):
        changes.append(f"permissions.deny: doplněno {len(DENY_RULES)} pravidel pro soubory s klíči")
    if not (hook_dst.exists() and hook_dst.read_bytes() == HOOK_SRC.read_bytes()):
        changes.append(f"hook: kopie {HOOK_SRC.name} → {hook_dst}")
    if register_hook(settings, hook_dst):
        changes.append("hooks.PreToolUse: zaregistrován env_guard")

    if not changes:
        print(f"✅ Už nastaveno, nic k práci: {settings_path}")
        sys.exit(0 if self_test(hook_dst) else 1)
    for c in changes:
        print(("· " if args.dry_run else "✔ ") + c)
    if args.dry_run:
        print("(dry-run — nic nezapsáno)")
        return

    cfg.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        shutil.copyfile(settings_path, settings_path.parent / "settings.json.bak")
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOOK_SRC, hook_dst)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Zapsáno: {settings_path} (záloha settings.json.bak). Otevřené relace Claude Code restartuj.")
    ok = self_test(hook_dst)
    print("   Ověření v praxi: v nové relaci v libovolném projektu požádej Claude, ať přečte .env —"
          " musí odmítnout hláškou 🔐.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

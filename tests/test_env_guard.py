"""Testy ochrany souborů s klíči: hook .claude/hooks/env_guard.py a instalátor scripts/setup_env_guard.py."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "env_guard.py"
SETUP = ROOT / "scripts" / "setup_env_guard.py"
sys.path.insert(0, str(HOOK.parent))
import env_guard  # noqa: E402


class TokenTest(unittest.TestCase):
    def test_soubory_s_klici_blokuje(self):
        for t in ("cat .env", "open('.env')", "grep X .env.local", ".env.production.local",
                  "cat druhy.env", "vercel env pull .env.local", "cat google-ads.yaml",
                  "~/Development/x/.env", "https://web.cz/.env", "cat .env.example .env"):
            self.assertTrue(env_guard.secret_file(t), t)

    def test_vzory_a_podobna_slova_projdou(self):
        for t in ("cat .env.example", ".env.local.example", "cp .env.sample x", ".env.template",
                  ".env.dist", "source .venv/bin/activate", "cat .envrc", "fetch.py --env prod",
                  "pip install python-dotenv", "echo environment", "scripts/lib/env.py"):
            self.assertIsNone(env_guard.secret_file(t), t)

    def test_okliky_jen_v_bashi(self):
        for cmd in ("printenv", "env", "env | grep X", "ls; env",
                    "python3 -c 'import os; print(os.environ)'",
                    "python3 -c 'from dotenv import load_dotenv'",
                    "python3 -c 'from lib.env import load'"):
            self.assertTrue(env_guard.secrets_hit("Bash", cmd), cmd)
        self.assertIsNone(env_guard.secrets_hit("Bash", "env PYTHONPATH=x python3 a.py"))
        self.assertIsNone(env_guard.secrets_hit("Bash", "python3 scripts/google_ads/fetch.py"))
        self.assertIsNone(env_guard.secrets_hit("Read", "docs/printenv.md"))


def run_hook(hook: Path, payload) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stdout


class HookProcessTest(unittest.TestCase):
    def test_read_env_deny(self):
        code, out = run_hook(HOOK, {"tool_name": "Read", "tool_input": {"file_path": "/Users/uzivatel/proj/.env"}})
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_obsah_zapisu_se_nekontroluje(self):
        code, out = run_hook(HOOK, {"tool_name": "Write", "tool_input": {
            "file_path": "docs/x.md", "content": "v textu se zmiňuje .env, to je v pořádku"}})
        self.assertEqual((code, out), (0, ""))

    def test_rozbity_vstup_neshodi_nastroj(self):
        p = subprocess.run([sys.executable, str(HOOK)], input="není json", capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


class OldPythonTest(unittest.TestCase):
    """macOS má jako `python3` často 3.9. Spadlý hook (exit 1) Claude Code akci PUSTÍ."""

    def test_hooky_bezi_na_pythonu_3_9(self):
        py = shutil.which("python3.9")
        if not py:
            self.skipTest("python3.9 není v PATH")
        block = json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat " + "." + "env"}})
        ok = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})
        for hook in (HOOK, HOOK.parent / "nda_guard.py"):
            p = subprocess.run([py, str(hook)], input=block, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, (hook.name, p.stderr))
            p = subprocess.run([py, str(hook)], input=ok, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, (hook.name, p.stderr))


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.settings = self.cfg / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_setup(self, *args):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), HOME=self.tmp.name)
        return subprocess.run([sys.executable, str(SETUP), *args], capture_output=True, text=True, env=env)

    def test_zachova_cizi_nastaveni_a_je_idempotentni(self):
        self.settings.write_text(json.dumps({
            "model": "opus",
            "permissions": {"deny": ["Read(~/.ssh/**)"], "allow": ["Bash(npm test)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}]},
        }), encoding="utf-8")
        p = self.run_setup()
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["permissions"]["allow"], ["Bash(npm test)"])
        deny = s["permissions"]["deny"]
        self.assertEqual(deny[0], "Read(~/.ssh/**)")
        for r in ("Read(.env)", "Read(.env.*)", "Read(!.env.example)", "Read(*.env)", "Read(google-ads.yaml)",
                  "Read(//**/.env)", "Read(//**/google-ads.yaml)"):
            self.assertIn(r, deny)
        self.assertIn("Samotest hooku prošel", p.stdout)
        self.assertLess(deny.index("Read(.env.*)"), deny.index("Read(!.env.example)"))
        self.assertEqual(len(s["hooks"]["PreToolUse"]), 2)
        self.assertIn("env_guard.py", s["hooks"]["PreToolUse"][1]["hooks"][0]["command"])
        self.assertTrue((self.cfg / "hooks" / "env_guard.py").exists())
        self.assertTrue((self.cfg / "settings.json.bak").exists())
        p2 = self.run_setup()
        self.assertIn("Už nastaveno", p2.stdout)
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")), s)

    def test_dry_run_nezapise_a_instalace_zalozi_soubor(self):
        p = self.run_setup("--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(self.settings.exists())
        p = self.run_setup()
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertIn("Read(.env)", s["permissions"]["deny"])
        self.assertEqual(len(s["hooks"]["PreToolUse"]), 1)

    def test_nainstalovany_hook_funguje(self):
        self.run_setup()
        installed = self.cfg / "hooks" / "env_guard.py"
        code, _ = run_hook(installed, {"tool_name": "Bash", "tool_input": {"command": "cat .env"}})
        self.assertEqual(code, 2)
        code, out = run_hook(installed, {"tool_name": "Bash", "tool_input": {"command": "cat .env.example"}})
        self.assertEqual((code, out), (0, ""))

    def test_rozbity_json_neprepise(self):
        self.settings.write_text("{nope", encoding="utf-8")
        p = self.run_setup()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{nope")


if __name__ == "__main__":
    unittest.main()

"""Testy NDA režimu: scripts/lib/nda.py, hook .claude/hooks/nda_guard.py, sanitize --reverse.

Spuštění:  .venv/bin/python -m unittest tests/test_nda.py -v
Testy nesahají na reálné klienty ani na tajnou složku — pracují v dočasných adresářích.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import nda  # noqa: E402

HOOK = ROOT / ".claude" / "hooks" / "nda_guard.py"
SECRET = "." + "secret"

MD_PLNA = """# Klient
## 3. Účty a přístupy
- **NDA:** true
- **NDA režim:** plna-data
- **NDA účty:** google:123-456-7890, meta:act_555, ga4:999
"""
MD_ANON = """- **NDA:** **true** (potvrzeno)
- **NDA režim:** anonymizace (poznámka)
- **NDA účty:** sklik:424242
"""
MD_BEZ_REZIMU = "- **NDA:** true\n- **NDA účty:** google:111-222-3333\n"
MD_BEZ_NDA = "- **NDA:** false (potvrzeno)\n- **NDA účty:** google:777-777-7777\n"


class TempWorld(unittest.TestCase):
    """Dočasné clients/, NDA složka a HOME s ~/.claude.json."""

    org_type = "claude_max"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.clients = base / "clients"
        (self.clients / SECRET).mkdir(parents=True)
        self.home = base / "home"
        self.home.mkdir()
        (self.home / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"organizationType": self.org_type}}), encoding="utf-8")
        self.ndadir = base / "nda"
        (self.ndadir / "tajny").mkdir(parents=True)
        (self.ndadir / "tajny" / "tajny.md").write_text(MD_PLNA, encoding="utf-8")
        (self.clients / "anon.md").write_text(MD_ANON, encoding="utf-8")
        (self.clients / "bezrezimu.md").write_text(MD_BEZ_REZIMU, encoding="utf-8")
        (self.clients / "verejny.md").write_text(MD_BEZ_NDA, encoding="utf-8")
        (self.clients / "_TEMPLATE.md").write_text(MD_PLNA, encoding="utf-8")
        (self.clients / "secretacc.md").write_text("- **NDA:** true\n- **NDA režim:** anonymizace\n",
                                                   encoding="utf-8")
        (self.clients / SECRET / "secretacc-account.json").write_text(
            json.dumps({"google_ads_customer_id": "444-555-6666", "note": "x"}), encoding="utf-8")
        self.patches = [
            mock.patch.object(nda, "CLIENTS_DIR", self.clients),
            mock.patch.object(nda, "SECRET_DIR", self.clients / SECRET),
            mock.patch.dict(os.environ, {"HOME": str(self.home), "PPC_NDA_DIR": str(self.ndadir),
                                         "CLAUDECODE": "1"}, clear=False),
        ]
        for p in self.patches:
            p.start()
        for v in ("PPC_NDA_SESSION", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                  "CLAUDE_CODE_USE_FOUNDRY"):
            os.environ.pop(v, None)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()


class ParseTest(unittest.TestCase):
    def test_plna_data(self):
        c = nda.parse_client_md(MD_PLNA, "x")
        self.assertTrue(c.nda)
        self.assertEqual(c.mode, "plna-data")
        self.assertEqual(c.accounts, {"1234567890", "act_555", "999"})

    def test_tucne_true_a_poznamka(self):
        c = nda.parse_client_md(MD_ANON, "x")
        self.assertTrue(c.nda)
        self.assertEqual(c.mode, "anonymizace")
        self.assertEqual(c.accounts, {"424242"})

    def test_false_a_neznamy_rezim(self):
        self.assertFalse(nda.parse_client_md(MD_BEZ_NDA, "x").nda)
        c = nda.parse_client_md("- **NDA:** true\n- **NDA režim:** něco\n", "x")
        self.assertIsNone(c.mode)

    def test_norm_account(self):
        self.assertEqual(nda.norm_account("google:987-654-3210"), "9876543210")
        self.assertEqual(nda.norm_account("ACT_12"), "act_12")
        self.assertEqual(nda.norm_account(9876543210), "9876543210")


class GuardConsumerTest(TempWorld):
    def test_verejny_klient_prochazi(self):
        nda.guard("777-777-7777", "read-raw")
        nda.guard("000-000-0000", "read-raw")  # neznámý účet

    def test_plna_data_ve_spotrebitelske_relaci_blokuje(self):
        with self.assertRaises(nda.NdaBlocked) as e:
            nda.guard("1234567890", "write")
        self.assertIn("nda.sh", str(e.exception))

    def test_anonymizace_blokuje_jen_syrove_cteni(self):
        with self.assertRaises(nda.NdaBlocked):
            nda.guard(424242, "read-raw")
        nda.guard(424242, "read-anon")
        nda.guard(424242, "write")
        nda.guard(424242, "any")

    def test_bez_rezimu_blokuje(self):
        for kind in ("read-raw", "read-anon", "write", "any"):
            with self.assertRaises(nda.NdaBlocked):
                nda.guard("111-222-3333", kind)

    def test_ucet_z_tajne_slozky(self):
        with self.assertRaises(nda.NdaBlocked):
            nda.guard("4445556666", "read-raw")

    def test_sablona_se_ignoruje(self):
        slugs = {c.slug for c in nda.load_clients()}
        self.assertNotIn("_TEMPLATE", slugs)
        self.assertIn("tajny", slugs)

    def test_mimo_claude_code_nic_neblokuje(self):
        with mock.patch.dict(os.environ, {"CLAUDECODE": ""}):
            nda.guard("1234567890", "read-raw")
            nda.guard("111-222-3333", "read-raw")

    def test_filtr_vypisu(self):
        rows = [{"id": 1234567890}, {"id": "act_555"}, {"id": 7777777777}]
        self.assertEqual(nda.filter_listing(rows), [{"id": 7777777777}])


class GuardNdaSessionTest(TempWorld):
    def test_nda_relace_pousti_plna_data(self):
        with mock.patch.dict(os.environ, {"PPC_NDA_SESSION": "1"}):
            self.assertEqual(nda.session_kind()[0], "obchodni")
            nda.guard("1234567890", "read-raw")
            rows = [{"id": 1234567890}]
            self.assertEqual(nda.filter_listing(rows), rows)

    def test_anonymizace_v_nda_relaci_stale_bez_syrovych_dat(self):
        with mock.patch.dict(os.environ, {"PPC_NDA_SESSION": "1"}):
            with self.assertRaises(nda.NdaBlocked):
                nda.guard(424242, "read-raw")


class GuardTeamLoginTest(TempWorld):
    org_type = "claude_team"

    def test_firemni_prihlaseni_je_obchodni(self):
        self.assertEqual(nda.session_kind()[0], "obchodni")
        nda.guard("1234567890", "read-raw")


def run_hook(payload, **env):
    e = {k: v for k, v in os.environ.items() if k != "PPC_NDA_SESSION"}
    e.update(env)
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stdout


class HookTest(TempWorld):
    def env(self):
        return {"HOME": str(self.home), "PPC_NDA_DIR": str(self.ndadir), "CLAUDE_PROJECT_DIR": str(ROOT)}

    def test_cteni_tajne_slozky_blokuje(self):
        code, out = run_hook({"tool_name": "Read",
                              "tool_input": {"file_path": f"clients/{SECRET}/x.json"}}, **self.env())
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_nda_slozka_v_bashi_blokuje(self):
        code, _ = run_hook({"tool_name": "Bash", "tool_input": {"command": f"cat {self.ndadir}/tajny/tajny.md"}},
                           **self.env())
        self.assertEqual(code, 2)

    def test_grep_a_glob_podle_cesty(self):
        for payload in ({"tool_name": "Grep", "tool_input": {"pattern": "x", "path": str(self.ndadir)}},
                        {"tool_name": "Glob", "tool_input": {"pattern": f"clients/{SECRET}/*"}}):
            self.assertEqual(run_hook(payload, **self.env())[0], 2)

    def test_zapis_dokumentace_se_zminkou_projde(self):
        code, _ = run_hook({"tool_name": "Write", "tool_input": {
            "file_path": str(ROOT / "docs" / "x.md"),
            "content": f"složka clients/{SECRET}/ a {self.ndadir}"}}, **self.env())
        self.assertEqual(code, 0)

    def test_hledani_textu_v_repu_projde(self):
        code, _ = run_hook({"tool_name": "Grep", "tool_input": {"pattern": f"{SECRET}/", "path": "scripts"}},
                           **self.env())
        self.assertEqual(code, 0)

    def test_bezny_soubor_projde(self):
        code, out = run_hook({"tool_name": "Read", "tool_input": {"file_path": "clients/verejny.md"}},
                             **self.env())
        self.assertEqual((code, out), (0, ""))

    def test_nda_relace_pusti(self):
        code, _ = run_hook({"tool_name": "Read", "tool_input": {"file_path": f"clients/{SECRET}/x.json"}},
                           PPC_NDA_SESSION="1", **self.env())
        self.assertEqual(code, 0)

    def test_rozbity_vstup_neshodi_nastroj(self):
        p = subprocess.run([sys.executable, str(HOOK)], input="není json", capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)

    def test_klice_blokuje_vzdy_i_v_nda_relaci(self):
        prikazy = (
            "cat .env",
            "cat .env",
            "grep TOKEN .env.local",
            "source .env && python3 x.py",
            "python3 -c \"print(open('.env').read())\"",
            "cat google-ads.yaml",
            "cat druhy.env",
            "python3 -c \"from lib.env import load; print(load())\"",
            "python3 -c 'import os; print(os.environ)'",
            "printenv | grep SKLIK",
            "env | grep GOOGLE",
            "env",
        )
        for cmd in prikazy:
            for extra in ({}, {"PPC_NDA_SESSION": "1"}, {"CLAUDE_CODE_USE_VERTEX": "1"}):
                code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}},
                                     **self.env(), **extra)
                self.assertEqual(code, 2, (cmd, extra))
                self.assertIn("Klíče", json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"])
        for path in (".env", "/Users/uzivatel/projekt/.env", "clients/.env.local", "google-ads.yaml"):
            code, _ = run_hook({"tool_name": "Read", "tool_input": {"file_path": path}},
                               PPC_NDA_SESSION="1", **self.env())
            self.assertEqual(code, 2, path)

    def test_vzor_env_a_bezne_prikazy_projdou(self):
        prikazy = (
            "cat .env.example",
            "python3 scripts/google_ads/fetch.py --customer 123",
            ".venv/bin/python scripts/sklik/fetch.py --user-id 1",
            "source .venv/bin/activate",
            "env PYTHONPATH=scripts python3 x.py",
            "echo environment setup",
            "sklik/fetch.py --env prod",
            "cat .envrc",
        )
        for cmd in prikazy:
            code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, **self.env())
            self.assertEqual((code, out), (0, ""), cmd)
        for path in (".env.example", "scripts/lib/env.py", "docs/navod-google-ads-pristupy.md"):
            code, out = run_hook({"tool_name": "Read", "tool_input": {"file_path": path}}, **self.env())
            self.assertEqual((code, out), (0, ""), path)


class SanitizeReverseTest(TempWorld):
    def test_zpetny_preklad_se_ve_spotrebitelske_relaci_nevypise(self):
        src = Path(self.tmp.name) / "plan.json"
        src.write_text("{}", encoding="utf-8")
        e = dict(os.environ)
        e.pop("PPC_NDA_SESSION", None)
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "sanitize.py"), "--client", "zzz-test",
                            "--reverse", "--in", str(src)], capture_output=True, text=True, env=e)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("NDA", p.stderr)


if __name__ == "__main__":
    unittest.main()

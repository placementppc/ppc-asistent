#!/usr/bin/env python3
"""Stav instalace pro průvodce /start — co je hotové a co chybí. Jen čte, nic nemění.

Soubory s klíči NEOTVÍRÁ: u `.env`, `chatgpt-ads/.env` a `banner-generator/.env.local`
zjistí jen, jestli existují. Jestli klíče fungují, ověří až read-only skripty
(`scripts/google_ads/fetch.py --list-clients` a spol., viz docs/napojeni/).

Výjimka `--ai`: ověří klíče pro AI bannery (Gemini, volitelně OpenAI) jedním bezplatným
dotazem na seznam modelů. Klíč si přečte sám, nikam ho nevypisuje, vrátí jen OK / CHYBA.

Použití:
    python3 scripts/start/stav.py          # přehled pro člověka
    python3 scripts/start/stav.py --json   # strojově (průvodce /start)
    python3 scripts/start/stav.py --ai     # navíc ověří klíče pro bannery

Návratový kód: 0 vždy (je to přehled, ne kontrola).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOUBOR_KLICU = "." + "env"  # složeno, ať text skriptu nevypadá jako práce se souborem klíčů


def _je(p: Path) -> bool:
    return p.exists()


def _klienti() -> list[str]:
    d = ROOT / "clients"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md")
                  if not p.name.startswith("_") and p.name != "README.md" and "-coverage" not in p.stem)


def _nda_klienti() -> tuple[dict, set[str]]:
    """Počty NDA klientů + množina jejich slugů (jen pro interní filtrování).

    Jména NDA klientů se nikam nevypisují — ani do přehledu, ani do --json
    (výstup čte AI i člověk, který může sdílet obrazovku).
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from lib.nda import load_clients
    except Exception:
        return {"pocet": 0, "bez_rezimu": 0}, set()
    nda = [c for c in load_clients() if c.nda]
    return ({"pocet": len(nda), "bez_rezimu": sum(1 for c in nda if not c.mode)},
            {c.slug for c in nda})


def _bez_nda_udaje(klienti: list[str]) -> list[str]:
    """Klienti (mimo NDA), v jejichž .md ještě chybí řádek `- **NDA:** …`."""
    import re
    pole = re.compile(r"^\s*-\s*\*\*NDA:\*\*", re.IGNORECASE | re.MULTILINE)
    out = []
    for k in klienti:
        try:
            text = (ROOT / "clients" / f"{k}.md").read_text(encoding="utf-8")
        except OSError:
            continue
        if not pole.search(text):
            out.append(k)
    return out


def _klienti_pocet(n: int) -> str:
    if n == 1:
        return "1 klient"
    return f"{n} klienti" if 2 <= n <= 4 else f"{n} klientů"


def _hlidac() -> dict:
    p = ROOT / "clients" / "hlidac-ucty.json"
    if not p.exists():
        return {"existuje": False}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"existuje": True, "chyba": f"neplatný JSON: {e}"}
    ucty = data.get("ucty") if isinstance(data, dict) else None
    if not isinstance(ucty, list):
        return {"existuje": True, "chyba": "chybí pole `ucty`"}
    systemy: dict[str, int] = {}
    hlidat: dict[str, int] = {}
    for u in ucty:
        if u.get("vypnuto"):
            continue
        systemy[u.get("system", "?")] = systemy.get(u.get("system", "?"), 0) + 1
        for h in u.get("hlidat") or ["vykyvy"]:
            hlidat[h] = hlidat.get(h, 0) + 1
    return {
        "existuje": True,
        "uctu": len(ucty),
        "systemy": systemy,
        "hlidat": hlidat,
        "planovani": bool(data.get("planovani")),
        "notifikace": (data.get("notifikace") or {}).get("kanal", "nenastaveno"),
    }


def _guard_globalne() -> bool:
    """Je env_guard zapnutý i v uživatelském nastavení (setup_env_guard.py)?"""
    import os
    cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
    try:
        return "env_guard" in (cfg / "settings.json").read_text(encoding="utf-8")
    except OSError:
        return False


def _brand_manualy() -> list[str]:
    d = ROOT / "banner-generator"
    return sorted(p.parent.name.removeprefix("banners-") for p in d.glob("banners-*/BRAND-MANUAL.md"))


def stav() -> dict:
    klienti = _klienti()
    nda, nda_slugy = _nda_klienti()
    return {
        "python_venv": _je(ROOT / ".venv"),
        "env_soubor": _je(ROOT / SOUBOR_KLICU),
        "env_guard_v_projektu": _je(ROOT / ".claude" / "hooks" / "env_guard.py"),
        "env_guard_globalne": _guard_globalne(),
        "chatgpt_ads_venv": _je(ROOT / "chatgpt-ads" / ".venv"),
        "chatgpt_ads_env": _je(ROOT / "chatgpt-ads" / SOUBOR_KLICU),
        "bannery_node_modules": _je(ROOT / "banner-generator" / "node_modules"),
        "bannery_env_local": _je(ROOT / "banner-generator" / (SOUBOR_KLICU + ".local")),
        "klienti": [k for k in klienti if k not in nda_slugy],
        "nda_klienti": nda,
        "klienti_bez_nda_udaje": _bez_nda_udaje([k for k in klienti if k not in nda_slugy]),
        "hlidac": _hlidac(),
        "brand_manualy": _brand_manualy(),
        "nda_relace_skript": _je(ROOT / "nda.sh"),
    }


# ------------------------------------------------------------------ ověření AI klíčů
def _klic_z_local(nazev: str) -> str | None:
    """Stejné čtení jako banner-generator/generate-banners*.ts: řádek NAZEV=hodnota."""
    p = ROOT / "banner-generator" / (SOUBOR_KLICU + ".local")
    try:
        for radek in p.read_text(encoding="utf-8").splitlines():
            radek = radek.strip()
            if radek.startswith(nazev) and "=" in radek and radek.split("=", 1)[0].strip() == nazev:
                v = radek.split("=", 1)[1].strip().strip("\"'")
                return v if v and not v.startswith("your-") else None
    except OSError:
        return None
    return None


def _get(url: str, hlavicky: dict) -> str:
    req = urllib.request.Request(url, headers=hlavicky, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return "OK" if r.status == 200 else f"CHYBA HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"CHYBA HTTP {e.code} (klíč neplatný, bez oprávnění nebo vyčerpaný limit)"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"CHYBA sítě: {getattr(e, 'reason', e)}"


def over_ai() -> dict:
    out = {}
    g = _klic_z_local("GEMINI_API_KEY")
    out["gemini"] = "chybí GEMINI_API_KEY" if not g else _get(
        "https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": g})
    o = _klic_z_local("OPENAI_API_KEY")
    out["openai"] = "nevyplněno (volitelné)" if not o else _get(
        "https://api.openai.com/v1/models", {"Authorization": f"Bearer {o}"})
    return out


def lidsky(s: dict) -> str:
    ano = lambda b: "✅" if b else "⬜"  # noqa: E731
    h = s["hlidac"]
    radky = [
        "Stav PPC asistenta",
        f"  {ano(s['python_venv'])} Python prostředí (.venv)",
        f"  {ano(s['env_soubor'])} soubor s přístupy v kořeni (jen existence, obsah se nečte)",
        f"  {ano(s['env_guard_v_projektu'])} hook proti čtení klíčů v projektu",
        f"  {ano(s['env_guard_globalne'])} hook proti čtení klíčů pro všechny projekty (setup_env_guard.py)",
        f"  {ano(s['chatgpt_ads_venv'] and s['chatgpt_ads_env'])} ChatGPT Ads (chatgpt-ads/setup.sh + vlastní soubor s klíčem)",
        f"  {ano(s['bannery_node_modules'] and s['bannery_env_local'])} AI bannery (npm install + banner-generator/.env.local)",
        f"  {ano(bool(s['klienti']) or bool(s['nda_klienti']['pocet']))} klienti: "
        f"{', '.join(s['klienti']) or ('žádný' if not s['nda_klienti']['pocet'] else '–')}",
    ]
    n = s["nda_klienti"]
    if n["pocet"]:
        txt = f"     NDA: {_klienti_pocet(n['pocet'])} pod NDA"
        if n["bez_rezimu"]:
            txt += f" (bez zvoleného režimu: {n['bez_rezimu']} — doplň `NDA režim` v jejich .md)"
        radky.append(txt)
    if not h.get("existuje"):
        radky.append("  ⬜ hlídače: clients/hlidac-ucty.json chybí")
    elif h.get("chyba"):
        radky.append(f"  ⚠️ hlídače: {h['chyba']}")
    else:
        radky.append(f"  ✅ hlídače: {h['uctu']} účtů {h['systemy']}, hlídá {h['hlidat']}, "
                     f"plánování {'ano' if h['planovani'] else 'ne'}, notifikace {h['notifikace']}")
    radky.append(f"  {ano(bool(s['brand_manualy']))} brand manuály: {', '.join(s['brand_manualy']) or 'žádný'}")
    if "ai" in s:
        radky.append(f"  AI klíče: Gemini {s['ai']['gemini']} · OpenAI {s['ai']['openai']}")
    return "\n".join(radky)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stav instalace pro průvodce /start (jen čte)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ai", action="store_true", help="ověř klíče pro AI bannery (Gemini/OpenAI)")
    a = ap.parse_args()
    s = stav()
    if a.ai:
        s["ai"] = over_ai()
    print(json.dumps(s, ensure_ascii=False, indent=2) if a.json else lidsky(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

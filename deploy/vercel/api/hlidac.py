"""Vercel Function: spustí hlídače PPC asistenta (jen čtou, v účtech nic nemění).

Volá ji Vercel Cron (vercel.json). Ověří hlavičku `Authorization: Bearer <CRON_SECRET>`,
podle hlavičky `x-vercel-cron-schedule` vybere režim, spustí deploy/spust.py a vrátí JSON.

Ruční test (stejný secret): GET /api/hlidac?rezim=rano s hlavičkou Authorization.

Proměnné prostředí (Vercel → Settings → Environment Variables), jen NÁZVY:
  CRON_SECRET            náhodný řetězec, aspoň 16 znaků (Vercel ho posílá v Authorization)
  HLIDAC_UCTY_JSON       obsah clients/hlidac-ucty.json
  GOOGLE_ADS_*, SKLIK_API_TOKEN, META_API_TOKEN   přístupy jako v .env
  PPC_DALSI_PROMENNE     volitelné: další názvy proměnných do .env, oddělené čárkou
"""
from __future__ import annotations

import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BALIK = Path(__file__).resolve().parents[1] / "balik"  # vytvoří priprav.sh
PRISTUPY = [
    "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    "SKLIK_API_TOKEN", "META_API_TOKEN",
]
# Vercel Cron běží v UTC; musí sedět s vercel.json
REZIM_PODLE_PLANU = {
    "30 5 * * *": "rano",
    "0 17 * * *": "vecer",
    "0 16 * * 5": "akce",
    "0 8 * * 0,6": "vikend",
}
REZIMY = {"rano", "vecer", "akce", "vikend", "auto"}
LIMIT_S = 280  # Hobby i výchozí Pro limit funkce je 300 s


def priprav_pracovni_slozku() -> Path:
    """Balík zkopíruje do /tmp, protože hlídače zapisují reporty a čtou .env z kořene."""
    prac = Path(tempfile.gettempdir()) / "ppc-asistent"
    if prac.exists():
        shutil.rmtree(prac, ignore_errors=True)
    shutil.copytree(BALIK, prac)
    (prac / "clients").mkdir(exist_ok=True)

    nazvy = list(PRISTUPY)
    nazvy += [n.strip() for n in os.environ.get("PPC_DALSI_PROMENNE", "").split(",") if n.strip()]
    radky = []
    for n in nazvy:
        hodnota = os.environ.get(n, "")
        if hodnota and "\n" not in hodnota:
            radky.append(f"{n}={hodnota}")
    env_soubor = prac / ".env"
    env_soubor.write_text("\n".join(radky) + "\n", encoding="utf-8")
    os.chmod(env_soubor, 0o600)

    konfigurace = os.environ.get("HLIDAC_UCTY_JSON", "")
    json.loads(konfigurace)  # ValueError = špatný JSON → 500 s hláškou níž
    (prac / "clients" / "hlidac-ucty.json").write_text(konfigurace, encoding="utf-8")
    return prac



def souhrn(data: dict, rezim: str, kod: int) -> dict:
    """Jen stav a počty. Odpověď končí v logu Vercelu (vidí ho každý s přístupem
    k projektu), proto v ní nesmí být obsah reportů, názvy účtů ani příkazy."""
    kroky = data.get("kroky") or []
    preskoceno = sum(1 for k in kroky if str(k.get("poznamka", "")).startswith("přeskočeno"))
    return {
        "ok": kod in (0, 1, 2),
        "rezim": data.get("rezim", rezim),
        "exit": data.get("exit", kod),
        "kroku": len(kroky),
        "v_poradku": sum(1 for k in kroky if k.get("exit") == 0) - preskoceno,
        "zlute": sum(1 for k in kroky if k.get("exit") == 1),
        "cervene": sum(1 for k in kroky if k.get("exit") == 2),
        "preskoceno": preskoceno,
        "reportu": len(data.get("reporty") or []),
    }

class handler(BaseHTTPRequestHandler):
    def _odpoved(self, kod: int, data: dict) -> None:
        telo = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(telo)

    def do_GET(self) -> None:  # noqa: N802 (název určuje BaseHTTPRequestHandler)
        tajemstvi = os.environ.get("CRON_SECRET", "")
        prislo = self.headers.get("authorization", "")
        if not tajemstvi or not hmac.compare_digest(prislo, f"Bearer {tajemstvi}"):
            self._odpoved(401, {"ok": False, "chyba": "neoprávněný požadavek"})
            return

        plan = self.headers.get("x-vercel-cron-schedule", "")
        dotaz = parse_qs(urlparse(self.path).query)
        rezim = REZIM_PODLE_PLANU.get(plan) or (dotaz.get("rezim") or ["auto"])[0]
        if rezim not in REZIMY:
            self._odpoved(400, {"ok": False, "chyba": f"neznámý režim {rezim}"})
            return
        if not os.environ.get("HLIDAC_UCTY_JSON"):
            self._odpoved(500, {"ok": False, "chyba": "chybí proměnná HLIDAC_UCTY_JSON"})
            return

        try:
            prac = priprav_pracovni_slozku()
        except ValueError:
            self._odpoved(500, {"ok": False, "chyba": "HLIDAC_UCTY_JSON není platný JSON"})
            return
        except OSError as e:
            self._odpoved(500, {"ok": False, "chyba": f"nejde připravit pracovní složku: {e.strerror}"})
            return

        try:
            p = subprocess.run(
                [sys.executable, "deploy/spust.py", "--rezim", rezim, "--json"],
                cwd=str(prac), capture_output=True, text=True, timeout=LIMIT_S,
            )
        except subprocess.TimeoutExpired:
            self._odpoved(504, {"ok": False, "rezim": rezim,
                                "chyba": f"hlídač nedoběhl do {LIMIT_S} s — rozděl účty nebo použij GitHub Actions"})
            return

        try:
            data = json.loads(p.stdout)
        except ValueError:
            # Syrový výstup nevracíme — mohou v něm být názvy účtů a čísla.
            self._odpoved(500, {"ok": False, "rezim": rezim, "exit": p.returncode,
                                "chyba": "hlídač nevrátil platný JSON — spusť ho ručně a podívej se na výstup"})
            return
        # 200 i při nálezech (exit 1/2) — nález není chyba funkce. Stav je v poli "exit".
        self._odpoved(200, souhrn(data, rezim, p.returncode))
        # Tady je místo pro notifikaci (viz docs/notifikace.md) — zatím se nikam nic neposílá.

"""NDA režim — kdo smí vidět data NDA klienta a za jakých podmínek.

Proč: data se v Claude Code posílají na servery Anthropicu. Na spotřebitelském
tarifu platí spotřebitelské podmínky, na API / Team / Enterprise
obchodní podmínky bez tréninku a s DPA (ověřeno 2026-09-16:
code.claude.com/docs/en/data-usage, anthropic.com/legal/commercial-terms).

Každý NDA klient má v `.md` zvolený jeden ze dvou režimů:

- **anonymizace** — pracuje se kdekoli (i v aplikaci Claude), ale jen s daty
  prohnanými přes `sanitize.py`. Syrové stahování se zablokuje.
- **plna-data** — plná data, ale POUZE v relaci pod obchodními podmínkami:
  `./nda.sh` (API klíč z Klíčenky) nebo přihlášení k Team/Enterprise.
  Soubory klienta leží mimo repo v `$PPC_NDA_DIR` (výchozí ~/ppc-asistent-nda).

Pole v `.md` klienta (sekce Účty a přístupy):
    - **NDA:** true
    - **NDA režim:** anonymizace | plna-data
    - **NDA účty:** google:123-456-7890, sklik:123456, meta:act_123, ga4:123456789
Čísla účtů mohou být místo toho v `clients/.secret/<klient>-account.json`
(klíče `*_id`) — ta čte jen tenhle kód a nikdy je nevypisuje.

Kontrola platí jen uvnitř Claude Code (proměnná CLAUDECODE). Když skript
spustí člověk ve vlastním terminálu, data k modelu nejdou a kontrola mlčí.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENTS_DIR = ROOT / "clients"
SECRET_DIR = CLIENTS_DIR / ".secret"
MODES = ("anonymizace", "plna-data")

# Přesné hodnoty `organizationType` pro Team/Enterprise nejsou ověřené (ověřená je jen
# hodnota jednoho spotřebitelského tarifu). Proto obecná shoda na podřetězec; cokoli jiného = spotřebitel.
_COMMERCIAL_ORG_HINTS = ("team", "enterprise")

_FIELD = re.compile(r"^\s*-\s*\*\*(NDA(?: režim| účty)?):\*\*\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def nda_dir() -> Path:
    return Path(os.environ.get("PPC_NDA_DIR") or Path.home() / "ppc-asistent-nda").expanduser()


def norm_account(value: str) -> str:
    """Sjednotí zápis ID: 123-456-7890 → 1234567890, ACT_1 → act_1, mezery pryč."""
    v = str(value).strip().lower().replace("-", "").replace(" ", "")
    return v.split(":", 1)[1] if ":" in v else v


@dataclass
class Client:
    slug: str
    nda: bool = False
    mode: str | None = None
    accounts: set[str] = field(default_factory=set)
    source: Path | None = None


def _parse_bool(text: str) -> bool:
    t = text.strip().strip("*").strip().lower()
    return t.startswith(("true", "ano", "yes"))


def parse_client_md(text: str, slug: str, source: Path | None = None) -> Client:
    c = Client(slug=slug, source=source)
    for key, val in _FIELD.findall(text):
        key = key.lower()
        if key == "nda":
            c.nda = _parse_bool(val)
        elif key == "nda režim":
            word = val.strip().strip("*`").split()[0].strip("*`,.").lower() if val.strip() else ""
            c.mode = word if word in MODES else None
        elif key == "nda účty":
            for part in re.split(r"[,;]", val):
                part = part.strip().strip("`*")
                if part and part not in ("—", "-"):
                    c.accounts.add(norm_account(part))
    return c


def _secret_accounts(slug: str) -> set[str]:
    p = SECRET_DIR / f"{slug}-account.json"
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {norm_account(v) for k, v in data.items()
            if k.endswith("_id") and isinstance(v, (str, int)) and str(v).strip()}


def load_clients() -> list[Client]:
    """Všichni klienti z repa i z NDA složky mimo repo."""
    files = [p for p in CLIENTS_DIR.glob("*.md") if not p.name.startswith("_")]
    nd = nda_dir()
    if nd.is_dir():
        files += list(nd.glob("*/*.md"))
    out = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        slug = p.parent.name if p.parent != CLIENTS_DIR else p.stem
        c = parse_client_md(text, slug, p)
        if c.nda:
            c.accounts |= _secret_accounts(slug)
        out.append(c)
    return out


def find_nda_client(account_id: str | int) -> Client | None:
    if account_id in (None, ""):
        return None
    acc = norm_account(str(account_id))
    for c in load_clients():
        if c.nda and acc in c.accounts:
            return c
    return None


def nda_accounts() -> set[str]:
    return {a for c in load_clients() if c.nda for a in c.accounts}


def in_claude_code() -> bool:
    return os.environ.get("CLAUDECODE") == "1"


def session_kind() -> tuple[str, str]:
    """(druh, vysvětlení). Druh: 'obchodni' | 'spotrebitelska'."""
    if os.environ.get("PPC_NDA_SESSION") == "1":
        return "obchodni", "NDA relace spuštěná přes ./nda.sh (API klíč, obchodní podmínky)"
    for v in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        if os.environ.get(v):
            return "obchodni", f"cloudový poskytovatel ({v})"
    org = ""
    try:
        cfg = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
        org = str((cfg.get("oauthAccount") or {}).get("organizationType") or "")
    except (OSError, ValueError):
        pass
    if org and any(h in org.lower() for h in _COMMERCIAL_ORG_HINTS):
        return "obchodni", f"přihlášení k firemnímu tarifu ({org})"
    where = "aplikace Claude" if os.environ.get("CLAUDE_CODE_DESKTOP_APP_VERSION") else "terminál"
    return "spotrebitelska", f"{where}, tarif {org or 'neznámý'} (spotřebitelské podmínky)"


def session_is_commercial() -> bool:
    return session_kind()[0] == "obchodni"


class NdaBlocked(SystemExit):
    pass


def _deny(msg: str) -> None:
    raise NdaBlocked("🔒 NDA: " + msg)


def guard(account_id: str | int | None, kind: str = "any") -> None:
    """Zastaví skript, pokud by data NDA klienta šla k modelu tam, kam nesmí.

    kind: 'read-raw'  — syrové stahování (fetch.py a spol.)
          'read-anon' — stahování, které výstup anonymizuje
          'write'     — zápis do účtu podle plánu
          'any'       — neznámý účel (pojistka v normalize_cid)
    """
    if not in_claude_code():
        return
    c = find_nda_client(account_id)
    if c is None:
        return
    commercial, why = session_is_commercial(), session_kind()[1]
    if c.mode == "plna-data":
        if commercial:
            return
        _deny(f"klient „{c.slug}“ je v režimu PLNÁ DATA — pracuje se s ním jen v NDA relaci. "
              f"Teď běží: {why}. Spusť v Terminálu `./nda.sh` a pokračuj tam.")
    if c.mode == "anonymizace":
        if kind == "read-raw":
            _deny(f"klient „{c.slug}“ je v režimu ANONYMIZACE — syrová data se nestahují. "
                  "Použij `scripts/google_ads/fetch_safe.py` (Google Ads) nebo "
                  "`scripts/sklik/fetch.py … --anon <klient>` (Sklik).")
        return
    # NDA bez zvoleného režimu: nic nestahovat, dokud se uživatel nerozhodne.
    if kind != "write" or not commercial:
        _deny(f"klient „{c.slug}“ je pod NDA, ale nemá zvolený režim. Doplň do jeho .md "
              "řádek `- **NDA režim:** anonymizace` nebo `plna-data` (viz docs/nda-rezim.md).")


def filter_listing(rows: list[dict], id_key: str = "id") -> list[dict]:
    """Z výpisu účtů (např. MCC) vyřadí NDA účty, pokud relace není obchodní."""
    if not in_claude_code() or session_is_commercial():
        return rows
    hidden = nda_accounts()
    return [r for r in rows if norm_account(r.get(id_key, "")) not in hidden]


if __name__ == "__main__":
    kind, why = session_kind()
    print(f"Relace: {kind} — {why}")
    print(f"NDA složka mimo repo: {nda_dir()} ({'existuje' if nda_dir().is_dir() else 'zatím neexistuje'})")
    for c in load_clients():
        if c.nda:
            stav = c.mode or "⚠️ režim nezvolen"
            ok = "✅ lze pracovat" if (c.mode == "anonymizace" or (c.mode == "plna-data" and kind == "obchodni")) \
                else "⛔ v této relaci ne"
            print(f"  NDA klient {c.slug}: {stav}, účtů {len(c.accounts)} — {ok}")

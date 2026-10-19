#!/usr/bin/env python3
"""Schválená dávková změna Meta Ads objektů (kampaně / ad sety / reklamy).

Výchozí režim je DRY-RUN: vypíše, co by se poslalo, a NIC neodešle.
Reálný zápis jen s --apply a pouze u plánu s approval.status=approved.

Plán (JSON):
{
  "change_id": "klient-meta-YYYY-MM-DD",
  "client": "...",
  "token_env": "META_API_TOKEN",        # volitelné; např. META_API_TOKEN_CATALOG pro katalogové zápisy
  "approval": {"status": "approved", "approved_by": "user", "approved_at": "YYYY-MM-DD"},
  "changes": [
    {"object_id": "1234567890", "note": "co a proč", "params": {"name": "...", "status": "PAUSED", ...}}
  ]
}

Řetězení kroků (zakládání kampaň → ad set → reklama):
  - krok může mít "id_as": "campaign"  → jeho vrácené `id` se uloží pod tímto jménem
  - kdekoli v `object_id` nebo v `params` lze použít placeholder "{{campaign.id}}"
    (v dry-runu se nahradí zástupným "<id kroku 'campaign'>", takže náhled je čitelný)

Použití:
  python scripts/meta/apply.py clients/plan.json           # dry-run
  python scripts/meta/apply.py clients/plan.json --apply   # zápis (po schválení)

Zapisuje sériově s pauzou; na rate-limit (kód 4/17/32/613 / HTTP 429) backoff.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import require  # noqa: E402

API_VERSION = "v21.0"
RATE_CODES = {4, 17, 32, 613, 80004}

# Prahy čerpání limitu (procenta z Metina okna). Nad HARD odmítneme volat.
USAGE_WARN, USAGE_THROTTLE, USAGE_HARD = 75, 90, 95
_usage_state = {"pct": 0, "throttled": False}


def _read_usage(headers) -> int:
    """Nejvyšší čerpání limitu z hlaviček odpovědi, v procentech.

    Meta posílá po KAŽDÉM volání, kolik má účet vyčerpáno. Reagovat až na
    chybu 80004 je pozdě — v tu chvíli už je okno zavřené a rozestavěná
    kampaň zůstane bez sad reklam. Tohle to přečte dřív, než se to stane.
    """
    peak = 0
    for h in ("x-business-use-case-usage", "x-ad-account-usage", "x-app-usage"):
        raw = headers.get(h)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        buckets = []
        if isinstance(data, dict):
            for v in data.values():
                buckets.extend(v if isinstance(v, list) else [v])
        for b in buckets:
            if not isinstance(b, dict):
                continue
            for k in ("call_count", "total_cputime", "total_time",
                      "acc_id_util_pct", "estimated_time_to_regain_access"):
                val = b.get(k)
                if isinstance(val, (int, float)) and k != "estimated_time_to_regain_access":
                    peak = max(peak, int(val))
    return peak


def _guard_usage() -> None:
    """Brzda před voláním. Nad tvrdým prahem raději skončíme, než abychom
    dostali účet do rate-limitu uprostřed rozestavěné kampaně."""
    pct = _usage_state["pct"]
    if pct >= USAGE_HARD:
        raise SystemExit(
            f"Čerpání limitu Meta API je {pct} % (práh {USAGE_HARD} %). Zastavuji, "
            f"ať nezůstane rozestavěná kampaň. Počkej na reset okna a pusť plán znovu — "
            f"apply.py pokračuje od prvního nevytvořeného objektu."
        )
    if pct >= USAGE_THROTTLE and not _usage_state["throttled"]:
        print(f"[limit] čerpáno {pct} % — zpomaluji na 5 s mezi zápisy", file=sys.stderr)
        _usage_state["throttled"] = True


def post(object_id: str, params: dict, token: str, validate_only: bool = False) -> dict:
    """Zápis do Meta API.

    `validate_only=True` pošle požadavek s Metiným příznakem `validate_only`:
    Meta plán zkontroluje a vrátí chybu, ale **nic nevytvoří**. To je skutečný
    náhled — na rozdíl od pouhého výpisu, co bychom poslali. Odhalí chybné
    nabídky, zakázaná pole i nesmyslné cílení dřív, než se něco založí.
    """
    _guard_usage()
    body = {**{k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()},
            "access_token": token}
    if validate_only:
        body["validate_only"] = "true"
    data = urllib.parse.urlencode(body).encode()
    for attempt in range(5):
        req = urllib.request.Request(
            f"https://graph.facebook.com/{API_VERSION}/{object_id}", data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode())
                pct = _read_usage(resp.headers)
                if pct:
                    _usage_state["pct"] = pct
                    if pct >= USAGE_WARN:
                        print(f"[limit] čerpáno {pct} % okna Meta API", file=sys.stderr)
                if _usage_state["throttled"]:
                    time.sleep(5)
                return payload
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode(errors="replace")
            try:
                code = json.loads(payload).get("error", {}).get("code")
            except Exception:
                code = None
            if (exc.code == 429 or code in RATE_CODES) and attempt < 4:
                wait = 15 * 2 ** attempt
                print(f"[rate-limit] čekám {wait}s…", file=sys.stderr)
                time.sleep(wait)
                continue
            raise SystemExit(f"Meta API {exc.code} u {object_id}: {payload[:2000]}")
    raise SystemExit("Vyčerpány pokusy po rate limitu.")


def resolve(obj, ids: dict, applying: bool, declared: set | None = None):
    """Nahradí placeholdery {{jmeno.id}} hodnotami z předchozích kroků (rekurzivně).

    Hlídá jen jména kroků deklarovaná přes `id_as`. Metin vlastní templating
    ({{product.name}}, {{product.price}}) musí projít beze změny.
    """
    declared = declared or set()
    if isinstance(obj, str):
        for name, val in ids.items():
            obj = obj.replace("{{%s.id}}" % name, str(val))
        if applying:
            zbyle = [n for n in declared if "{{%s.id}}" % n in obj]
            if zbyle:
                raise SystemExit(f"Nerozřešený odkaz na krok {zbyle} v: {obj[:200]}")
        return obj
    if isinstance(obj, dict):
        return {k: resolve(v, ids, applying, declared) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve(v, ids, applying, declared) for v in obj]
    return obj


def main() -> None:
    p = argparse.ArgumentParser(description="Meta Ads write (dry-run default)")
    p.add_argument("plan", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--validate", action="store_true",
                   help="V náhledu nechat plán ověřit přímo Metou (validate_only). Nic nevytvoří, ale odhalí chybné nabídky a pole.")
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    changes = plan.get("changes") or []
    if not changes:
        raise SystemExit("Plán neobsahuje žádné změny.")
    if args.apply and (plan.get("approval") or {}).get("status") != "approved":
        raise SystemExit("Odmítám zápis: plán nemá approval.status=approved.")

    # NDA: zápis do účtu NDA klienta jen v povolené relaci.
    import re as _re
    from lib.nda import guard
    for _acc in set(_re.findall(r"act_\d+", json.dumps(plan))):
        guard(_acc, "write")

    token_env = plan.get("token_env") or "META_API_TOKEN"
    token = require(token_env)[token_env]
    ids: dict[str, str] = {}
    declared = {ch["id_as"] for ch in changes if ch.get("id_as")}
    results = []
    validation_errors = 0
    for ch in changes:
        oid = resolve(str(ch["object_id"]), ids, args.apply, declared)
        params = resolve(ch["params"], ids, args.apply, declared)
        if args.apply:
            try:
                out = post(oid, params, token)
            except SystemExit as exc:
                # Zápis padl uprostřed — NESMÍME ztratit ID už vytvořených objektů,
                # jinak je nelze dohledat a hrozí duplicitní vytvoření při opakování.
                print(json.dumps({
                    "mode": "apply-FAILED",
                    "change_id": plan.get("change_id"),
                    "chyba_u": {"object_id": oid, "note": ch.get("note")},
                    "chyba": str(exc),
                    "JIZ_VYTVORENO": results,
                    "ids": ids,
                }, ensure_ascii=False, indent=2))
                raise SystemExit(1)
            if ch.get("id_as"):
                if not out.get("id"):
                    raise SystemExit(
                        f"Krok '{ch['id_as']}' nevrátil id — přerušuji, ať nevzniknou osiřelé objekty. "
                        f"Odpověď: {json.dumps(out, ensure_ascii=False)[:300]}")
                ids[ch["id_as"]] = out["id"]
            results.append({"object_id": oid, "note": ch.get("note"), "result": out})
            time.sleep(1.5)  # šetrné tempo, sériově
        else:
            if ch.get("id_as"):
                ids[ch["id_as"]] = f"<id kroku '{ch['id_as']}'>"
            row = {"object_id": oid, "note": ch.get("note"), "would_send": params}

            # Necháme plán zkontrolovat přímo Metou. Krok, který odkazuje na
            # předchozí krok, ověřit nejde — jeho rodič ještě neexistuje. V náhledu
            # už je odkaz nahrazený zástupným textem `<id kroku '…'>`, takže se
            # hledá ten, ne původní `{{…}}`. (Jinak Meta vrací chybu typu
            # „creative_id must be a number".)
            unresolved = "<id kroku" in json.dumps(params, ensure_ascii=False)
            if args.validate and not unresolved:
                try:
                    post(oid, params, token, validate_only=True)
                    row["overeno_metou"] = "OK"
                except SystemExit as exc:
                    row["overeno_metou"] = "CHYBA"
                    row["chyba"] = str(exc)[:600]
                    validation_errors += 1
            elif args.validate:
                row["overeno_metou"] = "přeskočeno — odkazuje na krok, který ještě nevznikl"
            results.append(row)

    print(json.dumps({
        "mode": "apply" if args.apply else ("dry-run + validate" if args.validate else "dry-run"),
        "change_id": plan.get("change_id"),
        "count": len(results),
        "chyb_pri_overeni": validation_errors if args.validate else None,
        "changes": results,
    }, ensure_ascii=False, indent=2))

    if args.validate and validation_errors:
        print(f"\n❌ Meta odmítla {validation_errors} z {len(results)} kroků. "
              f"Oprav plán DŘÍV, než pustíš --apply — jinak zůstane rozestavěná kampaň.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

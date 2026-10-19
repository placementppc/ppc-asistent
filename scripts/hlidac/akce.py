#!/usr/bin/env python3
"""Hlídač akcí — kde je prostor pro škálování. Jen navrhuje a posílá, NIC NEMĚNÍ.

Hledá kampaně (Google, Sklik) a sady reklam (Meta), které za posledních 14 dní plní cíl
s rezervou a brzdí je rozpočet. Ke každé navrhne nový denní rozpočet v limitech
z konfigurace, napíše proč (čísla), riziko a hotový DRY-RUN příkaz existujícího apply
skriptu. Plány pro apply skripty uloží do reports/hlidac-akci/plany/ jako NESCHVÁLENÉ.

Použití:
    python3 scripts/hlidac/akce.py              # ráno: posledních 14 dní do včerejška
    python3 scripts/hlidac/akce.py --dnes       # večer (~18:00): kdo už vyčerpal dnešní rozpočet
    python3 scripts/hlidac/akce.py --vikend     # pátek večer: menší kroky + rizika přečerpání do pondělí
    python3 scripts/hlidac/akce.py --klient muj-eshop --json

Report: reports/hlidac-akci/<datum>.md (večer -vecer, víkend -vikend).
Návratový kód: 0 nic k řešení · 1 jsou návrhy nebo víkendová rizika · 2 účet nešel načíst.
Metodika a co s návrhy dělat: .claude/skills/hlidac-akci/SKILL.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import warnings

warnings.simplefilter("ignore")
from datetime import date, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import pravidla_akce as pa  # noqa: E402
from kontroly import _fmt  # noqa: E402
# sdílené pomocné moduly ze scripts/lib (append → nepřebijí moduly hlídače)
sys.path.append(str(Path(__file__).resolve().parents[1]))
from lib.redact import redact, redact_exc  # noqa: E402

ROOT = config.ROOT
VYSTUP = ROOT / "reports" / "hlidac-akci"
HISTORIE = VYSTUP / "rozpocty.json"


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "ucet"


def klic_uctu(u: dict) -> str:
    return f"{u['system']}:{u['id']}"


def nacti_historii(cesta: Path) -> dict:
    try:
        return json.loads(cesta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def zapis_snimek(historie: dict, u: dict, kampane: list[pa.Kampan], dnes: date) -> dict:
    """Uloží dnešní rozpočty (pro týdenní strop navýšení). Starší než 30 dní zahodí."""
    hranice = (dnes - timedelta(days=30)).isoformat()
    ucet = historie.setdefault(klic_uctu(u), {})
    for k in kampane:
        if k.rozpocet:
            ucet.setdefault(k.id, {})[dnes.isoformat()] = k.rozpocet
    for oid in list(ucet):
        ucet[oid] = {d: v for d, v in ucet[oid].items() if d >= hranice}
        if not ucet[oid]:
            del ucet[oid]
    return historie


def prikazy(u: dict, navrhy: list[pa.Navrh], den: str, plany_dir: Path, zapsat: bool = True) -> dict:
    """Plán pro apply skript + dry-run příkaz. Sklik nemá skript na rozpočty → ruční krok."""
    if not navrhy:
        return {}
    jmeno = f"{den}-{slug(u.get('klient') or u['nazev'])}-{u['system']}.json"
    cesta = plany_dir / jmeno
    try:
        rel = cesta.relative_to(ROOT)
    except ValueError:
        rel = cesta
    if u["system"] == "google":
        plan = pa.plan_google(navrhy, den)
        if zapsat:
            cesta.parent.mkdir(parents=True, exist_ok=True)
            cesta.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"plan": str(rel), "dry_run": f"python3 scripts/google_ads/apply_changes.py {u['id']} {rel}",
                "kontrola": f"python3 scripts/google_ads/apply_changes.py {u['id']} {rel} --validate",
                "provedeni": "po schválení člověkem stejný příkaz s --apply"}
    if u["system"] == "meta":
        plan = pa.plan_meta(navrhy, u.get("klient") or slug(u["nazev"]), den)
        if zapsat:
            cesta.parent.mkdir(parents=True, exist_ok=True)
            cesta.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"plan": str(rel), "dry_run": f"python3 scripts/meta/apply.py {rel}",
                "kontrola": f"python3 scripts/meta/apply.py {rel} --validate",
                "provedeni": "po schválení člověkem nastav v plánu approval.status na approved a spusť s --apply"}
    return {"rucne": "Sklik: v repu není skript, který mění rozpočty (apply skripty je záměrně odmítají). "
                     "Po schválení změň denní rozpočet kampaně ručně v rozhraní Skliku."}


def vyhodnot_ucet(u: dict, vcera: date, *, kampane_fn, dny_fn, historie: dict, vikend: bool = False,
                  dnes_hodina: int | None = None) -> dict:
    """Jeden účet. `kampane_fn(u, od, do, dnes)` a `dny_fn(u, od, do)` jsou v testech mock."""
    dnes = vcera + timedelta(days=1)
    od = (vcera - timedelta(days=pa.PRAHY["okno_dni"] - 1)).isoformat()
    kampane = kampane_fn(u, od, vcera.isoformat(), dnes_hodina is not None)

    zacatek_mesice = dnes.replace(day=1)
    od_uctu = min(zacatek_mesice, vcera - timedelta(days=6))
    dny_uctu, _ = dny_fn(u, od_uctu.isoformat(), vcera.isoformat())
    utraceno_mesic = sum(d.utrata for d in dny_uctu if d.datum >= zacatek_mesice.isoformat())
    posl7 = [d for d in dny_uctu if d.datum >= (vcera - timedelta(days=6)).isoformat()]
    denni_utrata = sum(d.utrata for d in posl7) / 7
    soucet_rozpoctu = sum(k.rozpocet or 0 for k in kampane)

    rezerva, popis = pa.rezerva_uctu(u["limity"], soucet_rozpoctu, u["cile"], utraceno_mesic, denni_utrata, dnes)
    navrhy, poznamky = pa.kandidati(u["nazev"], kampane, u["cile"], u["limity"], vcera=vcera,
                                    rezerva=rezerva, popis_rezervy=popis,
                                    historie=historie.get(klic_uctu(u), {}), vikend=vikend,
                                    dnes_hodina=dnes_hodina)
    rizika = []
    if vikend:
        zbyva = (u["cile"]["mesicni_rozpocet"] - utraceno_mesic) if u["cile"].get("mesicni_rozpocet") else None
        rizika = pa.rizika_vikend(u["nazev"], kampane, u["cile"], vcera=vcera, zbyva_mesic=zbyva)
    return {"ucet": u, "kampane": kampane, "navrhy": navrhy, "poznamky": poznamky, "rizika": rizika,
            "rezerva": rezerva, "popis_rezervy": popis, "utraceno_mesic": utraceno_mesic}


def report_md(vysledky: list[dict], chyby: list[tuple[str, str]], nadpis: str, vikend: bool) -> str:
    navrhu = sum(len(v["navrhy"]) for v in vysledky)
    rizik = sum(len(v["rizika"]) for v in vysledky)
    radky = [f"# {nadpis}", ""]
    if navrhu:
        radky.append(f"💡 {navrhu} {'návrh' if navrhu == 1 else 'návrhy' if navrhu < 5 else 'návrhů'} na navýšení "
                     f"rozpočtu v {sum(1 for v in vysledky if v['navrhy'])} účtech.")
    else:
        radky.append("Žádná kampaň teď nesplňuje podmínky pro navýšení (plní cíl s rezervou a brzdí ji rozpočet).")
    if vikend:
        radky.append(f"⚠️ Rizika přes víkend: {rizik}." if rizik else "✅ Přes víkend nic nehrozí přečerpat.")
    if chyby:
        radky.append(f"🔴 Nenačteno: {len(chyby)} účtů.")
    radky += ["", "_Hlídač nic nezměnil. Plány níž jsou NESCHVÁLENÉ — bez `--apply` nic nezapíšou._", ""]

    if vikend and rizik:
        radky += ["## Rizika do pondělí", ""] + [f"- {r}" for v in vysledky for r in v["rizika"]] + [""]
    for nazev, chyba in chyby:
        radky += [f"## 🔴 {nazev}", f"- Účet nešel načíst: {chyba}", ""]
    for v in vysledky:
        u = v["ucet"]
        if not v["navrhy"] and not v["poznamky"]:
            continue
        radky.append(f"## {u['nazev']} ({config.SYSTEMY[u['system']]})")
        if v["popis_rezervy"]:
            radky.append(f"Rezerva účtu pro navýšení: {_fmt(max(v['rezerva'], 0))} Kč/den — {v['popis_rezervy']}.")
        for n in v["navrhy"]:
            nv = n.navyseni
            radky += ["", f"### {n.kampan.nazev} ({n.kampan.uroven}): {_fmt(nv.soucasny)} → {_fmt(nv.novy)} Kč/den "
                          f"(+{nv.pct:.0f} %)", "**Proč:**"]
            radky += [f"- {t}" for t in n.proc]
            if nv.omezeni:
                radky.append("**Krok omezen:** " + "; ".join(nv.omezeni) + ".")
            radky.append("**Riziko:**")
            radky += [f"- {t}" for t in n.rizika]
        cmd = v.get("prikazy") or {}
        if cmd.get("dry_run"):
            radky += ["", "**Jak to po schválení provést** (plán: `" + cmd["plan"] + "`):", "```",
                      cmd["dry_run"] + "      # náhled, nic nezapíše",
                      cmd["kontrola"] + "      # ověření u platformy, nic nezapíše", "```",
                      f"Zápis: {cmd['provedeni']}."]
        elif cmd.get("rucne"):
            radky += ["", f"**Jak to po schválení provést:** {cmd['rucne']}"]
        if v["poznamky"]:
            radky += ["", "Neprošly těsně:"] + [f"- {t}" for t in v["poznamky"]]
        radky.append("")
    return "\n".join(radky).rstrip() + "\n"


def _navrh_json(n: pa.Navrh) -> dict:
    return {"kampan": n.kampan.nazev, "id": n.kampan.id, "uroven": n.kampan.uroven,
            "soucasny": n.navyseni.soucasny, "novy": n.navyseni.novy, "pct": round(n.navyseni.pct, 1),
            "omezeni": n.navyseni.omezeni, "proc": n.proc, "rizika": n.rizika}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hlídač akcí — prostor pro škálování (jen navrhuje)")
    ap.add_argument("--ucty", type=Path, default=config.VYCHOZI_UCTY)
    ap.add_argument("--datum", help="poslední celý den YYYY-MM-DD (výchozí včera)")
    ap.add_argument("--klient", help="jen účty tohoto klienta")
    ap.add_argument("--dnes", action="store_true", help="večer: kampaně, které už dnes vyčerpaly rozpočet")
    ap.add_argument("--vikend", action="store_true", help="pátek večer → pondělí: opatrnější kroky + rizika")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    cfg = config.nacti(a.ucty)
    vcera = date.fromisoformat(a.datum) if a.datum else date.today() - timedelta(days=1)
    ucty = [u for u in config.ucty_pro(cfg, "akce") if not a.klient or u.get("klient") == a.klient]
    if not ucty:
        # Není to chyba: hlídač prostě nemá co hlídat. Kód 0, ať nasazení nehlásí poplach.
        print("Žádný účet nemá nastavené cíle pro hlídač akcí — nic nekontroluji. "
              "Přidej k účtu blok „cile“ (a „akce“ do pole „hlidat“), vzor scripts/hlidac/ucty.example.json.",
              file=sys.stderr)
        return 0

    import zdroje
    hodina = datetime.now().hour if a.dnes else None
    historie = nacti_historii(HISTORIE)
    vysledky, chyby, preskoceno = [], [], []
    for u in ucty:
        jmeno = f"{u['nazev']} ({config.SYSTEMY[u['system']]})"
        if a.dnes and u["system"] == "sklik":
            preskoceno.append(jmeno)   # neověřené, jak rychle Sklik plní dnešní statistiky
            continue
        try:
            v = vyhodnot_ucet(u, vcera, kampane_fn=zdroje.ucet_kampane, dny_fn=zdroje.ucet_dny,
                              historie=historie, vikend=a.vikend, dnes_hodina=hodina)
            v["prikazy"] = prikazy(u, v["navrhy"], vcera.isoformat(), VYSTUP / "plany")
            zapis_snimek(historie, u, v["kampane"], vcera + timedelta(days=1))
            vysledky.append(v)
            print(f"  {'!' if v['navrhy'] or v['rizika'] else '·'} {jmeno}", file=sys.stderr)
        except SystemExit as e:
            chyby.append((jmeno, redact(e)))
        except Exception as e:
            chyby.append((jmeno, redact_exc(e)))

    VYSTUP.mkdir(parents=True, exist_ok=True)
    HISTORIE.write_text(json.dumps(historie, ensure_ascii=False, indent=1), encoding="utf-8")
    den = vcera.isoformat() if not a.dnes else (vcera + timedelta(days=1)).isoformat()
    rezim = " — víkend" if a.vikend else (" — dnes večer" if a.dnes else "")
    text = report_md(vysledky, chyby, f"Hlídač akcí — {den}{rezim}", a.vikend)
    if preskoceno:
        text += ("\nVečer nekontrolováno (u Skliku není ověřené, jak rychle plní dnešní data): "
                 + ", ".join(preskoceno) + ".\n")
    out = VYSTUP / f"{den}{'-vikend' if a.vikend else '-vecer' if a.dnes else ''}.md"
    out.write_text(text, encoding="utf-8")
    if a.json:
        print(json.dumps({"datum": den, "vikend": a.vikend, "dnes": a.dnes,
                          "ucty": [{"nazev": v["ucet"]["nazev"], "system": v["ucet"]["system"],
                                    "navrhy": [_navrh_json(n) for n in v["navrhy"]],
                                    "poznamky": v["poznamky"], "rizika": v["rizika"],
                                    "prikazy": v.get("prikazy") or {}} for v in vysledky],
                          "chyby": [{"ucet": n, "chyba": c} for n, c in chyby]}, ensure_ascii=False, indent=2))
    else:
        print(text)
    print(f"[uloženo] {out.relative_to(ROOT)}", file=sys.stderr)
    if chyby:
        return 2
    return 1 if any(v["navrhy"] or v["rizika"] for v in vysledky) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):   # srozumitelná chyba (konfigurace, chybějící účty) → kód 2
            print(redact(e.code), file=sys.stderr)
            sys.exit(2)
        raise

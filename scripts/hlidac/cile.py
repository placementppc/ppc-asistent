#!/usr/bin/env python3
"""Hlídač cílů — plní účty od poslední změny cíl klienta? A co s tím udělat.

Jen čte. V účtech nic nemění. Návrhy jsou pravidlové a konzervativní; senior závěr
z nich udělá Claude podle skillu .claude/skills/hlidac-cilu/SKILL.md.

Použití:
    python3 scripts/hlidac/cile.py                    # všechny účty s "cile" v poli hlidat
    python3 scripts/hlidac/cile.py --klient muj-eshop # jen jeden klient
    python3 scripts/hlidac/cile.py --json             # strojový výstup
    python3 scripts/hlidac/cile.py --mesice 13        # navíc měsíční řada (kontext sezóny)
    python3 scripts/hlidac/cile.py --podle-planu      # respektuj planovani.frekvence (pro cron)

Poslední změna: `posledni_zmena` v konfiguraci → jinak nejnovější `### YYYY-MM-DD`
v changelogu clients/<klient>.md → jinak posledních 28 dní.
Report: reports/hlidac-cilu/<datum>.md. Návratový kód: 0 OK · 1 něco žluté · 2 červené nebo chyba.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings

warnings.simplefilter("ignore")  # knihovny Googlu na Pythonu 3.9 sypou varování o verzi
from dataclasses import asdict  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import pravidla_cile as pc  # noqa: E402
# sdílené pomocné moduly ze scripts/lib (append → nepřebijí moduly hlídače)
sys.path.append(str(Path(__file__).resolve().parents[1]))
from lib.redact import redact, redact_exc  # noqa: E402

ROOT = config.ROOT


def posledni_zmena(u: dict, vcera: date, klienti: Path) -> tuple[str | None, str]:
    """(datum, zdroj). Zdroj: config | changelog | výchozí."""
    if u.get("posledni_zmena"):
        return u["posledni_zmena"], "config"
    if u.get("klient"):
        soubor = klienti / f"{u['klient']}.md"
        if soubor.exists():
            d = pc.najdi_posledni_zmenu(soubor.read_text(encoding="utf-8"), vcera)
            if d:
                return d, "changelog"
    return None, "výchozí"


def vyhodnot_ucet(u: dict, vcera: date, dny_fn, klienti: Path, mesicu: int = 0) -> dict:
    """Vyhodnotí jeden účet. `dny_fn(u, od, do)` vrací (seznam Den, nálezy) — v testech mock."""
    cile = u["cile"]
    zmena, zdroj = posledni_zmena(u, vcera, klienti)
    okno = pc.okno_od_zmeny(zmena, zdroj, vcera)
    # Jedno stažení pokryje: okno + období před ním, 8 týdnů kontextu, začátek měsíce, volitelně měsíce.
    zacatky = [date.fromisoformat(okno.pred_od), vcera - timedelta(days=8 * 7 - 1), vcera.replace(day=1)]
    if mesicu:
        zacatky.append((vcera.replace(day=1) - timedelta(days=31 * (mesicu - 1))).replace(day=1))
    od = min(zacatky).isoformat()
    dny, nalezy = dny_fn(u, od, vcera.isoformat())

    po = pc.soucet(dny, okno.od, okno.do)
    pred = pc.soucet(dny, okno.pred_od, okno.pred_do)
    posudek = pc.posud_cil(po, pred, cile, okno)
    tempo = pc.tempo_mesice(dny, cile, vcera)
    pc.navrh_z_tempa(posudek, tempo)
    stav = posudek.stav if tempo is None else pc.horsi(posudek.stav, tempo.stav)
    if posudek.stav == pc.BILA and tempo and tempo.stav == pc.ZELENA:
        stav = pc.BILA
    tydny = pc.tydny(dny, vcera, cile["typ"])
    return {
        "nazev": u["nazev"], "system": u["system"], "klient": u.get("klient"),
        "stav": stav, "cil": cile, "okno": asdict(okno),
        "posudek": asdict(posudek), "tempo": asdict(tempo) if tempo else None,
        "tydny": tydny, "mesice": pc.mesice(dny, cile["typ"]) if mesicu else [],
        "stav_uctu": [n.text for n in nalezy],
    }


def report_md(vysledky: list[dict], chyby: list[tuple[str, str]], den: str) -> str:
    pocty = {s: sum(1 for v in vysledky if v["stav"] == s) for s in pc.IKONY}
    radky = [f"# Hlídač cílů — {den}", ""]
    souhrn = " · ".join(f"{pc.IKONY[s]} {pocty[s]}" for s in (pc.CERVENA, pc.ZLUTA, pc.ZELENA, pc.BILA) if pocty[s])
    if chyby:
        souhrn += f" · 🔴 nenačteno {len(chyby)}"
    radky += [souhrn or "Žádný účet s cílem.", "",
              "_Okno od změny slouží k vyhodnocení té změny. Na závěr o celém účtu (rozpočet, měřítko) "
              "je potřeba 8 týdnů po týdnech níž a měsíční řada za celou historii (skill `perf`)._", ""]
    for nazev, chyba in chyby:
        radky += [f"## 🔴 {nazev}", f"- Účet nešel načíst: {chyba}", ""]
    for v in sorted(vysledky, key=lambda v: -pc._PORADI[v["stav"]]):
        p = v["posudek"]
        radky.append(f"## {pc.IKONY[v['stav']]} {v['nazev']} ({config.SYSTEMY[v['system']]})")
        radky.append(f"**{p['shrnuti']}**")
        radky += [f"- {d}" for d in p["detaily"]]
        if v["tempo"]:
            radky += [f"- {pc.IKONY[v['tempo']['stav']]} {t}" for t in v["tempo"]["texty"]]
        radky += [f"- ⚠️ {t}" for t in v["stav_uctu"]]
        if p["navrhy"]:
            radky.append("")
            radky.append("**Návrh** (nic se nemění bez schválení):")
            radky += [f"{i}. {n}" for i, n in enumerate(p["navrhy"], 1)]
        radky += ["", "<details><summary>8 týdnů po týdnech</summary>", ""]
        radky += pc.tabulka_tydnu(v["tydny"], v["cil"]["typ"])
        if v["mesice"]:
            radky += ["", "| Měsíc | Útrata | Konverze | Hodnota | KPI |", "|---|---:|---:|---:|---:|"]
            radky += [f"| {m['mesic']} | {pc._fmt(m['utrata'])} | {m['konverze']:.0f} | {pc._fmt(m['hodnota'])} | "
                      f"{pc.fmt_kpi(m['kpi'], v['cil']['typ'])} |" for m in v["mesice"]]
        radky += ["", "</details>", ""]
    return "\n".join(radky).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hlídač cílů (jen čte)")
    ap.add_argument("--ucty", type=Path, default=config.VYCHOZI_UCTY)
    ap.add_argument("--datum", help="poslední hodnocený den YYYY-MM-DD (výchozí včera)")
    ap.add_argument("--klient", help="jen účty tohoto klienta (pole klient)")
    ap.add_argument("--mesice", type=int, default=0, help="přidat měsíční řadu za N měsíců")
    ap.add_argument("--json", action="store_true", help="strojový výstup na stdout")
    ap.add_argument("--podle-planu", action="store_true",
                    help="když dnes podle planovani.frekvence neběží, skonči s 0 (pro cron)")
    a = ap.parse_args(argv)

    cfg = config.nacti(a.ucty)
    vcera = date.fromisoformat(a.datum) if a.datum else date.today() - timedelta(days=1)
    if a.podle_planu and not config.ma_bezet(cfg["planovani"], vcera + timedelta(days=1)):
        print(f"Podle plánu ({cfg['planovani']['frekvence']}) dnes hlídač cílů neběží.", file=sys.stderr)
        return 0
    ucty = [u for u in config.ucty_pro(cfg, "cile") if not a.klient or u.get("klient") == a.klient]
    if not ucty:
        # Není to chyba: hlídač prostě nemá co hlídat. Kód 0, ať nasazení nehlásí poplach.
        print("Žádný účet nemá nastavené cíle pro hlídač cílů — nic nekontroluji. "
              "Přidej k účtu blok „cile“ (a „cile“ do pole „hlidat“), vzor scripts/hlidac/ucty.example.json.",
              file=sys.stderr)
        return 0

    import zdroje  # API knihovny až tady, ať jde --help a testy bez nich
    vysledky, chyby = [], []
    for u in ucty:
        jmeno = f"{u['nazev']} ({config.SYSTEMY[u['system']]})"
        try:
            vysledky.append(vyhodnot_ucet(u, vcera, zdroje.ucet_dny, ROOT / "clients", a.mesice))
            print(f"  · {jmeno}", file=sys.stderr)
        except SystemExit as e:
            chyby.append((jmeno, redact(e)))
        except Exception as e:  # jeden účet nesmí shodit celý běh
            chyby.append((jmeno, redact_exc(e)))

    den = vcera.isoformat()
    text = report_md(vysledky, chyby, den)
    out = ROOT / "reports" / "hlidac-cilu" / f"{den}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    if a.json:
        print(json.dumps({"datum": den, "ucty": vysledky,
                          "chyby": [{"ucet": n, "chyba": c} for n, c in chyby]}, ensure_ascii=False, indent=2))
    else:
        print(text)
    print(f"[uloženo] {out.relative_to(ROOT)}", file=sys.stderr)
    stavy = {v["stav"] for v in vysledky}
    if chyby or pc.CERVENA in stavy:
        return 2
    return 1 if pc.ZLUTA in stavy else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):   # srozumitelná chyba (konfigurace, chybějící účty) → kód 2
            print(redact(e.code), file=sys.stderr)
            sys.exit(2)
        raise

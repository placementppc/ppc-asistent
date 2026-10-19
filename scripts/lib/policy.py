"""Policy kontroly reklamních textů před zápisem do účtu.

Vzniklo z reálné chyby: sitelink s telefonním číslem v popisu → Google zamítl (policy „Telefonní číslo v textu reklamy").
Telefon patří VÝHRADNĚ do call assetu, nikdy do textů reklam/podkladů.

Použití (ve write skriptech PŘED mutací):
    from lib.policy import check_ad_texts
    check_ad_texts(["Zavolejte nám", ...], context="sitelinky")
    # → SystemExit s vysvětlením, když text porušuje pravidla
"""
from __future__ import annotations

import re

# telefonní čísla: 777 123 456 / 777123456 / 777 123 456 / 777-123-456
_PHONE = re.compile(r"(\+?\d{1,3}[ \-]?)?\d{3}[ \-]?\d{3}[ \-]?\d{3}(?!\d)")
# výjimka: čísla, která nejsou telefon (ceny, míry) — telefon má 9+ číslic v řadě
_DIGITS = re.compile(r"\d")


def _looks_like_phone(text: str) -> bool:
    m = _PHONE.search(text)
    if not m:
        return False
    digits = len(_DIGITS.findall(m.group(0)))
    return digits >= 9


def check_ad_texts(texts: list[str], context: str = "reklamní texty") -> None:
    """Zkontroluje texty proti známým policy pravidlům Google Ads / Sklik.

    Vyhodí SystemExit při nálezu — write skript se zastaví PŘED zápisem.
    """
    problems = []
    for t in texts:
        if not t:
            continue
        if _looks_like_phone(t):
            problems.append(f"telefonní číslo v textu: „{t}“ (patří do call assetu, ne do textu)")
        if "!" in t and context.lower().startswith("nadpis"):
            problems.append(f"vykřičník v nadpisu: „{t}“ (Google v headlines nepovoluje)")
    if problems:
        raise SystemExit(
            f"❌ POLICY kontrola ({context}) — zápis zastaven:\n  - " + "\n  - ".join(problems)
            + "\nOprav texty v plánu a spusť znovu. Viz knowledge/reklamy-ab-testy.md (policy checklist)."
        )

#!/usr/bin/env python3
"""Anonymizace stažených PPC dat pro klienty pod NDA.

Vsadí se MEZI stažení (`fetch.py`) a analýzu. `fetch.py` zůstává čistý a read-only;
tady se ze syrových dat odstraní vše, co podle NDA nesmí ven, a Claude pak čte
jen anonymizovaný výstup.

Co se SMAŽE natvrdo (identifikace účtu / URL / PII — k analýze netřeba):
  - název účtu (descriptiveName), customer ID, resourceName (obsahuje customer ID)
  - všechny URL (finalUrls, displayUrl, trackingUrlTemplate, Sklik url, …)
  - search terms (mohou obsahovat jména/telefony → PII) a product titles (brand)
  - texty reklam (headlines/descriptions — safety net pro vlastní GAQL)
  - CELÉ brandové kampaně (název obsahuje "brand") — branded vyhledávačka prozradí
    značku; vynechá se ještě před pseudonymizací (--keep-all-campaigns vypne)

Co se PSEUDONYMIZUJE (stabilní token přes salted hash, drží napříč běhy):
  - názvy kampaní → CMP_xxxxxx, sestav → AG_xxxxxx, rozpočtů → BUD_xxxxxx
  - product item id → PRD_xxxxxx

Co ZŮSTÁVÁ celé:
  - všechny metriky (náklady, konverze, CTR, imprese, podíly zobrazení)
  - číselná ID (campaign.id, adGroup.id, ad.id) — `apply_changes.py` přes ně adresuje
  - match types, statusy, typy kampaní/biddingu, klíčová slova (jsou generická)

Překladová mapa token→realita se ukládá do `clients/.secret/<klient>-map.json`
(gitignored, Claude ji NIKDY nečte). Díky ní drží pseudonymy napříč běhy
(návaznost learning-loopu) a jde z ní v případě potřeby přeložit token zpět.

Použití:
  # filtr (stdin → stdout), aktualizuje mapu klienta:
  python scripts/google_ads/fetch.py <cid> campaigns | \
      python scripts/sanitize.py --client acme > clients/acme-data.json

  # soubor → soubor:
  python scripts/sanitize.py --client acme --in raw.json --out clients/acme-data.json

  # zpětný překlad tokenů na realitu (např. pro kontrolu, který token je která kampaň):
  python scripts/sanitize.py --client acme --reverse --in plan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_DIR = ROOT / "clients" / ".secret"

# Leaf klíče, které se SMAŽOU úplně (camelCase i snake_case kvůli oběma API).
DROP_KEYS = {
    "session",                            # Sklik přihlašovací token — nikdy ven
    "resourceName", "resource_name",
    "descriptiveName", "descriptive_name",
    "finalUrls", "final_urls", "finalUrl", "final_url",
    "finalUrlSuffix", "final_url_suffix",
    "expandedFinalUrls", "expandedFinalUrl",
    "displayUrl", "display_url",
    "trackingUrlTemplate", "tracking_url_template",
    "searchTerm", "search_term",          # search terms → PII/brand, vypouštíme
    "productTitle", "product_title",       # název produktu → brand, vypouštíme
    "url",                                  # Sklik: url kampaně/inzerátu
    # texty reklam (safety net pro vlastní GAQL — předdefinované reporty je netahají)
    "headlines", "descriptions", "headline", "description",
    "responsiveSearchAd", "expandedTextAd", "responsiveDisplayAd",
    "longHeadline", "long_headline", "businessName", "business_name",
    "path1", "path2",
}

# Celé podstromy k zahození (objekt přímo identifikuje účet).
DROP_SUBTREES = {"customer", "customerClient", "customer_client"}

# Prefix pseudonymu podle rodičovského klíče (Google Ads i Sklik).
PARENT_PREFIX = {
    "campaign": "CMP", "campaigns": "CMP",
    "adGroup": "AG", "ad_group": "AG", "groups": "AG",
    "campaignBudget": "BUD", "campaign_budget": "BUD",
}
PSEUDO_KEYS = {"name"}                          # název objektu → pseudonym
ITEMID_KEYS = {"productItemId", "product_item_id"}

# Kampaně, jejichž název obsahuje některý z těchto podřetězců, se u NDA klientů
# NESTAHUJÍ vůbec (branded vyhledávačka prozradí značku). Case-insensitive.
DROP_CAMPAIGN_DEFAULT = ["brand"]


class Pseudonymizer:
    """Deterministická pseudonymizace se stabilní mapou na disku (per klient)."""

    def __init__(self, client: str) -> None:
        self.path = SECRET_DIR / f"{client}-map.json"
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {
                "client": client,
                "salt": secrets.token_hex(16),
                "created": date.today().isoformat(),
                "tokens": {},                   # token -> reálná hodnota
            }
        self.salt: str = self.data["salt"]
        self._rev: dict[str, str] = {v: k for k, v in self.data["tokens"].items()}
        self._new = 0

    def token(self, prefix: str, value) -> str:
        value = str(value)
        existing = self._rev.get(value)
        if existing and existing.startswith(prefix + "_"):
            return existing
        tok = self._hash(prefix, value)
        while tok in self.data["tokens"] and self.data["tokens"][tok] != value:
            tok = self._hash(prefix, tok)       # kolizní pojistka
        self.data["tokens"][tok] = value
        self._rev[value] = tok
        self._new += 1
        return tok

    def _hash(self, prefix: str, value: str) -> str:
        h = hashlib.sha256(f"{self.salt}|{value}".encode("utf-8")).hexdigest()[:6]
        return f"{prefix}_{h}"

    def save(self) -> None:
        SECRET_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def sanitize(obj, pseudo: Pseudonymizer, parent_key: str | None = None):
    """Rekurzivně projde JSON a aplikuje pravidla DROP / PSEUDO / KEEP."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in DROP_SUBTREES or k in DROP_KEYS:
                continue
            if k in PSEUDO_KEYS and not isinstance(v, (dict, list)):
                out[k] = pseudo.token(PARENT_PREFIX.get(parent_key, "OBJ"), v)
            elif k in ITEMID_KEYS and not isinstance(v, (dict, list)):
                out[k] = pseudo.token("PRD", v)
            else:
                out[k] = sanitize(v, pseudo, parent_key=k)
        return out
    if isinstance(obj, list):
        # parent_key necháváme — položky v "campaigns": [...] mají rodiče "campaigns"
        return [sanitize(x, pseudo, parent_key=parent_key) for x in obj]
    return obj


def drop_campaigns(obj, patterns: list[str], parent_key: str | None = None):
    """Vyhodí celé řádky/objekty patřící kampani, jejíž název matchuje některý
    z podřetězců (case-insensitive). Běží PŘED pseudonymizací — vidí reálné názvy.
    Pokrývá Google Ads (`campaign.name`) i Sklik (položka v listu `campaigns`).
    Vrací (očištěná data, počet zahozených řádků)."""
    pats = [p.lower() for p in patterns]
    dropped = 0

    def hit(name) -> bool:
        return isinstance(name, str) and any(p in name.lower() for p in pats)

    def walk(o, pkey):
        nonlocal dropped
        if isinstance(o, list):
            kept = []
            for x in o:
                if isinstance(x, dict):
                    nested = x.get("campaign")
                    cname = nested.get("name") if isinstance(nested, dict) else None
                    own = x.get("name") if pkey in ("campaigns",) else None
                    if hit(cname) or hit(own):
                        dropped += 1
                        continue
                kept.append(walk(x, pkey))
            return kept
        if isinstance(o, dict):
            return {k: walk(v, k) for k, v in o.items()}
        return o

    return walk(obj, parent_key), dropped


def reverse(obj, tokens: dict[str, str]):
    """Přeloží tokeny zpět na realitu (token→hodnota) kdekoli v JSON.
    Nahrazuje i tokeny uvnitř řetězců (jsou dost distinktivní: PREFIX_hex6)."""
    if not tokens:
        return obj
    rx = re.compile("|".join(re.escape(t) for t in
                    sorted(tokens, key=len, reverse=True)))

    def walk(o):
        if isinstance(o, str):
            return rx.sub(lambda m: tokens[m.group(0)], o)
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x) for x in o]
        return o

    return walk(obj)


def main() -> None:
    p = argparse.ArgumentParser(description="Anonymizace PPC dat pro NDA klienty")
    p.add_argument("--client", required=True, help="Slug klienta (pro mapu tokenů)")
    p.add_argument("--in", dest="infile", help="Vstupní JSON (default stdin)")
    p.add_argument("--out", dest="outfile", help="Výstupní JSON (default stdout)")
    p.add_argument("--reverse", action="store_true",
                   help="Zpětný překlad: tokeny → realita (vyžaduje existující mapu)")
    p.add_argument("--drop-campaign", action="append", metavar="SUBSTR",
                   help="Vynech kampaně s tímto podřetězcem v názvu (lze opakovat; "
                        f"default {DROP_CAMPAIGN_DEFAULT}). Branded vyhledávačka prozradí značku.")
    p.add_argument("--keep-all-campaigns", action="store_true",
                   help="Nevyhazuj žádné kampaně podle názvu (vypne i default 'brand').")
    args = p.parse_args()

    raw = (Path(args.infile).read_text(encoding="utf-8") if args.infile
           else sys.stdin.read())
    data = json.loads(raw)

    if args.reverse:
        # Zpětný překlad vrací SKUTEČNÉ názvy. Uvnitř Claude Code ve spotřebitelské
        # relaci je nesmíme vypsat na stdout (ten čte model) ani uložit tam, kam model vidí.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from lib.nda import in_claude_code, session_is_commercial
        if in_claude_code() and not session_is_commercial():
            out_ok = args.outfile and (".secret" in Path(args.outfile).parts
                                       or "ppc-asistent-nda" in str(Path(args.outfile).expanduser()))
            if not out_ok:
                raise SystemExit("🔒 NDA: zpětný překlad v téhle relaci nevypíšu. Ulož ho přes "
                                 f"--out clients/.secret/{args.client}-reverse.json a otevři si ho sám.")
        map_path = SECRET_DIR / f"{args.client}-map.json"
        if not map_path.exists():
            raise SystemExit(f"Mapa neexistuje: {map_path}")
        tokens = json.loads(map_path.read_text(encoding="utf-8"))["tokens"]
        result = reverse(data, tokens)
    else:
        dropped = 0
        if not args.keep_all_campaigns:
            patterns = args.drop_campaign or DROP_CAMPAIGN_DEFAULT
            data, dropped = drop_campaigns(data, patterns)
            if dropped:
                print(f"[sanitize] vynecháno {dropped} řádků brandových kampaní "
                      f"(podle názvu: {patterns})", file=sys.stderr)
        pseudo = Pseudonymizer(args.client)
        result = sanitize(data, pseudo)
        pseudo.save()
        print(f"[sanitize] klient={args.client} • tokenů celkem="
              f"{len(pseudo.data['tokens'])} (nových {pseudo._new}) • mapa={pseudo.path}",
              file=sys.stderr)

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.outfile:
        Path(args.outfile).write_text(out, encoding="utf-8")
    else:
        print(out)


if __name__ == "__main__":
    main()

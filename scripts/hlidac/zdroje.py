"""Stahování denních součtů účtu ze Skliku, Mety a Google Ads. Jen čte.

Každá funkce vrací seznam `Den` (součet celého účtu po dnech) a případně
`Nalez` o stavu účtu (zamítnuté reklamy, zablokovaný účet).

Pro hlídač akcí navíc výkon po kampaních (Google, Sklik) a sadách reklam (Meta) i s denním
rozpočtem — funkce `*_kampane` / `meta_sady` vrací `pravidla_akce.Kampan`.

Ověřeno:
- Google `metrics.search_budget_lost_impression_share` (0–0,9, nad 0,9 vrací 0,9001) a
  `campaign.primary_status_reasons` (Google Ads API v25, metrics.proto / campaign.proto,
  Context7 19. 10. 2026). Hodnota enumu BUDGET_CONSTRAINED v dokumentaci dohledaná nebyla —
  hlídač ji bere jen jako doplňkový signál. `campaign_budget.amount_micros`,
  `campaign_budget.explicitly_shared` — GAQL kuchařka a vzorové skripty Googlu.
- Meta `daily_budget` je v nejmenší jednotce měny (CZK offset 100), insights pole
  `adset_id`, `adset_name`, `campaign_id`, `spend`, `frequency` (Marketing API reference).
- Sklik `campaigns.list` s `displayColumns` `budget.dayBudget` (haléře) — čtou ho apply skripty
  při verifikaci. Pole „ztráta zobrazení kvůli rozpočtu“ ve Skliku NEOVĚŘENO, nepoužívá se.
- Sklik `campaigns.createReport` + `statGranularity: daily` vrací `stats[]` s `date`
  (YYYYMMDD), `clickMoney` v haléřích, `conversionValue` v Kč (živý test 19. 10. 2026,
  viz i knowledge/sklik.md). `readReport` stránkuje po dávkách, deduplikuje se podle id.
- Meta `account_status`: 1 = ACTIVE, 2 = DISABLED (Marketing API, Ad Account reference).
- Google `ad_group_ad.policy_summary.approval_status` = DISAPPROVED (Google Ads API fields v25).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from kontroly import CERVENA, ZLUTA, Den, Nalez
from pravidla_akce import Kampan

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def _modul(nazev: str, cesta: Path):
    """Načte modul podle cesty — všechny tři konektory se jmenují `client.py`."""
    sys.path.insert(0, str(cesta.parent))
    spec = importlib.util.spec_from_file_location(nazev, cesta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _iso(yyyymmdd: int | str) -> str:
    s = str(yyyymmdd).replace("-", "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


# --------------------------------------------------------------------- Sklik
_sklik: dict[str, object] = {}


class _SklikSBackoffem:
    """Obal klienta: na HTTP 429 počká a zkusí znovu (pravidlo API limitů, CLAUDE.md #5)."""

    def __init__(self, klient) -> None:
        self.k = klient

    def call(self, *args, **kw):
        import time
        import urllib.error
        pauza = 5
        while True:
            try:
                return self.k.call(*args, **kw)
            except urllib.error.HTTPError as e:
                if e.code != 429 or pauza > 80:
                    raise
                time.sleep(pauza)
                pauza *= 2


def _sklik_klient(token_var: str | None):
    """Klient pro daný token. `token_var` = NÁZEV proměnné (např. SKLIK_DRUHY_TOKEN)."""
    klic = token_var or ""
    if klic not in _sklik:
        mod = _modul("sklik_client", SCRIPTS / "sklik" / "client.py")
        puvodni = os.environ.get("SKLIK_TOKEN_VAR")
        if token_var:
            os.environ["SKLIK_TOKEN_VAR"] = token_var
        try:
            k = mod.SklikClient().login()
        finally:
            if puvodni is None:
                os.environ.pop("SKLIK_TOKEN_VAR", None)
            else:
                os.environ["SKLIK_TOKEN_VAR"] = puvodni
        k.nda_kind = "read-anon"  # ven jdou jen součty účtu
        _sklik[klic] = _SklikSBackoffem(k)
    return _sklik[klic]


def sklik_dny(user_id: int, od: str, do: str, token_var: str | None = None) -> tuple[list[Den], list[Nalez]]:
    sk = _sklik_klient(token_var)
    cr = sk.call("campaigns.createReport", {"dateFrom": od, "dateTo": do},
                 {"statGranularity": "daily"}, user_id=user_id)
    rid, celkem = str(cr["reportId"]), int(cr.get("totalCount") or 0)
    videno: dict[int, list] = {}
    offset = 0
    while offset < celkem:
        rr = sk.call("campaigns.readReport", rid,
                     {"offset": offset, "limit": 100,
                      "displayColumns": ["id", "impressions", "clicks", "clickMoney",
                                         "conversions", "conversionValue"]},
                     user_id=user_id)
        radky = rr.get("report") or []
        if not radky:
            break
        for r in radky:
            videno[r["id"]] = r.get("stats") or []
        offset += len(radky)

    soucty: dict[str, list[float]] = defaultdict(lambda: [0.0, 0, 0, 0.0, 0.0])
    for stats in videno.values():
        for s in stats:
            a = soucty[_iso(s["date"])]
            a[0] += (s.get("clickMoney") or 0) / 100      # haléře -> Kč
            a[1] += s.get("impressions") or 0
            a[2] += s.get("clicks") or 0
            a[3] += s.get("conversions") or 0
            a[4] += s.get("conversionValue") or 0         # už v Kč
    return [Den(d, *v) for d, v in sorted(soucty.items())], []


# ---------------------------------------------------------------------- Meta
_meta = None
# Stejné typy jako scripts/meta/product_report.py. Překrývají se (omni = souhrn),
# proto se bere maximum, ne součet.
NAKUP = ("onsite_web_purchase", "omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")


def _meta_klient():
    global _meta
    if _meta is None:
        _meta = _modul("meta_client", SCRIPTS / "meta" / "client.py").MetaClient()
    return _meta


def _nakupy(akce: list | None) -> float:
    hodnoty = [float(a.get("value", 0)) for a in (akce or []) if a.get("action_type") in NAKUP]
    return max(hodnoty) if hodnoty else 0.0


def meta_dny(act: str, od: str, do: str) -> tuple[list[Den], list[Nalez]]:
    m = _meta_klient()
    act = act if str(act).startswith("act_") else f"act_{act}"
    radky = m.get_all(f"{act}/insights", level="account", time_increment=1,
                      time_range=json.dumps({"since": od, "until": do}),
                      fields="spend,impressions,inline_link_clicks,actions,action_values")
    dny = [Den(r["date_start"], float(r.get("spend") or 0), int(r.get("impressions") or 0),
               int(r.get("inline_link_clicks") or 0), _nakupy(r.get("actions")),
               _nakupy(r.get("action_values"))) for r in radky]

    nalezy: list[Nalez] = []
    ucet = m.get(act, fields="account_status,disable_reason")
    st = ucet.get("account_status")
    if st == 2:
        nalezy.append(Nalez(CERVENA, f"Účet je ZABLOKOVANÝ (account_status 2, důvod {ucet.get('disable_reason')})."))
    elif st not in (1, None):
        nalezy.append(Nalez(CERVENA, f"Účet není aktivní (account_status {st}) — zkontroluj platbu a stav v Business Manageru."))
    zamitnute = m.get_all(f"{act}/ads", effective_status=json.dumps(["DISAPPROVED"]), fields="id", limit=200)
    if zamitnute:
        nalezy.append(Nalez(ZLUTA, f"Zamítnuté reklamy: {len(zamitnute)}."))
    return dny, nalezy


def meta_dnes(act: str) -> float:
    act = act if str(act).startswith("act_") else f"act_{act}"
    r = _meta_klient().get_all(f"{act}/insights", level="account", date_preset="today", fields="spend")
    return float(r[0].get("spend") or 0) if r else 0.0


# -------------------------------------------------------------------- Google
_google: dict[str, object] = {}


def _google_klient(profil: str | None):
    klic = profil or ""
    if klic not in _google:
        gmod = _modul("google_client", SCRIPTS / "google_ads" / "client.py")
        if profil:
            os.environ["GOOGLE_ADS_PROFILE"] = profil
        else:
            os.environ.pop("GOOGLE_ADS_PROFILE", None)
        _google[klic] = (gmod.build_client(), gmod)
    return _google[klic]


def _gaql(profil: str | None, cid: str, dotaz: str):
    klient, gmod = _google_klient(profil)
    cid = gmod.normalize_cid(cid, nda_kind="read-anon")
    svc = klient.get_service("GoogleAdsService")
    for davka in svc.search_stream(customer_id=cid, query=dotaz):
        yield from davka.results


def google_dny(cid: str, od: str, do: str, profil: str | None = None) -> tuple[list[Den], list[Nalez]]:
    dotaz = f"""
        SELECT segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.conversions_value
        FROM customer
        WHERE segments.date BETWEEN '{od}' AND '{do}'"""
    dny = [Den(r.segments.date, r.metrics.cost_micros / 1e6, r.metrics.impressions,
               r.metrics.clicks, r.metrics.conversions, r.metrics.conversions_value)
           for r in _gaql(profil, cid, dotaz)]
    zamitnute = sum(1 for _ in _gaql(profil, cid, """
        SELECT ad_group_ad.ad.id FROM ad_group_ad
        WHERE ad_group_ad.status = ENABLED AND ad_group.status = ENABLED
          AND campaign.status = ENABLED
          AND ad_group_ad.policy_summary.approval_status = DISAPPROVED"""))
    nalezy = [Nalez(ZLUTA, f"Zamítnuté aktivní reklamy: {zamitnute}.")] if zamitnute else []
    return sorted(dny, key=lambda d: d.datum), nalezy


def google_dnes(cid: str, profil: str | None = None) -> float:
    rows = _gaql(profil, cid, "SELECT metrics.cost_micros FROM customer WHERE segments.date DURING TODAY")
    return sum(r.metrics.cost_micros for r in rows) / 1e6


# ------------------------------------------------------------- účet (společné)
def ucet_dny(u: dict, od: str, do: str) -> tuple[list[Den], list[Nalez]]:
    """Denní součty účtu podle `system` z konfigurace hlídačů."""
    if u["system"] == "sklik":
        return sklik_dny(int(u["id"]), od, do, u.get("token_var"))
    if u["system"] == "meta":
        return meta_dny(str(u["id"]), od, do)
    return google_dny(str(u["id"]), od, do, u.get("profil"))


def ucet_kampane(u: dict, od: str, do: str, dnes: bool = False) -> list[Kampan]:
    """Kampaně / sady s denním rozpočtem a výkonem po dnech (pro hlídač akcí)."""
    if u["system"] == "sklik":
        return sklik_kampane(int(u["id"]), od, do, u.get("token_var"))
    if u["system"] == "meta":
        return meta_sady(str(u["id"]), od, do, dnes)
    return google_kampane(str(u["id"]), od, do, u.get("profil"), dnes)


# -------------------------------------------------------- Google po kampaních
def _enum_nazev(x) -> str:
    return getattr(x, "name", None) or str(x)


def google_kampane(cid: str, od: str, do: str, profil: str | None = None, dnes: bool = False) -> list[Kampan]:
    kampane: dict[str, Kampan] = {}
    for r in _gaql(profil, cid, f"""
        SELECT campaign.id, campaign.name, campaign.primary_status_reasons,
               campaign_budget.id, campaign_budget.amount_micros, campaign_budget.explicitly_shared,
               metrics.search_budget_lost_impression_share
        FROM campaign
        WHERE campaign.status = 'ENABLED' AND segments.date BETWEEN '{od}' AND '{do}'"""):
        kid = str(r.campaign.id)
        ztrata = r.metrics.search_budget_lost_impression_share
        kampane[kid] = Kampan(
            system="google", id=kid, nazev=r.campaign.name,
            rozpocet=r.campaign_budget.amount_micros / 1e6 or None,
            rozpocet_id=str(r.campaign_budget.id), sdileny_rozpocet=bool(r.campaign_budget.explicitly_shared),
            ztrata_is_rozpocet=float(ztrata) if ztrata else None,
            duvody_stavu=[_enum_nazev(x) for x in r.campaign.primary_status_reasons])
    for r in _gaql(profil, cid, f"""
        SELECT campaign.id, segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE campaign.status = 'ENABLED' AND segments.date BETWEEN '{od}' AND '{do}'"""):
        k = kampane.get(str(r.campaign.id))
        if k:
            k.dny.append(Den(r.segments.date, r.metrics.cost_micros / 1e6, r.metrics.impressions,
                             r.metrics.clicks, r.metrics.conversions, r.metrics.conversions_value))
    if dnes:
        for r in _gaql(profil, cid, """
            SELECT campaign.id, metrics.cost_micros FROM campaign
            WHERE campaign.status = 'ENABLED' AND segments.date DURING TODAY"""):
            k = kampane.get(str(r.campaign.id))
            if k:
                k.utrata_dnes = r.metrics.cost_micros / 1e6
    return list(kampane.values())


# --------------------------------------------------------- Sklik po kampaních
def sklik_kampane(user_id: int, od: str, do: str, token_var: str | None = None) -> list[Kampan]:
    sk = _sklik_klient(token_var)
    seznam = sk.call("campaigns.list", {"isDeleted": False},
                     {"offset": 0, "limit": 1000,
                      "displayColumns": ["id", "name", "status", "budget.dayBudget"]},
                     user_id=user_id)
    kampane: dict[int, Kampan] = {}
    for c in seznam.get("campaigns") or []:
        if c.get("status") != "active":
            continue
        rozpocet = (c.get("budget") or {}).get("dayBudget")
        kampane[c["id"]] = Kampan(system="sklik", id=str(c["id"]), nazev=c.get("name", str(c["id"])),
                                  rozpocet=rozpocet / 100 if rozpocet else None,   # haléře -> Kč
                                  rozpocet_id=str(c["id"]))
    cr = sk.call("campaigns.createReport", {"dateFrom": od, "dateTo": do},
                 {"statGranularity": "daily"}, user_id=user_id)
    rid, celkem = str(cr["reportId"]), int(cr.get("totalCount") or 0)
    offset = 0
    while offset < celkem:
        rr = sk.call("campaigns.readReport", rid,
                     {"offset": offset, "limit": 100,
                      "displayColumns": ["id", "impressions", "clicks", "clickMoney",
                                         "conversions", "conversionValue"]},
                     user_id=user_id)
        radky = rr.get("report") or []
        if not radky:
            break
        for r in radky:
            k = kampane.get(r["id"])
            if k is None or k.dny:
                continue
            k.dny = sorted((Den(_iso(s["date"]), (s.get("clickMoney") or 0) / 100, s.get("impressions") or 0,
                                s.get("clicks") or 0, s.get("conversions") or 0, s.get("conversionValue") or 0)
                            for s in (r.get("stats") or [])), key=lambda d: d.datum)
        offset += len(radky)
    return list(kampane.values())


# ----------------------------------------------------------- Meta po sadách
def meta_sady(act: str, od: str, do: str, dnes: bool = False) -> list[Kampan]:
    """Sady s denním rozpočtem; kampaně s rozpočtem kampaně (CBO) jako jeden celek.

    Doživotní rozpočty (lifetime_budget) hlídač akcí neřeší — vynechá je.
    """
    from datetime import date as _date, timedelta as _td
    m = _meta_klient()
    act = act if str(act).startswith("act_") else f"act_{act}"
    mena = (m.get(act, fields="currency") or {}).get("currency")
    offset = 1 if (mena or "").upper() in ("CLP", "COP", "CRC", "HUF", "ISK", "IDR", "JPY", "KRW", "PYG", "TWD", "VND") else 100
    aktivni = json.dumps(["ACTIVE"])
    kampane_cbo = {c["id"]: c for c in m.get_all(f"{act}/campaigns", effective_status=aktivni,
                                                   fields="id,name,daily_budget", limit=200)
                   if c.get("daily_budget")}
    sady = m.get_all(f"{act}/adsets", effective_status=aktivni,
                     fields="id,name,campaign_id,daily_budget", limit=200)
    objekty: dict[str, Kampan] = {}
    sada_na_objekt: dict[str, str] = {}
    for s in sady:
        if s.get("daily_budget"):
            objekty[s["id"]] = Kampan(system="meta", id=s["id"], nazev=s.get("name", s["id"]), uroven="sada",
                                      rozpocet=int(s["daily_budget"]) / offset, rozpocet_id=s["id"], mena=mena)
            sada_na_objekt[s["id"]] = s["id"]
        elif s.get("campaign_id") in kampane_cbo:
            c = kampane_cbo[s["campaign_id"]]
            if c["id"] not in objekty:
                objekty[c["id"]] = Kampan(system="meta", id=c["id"], nazev=c.get("name", c["id"]),
                                          uroven="kampaň", rozpocet=int(c["daily_budget"]) / offset,
                                          rozpocet_id=c["id"], mena=mena)
            sada_na_objekt[s["id"]] = c["id"]

    denne: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0, 0, 0.0, 0.0]))
    for r in m.get_all(f"{act}/insights", level="adset", time_increment=1,
                       time_range=json.dumps({"since": od, "until": do}),
                       fields="adset_id,spend,impressions,inline_link_clicks,actions,action_values", limit=500):
        oid = sada_na_objekt.get(r.get("adset_id"))
        if not oid:
            continue
        a = denne[oid][r["date_start"]]
        a[0] += float(r.get("spend") or 0)
        a[1] += int(r.get("impressions") or 0)
        a[2] += int(r.get("inline_link_clicks") or 0)
        a[3] += _nakupy(r.get("actions"))
        a[4] += _nakupy(r.get("action_values"))
    for oid, dny in denne.items():
        objekty[oid].dny = [Den(d, *v) for d, v in sorted(dny.items())]

    # Frekvence za posledních 7 dní okna. Frekvence se nesčítá, proto zvlášť dotaz bez time_increment
    # na úrovni objektu, který nese rozpočet.
    od7 = (_date.fromisoformat(do) - _td(days=6)).isoformat()
    for uroven, klic in (("adset", "adset_id"), ("campaign", "campaign_id")):
        for r in m.get_all(f"{act}/insights", level=uroven, time_range=json.dumps({"since": od7, "until": do}),
                           fields=f"{klic},frequency", limit=500):
            k = objekty.get(r.get(klic))
            if k and ((uroven == "adset") == (k.uroven == "sada")) and r.get("frequency"):
                k.frekvence_7d = float(r["frequency"])

    if dnes:
        for uroven, klic in (("adset", "adset_id"), ("campaign", "campaign_id")):
            for r in m.get_all(f"{act}/insights", level=uroven, date_preset="today",
                               fields=f"{klic},spend", limit=500):
                k = objekty.get(r.get(klic))
                if k and ((uroven == "adset") == (k.uroven == "sada")):
                    k.utrata_dnes = float(r.get("spend") or 0)
    return list(objekty.values())

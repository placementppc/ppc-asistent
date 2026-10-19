#!/usr/bin/env python3
"""Vygeneruje HTML report zahraniční návštěvnosti z více GA4 properties.

Report používá poslední dva dokončené kalendářní měsíce pro MoM a zároveň
zobrazuje součet od začátku roku. Domácí země se nastavuje pro každou property
zvlášť a v hlavní tabulce je vynechána.

Použití:
  .venv/bin/python scripts/ga4/country_report.py \
      --config clients/<klient>-ga4-country-report.json \
      --output /tmp/country-report.html
"""
from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from fetch import access_token, run_report


MONTHLY_METRICS = ("sessions", "engagedSessions")
PERIOD_METRICS = ("sessions", "activeUsers", "engagedSessions")


def previous_month(month: str) -> str:
    year, number = int(month[:4]), int(month[4:])
    if number == 1:
        return f"{year - 1}12"
    return f"{year}{number - 1:02d}"


def month_label(month: str) -> str:
    names = ("leden", "únor", "březen", "duben", "květen", "červen",
             "červenec", "srpen", "září", "říjen", "listopad", "prosinec")
    return f"{names[int(month[4:]) - 1]} {month[:4]}"


def complete_months(year: int, as_of: date) -> tuple[list[str], str, str]:
    first_current = as_of.replace(day=1)
    last_complete = first_current - timedelta(days=1)
    latest = f"{last_complete.year}{last_complete.month:02d}"
    previous = previous_month(latest)
    months = [f"{year}{number:02d}" for number in range(1, 13)
              if f"{year}{number:02d}" <= latest]
    return months, latest, previous


def integer(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def percent(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "—"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.1f} %".replace(".", ",")


def load_property(prop: dict, token: str, start: str, end: str) -> dict:
    monthly_rows = run_report(str(prop["property_id"]), token,
                              ["yearMonth", "country"], list(MONTHLY_METRICS),
                              start, end)
    period_rows = run_report(str(prop["property_id"]), token,
                             ["country"], list(PERIOD_METRICS), start, end)
    data: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {metric: 0 for metric in MONTHLY_METRICS}))
    for row in monthly_rows:
        country = row.get("country") or "(not set)"
        month = row.get("yearMonth") or ""
        for metric in MONTHLY_METRICS:
            data[country][month][metric] += integer(row.get(metric))
    period = {
        (row.get("country") or "(not set)"): {
            metric: integer(row.get(metric)) for metric in PERIOD_METRICS
        }
        for row in period_rows
    }
    return {"definition": prop, "data": data, "period": period}


def country_summary(payload: dict, months: list[str], latest: str,
                    previous: str) -> list[dict]:
    domestic = set(payload["definition"].get("domestic_countries", []))
    results = []
    for country, ytd in payload["period"].items():
        if country in domestic:
            continue
        by_month = payload["data"][country]
        current = by_month[latest]
        prior = by_month[previous]
        mom = None if prior["sessions"] == 0 else (
            (current["sessions"] - prior["sessions"]) / prior["sessions"] * 100)
        engagement = (ytd["engagedSessions"] / ytd["sessions"] * 100
                      if ytd["sessions"] else None)
        users = ytd["activeUsers"]
        anomaly = (
            (users <= 5 and ytd["sessions"] >= 100)
            or (users > 0 and ytd["sessions"] / users >= 15)
            or (ytd["sessions"] >= 500 and engagement is not None and engagement < 20)
        )
        results.append({
            "country": country,
            "ytd": ytd,
            "current": current,
            "prior": prior,
            "mom": mom,
            "engagement": engagement,
            "anomaly": anomaly,
            "months": by_month,
        })
    return sorted(results, key=lambda item: item["ytd"]["sessions"], reverse=True)


def render_table(payload: dict, months: list[str], latest: str,
                 previous: str, start: str, end: str, top: int) -> str:
    definition = payload["definition"]
    rows = country_summary(payload, months, latest, previous)[:top]
    headers = "".join(f"<th>{html.escape(month_label(m).split()[0])}</th>" for m in months)
    body = []
    for row in rows:
        cls = " class=\"anomaly\"" if row["anomaly"] else ""
        warning = " ⚠" if row["anomaly"] else ""
        monthly = "".join(f"<td>{fmt(row['months'][m]['sessions'])}</td>" for m in months)
        body.append(
            f"<tr{cls}><td>{html.escape(row['country'])}{warning}</td>"
            f"<td>{fmt(row['ytd']['sessions'])}</td>"
            f"<td>{fmt(row['ytd']['activeUsers'])}</td>"
            f"<td>{percent(row['engagement'])}</td>"
            f"<td>{fmt(row['prior']['sessions'])}</td>"
            f"<td>{fmt(row['current']['sessions'])}</td>"
            f"<td>{percent(row['mom'], signed=True)}</td>{monthly}</tr>"
        )
    return f"""
    <section>
      <h2>{html.escape(definition['name'])}</h2>
      <p class="meta">GA4 property {html.escape(str(definition['property_id']))}; domácí země vynechána:
      {html.escape(', '.join(definition.get('domestic_countries', [])))}</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Země</th><th>Návštěvy<br>{html.escape(start)}–{html.escape(end)}</th>
        <th>Aktivní uživatelé<br>{html.escape(start)}–{html.escape(end)}</th>
        <th>Míra zapojení<br>{html.escape(start)}–{html.escape(end)}</th>
        <th>Návštěvy<br>{html.escape(month_label(previous))}</th>
        <th>Návštěvy<br>{html.escape(month_label(latest))}</th>
        <th>Změna<br>{html.escape(month_label(latest))} vs. {html.escape(month_label(previous))}</th>{headers}</tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table></div>
    </section>"""


def render(config: dict, loaded: list[dict], missing: list[dict], errors: list[str],
           months: list[str], latest: str, previous: str, as_of: date,
           period_start: str, period_end: str, top: int) -> str:
    sections = "".join(
        render_table(item, months, latest, previous, period_start, period_end, top)
        for item in loaded
    )
    notices = []
    for prop in missing:
        notices.append(f"<li><strong>{html.escape(prop['name'])}</strong>: chybí property_id.</li>")
    notices.extend(f"<li>{html.escape(message)}</li>" for message in errors)
    notice_html = f"<div class=\"notice\"><ul>{''.join(notices)}</ul></div>" if notices else ""
    return f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(config.get('title', 'GA4 – zahraniční návštěvnost'))}</title>
<style>
body{{font:14px/1.45 Arial,sans-serif;color:#202124;margin:32px;background:#f7f8fa}}
main{{max-width:1500px;margin:auto}} h1{{margin-bottom:4px}} h2{{margin:0 0 4px}}
section{{background:white;border:1px solid #dadce0;border-radius:12px;padding:20px;margin:20px 0}}
.meta,.subtitle{{color:#5f6368}} .notice{{background:#fff4e5;border-left:4px solid #f9ab00;padding:10px 16px}}
.explain{{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:12px;margin:18px 0}}
.explain div{{background:#fff;border:1px solid #dadce0;border-radius:10px;padding:12px}}
.explain strong{{display:block;margin-bottom:4px}}
.table-wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;white-space:nowrap}}
th,td{{border-bottom:1px solid #e5e7eb;padding:8px 10px;text-align:right}} th:first-child,td:first-child{{text-align:left}}
th{{background:#f1f3f4;position:sticky;top:0}} tr.anomaly{{background:#fff4e5}}
.foot{{color:#5f6368;font-size:12px;margin-top:24px}}
</style></head><body><main>
<h1>{html.escape(config.get('title', 'GA4 – zahraniční návštěvnost'))}</h1>
<p class="subtitle">Vygenerováno {as_of.strftime('%-d. %-m. %Y')} · reportované období: {html.escape(period_start)}–{html.escape(period_end)} · poslední dokončený měsíc: {html.escape(month_label(latest))}</p>
{notice_html}
<div class="explain">
  <div><strong>Návštěvy</strong>Počet relací v GA4. Jeden člověk může web navštívit vícekrát, takže může vytvořit více návštěv.</div>
  <div><strong>Aktivní uživatelé</strong>Počet různých aktivních uživatelů za celé uvedené období. Měsíční uživatelé se nesčítají.</div>
  <div><strong>Míra zapojení</strong>Podíl návštěv, které trvaly déle než 10 sekund, měly konverzi nebo alespoň dvě zobrazení.</div>
  <div><strong>Meziměsíční změna</strong>Porovnání počtu návštěv za {html.escape(month_label(latest))} proti {html.escape(month_label(previous))}. Nejde o meziroční srovnání.</div>
</div>
<p>⚠ označuje pravděpodobně automatizovaný nebo technicky anomální provoz: extrémní poměr návštěv k uživatelům nebo alespoň 500 návštěv s mírou zapojení pod 20 %. Není automaticky odečten, aby report zůstal transparentní.</p>
{sections}
<p class="foot">Zdroj: Google Analytics Data API. Aktuální neuzavřený měsíc není zahrnut do tabulek ani meziměsíčního srovnání.</p>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    months, latest, previous = complete_months(args.year, args.as_of)
    latest_year, latest_number = int(latest[:4]), int(latest[4:])
    if latest_number == 12:
        last_complete_day = date(latest_year, 12, 31)
    else:
        last_complete_day = date(latest_year, latest_number + 1, 1) - timedelta(days=1)
    api_start = f"{args.year}-01-01"
    api_end = last_complete_day.isoformat()
    label_start = f"1. 1. {args.year}"
    label_end = last_complete_day.strftime("%-d. %-m. %Y")
    token = access_token()
    loaded, missing, errors = [], [], []
    for prop in config["properties"]:
        if not prop.get("property_id"):
            missing.append(prop)
            continue
        try:
            loaded.append(load_property(prop, token, api_start, api_end))
        except SystemExit as exc:
            errors.append(f"{prop['name']}: {exc}")
    output = render(config, loaded, missing, errors, months, latest, previous,
                    args.as_of, label_start, label_end, args.top)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

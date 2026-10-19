#!/usr/bin/env python3
"""Markdown → tisknutelné HTML → PDF (headless Chrome). Jen stdlib, žádné závislosti.

Použití:
  python3 scripts/meta/report_pdf.py <report.md> <report.pdf> ["Titulek"]

Pokrývá podmnožinu markdownu, kterou používá produktový report:
nadpisy, tabulky se zarovnáním, **tučné**, `kód`, _kurzíva_, seznamy, citace, ---
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4 landscape; margin: 14mm 12mm 16mm; }
* { box-sizing: border-box; }
body { font: 10.5px/1.5 -apple-system, "Helvetica Neue", Arial, sans-serif;
       color: #1a1a1a; margin: 0; }
h1 { font-size: 21px; margin: 0 0 4px; letter-spacing: -.2px; }
h2 { font-size: 15px; margin: 22px 0 8px; padding-bottom: 5px;
     border-bottom: 2px solid #1a1a1a; page-break-after: avoid; }
h3 { font-size: 12.5px; margin: 16px 0 6px; color: #000; page-break-after: avoid; }
p, li { margin: 5px 0; }
ul { margin: 6px 0; padding-left: 17px; }
strong { font-weight: 650; }
code { font-family: "SF Mono", Menlo, monospace; font-size: .9em;
       background: #f1f1ef; padding: 1px 4px; border-radius: 3px; }
em { color: #666; font-style: normal; font-size: .95em; }
hr { border: 0; border-top: 1px solid #ddd; margin: 18px 0; }
blockquote { margin: 8px 0; padding: 8px 12px; background: #f7f7f5;
             border-left: 3px solid #bbb; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px;
        font-size: 9px; page-break-inside: auto; }
th { background: #1a1a1a; color: #fff; font-weight: 600; text-align: left;
     padding: 5px 7px; white-space: nowrap; }
td { padding: 4px 7px; border-bottom: .5px solid #e3e3e0; }
tr { page-break-inside: avoid; }
tbody tr:nth-child(even) td { background: #fafaf8; }
.num { text-align: right; white-space: nowrap; }
.ctr { text-align: center; }
.meta { color: #666; font-size: 10px; margin-bottom: 14px; }
"""


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w_])_([^_]+)_(?![\w_])", r"<em>\1</em>", t)
    return t


def convert(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        # tabulka: hlavička + oddělovač se zarovnáním
        if (ln.startswith("|") and i + 1 < len(lines)
                and re.fullmatch(r"\|[-: |]+\|", lines[i + 1].strip())):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            aligns = []
            for spec in lines[i + 1].strip().strip("|").split("|"):
                spec = spec.strip()
                aligns.append("ctr" if spec.startswith(":") and spec.endswith(":")
                              else "num" if spec.endswith(":") else "")
            out.append("<table><thead><tr>" + "".join(
                f'<th class="{a}">{inline(c)}</th>' for c, a in zip(cells, aligns))
                + "</tr></thead><tbody>")
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(
                    f'<td class="{a}">{inline(c)}</td>'
                    for c, a in zip(row, aligns + [""] * len(row))) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue
        if ln.startswith("### "):
            out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append("<blockquote>" + "<br>".join(inline(b) for b in buf) + "</blockquote>")
            continue
        elif ln.startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].startswith("- "):
                out.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif ln.strip():
            cls = ' class="meta"' if ln.startswith("**Období:**") else ""
            out.append(f"<p{cls}>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        raise SystemExit(
            "Použití: report_pdf.py <vstup.md> <vystup.pdf> [\"Titulek\"]\n"
            "Sází přes headless Chrome, nic dalšího se neinstaluje."
        )
    src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    body = convert(src.read_text(encoding="utf-8"))
    title = html.escape(sys.argv[3] if len(sys.argv) > 3 else dst.stem)
    tmp = dst.with_suffix(".html")
    tmp.write_text(f"<!doctype html><html lang=cs><head><meta charset=utf-8>"
                   f"<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>",
                   encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={dst}", tmp.as_uri()],
                   check=True, capture_output=True, timeout=120)
    tmp.unlink()
    print(f"PDF: {dst} ({dst.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()

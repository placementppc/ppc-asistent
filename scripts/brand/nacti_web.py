#!/usr/bin/env python3
"""Načte web klienta a vytáhne podklady pro brand manuál (jen čte, nic neodesílá).

Co udělá:
  1. Stáhne homepage a z ní vybere 3–5 klíčových stránek (kategorie, produkt, o nás, kontakt).
  2. Stáhne jejich CSS (externí soubory + <style> + style="…").
  3. Vypíše strukturovaný JSON: barvy s četností (i z CSS proměnných, tlačítek, pozadí, textu),
     fonty (font-family, @font-face, Google Fonts), meta a og:image, kandidáty na logo,
     nadpisy, CTA texty, ukázky textů a odhad tykání / vykání.

Co neudělá:
  - Nespouští JavaScript. Weby renderované v prohlížeči (Next.js, React, část Shoptetu…)
    vrátí málo textu. Skript to pozná a v JSON nastaví `upozorneni` — pak doplň vestavěný
    prohlížeč (screenshot, přečtení stránky) a ruční kontrolu.
  - Neobchází robots.txt. Stránky zakázané pro všechny roboty přeskočí a napíše proč.

Použití:
  python3 scripts/brand/nacti_web.py https://www.muj-eshop.cz
  python3 scripts/brand/nacti_web.py https://www.muj-eshop.cz --max-stran 6 --out banner-generator/banners-muj-eshop/brand/web.json
  python3 scripts/brand/nacti_web.py https://www.muj-eshop.cz --stranky /o-nas/ /kontakt/

Exit: 0 OK · 1 načteno částečně / web nejspíš potřebuje prohlížeč · 2 chyba (homepage nejde načíst nebo ji zakazuje robots.txt).
Jen standardní knihovna Pythonu (3.9+).
"""
from __future__ import annotations

import argparse
import colorsys
import gzip
import json
import re
import sys
import time
import zlib
from collections import Counter
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen

USER_AGENT = "PPC-asistent-brand/1.0 (jednorazove nacteni webu pro brand manual)"
MAX_HTML_BYTES = 3_000_000
MAX_CSS_BYTES = 2_000_000
MAX_CSS_FILES = 15

# Klíčová slova v URL / textu odkazu → typ stránky. Pořadí = priorita výběru.
TYPY_STRANEK = [
    ("o-nas", ("o-nas", "o_nas", "onas", "about", "o-firme", "o-firmě", "pribeh", "příběh", "kdo-jsme")),
    ("kontakt", ("kontakt", "contact")),
    ("kategorie", ("kategorie", "category", "kolekce", "collection", "shop", "eshop", "e-shop", "obchod", "produkty", "products", "sluzby", "služby", "nabidka", "nabídka")),
    ("produkt", ("produkt", "product", "detail", "/p/", "zbozi", "zboží")),
]

CTA_SLOVA = re.compile(
    r"\b(koupit|kup|do košíku|do kosiku|objednat|objednej|objednejte|vyzkoušet|vyzkoušejte|vyzkoušej|"
    r"zjistit|zjistěte|zjisti|více|vice|přihlásit|přihlas|registr|rezerv|stáhnout|stáhni|začít|zacit|"
    r"poptat|poptávka|kontaktujte|napište|zavolejte|prohlédnout|nakupovat|vybrat|chci)\b",
    re.IGNORECASE,
)
VYKANI = re.compile(r"\b(vy|vás|vám|váš|vaše|vašeho|vaši|objednejte|zjistěte|vyzkoušejte|napište|zavolejte|"
                    r"kontaktujte|vyberte|nakupujte|přihlaste|získejte|máte|chcete|můžete|potřebujete)\b", re.IGNORECASE)
TYKANI = re.compile(r"\b(ty|tě|tebe|tobě|tvůj|tvoje|tvá|tvého|objednej|zjisti|vyzkoušej|napiš|zavolej|"
                    r"vyber|nakupuj|přihlas|získej|máš|chceš|můžeš|potřebuješ)\b", re.IGNORECASE)

NAMED_COLORS = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
    "gray": "#808080", "grey": "#808080", "orange": "#ffa500", "yellow": "#ffff00", "navy": "#000080",
    "silver": "#c0c0c0", "maroon": "#800000", "purple": "#800080", "teal": "#008080",
}
COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|rgba?\([^)]*\)|hsla?\([^)]*\)", re.IGNORECASE
)
DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)")
RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
VAR_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;{}]+)")
FONTFACE_RE = re.compile(r"@font-face\s*\{([^}]*)\}", re.IGNORECASE)
IMPORT_RE = re.compile(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", re.IGNORECASE)
COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy", "inherit", "initial",
                 "unset", "-apple-system", "blinkmacsystemfont", "ui-sans-serif", "ui-serif", "ui-monospace",
                 "emoji", "math", "fangsong", "revert"}


# ---------------------------------------------------------------- stahování

class Stahovac:
    def __init__(self, timeout: float, zpozdeni: float) -> None:
        self.timeout = timeout
        self.zpozdeni = zpozdeni
        self.robots: Dict[str, Optional[robotparser.RobotFileParser]] = {}
        self.chyby: List[str] = []
        self._posledni = 0.0

    def _robots_pro(self, url: str) -> Optional[robotparser.RobotFileParser]:
        p = urlparse(url)
        zaklad = f"{p.scheme}://{p.netloc}"
        if zaklad not in self.robots:
            rp = robotparser.RobotFileParser()
            try:
                data = self._get(zaklad + "/robots.txt", MAX_CSS_BYTES, kontrola_robots=False)[0]
                rp.parse(data.decode("utf-8", "replace").splitlines())
                self.robots[zaklad] = rp
            except Exception:
                self.robots[zaklad] = None  # robots.txt chybí nebo nejde načíst → bez omezení
        return self.robots[zaklad]

    def smi(self, url: str) -> bool:
        rp = self._robots_pro(url)
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def _get(self, url: str, limit: int, kontrola_robots: bool = True) -> Tuple[bytes, str, str]:
        if kontrola_robots and not self.smi(url):
            raise PermissionError(f"robots.txt zakazuje {url}")
        cekat = self.zpozdeni - (time.time() - self._posledni)
        if cekat > 0:
            time.sleep(cekat)
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/css,*/*;q=0.8",
            "Accept-Language": "cs,sk;q=0.9,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        })
        try:
            with urlopen(req, timeout=self.timeout) as r:
                data = r.read(limit + 1)
                kodovani = (r.headers.get("Content-Encoding") or "").lower()
                ctype = r.headers.get("Content-Type") or ""
                finalni = r.geturl()
        finally:
            self._posledni = time.time()
        if kodovani == "gzip":
            data = gzip.decompress(data)
        elif kodovani == "deflate":
            data = zlib.decompress(data)
        return data[:limit], ctype, finalni

    def text(self, url: str, limit: int) -> Optional[Tuple[str, str]]:
        """Vrátí (text, finální URL) nebo None a chybu zapíše do self.chyby."""
        try:
            data, ctype, finalni = self._get(url, limit)
        except PermissionError as e:
            self.chyby.append(str(e))
            return None
        except HTTPError as e:
            self.chyby.append(f"{url}: HTTP {e.code}")
            return None
        except (URLError, OSError, ValueError) as e:
            self.chyby.append(f"{url}: {getattr(e, 'reason', e)}")
            return None
        m = re.search(r"charset=([\w-]+)", ctype, re.IGNORECASE)
        kod = m.group(1) if m else "utf-8"
        try:
            return data.decode(kod, "replace"), finalni
        except LookupError:
            return data.decode("utf-8", "replace"), finalni


# ---------------------------------------------------------------- HTML

class Stranka(HTMLParser):
    """Jednoprůchodový sběr všeho, co je pro brand zajímavé."""

    PRESKOC = {"script", "noscript", "template", "svg"}

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title = ""
        self.lang = ""
        self.meta: Dict[str, str] = {}
        self.styly_odkazy: List[str] = []
        self.styly_inline: List[str] = []
        self.style_atributy: List[str] = []
        self.ikony: List[str] = []
        self.odkazy: List[Tuple[str, str]] = []
        self.obrazky: List[Dict[str, str]] = []
        self.nadpisy: List[Tuple[str, str]] = []
        self.cta: List[str] = []
        self.odstavce: List[str] = []
        self.inline_svg_logo = False
        self.next_data = False
        self._zasobnik: List[Tuple[str, Dict[str, str]]] = []
        self._text: List[str] = []
        self._v_title = False
        self._v_style = False
        self._preskakuj = 0
        self._zachyt: Optional[Tuple[str, List[str], Dict[str, str]]] = None
        self.viditelny_text: List[str] = []

    def handle_starttag(self, tag: str, attrs_l) -> None:  # noqa: C901
        a = {k: (v or "") for k, v in attrs_l}
        if tag in self.PRESKOC:
            if tag == "svg":
                trida = (a.get("class", "") + " " + a.get("id", "") + " " + a.get("aria-label", "")).lower()
                if "logo" in trida:
                    self.inline_svg_logo = True
            if tag == "script" and a.get("id") == "__NEXT_DATA__":
                self.next_data = True
            self._preskakuj += 1
            return
        if a.get("style"):
            self.style_atributy.append(a["style"])
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._v_title = True
        elif tag == "style":
            self._v_style = True
        elif tag == "meta":
            klic = (a.get("property") or a.get("name") or "").lower()
            if klic and a.get("content"):
                self.meta[klic] = a["content"]
        elif tag == "link":
            rel = a.get("rel", "").lower()
            href = a.get("href", "")
            if not href:
                return
            if "stylesheet" in rel or (a.get("as") == "style"):
                self.styly_odkazy.append(urljoin(self.base, href))
            if "icon" in rel:
                self.ikony.append(urljoin(self.base, href))
        elif tag == "a":
            href = a.get("href", "")
            if href and not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self._zachyt = ("a", [], a)
        elif tag == "button":
            self._zachyt = ("button", [], a)
        elif tag in ("h1", "h2", "h3"):
            self._zachyt = (tag, [], a)
        elif tag == "p":
            self._zachyt = ("p", [], a)
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or ""
            if src and not src.startswith("data:"):
                rodice = " ".join(f"{t} {at.get('class', '')} {at.get('id', '')}" for t, at in self._zasobnik[-4:])
                self.obrazky.append({
                    "src": urljoin(self.base, src),
                    "alt": a.get("alt", ""),
                    "trida": (a.get("class", "") + " " + a.get("id", "")).strip(),
                    "kontext": rodice.lower(),
                })
        elif tag == "input" and a.get("type", "").lower() in ("submit", "button") and a.get("value"):
            self.cta.append(a["value"].strip())
        if tag not in ("meta", "link", "img", "br", "hr", "input", "source"):
            self._zasobnik.append((tag, a))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.PRESKOC:
            self._preskakuj = max(0, self._preskakuj - 1)
            return
        if tag == "title":
            self._v_title = False
        elif tag == "style":
            self._v_style = False
        if self._zachyt and self._zachyt[0] == tag:
            druh, casti, a = self._zachyt
            text = re.sub(r"\s+", " ", " ".join(casti)).strip()
            self._zachyt = None
            if text:
                if druh in ("h1", "h2", "h3"):
                    self.nadpisy.append((druh, text))
                elif druh == "p" and len(text) >= 40:
                    self.odstavce.append(text)
                elif druh == "button":
                    self.cta.append(text)
                elif druh == "a":
                    self.odkazy.append((urljoin(self.base, a.get("href", "")), text))
                    trida = (a.get("class", "") + " " + a.get("role", "")).lower()
                    if any(k in trida for k in ("btn", "button", "cta")) or (len(text) <= 30 and CTA_SLOVA.search(text)):
                        self.cta.append(text)
            elif druh == "a":
                self.odkazy.append((urljoin(self.base, a.get("href", "")), ""))
        for i in range(len(self._zasobnik) - 1, -1, -1):
            if self._zasobnik[i][0] == tag:
                del self._zasobnik[i:]
                break

    def handle_data(self, data: str) -> None:
        if self._v_style:
            self.styly_inline.append(data)
            return
        if self._preskakuj:
            return
        if self._v_title:
            self.title += data
            return
        if data.strip():
            self.viditelny_text.append(data.strip())
            if self._zachyt:
                self._zachyt[1].append(data)


# ---------------------------------------------------------------- barvy a CSS

def na_hex(hodnota: str) -> Optional[str]:
    v = hodnota.strip().lower()
    if v in NAMED_COLORS:
        return NAMED_COLORS[v]
    if v.startswith("#"):
        h = v[1:]
        if len(h) in (3, 4):
            if len(h) == 4 and h[3] == "0":
                return None
            return "#" + "".join(c * 2 for c in h[:3])
        if len(h) in (6, 8):
            if len(h) == 8 and h[6:] == "00":
                return None
            return "#" + h[:6]
        return None
    m = re.match(r"(rgba?|hsla?)\(([^)]*)\)", v)
    if not m:
        return None
    cisla = re.findall(r"-?[\d.]+%?", m.group(2))
    if len(cisla) < 3:
        return None
    if len(cisla) >= 4:
        alfa = float(cisla[3].rstrip("%")) / (100 if cisla[3].endswith("%") else 1)
        if alfa < 0.15:
            return None  # skoro průhledné = nejde o brandovou barvu
    try:
        if m.group(1).startswith("rgb"):
            rgb = [float(c.rstrip("%")) * (2.55 if c.endswith("%") else 1) for c in cisla[:3]]
        else:
            h = float(cisla[0]) / 360.0
            s = float(cisla[1].rstrip("%")) / 100.0
            l = float(cisla[2].rstrip("%")) / 100.0
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            rgb = [r * 255, g * 255, b * 255]
    except ValueError:
        return None
    return "#" + "".join(f"{max(0, min(255, int(round(c)))):02x}" for c in rgb)


def je_neutralni(hexa: str) -> bool:
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < 18


def fonty_z_hodnoty(hodnota: str) -> List[str]:
    vysledek = []
    for cast in hodnota.split(","):
        jmeno = cast.strip().strip("'\"").strip()
        jmeno = re.sub(r"\s*!important$", "", jmeno)
        if jmeno and jmeno.lower() not in GENERIC_FONTS and not jmeno.startswith("var("):
            vysledek.append(jmeno)
    return vysledek


class CssSber:
    def __init__(self) -> None:
        self.barvy: Counter = Counter()
        self.barvy_tlacitek: Counter = Counter()
        self.barvy_pozadi: Counter = Counter()
        self.barvy_textu: Counter = Counter()
        self.promenne: Dict[str, str] = {}
        self.fonty: Counter = Counter()
        self.fonty_nadpisu: Counter = Counter()
        self.fonty_textu: Counter = Counter()
        self.font_face: List[Dict[str, str]] = []
        self.importy: List[str] = []

    def _barva(self, vlastnost: str, hodnota: str) -> List[str]:
        nalezene = []
        for m in COLOR_RE.findall(hodnota):
            h = na_hex(m)
            if h:
                nalezene.append(h)
        if not nalezene and vlastnost in ("color", "background-color", "background"):
            h = na_hex(hodnota.split()[0]) if hodnota.split() else None
            if h:
                nalezene.append(h)
        # var(--x) → hodnota proměnné, pokud ji už známe
        for jmeno in re.findall(r"var\((--[a-zA-Z0-9_-]+)", hodnota):
            if jmeno in self.promenne:
                h = na_hex(self.promenne[jmeno])
                if h:
                    nalezene.append(h)
        return nalezene

    def pridej(self, css: str, zdroj_url: str = "") -> None:
        css = COMMENT_RE.sub("", css)
        for m in IMPORT_RE.findall(css):
            self.importy.append(urljoin(zdroj_url, m) if zdroj_url else m)
        for blok in FONTFACE_RE.findall(css):
            fam = re.search(r"font-family\s*:\s*([^;]+)", blok, re.IGNORECASE)
            src = re.search(r"src\s*:\s*([^;]+)", blok, re.IGNORECASE)
            if fam:
                self.font_face.append({
                    "rodina": fam.group(1).strip().strip("'\""),
                    "zdroj": (src.group(1).strip()[:200] if src else ""),
                })
        css = FONTFACE_RE.sub("", css)
        for jmeno, hodnota in VAR_RE.findall(css):
            hodnota = hodnota.strip()
            if na_hex(hodnota) or COLOR_RE.search(hodnota):
                self.promenne.setdefault(jmeno, hodnota)
        for selektor, telo in RULE_RE.findall(css):
            sel = selektor.strip().lower()
            if sel.startswith("@"):
                continue
            tlacitko = any(k in sel for k in ("button", ".btn", "btn-", "cta", "[type=submit]", "add-to-cart", "addtocart"))
            nadpis = bool(re.search(r"(^|[\s,>])h[1-3]\b", sel)) or "heading" in sel or "title" in sel
            telo_stranky = bool(re.search(r"(^|,)\s*(html|body|:root)\s*(,|$)", sel))
            self.pridej_deklarace(telo, tlacitko=tlacitko, nadpis=nadpis, telo_stranky=telo_stranky)

    def pridej_deklarace(self, telo: str, tlacitko: bool = False, nadpis: bool = False,
                         telo_stranky: bool = False) -> None:
        for vlastnost, hodnota in DECL_RE.findall(telo):
            vlastnost = vlastnost.lower()
            hodnota = hodnota.strip()
            if vlastnost.startswith("--"):
                continue
            if vlastnost in ("font-family", "font"):
                fonty = fonty_z_hodnoty(hodnota if vlastnost == "font-family" else hodnota.split(" ", 3)[-1])
                if fonty:
                    self.fonty[fonty[0]] += 1
                    if nadpis:
                        self.fonty_nadpisu[fonty[0]] += 1
                    if telo_stranky:
                        self.fonty_textu[fonty[0]] += 1
                continue
            if not any(k in vlastnost for k in ("color", "background", "border", "fill", "stroke", "outline")):
                continue
            for h in self._barva(vlastnost, hodnota):
                self.barvy[h] += 1
                if tlacitko and vlastnost.startswith("background"):
                    self.barvy_tlacitek[h] += 1
                if telo_stranky and vlastnost.startswith("background"):
                    self.barvy_pozadi[h] += 1
                if telo_stranky and vlastnost == "color":
                    self.barvy_textu[h] += 1


# ---------------------------------------------------------------- výběr stránek

def vyber_stranky(odkazy: List[Tuple[str, str]], domena: str, kolik: int) -> List[Dict[str, str]]:
    videne = set()
    kandidati: Dict[str, List[str]] = {t: [] for t, _ in TYPY_STRANEK}
    for url, text in odkazy:
        url = urldefrag(url)[0]
        p = urlparse(url)
        if p.scheme not in ("http", "https") or p.netloc.replace("www.", "") != domena:
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|xml)$", p.path, re.IGNORECASE):
            continue
        if p.path in ("", "/") or url in videne:
            continue
        videne.add(url)
        stopa = (p.path + " " + text).lower()
        slova_stopy = set(re.split(r"[^0-9a-zá-ž]+", stopa))
        for typ, slova in TYPY_STRANEK:
            # celé slovo (ne „workshops" → „shop"), u vzorů s lomítkem stačí podřetězec
            if any((s in stopa) if "/" in s else (s in slova_stopy) for s in slova):
                kandidati[typ].append(url)
                break
    vyber: List[Dict[str, str]] = []
    # nejdřív po jedné od každého typu, pak doplnit kategorie / produkty
    for typ, _ in TYPY_STRANEK:
        if kandidati[typ] and len(vyber) < kolik:
            vyber.append({"typ": typ, "url": kandidati[typ].pop(0)})
    for typ in ("produkt", "kategorie"):
        while kandidati[typ] and len(vyber) < kolik:
            vyber.append({"typ": typ, "url": kandidati[typ].pop(0)})
    return vyber


def logo_kandidati(stranky: List[Stranka], meta: Dict[str, str]) -> List[Dict[str, str]]:
    skore: Dict[str, Dict[str, object]] = {}
    for s in stranky:
        for img in s.obrazky:
            stopa = f"{img['src']} {img['alt']} {img['trida']}".lower()
            body = 0
            if "logo" in stopa:
                body += 3
            if "header" in img["kontext"] or "navbar" in img["kontext"] or "brand" in img["kontext"]:
                body += 1
            if "logo" in img["kontext"]:
                body += 2
            if img["src"].lower().endswith(".svg"):
                body += 1
            if body >= 3:
                z = skore.setdefault(img["src"], {"src": img["src"], "alt": img["alt"], "body": 0})
                z["body"] = int(z["body"]) + body
    vysledek = sorted(skore.values(), key=lambda x: -int(x["body"]))[:6]
    out = [{"src": str(v["src"]), "alt": str(v["alt"]), "zdroj": "img na webu"} for v in vysledek]
    for klic in ("og:logo",):
        if meta.get(klic):
            out.append({"src": meta[klic], "alt": "", "zdroj": klic})
    if any(s.inline_svg_logo for s in stranky):
        out.append({"src": "(inline SVG v HTML)", "alt": "", "zdroj": "svg s třídou/ID logo — ulož ručně z prohlížeče"})
    return out


def top(counter: Counter, n: int) -> List[Dict[str, object]]:
    return [{"hodnota": k, "pocet": v} for k, v in counter.most_common(n)]


# ---------------------------------------------------------------- hlavní běh

def nacti(url: str, max_stran: int, extra: List[str], timeout: float, zpozdeni: float) -> Tuple[dict, int]:
    if not re.match(r"https?://", url):
        url = "https://" + url
    st = Stahovac(timeout, zpozdeni)
    domovska = st.text(url, MAX_HTML_BYTES)
    if domovska is None:
        return {"url": url, "chyby": st.chyby}, 2
    html, finalni = domovska
    domena = urlparse(finalni).netloc.replace("www.", "")
    hp = Stranka(finalni)
    hp.feed(html)

    vybrane = [{"typ": "homepage", "url": finalni}]
    for cesta in extra:
        vybrane.append({"typ": "zadana", "url": urljoin(finalni, cesta)})
    vybrane += vyber_stranky(hp.odkazy, domena, max(0, max_stran - len(vybrane)))
    vybrane = vybrane[:max_stran]

    stranky: List[Stranka] = [hp]
    vypis_stranek = [{"typ": "homepage", "url": finalni, "title": hp.title.strip(),
                      "znaku_textu": len(" ".join(hp.viditelny_text))}]
    for v in vybrane[1:]:
        r = st.text(v["url"], MAX_HTML_BYTES)
        if r is None:
            continue
        s = Stranka(r[1])
        s.feed(r[0])
        stranky.append(s)
        vypis_stranek.append({"typ": v["typ"], "url": r[1], "title": s.title.strip(),
                              "znaku_textu": len(" ".join(s.viditelny_text))})

    css = CssSber()
    css_soubory: List[str] = []
    for s in stranky:
        for blok in s.styly_inline:
            css.pridej(blok, s.base)
        for attr in s.style_atributy:
            css.pridej_deklarace(attr)
        for odkaz in s.styly_odkazy:
            if odkaz not in css_soubory and len(css_soubory) < MAX_CSS_FILES:
                css_soubory.append(odkaz)
    google_fonts = sorted({u for u in css_soubory if "fonts.googleapis.com" in u})
    for odkaz in [u for u in css_soubory if "fonts.googleapis.com" not in u]:
        r = st.text(odkaz, MAX_CSS_BYTES)
        if r:
            css.pridej(r[0], r[1])
    google_fonts += [u for u in css.importy if "fonts.googleapis.com" in u]
    google_rodiny = sorted({re.sub(r"[:&].*", "", f).replace("+", " ")
                            for u in google_fonts for f in re.findall(r"family=([^&]+)", u)})

    vse_text = " ".join(" ".join(s.viditelny_text) for s in stranky)
    vykani = len(VYKANI.findall(vse_text))
    tykani = len(TYKANI.findall(vse_text))
    if vykani + tykani < 5:
        osloveni = "nejasné (málo textu)"
    elif vykani >= tykani * 2:
        osloveni = "vykání"
    elif tykani >= vykani * 2:
        osloveni = "tykání"
    else:
        osloveni = "smíšené"

    cta = Counter(c for s in stranky for c in s.cta if 1 < len(c) <= 40)
    nadpisy = []
    for s in stranky:
        for uroven, text in s.nadpisy:
            if text not in [n["text"] for n in nadpisy] and len(text) <= 160:
                nadpisy.append({"uroven": uroven, "text": text})
    odstavce = []
    for s in stranky:
        for o in s.odstavce:
            if o not in odstavce:
                odstavce.append(o[:400])

    upozorneni = []
    malo_textu = [p["url"] for p in vypis_stranek if int(p["znaku_textu"]) < 400]
    if hp.next_data or 'id="__next"' in html or "data-reactroot" in html or 'id="root"></div>' in html \
            or "__NUXT__" in html or malo_textu:
        upozorneni.append(
            "Web nejspíš skládá obsah JavaScriptem (nebo má stránky s velmi málo textu: "
            + ", ".join(malo_textu[:3]) + "). Doplň vestavěný prohlížeč: screenshot homepage a produktu, "
            "přečtení textu stránky, barvy tlačítek z vykresleného webu. Výsledek zkontroluj ručně.")
    elif "/_next/" in html or "/_nuxt/" in html or "/wp-json/" in html and "elementor" in html.lower():
        upozorneni.append("Web je postavený na JS frameworku (Next.js / Nuxt / page builder). Server vrátil text, "
                          "ale část obsahu, barev a fontů se může dotahovat až v prohlížeči. Barvy tlačítek "
                          "a logo ověř na screenshotu z vestavěného prohlížeče.")
    if "shoptet" in html.lower():
        upozorneni.append("Web běží na Shoptetu: část barev pochází ze šablony Shoptetu, ne ze značky. "
                          "Barvy ověř podle loga a tlačítek na screenshotu.")
    if not css.barvy:
        upozorneni.append("V CSS se nenašly žádné barvy (CSS může být blokované nebo generované JS).")

    barevne = Counter({k: v for k, v in css.barvy.items() if not je_neutralni(k)})
    neutralni = Counter({k: v for k, v in css.barvy.items() if je_neutralni(k)})
    meta = hp.meta
    vysledek = {
        "url": finalni,
        "nacteno": time.strftime("%Y-%m-%d %H:%M"),
        "stranky": vypis_stranek,
        "meta": {
            "title": hp.title.strip(),
            "description": meta.get("description", ""),
            "lang": hp.lang,
            "og:title": meta.get("og:title", ""),
            "og:description": meta.get("og:description", ""),
            "og:image": meta.get("og:image", ""),
            "og:site_name": meta.get("og:site_name", ""),
            "theme-color": meta.get("theme-color", ""),
            "ikony": sorted(set(i for s in stranky for i in s.ikony))[:6],
        },
        "logo_kandidati": logo_kandidati(stranky, meta),
        "barvy": {
            "nejcastejsi_barevne": top(barevne, 12),
            "nejcastejsi_neutralni": top(neutralni, 8),
            "tlacitka_pozadi": top(css.barvy_tlacitek, 6),
            "pozadi_stranky": top(css.barvy_pozadi, 4),
            "text_stranky": top(css.barvy_textu, 4),
            "css_promenne": dict(list(css.promenne.items())[:40]),
            "theme_color_meta": meta.get("theme-color", ""),
        },
        "fonty": {
            "font_family_nejcastejsi": top(css.fonty, 8),
            "nadpisy": top(css.fonty_nadpisu, 4),
            "text_body": top(css.fonty_textu, 4),
            "font_face": css.font_face[:12],
            "google_fonts_odkazy": sorted(set(google_fonts))[:6],
            "google_fonts_rodiny": google_rodiny,
        },
        "texty": {
            "nadpisy": nadpisy[:40],
            "cta": top(cta, 20),
            "ukazky_odstavcu": odstavce[:15],
            "osloveni_odhad": {"vysledek": osloveni, "vykani_slov": vykani, "tykani_slov": tykani,
                               "pozn": "Hrubý odhad podle slov. Ověř na citacích."},
        },
        "css_souboru_nacteno": len(css_soubory),
        "upozorneni": upozorneni,
        "chyby": st.chyby,
    }
    kod = 1 if (upozorneni or st.chyby) else 0
    return vysledek, kod


def main() -> int:
    ap = argparse.ArgumentParser(description="Načte web klienta a vypíše podklady pro brand manuál (JSON).")
    ap.add_argument("url", help="adresa webu, např. https://www.muj-eshop.cz")
    ap.add_argument("--max-stran", type=int, default=6, help="kolik stránek celkem včetně homepage (default 6, max 10)")
    ap.add_argument("--stranky", nargs="*", default=[], help="konkrétní cesty navíc, např. /o-nas/ /kontakt/")
    ap.add_argument("--timeout", type=float, default=15.0, help="timeout jednoho požadavku v s (default 15)")
    ap.add_argument("--zpozdeni", type=float, default=1.0, help="pauza mezi požadavky v s (default 1)")
    ap.add_argument("--out", help="uloží JSON do souboru (jinak vypíše na výstup)")
    args = ap.parse_args()

    vysledek, kod = nacti(args.url, max(1, min(args.max_stran, 10)), args.stranky, args.timeout, args.zpozdeni)
    text = json.dumps(vysledek, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Uloženo do {args.out} · stránek {len(vysledek.get('stranky', []))} · "
              f"upozornění {len(vysledek.get('upozorneni', []))} · chyb {len(vysledek.get('chyby', []))}")
        for u in vysledek.get("upozorneni", []):
            print("⚠️ ", u)
    else:
        print(text)
    return kod


if __name__ == "__main__":
    sys.exit(main())

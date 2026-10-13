#!/usr/bin/env python3
"""Senegal: Journal officiel de la République du Sénégal (www.jo.gouv.sn, SPIP site).

The official site is unreachable (TCP time-outs), so Internet Archive captures of the official
pages are used. Steps:
  1. CDX listing of all captured jo.gouv.sn URLs           -> _raw/sn/cdx_all.txt
  2. fetch every captured issue page (spip.php?rubriqueN)  -> article id -> title index
  3. keep laws / ordinances / constitution / codes and fetch their article pages
  4. convert to Markdown (lois/<year>/, ordonnances/<year>/ ...)
Usage: python3 sn_fetch.py [--no-download]"""
import html
import json
import os
import re
import sys
import time

import requests
from lxml import html as LH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sn_text as T  # noqa

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(os.path.dirname(REPO), "_raw", "sn")
WB = "https://web.archive.org/web/%sid_/%s"
RETRIEVED = os.environ.get("LC_RETRIEVED", "2026-10-13")
S = requests.Session()
S.headers["User-Agent"] = T.UA

KEEP = re.compile(r"^\s*(LOI|Loi|loi|ORDONNANCE|Ordonnance|CONSTITUTION|Constitution|CODE |Code |"
                  r"D[ÉE]CRET[- ]LOI|Décret-loi)", re.U)


def cdx():
    path = os.path.join(RAW, "cdx_all.txt")
    if os.path.exists(path):
        return path
    out = open(path + ".part", "w")
    key = None
    while True:
        url = ("https://web.archive.org/cdx/search/cdx?url=jo.gouv.sn&matchType=domain&output=txt"
               "&filter=statuscode:200&collapse=urlkey&fl=original,timestamp,length&limit=20000&showResumeKey=true")
        if key:
            url += "&resumeKey=" + requests.utils.quote(key)
        for i in range(5):
            try:
                r = S.get(url, timeout=300)
                r.raise_for_status()
                break
            except Exception as e:  # noqa
                print("retry", e)
                time.sleep(30)
        lines = r.text.rstrip("\n").split("\n")
        key = None
        if len(lines) >= 2 and lines[-2] == "":
            key, lines = lines[-1], lines[:-2]
        out.write("\n".join(lines) + "\n")
        if not key:
            break
        time.sleep(3)
    out.close()
    os.replace(path + ".part", path)
    return path


def wb_get(orig, ts, dest):
    return T.fetch(WB % (ts, orig), dest, delay=2.5, timeout=120)


def read(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def main():
    os.makedirs(RAW, exist_ok=True)
    caps = {}
    for line in open(cdx()):
        p = line.split()
        if len(p) < 2:
            continue
        orig, ts = p[0], p[1]
        m = re.search(r"spip\.php\?(rubrique|article)(\d+)$", orig) or re.search(r"(rubrique|article)\.php3\?id_\w+=(\d+)$", orig)
        if not m:
            continue
        k = (m.group(1), int(m.group(2)))
        if k not in caps or ts > caps[k][1]:
            caps[k] = (orig, ts)
    print("captures: rubriques", sum(1 for k in caps if k[0] == "rubrique"), "articles", sum(1 for k in caps if k[0] == "article"))
    # 2. issue pages
    idx_path = os.path.join(RAW, "index.json")
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    done = set(index.get("_rubriques_done", []))
    for (kind, n), (orig, ts) in sorted(caps.items()):
        if kind != "rubrique" or n in done:
            continue
        dest = os.path.join(RAW, "rub", "%d.html" % n)
        if "--no-download" not in sys.argv:
            wb_get(orig, ts, dest)
        if not os.path.exists(dest):
            continue
        s = read(dest)
        jo = re.search(r"J\.O\.\s*N°\s*([^<]{3,80})", s)
        for m in re.finditer(r'<a[^>]*href="[^"]*?article(\d+)"[^>]*>(.*?)</a>', s, re.S):
            t = html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", m.group(2)))).strip()
            if t and t not in ("IMPRIMER",):
                index.setdefault(m.group(1), {"title": t, "jo": jo.group(1).strip() if jo else None, "rubrique": n})
        done.add(n)
        index["_rubriques_done"] = sorted(done)
        if len(done) % 25 == 0:
            json.dump(index, open(idx_path, "w"), ensure_ascii=False, indent=0)
    json.dump(index, open(idx_path, "w"), ensure_ascii=False, indent=0)
    # 3. articles
    want = []
    for aid, (orig, ts) in ((n, v) for (k, n), v in caps.items() if k == "article"):
        info = index.get(str(aid))
        if info is None and "--unknown" in sys.argv:
            want.append((aid, orig, ts, None))  # unknown title: fetch, decide from page
        elif KEEP.match(info["title"]):
            want.append((aid, orig, ts, info))
    print("articles to consider", len(want), "known-law", sum(1 for w in want if w[3]))
    for aid, orig, ts, info in sorted(want):
        dest = os.path.join(RAW, "art", "%d.html" % aid)
        if "--no-download" not in sys.argv:
            wb_get(orig, ts, dest)
    # 4. convert
    convert(caps, index, want)


def article_parts(s):
    doc = LH.fromstring(s)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    box = doc.xpath('//div[@id="explorei"]')
    if not box:
        return None
    box = box[0]
    jo = None
    txt_jo = box.text_content()
    m = re.search(r"J\.O\.\s*N°\s*(\d+)\s+du\s+(\w+\s+\d+\w*\s+\w+\s+\d{4})", txt_jo)
    if m:
        jo = (m.group(1), m.group(2))
    rt = box.xpath('.//div[@id="retour"]')
    for r in rt:
        r.getparent().remove(r)
    # ministry line (b/font) and title (B/FONT/div)
    lines = []
    for el in box.iter():
        if el.tag in ("p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "td"):
            el.tail = "\n" + (el.tail or "")
            if el.tag != "br":
                el.text = "\n" + (el.text or "")
    raw = box.text_content()
    for ln in raw.split("\n"):
        ln = T.norm(ln)
        lines.append(ln)
    # drop navigation prefix
    while lines and (not lines[0] or lines[0].startswith((">>", "ACCUEIL")) or re.match(r"^>?>?\s*ACCUEIL", lines[0]) or lines[0].startswith("J.O.")):
        lines.pop(0)
    return jo, lines


MONTHS = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
          "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12}


def parse_date(t):
    m = re.search(r"\b(\d{1,2})(?:er)?\s+([a-zéû]+)\s+(\d{4})", t, re.I)
    if m and m.group(2).lower() in MONTHS:
        return "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def classify(title):
    t = title.lower()
    if t.startswith("constitution") or "loi constitutionnelle" in t:
        return "constitution", "constitution"
    if t.startswith("loi organique"):
        return "lois-organiques", "organic_law"
    if t.startswith("loi"):
        return "lois", "act"
    if t.startswith("ordonnance"):
        return "ordonnances", "ordinance"
    if t.startswith("décret-loi") or t.startswith("decret-loi") or t.startswith("décret loi"):
        return "decrets-lois", "decree_law"
    if t.startswith("code"):
        return "codes", "code"
    return None, None


def convert(caps, index, want):
    used = {}
    n_ok = 0
    for aid, orig, ts, info in sorted(want):
        dest = os.path.join(RAW, "art", "%d.html" % aid)
        if not os.path.exists(dest):
            continue
        parts = article_parts(read(dest))
        if not parts:
            continue
        jo, lines = parts
        nz = [x for x in lines if x]
        if not nz:
            continue
        # first non-empty lines: ministry (upper case, optional) then title
        title = info["title"] if info else None
        if not title:
            for x in nz[:4]:
                if KEEP.match(x):
                    title = x
                    break
        if not title or not KEEP.match(title):
            continue
        cat, typ = classify(title)
        if not cat:
            continue
        # body starts after the short title line; keep everything (incl. exposé des motifs)
        try:
            k = lines.index(next(x for x in lines if x and T.norm(x).startswith(T.norm(title)[:25])))
            body_lines = lines[k + 1:]
            ministry = " ".join(x for x in lines[:k] if x)
        except StopIteration:
            body_lines, ministry = lines, ""
        while body_lines and not body_lines[0]:
            body_lines.pop(0)
        full_title = body_lines[0] if body_lines and len(body_lines[0]) > len(title) and body_lines[0][:10].lower() == title[:10].lower() else title
        body = T.structure(body_lines, "fr")
        if sum(len(x) for x in body) < 150:
            continue
        num = re.search(r"n[°o]\s*(\d{2,4}\s*[-–.]\s*\d+)", title, re.I)
        ident = num.group(1).replace(" ", "").replace("–", "-") if num else None
        date = parse_date(title)
        year = (date or "")[:4] or (re.search(r"(19|20)\d\d", title).group(0) if re.search(r"(19|20)\d\d", title) else "undated")
        if cat == "constitution":
            rel = "constitution/%s.md" % T.slug(title, 80)
        else:
            rel = "%s/%s/%s.md" % (cat, year, T.slug(("%s-%s" % (typ.split("_")[0], ident)) if ident else title, 80))
        if rel in used:
            if used[rel] == aid:
                continue
            rel = rel[:-3] + "-a%d.md" % aid
        used[rel] = aid
        meta = {"title": full_title, "identifier": ident, "type": typ, "jurisdiction": "sn", "language": "fr",
                "date": date, "status": "unknown",
                "source": "http://www.jo.gouv.sn/spip.php?article%d" % aid,
                "archived_source": WB.replace("id_", "") % (ts, orig),
                "gazette": ("Journal officiel n° %s du %s" % jo) if jo else (info or {}).get("jo"),
                "ministry": ministry.strip() or None,
                "retrieved": RETRIEVED}
        T.write_md(os.path.join(REPO, rel), meta, full_title, body)
        n_ok += 1
    print("written", n_ok)


CC_CONST = "https://conseilconstitutionnel.sn/la-constitution/"


def html_block_lines(el):
    """Text of block-level descendants of el, one line per block (line breaks kept)."""
    for b in el.xpath(".//br"):
        b.tail = "\n" + (b.tail or "")
    out = []
    blocks = el.xpath(".//p|.//h1|.//h2|.//h3|.//h4|.//h5|.//h6|.//li|.//tr|.//pre")
    for b in blocks:
        if b.xpath("ancestor::p|ancestor::li|ancestor::tr")[:1] and b.tag not in ("tr",):
            continue
        t = b.text_content()
        for ln in t.split("\n"):
            out.append(T.norm(ln))
        out.append("")
    return out


def constitution():
    dest = os.path.join(RAW, "constitution.html")
    if "--no-download" not in sys.argv or not os.path.exists(dest):
        T.fetch(CC_CONST, dest, delay=1)
    doc = LH.fromstring(read(dest))
    box = doc.xpath('//div[contains(@class,"entry-content")]')[0]
    lines = html_block_lines(box)
    body = T.structure(lines, "fr")
    meta = {"title": "Constitution de la République du Sénégal",
            "identifier": "Loi n° 2001-03 du 22 janvier 2001 portant Constitution, modifiée",
            "type": "constitution", "jurisdiction": "sn", "language": "fr", "date": "2001-01-22",
            "status": "in_force", "source": CC_CONST, "retrieved": RETRIEVED,
            "note": ("Consolidated text with notes on each amendment, as published by the Conseil constitutionnel "
                     "(including its foreword on discrepancies between the promulgated texts and the Journal officiel)")}
    T.write_md(os.path.join(REPO, "constitution", "constitution-2001.md"), meta, meta["title"], body)
    print("OK constitution", sum(len(x) for x in body))


if __name__ == "__main__":
    constitution()
    if "--constitution-only" not in sys.argv:
        main()

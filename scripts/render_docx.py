#!/usr/bin/env python3
"""Render a SOW markdown file into the Premier Cloud .docx house design.

    python3 scripts/render_docx.py build/foo-sow.md -o build/Foo-SOW.docx

Design comes entirely from `assets/premier-cloud-sow-template.docx`, which is
the real issued template stripped of its body and customer logos. Styles,
embedded Google Sans, the letterhead header, page setup and numbering are
reused untouched; only `word/document.xml` is rebuilt. Nothing here reinvents
the look — change the template, not this script.

Design facts inherited from the template (do not hardcode them differently):
  A4 portrait, 1in margins, distinct first page
  Body        Google Sans 11pt
  Heading1    18pt #6D9EEB bold      Heading2  14pt #6D9EEB bold
  Heading3    #434343 bold           Heading4  12pt #666666 regular
  Tables      fixed layout, black sz=8 borders, header row #4285F4 white bold
  Cover meta  left, bold label, #666666, 10pt
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "assets", "premier-cloud-sow-template.docx")

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
TABLE_W = 9000          # dxa, matches the template's tables
HEADER_FILL = "4285f4"  # Google blue header row
META_GREY = "666666"

DOC_OPEN = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
    "<w:body>"
)


# ---------------------------------------------------------------- inline runs

def runs(text: str, *, bold=False, size=None, color=None, align_rtl=True) -> str:
    """Emit runs for text, honouring **bold**, *italic* and [label](url)."""
    out = []
    token = re.compile(r"(\*\*[^*]+\*\*|\*[^*\n]+\*|\[[^\]]+\]\([^)]+\))")
    pos = 0
    for m in token.finditer(text):
        if m.start() > pos:
            out.append(_run(text[pos:m.start()], bold=bold, size=size, color=color))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append(_run(tok[2:-2], bold=True, size=size, color=color))
        elif tok.startswith("["):
            label = tok[1:tok.index("]")]
            # Hyperlinks need a relationship; render as styled text instead so
            # the package stays self-contained and rels never drift.
            out.append(_run(label, bold=bold, size=size, color="1155cc", underline=True))
        else:
            out.append(_run(tok[1:-1], bold=bold, size=size, color=color, italic=True))
        pos = m.end()
    if pos < len(text):
        out.append(_run(text[pos:], bold=bold, size=size, color=color))
    return "".join(out) or _run("", bold=bold, size=size, color=color)


def _run(text, *, bold=False, italic=False, size=None, color=None, underline=False) -> str:
    rpr = ""
    if bold:
        rpr += '<w:b w:val="1"/><w:bCs w:val="1"/>'
    if italic:
        rpr += '<w:i w:val="1"/><w:iCs w:val="1"/>'
    if color:
        rpr += f'<w:color w:val="{color}"/>'
    if size:
        rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    if underline:
        rpr += '<w:u w:val="single"/>'
    rpr += '<w:rtl w:val="0"/>'
    return f"<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"


def para(content: str, *, style=None, align=None, spacing=None, indent=None, numid=None, ilvl=0) -> str:
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if numid:
        ppr += f'<w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{numid}"/></w:numPr>'
    if spacing:
        ppr += spacing
    if indent:
        ppr += indent
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{content}</w:p>"


# -------------------------------------------------------------------- tables

def table(rows: list[list[str]]) -> str:
    cols = max(len(r) for r in rows)
    first = round(TABLE_W * (0.28 if cols > 2 else 0.45))
    rest = (TABLE_W - first) // max(cols - 1, 1)
    widths = [first] + [rest] * (cols - 1) if cols > 1 else [TABLE_W]
    widths[-1] += TABLE_W - sum(widths)

    border = "".join(
        f'<w:{e} w:color="000000" w:space="0" w:sz="8" w:val="single"/>'
        for e in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    tbl = [
        "<w:tbl><w:tblPr>"
        f'<w:tblW w:w="{TABLE_W}" w:type="dxa"/><w:jc w:val="left"/>'
        f"<w:tblBorders>{border}</w:tblBorders>"
        '<w:tblLayout w:type="fixed"/><w:tblLook w:val="0600"/></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>"
    ]
    for ri, row in enumerate(rows):
        cells = []
        for ci in range(cols):
            raw = row[ci] if ci < len(row) else ""
            head = ri == 0
            shd = f'<w:shd w:fill="{HEADER_FILL}" w:val="clear"/>' if head else ""
            body = runs(raw.replace("**", ""), bold=head, color="ffffff" if head else None)
            cells.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/>{shd}</w:tcPr>'
                + para(body, align="center" if head else None)
                + "</w:tc>"
            )
        tbl.append(f"<w:tr>{''.join(cells)}</w:tr>")
    tbl.append("</w:tbl>")
    # Word requires a paragraph after a table.
    return "".join(tbl) + para("")


# ------------------------------------------------------------------- parsing

def heading_map(lines: list[str]) -> dict:
    """Map markdown heading depths onto template styles, shallowest -> Heading1."""
    depths = sorted({len(m.group(1)) for line in lines
                     if (m := re.match(r"^(#{1,6})\s+\S", line))})
    # The document title is rendered on the cover, so drop the top level if it
    # is used exactly once (the title line).
    titles = [l for l in lines if re.match(r"^#\s+\S", l)]
    if depths and depths[0] == 1 and len(titles) == 1:
        depths = depths[1:]
    return {d: f"Heading{min(i + 1, 4)}" for i, d in enumerate(depths)}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def build_body(md: str, cover: dict) -> str:
    lines = md.split("\n")
    hmap = heading_map(lines)
    out: list[str] = []

    # The markdown carries its own cover and table of contents; this renderer
    # builds the cover from the template instead, so drop everything before the
    # first real section. The DRAFT banner is kept and moved above the cover.
    first_section = next(
        (idx for idx, l in enumerate(lines)
         if (m := re.match(r"^(#{1,6})\s+\S", l.strip())) and hmap.get(len(m.group(1))) == "Heading1"),
        0,
    )
    banner = [l.strip().lstrip(">").strip() for l in lines[:first_section]
              if l.strip().startswith(">")]
    lines = lines[first_section:]

    # ---- cover ----
    big = '<w:sz w:val="40"/><w:szCs w:val="40"/>'
    out.append(para("", spacing='<w:spacing w:after="0" w:before="200"/>'))
    out.append(para(_run(cover["title"], size=40), align="center",
                    spacing='<w:spacing w:after="0" w:before="200"/>'))
    if cover.get("subtitle"):
        out.append(para(_run(cover["subtitle"], size=32, color=META_GREY), align="center",
                        spacing='<w:spacing w:after="0" w:before="120"/>'))
    if cover.get("date"):
        out.append(para(_run(cover["date"], size=32), align="center",
                        spacing='<w:spacing w:after="0" w:before="200"/>'))
    out.append(para(""))
    for label, value in (("Prepared by:", cover.get("prepared_by", "")),
                         ("Prepared for:", cover.get("prepared_for", "")),
                         ("Date:", cover.get("date", "")),
                         ("Version:", cover.get("version", ""))):
        if not value:
            continue
        body = (_run(label + " ", bold=True, size=20, color=META_GREY)
                + _run(value, size=20, color=META_GREY))
        out.append(para(body, spacing='<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'))
    out.append(para("<w:r><w:br w:type=\"page\"/></w:r>"))
    for b in filter(None, banner):
        out.append(para(runs(b, size=20, color="B06000"),
                        indent='<w:ind w:left="240"/>',
                        spacing='<w:spacing w:after="60"/>'))
    if banner:
        out.append(para(""))

    # ---- body ----
    i, n = 0, len(lines)
    first_h1_seen = False
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue

        if s.startswith("|"):
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i]); i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block]
            rows = [r for r in rows if not all(re.fullmatch(r"-{2,}", c or "") for c in r)]
            if rows:
                out.append(table(rows))
            continue

        if re.fullmatch(r"-{3,}", s):
            i += 1
            continue

        if s.startswith(">"):
            block = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip()); i += 1
            for b in filter(None, block):
                out.append(para(runs(b, size=20, color="B06000"),
                                indent='<w:ind w:left="240"/>'))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            depth = len(m.group(1))
            text = clean(m.group(2))
            style = hmap.get(depth)
            if style is None:          # the cover title, already rendered
                i += 1
                continue
            if style == "Heading1" and first_h1_seen:
                pass
            first_h1_seen = first_h1_seen or style == "Heading1"
            out.append(para(runs(text), style=style))
            i += 1
            continue

        b = re.match(r"^(\s*)-\s+(.*)$", line)
        if b:
            lvl = min(len(b.group(1)) // 2, 2)
            out.append(para(runs(b.group(2)), numid=1, ilvl=lvl,
                            indent=f'<w:ind w:left="{720 + lvl * 360}" w:hanging="360"/>'))
            i += 1
            continue

        o = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if o:
            body = _run(f"{o.group(2)}. ", bold=True) + runs(o.group(3))
            out.append(para(body, indent='<w:ind w:left="720" w:hanging="360"/>',
                            spacing='<w:spacing w:after="60"/>'))
            i += 1
            continue

        buf = []
        while i < n:
            l = lines[i]
            t = l.strip()
            if (not t or t.startswith(("|", ">", "#"))
                    or re.fullmatch(r"-{3,}", t)
                    or re.match(r"^\s*-\s+", l) or re.match(r"^\s*\d+\.\s+", l)):
                break
            buf.append(t); i += 1
        if buf:
            out.append(para(runs(" ".join(buf)),
                            spacing='<w:spacing w:after="160" w:line="276" w:lineRule="auto"/>'))
    return "".join(out)


# ------------------------------------------------------------------- package

def render(md_path: str, out_path: str, cover: dict, template: str = TEMPLATE) -> None:
    md = open(md_path, encoding="utf-8").read()
    zin = zipfile.ZipFile(template)
    old = zin.read("word/document.xml").decode("utf-8")
    sectpr = re.search(r"<w:sectPr\b.*?</w:sectPr>", old, re.S).group(0)
    doc = DOC_OPEN + build_body(md, cover) + sectpr + "</w:body></w:document>"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zo:
        for name in zin.namelist():
            zo.writestr(name, doc if name == "word/document.xml" else zin.read(name))


def main() -> int:
    ap = argparse.ArgumentParser(description="Render SOW markdown into the house .docx design.")
    ap.add_argument("markdown")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title"); ap.add_argument("--subtitle")
    ap.add_argument("--date"); ap.add_argument("--version")
    ap.add_argument("--prepared-for"); ap.add_argument("--prepared-by", default="Premier Cloud Inc.")
    ap.add_argument("--template", default=TEMPLATE)
    a = ap.parse_args()

    if not os.path.exists(a.template):
        print(f"template not found: {a.template}", file=sys.stderr)
        return 1

    md = open(a.markdown, encoding="utf-8").read()
    # Fall back to the markdown's own front matter for anything not passed in.
    def sniff(pattern, default=""):
        m = re.search(pattern, md, re.M)
        return clean(m.group(1)) if m else default

    cover = {
        "title": a.title or sniff(r"^#\s+(.*)$", "Statement of Work"),
        "subtitle": a.subtitle or sniff(r"^\*\*(.+?)\*\*\s*$"),
        "date": a.date or sniff(r"^\*\*Date:\*\*\s*(.*)$"),
        "version": a.version or sniff(r"^\*\*Version:\*\*\s*(.*)$", "1.0"),
        "prepared_for": a.prepared_for or sniff(r"^\*\*Prepared for:\*\*\s*(.*)$"),
        "prepared_by": a.prepared_by or sniff(r"^\*\*Prepared by:\*\*\s*(.*)$"),
    }
    render(a.markdown, a.out, cover, a.template)
    print(f"Wrote {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

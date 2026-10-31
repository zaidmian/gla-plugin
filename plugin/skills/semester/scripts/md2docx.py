#!/usr/bin/env python3
"""md2docx.py — convert an ICS3U master-course markdown document into a
Google-Docs-ready .docx file. Zero dependencies (Python 3.9+ stdlib only).

Usage:
    python3 md2docx.py INPUT.md OUTPUT.docx [--strip-teacher-note] [--kind=test]

Design targets (see the semester SKILL.md):
- Body font Roboto 11pt, code font Roboto Mono. The fonts are referenced by
  name; they resolve when the file is uploaded to Google Docs even if not
  installed locally.
- The header block (the **Slot:** / **Type:** / **Expectations:** / **Marks:**
  lines under the title) renders as a shaded box with a maroon left bar (GLA
  accent). Because the .docx is a student handout, the box is rewritten: a
  fill-in **Name:** line for exercises, assignments, and tests, the **Due:** date, and
  **Marks:** (the slot IDs, type, and expectation codes are dropped).
- Slot IDs (U1.W2.D1 and the like) are replaced with their calendar date when
  a slot->date map is supplied (convert_instance.py reads it from the
  instance's calendar.yaml).
- References to other documents render as the referenced file's title, not its
  filename (`REF_Hardware_Terms.md` becomes "Reference: Hardware Terms").
- Teacher-only content is dropped from the student copy: the "Running this
  class with a substitute" box, the "How this is marked" section (covered once
  at the start of the semester, identical for every exercise), and sentences
  that point students at a teacher-only file (marking_notes, rubric, *_KEY,
  *_MARKING). The HTML twins (md2html.py) keep all of it.
- md H1 -> Title, H2 -> Heading 1, H3 -> Heading 2, H4 -> Heading 3 so the
  Google Docs outline works after upload.
- Tables get a shaded bold header row and light borders.
- Fenced code blocks render as a shaded single-cell table in Roboto Mono
  (spaces preserved).
- Blockquotes render as a gold-tinted box.
- Ordered/unordered lists keep their literal source numbering (course docs
  number questions continuously across sections, so auto-numbering would be
  wrong). Checkbox items (- [ ]) render with a ballot box character.
- Test papers (doc_kind="test", set on the manifest rule) get a layout of their
  own: the "Structure" blurb and the "Companion files" section are dropped,
  answers left in the teacher copy are stripped, each multiple-choice option is
  marked by its own letter instead of a bullet, short option sets lay out in
  columns, and every question gets air above it.
"""

import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- constants

BODY_FONT = "Roboto"
MONO_FONT = "Roboto Mono"

# GLA palette. Maroon is 872634, gold is DABE81, and every grey comes from one
# scale based on 272727. A tint is tint(c, p) = round(255 - (255 - ch) * p) per
# channel, where p is the share of the base colour. Grey steps allowed:
# p in {1.00, 0.75, 0.55, 0.40, 0.25, 0.12, 0.06, 0.03}. Gold is never used as
# text here, so no darker gold_text variant exists; add one if that changes.
ACCENT = "872634"       # GLA maroon, p 1.00 (header-block left bar, Heading 1)
GOLD_BG = "F9F5EC"      # gold tint p 0.15 (blockquote / substitute-box fill)
GOLD_BORDER = "DABE81"  # GLA gold, p 1.00 (blockquote border)
META_BG = "F5EEEF"      # maroon tint p 0.08 (header-block background)
CODE_BG = "F2F2F2"      # grey p 0.06 (code background)
TABLE_HEAD_BG = "F2F2F2"  # grey p 0.06 (table header row)
BORDER_GREY = "C9C9C9"  # grey p 0.25 (table and box borders)
TEXT_DARK = "272727"    # grey p 1.00 (title, Heading 2)
TEXT_GREY = "5D5D5D"    # grey p 0.75 (Heading 3, meta text, footer)

META_LABELS = ("Slot", "Type", "Expectations", "Marks", "Time", "Course")

# ---- list and test-paper layout (twips: 20 = 1pt)
LI_SPACING = ('<w:spacing w:before="0" w:after="60" '
              'w:line="276" w:lineRule="auto"/>')
Q_SPACING = ('<w:spacing w:before="260" w:after="80" '
             'w:line="276" w:lineRule="auto"/>')   # air above each question
OPT_SPACING = ('<w:spacing w:before="0" w:after="40" '
               'w:line="264" w:lineRule="auto"/>')  # options sit tight together
CELL_SPACING = ('<w:spacing w:before="0" w:after="60" '
                'w:line="264" w:lineRule="auto"/>')
NO_BORDERS = "".join(
    '<w:%s w:val="none" w:sz="0" w:space="0" w:color="auto"/>' % s
    for s in ("top", "left", "bottom", "right", "insideH", "insideV"))

MC_OPT_RE = re.compile(r"^([A-H])[.)]\s+(.+)$")
MC_COL4_MAX = 16        # longest option (printed chars) that fits 4 across
MC_COL2_MAX = 36        # ... and 2 across
QUESTION_RE = re.compile(r"^\*\*[A-Z]?\d+[a-z]?\.\*\*")   # **B1.** (3 marks) ...
ANSWER_LEAD_RE = re.compile(
    r"^\*\*(Answers?|Errors?|Fix|Output|Model answer|Accept|Marking"
    r"|Sample answer)(\s*\([^)]*\))?\s*:", re.I)

# ------------------------------------------------------------ inline parser

INLINE_RE = re.compile(
    r"(`[^`]+`)"                 # inline code
    r"|(\*\*\*[^*]+\*\*\*)"      # bold italic
    r"|(\*\*[^*]+(?:\*(?!\*)[^*]*)*\*\*)"  # bold (tolerates single * inside)
    r"|(\*[^*\s][^*]*\*)"        # italic
    r"|(\[[^\]]+\]\([^)\s]+\))"  # link
)


def parse_inline(text, base=None):
    """Return a list of run dicts: {text, bold, italic, code, link}."""
    base = base or {}
    runs = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            runs.append(dict(base, text=text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("`"):
            runs.append(dict(base, text=tok[1:-1], code=True))
        elif tok.startswith("***"):
            runs.extend(parse_inline(tok[3:-3], dict(base, bold=True, italic=True)))
        elif tok.startswith("**"):
            runs.extend(parse_inline(tok[2:-2], dict(base, bold=True)))
        elif tok.startswith("["):
            lm = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)", tok)
            runs.extend(parse_inline(lm.group(1), dict(base, link=lm.group(2))))
        else:  # *italic*
            runs.extend(parse_inline(tok[1:-1], dict(base, italic=True)))
        pos = m.end()
    if pos < len(text):
        runs.append(dict(base, text=text[pos:]))
    return [r for r in runs if r.get("text")]


# ------------------------------------------------------------- block parser

def parse_blocks(lines):
    """Parse markdown lines into a list of block dicts."""
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i].rstrip("\n"))
                i += 1
            i += 1  # closing fence
            blocks.append({"type": "code", "lines": code})
            continue

        # heading
        hm = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if hm:
            blocks.append({"type": "heading", "level": len(hm.group(1)),
                           "text": hm.group(2).strip()})
            i += 1
            continue

        # horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*> ?", "", lines[i].rstrip("\n")))
                i += 1
            blocks.append({"type": "quote", "blocks": parse_blocks(quote)})
            continue

        # table
        if stripped.startswith("|") and i + 1 < n and \
                re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows, aligns = [], []
            header = split_row(lines[i])
            aligns = parse_aligns(lines[i + 1], len(header))
            rows.append(header)
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            blocks.append({"type": "table", "rows": rows, "aligns": aligns})
            continue

        # list item (ordered, unordered, checkbox, lettered continuation)
        lm = re.match(r"^(\s*)(?:([-*])|(\d+)[.)]|([a-z])\))\s+(.*)$", line.rstrip("\n"))
        if lm:
            indent, bullet, num, letter, rest = lm.groups()
            level = min(len(indent) // 3, 3)
            marker = "•"  # bullet
            if num:
                marker = num + "."
            elif letter:
                marker = letter + ")"
                level = max(level, 1)
            elif rest.startswith("[ ]"):
                marker, rest = "☐", rest[3:].strip()   # ballot box
            elif rest.startswith("[x]") or rest.startswith("[X]"):
                marker, rest = "☑", rest[3:].strip()
            blocks.append({"type": "li", "level": level, "marker": marker,
                           "text": rest})
            i += 1
            continue

        # plain paragraph: consume consecutive plain lines
        para = [stripped]
        i += 1
        while i < n:
            nxt = lines[i]
            s = nxt.strip()
            if (not s or s.startswith(("#", ">", "|", "```"))
                    or re.match(r"^(-{3,}|\*{3,})$", s)
                    or re.match(r"^(\s*)(?:[-*]|\d+[.)]|[a-z]\))\s+", nxt)):
                break
            para.append(s)
            i += 1
        # meta-line paragraphs (bold-label header block) keep their line breaks
        if all(re.match(r"^\*\*(%s)" % "|".join(META_LABELS), p) for p in para):
            blocks.append({"type": "meta", "lines": para})
        else:
            blocks.append({"type": "para", "text": " ".join(para)})
    return blocks


def split_row(line):
    # an escaped pipe (\|) belongs to the cell, as in `\|\|` for Java's OR
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_aligns(sep, ncols):
    aligns = []
    for c in sep.strip().strip("|").split("|"):
        c = c.strip()
        if c.startswith(":") and c.endswith(":"):
            aligns.append("center")
        elif c.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")
    while len(aligns) < ncols:
        aligns.append("left")
    return aligns


# --------------------------------------------------------------- XML output

class DocBuilder:
    def __init__(self):
        self.body = []
        self.rels = []       # (rid, url) hyperlinks
        self._rid = 10       # rIds 1..9 reserved for static parts

    def next_rid(self, url):
        self._rid += 1
        rid = "rId%d" % self._rid
        self.rels.append((rid, url))
        return rid

    # ---- runs

    def run_xml(self, run, force_bold=False, size=None, color=None,
                mono=False, base_size=22):
        props = []
        code = run.get("code") or mono
        if code:
            props.append('<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>'
                         % (MONO_FONT, MONO_FONT, MONO_FONT))
            props.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>'
                         % (size or 20, size or 20))
            if run.get("code") and not mono:
                props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % CODE_BG)
        elif size:
            props.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size))
        if run.get("bold") or force_bold:
            props.append("<w:b/>")
        if run.get("italic"):
            props.append("<w:i/>")
        if run.get("link"):
            props.append('<w:color w:val="1155CC"/><w:u w:val="single"/>')
        elif color:
            props.append('<w:color w:val="%s"/>' % color)
        rpr = "<w:rPr>%s</w:rPr>" % "".join(props) if props else ""
        text = '<w:t xml:space="preserve">%s</w:t>' % escape(run["text"])
        r = "<w:r>%s%s</w:r>" % (rpr, text)
        if run.get("link"):
            rid = self.next_rid(run["link"])
            return '<w:hyperlink r:id="%s">%s</w:hyperlink>' % (rid, r)
        return r

    def runs_xml(self, runs, **kw):
        return "".join(self.run_xml(r, **kw) for r in runs)

    # ---- paragraphs

    def para(self, runs, style=None, jc=None, ind=None, spacing=None,
             tabs=None, lead="", **runkw):
        ppr = []
        if style:
            ppr.append('<w:pStyle w:val="%s"/>' % style)
        if tabs:
            ppr.append("<w:tabs>%s</w:tabs>" % "".join(
                '<w:tab w:val="left" w:pos="%d"/>' % t for t in tabs))
        if spacing:
            ppr.append(spacing)
        if ind:
            ppr.append(ind)
        if jc:
            ppr.append('<w:jc w:val="%s"/>' % jc)
        pprx = "<w:pPr>%s</w:pPr>" % "".join(ppr) if ppr else ""
        return "<w:p>%s%s%s</w:p>" % (pprx, lead, self.runs_xml(runs, **runkw))

    # ---- boxed single-cell table helper

    def box_table(self, inner_xml, bg, border_color, border_size=4,
                  left_bar=None):
        left = ('<w:left w:val="single" w:sz="%d" w:space="0" w:color="%s"/>'
                % ((24, left_bar) if left_bar else (border_size, border_color)))
        borders = (
            '<w:tblBorders>'
            '<w:top w:val="single" w:sz="%(s)d" w:space="0" w:color="%(c)s"/>'
            '%(left)s'
            '<w:bottom w:val="single" w:sz="%(s)d" w:space="0" w:color="%(c)s"/>'
            '<w:right w:val="single" w:sz="%(s)d" w:space="0" w:color="%(c)s"/>'
            '</w:tblBorders>' % {"s": border_size, "c": border_color, "left": left})
        return (
            '<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>%s'
            '<w:tblCellMar>'
            '<w:top w:w="140" w:type="dxa"/><w:left w:w="220" w:type="dxa"/>'
            '<w:bottom w:w="140" w:type="dxa"/><w:right w:w="220" w:type="dxa"/>'
            '</w:tblCellMar></w:tblPr>'
            '<w:tr><w:tc><w:tcPr>'
            '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
            '</w:tcPr>%s</w:tc></w:tr></w:tbl>'
            % (borders, bg, inner_xml)) + self.spacer()

    @staticmethod
    def spacer(after=60, sz=8):
        # empty small paragraph after tables so consecutive tables don't merge
        return ('<w:p><w:pPr><w:spacing w:before="0" w:after="%d" '
                'w:line="240" w:lineRule="auto"/>'
                '<w:rPr><w:sz w:val="%d"/></w:rPr></w:pPr></w:p>' % (after, sz))

    # ---- block renderers

    def render_blocks(self, blocks, in_quote=False):
        out = []
        for b in blocks:
            t = b["type"]
            if t == "heading":
                out.append(self.render_heading(b))
            elif t == "meta":
                out.append(self.render_meta(b))
            elif t == "para":
                out.append(self.para(parse_inline(b["text"]),
                                     spacing=b.get("spacing")))
            elif t == "li":
                out.append(self.render_li(b, in_quote=in_quote))
            elif t == "table":
                out.append(self.render_table(b))
            elif t == "code":
                out.append(self.render_code(b))
            elif t == "quote":
                out.append(self.render_quote(b))
            elif t == "mcopts":
                out.append(self.render_mcopts(b))
            elif t == "hr":
                out.append(
                    '<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" '
                    'w:space="1" w:color="%s"/></w:pBdr>'
                    '<w:spacing w:after="160"/></w:pPr></w:p>' % BORDER_GREY)
        return "".join(out)

    def render_heading(self, b):
        style = {1: "Title", 2: "Heading1", 3: "Heading2"}.get(b["level"], "Heading3")
        return self.para(parse_inline(b["text"]), style=style)

    def render_meta(self, b):
        inner = "".join(
            self.para(parse_inline(line),
                      spacing='<w:spacing w:before="0" w:after="40" '
                              'w:line="240" w:lineRule="auto"/>',
                      size=20, color=TEXT_GREY)
            for line in b["lines"])
        return self.box_table(inner, META_BG, META_BG, left_bar=ACCENT)

    def render_li(self, b, in_quote=False):
        left = 360 + 400 * b["level"]
        return self.para(
            parse_inline(b["text"]), tabs=[left],
            ind='<w:ind w:left="%d" w:hanging="360"/>' % left,
            spacing=b.get("spacing") or LI_SPACING,
            lead=self.run_xml({"text": b["marker"]}) + "<w:r><w:tab/></w:r>")

    def render_mcopts(self, b):
        """Multiple-choice options: lettered items down the page, or, when they
        are short enough to gain from it, laid out across in columns."""
        if b["cols"] < 2:
            return "".join(
                self.render_li(dict(o, type="li", spacing=OPT_SPACING))
                for o in b["opts"])
        return self.option_table(b["opts"], b["cols"])

    def option_table(self, opts, cols, width=9000, indent=360, hang=280):
        """One option per cell with no borders drawn: the letters line up in
        columns without a grid appearing on the test paper."""
        w = width // cols
        rows = []
        for r in range(0, len(opts), cols):
            cells = []
            for c in range(cols):
                o = opts[r + c] if r + c < len(opts) else None
                p = self.para(
                    parse_inline(o["text"]) if o else [],
                    tabs=[hang], spacing=CELL_SPACING,
                    ind='<w:ind w:left="%d" w:hanging="%d"/>' % (hang, hang),
                    lead=(self.run_xml({"text": o["marker"]})
                          + "<w:r><w:tab/></w:r>") if o else "")
                cells.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
                             '</w:tcPr>%s</w:tc>' % (w, p))
            rows.append("<w:tr>%s</w:tr>" % "".join(cells))
        return (
            '<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/>'
            '<w:tblLayout w:type="fixed"/>'
            '<w:tblInd w:w="%d" w:type="dxa"/>'
            '<w:tblBorders>%s</w:tblBorders>'
            '<w:tblCellMar>'
            '<w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
            '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="140" w:type="dxa"/>'
            '</w:tblCellMar></w:tblPr><w:tblGrid>%s</w:tblGrid>%s</w:tbl>'
            % (width, indent, NO_BORDERS,
               ('<w:gridCol w:w="%d"/>' % w) * cols, "".join(rows))
        ) + self.spacer(after=0, sz=4)

    def render_table(self, b):
        ncols = max(len(r) for r in b["rows"])
        border = ('<w:%(side)s w:val="single" w:sz="4" w:space="0" '
                  'w:color="' + BORDER_GREY + '"/>')
        borders = "<w:tblBorders>%s</w:tblBorders>" % "".join(
            border % {"side": s}
            for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
        xml = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>', borders,
               '<w:tblCellMar>'
               '<w:top w:w="80" w:type="dxa"/><w:left w:w="140" w:type="dxa"/>'
               '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="140" w:type="dxa"/>'
               '</w:tblCellMar></w:tblPr>']
        for ri, row in enumerate(b["rows"]):
            xml.append("<w:tr>")
            if ri == 0:
                xml.append("<w:trPr><w:tblHeader/></w:trPr>")
            for ci in range(ncols):
                cell = row[ci] if ci < len(row) else ""
                align = b["aligns"][ci] if ci < len(b["aligns"]) else "left"
                shd = ('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
                       % TABLE_HEAD_BG) if ri == 0 else ""
                p = self.para(parse_inline(cell),
                              jc=align if align != "left" else None,
                              spacing='<w:spacing w:before="0" w:after="0" '
                                      'w:line="240" w:lineRule="auto"/>',
                              force_bold=(ri == 0), size=21)
                xml.append("<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>" % (shd, p))
            xml.append("</w:tr>")
        xml.append("</w:tbl>")
        return "".join(xml) + self.spacer()

    def render_code(self, b):
        lines = b["lines"] or [""]
        inner = "".join(
            self.para([{"text": ln if ln else " "}],
                      spacing='<w:spacing w:before="0" w:after="0" '
                              'w:line="240" w:lineRule="auto"/>',
                      mono=True, size=20)
            for ln in lines)
        return self.box_table(inner, CODE_BG, BORDER_GREY)

    def render_quote(self, b):
        inner = self.render_blocks(b["blocks"], in_quote=True)
        return self.box_table(inner, GOLD_BG, GOLD_BORDER)


# ------------------------------------------------------------- static parts

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="{body}" w:hAnsi="{body}" w:eastAsia="{body}" w:cs="{body}"/>
<w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="{dark}"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr>
<w:spacing w:before="0" w:after="160" w:line="276" w:lineRule="auto"/>
</w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="120"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="48"/><w:szCs w:val="48"/><w:color w:val="{dark}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/><w:color w:val="{accent}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/><w:color w:val="{dark}"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="2"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="{grey}"/></w:rPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
<Application>GLA semester (Google Docs handouts)</Application></Properties>"""


def core_xml(title):
    return ("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>%s</dc:title><dc:creator>GLA semester</dc:creator>
</cp:coreProperties>""" % escape(title))


FOOTER_RID = "rId2"  # fixed; hyperlink rIds start at rId11, so no collision

# centered "Page X of Y" using PAGE / NUMPAGES field codes (9pt grey)
FOOTER_XML = ("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" """
"""xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">"""
'<w:p><w:pPr><w:jc w:val="center"/>'
'<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
'<w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="%(g)s"/></w:rPr></w:pPr>'
'<w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="%(g)s"/></w:rPr>'
'<w:t xml:space="preserve">Page </w:t></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:t xml:space="preserve"> of </w:t></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:instrText xml:space="preserve"> NUMPAGES </w:instrText></w:r>'
'<w:r><w:rPr><w:sz w:val="18"/><w:color w:val="%(g)s"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
'</w:p></w:ftr>') % {"g": TEXT_GREY}


def document_rels(hyperlinks):
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            % FOOTER_RID]
    for rid, url in hyperlinks:
        rels.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/'
                    'officeDocument/2006/relationships/hyperlink" Target="%s" '
                    'TargetMode="External"/>' % (rid, escape(url, {'"': "&quot;"})))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships">%s</Relationships>' % "".join(rels))


def document_xml(body):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<w:body>%s'
        '<w:sectPr>'
        '<w:footerReference w:type="default" r:id="%s"/>'
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '</w:sectPr></w:body></w:document>' % (body, FOOTER_RID))


# ------------------------------------------------- student-copy transforms

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def format_date(iso):
    """'2026-09-16' -> 'September 16, 2026'."""
    y, m, d = iso.split("-")
    return "%s %d, %s" % (MONTHS[int(m) - 1], int(d), y)


def is_teacher_only_ref(name):
    """True for a referenced file that students should never be sent to."""
    stem = name.rsplit("/", 1)[-1]
    if stem in ("marking_notes.md", "rubric.md", "rubric.csv"):
        return True
    base = stem[:-3] if stem.endswith(".md") else stem
    return base.endswith(("_KEY", "_MARKING"))


def resolve_title(name, src_dir):
    """The H1 title of a referenced markdown file, resolved beside the source."""
    if not name.endswith(".md"):
        return None
    p = src_dir / name
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def is_substitute_quote(b):
    return b["type"] == "quote" and any(
        ib["type"] == "heading"
        and ib["text"].lower().startswith("running this class with a substitute")
        for ib in b["blocks"])


def strip_section(blocks, starts):
    """Drop a heading whose text starts with `starts` and every block under it
    up to the next heading of the same or higher level."""
    out, skip_level = [], None
    for b in blocks:
        if b["type"] == "heading":
            if skip_level is not None and b["level"] <= skip_level:
                skip_level = None
            if skip_level is None and b["text"].lower().startswith(starts):
                skip_level = b["level"]
                continue
        if skip_level is None:
            out.append(b)
    return out


def strip_bold_lead(blocks, labels):
    """Drop a paragraph whose bold lead-in is one of `labels`, the inline twin
    of the section `strip_section` removes by heading (**Structure:** ...)."""
    pat = re.compile(r"^\*\*(%s):?\*\*" % "|".join(labels), re.I)
    return [b for b in blocks
            if not (b["type"] == "para" and pat.match(b["text"]))]


def strip_answers(blocks):
    """Remove the answers a teacher copy carries inline: the bolding on the
    correct multiple-choice option, and whole lines that lead with Answer:,
    Error:, Accept: or Marking:."""
    out = []
    for b in blocks:
        if b["type"] in ("para", "li") and ANSWER_LEAD_RE.match(b["text"]):
            continue
        if b["type"] == "li" and MC_OPT_RE.match(re.sub(r"^\*\*|\*\*$", "", b["text"])):
            b["text"] = re.sub(r"^\*\*(.*)\*\*$", r"\1", b["text"].strip())
        if b["type"] == "table":
            # a trace table's answers are the bolded cells; blank them
            b["rows"] = [b["rows"][0]] + [
                ["" if re.fullmatch(r"\*\*.*\*\*", c.strip()) else c for c in row]
                for row in b["rows"][1:]]
        out.append(b)
    return out


def option_width(text):
    """Roughly how wide an option prints, in body characters. Markup does not
    print; a monospace run is about a third wider per character."""
    mono = sum(len(m) for m in re.findall(r"`([^`]+)`", text))
    return len(re.sub(r"[`*]", "", text)) + mono // 3


def mc_columns(opts):
    """How many columns one option group gets. 1 keeps the vertical list."""
    longest = max(option_width(o["text"]) for o in opts)
    if longest <= MC_COL4_MAX and len(opts) <= 4:
        return len(opts)
    if longest <= MC_COL2_MAX and len(opts) % 2 == 0:
        return 2
    return 1


def group_mc_options(blocks):
    """Fold each run of A. / B. / C. bullets into one mcopts block: the letter
    becomes the marker and the longest option picks the column count. The run
    has to be A, B, C, ... in order and at least three long, so an ordinary
    bullet list that happens to start with "A." is left alone."""
    out, i, n = [], 0, len(blocks)
    while i < n:
        opts, j = [], i
        while j < n and blocks[j]["type"] == "li" and blocks[j]["marker"] == "\u2022":
            m = MC_OPT_RE.match(blocks[j]["text"])
            if not m or m.group(1) != chr(ord("A") + len(opts)):
                break
            opts.append({"level": blocks[j]["level"], "marker": m.group(1) + ".",
                         "text": m.group(2).strip()})
            j += 1
        if len(opts) >= 3:
            out.append({"type": "mcopts", "opts": opts, "cols": mc_columns(opts)})
            i = j
            continue
        out.append(blocks[i])
        i += 1
    return out


def space_questions(blocks):
    """Give every numbered question air above it so the paper does not read as
    a wall of text. Options keep their own tight spacing."""
    for b in blocks:
        numbered_li = (b["type"] == "li" and b["level"] == 0
                       and b["marker"][:-1].isdigit())
        if numbered_li or (b["type"] == "para" and QUESTION_RE.match(b["text"])):
            b["spacing"] = Q_SPACING


def apply_test_layout(blocks):
    """The test-paper pass. Runs last, so the text transforms above only ever
    see plain li blocks."""
    blocks = group_mc_options(blocks)
    space_questions(blocks)
    return blocks


def strip_teacher_sentences(blocks):
    """Drop sentences that point at a teacher-only file; drop a block left empty."""
    out = []
    for b in blocks:
        if b["type"] in ("para", "li"):
            kept = [s for s in re.split(r"(?<=[.!?])\s+", b["text"])
                    if not any(is_teacher_only_ref(t)
                               for t in re.findall(r"`([^`]+)`", s))]
            b["text"] = " ".join(kept)
            if not b["text"].strip():
                continue
        elif b["type"] == "quote":
            b["blocks"] = strip_teacher_sentences(b["blocks"])
            if not b["blocks"]:
                continue
        out.append(b)
    return out


def map_text(blocks, fn):
    """Apply fn to every rendered text field (paragraphs, list items, headings,
    table cells; recurses into quotes). Leaves meta and code blocks alone."""
    for b in blocks:
        t = b["type"]
        if t in ("para", "li", "heading"):
            b["text"] = fn(b["text"])
        elif t == "table":
            b["rows"] = [[fn(c) for c in row] for row in b["rows"]]
        elif t == "quote":
            map_text(b["blocks"], fn)


def make_slot_sub(slot_dates):
    if not slot_dates:
        return lambda t: t
    pat = re.compile(r"\b(%s)\b" % "|".join(
        re.escape(k) for k in sorted(slot_dates, key=len, reverse=True)))
    return lambda t: pat.sub(lambda m: slot_dates[m.group(1)], t)


def make_ref_sub(src_dir):
    """Replace an inline-code filename with the referenced file's title, set in
    italics so it stays distinct from the surrounding text."""
    def repl(m):
        title = resolve_title(m.group(1), src_dir)
        return "*%s*" % title if title else m.group(0)
    return lambda t: re.sub(r"`([^`]+)`", repl, t)


def normalize_emdash(blocks):
    """Replace em-dashes (they slip in from the master content; the house rule is
    commas or parentheses). A heading's first em-dash reads better as a colon."""
    for b in blocks:
        t = b["type"]
        if t == "heading":
            b["text"] = re.sub(r"\s*—\s*", ": ", b["text"], count=1)
            b["text"] = re.sub(r"\s*—\s*", ", ", b["text"])
        elif t in ("para", "li"):
            b["text"] = re.sub(r"\s*—\s*", ", ", b["text"])
        elif t == "table":
            b["rows"] = [[re.sub(r"\s*—\s*", ", ", c) for c in row]
                         for row in b["rows"]]
        elif t == "quote":
            normalize_emdash(b["blocks"])


def parse_meta_fields(lines):
    """[(label, value), ...] from the header block, splitting the ·-joined line."""
    fields = []
    for line in lines:
        for seg in line.split(" · "):
            m = re.match(r"^\*\*([A-Za-z ]+):\*\*\s*(.*)$", seg.strip())
            if m:
                fields.append((m.group(1).strip(), m.group(2).strip()))
    return fields


def rebuild_meta(lines, slot_dates, is_handout):
    """Rewrite the header block for the student copy: a Name line (exercises,
    assignments, tests), the Due date, and Marks. Slot IDs, type, and
    expectations are dropped."""
    fields = dict(parse_meta_fields(lines))
    out = []
    if is_handout:
        out.append("**Name:** " + "_" * 44)
    m = re.search(r"due\s+([A-Za-z0-9.]+)", fields.get("Slot", ""))
    if m:
        due = (slot_dates or {}).get(m.group(1), m.group(1))
        out.append("**Due:** " + due)
    for label in ("Marks", "Time", "Course"):
        if label in fields:
            out.append("**%s:** %s" % (label, fields[label]))
    return out


# --------------------------------------------------------------------- main

def convert(md_path, out_path, strip_teacher_note=False, slot_dates=None,
            doc_kind=None):
    text = Path(md_path).read_text(encoding="utf-8")
    lines = text.split("\n")
    blocks = parse_blocks(lines)

    if strip_teacher_note:
        blocks = [b for b in blocks
                  if not (b["type"] == "para"
                          and b["text"].lower().startswith("teacher copy"))]

    title = next((b["text"] for b in blocks
                  if b["type"] == "heading" and b["level"] == 1), Path(md_path).stem)
    meta_lines = next((b["lines"] for b in blocks if b["type"] == "meta"), [])
    meta_type = dict(parse_meta_fields(meta_lines)).get("Type", "").lower()
    # exercises, assignments, and tests are written on by students, so they get
    # a Name line; assess is the test type
    is_handout = (meta_type in ("exercise", "assignment", "assess")
                  or title.lower().startswith(("exercise", "assignment")))

    # student-copy cleanup: drop teacher-only content, then rewrite text
    blocks = [b for b in blocks if not is_substitute_quote(b)]
    blocks = strip_section(blocks, "how this is marked")
    if doc_kind == "test":
        # prefix match: no test carries a heading that starts either way
        blocks = strip_section(blocks, ("structure", "companion files"))
        blocks = strip_bold_lead(blocks, ("Structure",))
        blocks = strip_answers(blocks)
    blocks = strip_teacher_sentences(blocks)
    while blocks and blocks[-1]["type"] == "hr":  # trailing rule left by a strip
        blocks.pop()
    map_text(blocks, make_slot_sub(slot_dates))
    map_text(blocks, make_ref_sub(Path(md_path).parent))
    normalize_emdash(blocks)
    for b in blocks:
        if b["type"] == "meta":
            b["lines"] = rebuild_meta(b["lines"], slot_dates, is_handout)
    if doc_kind == "test":
        blocks = apply_test_layout(blocks)

    builder = DocBuilder()
    body = builder.render_blocks(blocks)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("docProps/core.xml", core_xml(title))
        z.writestr("docProps/app.xml", APP_XML)
        z.writestr("word/styles.xml", STYLES_XML.format(
            body=BODY_FONT, dark=TEXT_DARK, accent=ACCENT, grey=TEXT_GREY))
        z.writestr("word/footer1.xml", FOOTER_XML)
        z.writestr("word/_rels/document.xml.rels", document_rels(builder.rels))
        z.writestr("word/document.xml", document_xml(body))
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(args) != 2:
        print(__doc__)
        return 2
    kind = next((a.split("=", 1)[1] for a in flags if a.startswith("--kind=")), None)
    out = convert(args[0], args[1], doc_kind=kind,
                  strip_teacher_note="--strip-teacher-note" in flags)
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

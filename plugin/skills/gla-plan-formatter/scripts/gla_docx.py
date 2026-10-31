#!/usr/bin/env python3
"""
gla_docx: the shared print design system for every GLA document type.

Every colour, size, margin, and spacing value comes from assets/tokens.json
(override the file with GLA_TOKENS=/path/to/tokens.json). Nothing in the
doctypes/ builders declares a style value of its own; they compose the
furniture defined here. references/design_system.md explains the intent.
"""

import json
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# ----------------------------------------------------------------------------
# Locations and tokens
# ----------------------------------------------------------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOKENS = SKILL_ROOT / "assets" / "tokens.json"
LOGO = os.environ.get("GLA_LOGO", str(SKILL_ROOT / "assets" / "GLA_Logo.jpg"))


def load_tokens(path=None):
    p = Path(path) if path else Path(os.environ.get("GLA_TOKENS", DEFAULT_TOKENS))
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def skill_version():
    v = SKILL_ROOT / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.exists() else "dev"


TOKENS = load_tokens()
P, T, PG, SP, RL, STR = (TOKENS[k] for k in ("palette", "type", "page", "spacing", "rules", "strings"))

MAROON = P["maroon"]
GOLD = P["gold"]
GOLD_TEXT = P["gold_text"]
GOLD_TINT = P["gold_tint"]
BLUSH = P["blush"]
CREAM = P["cream"]
INK = P["ink"]
RULE = P["rule"]
FOOTER_GRAY = P["footer_gray"]
WHITE = P["white"]
MUTED = P["muted"]
MUTED_BOX = P["muted_box"]
BULLET_MARKER = P["bullet_marker"]

BODY_FONT = T["body_font"]
SYMBOL_FONT = T["symbol_font"]
BODY_PT = T["body_pt"]
SMALL_PT = T["small_pt"]
MICRO_PT = T["micro_pt"]

CONTENT_WIN = PG["width_in"] - PG["margin_left_in"] - PG["margin_right_in"]
TEXT_INSET = SP["cell_pad_h_dxa"] / 1440.0        # bar text, body, and cell text share one guide
LABEL_COL = SP["label_col_in"]
META_LABEL_COL = SP["meta_label_col_in"]
BULLET_HANG = SP["bullet_hang_in"]

SCHOOL = STR["school"]
SCHOOL_TITLE = STR["school_title"]


class SpecError(ValueError):
    """Raised for a malformed or incomplete content spec."""


def require(spec, *keys, where="spec"):
    for k in keys:
        if k not in spec or spec[k] in (None, ""):
            raise SpecError(f"{where}: missing required key '{k}'")


# ----------------------------------------------------------------------------
# Low-level XML helpers
# ----------------------------------------------------------------------------
def _set_shading(element_pr, fill_hex):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    element_pr.append(shd)


def _border_el(edge, sz, color, space="0"):
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))          # eighths of a point
    el.set(qn("w:space"), space)
    el.set(qn("w:color"), color)
    return el


def _para_border(paragraph, edge, sz, color, space="2"):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = pPr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        pPr.append(pbdr)
    pbdr.append(_border_el(edge, sz, color, space))


def _shade_paragraph(paragraph, fill_hex):
    _set_shading(paragraph._p.get_or_add_pPr(), fill_hex)


def _shade_cell(cell, fill_hex):
    _set_shading(cell._tc.get_or_add_tcPr(), fill_hex)


def _cell_borders(cell, color=None, sz=None):
    color = color or RULE
    sz = sz or RL["cell_border_sz"]
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        borders.append(_border_el(edge, sz, color))
    tcPr.append(borders)


def _cell_border(cell, edge, *, color=None, sz=4, nil=False):
    """Set or clear one border edge of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    ex = borders.find(qn(f"w:{edge}"))
    if ex is not None:
        borders.remove(ex)
    el = OxmlElement(f"w:{edge}")
    if nil:
        el.set(qn("w:val"), "nil")
    else:
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
    borders.append(el)


def _no_space(paragraph, before=0, after=0, line=None):
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = line


def _keep_with_next(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    if pPr.find(qn("w:keepNext")) is None:
        pPr.append(OxmlElement("w:keepNext"))


def _keep_lines(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    if pPr.find(qn("w:keepLines")) is None:
        pPr.append(OxmlElement("w:keepLines"))


def _page_break_before(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    if pPr.find(qn("w:pageBreakBefore")) is None:
        pPr.append(OxmlElement("w:pageBreakBefore"))


def _row_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:cantSplit")) is None:
        trPr.append(OxmlElement("w:cantSplit"))


def _repeat_header_row(row):
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:tblHeader")) is None:
        trPr.append(OxmlElement("w:tblHeader"))


def _set_row_height(row, inches, rule="atLeast"):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(inches * 1440)))
    h.set(qn("w:hRule"), rule)
    trPr.append(h)


def _run(paragraph, text, *, bold=False, italic=False, size=None, color=None, font=None):
    r = paragraph.add_run(text)
    r.bold = bold
    r.italic = italic
    r.font.size = Pt(size if size is not None else BODY_PT)
    r.font.name = font or BODY_FONT
    r.font.color.rgb = RGBColor.from_string(color or INK)
    return r


_INLINE_RX = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")


def _runs_from_inline(paragraph, text, *, base_bold=False, base_italic=False,
                      size=None, color=None):
    """Render inline **bold** and *italic* segments within a string."""
    for seg in _INLINE_RX.split(text or ""):
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**") and len(seg) > 4:
            _run(paragraph, seg[2:-2], bold=True, italic=base_italic, size=size, color=color)
        elif seg.startswith("*") and seg.endswith("*") and len(seg) > 2:
            _run(paragraph, seg[1:-1], bold=base_bold, italic=True, size=size, color=color)
        else:
            _run(paragraph, seg, bold=base_bold, italic=base_italic, size=size, color=color)


# ----------------------------------------------------------------------------
# Document scaffolding
# ----------------------------------------------------------------------------
def new_document(school_name=None):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(BODY_PT)
    normal.font.color.rgb = RGBColor.from_string(INK)
    pf = normal.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = T["line_body"]

    sec = doc.sections[0]
    sec.page_width = Inches(PG["width_in"])
    sec.page_height = Inches(PG["height_in"])
    sec.left_margin = Inches(PG["margin_left_in"])
    sec.right_margin = Inches(PG["margin_right_in"])
    sec.top_margin = Inches(PG["margin_top_in"])
    sec.bottom_margin = Inches(PG["margin_bottom_in"])
    sec.header_distance = Inches(PG["header_distance_in"])
    sec.footer_distance = Inches(PG["footer_distance_in"])
    _build_running_header(sec, school_name or SCHOOL)
    return doc


def _build_running_header(section, school_name):
    """Crest and school name in a two-cell table on a shared centre line, with a
    maroon rule beneath. Repeats on every page."""
    hdr = section.header
    hdr.is_linked_to_previous = False
    p0 = hdr.paragraphs[0]
    _no_space(p0, 0, 0, line=1.0)
    p0.add_run().font.size = Pt(1)

    logo_w = PG["logo_col_in"]
    widths = [logo_w, CONTENT_WIN - logo_w]
    t = hdr.add_table(rows=1, cols=2, width=Inches(CONTENT_WIN))
    t.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    t._tbl.tblPr.append(layout)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 1440)))
    _set_cell_margins(t, top=0, bottom=0, left=0, right=SP["cell_pad_h_dxa"])
    cells = t.rows[0].cells
    for i, c in enumerate(cells):
        c.width = Inches(widths[i])
        c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for e in ("top", "left", "right"):
            _cell_border(c, e, nil=True)
        _cell_border(c, "bottom", color=MAROON, sz=RL["header_sz"])
    lp = cells[0].paragraphs[0]
    _no_space(lp, 3, 3, line=1.0)
    if os.path.exists(LOGO):
        lp.add_run().add_picture(LOGO, height=Inches(PG["logo_height_in"]))
    else:
        print(f"WARNING: crest not found at {LOGO}; header built without it", file=sys.stderr)
    npp = cells[1].paragraphs[0]
    _no_space(npp, 3, 3, line=1.0)
    _run(npp, school_name, bold=True, size=T["header_name_pt"], color=MAROON)


def footer_text(*parts):
    """The house footer breadcrumb: parts joined by two spaces, a bar, two spaces."""
    return "  |  ".join(str(x) for x in parts if x)


def add_footer(doc, text):
    """Centred breadcrumb with a gold rule above it. Repeats on every page."""
    sec = doc.sections[0]
    ftr = sec.footer
    ftr.is_linked_to_previous = False
    p = ftr.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(p, 4, 0, line=1.0)
    p.paragraph_format.left_indent = Inches(0)
    p.paragraph_format.right_indent = Inches(0)
    _para_border(p, "top", RL["footer_sz"], GOLD, space="4")
    _run(p, text, size=MICRO_PT, color=FOOTER_GRAY)


def set_core_properties(doc, doc_type, title=None):
    """Record the generator and type invisibly (File > Properties), never on the page."""
    cp = doc.core_properties
    cp.comments = f"gla-plan-formatter {skill_version()}"
    cp.category = doc_type
    cp.author = SCHOOL_TITLE
    if title:
        cp.title = title


def finish(doc, spec, doc_type, out_path, default_footer=None):
    add_footer(doc, spec.get("footer") or default_footer or SCHOOL_TITLE)
    set_core_properties(doc, doc_type, spec.get("title") or spec.get("subtitle"))
    doc.save(out_path)
    return out_path


def spacer(doc, pts=8):
    p = doc.add_paragraph()
    _no_space(p, 0, 0, line=1.0)
    p.add_run().font.size = Pt(pts / 2.0)
    return p


def add_title_block(doc, title, subtitle=None):
    """Big centred document title with a gold rule and an optional subtitle."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(p, 6, 0, line=1.0)
    _keep_with_next(p)
    _run(p, title, bold=True, size=T["title_pt"], color=MAROON)
    _para_border(p, "bottom", RL["title_sz"], GOLD, space="6")
    if subtitle:
        s = doc.add_paragraph()
        s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _no_space(s, 8, 4, line=1.05)
        _keep_with_next(s)
        _run(s, subtitle, bold=True, size=T["subtitle_pt"], color=MAROON)


def centred_lines(doc, lines):
    """Stacked centred lines (school, semester, course, plan name, teacher).
    lines: list of (text, size, bold, color)."""
    last = None
    for text, size, bold, color in lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _no_space(p, 2, 2, line=1.05)
        _keep_with_next(p)
        _run(p, text, bold=bold, size=size, color=color)
        last = p
    return last


# ----------------------------------------------------------------------------
# Bars and headings
# ----------------------------------------------------------------------------
def section_bar(doc, text, fill=None, gold_rule=True):
    """Solid maroon bar, white bold uppercase text, gold underline. A shaded
    paragraph (not a table) so keepNext binds it to what follows."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(SP["section_before_pt"])
    pf.space_after = Pt(SP["section_after_pt"])
    pf.line_spacing = Pt(T["section_bar_atleast_pt"])
    pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    pf.left_indent = Inches(0)
    pf.right_indent = Inches(0)
    pf.first_line_indent = Inches(TEXT_INSET)
    _shade_paragraph(p, fill or MAROON)
    if gold_rule:
        _para_border(p, "bottom", RL["section_sz"], GOLD, space="2")
    _keep_with_next(p)
    _keep_lines(p)
    _run(p, text.upper(), bold=True, size=T["section_pt"], color=WHITE)
    return p


def sub_bar(doc, text):
    """Blush sub-bar with maroon bold text and a hairline maroon rule."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(SP["sub_before_pt"])
    pf.space_after = Pt(SP["sub_after_pt"])
    pf.line_spacing = Pt(T["sub_bar_atleast_pt"])
    pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    pf.left_indent = Inches(0)
    pf.right_indent = Inches(0)
    pf.first_line_indent = Inches(TEXT_INSET)
    _shade_paragraph(p, BLUSH)
    _para_border(p, "bottom", RL["sub_sz"], MAROON, space="1")
    _keep_with_next(p)
    _keep_lines(p)
    _run(p, text, bold=True, size=T["sub_pt"], color=MAROON)
    return p


def phase_text(num=None, phase=None, time=None, subtitle=None, text=None):
    """Numbered phase or day heading, e.g. '1.  MINDS ON  (10 minutes): Hook'."""
    if text is not None:
        return text
    bits = ""
    if phase:
        bits = f"{num}.  {phase}" if num not in (None, "") else phase
    if time:
        bits += f"  ({time})"
    if subtitle:
        bits += f": {subtitle}"
    return bits.strip()


def phase_bar(doc, num=None, phase=None, time=None, subtitle=None, text=None):
    return sub_bar(doc, phase_text(num, phase, time, subtitle, text))


def step_banner(doc, text):
    """Centred maroon banner with a gold rule (unit-plan STEP headings)."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(SP["section_before_pt"])
    pf.space_after = Pt(SP["section_after_pt"])
    pf.line_spacing = Pt(T["section_bar_atleast_pt"])
    pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _shade_paragraph(p, MAROON)
    _para_border(p, "bottom", RL["section_sz"], GOLD, space="2")
    _keep_with_next(p)
    _keep_lines(p)
    _run(p, text.upper(), bold=True, size=T["section_pt"], color=WHITE)
    return p


def plain_heading(doc, text):
    """Maroon uppercase heading with a thin gold underline (no fill)."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(SP["section_before_pt"])
    pf.space_after = Pt(SP["section_after_pt"])
    pf.line_spacing = 1.1
    pf.first_line_indent = Inches(TEXT_INSET)
    _keep_with_next(p)
    _keep_lines(p)
    _run(p, text.upper(), bold=True, size=T["heading_pt"], color=MAROON)
    _para_border(p, "bottom", RL["heading_sz"], GOLD, space="2")
    return p


# ----------------------------------------------------------------------------
# Body text (document level)
# ----------------------------------------------------------------------------
def body_para(doc, text, *, italic=False, bold=False, color=None, keep_next=False, align=None):
    p = doc.add_paragraph()
    _no_space(p, SP["para_before_pt"], SP["para_after_pt"], line=1.16)
    p.paragraph_format.left_indent = Inches(TEXT_INSET)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _keep_lines(p)
    if keep_next or (text or "").rstrip().endswith(":"):
        _keep_with_next(p)
    if italic and not color:
        color = MAROON
    _runs_from_inline(p, text, base_bold=bold, base_italic=italic, color=color)
    return p


def _bullet_paragraph(p, text, *, base=0.0, marker="•", bold=False, size=None,
                      color=None, line=1.1):
    """A true hanging indent: wrapped lines align with the text after the marker."""
    _no_space(p, 1, 2, line=line)
    pf = p.paragraph_format
    pf.left_indent = Inches(base + BULLET_HANG)
    pf.first_line_indent = Inches(-BULLET_HANG)
    pf.tab_stops.add_tab_stop(Inches(base + BULLET_HANG))
    _run(p, f"{marker}\t", bold=bold, size=size, color=BULLET_MARKER)
    _runs_from_inline(p, text, base_bold=bold, size=size, color=color)
    return p


def bullet(doc, text, numbered=None, bold=False):
    p = doc.add_paragraph()
    marker = f"{numbered}." if numbered is not None else "•"
    return _bullet_paragraph(p, text, base=TEXT_INSET, marker=marker, bold=bold, line=1.14)


# ----------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------
def _set_table_width(table, width_in):
    tblPr = table._tbl.tblPr
    for e in tblPr.findall(qn("w:tblW")):
        tblPr.remove(e)
    if abs(width_in - CONTENT_WIN) < 0.01:
        w = OxmlElement("w:tblW")
        w.set(qn("w:type"), "pct")
        w.set(qn("w:w"), "5000")
    else:
        w = OxmlElement("w:tblW")
        w.set(qn("w:w"), str(int(width_in * 1440)))
        w.set(qn("w:type"), "dxa")
    tblPr.append(w)


def _set_cell_margins(table, top, bottom, left, right):
    mar = OxmlElement("w:tblCellMar")
    for edge, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    table._tbl.tblPr.append(mar)


def gap(doc, pts):
    """An empty paragraph of exactly pts height (spacing that carries no keep flags)."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = Pt(pts)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.add_run().font.size = Pt(1)
    return p


def _separate_tables(doc):
    """Word and LibreOffice fuse two tables that touch, so a repeating header
    row from one would reappear over the other. A 1pt paragraph keeps them apart."""
    body = doc.element.body
    children = [c for c in body if not c.tag.endswith("}sectPr")]
    if children and children[-1].tag.endswith("}tbl"):
        gap(doc, 1)


def _bar_row(table, text, kind):
    """A section or sub bar fused into a table as its first row. The row repeats
    when the table continues on a later page and never separates from the row
    below it, which a keepNext paragraph cannot guarantee in LibreOffice when
    the row that follows is taller than the space left on the page."""
    row = table.add_row()
    cells = row.cells
    cell = cells[0].merge(cells[-1]) if len(cells) > 1 else cells[0]
    cell.width = Inches(sum(table._gla_widths))
    _row_cant_split(row)
    _repeat_header_row(row)
    section = kind == "section"
    _shade_cell(cell, MAROON if section else BLUSH)
    for e in ("top", "left", "right"):
        _cell_border(cell, e, nil=True)
    if section:
        _cell_border(cell, "bottom", color=GOLD, sz=RL["section_sz"])
    else:
        _cell_border(cell, "bottom", color=MAROON, sz=RL["sub_sz"])
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    _no_space(p, 2, 2, line=1.05)
    _keep_with_next(p)
    if section:
        _run(p, text.upper(), bold=True, size=T["section_pt"], color=WHITE)
    else:
        _run(p, text, bold=True, size=T["sub_pt"], color=MAROON)
    return row


def make_table(doc, col_widths, *, vpad=None, container=None, bar=None, bar_kind="section"):
    """Fixed-layout table whose columns are exactly col_widths (inches).
    bar= fuses a section (or sub) bar into the table as its first row; use it
    for a bar that introduces a single tall row of content."""
    host = container or doc
    if bar and container is None:
        gap(doc, SP["section_before_pt"] if bar_kind == "section" else SP["sub_before_pt"])
    elif container is None:
        _separate_tables(doc)
    table = host.add_table(rows=0, cols=len(col_widths))
    table.autofit = False
    table.allow_autofit = False
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    ind = OxmlElement("w:tblInd")
    ind.set(qn("w:w"), str(SP["table_indent_dxa"]))
    ind.set(qn("w:type"), "dxa")
    tblPr.append(ind)
    _set_table_width(table, sum(col_widths))
    v = SP["cell_pad_v_dxa"] if vpad is None else vpad
    _set_cell_margins(table, top=v, bottom=v, left=SP["cell_pad_h_dxa"], right=SP["cell_pad_h_dxa"])
    grid = table._tbl.tblGrid
    for gc, win in zip(grid.findall(qn("w:gridCol")), col_widths):
        gc.set(qn("w:w"), str(int(win * 1440)))
    table._gla_widths = col_widths
    if bar:
        _bar_row(table, bar, bar_kind)
    return table


def add_row(table, *, cant_split=False, header=False, borders=True):
    row = table.add_row()
    for i, c in enumerate(row.cells):
        c.width = Inches(table._gla_widths[i])
        if borders:
            _cell_borders(c)
        else:
            for e in ("top", "left", "right", "bottom"):
                _cell_border(c, e, nil=True)
        c.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    if cant_split or header:
        _row_cant_split(row)
    if header:
        _repeat_header_row(row)
        # A header row is a full blush row, like a sub bar, and carries the same
        # maroon rule beneath it in every table of every type.
        for c in row.cells:
            _cell_border(c, "bottom", color=MAROON, sz=RL["sub_sz"])
    return row


def _cell_valign(cell, val="top"):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP if val == "top" else WD_ALIGN_VERTICAL.CENTER


def header_cell(cell, text, fill=None, color=None, size=None, align="left"):
    """A table header cell: blush fill, maroon bold text. Maroon fills belong to
    section bars only, so a table never stacks a second maroon band under one."""
    _shade_cell(cell, fill or BLUSH)
    p = cell.paragraphs[0]
    _no_space(p, 2, 2, line=1.05)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=True, size=size if size is not None else BODY_PT, color=color or MAROON)


def _fill_cell(cell, text, *, bold=False, italic=False, center=False, color=None,
               fill=None, size=None):
    if fill:
        _shade_cell(cell, fill)
    p = cell.paragraphs[0]
    _no_space(p, 2, 2, line=1.08)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _runs_from_inline(p, text, base_bold=bold, base_italic=italic, color=color, size=size)


def _label_cell(cell, text, size=None, fill=None, color=None):
    _shade_cell(cell, fill or BLUSH)
    p = cell.paragraphs[0]
    _no_space(p, 2, 2, line=1.05)
    _run(p, text, bold=True, size=size, color=color or MAROON)


# ----------------------------------------------------------------------------
# Block rendering inside a cell
# ----------------------------------------------------------------------------
def _first_or_new(cell, used):
    if not used[0] and len(cell.paragraphs) == 1 and not cell.paragraphs[0].runs:
        used[0] = True
        return cell.paragraphs[0]
    return cell.add_paragraph()


def _add_bullet(cell, used, text, bold=False, size=None, numbered=None):
    p = _first_or_new(cell, used)
    marker = f"{numbered}." if numbered is not None else "•"
    _bullet_paragraph(p, text, base=0.0, marker=marker, bold=bold, size=size, line=1.06)


def _checkbox_paragraph(p, txt, checked, size=None):
    _no_space(p, 1, 1, line=1.1)
    p.paragraph_format.left_indent = Inches(0.24)
    p.paragraph_format.first_line_indent = Inches(-0.24)
    box = "☑" if checked else "☐"
    _run(p, box + "  ", size=12, color=MAROON if checked else MUTED_BOX, font=SYMBOL_FONT)
    _runs_from_inline(p, txt, size=size, color=INK)


def render_blocks(cell, blocks, used=None):
    """Render content blocks into a table cell. See references/blocks.md."""
    if used is None:
        used = [False]
    for b in blocks or []:
        if isinstance(b, str):
            b = {"type": "para", "text": b}
        t = b.get("type", "para")
        if t == "para":
            p = _first_or_new(cell, used)
            _no_space(p, 2, 2, line=1.08)
            _runs_from_inline(p, b.get("text", ""), base_bold=b.get("bold", False),
                              base_italic=b.get("italic", False),
                              size=b.get("size"), color=b.get("color"))
        elif t == "label":
            p = _first_or_new(cell, used)
            _no_space(p, 5, 1, line=1.05)
            _keep_with_next(p)
            _run(p, b["text"], bold=True, size=b.get("size"), color=MAROON)
        elif t == "quote":
            p = _first_or_new(cell, used)
            _no_space(p, 2, 2, line=1.08)
            _runs_from_inline(p, b["text"], base_italic=True, size=b.get("size"), color=MAROON)
        elif t == "bullets":
            for it in b.get("items", []):
                _add_bullet(cell, used, it, bold=b.get("bold", False), size=b.get("size"))
        elif t == "numbered":
            start = b.get("start", 1)
            for i, it in enumerate(b.get("items", [])):
                _add_bullet(cell, used, it, bold=b.get("bold", False), size=b.get("size"),
                            numbered=start + i)
        elif t == "checks":
            for item in b.get("items", []):
                txt, checked = (item if isinstance(item, (list, tuple)) else (item, True))
                p = _first_or_new(cell, used)
                _checkbox_paragraph(p, txt, bool(checked), size=b.get("size"))
        elif t == "rule":
            p = _first_or_new(cell, used)
            _no_space(p, 14, 2, line=1.0)
            _para_border(p, "bottom", RL["signature_sz"], INK, space="1")
        else:
            raise SpecError(f"unknown block type '{t}'")
    return used


# ----------------------------------------------------------------------------
# Shared higher-level components
# ----------------------------------------------------------------------------
def context_banner(doc, left_lines, badge_text):
    """Maroon context block with a gold badge box on the right."""
    lw = CONTENT_WIN * 0.72
    rw = CONTENT_WIN - lw
    t = make_table(doc, [lw, rw])
    row = add_row(t, cant_split=True)
    left, right = row.cells
    _shade_cell(left, MAROON)
    _cell_valign(left, "center")
    used = [False]
    for i, line in enumerate(left_lines):
        if not line:
            continue
        p = _first_or_new(left, used)
        _no_space(p, 1, 1, line=1.05)
        _run(p, line, bold=(i == 0), size=T["section_pt"] if i == 0 else SMALL_PT,
             color=WHITE if i == 0 else GOLD)
    _shade_cell(right, GOLD)
    _cell_valign(right, "center")
    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(rp, 1, 1, line=1.05)
    _run(rp, badge_text or "", bold=True, size=T["badge_pt"], color=MAROON)


PATHWAYS = {"D": "Academic", "P": "Applied", "U": "University Prep", "C": "College Prep",
            "M": "University/College Prep", "O": "Open", "W": "De-streamed",
            "E": "Workplace Prep", "L": "Locally Developed"}
GRADES = {"1": "9", "2": "10", "3": "11", "4": "12"}


def derive_badge(code=None, grade=None, pathway=None):
    """'Grade 12 | University Prep' from an Ontario course code, or from the
    parts a spec supplies. Returns '' when nothing can be derived."""
    code = (code or "").strip().upper()
    if not grade and len(code) >= 4:
        grade = GRADES.get(code[3])
    if not pathway and len(code) >= 5:
        pathway = PATHWAYS.get(code[4])
    grade = str(grade or "").replace("Grade", "").strip()
    bits = [f"Grade {grade}" if grade else "", pathway or ""]
    return "  |  ".join(b for b in bits if b)


_PATHWAY_WORDS = [
    ("university/college", "University/College Prep"), ("university / college", "University/College Prep"),
    ("university", "University Prep"), ("college", "College Prep"), ("workplace", "Workplace Prep"),
    ("academic", "Academic"), ("applied", "Applied"), ("open", "Open"), ("de-streamed", "De-streamed"),
    ("destreamed", "De-streamed"), ("locally developed", "Locally Developed"),
]


def normalize_badge(text, code=None):
    """Rewrite a supplied badge ('Grade 11 | University Preparation') in the
    house form ('Grade 11  |  University Prep'). Unrecognised text is kept."""
    if not text:
        return derive_badge(code)
    low = str(text).lower()
    m = re.search(r"grade\s*(\d{1,2})", low) or re.search(r"\b(9|10|11|12)\b", low)
    grade = m.group(1) if m else None
    pathway = None
    for key, canon in _PATHWAY_WORDS:
        if key in low:
            pathway = canon
            break
    if grade or pathway:
        return derive_badge(code, grade=grade, pathway=pathway)
    return str(text)


def course_line(code=None, title=None, grade=None):
    """'SBI4U: Biology, Grade 12' from the parts available."""
    bits = []
    if title:
        bits.append(title)
    grade = str(grade or "").replace("Grade", "").strip()
    if grade and grade not in (title or ""):
        bits.append(f"Grade {grade}")
    line = ", ".join(bits)
    if code:
        line = f"{code}: {line}" if line else code
    return line or ""


def masthead(doc, *, title, subtitle=None, course_line_text=None, context_line=None, badge=None,
             code=None):
    """The shared opening of every document: the maroon course strip with
    the gold grade badge, then the document title block. Builders pass their
    lines; a missing badge is derived from the course code."""
    badge = normalize_badge(badge, code) if badge else derive_badge(code)
    context_banner(doc, [course_line_text or "", context_line or ""], badge or "")
    add_title_block(doc, title, subtitle)


def checkbox_line(cell, categories):
    """categories: list of (name, checked). One wrapped line of boxes."""
    p = cell.paragraphs[0]
    _no_space(p, 1, 1, line=1.15)
    for name, checked in categories:
        box = "☑" if checked else "☐"
        _run(p, box + "\u00a0", size=12, color=MAROON if checked else MUTED_BOX, font=SYMBOL_FONT)
        _run(p, name + "      ", bold=bool(checked), size=BODY_PT,
             color=INK if checked else MUTED)


def kv_row(table, label, value, cant_split=False):
    """Blush label cell on the left, value (string or blocks) on the right."""
    row = add_row(table, cant_split=cant_split)
    lab, val = row.cells
    _label_cell(lab, label)
    if isinstance(value, list):
        render_blocks(val, value)
    else:
        vp = val.paragraphs[0]
        _no_space(vp, 2, 2, line=1.08)
        _runs_from_inline(vp, value or "")
    return row


def labeled_row(doc, label, blocks, label_fill=None, label_color=None, cant_split=False):
    """Tall maroon left-label cell with block content on the right."""
    t = make_table(doc, [LABEL_COL, CONTENT_WIN - LABEL_COL])
    row = add_row(t, cant_split=cant_split)
    lab, content = row.cells
    _shade_cell(lab, label_fill or MAROON)
    lp = lab.paragraphs[0]
    _no_space(lp, 2, 2, line=1.12)
    _run(lp, label, bold=True, color=label_color or WHITE)
    render_blocks(content, blocks)
    return t


def _grid_label(cell, text, size=None):
    _label_cell(cell, text if text.endswith(":") else text + ":", size=size)


def _grid_value(cell, value, bold=False, size=None):
    p = cell.paragraphs[0]
    _no_space(p, 2, 2, line=1.08)
    _runs_from_inline(p, value or "", base_bold=bold, size=size)


def overview_grid(doc, ov, pairs, full_keys=(), label_w=None, value_bold=()):
    """Two label/value pairs per row; keys in full_keys span the row."""
    labw = label_w or LABEL_COL
    valw = CONTENT_WIN / 2.0 - labw
    t = make_table(doc, [labw, valw, labw, valw])
    for l1, l2 in pairs:
        if l1 not in ov and (l2 is None or l2 not in ov):
            continue
        row = add_row(t, cant_split=True)
        _grid_label(row.cells[0], l1)
        if l2 is None or l1 in full_keys:
            merged = row.cells[1].merge(row.cells[3])
            _grid_value(merged, ov.get(l1), bold=(l1 in value_bold))
        else:
            _grid_value(row.cells[1], ov.get(l1), bold=(l1 in value_bold))
            _grid_label(row.cells[2], l2)
            _grid_value(row.cells[3], ov.get(l2), bold=(l2 in value_bold))
    for key in full_keys:
        if key in ov and not any(key in pr for pr in pairs):
            row = add_row(t, cant_split=True)
            _grid_label(row.cells[0], key)
            merged = row.cells[1].merge(row.cells[3])
            _grid_value(merged, ov.get(key))
    return t


def metadata_grid(doc, data, layout, full_keys=(), label_w=None):
    """Compact metadata block: label cells at 9.5pt on blush, values beside them.
    layout: list of (left_key, right_key_or_None). Unknown keys in data are
    appended as full-width rows so nothing supplied is dropped."""
    labw = label_w or META_LABEL_COL
    valw = (CONTENT_WIN - 2 * labw) / 2.0
    t = make_table(doc, [labw, valw, labw, valw], vpad=SP["grid_pad_v_dxa"])

    def label(cell, text):
        _shade_cell(cell, BLUSH)
        p = cell.paragraphs[0]
        _no_space(p, 1, 1, line=1.05)
        _run(p, text, bold=True, size=SMALL_PT, color=MAROON)

    def value(cell, text):
        p = cell.paragraphs[0]
        _no_space(p, 1, 1, line=1.08)
        _runs_from_inline(p, text or "")

    rows = [pair for pair in layout if pair[0] in data or (pair[1] and pair[1] in data)]
    known = {k for pair in layout for k in pair if k}
    for key in data:
        if key not in known:
            rows.append((key, None))
    for left, right in rows:
        r = add_row(t, cant_split=True)
        label(r.cells[0], left)
        if right is None or left in full_keys or not data.get(right):
            merged = r.cells[1].merge(r.cells[2]).merge(r.cells[3])
            value(merged, data.get(left, ""))
        else:
            value(r.cells[1], data.get(left, ""))
            label(r.cells[2], right)
            value(r.cells[3], data.get(right, ""))
    return t


def _col_widths(rows, total=None, minw=0.7):
    """Every column gets at least its longest word; the rest is shared by content length."""
    total = total or CONTENT_WIN
    ncol = max(len(r) for r in rows)
    CPI = 0.088          # inches per character at Arial 10.5, with slack
    maxlen = [0] * ncol
    maxword = [0] * ncol
    for r in rows:
        for i in range(ncol):
            cell = re.sub(r"\*\*", "", str(r[i])) if i < len(r) else ""
            maxlen[i] = max(maxlen[i], len(cell))
            for w in cell.split():
                maxword[i] = max(maxword[i], len(w))
    floor = [max(minw, maxword[i] * CPI + 0.22) for i in range(ncol)]
    if sum(floor) > total:
        k = total / sum(floor)
        return [w * k for w in floor]
    rem = total - sum(floor)
    lsum = sum(maxlen) or 1
    widths = [floor[i] + rem * (maxlen[i] / lsum) for i in range(ncol)]
    s = sum(widths)
    return [w / s * total for w in widths]


_LABEL_HEADERS = ("category", "level", "component", "criteria")


def render_table(doc, header, rows, *, widths=None, label_first=None, centre_short=True,
                 total_rows=True, size=None, cant_split=True):
    """Generic maroon-header table. Alignment is decided per column: a non-first
    column is centred only when every body cell is short. A row whose first cell
    starts with 'Total' is bold on blush."""
    all_rows = ([header] if header else []) + list(rows)
    if not all_rows:
        return None
    ncol = max(len(r) for r in all_rows)
    all_rows = [list(r) + [""] * (ncol - len(r)) for r in all_rows]
    rows = all_rows[1:] if header else all_rows
    widths = widths or _col_widths(all_rows)
    t = make_table(doc, widths)

    def _clean(s):
        return re.sub(r"\*\*", "", str(s or ""))

    center_col = [False] * ncol
    if centre_short:
        for i in range(1, ncol):
            maxlen = max((len(_clean(r[i])) for r in rows), default=0)
            center_col[i] = maxlen <= 14
    if label_first is None:
        label_first = bool(header) and _clean(header[0]).strip().lower() in _LABEL_HEADERS

    if header:
        r = add_row(t, header=True)
        for i, cell_text in enumerate(header):
            header_cell(r.cells[i], _clean(cell_text), size=size,
                        align="center" if (i > 0 and center_col[i]) else "left")
    for body_row in rows:
        r = add_row(t, cant_split=cant_split)
        is_total = total_rows and _clean(body_row[0]).strip().lower().startswith("total")
        for i, cell_text in enumerate(body_row):
            fill = BLUSH if (is_total or (i == 0 and label_first)) else None
            _fill_cell(r.cells[i], cell_text, bold=is_total, color=INK,
                       center=(i > 0 and center_col[i]), fill=fill, size=size)
    return t


def signature_block(doc, signatories, captions=("Signature", "Date"), widths=None, bar=None):
    """Aligned name / signature / date fill-in lines, one row per signatory."""
    if not bar:
        _keep_with_next(spacer(doc, 6))
    widths = widths or [3.0, 2.3, CONTENT_WIN - 3.0 - 2.3]
    t = make_table(doc, widths, vpad=0, bar=bar)
    for ridx, name in enumerate(signatories):
        row = add_row(t, cant_split=True, borders=False)
        _set_row_height(row, SP["signature_row_in"])
        for i, cap in enumerate((name,) + tuple(captions)):
            c = row.cells[i]
            line_p = c.paragraphs[0]
            _no_space(line_p, 22, 0, line=1.0)
            _para_border(line_p, "bottom", RL["signature_sz"], INK, space="1")
            cap_p = c.add_paragraph()
            _no_space(cap_p, 2, 6, line=1.0)
            _run(cap_p, cap, size=MICRO_PT, color=FOOTER_GRAY)
            if ridx < len(signatories) - 1:
                _keep_with_next(line_p)
                _keep_with_next(cap_p)
    return t


def signature_pairs(doc, rows, bar=None):
    """Signature fields two per row: a rule with the caption beneath, the same
    furniture as signature_block, so every document's signatures look alike."""
    if not bar:
        _keep_with_next(spacer(doc, 6))
    gutter = 0.5
    half = (CONTENT_WIN - gutter) / 2.0
    t = make_table(doc, [half, gutter, half], vpad=0, bar=bar)
    for ridx, pair in enumerate(rows):
        row = add_row(t, cant_split=True, borders=False)
        _set_row_height(row, SP["signature_row_in"])
        for c, label in zip((row.cells[0], row.cells[2]), pair):
            line_p = c.paragraphs[0]
            _no_space(line_p, 22, 0, line=1.0)
            _para_border(line_p, "bottom", RL["signature_sz"], INK, space="1")
            cap_p = c.add_paragraph()
            _no_space(cap_p, 2, 6, line=1.0)
            _run(cap_p, label, size=MICRO_PT, color=FOOTER_GRAY)
            if ridx < len(rows) - 1:
                _keep_with_next(line_p)
                _keep_with_next(cap_p)
    return t


def fill_line(label, width=28):
    return f"{label} " + "_" * width

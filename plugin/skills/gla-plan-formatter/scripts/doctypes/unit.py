"""Unit plan (backward design). Schema: references/unit_schema.md.

Rendered in the same vocabulary as every other type: STEP banners are section
bars fused to the table beneath them, the backward-design blocks (A. Big Idea,
B. Overall Expectations, ...) are blush label rows of one table per step, the
sub-headings are sub bars, and every table header is a blush header row.
"""

from docx.enum.text import WD_ALIGN_PARAGRAPH

from gla_docx import (
    CONTENT_WIN, GOLD_TEXT, GOLD_TINT, LABEL_COL, MAROON, SMALL_PT, STR, SCHOOL_TITLE,
    _label_cell, _no_space, _run, _runs_from_inline, _shade_cell, add_row,
    body_para, derive_badge, finish, header_cell, make_table, masthead, new_document,
    overview_grid, render_blocks,
    require, section_bar, sub_bar,
)

OVERVIEW_PAIRS = [("Course", "Grade"), ("Unit Title", "Unit #"),
                  ("Number of Days", "Culminating Task Due")]
OVERVIEW_FULL = ("Core Texts", "Strands Addressed")
TABLE_KINDS = {"expectations", "achievement", "lesson_table", "reflection"}


def expectations_table(doc, rows, bar=None):
    c1 = LABEL_COL
    rest = (CONTENT_WIN - c1) / 2.0
    t = make_table(doc, [c1, rest, rest], bar=bar)
    hr = add_row(t, header=True)
    header_cell(hr.cells[0], "Specific Expectations")
    header_cell(hr.cells[1], "Assessed (Formally Evaluated)")
    _shade_cell(hr.cells[2], GOLD_TINT)
    hp = hr.cells[2].paragraphs[0]
    _no_space(hp, 2, 2, line=1.05)
    _run(hp, "Covered (Taught but Not Formally Assessed)", bold=True, color=GOLD_TEXT)
    for r in rows or []:
        dr = add_row(t)
        _label_cell(dr.cells[0], r.get("strand", ""))
        render_blocks(dr.cells[1], [{"type": "bullets", "items": r.get("assessed", [])}])
        render_blocks(dr.cells[2], [{"type": "bullets", "items": r.get("covered", [])}])
    return t


def achievement_table(doc, cats, bar=None):
    cats = cats or []
    w = CONTENT_WIN / max(len(cats), 1)
    t = make_table(doc, [w] * max(len(cats), 1), bar=bar)
    hr = add_row(t, header=True)
    for c, cat in zip(hr.cells, cats):
        header_cell(c, cat.get("name", ""))
    dr = add_row(t)
    for c, cat in zip(dr.cells, cats):
        p = c.paragraphs[0]
        _no_space(p, 2, 2, line=1.08)
        _runs_from_inline(p, cat.get("desc", ""), size=SMALL_PT)
    return t


def lesson_seq_table(doc, rows, bar=None):
    cols = [0.55, 1.25, 1.50, 1.35, 1.15, 1.10]      # sums to CONTENT_WIN (6.9")
    t = make_table(doc, cols, bar=bar)
    hr = add_row(t, header=True)
    for c, label in zip(hr.cells, ["#", "Lesson Topic / Activity", "What the Teacher Will Do",
                                   "What the Student Will Do", "Assessment (Say / Write / Do)",
                                   "Specific Expectations & Resources"]):
        header_cell(c, label, size=SMALL_PT)
    for r in rows or []:
        dr = add_row(t, cant_split=True)
        np_ = dr.cells[0].paragraphs[0]
        _no_space(np_, 2, 2, line=1.05)
        np_.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(np_, str(r.get("num", "")), bold=True, size=SMALL_PT, color=MAROON)
        for cell, key in ((dr.cells[1], "topic"), (dr.cells[2], "teacher"),
                          (dr.cells[3], "student"), (dr.cells[4], "assessment"),
                          (dr.cells[5], "expectations")):
            p = cell.paragraphs[0]
            _no_space(p, 2, 2, line=1.06)
            if key == "topic" and r.get("date"):
                # the lesson's date sits on its own first line in the topic cell
                _run(p, str(r["date"]), bold=True, size=SMALL_PT, color=MAROON)
                p.add_run().add_break()
            _runs_from_inline(p, r.get(key, ""), size=SMALL_PT)
    return t


def reflection_table(doc, rows, bar=None):
    c1 = LABEL_COL
    rest = (CONTENT_WIN - c1) / 2.0
    t = make_table(doc, [c1, rest, rest], bar=bar)
    hr = add_row(t, header=True)
    for c, label in zip(hr.cells, ["Criteria", "Exemplars (Pre-Unit Intentions)",
                                   "Evidence (Post-Unit Reflection)"]):
        header_cell(c, label)
    for r in rows or []:
        dr = add_row(t, cant_split=True)
        _label_cell(dr.cells[0], r.get("criteria", ""))
        for cell, key in ((dr.cells[1], "exemplar"), (dr.cells[2], "evidence")):
            p = cell.paragraphs[0]
            _no_space(p, 2, 2, line=1.08)
            val = r.get(key)
            _runs_from_inline(p, val or STR["reflection_placeholder"], base_italic=not val)
    return t


def variety_blocks(sec):
    blocks = []
    groups = list(sec.get("groups") or [])
    if groups and isinstance(groups[0], dict) and groups[0].get("intro"):
        blocks.append({"type": "para", "text": groups[0]["intro"], "italic": True})
        groups = groups[1:]
    for g in groups:
        blocks.append({"type": "label", "text": g.get("label", "")})
        blocks.append({"type": "checks", "items": g.get("items", [])})
    return blocks


class _LabelTable:
    """Consecutive labeled sections share one two-column table so their borders
    align and no gap opens between them."""

    def __init__(self, doc, bar=None):
        self.t = make_table(doc, [LABEL_COL, CONTENT_WIN - LABEL_COL], bar=bar)

    def add(self, label, blocks):
        row = add_row(self.t)
        _label_cell(row.cells[0], label)
        render_blocks(row.cells[1], blocks)


def render_sections(doc, sections):
    pending = None      # a section bar waiting to fuse with the next table
    table = None        # the open label table, if any

    def take_bar():
        nonlocal pending
        b, pending = pending, None
        return b

    def close():
        nonlocal table
        table = None

    for sec in sections or []:
        kind = sec.get("kind")
        if kind == "step":
            close()
            if pending:
                section_bar(doc, pending)
            pending = sec["text"]
        elif kind == "heading":
            close()
            if pending:
                section_bar(doc, take_bar())
            sub_bar(doc, sec["text"])
        elif kind == "para":
            close()
            if pending:
                section_bar(doc, take_bar())
            body_para(doc, sec["text"], italic=sec.get("italic", False), bold=sec.get("bold", False))
        elif kind in ("labeled", "variety"):
            if table is None:
                table = _LabelTable(doc, bar=take_bar())
            if kind == "labeled":
                table.add(sec["label"], sec.get("blocks", []))
            else:
                table.add(sec.get("label", "Variety of Learning Experiences"), variety_blocks(sec))
        elif kind == "expectations":
            close()
            expectations_table(doc, sec.get("rows", []), bar=take_bar())
        elif kind == "achievement":
            close()
            achievement_table(doc, sec.get("categories", []), bar=take_bar())
        elif kind == "lesson_table":
            close()
            lesson_seq_table(doc, sec.get("rows", []), bar=take_bar())
        elif kind == "reflection":
            close()
            reflection_table(doc, sec.get("rows", []), bar=take_bar())
        else:
            raise ValueError(f"unit: unknown section kind '{kind}'")
    if pending:
        section_bar(doc, pending)


def build(spec, out_path):
    require(spec, "overview", "sections", where="unit")
    doc = new_document(spec.get("school"))
    ov = spec.get("overview", {}) or {}
    rh = spec.get("context", {}) or {}
    code = (ov.get("Course") or "").split(" ")[0].strip(":,")
    unit_bits = [x for x in (ov.get("Unit Title"), ov.get("Unit #")) if x]
    masthead(doc, title="UNIT PLAN",
             subtitle=spec.get("subtitle", "Backward Design Cross-Curricular Planning Model"),
             course_line_text=rh.get("course_line") or ov.get("Course"),
             context_line=rh.get("context_line") or "  |  ".join(unit_bits),
             badge=spec.get("badge") or derive_badge(code, grade=ov.get("Grade")), code=code)
    overview_grid(doc, spec.get("overview", {}), OVERVIEW_PAIRS, full_keys=OVERVIEW_FULL,
                  value_bold=("Unit Title",))
    render_sections(doc, spec.get("sections", []))
    return finish(doc, spec, "unit", out_path, default_footer=SCHOOL_TITLE)

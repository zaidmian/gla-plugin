"""Weekly lesson plan (one week, DAY 1 to DAY 5). Schema: references/weekly_plan_schema.md.

The v1 lesson furniture carries the official HS Lesson Plan Template's fields as
first-class sections (see references/SAMPLE_DELTAS.md section 2).
"""

from gla_docx import (
    CONTENT_WIN, INK, MAROON, SCHOOL_TITLE,
    _bar_row, _label_cell, _no_space, _run, add_row, checkbox_line,
    finish, header_cell, kv_row, make_table, masthead, new_document,
    phase_text, render_blocks, require,
)
from doctypes import lesson as L

LEARNING_SKILLS = ["Responsibility", "Organization", "Independent Work",
                   "Collaboration", "Initiative", "Self-Regulation"]
AOL_GROUPS = ["Observation", "Conversation", "Product"]


def _blocks(value):
    """Accept a string, a block list, or {values, text} and return blocks."""
    if isinstance(value, dict):
        out = []
        vals = value.get("values") or []
        if vals:
            out.append({"type": "para", "text": ", ".join(vals), "bold": True})
        out.extend(_blocks(value.get("text")))
        return out
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [{"type": "para", "text": value}]


def meta_grid2(doc, rows):
    """Two header/value pairs stacked in one 4-column table."""
    ncol = len(rows[0][0])
    w = CONTENT_WIN / ncol
    t = make_table(doc, [w] * ncol)
    for ri, (labels, values) in enumerate(rows):
        hr = add_row(t, header=(ri == 0), cant_split=True)
        for c, label in zip(hr.cells, labels):
            header_cell(c, label)
        dr = add_row(t, cant_split=True)
        for ci, (c, v) in enumerate(zip(dr.cells, values)):
            p = c.paragraphs[0]
            _no_space(p, 2, 2, line=1.08)
            lead = ri == 0 and ci == 0
            _run(p, v or "", bold=lead, color=MAROON if lead else INK)
    return t


class _ParaHost:
    """Lets checkbox_line (which writes to cell.paragraphs[0]) fill a chosen paragraph."""

    def __init__(self, paragraph):
        self.paragraphs = [paragraph]


def checkbox_lines(cell, items, per_line=3):
    """Checkbox rows of per_line items each, so a box never separates from its name."""
    for i in range(0, len(items), per_line):
        host = cell if i == 0 else _ParaHost(cell.add_paragraph())
        checkbox_line(host, items[i:i + per_line])


def content_standards(doc, spec):
    lw = CONTENT_WIN * 0.26
    t = make_table(doc, [lw, CONTENT_WIN - lw], bar="Content Standards")
    skills = spec.get("learning_skills", {}) or {}
    row = add_row(t, cant_split=True)
    _label_cell(row.cells[0], "Learning Skills")
    checkbox_lines(row.cells[1], [(k, bool(skills.get(k, False))) for k in LEARNING_SKILLS])
    cur = spec.get("curriculum", {}) or {}
    cats = cur.get("achievement_categories", {}) or {}
    row = add_row(t, cant_split=True)
    _label_cell(row.cells[0], "Achievement Categories")
    checkbox_line(row.cells[1],
                  [(k, bool(cats.get(k, False))) for k in (list(cats) or L.ACHIEVEMENT)])
    kv_row(t, "Overall Expectations", cur.get("overall"), cant_split=True)
    kv_row(t, "Specific Expectations", cur.get("specific"), cant_split=True)
    res = spec.get("resources") or []
    # The tallest row; it may continue on the next page under the repeated bar.
    kv_row(t, "Resources / Worksheets", [{"type": "bullets", "items": res}] if res else None, cant_split=True)
    return t


def islamic_character(doc, spec):
    L.two_column(doc, _blocks(spec.get("islamic_expectations")),
                 _blocks(spec.get("character_education")),
                 bar="Islamic Expectations & Character Education",
                 headers=("Islamic Expectations", "Character Education"))


def daily_lessons(doc, days, left_ratio=0.52):
    """One fused sub-bar table per day. The section bar is fused into the first
    day's table as well, so it can never be orphaned at a page foot."""
    lw = CONTENT_WIN * left_ratio
    widths = [lw, CONTENT_WIN - lw]
    for i, day in enumerate(days or []):
        num = day.get("num") or str(i + 1)
        text = phase_text(num, f"DAY {num}", day.get("time"), day.get("title"), day.get("text"))
        if i == 0:
            t = make_table(doc, widths, bar="Daily Lessons")
            _bar_row(t, text, "sub")
        else:
            t = make_table(doc, widths, bar=text, bar_kind="sub")
        cr = add_row(t)
        for cell, side, default in ((cr.cells[0], "left", "Teacher Actions"),
                                    (cr.cells[1], "right", None)):
            data = day.get(side, {}) or {}
            label = data.get("label", default)
            blocks = [{"type": "label", "text": label}] if label else []
            render_blocks(cell, blocks + list(data.get("blocks", []) or []))


def assessment_block(doc, asm):
    asm = asm or {}
    third = CONTENT_WIN / 3.0
    t = make_table(doc, [third, third, third], bar="Assessment")
    hr = add_row(t, header=True)
    for c, label in zip(hr.cells, ("Assessment for Learning (AFL)",
                                   "Assessment as Learning (AAL)",
                                   "Assessment of Learning (AOL)")):
        header_cell(c, label, align="center")
    cr = add_row(t)
    render_blocks(cr.cells[0], [{"type": "bullets", "items": asm.get("for_learning") or []}])
    render_blocks(cr.cells[1], [{"type": "bullets", "items": asm.get("as_learning") or []}])
    of = asm.get("of_learning") or []
    if isinstance(of, dict):
        blocks = []
        order = [g for g in AOL_GROUPS if g in of] + [g for g in of if g not in AOL_GROUPS]
        for g in order:
            if of.get(g):
                blocks.append({"type": "label", "text": g})
                blocks.append({"type": "bullets", "items": of[g]})
        render_blocks(cr.cells[2], blocks)
    else:
        render_blocks(cr.cells[2], [{"type": "bullets", "items": of}])
    return t


def build(spec, out_path):
    require(spec, "title", "meta", where="weekly_plan")
    doc = new_document(spec.get("school"))

    rh = spec.get("context", {}) or {}
    masthead(doc, title="WEEKLY LESSON PLAN", subtitle=spec.get("title"),
             course_line_text=rh.get("course_line"), context_line=rh.get("context_line"),
             badge=spec.get("badge"), code=(spec.get("meta") or {}).get("course_code"))

    meta = spec.get("meta", {}) or {}
    meta_grid2(doc, [
        (["Teacher", "Course Code", "Subject", "Unit"],
         [meta.get("teacher", ""), meta.get("course_code", ""),
          meta.get("subject", ""), meta.get("unit", "")]),
        (["Week", "Dates", "Duration", "Grade"],
         [meta.get("week", ""), meta.get("dates", ""),
          meta.get("duration", ""), meta.get("grade", "")]),
    ])

    islamic_character(doc, spec)
    content_standards(doc, spec)
    L.goals_block(doc, spec)
    daily_lessons(doc, spec.get("days", []))
    assessment_block(doc, spec.get("assessment"))

    if spec.get("differentiation"):
        L.differentiation(doc, spec["differentiation"])

    if spec.get("notes"):
        t = make_table(doc, [CONTENT_WIN], bar="Notes")
        cr = add_row(t)
        render_blocks(cr.cells[0], _blocks(spec["notes"]))

    footer = "  |  ".join(x for x in (SCHOOL_TITLE, meta.get("course_code"), meta.get("week")) if x)
    return finish(doc, spec, "weekly_plan", out_path, default_footer=footer)

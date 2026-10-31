"""Short and Long Term Plan. Schema: references/long_range_plan_schema.md.

Same furniture as every other type: title block, blush metadata grid, maroon
section bars, maroon-header tables, and the rule-and-caption signature grid.
"""

import re

from gla_docx import (
    BLUSH, CONTENT_WIN, INK, MAROON, SCHOOL_TITLE, SpecError, _fill_cell, _label_cell,
    add_row, body_para, bullet, derive_badge, finish, footer_text, header_cell, masthead,
    make_table, metadata_grid, new_document, render_blocks, require, section_bar,
    signature_pairs,
)

SHORT_COLUMNS = ["Unit", "Unit Title", "Start", "End (approx.)", "Evaluation"]
SHORT_WIDTHS = [0.6, 2.2, 1.15, 1.25, 1.7]
LONG_COLUMNS = ["Evaluation", "Due Date", "Title of Evaluation", "% of Grade"]
LONG_WIDTHS = [2.5, 1.3, 2.05, 1.05]
SIGNATURE_ROWS = [("Teacher's Signature", "Principal's Signature"),
                  ("Student's Signature", "Parent's Signature")]
META_LAYOUT = [("Course", "Course Code"), ("Grade", "Pathway"), ("Semester", "Teacher"),
               ("School Year", None)]

_PCT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _scale(widths):
    k = CONTENT_WIN / sum(widths)
    return [w * k for w in widths]


def _course(spec):
    course = spec.get("course")
    if isinstance(course, str):
        return {"code": course, "title": ""}
    return course or {}


def subtitle(spec):
    c = _course(spec)
    bits = []
    if c.get("grade"):
        bits.append(f"Grade {c['grade']}")
    if c.get("title"):
        bits.append(c["title"])
    line = ", ".join(bits)
    if c.get("code"):
        line = f"{line} ({c['code']})" if line else c["code"]
    return line or ""


def _lines(value):
    if isinstance(value, list):
        return "\n".join(str(v) for v in value if str(v).strip())
    return str(value or "")


def _percent_total(values):
    """Sum of the percentages found in values; None when any value has none."""
    total = 0.0
    for v in values:
        found = _PCT_RX.findall(_lines(v))
        if not found:
            return None
        total += sum(float(x) for x in found)
    return total


def _check_total(values, where):
    total = _percent_total(values)
    if total is not None and abs(total - 100.0) > 0.01:
        raise SpecError(f"{where}: weights total {total:g}%, expected 100%")


def _centre_map(rows, keys, limit=14):
    return {k: max((len(str(r.get(k, ""))) for r in rows), default=0) <= limit for k in keys}


def short_term_table(doc, st, bar=None):
    st = st or {}
    rows = st.get("rows", [])
    _check_total([r.get("evaluation", "") for r in rows], "short_term")
    keys = ["unit", "title", "start", "end", "evaluation"]
    centre = _centre_map(rows, ["start", "end"])
    columns = st.get("columns") or SHORT_COLUMNS
    t = make_table(doc, _scale(SHORT_WIDTHS), bar=bar)
    hr = add_row(t, header=True)
    for i, text in enumerate(columns):
        header_cell(hr.cells[i], text, align="center" if keys[i] in ("start", "end") else "left")
    for r in rows:
        row = add_row(t, cant_split=True)
        for i, k in enumerate(keys):
            _fill_cell(row.cells[i], _lines(r.get(k, "")), color=INK,
                       bold=(k == "unit"), center=bool(centre.get(k)))
    total = add_row(t, cant_split=True)
    for i, text in enumerate(["Total", "", "", "", st.get("total") or "100%"]):
        _fill_cell(total.cells[i], text, bold=True, color=INK, fill=BLUSH)
    return t


def long_term_table(doc, lt, bar=None):
    """The first cell carries the unit (maroon) above the evaluation label; the
    unit is shown on the first row of each run of rows that share it."""
    lt = lt or {}
    rows = lt.get("rows", [])
    _check_total([r.get("weight", "") for r in rows], "long_term")
    columns = lt.get("columns") or LONG_COLUMNS
    keys = ["due", "title", "weight"]
    centre = _centre_map(rows, keys)
    t = make_table(doc, _scale(LONG_WIDTHS), bar=bar)
    hr = add_row(t, header=True)
    for i, text in enumerate(columns):
        header_cell(hr.cells[i], text, align="center" if (i > 0 and centre[keys[i - 1]]) else "left")
    previous = None
    for r in rows:
        row = add_row(t, cant_split=True)
        blocks = []
        group = r.get("group")
        if group and group != previous:
            blocks.append({"type": "para", "text": group, "bold": True, "color": MAROON})
        previous = group
        if r.get("label"):
            blocks.append({"type": "para", "text": r["label"], "bold": True})
        render_blocks(row.cells[0], blocks)
        for i, k in enumerate(keys, start=1):
            _fill_cell(row.cells[i], r.get(k, ""), color=INK, center=centre[k])
    total = add_row(t, cant_split=True)
    for i, text in enumerate(["Total", "", "", lt.get("total") or "100%"]):
        _fill_cell(total.cells[i], text, bold=True, color=INK, fill=BLUSH,
                   center=(i > 0 and centre[keys[i - 1]]))
    return t


def build(spec, out_path):
    require(spec, "course", "teacher", "short_term", "long_term", where="long_range_plan")
    doc = new_document(spec.get("school"))
    c = _course(spec)

    rh = spec.get("context", {}) or {}
    ctx_bits = [x for x in (str(spec.get("semester") or ""), f"Teacher: {spec['teacher']}" if spec.get("teacher") else "") if x]
    masthead(doc, title="SHORT AND LONG TERM PLAN", subtitle=subtitle(spec),
             course_line_text=rh.get("course_line") or (f"{c['code']}: {c['title']}" if c.get("title") else c.get("code")),
             context_line=rh.get("context_line") or "  |  ".join(ctx_bits),
             badge=spec.get("badge") or derive_badge(c.get("code"), grade=c.get("grade"), pathway=c.get("pathway")),
             code=c.get("code"))
    meta = {
        "Course": c.get("title") or "",
        "Course Code": c.get("code") or "",
        "Grade": f"Grade {c['grade']}" if c.get("grade") else "",
        "Pathway": c.get("pathway") or "",
        "Semester": str(spec.get("semester") or ""),
        "Teacher": spec.get("teacher") or "",
    }
    if spec.get("school_year"):
        meta["School Year"] = str(spec["school_year"])
    meta = {k: v for k, v in meta.items() if v}
    metadata_grid(doc, meta, META_LAYOUT)

    short_term_table(doc, spec.get("short_term"), bar="Short Term Plan")
    long_term_table(doc, spec.get("long_term"), bar="Long Term Plan")

    notes = spec.get("notes") or []
    if notes:
        section_bar(doc, "Notes")
        for n in notes:
            bullet(doc, n)

    if spec.get("signatures", True):
        signature_pairs(doc, SIGNATURE_ROWS, bar="Signatures")

    footer = footer_text(SCHOOL_TITLE, "Short and Long Term Plan", c.get("code"))
    return finish(doc, spec, "long_range_plan", out_path, default_footer=footer)

"""Exam cover page (one page). Schema: references/exam_cover_schema.md.

Same furniture as every other type: title block, blush metadata grid, fused
section bars over the categories table and the instructions.
"""

from docx.enum.text import WD_ALIGN_PARAGRAPH

import categories
from gla_docx import (
    CONTENT_WIN, INK, MAROON, SCHOOL_TITLE, SP, T, _bullet_paragraph, _fill_cell,
    _no_space, _run, add_row, derive_badge, finish, footer_text, header_cell, masthead,
    make_table, metadata_grid, new_document, require,
)

BISMILLAH = "In the name of Allah the Most Gracious, the Most Merciful"
FIELD_LAYOUT = [("Name", "Course Teacher"), ("Course Name", "Course Code"),
                ("Exam Date", "Exam Time"), ("Exam Room", "Exam Pages")]
FIELD_KEYS = {"Name": "name", "Course Teacher": "course_teacher", "Course Name": "course_name",
              "Course Code": "course_code", "Exam Date": "exam_date", "Exam Time": "exam_time",
              "Exam Room": "exam_room", "Exam Pages": "exam_pages"}
# "T/I" is the Science abbreviation (Thinking and Investigation). Every other
# subject, Computer Studies included, abbreviates the category "T"; the course
# code decides, via categories.thinking_abbrev.
def default_categories(course_code=None):
    return [
        {"name": "K/U", "marks": "/XX", "weight": "XX%"},
        {"name": categories.thinking_abbrev(course_code), "marks": "/XX", "weight": "XX%"},
        {"name": "COMM", "marks": "/XX", "weight": "XX%"},
        {"name": "APP", "marks": "/XX", "weight": "XX%"},
        {"name": "FINAL", "marks": "/XX", "weight": "____%"},
    ]
DEFAULT_INSTRUCTIONS = [
    "Complete, well-written answers are required for all questions.",
    "Read all questions carefully to avoid losing marks unnecessarily.",
    "This exam is made up of ___ pages (including this page or the answer sheet). "
    "Check that all pages are included.",
    "This exam is worth ___ % of your final mark.",
    "Check your answers before submitting your exam. Do not leave any questions blank.",
]


def bismillah_line(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(p, SP["para_before_pt"], SP["para_after_pt"])
    _run(p, text, italic=True, size=T["sub_pt"], color=MAROON)
    return p


def field_grid(doc, fields):
    """The blush label grid used by every other type; a blank value is the
    student's space to write."""
    fields = fields or {}
    data = {label: str(fields.get(key) or "") for label, key in FIELD_KEYS.items()}
    return metadata_grid(doc, data, FIELD_LAYOUT, label_w=1.3)


def categories_table(doc, cats, course_code=None):
    cats = cats or default_categories(course_code)
    w = CONTENT_WIN / len(cats)
    t = make_table(doc, [w] * len(cats), bar="Categories")
    hr = add_row(t, header=True)
    for c, cat in zip(hr.cells, cats):
        header_cell(c, cat.get("name", ""), align="center")
    mr = add_row(t, cant_split=True)
    for c, cat in zip(mr.cells, cats):
        _fill_cell(c, cat.get("marks", ""), bold=True, center=True, color=INK, size=T["section_pt"])
    wr = add_row(t, cant_split=True)
    for c, cat in zip(wr.cells, cats):
        _fill_cell(c, cat.get("weight", ""), center=True, color=INK)
    return t


def instructions_block(doc, items):
    t = make_table(doc, [CONTENT_WIN], bar="Instructions for Students")
    row = add_row(t)
    cell = row.cells[0]
    for n, text in enumerate(items, start=1):
        p = cell.paragraphs[0] if n == 1 else cell.add_paragraph()
        _bullet_paragraph(p, text, base=0.0, marker=f"{n}.", line=1.1)
    return t


def build(spec, out_path):
    require(spec, "exam_period", "month_year", where="exam_cover")
    doc = new_document(spec.get("school"))

    fields = spec.get("fields") or {}
    rh = spec.get("context", {}) or {}
    code = fields.get("course_code") or ""
    sub = "  |  ".join(x for x in (spec["exam_period"], spec["month_year"]) if x)
    masthead(doc, title=spec.get("title") or "EXAMINATION", subtitle=sub,
             course_line_text=rh.get("course_line")
             or (f"{code}: {fields['course_name']}" if fields.get("course_name") else code or None),
             context_line=rh.get("context_line") or (spec.get("division") or "Secondary Division"),
             badge=spec.get("badge") or derive_badge(code), code=code)

    bismillah = spec.get("bismillah", True)
    if bismillah:
        bismillah_line(doc, bismillah if isinstance(bismillah, str) else BISMILLAH)

    field_grid(doc, spec.get("fields"))
    categories_table(doc, spec.get("categories"),
                     (spec.get("fields") or {}).get("course_code"))
    instructions_block(doc, spec.get("instructions") or DEFAULT_INSTRUCTIONS)

    code = (spec.get("fields") or {}).get("course_code")
    return finish(doc, spec, "exam_cover", out_path,
                  default_footer=footer_text(SCHOOL_TITLE, "Examination", code))

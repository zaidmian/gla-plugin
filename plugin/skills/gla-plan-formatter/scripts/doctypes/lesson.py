"""Lesson plan (single period). Schema: references/lesson_schema.md."""

from gla_docx import (
    CONTENT_WIN, INK, MAROON, SCHOOL_TITLE,
    _label_cell, _no_space, _run, add_row, checkbox_line,
    finish, header_cell, kv_row, make_table, masthead, new_document,
    phase_text, render_blocks, require,
)

# Fallback order only. A spec's achievement_categories carries the names its
# parser resolved for the course's subject, and those win (categories.py).
ACHIEVEMENT = ["Knowledge & Understanding", "Thinking", "Communication", "Application"]
DIFF_DEFAULT = ["ELL Students", "IEP / Accommodation", "Advanced / Extension"]


def meta_grid(doc, labels, values, first_bold=True, bar=None):
    """Equal-column header + value grid (the 4-up lesson meta block)."""
    w = CONTENT_WIN / len(labels)
    t = make_table(doc, [w] * len(labels), bar=bar)
    hr = add_row(t, header=True)
    for c, label in zip(hr.cells, labels):
        header_cell(c, label)
    dr = add_row(t, cant_split=True)
    for i, (c, v) in enumerate(zip(dr.cells, values)):
        p = c.paragraphs[0]
        _no_space(p, 2, 2, line=1.08)
        _run(p, v or "", bold=(i == 0 and first_bold),
             color=MAROON if (i == 0 and first_bold) else INK)
    return t


def two_column(doc, left_blocks, right_blocks, bar=None, bar_kind="section",
               headers=None, left_ratio=0.5):
    """One row of two block-filled cells, optionally under a fused bar and a header row."""
    lw = CONTENT_WIN * left_ratio
    t = make_table(doc, [lw, CONTENT_WIN - lw], bar=bar, bar_kind=bar_kind)
    if headers:
        hr = add_row(t, header=True)
        header_cell(hr.cells[0], headers[0], align="center")
        header_cell(hr.cells[1], headers[1], align="center")
    cr = add_row(t)
    render_blocks(cr.cells[0], left_blocks)
    render_blocks(cr.cells[1], right_blocks)
    return t


def sequence(doc, phases, left_ratio=0.52):
    for ph in phases or []:
        text = phase_text(ph.get("num"), ph.get("phase"), ph.get("time"),
                          ph.get("subtitle"), ph.get("text"))
        sides = []
        for side in ("left", "right"):
            data = ph.get(side, {}) or {}
            blocks = [{"type": "label", "text": data["label"]}] if data.get("label") else []
            sides.append(blocks + data.get("blocks", []))
        two_column(doc, sides[0], sides[1], bar=text, bar_kind="sub", left_ratio=left_ratio)


def differentiation(doc, diff, title="Teacher Notes & Differentiation Summary"):
    third = CONTENT_WIN / 3.0
    t = make_table(doc, [third, third, third], bar=title)
    cr = add_row(t)
    order = list(diff.keys()) if diff else DIFF_DEFAULT
    for cell, key in zip(cr.cells, order):
        render_blocks(cell, [{"type": "label", "text": key},
                             {"type": "bullets", "items": (diff or {}).get(key, [])}])


def curriculum_block(doc, cur, bar="Curriculum Expectations"):
    lw = CONTENT_WIN * 0.26
    t = make_table(doc, [lw, CONTENT_WIN - lw], bar=bar)
    kv_row(t, "Overall Expectation", cur.get("overall"))
    kv_row(t, "Specific Expectations", cur.get("specific"))
    row = add_row(t, cant_split=True)
    lab, val = row.cells
    _label_cell(lab, "Achievement Chart Categories")
    cats = cur.get("achievement_categories", {}) or {}
    checkbox_line(val, [(k, bool(cats.get(k, False))) for k in (list(cats) or ACHIEVEMENT)])
    return t


def goals_block(doc, spec):
    lg_blocks = []
    if spec.get("learning_goals_lead"):
        lg_blocks.append({"type": "para", "text": spec["learning_goals_lead"], "bold": True})
    lg_blocks.append({"type": "bullets", "items": spec.get("learning_goals", [])})
    two_column(doc, lg_blocks, [{"type": "bullets", "items": spec.get("success_criteria", [])}],
               bar="Learning Goals & Success Criteria",
               headers=("Learning Goals", "Success Criteria"))


def materials_block(doc, mats):
    mats = mats or {}
    two_column(doc,
               [{"type": "label", "text": "Teacher Materials"},
                {"type": "bullets", "items": mats.get("teacher", [])}] + mats.get("teacher_extra", []),
               [{"type": "label", "text": "Student Materials"},
                {"type": "bullets", "items": mats.get("student", [])}] + mats.get("student_extra", []),
               bar="Materials & Resources")


def build(spec, out_path):
    require(spec, "title", "meta", where="lesson")
    doc = new_document(spec.get("school"))

    rh = spec.get("context", {}) or {}
    meta = spec.get("meta", {})
    masthead(doc, title="LESSON PLAN", subtitle=spec.get("title"),
             course_line_text=rh.get("course_line"), context_line=rh.get("context_line"),
             badge=spec.get("badge"), code=meta.get("course_code"))

    meta_grid(doc, ["Course Code", "Unit", "Lesson", "Duration"],
              [meta.get("course_code", ""), meta.get("unit", ""),
               meta.get("lesson", ""), meta.get("duration", "")])

    curriculum_block(doc, spec.get("curriculum", {}) or {})
    goals_block(doc, spec)
    materials_block(doc, spec.get("materials"))

    # The Lesson Sequence bar introduces a run of phase tables; a paragraph bar
    # with keepNext is right here because the first phase bar row is short.
    from gla_docx import section_bar
    section_bar(doc, "Lesson Sequence")
    sequence(doc, spec.get("sequence", []))

    differentiation(doc, spec.get("differentiation", {}))

    gc = spec.get("google_classroom")
    if gc:
        t = make_table(doc, [CONTENT_WIN], bar="Connections to Google Classroom")
        cr = add_row(t)
        render_blocks(cr.cells[0], [{"type": "bullets", "items": gc}])

    return finish(doc, spec, "lesson", out_path, default_footer=SCHOOL_TITLE)

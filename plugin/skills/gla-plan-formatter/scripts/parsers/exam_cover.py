"""Markdown -> exam_cover spec. Conventions: references/exam_cover_schema.md.

    ---                                   front matter carries the scalars:
    division: Secondary Division          division, exam_period (quote it, it
    exam_period: "Final Exams: Semester 1"  holds a colon), month_year,
    month_year: January 2026              bismillah (true | false | text),
    fields:                               footer, and the field grid either
      exam_room: Gym                      nested under fields: or flat
    ---
    ## Categories                         optional pipe table: header = names,
    | K/U | T/I | ... |                   row 1 = marks, row 2 = weights
    ## Instructions                       numbered list; blanks stay as ___
"""

from mdparse import (
    find_section, first_table, list_items, section_map, split_front_matter, strip_inline,
    tokenize,
)

FIELD_KEYS = ("name", "course_teacher", "course_name", "course_code",
              "exam_date", "exam_time", "exam_room", "exam_pages")


def _text(v):
    return "" if v is None else str(v).strip()


def _categories(table):
    if not table or not table.get("header"):
        return None
    names = [strip_inline(h) for h in table["header"]]
    rows = table.get("rows", [])
    marks = rows[0] if rows else []
    weights = rows[1] if len(rows) > 1 else []
    out = []
    for i, name in enumerate(names):
        if not name:
            continue
        out.append({
            "name": name,
            "marks": strip_inline(marks[i]) if i < len(marks) else "",
            "weight": strip_inline(weights[i]) if i < len(weights) else "",
        })
    return out or None


def parse(text, path=None):
    front, body = split_front_matter(text)
    tokens = tokenize(body)
    spec = {}
    for key in ("school", "division", "exam_period", "month_year", "footer"):
        if front.get(key) not in (None, ""):
            spec[key] = _text(front[key])
    if "bismillah" in front:
        b = front["bismillah"]
        spec["bismillah"] = b if isinstance(b, bool) else _text(b)

    fields = {}
    nested = front.get("fields")
    if isinstance(nested, dict):
        for k, v in nested.items():
            fields[str(k)] = _text(v)
    for k in FIELD_KEYS:
        if k in front and k not in fields:
            fields[k] = _text(front[k])
    if fields:
        spec["fields"] = fields

    sections = section_map(tokens)
    cats = find_section(sections, "categor")
    parsed = _categories(first_table(cats)) if cats else None
    if parsed:
        spec["categories"] = parsed

    ins = find_section(sections, "instruction")
    items = list_items(ins) if ins else []
    if items:
        spec["instructions"] = [strip_inline(x) for x in items]
    return spec

"""Markdown -> long_range_plan spec (GLA "Short and Long Term Plan").
Conventions: references/long_range_plan_schema.md.

Two source shapes are accepted:

  (a) front matter (semester, course{code,title,grade,pathway}, teacher, ...)
      followed by `## Short Term Plan` and `## Long Term Plan`, each with one
      pipe table, and an optional `## Notes` bullet list;

  (b) the CS-pipeline shape: bold header lines (`**GIBRALTAR LEADERSHIP
      ACADEMY**`, `**GRADE 11 Introduction to Computer Science (ICS3U)**`,
      `**SHORT TERM PLAN**`), a `TEACHER: NAME` line, then the table; repeated
      for `**LONG TERM PLAN**`.

Short-term rows: `Unit | Unit Title | Start | End | Evaluation`. A row whose
title is empty takes the first cell as its title (Mock Trial, FINAL EXAM). A
first cell starting with TOTAL is the total row. Evaluation cells split on
`<br>` and, failing that, before each "NN%" so "4% Test 3% Assignment" becomes
two lines.

Long-term rows: `Evaluations | Due | Title | Weight`. A bold row with empty
other cells is a group header for the rows that follow; a first cell written
as `**GROUP**<br>Label` carries its group inline. TOTAL closes the table.
"""

import os
import re

from mdparse import (
    cell_lines, first_table, list_items, section_map, split_front_matter, strip_inline,
    tokenize,
)
from parsers._course import find_course_yaml, load_course_yaml, pathway_for_code, semester_label

_COURSE_RX = re.compile(
    r"^GRADE\s*-?\s*(\d+)\s*[,:]?\s*(.*?)\s*\(?\s*([A-Z]{3}[0-9][A-Z0-9])\s*\)?\s*$", re.I)
_SEMESTER_RX = re.compile(r"^SEMESTER\s*[:-]?\s*(\S.*)$", re.I)
_TEACHER_RX = re.compile(r"^TEACHER\s*[:-]\s*(.*)$", re.I)
_PCT_SPLIT_RX = re.compile(r"\s+(?=\d+(?:\.\d+)?\s*%)")
_PCT_RX = re.compile(r"\d+(?:\.\d+)?\s*%")


def _plain(text):
    return strip_inline(text or "").rstrip(":").strip()


def _is_total(cell):
    return _plain(cell).upper().startswith("TOTAL")


def _last_nonempty(cells):
    for c in reversed(cells):
        if _plain(c):
            return _plain(c)
    return ""


def _evaluation(cell):
    lines = [strip_inline(x) for x in cell_lines(cell)]
    if len(lines) == 1 and len(_PCT_RX.findall(lines[0])) > 1:
        lines = [x.strip() for x in _PCT_SPLIT_RX.split(lines[0]) if x.strip()]
    if not lines:
        return ""
    return lines[0] if len(lines) == 1 else lines


def _short_term(table):
    out = {"rows": []}
    for raw in table["rows"]:
        cells = list(raw) + [""] * (5 - len(raw))
        if not any(_plain(c) for c in cells):
            continue
        if _is_total(cells[0]):
            out["total"] = _last_nonempty(cells[1:]) or "100%"
            continue
        unit, title = _plain(cells[0]), _plain(cells[1])
        if not title and unit:
            unit, title = "", unit
        out["rows"].append({
            "unit": unit,
            "title": title,
            "start": _plain(cells[2]),
            "end": _plain(cells[3]),
            "evaluation": _evaluation(cells[4]),
        })
    return out


def _long_term(table):
    out = {"rows": []}
    group = None
    for raw in table["rows"]:
        cells = list(raw) + [""] * (4 - len(raw))
        if not any(_plain(c) for c in cells):
            continue
        if _is_total(cells[0]):
            out["total"] = _last_nonempty(cells[1:]) or "100%"
            continue
        first = cell_lines(cells[0])
        rest_empty = not any(_plain(c) for c in cells[1:])
        if rest_empty and len(first) == 1:
            group = _plain(first[0])
            continue
        row = {}
        if len(first) >= 2:
            row["group"] = _plain(first[0])
            label = " ".join(_plain(x) for x in first[1:])
        else:
            if group:
                row["group"] = group
            label = _plain(first[0]) if first else ""
        row.update({
            "label": label,
            "due": _plain(cells[1]),
            "title": _plain(cells[2]),
            "weight": _plain(cells[3]),
        })
        out["rows"].append(row)
    return out


def _course_from_front(front):
    course = front.get("course")
    if isinstance(course, dict):
        return {k: str(v) for k, v in course.items() if v not in (None, "")}
    out = {}
    if isinstance(course, str) and course.strip():
        m = _COURSE_RX.match(course.strip())
        if m:
            out = {"code": m.group(3).upper(), "title": m.group(2).strip(), "grade": m.group(1)}
        else:
            out["code"] = course.strip()
    for src, dst in (("course_code", "code"), ("course_title", "title"),
                     ("grade", "grade"), ("pathway", "pathway")):
        if front.get(src) not in (None, ""):
            out[dst] = str(front[src])
    return out


def parse(text, path=None):
    front, body = split_front_matter(text)
    tokens = tokenize(body)

    spec = {}
    if front.get("school"):
        spec["school"] = str(front["school"])
    if front.get("semester"):
        spec["semester"] = str(front["semester"])
    course = _course_from_front(front)
    if course:
        spec["course"] = course
    if front.get("teacher"):
        spec["teacher"] = str(front["teacher"])

    # Walk the body: headings and bold header lines steer which table is which.
    section = None
    tables = {}
    loose = []
    notes = []
    for b in tokens:
        if b.kind in ("h1", "h2", "h3"):
            low = b.text.lower()
            if low.startswith("short"):
                section = "short"
            elif low.startswith("long"):
                section = "long"
            elif low.startswith("note"):
                section = "notes"
            else:
                section = None
            continue
        if b.kind in ("label", "p"):
            txt = _plain(b.text)
            up = txt.upper()
            if up.startswith("SHORT TERM PLAN"):
                section = "short"
            elif up.startswith("LONG TERM PLAN"):
                section = "long"
            elif _TEACHER_RX.match(txt):
                spec.setdefault("teacher", _TEACHER_RX.match(txt).group(1).strip())
            elif _SEMESTER_RX.match(txt) and len(txt) < 30:
                spec.setdefault("semester", "Semester " + _SEMESTER_RX.match(txt).group(1).strip())
            elif _COURSE_RX.match(txt):
                m = _COURSE_RX.match(txt)
                spec.setdefault("course", {"code": m.group(3).upper(),
                                           "title": m.group(2).strip(),
                                           "grade": m.group(1)})
            elif up == "GIBRALTAR LEADERSHIP ACADEMY" or (up.isupper() and "ACADEMY" in up):
                spec.setdefault("school", txt)
            continue
        if b.kind == "table":
            if section in ("short", "long") and section not in tables:
                tables[section] = b.table
            else:
                loose.append(b.table)
            continue
        if b.kind in ("ul", "ol") and section == "notes":
            notes.extend(list_items([b]))

    for key in ("short", "long"):
        if key not in tables and loose:
            tables[key] = loose.pop(0)

    if "short" in tables:
        spec["short_term"] = _short_term(tables["short"])
    if "long" in tables:
        spec["long_term"] = _long_term(tables["long"])

    if front.get("notes"):
        notes = [str(n) for n in front["notes"]] + notes
    if notes:
        spec["notes"] = notes
    if "signatures" in front:
        spec["signatures"] = bool(front["signatures"])
    if front.get("footer"):
        spec["footer"] = str(front["footer"])

    _fill_from_course_repo(spec, path)
    return spec


def _fill_from_course_repo(spec, path):
    """Values the plan itself does not state: the semester label from the instance
    folder name, and pathway, title, grade, and the formal teacher name from the
    course.yaml above the source. Each fill is listed for review."""
    items = []
    course = spec.setdefault("course", {})
    if "semester" not in spec and path:
        label = semester_label(os.path.basename(os.path.dirname(os.path.abspath(path))))
        if label:
            spec["semester"] = label
            items.append({"section": "Header", "text": f"Semester read as \"{label}\" from the instance folder name."})
    cfg_path = find_course_yaml(path) if path else None
    cfg = load_course_yaml(cfg_path) if cfg_path else {}
    if cfg:
        if not course.get("pathway") and cfg.get("type"):
            course["pathway"] = str(cfg["type"])
            items.append({"section": "Header", "text": f"Pathway \"{course['pathway']}\" taken from course.yaml."})
        for src, dst in (("title", "title"), ("grade", "grade"), ("code", "code")):
            if not course.get(dst) and cfg.get(src) not in (None, ""):
                course[dst] = str(cfg[src])
        formal = cfg.get("teacher_formal")
        if formal and spec.get("teacher") != formal:
            old = spec.get("teacher")
            spec["teacher"] = str(formal)
            was = f" (the plan said \"{old}\")" if old else ""
            items.append({"section": "Header",
                          "text": f"Teacher set to the formal name \"{formal}\" from course.yaml{was}."})
    if not course.get("pathway") and course.get("code"):
        course["pathway"] = pathway_for_code(course["code"])
        if course["pathway"]:
            items.append({"section": "Header",
                          "text": f"Pathway \"{course['pathway']}\" derived from the course code."})
    if not course:
        spec.pop("course")
    if items:
        rv = spec.setdefault("review", {})
        rv.setdefault("items", []).extend(items)

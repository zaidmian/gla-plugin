"""Ontario curriculum expectations for a course code, read from Teaching/Curriculum.

Modern courses have Curriculum/data/curriculum/<CODE>.json, which carries
every code. Older (pdf-tier) courses only have the knowledge-graph page
Curriculum/docs/knowledge-graph/courses/<CODE>.md, where specific expectations
are unnumbered bullets; they get codes by position under their overall
expectation (A1.1, A1.2, ...), which is the local convention ICS3U and ICS4U
use. Pages where position is not trustworthy set `positional_reliable` False.
Strands the page leaves unlettered (all 2007 English, all Business, a few
others) get letters by position too (A, B, C in document order), so their
codes stay unique; `letters_assigned` is True then.
"""
import json
import os
import re

from . import paths

_STRAND = re.compile(r"^### (?:([A-Z])\. )?(.+)$")
_OVERALL = re.compile(r"^\*\*([A-Z]?)(\d+)(?:[^*]*)?\*\*\s*(.*)$")
_BULLET = re.compile(r"^- (.+)$")
_CONT = re.compile(r"^\s+> ?(.*)$")


class Course:
    def __init__(self, code):
        self.code = code
        self.meta = {}
        self.strands = []           # [{"letter", "title", "overalls": [{"code", "text", "specifics": [(code, text)]}]}]
        self.source = None
        self.positional = False
        self.positional_reliable = True
        self.letters_assigned = False
        self.notes = []

    @property
    def subject(self):
        return self.meta.get("subject", "")

    @property
    def grade(self):
        g = self.meta.get("grade")
        if isinstance(g, list):
            g = g[0] if g else None
        try:
            return int(g)
        except (TypeError, ValueError):
            return None

    @property
    def year_issued(self):
        try:
            return int(self.meta.get("year_issued"))
        except (TypeError, ValueError):
            return None

    def overall_codes(self):
        return [o["code"] for s in self.strands for o in s["overalls"]]

    def specific_codes(self):
        return [c for s in self.strands for o in s["overalls"] for c, _ in o["specifics"]]

    def specifics(self):
        return {c: t for s in self.strands for o in s["overalls"] for c, t in o["specifics"]}


def json_path(code):
    return os.path.join(paths.CURRICULUM, "data", "curriculum", "%s.json" % code)


def page_path(code):
    return os.path.join(paths.CURRICULUM, "docs", "knowledge-graph", "courses", "%s.md" % code)


def _frontmatter(text):
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    for line in text[3:end].splitlines():
        m = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', line)
        if m and m.group(2):
            meta[m.group(1)] = m.group(2)
    return meta, text[end + 4:]


def _from_json(course, path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    course.meta.update({"subject": data.get("subject", ""), "grade": data.get("grades"),
                        "course_type": data.get("course_type", ""), "name": data.get("name", "")})
    for s in data.get("strands") or []:
        os_ = s.get("overall_expectations") or []
        strand = {"letter": s.get("index"), "title": s.get("title", ""), "overalls": [],
                  "describer": (os_[0].get("describer", "") if os_ else "") or s.get("describer", "")}
        for o in os_:
            strand["overalls"].append({"code": o["index"], "text": o.get("text", ""), "title": o.get("title", ""),
                                       "specifics": [(x["index"], x.get("text", "")) for x in o.get("specific_expectations") or []]})
        course.strands.append(strand)


def _from_page(course, path):
    with open(path, encoding="utf-8") as f:
        meta, body = _frontmatter(f.read())
    course.meta.update(meta)
    course.positional = True
    strand = overall = None
    started = False
    for line in body.splitlines():
        if line.startswith("## "):
            started = line.strip() == "## What students learn"
            continue
        if not started:
            continue
        if line.strip() == "---":
            break
        m = _STRAND.match(line)
        if m:
            letter = m.group(1)
            if not letter:
                letter = chr(ord("A") + len(course.strands))
                course.letters_assigned = True
            strand = {"letter": letter, "title": m.group(2).strip(), "overalls": [], "describer": ""}
            course.strands.append(strand)
            overall = None
            continue
        if line.strip().lower().rstrip(":") == "students will":
            course.positional_reliable = False
            note = "bullets grouped under 'Students will:', not under their overall"
            if note not in course.notes:
                course.notes.append(note)
            continue
        if strand is not None and not strand["overalls"] and not strand["describer"] and re.match(r"^\*[^*].*\*$", line.strip()):
            strand["describer"] = line.strip().strip("*").strip()
            continue
        m = _OVERALL.match(line)
        if m and strand is not None:
            letter = m.group(1) or strand["letter"] or ""
            overall = {"code": "%s%s" % (letter, m.group(2)), "text": m.group(3).strip(), "title": "", "specifics": []}
            strand["overalls"].append(overall)
            continue
        m = _BULLET.match(line)
        if m and overall is not None:
            n = len(overall["specifics"]) + 1
            overall["specifics"].append(("%s.%d" % (overall["code"], n), m.group(1).strip().rstrip(";.")))
            continue
        m = _CONT.match(line)
        if m and overall is not None and overall["specifics"]:
            c, t = overall["specifics"][-1]
            overall["specifics"][-1] = (c, (t + " " + m.group(1)).strip())


def load(code):
    """Course data for a code, from the JSON when it exists, else the knowledge-graph page.
    Raises FileNotFoundError when the curriculum repo has neither."""
    code = code.upper()
    course = Course(code)
    page = page_path(code)
    if os.path.exists(page):
        with open(page, encoding="utf-8") as f:
            course.meta.update(_frontmatter(f.read())[0])
    if os.path.exists(json_path(code)):
        course.source = json_path(code)
        _from_json(course, course.source)
    elif os.path.exists(page):
        course.source = page
        _from_page(course, page)
    else:
        raise FileNotFoundError("no curriculum data for %s" % code)
    return course


def cross_cutting(course):
    """Strand letters the Ministry designates "throughout this course"."""
    return [s["letter"] for s in course.strands if (s.get("describer") or "").lower().startswith("throughout")]


def prerequisite(code):
    """The prerequisite as the curriculum states it: 'None', a code list, or ''."""
    jp = json_path(code.upper())
    if os.path.exists(jp):
        with open(jp, encoding="utf-8") as f:
            d = json.load(f)
        codes = d.get("prerequisite_codes") or []
        return ", ".join(codes) if codes else (d.get("prerequisites") or "None")
    pp = page_path(code.upper())
    if not os.path.exists(pp):
        return ""
    with open(pp, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^## Before you take this course\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        return ""
    body = m.group(1).strip()
    if re.search(r"no (formal )?prerequisite", body, re.I):
        return "None"
    found = re.findall(r"\b[A-Z]{3}[1-4][A-Z]\b", body)
    return ", ".join(dict.fromkeys(found)) if found else body.splitlines()[0]


def era(code):
    """'modern' when the JSON exists, else '2008' (pdf tier)."""
    return "modern" if os.path.exists(json_path(code.upper())) else "2008"


def thinking_name(subject):
    """The second achievement-chart category, as the course's curriculum document names it."""
    key = re.sub(r"[^a-z]", "", (subject or "").lower())
    return "Thinking and Investigation" if key in ("science", "scienceandtechnology") else "Thinking"

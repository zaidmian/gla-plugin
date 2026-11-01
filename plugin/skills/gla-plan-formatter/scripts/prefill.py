#!/usr/bin/env python3
"""
prefill: print the interview's "A. Confirm" block with every value that can be
determined without judgement, each with where it came from, and the facts it
could not determine as "B. Missing" candidates.

    python3 prefill.py --type TYPE [--code SBI4U] [--course-yaml path] [--source extracted.txt]

TYPE is one of lesson, weekly_plan, unit, course_outline, long_range_plan,
exam_cover. Sources, in order of precedence:

- course.yaml (--course-yaml, or the first one found in the current directory
  or above it): code, title, grade, type, department, prerequisite, credit,
  hours, curriculum document, teacher_formal, assessment buckets.
- the course code (--code, else course.yaml, else the first code in --source):
  the grade from the fourth character and the course type from the suffix
  (rule below); the title, prerequisite, curriculum document and strands from
  the bundled curriculum index through curriculum.py; the second
  achievement-chart category through categories.py.
- the 2026 Growing Success model: final-mark buckets by grade, and the exam
  versus culminating split from the subject matrix in
  Teaching/Standards/assessment/growing-success-summary.md when that file is
  reachable (Claude Code), else from the bundle's
  references/growing_success_matrix.md (claude.ai, copied in at build time);
  with neither, the split is listed as missing.
- --source (text from extract_text.py, or any file it reads): a course code,
  a name after "Teacher:", and dates, each marked "from your document, confirm".

Nothing is guessed. A value with no source is a "B. Missing" candidate; the
mapping step drops any candidate the teacher's document does supply.
"""

import argparse
import datetime as dt
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import categories  # noqa: E402
import curriculum  # noqa: E402

TYPES = ["lesson", "weekly_plan", "unit", "course_outline", "long_range_plan", "exam_cover"]

# Course type from the code's suffix (the fifth character).
SUFFIX = {
    "D": "Academic",
    "P": "Applied",
    "U": "University Preparation",
    "C": "College Preparation",
    "M": "University/College Preparation",
    "O": "Open",
    "W": "De-streamed",
    "E": "Workplace Preparation",
}
# Grade from the fourth character.
GRADE = {"1": 9, "2": 10, "3": 11, "4": 12}

# Final-mark buckets, 2026 Growing Success model (interview.md, "Derivations";
# growing-success-summary.md, Chapter 6, "Final mark breakdown").
BUCKETS = {
    "9-10": {"classroom": 65, "final_evaluation": 20, "attendance": 15},
    "11-12": {"classroom": 65, "final_evaluation": 25, "attendance": 10},
}
# Achievement-chart default weighting (interview.md, "Derivations").
CHART_WEIGHTS = "K/U 25, Thinking 30, Communication 20, Application 25"
SCHOOL = "Gibraltar Leadership Academy"

# Subject labels as the Growing Success matrix writes them, where they differ
# from the curriculum extract's file name.
SUBJECT_LABEL = {
    "First_Nations_M_tis_and_Inuit_Studies.md": "First Nations, Métis, and Inuit Studies",
    "French_as_a_Second_Language.md": "French",
}
# Subjects with no mandatory written exam (growing-success-summary.md,
# "Exemptions from the written-exam requirement").
EXAM_EXEMPT_SUBJECTS = {"Guidance and Career Education", "Cooperative Education",
                        "Interdisciplinary Studies", "American Sign Language as a Second Language"}
EXAM_EXEMPT_EXCEPT = {"GLC2O"}

GS_REL = os.path.join("Standards", "assessment", "growing-success-summary.md")
# The bundle's copy of the matrix sections (make_skill_bundle.py, .bundlevendor).
GS_BUNDLED = os.path.join(HERE, "..", "references", "growing_success_matrix.md")
CODE_RX = re.compile(r"\b([A-Z]{3}[1-4][A-Z])\d?\b")
MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
          "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
DATE_RX = re.compile(
    rf"\b(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?,?\s+)?"
    rf"(?:(?:{MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}\s+(?:{MONTHS})\.?,?\s+\d{{4}}"
    rf"|\d{{4}}-\d{{2}}-\d{{2}})\b")
TEACHER_RX = re.compile(r"^[\s|]*(?:course\s+)?teacher(?:'s)?(?:\s+name)?\s*[:|]\s*([^|\n]+)",
                        re.I | re.M)


# ---------------------------------------------------------------- course.yaml

def _scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def read_yaml(path):
    """course.yaml as a dict. PyYAML when present, else a reader for the flat
    keys and one-level mappings that course.yaml uses."""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except ImportError:
        pass
    data, parent = {}, None
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split(" #")[0].rstrip() if not raw.lstrip().startswith("#") else ""
            if not line.strip():
                continue
            m = re.match(r"^(\s*)([A-Za-z_][\w-]*):\s*(.*)$", line)
            if not m:
                continue
            indent, key, val = m.groups()
            if not indent:
                if val:
                    data[key], parent = _scalar(val), None
                else:
                    data[key], parent = {}, key
            elif parent is not None and val:
                data[parent][key] = _scalar(val)
    return data


def find_course_yaml(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, "course.yaml")
        if os.path.isfile(p):
            return p
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


# ---------------------------------------------------------------- curriculum

def course_facts(code):
    """Title, subject, prerequisite, document year and strands from the
    bundled index, or {} when the code is not bundled."""
    try:
        rows = {c.strip().upper(): (f, t) for c, f, t in curriculum.index()}
    except Exception:
        return {}
    if code not in rows:
        return {}
    fname, title = rows[code]
    facts = {"file": fname,
             "title": strip_title(code, title),
             "subject": SUBJECT_LABEL.get(fname, os.path.splitext(fname)[0].replace("_", " "))}
    try:
        text = curriculum.course_text(code)
    except SystemExit:
        return facts
    m = re.search(r"year_issued:\s*(\d{4})", text)
    if m:
        facts["year"] = m.group(1)
    m = re.search(r"^## Before you take this course\s*\n+(.+)$", text, flags=re.M)
    if m:
        line = m.group(1).strip()
        if re.search(r"no formal prerequisite", line, flags=re.I):
            facts["prerequisite"] = "None"
        else:
            facts["prerequisite"] = re.sub(r"^Students should first complete\s+", "", line).rstrip(".")
    try:
        facts["strands"] = curriculum.strand_names(code)
    except SystemExit:
        pass
    return facts


# ---------------------------------------------------------------- Growing Success

def find_growing_success(*starts):
    for start in starts:
        if not start:
            continue
        d = os.path.abspath(start)
        while True:
            p = os.path.join(d, GS_REL)
            if os.path.isfile(p):
                return p
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
    return GS_BUNDLED if os.path.isfile(GS_BUNDLED) else None


def _fold(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _pct(cell):
    m = re.match(r"\s*(\d+)\s*%", cell)
    if m:
        return int(m.group(1))
    return 0 if cell.strip() in ("\u2014", "-", "\u2013", "") else None


def parse_matrix(text):
    """{'9-10': [(subject cell, exam cell, culminating cell)], '11-12': [...]}"""
    out, band = {}, None
    for line in text.splitlines():
        h = re.match(r"^#+\s*Final evaluation by subject\D*(\d+)\D+(\d+)", line)
        if h:
            band = f"{h.group(1)}-{h.group(2)}"
            out[band] = []
            continue
        if line.startswith("#"):
            band = None
            continue
        if band and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and not re.fullmatch(r":?-+:?", cells[1]) and cells[0] != "Subject area":
                out[band].append((cells[0], cells[1], cells[2]))
    return out


def strip_title(code, title):
    """The course title without its code or an "(effective ... school year)" note."""
    t = re.sub(r"\s*\(" + re.escape(code) + r"\)\s*$", "", title, flags=re.I)
    return re.sub(r"\s*\(effective [^)]*\)", "", t, flags=re.I).strip()


def exam_split(code, grade, facts, gs_path):
    """(exam, culminating, note) from the Growing Success matrix, or
    (None, None, reason) when it cannot be read off."""
    if not gs_path:
        return None, None, "the subject matrix (Standards/assessment/growing-success-summary.md) is not in reach"
    with open(gs_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    band = "9-10" if grade in (9, 10) else "11-12"
    for line in text.splitlines():
        if "special case" in line.lower() and code in line:
            m = re.search(r"(\d+)\s*%\s*written exam", line.replace("*", ""))
            if m:
                return int(m.group(1)), 0, ("the EQAO Grade 9 assessment is the written exam" if "EQAO" in line
                                            else "special case in the matrix")
    subject = facts.get("subject", "")
    suffix = code[4]
    if (subject in EXAM_EXEMPT_SUBJECTS and code not in EXAM_EXEMPT_EXCEPT) \
            or (band == "11-12" and suffix in ("E", "O")):
        why = "an Open or Workplace course" if subject not in EXAM_EXEMPT_SUBJECTS else subject
        return None, None, f"no mandatory written exam ({why}, exemption in the matrix)"
    rows = parse_matrix(text).get(band, [])
    for cell, ex, cu in rows:
        if re.search(r"\(" + re.escape(code) + r"\)", cell):
            return _pct(ex), _pct(cu), cu if _pct(cu) is not None and not re.fullmatch(r"\d+%", cu) else ""
    if subject:
        rx = re.compile(r"\b" + re.escape(_fold(subject)) + r"\b(?:\s*\(([^)]+)\))?")
        for cell, ex, cu in rows:
            m = rx.search(_fold(cell))
            if not m:
                continue
            qual = m.group(1)
            if qual and _fold(qual) not in _fold(facts.get("title", "")):
                continue
            e, c = _pct(ex), _pct(cu)
            if e is None or c is None:
                continue
            return e, c, ""
    return None, None, f"no row for {subject or code} in the matrix"


# ---------------------------------------------------------------- source facts

def source_facts(text):
    facts = {"codes": [], "teacher": None, "dates": []}
    for c in CODE_RX.findall(text):
        if c not in facts["codes"]:
            facts["codes"].append(c)
    m = TEACHER_RX.search(text)
    if m:
        name = m.group(1).strip().strip("_").strip()
        if name and not re.fullmatch(r"[_\s.]*", name):
            facts["teacher"] = name
    seen = set()
    for line in text.splitlines():
        for dm in DATE_RX.finditer(line):
            date = " ".join(dm.group(0).split())
            before = line[:dm.start()]
            label = ""
            if ":" in before or "|" in before:
                label = re.split(r"[|]", before)[-1].strip().rstrip(":").strip()
                if not label:
                    parts = [p.strip() for p in before.split("|") if p.strip()]
                    label = parts[-1].rstrip(":") if parts else ""
            key = (label.lower(), date)
            if key in seen:
                continue
            seen.add(key)
            facts["dates"].append((label[:40], date))
    return facts


# ---------------------------------------------------------------- assemble

def prefill(doc_type, code=None, course_yaml=None, source_text=None, cwd=None, today=None):
    """Returns (confirm, missing): confirm is [(label, value, origin)],
    missing is [(label, note)]."""
    confirm, missing, notes = [], [], []
    cy, cy_path = {}, course_yaml
    if not cy_path:
        cy_path = find_course_yaml(cwd or os.getcwd())
    if cy_path:
        cy = read_yaml(cy_path)
        cy_code = str(cy.get("code", "")).strip().upper()
        if code and cy_code and cy_code != code.upper() and not course_yaml:
            notes.append(f"course.yaml at {cy_path} is for {cy_code}, not {code.upper()}; not used")
            cy = {}
    src = source_facts(source_text) if source_text else {"codes": [], "teacher": None, "dates": []}

    YML = "[from course.yaml]"
    DOC = "[from your document, confirm]"
    IDX = "[from the curriculum index]"

    # The code.
    origin = None
    if code:
        code, origin = code.strip().upper(), "[given]"
    elif cy.get("code"):
        code, origin = str(cy["code"]).strip().upper(), YML
    elif src["codes"]:
        code, origin = src["codes"][0], DOC
    m = re.fullmatch(r"([A-Z]{3}[1-4][A-Z])\d?", code or "")
    code = m.group(1) if m else code
    if src["codes"] and code and code not in src["codes"]:
        notes.append(f"your document names {', '.join(src['codes'][:3])}, not {code}")
    facts = course_facts(code) if m else {}

    if not code:
        missing.append(("Course code", "not given and not found in the source"))
    title = cy.get("title") or facts.get("title")
    if code:
        t_origin = YML if cy.get("title") else (IDX if facts.get("title") else None)
        value = f"{code}, {title}" if title else code
        if not t_origin or t_origin == origin:
            c_origin = origin
        else:
            c_origin = f"[code {origin.strip('[]')}; title {t_origin.strip('[]')}]"
        confirm.append(("Course", value, c_origin))
        if not title:
            missing.append(("Course title", f"{code} is not in the bundled curriculum index"))

    # Grade and course type.
    grade = cy.get("grade")
    g_origin = YML if grade else None
    if not grade and m:
        grade, g_origin = GRADE[code[3]], f'[derived from "{code[3:]}"]'
    ctype = cy.get("type")
    t_origin = YML if ctype else None
    if not ctype and m and code[4] in SUFFIX:
        ctype, t_origin = SUFFIX[code[4]], f'[derived from "{code[3:]}"]'
    if grade or ctype:
        val = ", ".join(x for x in (f"Grade {grade}" if grade else "", ctype or "") if x)
        confirm.append(("Grade and course type", val, g_origin if g_origin == t_origin or not t_origin
                        else (t_origin if not g_origin else f"{g_origin}; type {t_origin}")))
    if not grade:
        missing.append(("Grade", "no course code or course.yaml to read it from"))
    if code and m and not ctype:
        missing.append(("Course type", f'suffix "{code[4]}" is not in the course-type rule'))
    try:
        grade = int(grade) if grade else None
    except (TypeError, ValueError):
        grade = None

    # Achievement-chart categories.
    second = categories.thinking_name(code)
    cats = f"Knowledge and Understanding, {second}, Communication, Application"
    if doc_type in ("lesson", "weekly_plan") and code:
        confirm.append(("Achievement categories named", cats, "[second category from the curriculum document]"))
    if doc_type == "exam_cover" and code:
        confirm.append(("Category abbreviations", f"K/U, {categories.thinking_abbrev(code)}, COMM, APP",
                        "[second category from the curriculum document]"))

    # Teacher.
    if doc_type in ("weekly_plan", "long_range_plan", "exam_cover"):
        forms = []
        if cy.get("teacher_formal"):
            forms.append((str(cy["teacher_formal"]), YML))
        if src["teacher"] and all(src["teacher"] != f for f, _ in forms):
            forms.append((src["teacher"], DOC))
        if cy.get("teacher") and cy.get("teacher_formal") and cy["teacher"] != cy["teacher_formal"]:
            notes.append(f"course.yaml also has the informal form \"{cy['teacher']}\"; "
                         "teacher_formal is the name for the document")
        if forms:
            val, org = forms[0]
            if len(forms) > 1:
                val += f" (your document says {forms[1][0]})"
            confirm.append(("Teacher", val, org))
        else:
            missing.append(("Teacher", "never guessed; the name to print"))

    # Course-outline facts.
    if doc_type == "course_outline":
        if cy.get("department"):
            confirm.append(("Department", str(cy["department"]), YML))
        elif facts.get("subject"):
            confirm.append(("Department", facts["subject"], "[the curriculum subject, confirm the school's name for it]"))
        else:
            missing.append(("Department", "no course.yaml and no curriculum subject"))
        if cy.get("prerequisite"):
            confirm.append(("Prerequisite", str(cy["prerequisite"]), YML))
        elif facts.get("prerequisite"):
            confirm.append(("Prerequisite", facts["prerequisite"], IDX))
        else:
            missing.append(("Prerequisite", "not in course.yaml or the curriculum index"))
        if cy.get("curriculum_document"):
            confirm.append(("Curriculum document", str(cy["curriculum_document"]), YML))
        elif facts.get("subject"):
            year = f", issued {facts['year']}" if facts.get("year") else ""
            confirm.append(("Curriculum document", f"The Ontario Curriculum: {facts['subject']}{year}",
                            IDX + " (confirm the full title)"))
        else:
            missing.append(("Curriculum document", "the course is not in the bundled index"))
        confirm.append(("Developed By", SCHOOL, "[default, interview.md]"))
        today = today or dt.date.today()
        confirm.append(("Date Developed", today.strftime("%B %Y"), "[default: this month, interview.md]"))

    if doc_type == "long_range_plan" and ctype:
        confirm.append(("Pathway", ctype, t_origin))

    if doc_type == "course_outline":
        credit = cy.get("credit")
        hours = cy.get("hours")
        confirm.append(("Credit", str(credit if credit is not None else "1.0"),
                        YML if credit is not None else "[default, interview.md]"))
        confirm.append(("Hours", str(hours if hours is not None else 110),
                        YML if hours is not None else "[default, interview.md]"))

    # Strands.
    if doc_type == "unit" and facts.get("strands"):
        confirm.append(("Strands in the course", "; ".join(f"{k}. {v}" for k, v in facts["strands"].items()), IDX))

    # Assessment buckets and the exam split.
    if doc_type in ("course_outline", "long_range_plan", "exam_cover"):
        asmt = cy.get("assessment") if isinstance(cy.get("assessment"), dict) else {}
        band = "9-10" if grade in (9, 10) else ("11-12" if grade in (11, 12) else None)
        gs = BUCKETS.get(band)
        if doc_type in ("course_outline", "long_range_plan"):
            if all(k in asmt for k in ("classroom", "final_evaluation", "attendance")):
                val = f"classroom {asmt['classroom']}, final evaluation {asmt['final_evaluation']}, attendance {asmt['attendance']}"
                if gs and any(asmt[k] != gs[k] for k in gs):
                    val += (f" (the 2026 model for Grades {band} is {gs['classroom']}/"
                            f"{gs['final_evaluation']}/{gs['attendance']})")
                confirm.append(("Final-mark buckets", val, YML))
            elif gs:
                confirm.append(("Final-mark buckets",
                                f"classroom {gs['classroom']}, final evaluation {gs['final_evaluation']}, attendance {gs['attendance']}",
                                f"[2026 Growing Success, Grades {band}]"))
            else:
                missing.append(("Final-mark buckets", "the grade is unknown"))
        if code and m and grade:
            gs_path = find_growing_success(HERE, os.path.dirname(cy_path) if cy_path else None, cwd or os.getcwd())
            e, c, why = exam_split(code, grade, facts, gs_path)
            if "exam" in asmt and "culminating" in asmt:
                val = f"written exam {asmt['exam']}, culminating {asmt['culminating']}"
                if e is not None and (e, c) != (asmt["exam"], asmt["culminating"]):
                    val += f" (the subject matrix gives {e}/{c})"
                confirm.append(("Final evaluation split", val, YML))
            elif e is not None:
                val = (f"written exam {e}, culminating {c}" if e and c
                       else (f"written exam {e} only" if e else f"culminating {c} only"))
                if why:
                    val += f" ({why})"
                confirm.append(("Final evaluation split", val,
                                f"[Growing Success subject matrix, {facts.get('subject') or code}, Grades {band}]"))
            else:
                missing.append(("Final evaluation split (exam versus culminating)", why))
        if doc_type == "course_outline":
            confirm.append(("Achievement-chart weighting",
                            CHART_WEIGHTS.replace("Thinking", second, 1) if second != "Thinking" else CHART_WEIGHTS,
                            "[default, interview.md]"))

    # Dates found in the source.
    if src["dates"]:
        shown = [f"{lab}: {d}" if lab else d for lab, d in src["dates"][:8]]
        confirm.append(("Dates in your document", "; ".join(shown), DOC))

    # Facts only the teacher or the source can give.
    per_type = {
        "lesson": ["Unit", "Lesson N of M", "Duration", "Badge", "Phase names and minutes"],
        "weekly_plan": ["Unit", "Week N of M", "Dates of the week", "Duration per class"],
        "unit": ["Unit title and number", "Number of days", "Culminating task and its due point", "Core texts"],
        "course_outline": ["Unit list with hours (must total 110)"],
        "long_range_plan": ["Semester", "Unit start and end dates", "Evaluation titles and weights (must total 100)"],
        "exam_cover": ["Semester and exam period", "Month and year", "Exam date, time, room",
                       "Page count", "Category marks"],
    }[doc_type]
    if doc_type in ("weekly_plan",) and src["dates"]:
        per_type = [x for x in per_type if x != "Dates of the week"]
    for item in per_type:
        missing.append((item, "not determinable from the code or course.yaml"))
    return confirm, missing, notes


def render(doc_type, confirm, missing, notes):
    lines = [f"Prefill for {doc_type} (values the scripts could determine; the mapping adds the rest)", "",
             "A. Confirm (reply \"ok\" or correct any line)"]
    n = 0
    width = max((len(f"{l}: {v}") for l, v, _ in confirm), default=0)
    width = min(width, 70)
    for label, value, origin in confirm:
        n += 1
        text = f"{label}: {value}"
        lines.append(f"  {n}. {text.ljust(width)}  {origin}")
    lines += ["", "B. Missing candidates (drop any the source supplies; the rest become numbered gaps)"]
    for label, why in missing:
        n += 1
        lines.append(f"  {n}. {label}: {why}")
    if notes:
        lines += ["", "Notes:"] + [f"  - {x}" for x in notes]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", required=True, choices=TYPES)
    ap.add_argument("--code")
    ap.add_argument("--course-yaml")
    ap.add_argument("--source", help="extracted text (extract_text.py) or any file it can read")
    a = ap.parse_args()
    if a.course_yaml and not os.path.isfile(a.course_yaml):
        ap.error(f"no such file: {a.course_yaml}")
    text = None
    if a.source:
        import extract_text
        try:
            text = extract_text.extract(a.source)
        except extract_text.ExtractError as e:
            ap.error(str(e))
    confirm, missing, notes = prefill(a.type, a.code, a.course_yaml, text)
    sys.stdout.write(render(a.type, confirm, missing, notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())

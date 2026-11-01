#!/usr/bin/env python3
"""Build a Google Classroom rubric (CSV) and its Markdown twin from a JSON spec.

    python3 build_rubric.py SPEC.json [--out DIR] [--name STEM]
    python3 build_rubric.py --check RUBRIC.csv [--total N]
    python3 build_rubric.py --from-assignment DIR [--spec-out FILE]
    python3 build_rubric.py --import-csv RUBRIC.csv [--spec-out FILE]

In a GLA course repo, --from-assignment starts the spec from an assignment
folder: the name, total and bonus from instructions.md, the course and subject
from course.yaml, the house header (slot, expectations, marks), and the
criteria of an existing rubric.csv if there is one. Build it back into the
folder with --out DIR --name rubric to write rubric.csv and rubric.md.

The model writes only the words (criterion focus, description, five level
descriptors) and picks the assignment type. This script does everything
mechanical: the category split, rounding, level points, the second
category's name, the exact CSV format, the Markdown, and the checklist.

Spec (JSON):

    {
      "assignment": "Computer Buying Guide",        required
      "total": 20,                                  required, a multiple of 0.5
      "type": "programming",                        programming | research | creative | balanced | lab_report | essay
      "weights": {"ku": 25, "thinking": 30, ...},   optional, replaces the type's split (must total 100)
      "course": "ICS3U",                            optional; or "subject": "Science"
      "assessment_type": "Assignment",              optional, shown in the Markdown
      "house": {"slot": "...", "expectations": "...", "marks": "..."},   optional, course-repo header block
               (or "header_lines": [...] to keep a rubric's own header verbatim)
      "title": "...",                               optional H1 (house mode)
      "intro_md", "overview_note_md", "extra_md":   optional free Markdown before the overview, after it, after the criteria
      criteria[].note: "..."                        optional Markdown under that criterion's description
      "criteria": [                                 one per category, or fewer with combined categories
        {"category": "ku",                          ku | thinking | communication | application, or a list
         "focus": "Hardware Components",
         "description": "One or two sentences on what is assessed.",
         "points": 5,                               optional; if any criterion sets points, all must
         "levels": ["L4", "L3", "L2", "L1", "Below L1"]}
      ]
    }

Writes <Assignment_Name>_Rubric.csv and <Assignment_Name>_Rubric.md. Exit 0
written (warnings printed), 2 the spec is invalid. --check validates an
existing CSV and exits 1 on any structural fault.
Stdlib only: it ships inside the claude.ai bundle.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.realpath(__file__))
CATS = ("ku", "thinking", "communication", "application")
NAMES = {"ku": "Knowledge and Understanding", "thinking": "Thinking",
         "communication": "Communication", "application": "Application"}
SPLITS = {
    "programming": {"ku": 25, "thinking": 30, "communication": 20, "application": 25},
    "research":    {"ku": 27, "thinking": 27, "communication": 26, "application": 20},
    "creative":    {"ku": 20, "thinking": 25, "communication": 30, "application": 25},
    "balanced":    {"ku": 25, "thinking": 25, "communication": 25, "application": 25},
    "lab_report":  {"ku": 20, "thinking": 30, "communication": 25, "application": 25},
    "essay":       {"ku": 20, "thinking": 30, "communication": 30, "application": 20},
}
RATIOS = (Decimal("1"), Decimal("0.75"), Decimal("0.6"), Decimal("0.5"), Decimal("0.125"))
LEVEL_TITLES = ("High Degree of Effectiveness (Level 4)", "Considerable Effectiveness (Level 3)",
                "Some Effectiveness (Level 2)", "Limited Effectiveness (Level 1)", "Not Yet Demonstrated")
LEVEL_SHORT = ("Level 4", "Level 3", "Level 2", "Level 1", "Below Level 1")
HEADER = ("It is recommended that you do not edit rubrics in spreadsheet format", "v1.0-s")
SCIENCE_PREFIXES = ("SNC", "SBI", "SCH", "SPH", "SVN", "SES")
LEARNING_SKILLS = re.compile(r"\b(late(ness)?|on time|punctual\w*|attendance|effort|conduct|neatness|participation)\b", re.I)
ALIASES = {"k/u": "ku", "knowledge": "ku", "knowledge and understanding": "ku", "t": "thinking",
           "thinking and investigation": "thinking", "t/i": "thinking", "c": "communication", "a": "application"}


class SpecError(Exception):
    pass


def version():
    try:
        with open(os.path.join(HERE, "..", "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def thinking_name(course=None, subject=None):
    """Science names the second category Thinking and Investigation; every other subject says Thinking."""
    if subject and re.sub(r"[^a-z]", "", subject.lower()) in ("science", "scienceandtechnology"):
        return "Thinking and Investigation"
    if course and course.upper().startswith(SCIENCE_PREFIXES):
        return "Thinking and Investigation"
    return "Thinking"


def cat_key(v):
    k = str(v).strip().lower()
    k = ALIASES.get(k, k)
    if k not in CATS:
        raise SpecError("unknown category %r (use ku, thinking, communication, application)" % v)
    return k


def split(total, weights):
    """Category points in half-point units, preserving the total exactly
    (largest remainder; ties go to the higher weight, then K/U, T, C, A order),
    with at least 0.5 for every category."""
    units = int(Decimal(str(total)) * 2)
    raw = {c: Decimal(units) * Decimal(weights[c]) / Decimal(100) for c in CATS}
    got = {c: int(raw[c]) for c in CATS}
    order = sorted(CATS, key=lambda c: (-(raw[c] - got[c]), -weights[c], CATS.index(c)))
    for c in order[:units - sum(got.values())]:
        got[c] += 1
    for c in CATS:
        while got[c] < 1:
            donor = max(CATS, key=lambda x: (got[x], weights[x]))
            if got[donor] <= 1:
                raise SpecError("a total of %s is too small to give every category 0.5 points" % total)
            got[donor] -= 1
            got[c] += 1
    return {c: Decimal(got[c]) / 2 for c in CATS}


def num(d):
    """Decimal -> '2.4', '3', '0.5' (one decimal place at most, half-up)."""
    q = d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    return s[:-2] if s.endswith(".0") else s


def level_points(points):
    return [num(Decimal(str(points)) * r) for r in RATIOS]


def load_spec(spec):
    for k in ("assignment", "total", "criteria"):
        if k not in spec:
            raise SpecError("spec is missing %r" % k)
    if spec["total"] in (None, ""):
        raise SpecError("total is missing (the assignment's instructions have no **Marks:** or **Points:** number); set it in the spec")
    try:
        total = Decimal(str(spec["total"]))
    except ArithmeticError:
        raise SpecError("total %r is not a number" % spec["total"])
    if total <= 0 or (total * 2) % 1:
        raise SpecError("total must be a positive multiple of 0.5")
    weights = spec.get("weights")
    if weights:
        weights = {cat_key(k): v for k, v in weights.items()}
        if set(weights) != set(CATS) or sum(weights.values()) != 100:
            raise SpecError("weights must name all four categories and total 100")
    else:
        t = spec.get("type", "balanced")
        if t not in SPLITS:
            raise SpecError("type %r is not one of %s" % (t, ", ".join(SPLITS)))
        weights = SPLITS[t]
    crits = []
    for i, c in enumerate(spec["criteria"]):
        cats = c.get("category")
        cats = [cat_key(x) for x in (cats if isinstance(cats, list) else [cats])]
        levels = c.get("levels") or []
        if len(levels) != 5 or not all(str(x).strip() for x in levels):
            raise SpecError("criterion %d needs exactly five non-empty level descriptors (L4 to Below L1)" % (i + 1))
        if not str(c.get("focus", "")).strip() or not str(c.get("description", "")).strip():
            raise SpecError("criterion %d needs a focus and a description" % (i + 1))
        crits.append({"cats": cats, "focus": c["focus"].strip(), "description": " ".join(c["description"].split()),
                      "levels": [" ".join(str(x).split()) for x in levels], "points": c.get("points"),
                      "note": c.get("note") or ""})
    covered = {k for c in crits for k in c["cats"]}
    if covered != set(CATS):
        raise SpecError("every Ontario category must be assessed; missing: %s"
                        % ", ".join(NAMES[c] for c in CATS if c not in covered))
    given = [c["points"] is not None for c in crits]
    if any(given):
        if not all(given):
            raise SpecError("if any criterion sets points, every criterion must")
        for c in crits:
            c["points"] = Decimal(str(c["points"]))
        if sum(c["points"] for c in crits) != total:
            raise SpecError("criterion points total %s, not %s" % (sum(c["points"] for c in crits), total))
    else:
        if len(crits) != 4 or any(len(c["cats"]) != 1 for c in crits) or len({c["cats"][0] for c in crits}) != 4:
            raise SpecError("without explicit points, give one criterion per category (or set points on combined criteria)")
        pts = split(total, weights)
        for c in crits:
            c["points"] = pts[c["cats"][0]]
    return total, weights, crits


def title(crit, tname):
    names = [tname if k == "thinking" else NAMES[k] for k in crit["cats"]]
    return "%s - %s" % (" / ".join(names), crit["focus"])


def warnings(crits, spec):
    out = []
    for c in crits:
        for text in [c["description"]] + c["levels"]:
            m = LEARNING_SKILLS.search(text)
            if m:
                out.append("%r in %s marks a learning skill or work habit; Growing Success reports those separately"
                           % (m.group(0), c["focus"]))
            if "—" in text:
                out.append("em dash in %s; house style uses a comma or colon" % c["focus"])
        if not re.search(r"\byou(r)?\b", " ".join(c["levels"]), re.I):
            out.append("%s: descriptors should speak to the student ('you')" % c["focus"])
        if len(set(x.lower() for x in c["levels"])) < 5:
            out.append("%s: two levels share the same descriptor" % c["focus"])
    return out


def csv_text(spec, crits, tname):
    rows = [[HEADER[0]] + [""] * 6, [HEADER[1]] + [""] * 6]
    for c in crits:
        rows.append([title(c, tname)] + [""] * 6)
        rows.append([c["description"]] + [""] * 6)
        rows.append([""] + level_points(c["points"]) + [""])
        rows.append([""] + list(LEVEL_TITLES) + [""])
        rows.append([""] + c["levels"] + [""])
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerows(rows)
    return buf.getvalue().rstrip("\n")


def md_text(spec, crits, tname, total, csv_name=None):
    house = spec.get("house")
    if house:
        L = ["# %s" % (spec.get("title") or "%s: Assessment Rubric" % spec["assignment"]), ""]
        if house.get("header_lines"):
            L += list(house["header_lines"])
        else:
            L += ["**Slot:** %s · **Type:** %s rubric (reference copy of `%s`)" % (
                      house.get("slot", ""), spec.get("assessment_type", "assignment").lower(), csv_name or "rubric.csv"),
                  "**Marks:** %s" % house.get("marks", num(total))]
            if house.get("expectations"):
                L.insert(-1, "**Expectations:** %s" % house["expectations"])
        L += ["", "This is the human-readable copy of `%s` (the Google Classroom import file). Both are built from one spec "
              "by gc-rubric's `build_rubric.py`; rebuild them together, never edit one alone." % (csv_name or "rubric.csv"), ""]
        if spec.get("intro_md"):
            L += [spec["intro_md"].strip(), ""]
        L += ["## Rubric Overview", "", "| Category | Criterion | Points |", "|----------|-----------|--------|"]
    else:
        L = ["# %s - Assessment Rubric" % spec["assignment"], ""]
        if spec.get("course"):
            L.append("**Course:** %s" % spec["course"])
        L += ["**Total Points:** %s" % num(total), "**Assessment Type:** %s" % spec.get("assessment_type", "Assignment"), "",
              "## Rubric Overview", "", "| Category | Criterion | Points |", "|----------|-----------|--------|"]
    for c in crits:
        L.append("| %s | %s | %s |" % (" / ".join(tname if k == "thinking" else NAMES[k] for k in c["cats"]), c["focus"], num(c["points"])))
    L += ["| **Total** | | **%s** |" % num(total), ""]
    if spec.get("overview_note_md"):
        L += [spec["overview_note_md"].strip(), ""]
    L += ["## Detailed Criteria", ""]
    for c in crits:
        L += ["### %s (%s points)" % (title(c, tname), num(c["points"])), "", c["description"], ""]
        if c.get("note"):
            L += [c["note"].strip(), ""]
        L += ["| Level | Points | Descriptor |", "|-------|--------|------------|"]
        for name, pts, desc in zip(LEVEL_SHORT, level_points(c["points"]), c["levels"]):
            L.append("| %s | %s | %s |" % (name, pts, desc.replace("|", "/")))
        L.append("")
    if spec.get("extra_md"):
        L += [spec["extra_md"].strip(), ""]
    L += ["---", "", "*Rubric aligned with Ontario Growing Success assessment framework. gc-rubric %s.*" % version(),
          "*Level 3 represents the provincial standard.*"]
    return "\n".join(L) + "\n"


def check_csv(path, total=None):
    """Structural faults in an existing Google Classroom rubric CSV."""
    with open(path, "rb") as f:
        raw = f.read()
    faults = []
    if raw.startswith(b"\xef\xbb\xbf"):
        faults.append("file starts with a byte order mark")
    if b"\r\n" in raw:
        faults.append("CRLF line endings (use LF)")
    if raw.endswith(b"\n"):
        faults.append("trailing newline after the last row")
    text = raw.decode("utf-8-sig")
    lines = text.split("\n")
    for k, line in enumerate(lines, 1):
        if line and not (line.startswith('"') and line.endswith('"')):
            faults.append("row %d: every cell must be double-quoted" % k)
    rows = list(csv.reader(io.StringIO(text)))
    for k, r in enumerate(rows, 1):
        if len(r) != 7:
            faults.append("row %d has %d columns, not 7" % (k, len(r)))
        elif r[6] != "":
            faults.append("row %d: the 7th column must be empty" % k)
    if len(rows) < 2 or rows[0][0] != HEADER[0] or rows[1][0] != HEADER[1]:
        faults.append("the two header rows are missing or altered")
    body = rows[2:]
    if len(body) % 5:
        faults.append("%d criterion rows is not a multiple of 5" % len(body))
    l4 = Decimal(0)
    for i in range(0, len(body) - len(body) % 5, 5):
        name = body[i][0] if body[i] else "?"
        if body[i + 3][1:6] != list(LEVEL_TITLES):
            faults.append("%s: level titles row is not the exact five strings" % name)
        try:
            pts = [Decimal(x) for x in body[i + 2][1:6]]
        except Exception:
            faults.append("%s: point row has a non-number" % name)
            continue
        l4 += pts[0]
        long = [x for x in body[i + 2][1:6] if "." in x and len(x.split(".")[1]) > 1]
        if long:
            faults.append("%s: points %s have more than one decimal place" % (name, ", ".join(long)))
        want = level_points(pts[0])
        if [num(p) for p in pts] != want:
            faults.append("%s: points %s do not follow 100/75/60/50/12.5%% of %s (expected %s)"
                          % (name, [num(p) for p in pts], num(pts[0]), want))
        if any(not x.strip() for x in body[i + 4][1:6]):
            faults.append("%s: a level descriptor is empty" % name)
    if total is not None and l4 != Decimal(str(total)):
        faults.append("Level 4 points total %s, not %s" % (num(l4), total))
    return faults


def build(spec, out_dir, name=None):
    total, weights, crits = load_spec(spec)
    tname = thinking_name(spec.get("course"), spec.get("subject"))
    stem = name or (re.sub(r"[^\w-]+", "_", spec["assignment"].strip()).strip("_") + "_Rubric")
    csv_path = os.path.join(out_dir, stem + ".csv")
    md_path = os.path.join(out_dir, stem + ".md")
    os.makedirs(out_dir, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_text(spec, crits, tname))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text(spec, crits, tname, total, os.path.basename(csv_path)))
    faults = check_csv(csv_path, total)
    if faults:
        raise RuntimeError("generated CSV failed its own check: %s" % "; ".join(faults))
    return csv_path, md_path, crits, warnings(crits, spec)


TITLE_RE = re.compile(r"^(?P<cats>.+?) - (?P<focus>.+)$")
NAME_TO_KEY = {"knowledge and understanding": "ku", "thinking": "thinking", "thinking and investigation": "thinking",
               "communication": "communication", "application": "application"}


def import_csv(path):
    """An existing Google Classroom rubric CSV as spec criteria (points from Level 4)."""
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    body, crits = rows[2:], []
    for i in range(0, len(body) - len(body) % 5, 5):
        m = TITLE_RE.match(body[i][0].strip())
        if not m:
            raise SpecError("%s: criterion title %r is not '<Category> - <Focus>'" % (path, body[i][0]))
        cats = [NAME_TO_KEY.get(x.strip().lower()) for x in m.group("cats").split("/")]
        if None in cats:
            raise SpecError("%s: unknown category in %r" % (path, body[i][0]))
        focus = re.sub(r"\s*\(\d+(\.\d+)? points?\)$", "", m.group("focus").strip())
        crits.append({"category": cats if len(cats) > 1 else cats[0], "focus": focus,
                      "description": body[i + 1][0].strip(), "points": float(body[i + 2][1]),
                      "levels": [x.strip() for x in body[i + 4][1:6]]})
    return crits


def _course_info(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, "course.yaml")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                text = f.read()
            get = lambda k: (re.search(r"^%s:\s*\"?([^\"#\n]+?)\"?\s*(#.*)?$" % k, text, re.M) or [None, ""])[1]  # noqa: E731
            return get("code"), get("department")
        if os.path.dirname(d) == d:
            return "", ""
        d = os.path.dirname(d)


def from_assignment(folder):
    """A starting spec for an assignment folder in a GLA course repo."""
    inst = next((os.path.join(folder, n) for n in ("instructions.md", "assignment_instructions.md")
                 if os.path.exists(os.path.join(folder, n))), None)
    if not inst:
        raise SpecError("%s has no instructions.md or assignment_instructions.md" % folder)
    with open(inst, encoding="utf-8") as f:
        text = f.read()
    title = re.search(r"^# (?:Assignment|Culminating Project)?:?\s*(.+)$", text, re.M)
    field = lambda k: (re.search(r"^\*\*%s:\*\*\s*(.+?)\s*(?:·|$)" % k, text, re.M) or [None, ""])[1]  # noqa: E731
    marks_line = (re.search(r"^\*\*(?:Marks|Points|Worth):\*\*\s*(.+)$", text, re.M) or [None, ""])[1].split("·")[0].strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:points?)?", marks_line)
    slot_line = (re.search(r"^\*\*Slot:\*\*\s*(.+?)\s*(?:·\s*\*\*|$)", text, re.M) or [None, ""])[1]
    slot = re.sub(r"\s*\([^)]*\)", "", slot_line).strip()   # ICD2O writes "handed out X · due Y" inside the slot
    code, dept = _course_info(folder)
    spec = {"assignment": title.group(1).strip() if title else os.path.basename(folder.rstrip("/")),
            "total": float(m.group(1)) if m else None,
            "course": code, "subject": dept, "assessment_type": "Assignment",
            "house": {"slot": slot, "expectations": field("Expectations"), "marks": marks_line}}
    existing = os.path.join(folder, "rubric.csv")
    if os.path.exists(existing):
        spec["criteria"] = import_csv(existing)
        spec["_note"] = "criteria imported from rubric.csv; edit the words, keep or change the points, then build"
    else:
        spec["type"] = "programming" if dept.lower() == "computer studies" else "balanced"
        spec["criteria"] = [{"category": c, "focus": "", "description": "", "levels": ["", "", "", "", ""]} for c in CATS]
        spec["_note"] = "fill focus, description and the five level descriptors for each category, then build"
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out", default=".")
    ap.add_argument("--check")
    ap.add_argument("--total")
    ap.add_argument("--name", help="output file stem, e.g. rubric (default <Assignment>_Rubric)")
    ap.add_argument("--from-assignment", dest="from_assignment")
    ap.add_argument("--import-csv", dest="import_csv")
    ap.add_argument("--spec-out", dest="spec_out")
    a = ap.parse_args(argv)
    if a.from_assignment or a.import_csv:
        try:
            out = from_assignment(a.from_assignment) if a.from_assignment else {"criteria": import_csv(a.import_csv)}
        except SpecError as e:
            print("SPEC ERROR: %s" % e)
            return 2
        text = json.dumps(out, indent=2, ensure_ascii=False)
        if a.spec_out:
            with open(a.spec_out, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            print("wrote %s" % a.spec_out)
        else:
            print(text)
        return 0
    if a.check:
        faults = check_csv(a.check, a.total)
        print("\n".join(faults) if faults else "clean")
        return 1 if faults else 0
    if not a.spec:
        ap.error("give a SPEC.json or --check RUBRIC.csv")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    try:
        csv_path, md_path, crits, warns = build(spec, a.out, a.name)
    except SpecError as e:
        print("SPEC ERROR: %s" % e)
        return 2
    print("wrote %s" % csv_path)
    print("wrote %s" % md_path)
    print("points: %s" % ", ".join("%s %s" % ("/".join(c["cats"]), num(c["points"])) for c in crits))
    for w in warns:
        print("WARN: " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Scaffold a unit's assignment or unit test: correctly named, correctly headed starting files.

    python3 scaffold_assessment.py U2 assignment [--name Creature_Clinic] [--root COURSE_ROOT] [--dry-run]
    python3 scaffold_assessment.py U2 test [--root COURSE_ROOT] [--dry-run]

Reads course.yaml, the unit's unit_overview.md (## Evaluations, the week
tables, the hand-out note), the Curriculum_Coverage_Map.md, the curriculum,
the Assessment_Plan.md and the course's other units' assessments, then writes
into master/02_Units/U<n>_*/Assessment/:

  Assignment_<Name>/instructions.md    from Standards/templates/Assignment_Template.md
  Assignment_<Name>/marking_notes.md   teacher-only notes in the course's form
  Test/test.md                         from Test_Template.md
  Test/test_KEY.md                     teacher key
  Test/coverage_table.md               header and the empty question table
  Test/review_sheet.md                 student review for the review day
  Test/test_reference.md               from Test_Reference_Template.md

Header forms follow the course's other units (ICD2O writes **Points:** and a
**Window:**; ICS3U and ICS4U write **Marks:** ... points (Google Classroom
rubric)). Bodies stay as placeholders for the model to write. Existing files
are never overwritten. The rubric is not created; the gc-rubric commands are
printed instead.
"""
import argparse
import glob
import math
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
import yaml  # noqa: E402,F401  (PyYAML is the library's dependency; course.load needs it)

from gla import course, curriculum, mdtable, paths, slots  # noqa: E402

TEMPLATES = os.path.join(paths.STANDARDS, "templates")
BUILD_RUBRIC = os.path.join(paths.SKILLS, "gc-rubric", "scripts", "build_rubric.py")

CODE_RE = re.compile(r"\b[A-Z]\d+\.\d+\b")
CODE_RANGE = re.compile(r"\b([A-Z])(\d+)\.(\d+)\s*[–-]\s*(?:([A-Z])(\d+)\.)?(\d+)\b")
FIELD_RE = re.compile(r"\*\*([^*]+?):\*\*\s*(.*?)(?=\s*·\s*\*\*|$)")
UNIT_ITEM = re.compile(r"(?<![\w./])((?:U\d+\s*/\s*)*U\d+)\s+(assignments?|tests?)\b", re.I)
EVERY_ITEM = re.compile(r"\bevery\s+(?:later\s+)?(assignment|test)", re.I)
PLACE_TOTAL, PLACE_BONUS, PLACE_MARKS = "<total>", "<n>", "<marks>"


# ------------------------------------------------------------------ small helpers
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def codes_in(text):
    """Expectation codes mentioned in text, ranges expanded (A4.1–A4.5), in order, unique."""
    found = []
    for m in CODE_RANGE.finditer(text or ""):
        l1, o1, a, l2, o2, b = m.groups()
        if (l2 or l1) == l1 and (o2 or o1) == o1 and int(a) < int(b) <= int(a) + 20:
            found += ["%s%s.%d" % (l1, o1, k) for k in range(int(a), int(b) + 1)]
    found += CODE_RE.findall(text or "")
    return list(dict.fromkeys(found))


def header_fields(text, lines=8):
    """{field: value} from the bold header lines at the top of a file (first value wins)."""
    out = {}
    for line in (text or "").splitlines()[:lines]:
        if line.startswith("**"):
            for k, v in FIELD_RE.findall(line):
                out.setdefault(k.strip(), v.strip())
    return out


def after_header(tpl):
    """Template text after its title and bold header block."""
    lines = tpl.splitlines(True)
    i = 0
    while i < len(lines) and (lines[i].startswith("# ") or not lines[i].strip() or lines[i].startswith("**")):
        i += 1
    return "".join(lines[i:])


def spaced(token):
    return token.replace("_", " ")


def num(x):
    return ("%g" % x) if isinstance(x, float) else str(x)


def majority(values, default, least=1):
    """The most common value, or default when there is none, the top two tie, or it occurs fewer than least times."""
    c = Counter(v for v in values if v)
    if not c:
        return default
    top = c.most_common(2)
    if (len(top) > 1 and top[0][1] == top[1][1]) or top[0][1] < least:
        return default
    return top[0][0]


def weeks_phrase(n, per_week=5):
    """7 -> '≈ 1.5 weeks', 8 -> '≈ 1.5–2 weeks', 10 -> '≈ 2 weeks' (the courses' existing wording)."""
    w = n / float(per_week)
    near = math.floor(w * 2 + 0.5) / 2
    if near <= 0:
        return ""
    fmt = lambda x: ("%g" % x)  # noqa: E731
    if w <= near + 1e-9:
        return "≈ %s week%s" % (fmt(near), "" if near == 1 else "s")
    return "≈ %s–%s weeks" % (fmt(near), fmt(near + 0.5))


def parse_points(value):
    """'20 points (Google Classroom rubric) + up to 2 bonus' or '20 (+ up to 2 bonus)' -> (20, 2)."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)", value or "")
    if not m:
        return None, None
    b = re.search(r"up to\s*\+?\s*(\d+(?:\.\d+)?)\s*bonus", value)
    pts = float(m.group(1))
    pts = int(pts) if pts.is_integer() else pts
    bonus = None
    if b:
        bonus = float(b.group(1))
        bonus = int(bonus) if bonus.is_integer() else bonus
    return pts, bonus


def coverage_rows(path):
    """[(code, assessed_cell, line)] from every Code table of the coverage map."""
    if not os.path.exists(path):
        return []
    rows = []
    for hdr, body, _ in mdtable.tables(read(path)):
        if not hdr or hdr[0].strip().lower() != "code":
            continue
        try:
            ai = mdtable.column(hdr, "assessed")
        except KeyError:
            continue
        for line, c in body:
            code = c[0].strip()
            if CODE_RE.fullmatch(code) and ai < len(c):
                rows.append((code, c[ai], line))
    return rows


def names_item(cell, unit, kind, item_name=None):
    """True when an 'Assessed in' cell names this unit's assignment or test:
    'U2 assignment', 'U2 Test (Part A)', 'U2/U3/U5 assignment rubric rows', 'Assignment_Creature_Clinic', 'Unit 2 Test'."""
    for m in UNIT_ITEM.finditer(cell or ""):
        units = [u.strip() for u in m.group(1).split("/")]
        if unit in units and m.group(2).lower().startswith(kind):
            return True
    if kind == "assignment" and item_name and re.search(r"(?<![\w])%s(?![\w])" % re.escape(item_name), cell or ""):
        return True
    if kind == "test" and re.search(r"\bUnit\s+%s\s+Test\b" % re.escape(unit[1:]), cell or "", re.I):
        return True
    return False


# ------------------------------------------------------------------ scaffold
class Scaffolder:
    def __init__(self, root, unit, kind, name=None, dry_run=False, out=sys.stdout):
        self.root = os.path.abspath(root)
        self.unit = unit
        self.kind = kind
        self.name = name
        self.dry = dry_run
        self.out = out
        self.created, self.skipped, self.notes, self.unresolved = [], [], [], []
        self.sources = []          # (what, value, from)
        self.codes_report = []

    def say(self, *a):
        print(*a, file=self.out)

    # -- inputs
    def load(self):
        if not re.fullmatch(r"U\d+", self.unit or ""):
            raise SystemExit("ERROR: unit must look like U2 (got %r)" % self.unit)
        if self.kind not in ("assignment", "test"):
            raise SystemExit("ERROR: kind must be assignment or test (got %r)" % self.kind)
        self.cfg = course.load(self.root)
        units = sorted(u for u in glob.glob(os.path.join(self.root, "master", "02_Units", "%s_*" % self.unit)) if os.path.isdir(u))
        if not units:
            raise SystemExit("ERROR: no master/02_Units/%s_*/ folder" % self.unit)
        self.unit_dir = units[0]
        ov = os.path.join(self.unit_dir, "unit_overview.md")
        if not os.path.exists(ov):
            raise SystemExit("ERROR: %s has no unit_overview.md" % self.unit_dir)
        self.ov_path = ov
        self.overview = read(ov)
        h1 = re.search(r"^# (.+)$", self.overview, re.M)
        title = h1.group(1).strip() if h1 else ""
        self.unit_name = title.split(":", 1)[1].strip() if ":" in title else title
        self.unit_n = self.unit[1:]
        wk = re.search(r"\*\*Weeks:\*\*[^\n]*?–\s*%s\.W\d+\.D(\d+)" % re.escape(self.unit), self.overview)
        self.per_week = int(wk.group(1)) if wk else 5
        self.assess_dir = os.path.join(self.unit_dir, "Assessment")
        self.evals = self.read_evaluations()
        self.week_rows = self.read_week_rows()
        try:
            self.cur = curriculum.load(self.cfg["code"])
            self.order = {c: i for i, c in enumerate(self.cur.specific_codes())}
        except (KeyError, FileNotFoundError):
            self.cur, self.order = None, {}
            self.unresolved.append("no curriculum data for %s; codes are not checked" % self.cfg.get("code"))
        self.cov_path = os.path.join(self.root, "master", "01_Standards", "Curriculum_Coverage_Map.md")
        self.cov = coverage_rows(self.cov_path)
        if not self.cov:
            self.unresolved.append("no Code tables with an Assessed in column in master/01_Standards/Curriculum_Coverage_Map.md")
        plan = os.path.join(self.root, "master", "00_Admin", "Assessment_Plan.md")
        self.plan_text = read(plan) if os.path.exists(plan) else ""
        m = re.search(r"^## Marking schemes.*?(?=^## |\Z)", self.plan_text, re.M | re.S)
        self.schemes = m.group(0) if m else ""
        self.sibling_dirs = [d for d in sorted(glob.glob(os.path.join(self.root, "master", "02_Units", "*", "Assessment")))
                             if os.path.dirname(d) != self.unit_dir]
        subject = (self.cur.subject if self.cur else "") or self.cfg.get("department", "")
        self.thinking = curriculum.thinking_name(subject)

    def read_evaluations(self):
        t = mdtable.find_table(self.overview, "item", "kind", "handed out", "due")
        out = []
        if not t:
            self.unresolved.append("unit_overview.md has no | Item | Kind | Handed out | Due | Weight | table")
            return out
        hdr, rows, _ = t
        ii, ki, hi, di = (mdtable.column(hdr, x) for x in ("item", "kind", "handed out", "due"))
        for line, c in rows:
            get = lambda k: c[k].strip() if k < len(c) else ""  # noqa: E731
            item = re.sub(r"[*`]", "", get(ii)).strip()
            if not item:
                continue
            h, d = slots.find_all(get(hi)), slots.find_all(get(di))
            out.append({"item": item, "kind": get(ki).lower(), "handed": h[0] if h else None,
                        "due": d[0] if d else None, "line": line})
        return out

    def read_week_rows(self):
        rows = []
        for hdr, body, _ in mdtable.tables(self.overview):
            low = [h.lower() for h in hdr]
            if not ({"slot", "type", "topic"} <= set(low)):
                continue
            si, ti, pi = low.index("slot"), low.index("type"), low.index("topic")
            for _, c in body:
                if si < len(c) and slots.is_slot(c[si].strip()):
                    rows.append({"slot": c[si].strip(), "type": c[ti].strip().lower() if ti < len(c) else "",
                                 "topic": c[pi] if pi < len(c) else ""})
        return rows

    def real(self, codes, where):
        if not self.order:
            return list(codes)
        bad = [c for c in codes if c not in self.order]
        if bad:
            self.unresolved.append("%s: %s not in the %s curriculum, dropped" % (where, ", ".join(bad), self.cfg["code"]))
        return [c for c in codes if c in self.order]

    def sort(self, codes):
        return sorted(set(codes), key=lambda c: self.order.get(c, 10 ** 6))

    def siblings(self, pattern):
        """[(unit folder name, path)] for a file pattern under the other units' Assessment folders."""
        out = []
        for d in self.sibling_dirs:
            for p in sorted(glob.glob(os.path.join(d, pattern))):
                out.append((os.path.basename(os.path.dirname(d)).split("_")[0], p))
        return out

    def sibling_fields(self, pattern):
        return [(u, p, header_fields(read(p))) for u, p in self.siblings(pattern)]

    # -- codes
    def find_codes(self, item_name=None):
        label = "%s %s" % (self.unit, self.kind)
        picked, every = [], []
        for code, cell, line in self.cov:
            ev = EVERY_ITEM.search(cell)
            if names_item(cell, self.unit, self.kind, item_name):
                picked.append(code)
            elif ev and ev.group(1).lower() == self.kind and not self.before_later(ev.group(0), cell):
                every.append("%s ('%s')" % (code, ev.group(0)))
        codes = self.sort(self.real(picked, "coverage map"))
        src = "coverage map rows whose Assessed in names %s%s" % (label, " or " + item_name if item_name else "")
        if every:
            self.notes.append("coverage map's Assessed in names %s without a unit: %s; not added, add by hand if this %s carries it"
                              % ("every " + self.kind, ", ".join(every), self.kind))
        if not codes:
            self.unresolved.append("no coverage-map row names %s; **Expectations:** left as <codes>" % label)
        return codes, src

    def before_later(self, phrase, cell):
        """True for 'every later test' in a cell that names a unit at or after this one."""
        if "later" not in phrase.lower():
            return False
        named = [int(u) for u in re.findall(r"(?<![\w.])U(\d+)\b", cell)]
        return bool(named) and int(self.unit_n) <= max(named)

    def compare_overview_codes(self, codes, which, text, where, elsewhere=()):
        listed = self.real(codes_in(text), where) if text else []
        if not listed:
            return
        missing = sorted(set(listed) - set(codes) - set(elsewhere))
        extra = sorted(set(codes) - set(listed))
        if missing or extra:
            parts = []
            if missing:
                parts.append("in %s but no coverage-map row names the %s: %s" % (which, self.kind, ", ".join(self.sort(missing))))
            if extra:
                parts.append("named by the coverage map but not in %s: %s" % (which, ", ".join(self.sort(extra))))
            self.notes.append("; ".join(parts))

    # -- marks
    def assignment_marks(self, own_dir):
        for name in ("instructions.md", "marking_notes.md"):
            p = os.path.join(own_dir, name)
            if os.path.exists(p):
                f = header_fields(read(p))
                pts, bonus = parse_points(f.get("Points") or f.get("Marks"))
                if pts is not None:
                    return pts, bonus, "this assignment's existing %s" % name
        m = re.search(r"\bassignments?\b[^.\n]*?\b(?:are|is|out of|worth|carr(?:y|ies))\s+(\d+)\s+points", self.schemes, re.I)
        if m:
            return int(m.group(1)), None, "Assessment_Plan.md ## Marking schemes"
        seen = {}
        for u, p, f in self.sibling_fields("Assignment_*/instructions.md"):
            pts, bonus = parse_points(f.get("Points") or f.get("Marks"))
            if pts is not None:
                seen[u] = (pts, bonus)
        vals = set(seen.values())
        if len(vals) == 1:
            pts, bonus = vals.pop()
            return pts, bonus, "the course's other assignments (%s, all %s%s)" % (
                ", ".join(sorted(seen)), num(pts), " + %s bonus" % num(bonus) if bonus is not None else "")
        if vals:
            self.unresolved.append("other assignments disagree on points (%s); header left as %s"
                                   % (", ".join("%s %s" % (u, num(v[0])) for u, v in sorted(seen.items())), PLACE_TOTAL))
        else:
            self.unresolved.append("no assignment points found in the Assessment Plan or other units; header left as %s" % PLACE_TOTAL)
        return None, None, "not found"

    def bonus_for(self, pts, bonus, src):
        if bonus is not None:
            return bonus, src
        if pts is not None and re.search(r"up to 10% of (?:the assignment's|its) points", self.schemes):
            b = pts / 10.0
            return (int(b) if b.is_integer() else b), "10% of the points, per Assessment_Plan.md stretch-goal rule"
        self.unresolved.append("bonus not found; header left as up to %s bonus" % PLACE_BONUS)
        return None, "not found"

    def test_marks(self, own_dir):
        for name in ("test.md", "test_KEY.md", "coverage_table.md"):
            p = os.path.join(own_dir, name)
            if os.path.exists(p):
                m = re.match(r"(\d+)", header_fields(read(p)).get("Marks", ""))
                if m:
                    return int(m.group(1)), "this test's existing %s" % name
        u = re.search(r"\(([^)]*\bUnit\s+%s:\s*(\d+)\s+marks[^)]*)\)" % self.unit[1:], self.schemes)
        if u:
            return int(u.group(2)), "Assessment_Plan.md ## Marking schemes (Unit %s exception)" % self.unit[1:]
        m = re.search(r"\btests?\b[^.\n]*?\b(?:are|is|out of|worth)\s+(\d+)\s+marks", self.schemes, re.I)
        if m:
            return int(m.group(1)), "Assessment_Plan.md ## Marking schemes"
        seen = {}
        for u, p, f in self.sibling_fields("Test/test.md"):
            m = re.match(r"(\d+)", f.get("Marks", ""))
            if m:
                seen[u] = int(m.group(1))
        vals = set(seen.values())
        if len(vals) == 1:
            v = vals.pop()
            self.length_note(sorted(seen), "test marks")
            return v, "the course's other unit tests (%s, all %d)" % (", ".join(sorted(seen)), v)
        if vals:
            self.unresolved.append("other unit tests disagree on marks (%s); header left as %s"
                                   % (", ".join("%s %d" % kv for kv in sorted(seen.items())), PLACE_MARKS))
        else:
            self.unresolved.append("no test marks found in the Assessment Plan or other units; header left as %s" % PLACE_MARKS)
        return None, "not found"

    def unit_weeks(self, unit_dir):
        p = os.path.join(unit_dir, "unit_overview.md")
        m = re.search(r"\*\*Weeks:\*\*\s*(\d+)", read(p)) if os.path.exists(p) else None
        return int(m.group(1)) if m else None

    def length_note(self, units, what):
        """A note when the units the value was read from are all a different length from this one."""
        mine = self.unit_weeks(self.unit_dir)
        theirs = {}
        for d in self.sibling_dirs:
            u = os.path.basename(os.path.dirname(d)).split("_")[0]
            if u in units:
                theirs[u] = self.unit_weeks(os.path.dirname(d))
        if mine and theirs and mine not in theirs.values():
            self.notes.append("%s taken from %s, which run %s weeks; this unit runs %d, so check the total"
                              % (what, ", ".join(sorted(theirs)), "/".join(str(w) for w in sorted(set(v for v in theirs.values() if v))), mine))

    def test_minutes(self):
        m = re.search(r"\*\*Tests:\*\*[^\n]*?(\d+)\s*minutes", self.schemes)
        if m:
            return int(m.group(1)), "Assessment_Plan.md **Tests:**"
        return 50, "Test_Template.md default"

    # -- slots
    def school_days(self, h, d):
        try:
            bh, wh, dh = slots.parse(h)
            bd, wd, dd = slots.parse(d)
        except ValueError:
            return None
        if bh != bd or not (wh and wd) or wh == "S" or wd == "S":
            return None
        return (int(wd[1:]) - int(wh[1:])) * self.per_week + (dd - dh)

    def pick(self, kind):
        if kind == "assignment":
            rows = [e for e in self.evals if e["item"].startswith("Assignment_") or e["kind"].startswith("assignment")]
        else:
            rows = [e for e in self.evals if e["kind"].startswith("test") or re.fullmatch(r"Unit\s+\d+\s+Test", e["item"], re.I)]
        return rows

    # -- plans
    def plan_assignment(self):
        rows = self.pick("assignment")
        if self.name:
            token = re.sub(r"^Assignment_", "", self.name.strip())
            match = [e for e in rows if e["item"] == "Assignment_" + token]
            if not match:
                self.unresolved.append("--name %s: no Assignment_%s row in the overview's ## Evaluations; slots left as U_.W_.D_"
                                       % (self.name, token))
            row = match[0] if match else None
            self.name_src = "--name"
        else:
            if not rows:
                raise SystemExit("ERROR: %s has no assignment row in its ## Evaluations table (%s); nothing to scaffold. "
                                 "Add the row, or pass --name to scaffold one anyway." % (self.unit, os.path.relpath(self.ov_path, self.root)))
            if len(rows) > 1:
                raise SystemExit("ERROR: %s lists %d assignments in ## Evaluations (%s); pass --name to pick one."
                                 % (self.unit, len(rows), ", ".join(e["item"] for e in rows)))
            row = rows[0]
            token = re.sub(r"^Assignment_", "", row["item"])
            if not row["item"].startswith("Assignment_"):
                token = re.sub(r"\W+", "_", token).strip("_")
                self.notes.append("assignment row %r has no Assignment_ prefix; folder named Assignment_%s" % (row["item"], token))
            self.name_src = "unit_overview ## Evaluations"
        self.token = token
        self.item = "Assignment_" + token
        self.title = spaced(token)
        self.dir = os.path.join(self.assess_dir, self.item)
        self.handed = row["handed"] if row else None
        self.due = row["due"] if row else None
        if row:
            self.sources.append(("slots", "handed out %s, due %s" % (self.handed or "?", self.due or "?"),
                                 "unit_overview ## Evaluations, line %d" % row["line"]))
        if not (self.handed and self.due):
            self.unresolved.append("hand-out or due slot not found; left as U_.W_.D_")

        # the overview's hand-out note: slots and the day count
        self.days, days_src = None, None
        note = next((ln for ln in self.overview.splitlines() if "`%s`" % self.item in ln and ln.startswith("**Assignment")), "")
        if note:
            ns = slots.find_all(note)
            if len(ns) >= 2 and (ns[0], ns[1]) != (self.handed, self.due):
                self.notes.append("overview hand-out note says %s to %s; ## Evaluations says %s to %s (Evaluations used)"
                                  % (ns[0], ns[1], self.handed, self.due))
            m = re.search(r"\((\d+)\s+(?:class|school)\s+days", note)
            if m:
                self.days, days_src = int(m.group(1)), "unit_overview hand-out note"
        computed = self.school_days(self.handed, self.due) if (self.handed and self.due) else None
        if self.days is None and computed is not None:
            self.days, days_src = computed, "slot arithmetic (%d days a week)" % self.per_week
        elif self.days is not None and computed is not None and computed != self.days:
            self.notes.append("hand-out note says %d class days; the slots give %d school days (%d a week); the note's %d is used"
                              % (self.days, computed, self.per_week, self.days))
        if self.days is None:
            self.unresolved.append("window length not found; left as <n> school days")
        else:
            self.sources.append(("window", "%d school days" % self.days, days_src))

        self.codes, csrc = self.find_codes(self.item)
        self.codes_report.append(("instructions.md, marking_notes.md", self.codes, csrc))
        self.compare_overview_codes(self.codes, "the overview hand-out note's Covers list",
                                    (re.search(r"Covers\s+([^.]*)", note) or [None, ""])[1] if note else "", "hand-out note")

        pts, bonus, psrc = self.assignment_marks(self.dir)
        bonus, bsrc = self.bonus_for(pts, bonus, psrc)
        self.points, self.bonus = pts, bonus
        self.sources.append(("points", "%s + up to %s bonus" % (num(pts) if pts is not None else PLACE_TOTAL,
                                                                  num(bonus) if bonus is not None else PLACE_BONUS),
                             psrc if bsrc == psrc else "%s; bonus from %s" % (psrc, bsrc)))

        # header forms, read off the course's other assignments
        inst = self.sibling_fields("Assignment_*/instructions.md")
        self.points_form = majority(["points" if "Points" in f else "marks" for _, _, f in inst], "marks")
        mn = [(u, p, read(p)) for u, p in self.siblings("Assignment_*/marking_notes.md")]
        self.notes_form = majority(["anchors" if "**Batch strategy:**" in t[:600] else "header" for _, _, t in mn], "header")
        slot_vals = [header_fields(t).get("Slot", "") for _, _, t in mn]
        self.notes_handed = majority(["handed" if s.startswith("handed out") else "due" for s in slot_vals if s], "due") == "handed"
        self.sources.append(("form", "%s header, %s marking notes" % ("**Points:** + **Window:**" if self.points_form == "points"
                                                                        else "**Marks:** ... points (Google Classroom rubric)",
                                                                        "batch strategy + level anchors" if self.notes_form == "anchors"
                                                                        else "slot/expectations/marks header"),
                             "the course's other assignments (%d)" % len(inst) if inst else "Assignment_Template.md (no other assignments)"))

    def plan_test(self):
        rows = self.pick("test")
        if not rows:
            raise SystemExit("ERROR: %s has no test row in its ## Evaluations table (%s); nothing to scaffold."
                             % (self.unit, os.path.relpath(self.ov_path, self.root)))
        if len(rows) > 1:
            raise SystemExit("ERROR: %s lists %d tests in ## Evaluations (%s); scaffold by hand."
                             % (self.unit, len(rows), ", ".join(e["item"] for e in rows)))
        row = rows[0]
        self.dir = os.path.join(self.assess_dir, "Test")
        self.slot = row["due"]
        if self.slot:
            self.sources.append(("slot", self.slot, "unit_overview ## Evaluations, line %d (Due)" % row["line"]))
        else:
            self.unresolved.append("test slot not found in ## Evaluations; left as U_.W_.D_")
        assess = [r for r in self.week_rows if r["type"].startswith("assess") and re.search(r"\btest\b", r["topic"], re.I)]
        if assess and self.slot and assess[0]["slot"] != self.slot:
            self.notes.append("week table puts the test on %s; ## Evaluations says %s (Evaluations used)" % (assess[0]["slot"], self.slot))

        rev = [r for r in self.week_rows if "review_sheet" in r["topic"].lower()]
        if self.slot:
            same = [r for r in rev if slots.week_key(r["slot"]) == slots.week_key(self.slot)]
            rev = same or rev
        if rev:
            self.review = rev[0]["slot"]
            self.sources.append(("review", self.review, "week table row naming review_sheet"))
        elif self.slot and slots.parse(self.slot)[2] > 1:
            b, w, d = slots.parse(self.slot)
            self.review = "%s.%s.D%d" % (b, w, d - 1) if w else "%s.D%d" % (b, d - 1)
            self.notes.append("no week row names review_sheet; review day taken as the day before the test (%s)" % self.review)
            self.sources.append(("review", self.review, "the day before the test"))
        else:
            self.review = None
            self.unresolved.append("review day not found; review_sheet slot left as U_.W_.D_")

        self.codes, csrc = self.find_codes()
        self.codes_report.append(("test.md, test_KEY.md, coverage_table.md, review_sheet.md", self.codes, csrc))
        self.ref_codes = self.codes
        self.codes_report.append(("test_reference.md", self.codes, "the test's codes (trim to what the sheet carries)"))
        prim = re.search(r"^\*\*Expectations \(primary\):\*\*(.*)$", self.overview, re.M)
        by_assignment = [c for c, cell, _ in self.cov if names_item(cell, self.unit, "assignment")]
        self.compare_overview_codes(self.codes, "the overview's Expectations (primary) (and not the assignment's)",
                                    prim.group(1) if prim else "", "overview primary", by_assignment)

        self.marks, msrc = self.test_marks(self.dir)
        self.sources.append(("marks", num(self.marks) if self.marks is not None else PLACE_MARKS, msrc))
        self.minutes, tsrc = self.test_minutes()
        self.sources.append(("time", "%d min" % self.minutes, tsrc))

        keys = [read(p) for _, p in self.siblings("Test/test_KEY.md")]
        self.key_form = majority(["short" if re.search(r"^# .*KEY \(teacher only\)", t, re.M) else "full" for t in keys], "full")
        cov = [read(p) for _, p in self.siblings("Test/coverage_table.md")]
        self.cov_type = majority([header_fields(t).get("Type") for t in cov], "assess (coverage documentation)", least=2)
        self.cat_sep = majority(["·" if re.search(r"Understanding\s*·", t) else "," for t in cov if "K = Knowledge" in t], "·")
        revs = [read(p) for _, p in self.siblings("Test/review_sheet.md")]
        self.review_type = majority([header_fields(t).get("Type") for t in revs], "review (student-facing)", least=2)
        self.sources.append(("form", "KEY %s, review sheet type '%s'" % ("short (Slot · Marks)" if self.key_form == "short" else
                                                                         "full (Slot, Expectations, Marks)", self.review_type),
                             "the course's other unit tests (%d)" % len(keys) if keys else "defaults (no other tests)"))
        self.refs = re.findall(r"`(REF_[A-Za-z0-9_]+\.md)`", (re.search(r"^## Reference sheets\s*$(.*?)(?=^## |\Z)", self.overview, re.M | re.S)
                                                             or [None, ""])[1] if "## Reference sheets" in self.overview else "")

    # -- writers
    def emit(self, name, text):
        path = os.path.join(self.dir, name)
        if os.path.exists(path):
            self.skipped.append(name)
            return
        if self.dry:
            self.say("--- would write %s" % os.path.relpath(path, self.root))
            for line in text.splitlines()[:7]:
                self.say("    " + line)
        else:
            os.makedirs(self.dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        self.created.append(name)

    def template(self, name):
        return read(os.path.join(TEMPLATES, name))

    def codes_line(self):
        return ", ".join(self.codes) or "<codes>"

    def write_assignment(self):
        h, d = self.handed or "U_.W_.D_", self.due or "U_.W_.D_"
        pts = num(self.points) if self.points is not None else PLACE_TOTAL
        bonus = num(self.bonus) if self.bonus is not None else PLACE_BONUS
        if self.points_form == "points":
            slot = "handed out %s · due %s" % (h, d)
            marks = "**Points:** %s (+ up to %s bonus) · **Window:** %s class days" % (pts, bonus, self.days if self.days is not None else "<n>")
        else:
            win = "%d school days %s" % (self.days, weeks_phrase(self.days, self.per_week)) if self.days is not None else "<n> school days ≈ 1.5–2 weeks"
            slot = "handed out %s, due %s (%s)" % (h, d, win.strip())
            marks = "**Marks:** %s points (Google Classroom rubric) + up to %s bonus" % (pts, bonus)
        head = "# Assignment: %s\n\n**Slot:** %s · **Type:** assignment\n%s\n\n" % (self.title, slot, marks)   # student-facing: no codes
        self.emit("instructions.md", head + after_header(self.template("Assignment_Template.md")))

        if self.notes_form == "anchors":
            text = ("# %s: Marking Notes (teacher only)\n\n**Batch strategy:** <the fastest honest pass: what to run or read first, "
                    "then mark per rubric>\n\n## Level anchors\n\n- **Level 4 smell:** <what a Level 4 submission shows>\n"
                    "- **Level 3 smell:** <what a solid, provincial-standard submission shows>\n- **Level 2 smell:** <common gaps>\n"
                    "- **Level 1 smell:** <minimal evidence>\n\n## Verification moves\n\n- <a quick check that separates levels>\n\n"
                    "## Integrity red flags\n\n- <pattern worth a conversation>\n\n## Feedback that pays forward\n\n"
                    "- <comment stems that point at the next unit>\n" % self.title)
        else:
            slot = "handed out %s, due %s" % (h, d) if self.notes_handed else "due %s" % d
            text = ("# Marking Notes: %s\n\n**Slot:** %s · **Type:** assignment (teacher marking notes)\n**Expectations:** %s\n"
                    "**Marks:** %s points + up to %s bonus\n\nTeacher-only. Pair with `rubric.md` / `rubric.csv`.\n\n"
                    "## Marking workflow\n\n1. <compile and run; the inputs to feed it>\n2. <what to check, in order>\n\n"
                    "## Requirements quick-check\n\n| Requirement | Look for |\n|-------------|----------|\n| <requirement> | <evidence> |\n\n"
                    "## Model solution\n\n<verified: compiles and runs>\n\n## Common issues and how to score them\n\n- <issue>: <rubric effect>\n\n"
                    "## Stretch goal scoring\n\n- **Stretch 1:** <how the bonus is earned>\n- **Stretch 2:** <how the bonus is earned>\n\n"
                    "## Late / integrity\n\n<late and integrity handling, per the Assessment Plan>\n"
                    % (self.title, slot, self.codes_line(), pts, bonus))
        text += ("\n## Expectations assessed\n\nTeacher-side record of what this assignment evaluates (the student copy carries no codes). "
                 "One row per rubric criterion; every code below must appear, and the coverage map's Assessed in cells must agree.\n\n"
                 "Codes the coverage map assigns to this assignment: %s.\n\n"
                 "| Rubric criterion | Category | Expectation codes |\n|------------------|----------|-------------------|\n"
                 "| <Knowledge and Understanding criterion> | K | <codes> |\n| <%s criterion> | T | <codes> |\n"
                 "| <Communication criterion> | C | <codes> |\n| <Application criterion> | A | <codes> |\n"
                 % (self.codes_line(), self.thinking))
        self.emit("marking_notes.md", text)

    def write_test(self):
        s = self.slot or "U_.W_.D_"
        marks = num(self.marks) if self.marks is not None else PLACE_MARKS
        codes = self.codes_line()
        tname = "Unit %s Test: %s" % (self.unit_n, self.unit_name)
        head = "# %s\n\n**Slot:** %s · **Type:** assess\n**Marks:** %s · **Time:** %d min\n\n" % (tname, s, marks, self.minutes)   # student-facing: no codes
        self.emit("test.md", head + after_header(self.template("Test_Template.md")))

        if self.key_form == "short":
            key = ("# Unit %s Test: KEY (teacher only)\n\n**Slot:** %s · **Marks:** %s\n\n## Part A (1 mark each)\n\n"
                   "1. **<letter>** · 2. **<letter>**\n\n## Part B\n\n**B1 (<marks>).** <full answer; what earns each mark>\n\n"
                   "## Accepted-variation notes\n\n- <accepted variation>\n" % (self.unit_n, s, marks))
        else:
            key = ("# Unit %s Test KEY: %s\n\n**Slot:** %s · **Type:** assess (teacher key)\n**Expectations:** %s\n"
                   "**Marks:** %s · **Time:** %d min\n\n## Part A: Multiple choice (<n> marks, 1 each)\n\n"
                   "| Q | Answer | Notes |\n|---|--------|-------|\n| A1 | <letter> | <why the distractors fail> |\n\n"
                   "## Part B: Short answer and coding (<n> marks)\n\n### B1. <question type> (<marks>)\n\n"
                   "<full answer, compiled and run where it is code; accepted variations; what earns each mark>\n\n"
                   "## Common errors to watch for\n\n- <error and how it is marked>\n" % (self.unit_n, self.unit_name, s, codes, marks, self.minutes))
        self.emit("test_KEY.md", key)

        sep = " · " if self.cat_sep == "·" else ", "
        cats = sep.join(["K = Knowledge/Understanding", "T = %s" % self.thinking, "C = Communication", "A = Application"])
        self.emit("coverage_table.md", "# Unit %s Test: Coverage Table\n\n**Slot:** %s · **Type:** %s\n**Expectations:** %s\n**Marks:** %s\n\n"
                  "Categories: %s.\n\n| Question | Expectation codes | Category | Marks |\n|----------|-------------------|----------|-------|\n"
                  % (self.unit_n, s, self.cov_type, codes, marks, cats))

        r = self.review or "U_.W_.D_"
        refs = ", ".join("`%s`" % x for x in self.refs) if self.refs else "<the unit's REF_ sheets>"
        self.emit("review_sheet.md", "# Unit %s Review Sheet: %s\n\n**Slot:** %s (review day) · **Type:** %s\n\n"
                  "<What the test looks like (%d minutes, multiple choice plus short answer), how to use this sheet today, "
                  "and the study companions: %s.>\n\n## 1. <topic group>: can you...\n\n- <observable ability>\n\n"
                  "## Practice questions (different from the test)\n\n1. <question>\n\n## Answers\n\n1. <answer>\n"
                  % (self.unit_n, self.unit_name, r, self.review_type, self.minutes, refs))

        rname = self.unit_name.replace(": ", ", ").replace(" & ", " and ")
        self.emit("test_reference.md", "# Test Reference: %s\n\n**Course:** %s\n\n%s"
                  % (rname, self.cfg.get("code"), after_header(self.template("Test_Reference_Template.md"))))

    # -- run
    def run(self):
        self.load()
        if self.kind == "assignment":
            self.plan_assignment()
            self.write_assignment()
        else:
            self.plan_test()
            self.write_test()
        self.report()

    def report(self):
        s = self.say
        what = "%s (%s)" % (self.kind, self.token) if self.kind == "assignment" else "test"
        s("%s %s %s (%s) %s" % (self.cfg.get("code"), self.unit, what, self.unit_name, "[dry run]" if self.dry else ""))
        s("folder:  %s%s" % (os.path.relpath(self.dir, self.root), "" if os.path.isdir(self.dir) else " (new)"))
        if self.kind == "assignment":
            s("name:    %s (%s)" % (self.item, self.name_src))
        for k, v, src in self.sources:
            s("%-8s %s (from %s)" % (k + ":", v, src))
        s("%s (%d):" % ("would create" if self.dry else "created", len(self.created)))
        for x in self.created:
            s("  + " + x)
        s("skipped, already exists (%d):" % len(self.skipped))
        for x in self.skipped:
            s("  = " + x)
        s("codes:")
        for w, codes, src in self.codes_report:
            s("  %-56s %s" % (w, ", ".join(codes) or "(none)"))
            s("  %-56s from %s" % ("", src))
        if self.kind == "assignment":
            have = [n for n in ("rubric.csv", "rubric.md") if os.path.exists(os.path.join(self.dir, n))]
            if len(have) == 2:
                s("rubric:  rubric.csv and rubric.md exist")
            else:
                s("rubric (not created; gc-rubric builds it once instructions.md is written):")
                s("  python3 %s --from-assignment %s --spec-out /tmp/rubric.json" % (BUILD_RUBRIC, self.dir))
                s("  python3 %s /tmp/rubric.json --out %s --name rubric" % (BUILD_RUBRIC, self.dir))
        if self.notes:
            s("notes:")
            for x in self.notes:
                s("  - " + x)
        if self.unresolved:
            s("could not resolve:")
            for x in self.unresolved:
                s("  ! " + x)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("unit", help="unit such as U2")
    ap.add_argument("kind", choices=("assignment", "test"))
    ap.add_argument("--name", help="assignment name, e.g. Creature_Clinic (default: the unit's single assignment row)")
    ap.add_argument("--root", help="course repo root (default: found from the cwd)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.name and args.kind != "assignment":
        ap.error("--name applies to assignments only")
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root or not os.path.exists(os.path.join(root, "course.yaml")):
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    Scaffolder(root, args.unit, args.kind, name=args.name, dry_run=args.dry_run).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Scaffold a new GLA course repo from an answers file.

    python3 scaffold_course.py init CODE [--out answers.yaml]
    python3 scaffold_course.py codes CODE
    python3 scaffold_course.py check answers.yaml
    python3 scaffold_course.py build answers.yaml --dest Courses/CODE [--force]

init   writes the interview as a YAML file the teacher edits: everything the
       curriculum data settles is filled in and marked DETECT (confirm it),
       everything the teacher decides is TODO.
codes  prints every specific expectation with its code, by strand and
       overall expectation (the codes a teacher cannot look up for a 2008 course).
check  validates the answers against the curriculum, the 2026 Growing Success
       buckets and the subject matrix: no TODO left, weights total the
       classroom bucket, every specific expectation has a home.
build  runs check, then writes the tree, course.yaml, gdocs_manifest.yaml,
       rehydration.yaml, the coverage map with every expectation row, and
       skeletons of the parameter documents. Prose the model or teacher
       writes is marked <!-- TODO(bootstrap): ... -->; the run lists those
       files. --dest must not exist or be empty (--force allows a non-empty
       one, for tests; nothing is deleted).

Exit codes: 0 ok; 1 the answers have errors; 2 usage.
"""
import argparse
import importlib.util
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
from gla import course as gcourse, curriculum, paths  # noqa: E402
from gla.weekplan import DAY_TYPES  # noqa: E402
from gla import features  # noqa: E402
from gla.coursecheck import expand_codes  # noqa: E402

TODO = "TODO"
MARK = "<!-- TODO(bootstrap): %s -->"
BUCKETS = {9: (65, 20, 15), 10: (65, 20, 15), 11: (65, 25, 10), 12: (65, 25, 10)}
# Generated documents name the shared standards by their place in the GLA
# install (`gla where` prints its folder), never by a machine's absolute path.
STD = "Standards"
# The finding-code prefixes a fresh scaffold must pass (SKILL.md, Self-check).
SELF_CHECK = "course,curriculum,coverage,weight,admin,index,name,map,code,style"


# ------------------------------------------------------------------ helpers

def slug(text):
    """Folder name from a title: words joined by underscores, punctuation dropped."""
    words = re.findall(r"[A-Za-z0-9]+", text.replace("'", ""))
    return "_".join(words)


def has_todo(v):
    return isinstance(v, str) and TODO in v


def todos(obj, at=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += todos(v, "%s.%s" % (at, k) if at else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += todos(v, "%s[%d]" % (at, i))
    elif has_todo(obj):
        out.append(at)
    return out


def load_prefill():
    spec = importlib.util.spec_from_file_location(
        "prefill", os.path.join(paths.SKILLS, "gla-plan-formatter", "scripts", "prefill.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(spec.origin))
    spec.loader.exec_module(mod)
    return mod


def exam_split(code, grade):
    """(exam, culminating, note) from the Growing Success subject matrix."""
    pf = load_prefill()
    gs = os.path.join(paths.STANDARDS, "assessment", "growing-success-summary.md")
    return pf.exam_split(code, grade, pf.course_facts(code), gs)


def resolve_codes(spec, cur):
    """Specific codes named by a spec: codes, ranges (A4.1-A4.5), overall codes (C1), strand letters (C)."""
    text = spec if isinstance(spec, str) else ", ".join(str(x) for x in spec or [])
    out = set(expand_codes(text))
    overalls = {o["code"]: [c for c, _ in o["specifics"]] for s in cur.strands for o in s["overalls"]}
    strands = {s["letter"]: [c for o in s["overalls"] for c, _ in o["specifics"]] for s in cur.strands}
    for tok in re.split(r"[,;]", text):
        tok = re.sub(r"\(.*?\)", "", tok).replace("reinforces", "").replace("reinforced", "").strip()
        if tok in overalls:
            out.update(overalls[tok])
        elif tok in strands:
            out.update(strands[tok])
    return out


def gla_rel(path):
    """A shared file as GLA_ROOT/..., the form that holds on every install."""
    return "GLA_ROOT/" + os.path.relpath(path, paths.TEACHING_ROOT).replace(os.sep, "/")


def weight_total(w):
    return sum(float(v) for v in (w or {}).values())


def fmt(n):
    return ("%g" % n)


# --------------------------------------------------------------------- init

PROGRAMMING_SUBJECTS = ("Computer Studies", "Technological Education")
UNIT_WEEKS = 17     # unit and culminating weeks in a semester, after the intro days and the exam


def even_parts(total, n):
    """n whole numbers that sum to total, as even as they can be, larger first."""
    base, extra = divmod(int(total), n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def prefill_units(cur, cc, classroom, cp_weeks):
    """One unit per strand that is not cross-cutting, as YAML lines: the strand's
    codes, weeks from its share of the specific expectations (two at least),
    and the classroom bucket split evenly, all for the teacher to confirm. Each
    strand's overall expectations print above its unit as comments."""
    strands = [s for s in cur.strands if s["letter"] not in cc] or cur.strands
    if not strands:
        return ["  - name: TODO", "    weeks: [TODO]", "    codes: TODO",
                "    weight: {test: TODO, assignment: TODO, exercises: TODO}", "    assignment: TODO", "    rhythm: standard"]
    sizes = [max(1, sum(len(o["specifics"]) for o in s["overalls"])) for s in strands]
    avail = max(2 * len(strands), UNIT_WEEKS - cp_weeks)
    weeks = [max(2, round(avail * z / sum(sizes))) for z in sizes]
    while sum(weeks) > avail and max(weeks) > 2:
        weeks[weeks.index(max(weeks))] -= 1
    while sum(weeks) < avail:
        weeks[weeks.index(min(weeks))] += 1
    out = []
    for s, w, total in zip(strands, weeks, even_parts(classroom, len(strands))):
        ex = min(w - 1, max(1, total // 4))
        test = (total - ex + 1) // 2
        out += ["  # Strand %s: %s" % (s["letter"], s["title"])]
        out += ["  #   %s %s" % (o["code"], abridge(o["text"], 100)) for o in s["overalls"]]
        out += ["  - name: \"%s\"   # CONFIRM: one unit per strand is a starting point" % s["title"].title().replace('"', "'"),
                "    weeks: [%s]   # CONFIRM: %d weeks from the strand's share of the expectations; title each" % (", ".join([TODO] * w), w),
                "    codes: %s     # CONFIRM: the whole strand" % s["letter"],
                "    weight: {test: %d, assignment: %d, exercises: %d}   # CONFIRM: an even share of the classroom %d%%" % (test, total - ex - test, ex, classroom),
                "    assignment: TODO", "    rhythm: standard"]
    return out


def codes_text(code):
    """Every specific expectation of a course with its code, by strand and overall."""
    cur = curriculum.load(code)
    L = ["%s: %s" % (code, re.sub(r"\s*\(%s\)\s*$" % code, "", cur.meta.get("title") or cur.meta.get("name") or ""))]
    if cur.positional:
        L.append("Specific expectations are numbered by position under their overall expectation (a local convention).")
    if cur.letters_assigned:
        L.append("Strand letters are assigned by position; the Ministry document does not letter its strands.")
    if not cur.positional_reliable:
        L.append("Positions are unreliable here: " + "; ".join(cur.notes))
    for s in cur.strands:
        L += ["", "Strand %s: %s" % (s["letter"], s["title"])]
        for o in s["overalls"]:
            L.append("  %s  %s" % (o["code"], abridge(o["text"], 110)))
            L += ["    %s  %s" % (c, abridge(re.split(r"\s+Teacher prompts?:", t)[0], 104)) for c, t in o["specifics"]]
    return "\n".join(L) + "\n"

def init_text(code):
    cur = curriculum.load(code)
    era = curriculum.era(code)
    cc = curriculum.cross_cutting(cur)
    grade = cur.grade or 0
    title = re.sub(r"\s*\(%s\)\s*$" % code, "", cur.meta.get("title") or cur.meta.get("name") or "")
    title = re.sub(r"\s*\(effective [^)]*\)", "", title, flags=re.I).strip()
    ctype = cur.meta.get("course_type", "")
    subject = cur.subject
    year = cur.meta.get("year_issued", "")
    e, c, note = exam_split(code, grade)
    split = "{exam: %s, culminating: %s}" % (e, c) if e is not None else "{exam: TODO, culminating: TODO}"
    conv_dir = os.path.join(paths.STANDARDS, "style")
    convs = sorted(f for f in os.listdir(conv_dir) if f.endswith("_Conventions.md")) if os.path.isdir(conv_dir) else []
    strands = "; ".join("%s %s" % (s["letter"], s["title"]) for s in cur.strands)
    classroom = BUCKETS.get(grade, (65, 25, 10))[0]
    units = "\n".join(prefill_units(cur, cc, classroom, 0 if c == 0 else 3))
    cp_block = ("culminating: null           # DETECT: the matrix gives no culminating task, so there is no CP block" if c == 0 else
                """culminating:
  shape: TODO                # form and topic of the culminating task
  weeks: 3
  codes: TODO                # codes the project is the home for
  student_docs: [assignment_instructions, getting_started]   # CP student-facing files (stems)
  makeup: true               # an Individual_Makeup variant""")
    if subject in PROGRAMMING_SUBJECTS:
        lang_block = ('language: TODO               # null for a non-programming course\n'
                      'conventions_file: TODO       # null when language is null; otherwise in Standards/style/: %s; a new one is a Standards change'
                      % (", ".join(convs) or "none yet"))
    else:
        lang_block = ('language: null               # DETECT: %s is not a programming subject (no code samples, no feature table)\n'
                      'conventions_file: null' % subject)
    letters = " Strand letters are assigned by position (the Ministry document has none)." if cur.letters_assigned else ""
    q = lambda v: '"%s"' % str(v).replace('"', "'")  # noqa: E731
    return f"""# bootstrap-gla-course answers for {code}. Edit every TODO, confirm every DETECT.
#   gla course check <this file>
#   gla course build <this file> --dest <the course folder, outside the GLA install>
#   gla course codes {code}      every expectation with its code
# Batch letters follow the interview in bootstrap-gla-course/SKILL.md.
schema: 1

# Batch A.1: identity. DETECT from {os.path.relpath(cur.source, paths.TEACHING_ROOT)}; confirm each.
course:
  code: {code}
  title: {q(title)}
  grade: {grade}
  type: {q(ctype)}
  department: {q(subject)}
  curriculum_document: {q("The Ontario Curriculum: %s, %s" % (subject, year))}  # DETECT: use the document's exact title
  prerequisite: {q(curriculum.prerequisite(code) or TODO)}
  credit: 1.0
  hours: 110
  feeder_role: TODO          # what the next course assumes its alumni know
teacher: TODO                # as students see it, e.g. "Br. Zaid"
teacher_formal: TODO         # for official documents

# Batch A.2-3. DETECT: era {era} ({"Ministry-numbered specific expectations" if era == "modern" else "specific expectations numbered locally by position, A1.1, A1.2, ..."}).
# Strands: {strands}.{letters}
curriculum:
  era: "{era}"
  cross_cutting: [{", ".join(cc)}]   # DETECT: strands described "Throughout this course"

# The course-introduction block (INTRO), before Unit 1.
intro_days:
  - {{title: "Welcome to {code}", day_type: teach}}
  - {{title: TODO, day_type: lab}}

# Batch B.4 and C.8-9: the unit spine. One entry per unit, in order.
#   weeks: week titles, one per week (they name the W<n>_<Title> folders; frozen once committed)
#   codes: the unit's primary codes, as the unit overview will list them. Codes,
#          ranges (C1.1-C1.4), overall codes (C1) or strand letters (C); notes in
#          parentheses are kept, e.g. "A1.4 (arithmetic)". "reinforces ..." is allowed.
#   weight: the unit's share of the classroom 65%, split by kind
#   assignment: the assignment folder name (Assignment_<Name>)
#   rhythm: one of rhythms below
#   folder: optional; the U<n>_ folder name when it should differ from the name's words
# The units below are prefilled one per strand: confirm or reshape every CONFIRM line.
units:
{units}

rhythms: [standard]          # Batch B.5: add a variant (e.g. studio) only if some units use it
studio: false                # Batch B.6: divergent-output work (BRIEF_ and _MARKING pairs)?

# Batch B.7: an optional standby module, or null. Example:
#   standby: {{name: AI Standby Module, block: AI, weight: 2, coverage: enrichment,
#             codes: "D2.1-D2.3", config_key: ai_module, manifest_dest: AI_Module,
#             variants: [{{folder: Full_2Week, value: full, weeks: [How AI Works, AI in Context]}},
#                        {{folder: Short_3Day, value: short, weeks: []}}]}}
standby: null

# Batch C.10: final evaluation. The split is DETECT from the Growing Success matrix ({note or "subject row"}).
exam_split: {split}
category_weights: null       # Batch C.9: null keeps the school default (K/U 25, T 30, C 20, A 25) for rubrics;
                             #   or {{ku: .., thinking: .., communication: .., application: ..}} totalling 100
{cp_block}

# Batch D.11-14.
environment:
  in_class: TODO
  at_home: TODO
  provenance: TODO           # how authorship is evidenced (git cadence, check-ins, ...)
{lang_block}
typography: [no em dashes, no emojis]   # confirm each
decks: true                  # a slide deck (and its teacher guide) on every teach day; false: lessons only
test_parts: [A, B]           # the unit test's parts: A is multiple choice, every later part written (history might use [A, B, C])
deck_theme: glass            # glass (marine and coral) or gla (maroon, gold, grays)

# Batch E.15-16.
legacy: false                # legacy material to audit? (adds Legacy_Reuse_Map.md)
deployment: false            # one-time lab setup? (adds Deployment_Checklist.md)

# Batch F.17: shared (Standards' Semester_Config_Template.yaml) or course (a copy in the rehydration folder).
semester_config: shared
"""


# -------------------------------------------------------------------- check

class Answers:
    def __init__(self, data):
        self.d = data
        self.errors, self.warnings = [], []
        self.cur = None
        self.unit_codes = []          # [set of codes] per unit
        self.cp_codes = set()
        self.standby_codes = set()

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    @property
    def code(self):
        return (self.d.get("course") or {}).get("code", "")

    @property
    def grade(self):
        return int((self.d.get("course") or {}).get("grade") or 0)

    @property
    def standby(self):
        return self.d.get("standby") or None

    def buckets(self):
        return BUCKETS.get(self.grade, (65, 25, 10))

    @property
    def has_cp(self):
        """False when the final evaluation has no culminating task (English, Math, Science)."""
        try:
            return int((self.d.get("exam_split") or {}).get("culminating")) > 0
        except (TypeError, ValueError):
            return True

    def numbering(self):
        """Positional folder numbers: (standby, culminating, rehydration) prefixes, None when absent."""
        n, out = 3, []
        for present in (bool(self.standby), self.has_cp):
            out.append("%02d" % n if present else None)
            n += present
        return out[0], out[1], "%02d" % n

    def check(self):
        d = self.d
        for t in todos(d):
            self.err("%s is still TODO" % t)
        code = self.code
        try:
            self.cur = curriculum.load(code)
        except FileNotFoundError:
            self.err("no curriculum data for %s (Curriculum/docs/knowledge-graph/courses/%s.md)" % (code, code))
            return self
        c = d.get("course") or {}
        for k in ("code", "title", "grade", "type", "department", "curriculum_document", "prerequisite", "credit", "hours"):
            if c.get(k) in (None, ""):
                self.err("course.%s is missing" % k)
        if c.get("type") and c["type"] not in gcourse.TYPES:
            self.err("course.type %r is not one of %s" % (c["type"], ", ".join(gcourse.TYPES)))
        if self.cur.grade and self.grade != self.cur.grade:
            self.err("course.grade %s, the curriculum says %s" % (self.grade, self.cur.grade))
        cu = d.get("curriculum") or {}
        era = curriculum.era(code)
        if str(cu.get("era")) != era:
            self.err("curriculum.era %r, detected %r" % (cu.get("era"), era))
        cc = list(cu.get("cross_cutting") or [])
        detected = curriculum.cross_cutting(self.cur)
        letters = [s["letter"] for s in self.cur.strands]
        for s in cc:
            if s not in letters:
                self.err("cross_cutting strand %r is not in %s" % (s, code))
        if sorted(cc) != sorted(detected):
            self.warn("cross_cutting %s, the curriculum describes %s as 'throughout this course'" % (cc, detected or "none"))
        for i, day in enumerate(d.get("intro_days") or []):
            if day.get("day_type") not in DAY_TYPES:
                self.err("intro_days[%d].day_type %r is not one of %s" % (i, day.get("day_type"), ", ".join(DAY_TYPES)))
        units = d.get("units") or []
        if not units:
            self.err("no units")
        known = set(self.cur.specific_codes())
        rhythms = d.get("rhythms") or ["standard"]
        from gla.weekplan import RHYTHMS as weekplan_rhythms
        total = 0.0
        for i, u in enumerate(units):
            where = "units[%d] (%s)" % (i, u.get("name"))
            if not u.get("weeks") or not isinstance(u["weeks"], list):
                self.err("%s: weeks must be a list of week titles" % where)
            codes = resolve_codes(u.get("codes") or "", self.cur)
            for x in sorted(codes - known):
                self.err("%s: %s is not a %s code" % (where, x, code))
            self.unit_codes.append(codes & known)
            try:
                total += weight_total(u.get("weight"))
            except (TypeError, ValueError):
                self.err("%s: weight parts must be numbers" % where)
            if u.get("rhythm", "standard") not in weekplan_rhythms:
                self.err("%s: rhythm %r is not one of %s" % (where, u.get("rhythm"), ", ".join(weekplan_rhythms)))
            if u.get("rhythm", "standard") not in rhythms:
                self.err("%s: rhythm %r is not in rhythms %s" % (where, u.get("rhythm"), rhythms))
            if not u.get("assignment"):
                self.err("%s: no assignment name" % where)
            if u.get("folder") and not re.fullmatch(r"[A-Za-z0-9_]+", str(u["folder"])):
                self.err("%s: folder %r must be letters, digits and underscores" % (where, u["folder"]))
            if u.get("assignment") and not re.fullmatch(r"[A-Za-z0-9_]+", str(u["assignment"])):
                self.err("%s: assignment %r must be letters, digits and underscores" % (where, u["assignment"]))
            for w in u.get("weeks") or []:
                if not has_todo(w) and not slug(str(w)):
                    self.err("%s: week title %r has no letters" % (where, w))
        sb = self.standby
        if sb:
            try:
                total += float(sb.get("weight") or 0)
            except (TypeError, ValueError):
                self.err("standby.weight must be a number")
            self.standby_codes = resolve_codes(sb.get("codes") or "", self.cur) & known
            for k in ("name", "block", "coverage", "config_key", "variants"):
                if not sb.get(k):
                    self.err("standby.%s is missing" % k)
            if sb.get("coverage") not in ("enrichment", "baseline"):
                self.err("standby.coverage must be enrichment or baseline")
        classroom, final, _ = self.buckets()
        if abs(total - classroom) > 0.01:
            self.err("unit weights%s total %s%%; the classroom bucket is %d%%" % (" and the standby module" if sb else "", fmt(total), classroom))
        cp = (d.get("culminating") or {}) if self.has_cp else {}
        if self.has_cp and not d.get("culminating"):
            self.err("culminating is missing; the final evaluation has a %s%% culminating task" % (d.get("exam_split") or {}).get("culminating"))
        if not self.has_cp and d.get("culminating"):
            self.warn("culminating is ignored: exam_split gives the culminating task 0%")
        self.cp_codes = resolve_codes(cp.get("codes") or "", self.cur) & known
        cross = {x for s in self.cur.strands if s["letter"] in cc for o in s["overalls"] for x, _ in o["specifics"]}
        homed = set().union(*self.unit_codes) | self.cp_codes if self.unit_codes else self.cp_codes
        for x in sorted(known - homed - cross, key=_code_key):
            if x in self.standby_codes and sb and sb.get("coverage") == "enrichment":
                self.err("%s lives only in the standby module, whose coverage is enrichment; give it an unconditional home" % x)
            elif x not in self.standby_codes:
                self.err("%s has no unit%s home" % (x, " or culminating" if self.has_cp else ""))
        ex = d.get("exam_split") or {}
        e, cu_, note = exam_split(code, self.grade)
        try:
            got = (int(ex.get("exam")), int(ex.get("culminating")))
            if got[0] + got[1] != final:
                self.err("exam_split totals %d; the final evaluation bucket is %d%%" % (sum(got), final))
            if e is not None and got != (e, cu_):
                self.warn("exam_split %d/%d, the Growing Success matrix gives %s/%s" % (got[0], got[1], e, cu_))
        except (TypeError, ValueError):
            if not todos(ex):
                self.err("exam_split needs exam and culminating numbers")
        conv = d.get("conventions_file")
        if not todos([d.get("language"), conv]) and bool(d.get("language")) != bool(conv):
            self.err("language and conventions_file must both be set or both be null")
        if conv and not has_todo(conv) and not os.path.exists(os.path.join(paths.STANDARDS, "style", conv)):
            self.warn("Standards/style/%s does not exist yet; adding it is a Standards change with its own CHANGELOG entry" % conv)
        cw = d.get("category_weights")
        if cw is not None and not (isinstance(cw, dict) and set(cw) == {"ku", "thinking", "communication", "application"}
                                   and all(isinstance(v, (int, float)) for v in cw.values()) and abs(sum(cw.values()) - 100) < 0.01):
            self.err("category_weights needs ku, thinking, communication and application, totalling 100 (or null)")
        if "decks" in d and not isinstance(d["decks"], bool):
            self.err("decks must be true or false")
        tp = d.get("test_parts", ["A", "B"])
        if not (isinstance(tp, list) and tp and all(isinstance(x, str) and re.fullmatch(r"[A-Z]", x) for x in tp) and len(set(tp)) == len(tp)):
            self.err("test_parts must be distinct capital letters, for example [A, B]")
        if d.get("deck_theme") not in gcourse.DECK_THEMES:
            self.err("deck_theme %r is not one of %s" % (d.get("deck_theme"), ", ".join(gcourse.DECK_THEMES)))
        if d.get("semester_config") not in ("shared", "course"):
            self.err("semester_config must be shared or course")
        return self


def _code_key(c):
    m = re.match(r"([A-Z])(\d+)\.(\d+)", c)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else (c, 0, 0)


# -------------------------------------------------------------------- build

class Builder:
    def __init__(self, a, dest):
        self.a, self.d, self.dest = a, a.d, dest
        self.written, self.marked = [], []
        self.code = a.code
        sb_n, cp_n, rh_n = a.numbering()
        self.standby_dir = "%s_%s" % (sb_n, slug(a.standby["name"])) if a.standby else None
        self.cp_dir = "%s_Culminating_Project" % cp_n if cp_n else None
        self.rh_dir = "%s_Rehydration" % rh_n
        self.units = []
        for i, u in enumerate(self.d["units"], 1):
            weeks = ["W%d_%s" % (k, slug(str(w))) for k, w in enumerate(u["weeks"], 1)]
            self.units.append({"n": i, "id": "U%d" % i, "dir": "U%d_%s" % (i, u.get("folder") or slug(u["name"])), "name": u["name"],
                               "weeks": weeks, "titles": [str(w) for w in u["weeks"]], "u": u,
                               "codes": a.unit_codes[i - 1]})

    # -- io
    def write(self, rel, text):
        full = os.path.join(self.dest, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text.rstrip("\n") + "\n")
        self.written.append(rel)
        if "TODO(bootstrap)" in text:
            self.marked.append(rel)

    def keep(self, rel):
        """An empty folder git can hold."""
        full = os.path.join(self.dest, rel)
        os.makedirs(full, exist_ok=True)
        if not os.listdir(full):
            open(os.path.join(full, ".gitkeep"), "w").close()

    # -- facts
    @property
    def cfg(self):
        return self.d["course"]

    def m(self, rel):
        return "master/" + rel

    def cp_weeks(self):
        if not self.a.has_cp:
            return 0
        return int((self.d.get("culminating") or {}).get("weeks") or 3)

    def block_rows(self):
        rows = [("INTRO", "INTRO.D1 – INTRO.D%d" % len(self.d.get("intro_days") or []), "-", "Course introduction")]
        for u in self.units:
            n = len(u["weeks"])
            rows.append((u["id"], "%s.W1.D1 – %s.W%d.D5" % (u["id"], u["id"], n), str(n), u["name"]))
        sb = self.a.standby
        if sb:
            rows.append((sb["block"], "see %s/module_overview.md" % self.standby_dir, "optional", sb["name"] + " (standby)"))
        if self.a.has_cp:
            rows.append(("CP", "CP.W1.D1 – CP.W%d.D5" % self.cp_weeks(), str(self.cp_weeks()), "Culminating project"))
        return rows

    def flex_slots(self):
        """(unit D5 slots, latest unit first; culminating D5 slots): the cuts every rhythm allows."""
        flex = ["%s.W%d.D5" % (u["id"], k) for u in reversed(self.units) for k in range(len(u["weeks"]), 0, -1)]
        cp = ["CP.W%d.D5" % k for k in range(1, self.cp_weeks() + 1)] if self.a.has_cp else []
        return flex, cp

    def nominal_slots(self):
        return len(self.d.get("intro_days") or []) + 5 * (sum(len(u["weeks"]) for u in self.units) + self.cp_weeks())

    def code_blocks(self):
        """{code: [blocks]} in course order."""
        out = {}
        for u in self.units:
            for c in u["codes"]:
                out.setdefault(c, []).append(u["id"])
        for c in self.a.standby_codes:
            out.setdefault(c, []).append(self.a.standby["block"])
        for c in self.a.cp_codes:
            out.setdefault(c, []).append("CP")
        return out

    def weight_line(self, u):
        w = u["u"]["weight"]
        parts = ", ".join("%s %s" % (k, fmt(float(v))) for k, v in w.items())
        rhythm = " · **Rhythm:** %s" % u["u"].get("rhythm", "standard")
        return "**Weeks:** %d (slots %s.W1.D1 – %s.W%d.D5) · **Weight:** %s%% (%s)%s" % (
            len(u["weeks"]), u["id"], u["id"], len(u["weeks"]), fmt(weight_total(w)), parts, rhythm)

    # -- documents
    def build(self):
        os.makedirs(self.dest, exist_ok=True)
        self.course_yaml()
        self.manifest()
        self.coverage_map()
        self.units_tree()
        self.standby_tree()
        self.cp_tree()
        self.admin()
        self.style_guide()
        self.rehydration()
        self.master_index()
        self.readme()
        self.keep("instances")
        self.write(".gitignore", ".DS_Store\n__pycache__/\n")
        return self

    def course_yaml(self):
        c, d = self.cfg, self.d
        classroom, final, att = self.a.buckets()
        ex = d["exam_split"]
        cur = self.a.cur
        cf = os.path.relpath(curriculum.page_path(self.code), paths.TEACHING_ROOT)
        lines = [
            "# %s course configuration. Schema: GLA_ROOT/Standards/templates/Course_Config_Schema.yaml" % self.code,
            "code: %s" % self.code,
            "title: %s" % c["title"],
            "grade: %d" % int(c["grade"]),
            "type: %s" % c["type"],
            "department: %s" % c["department"],
            'curriculum_document: "%s"' % c["curriculum_document"],
            "curriculum_file: %s" % cf,
            "prerequisite: %s" % c["prerequisite"],
            "credit: %s" % c["credit"],
            "hours: %s" % c["hours"],
            "language: %s" % ("null" if d.get("language") is None else d["language"]),
            "conventions_file: %s" % ("null" if d.get("conventions_file") is None else d["conventions_file"]),
            "rehydration_dir: %s" % self.rh_dir,
            "gdocs_manifest: gdocs_manifest.yaml",
            "assessment:",
            "  classroom: %d" % classroom,
            "  final_evaluation: %d" % final,
            "  attendance: %d" % att,
            "  exam: %s" % ex["exam"],
            "  culminating: %s" % ex["culminating"],
        ]
        cw = d.get("category_weights")
        if cw:
            lines.append("  category_weights: {%s}" % ", ".join("%s: %s" % (k, fmt(float(cw[k]))) for k in ("ku", "thinking", "communication", "application")))
        if d.get("deck_theme", "glass") != "glass":
            lines.append("deck_theme: %s" % d["deck_theme"])
        if d.get("decks") is False:
            lines.append("decks: false")
        if d.get("test_parts", ["A", "B"]) != ["A", "B"]:
            lines.append("test_parts: [%s]" % ", ".join(d["test_parts"]))
        lines += ["teacher: %s" % d["teacher"], "teacher_formal: %s" % d["teacher_formal"]]
        del cur
        self.write("course.yaml", "\n".join(lines))

    def manifest(self):
        cp = "master/%s" % self.cp_dir
        rules = [
            ("master/02_Units/U*_*/W*_*/EX_*.md", "master/02_Units", "{relparent}/{stem}.docx", {}),
        ]
        if self.d.get("studio"):
            rules.append(("master/02_Units/U*_*/W*_*/BRIEF_*.md", "master/02_Units", "{relparent}/{stem}.docx", {}))
        rules += [
            ("master/02_Units/U*_*/W*_*/REF_*.md", "master/02_Units", "{relparent}/{stem}.docx", {}),
            ("master/02_Units/U*_*/Assessment/Assignment_*/instructions.md", "master/02_Units", "{unit}/Assessment/{parentname}.docx", {}),
            ("master/02_Units/U*_*/Assessment/Test/test.md", "master/02_Units", "{unit}/Assessment/{uprefix}_Test.docx",
             {"strip_teacher_note": "true", "doc_kind": "test"}),
            ("master/02_Units/U*_*/Assessment/Test/test_reference.md", "master/02_Units", "{unit}/Assessment/{uprefix}_Test_Reference.docx", {}),
            ("master/02_Units/U*_*/Assessment/Test/review_sheet.md", "master/02_Units", "{unit}/Assessment/{uprefix}_Test_Review_Sheet.docx", {}),
        ]
        sb = self.a.standby
        if sb:
            for v in sb["variants"]:
                base = "master/%s/%s" % (self.standby_dir, v["folder"])
                rules.append((base + "/**/EX_*.md", base, "%s/{relparent}/{stem}.docx" % sb.get("manifest_dest", slug(sb["block"] + " Module")),
                              {"when_config_regex": '"%s:\\\\s*%s"' % (sb["config_key"], v["value"])}))
        cpd = (self.d.get("culminating") or {}) if self.a.has_cp else {}
        for stem in cpd.get("student_docs") or []:
            rules.append(("%s/%s.md" % (cp, stem), cp, "Culminating_Project/CP_{Stem}.docx", {}))
        if self.a.has_cp and cpd.get("makeup", True):
            rules.append(("%s/Individual_Makeup/assignment_instructions.md" % cp, cp,
                          "Culminating_Project/CP_Individual_Makeup_Instructions.docx", {}))
        out = ["# %s gdocs manifest" % self.code,
               "# Student-facing docs only; the converter hard-excludes *_KEY.md, *_MARKING.md,",
               "# marking_notes.md, and rubric.* regardless of these rules.",
               "rules:"]
        for g, base, dest, extra in rules:
            out += ['  - glob: "%s"' % g, '    base: "%s"' % base, '    dest: "%s"' % dest]
            out += ["    %s: %s" % (k, v) for k, v in extra.items()]
        self.write("gdocs_manifest.yaml", "\n".join(out))

    def coverage_map(self):
        a, cur = self.a, self.a.cur
        cc = set((self.d.get("curriculum") or {}).get("cross_cutting") or [])
        modern = self.d["curriculum"]["era"] == "modern"
        src = gla_rel(curriculum.json_path(self.code) if modern else curriculum.page_path(self.code))
        year = cur.meta.get("year_issued", "")
        blocks = self.code_blocks()
        L = ["# %s Curriculum Coverage Map" % self.code, "",
             "**The compliance authority for the master course.** Every specific expectation of the Ontario %s curriculum (%s) is listed here with where it is taught and where it is assessed." % (self.code, year), ""]
        if modern:
            L.append("**Source:** `%s` (authoritative expectation text). The %s curriculum numbers its own specific expectations: the codes below are the Ministry's, used directly." % (src, year))
        else:
            L.append("**Source:** `%s` (and the Ministry PDF). The Ministry document leaves specific expectations unnumbered; the A1.1-style numbering below is this course's local convention: specific expectations numbered by position under their overall expectation, in document order." % src)
        if self.d.get("legacy"):
            L[-1] += " **Codes found in legacy materials are from a different scheme and must never be carried over** (see `00_Admin/Legacy_Reuse_Map.md`)."
        L += ["", "**Rules:**",
              "1. Every specific expectation has **≥1 teach/anchor slot** and **≥1 evaluated artifact** (exercise, assignment, test question, or culminating rubric row). A write, use or apply expectation needs a submitted doing-artifact, not only a test question.",
              "2. Every lesson and exercise header carries its codes. Assignments record theirs in the `## Expectations assessed` table of `marking_notes.md` and tests in `coverage_table.md` (student-facing assessment documents carry none). `check_course.py` compares the Assessed in cells with both records.",
              "3. If you change what a document covers, update this map in the same change."]
        if cc:
            L.append("4. **Cross-cutting expectations (strand %s) use the anchored + woven model**: each has an **anchor slot** (a designated day) and may additionally have a **woven thread**: a named recurring assessed artifact. A woven thread must name concrete artifacts; \"throughout the course\" is not a location." % ", ".join(sorted(cc)))
        L += ["", "**Status legend:** `planned` (architecture only) → `built` (content exists) → `verified` (audit confirmed both directions).", "",
              MARK % "Taught in names the block only; refine to week slots (U2.W1) as week plans are written. Assessed in says (to assign) until author-assessment records the real artifacts.", "", "---"]
        for s in cur.strands:
            cross = s["letter"] in cc
            L += ["", "## Strand %s: %s%s" % (s["letter"], s["title"], " (cross-cutting)" if cross else "")]
            if cross:
                lead = re.sub(r",?\s*students will:?\s*$", "", s["describer"]).rstrip(",. ")
                L += ["", "*The Ministry introduces strand %s with \"%s.\" Each expectation below names its anchor slot and its woven thread.*" % (s["letter"], lead)]
            for o in s["overalls"]:
                L += ["", "### %s: %s" % (o["code"], o.get("title") or o["text"]), ""]
                if cross:
                    L += ["| Code | Expectation (abridged) | Anchor slot | Woven thread (named artifacts) | Assessed in | Status |",
                          "|------|------------------------|-------------|-------------------------------|-------------|--------|"]
                else:
                    L += ["| Code | Expectation (abridged) | Taught in | Assessed in | Status |",
                          "|------|------------------------|-----------|-------------|--------|"]
                for code, text in o["specifics"]:
                    b = blocks.get(code, [])
                    where = ", ".join(b) if b else "(to anchor)"
                    assessed = ", ".join("%s (to assign)" % x for x in b) if b else "(to assign)"
                    ab = abridge(text)
                    if cross:
                        L.append("| %s | %s | %s | - | %s | planned |" % (code, ab, where, assessed))
                    else:
                        L.append("| %s | %s | %s | %s | planned |" % (code, ab, where, assessed))
        L += ["", "## Reverse index (unit → codes)", "", "| Unit | Primary codes |", "|------|---------------|"]
        for u in self.units:
            L.append("| %s (%d wks) | %s |" % (u["id"], len(u["weeks"]), u["u"]["codes"]))
        if a.standby:
            L.append("| %s (standby) | %s (%s) |" % (a.standby["block"], a.standby["codes"], a.standby["coverage"]))
        if a.has_cp:
            L.append("| CP (%d wks) | %s |" % (self.cp_weeks(), self.d["culminating"]["codes"]))
        if cc:
            L += ["", "## Cross-cutting notes", "",
                  "- **Strand %s has no unit.** Every expectation gets a concrete anchor slot; an anchor may never dissolve into \"covered throughout.\"" % ", ".join(sorted(cc)),
                  "- **Woven threads are load-bearing:** a named rubric row on a named artifact. Removing one requires updating this map.",
                  "", MARK % "assign each cross-cutting expectation an anchor slot and, where relevant, a woven thread."]
        self.write(self.m("01_Standards/Curriculum_Coverage_Map.md"), "\n".join(L))

    def units_tree(self):
        for u in self.units:
            base = self.m("02_Units/%s" % u["dir"])
            uu = u["u"]
            L = ["# Unit %d: %s" % (u["n"], u["name"]), "", self.weight_line(u),
                 "**Expectations (primary):** %s" % uu["codes"], "",
                 "## Story of the unit", "", MARK % "the unit's story: what students can do at the end and why it comes here.", "",
                 "## Week architecture (frozen at the first commit: never renumber)"]
            for k, (wd, title) in enumerate(zip(u["weeks"], u["titles"]), 1):
                L += ["", "### W%d: %s (`%s/`)" % (k, title, wd), "",
                      "| Slot | Type | Topic | Notes |", "|------|------|-------|-------|"]
                for day in range(1, 6):
                    L.append("| %s.W%d.D%d | | | |" % (u["id"], k, day))
                self.keep("%s/%s" % (base, wd))
            w = uu["weight"]
            L += ["", "## Evaluations", "", "| Item | Kind | Handed out | Due | Weight |", "|------|------|-----------|-----|--------|",
                  "| Assignment_%s | assignment (rubric) | | | %s%% |" % (uu["assignment"], fmt(float(w.get("assignment", 0)))),
                  "| Unit %d Test | test | - | %s.W%d.D4 | %s%% |" % (u["n"], u["id"], len(u["weeks"]), fmt(float(w.get("test", 0)))),
                  "", MARK % "add the exercises (or ships) and the assignment's hand-out and due slots.", "",
                  "## Reference sheets", "", MARK % "the unit's REF_ sheets, by week."]
            if self.d.get("legacy"):
                L += ["", "## Content sources", "", "Legacy pointers: adapt facts only, re-derive all codes from the curriculum.", "", MARK % "legacy sources for this unit."]
            self.write(base + "/unit_overview.md", "\n".join(L))
            self.keep("%s/Assessment/Assignment_%s" % (base, uu["assignment"]))
            self.keep("%s/Assessment/Test" % base)

    def standby_tree(self):
        sb = self.a.standby
        if not sb:
            return
        base = self.m(self.standby_dir)
        forms = ", ".join("%s (`%s/`, `%s: %s`)" % (v["folder"].replace("_", " "), v["folder"], sb["config_key"], v["value"]) for v in sb["variants"])
        self.write(base + "/module_overview.md", "\n".join([
            "# %s" % sb["name"], "",
            "**Slots:** %s.* (by form) · **Weight:** %s%% of classroom work" % (sb["block"], fmt(float(sb.get("weight") or 0))),
            "**Expectations:** %s (%s)" % (sb["codes"], sb["coverage"]), "",
            "Optional and deployable. Forms: %s. The course is curriculum-compliant without it%s." % (
                forms, "" if sb["coverage"] == "enrichment" else "; its baseline codes must also have an unconditional home"),
            "", MARK % "the module's story, forms, and where its weight moves when it is not run."]))
        self.write(base + "/insertion_guide.md", "# %s: insertion guide\n\n%s" % (sb["name"], MARK % "where the module can be placed, and what each placement changes."))
        for v in sb["variants"]:
            weeks = v.get("weeks") or []
            if not weeks:
                self.keep("%s/%s" % (base, v["folder"]))
            for k, w in enumerate(weeks, 1):
                self.keep("%s/%s/W%d_%s" % (base, v["folder"], k, slug(w)))

    def cp_tree(self):
        if not self.a.has_cp:
            return
        base = self.m(self.cp_dir)
        cp = self.d["culminating"]
        _, final, _ = self.a.buckets()
        self.write(base + "/PROJECT_DECISIONS.md", "\n".join([
            "# Culminating Project: decisions", "", "Authoritative constraints for the %s culminating project (%s%% of the final mark)." % (self.code, self.d["exam_split"]["culminating"]), "",
            "## What it is", "", str(cp["shape"]), "",
            "## Technical constraints", "", MARK % ("language features allowed, starter code, tools." if self.d.get("language") else "materials, tools, and safety constraints."), "",
            "## Prompt directions", "", MARK % "the project prompts students choose from.", "",
            "## Components and evaluation", "", MARK % "components, weights, rubric rows.", "",
            "## Expectations assessed here", "", str(cp["codes"]), "",
            "## Makeup variant", "", "An individual makeup version lives in `Individual_Makeup/`." if cp.get("makeup", True) else "None."]))
        self.write(base + "/cp_overview.md", "# Culminating Project overview\n\n**Weeks:** %d (slots CP.W1.D1 – CP.W%d.D5)\n\n%s" % (
            self.cp_weeks(), self.cp_weeks(), MARK % "week-by-week overview."))
        self.keep(base + "/Launch_Week")
        if cp.get("makeup", True):
            self.keep(base + "/Individual_Makeup")

    def admin(self):
        c, d = self.cfg, self.d
        classroom, final, att = self.a.buckets()
        ex = d["exam_split"]
        thinking = curriculum.thinking_name(c["department"])
        sb = self.a.standby
        rows = []
        for u in self.units:
            w = u["u"]["weight"]
            other = sum(float(v) for k, v in w.items() if k not in ("test", "assignment"))
            rows.append("| %s %s | %s%% | %s | %s | %s |" % (u["id"], u["name"], fmt(weight_total(w)), fmt(float(w.get("test", 0))),
                                                         fmt(float(w.get("assignment", 0))), fmt(other)))
        if sb:
            rows.append("| %s %s (standby) | %s%% | - | - | %s |" % (sb["block"], sb["name"], fmt(float(sb.get("weight") or 0)), fmt(float(sb.get("weight") or 0))))
        grades = "Grades 9-10" if self.a.grade in (9, 10) else "Grades 11-12"
        self.write(self.m("00_Admin/Assessment_Plan.md"), "\n".join([
            "# %s Assessment Plan" % self.code, "",
            "## Final grade structure", "",
            "The 2026 Growing Success model (%s): classroom work %d%%, final evaluation %d%%, attendance and participation %d%%." % (grades, classroom, final, att), "",
            "| Bucket | Weight |", "|--------|--------|",
            "| Classroom work | %d%% |" % classroom, "| Final evaluation | %d%% |" % final, "| Attendance and participation | %d%% |" % att, "| **Total** | **100%** |", "",
            "## Classroom work breakdown", "",
            "| Unit | Weight | Test | Assignment | %s |" % ("Exercises/Ships" if self.d.get("studio") else "Exercises"), "|------|--------|------|------------|-----------|",
            *rows, "| **Total** | **%d%%** | | | |" % classroom, "",
            MARK % "notes on exercises or ships, the assignment count, and the compression-fold rule.", "",
            "## Final evaluation", "",
            ("Written exam %s%%, culminating task %s%%" % (ex["exam"], ex["culminating"]) if self.a.has_cp else "Written exam %s%%, no culminating task" % ex["exam"])
            + " (the Growing Success subject matrix for %s, %s). Exam spec: `00_Admin/Final_Exam/exam_spec.md`." % (c["department"], grades), "",
            *(["## Culminating project", "", str(d["culminating"]["shape"]), ""] if self.a.has_cp else []),
            "## Attendance and participation", "", "Marked on the unexcused-absence scale in `%s/assessment/growing-success-summary.md`." % STD, "",
            "## Marking schemes", "", MARK % "exercises or ships, assignments, stretch goals, tests.", "",
            "## Assessment-week pattern", "", MARK % "how a unit's last week runs.", "",
            "## Achievement categories across the course", "",
            "Knowledge and Understanding, %s, Communication, Application (the %s curriculum's names)." % (thinking, c["department"]), "",
            MARK % "how each category is weighted across the course's work."]))
        self.write(self.m("00_Admin/Final_Exam/exam_spec.md"), "# %s final exam spec\n\n**Weight:** %s%% of the final mark\n\n%s" % (self.code, ex["exam"], MARK % "length, parts, and what it covers."))
        urows = ["| %d | %s | %d weeks | %s%% |" % (u["n"], u["name"], len(u["weeks"]), fmt(weight_total(u["u"]["weight"]))) for u in self.units]
        if sb:
            urows.append("| %s | %s (optional) | {{%s_LENGTH}} | %s%% |" % (sb["block"], sb["name"], sb["block"], fmt(float(sb.get("weight") or 0))))
        if self.a.has_cp:
            urows.append("| CP | Culminating project | %d weeks | %s%% |" % (self.cp_weeks(), ex["culminating"]))
        self.write(self.m("00_Admin/Course_Outline.md"), "\n".join([
            "# %s: %s" % (self.code, c["title"]), "",
            "| | |", "|---|---|", "| Course code | %s |" % self.code, "| Grade | %s |" % c["grade"], "| Type | %s |" % c["type"],
            "| Prerequisite | %s |" % c["prerequisite"], "| Credit | %s |" % c["credit"], "| Teacher | %s |" % d["teacher"],
            "| Semester | {{SEMESTER}} |", "",
            "## Course description", "", MARK % "the course description, from the curriculum, in student language.", "",
            "## Units of study", "", "| Unit | Title | Length | Weight |", "|------|-------|--------|--------|", *urows, "",
            "## How your grade is calculated", "",
            "Classroom work %d%%, final evaluation %d%% (%s), attendance and participation %d%%." % (
                classroom, final, "written exam %s%%, culminating project %s%%" % (ex["exam"], ex["culminating"]) if self.a.has_cp else "the written exam", att), "",
            "## How class works", "", MARK % "the weekly rhythm in student language.", "",
            "## Course policies", "", MARK % "late work, academic integrity, devices.", "",
            "## Materials", "", MARK % "what students need.", "",
            "## Support", "", MARK % "extra help.", "",
            "## Islamic perspective", "", MARK % "how the course connects to Islamic values.", "",
            "## Important dates", "", "| Event | Date |", "|-------|------|", "| First class | {{FIRST_DAY}} |", "| Final exam | {{EXAM_DATE}} |"]))
        st = ["| %s | %s | {{%s_START}} | {{%s_END}} | %s%% |" % (u["id"], u["name"], u["id"], u["id"], fmt(weight_total(u["u"]["weight"]))) for u in self.units]
        self.write(self.m("00_Admin/Short_and_Long_Term_Plan_Template.md"), "\n".join([
            "<!-- Rehydration: fill every {{...}}, recompute the percentages, the totals must be 100. -->", "",
            "# %s Short and Long Term Plan" % self.code, "",
            "## Short-term plan", "", "| Unit | Unit Title | Start Time | End Time | Evaluation Percentage |", "|------|-----------|-----------|---------|----------------------|",
            *st, *(["| CP | Culminating project | {{CP_START}} | {{CP_END}} | %s%% |" % ex["culminating"]] if self.a.has_cp else []), "| **TOTAL** | | | | **100%** |", "",
            "## Long-term plan", "", "| EVALUATIONS | DUE DATES | TITLES OF EVALUATION | % OF GRADE |", "|---|---|---|---|",
            "| {{EVALUATION}} | {{DUE}} | {{TITLE}} | {{PCT}} |", "| **TOTAL** | | | **100%** |"]))
        self.keep(self.m("00_Admin/Course_Introduction"))
        self.keep(self.m("00_Admin/Emergency_Sub_Packets"))
        self.write(self.m("00_Admin/BOOTSTRAP_DELTAS.md"), deltas_text(self.code))
        if d.get("legacy"):
            self.write(self.m("00_Admin/Legacy_Reuse_Map.md"), "\n".join([
                "# %s Legacy Reuse Map" % self.code, "", "Approved by %s before content build." % d["teacher"], "",
                "## Hard rules", "", "1. No legacy expectation code may be carried over; every code is re-derived from the curriculum source.",
                "2. Strip on adaptation: dates, old course codes, version suffixes, names that do not follow the content rules.", "",
                "| Legacy asset | Verdict | New home |", "|--------------|---------|----------|", "", MARK % "the Adapt / Mine / Discard audit."]))
        if d.get("deployment"):
            self.write(self.m("00_Admin/Deployment_Checklist.md"), "\n".join([
                "# %s Deployment Checklist" % self.code, "",
                "One-time setup per deployment: the physical-world counterpart of rehydration.", "",
                "## Tooling", "", "- [ ] %s" % (MARK % "install and licensing"), "", "## Version control identity", "", "- [ ] ",
                "", "## Home access", "", "- [ ] ", "", "## Classroom platform", "", "- [ ] "]))

    def style_guide(self):
        c, d = self.cfg, self.d
        rows = ["| %s | %s | %s |" % (b, s, w) for b, s, _, w in [(r[0], r[1], r[2], r[3]) for r in self.block_rows()]]
        env = d.get("environment") or {}
        L = ["# %s Style Guide (course layer)" % self.code, "",
             "**This file is a thin course layer.** The rules live in the shared package:", "",
             "- `%s/style/Style_Guide_Core.md`" % STD,
             ] + (["- `%s/style/%s`" % (STD, d["conventions_file"])] if d.get("conventions_file") else []) + [
             "- `%s/assessment/Grading_Conventions.md`" % STD, "",
             "This layer adds only what is true of `%s` specifically. It may tighten shared rules; it never contradicts them." % self.code, "",
             "## 1. Course identity", "",
             "- **Code and name:** %s, %s" % (self.code, c["title"]),
             "- **Grade and type:** %s, %s" % (c["grade"], c["type"]),
             "- **Prerequisite:** %s" % c["prerequisite"],
             "- **Curriculum:** %s. Source of truth: `%s`" % (c["curriculum_document"], gla_rel(curriculum.page_path(self.code))),
             "- **Language and environment:** %s" % (d.get("language") or "no programming language"),
             "- **Feeder role:** %s" % c.get("feeder_role", ""), "",
             "## 2. Slot blocks (frozen; never renumber)", "",
             "| Block | Slots | What it is |", "|-------|-------|------------|", *rows, "",
             "Nominal size: %d slots." % self.nominal_slots()]
        rh = d.get("rhythms") or ["standard"]
        if len(rh) > 1:
            L += ["", "## 3. Weekly rhythms", "", "Rhythms: %s. %s" % (", ".join(rh), MARK % "each rhythm as a day-by-day table; D4 submits, D5 flex is cuttable, every day is sub-ready (Style Guide Core §8)."),
                  "", "| Unit | Rhythm |", "|------|--------|", *["| %s | %s |" % (u["id"], u["u"].get("rhythm", "standard")) for u in self.units]]
        if d.get("language"):   # a feature table only where there is code
            fdata = {"baseline": [], "rows": [{"from": "U%d.W%d" % (u["n"], k), "available": ""}
                                              for u in self.units for k in range(1, len(u["weeks"]) + 1)]}
            self.write(self.m("01_Standards/feature_availability.yaml"),
                       features.dump(fdata, self.code).replace("# baseline:", "# TODO(bootstrap): fill each row's available cell, then `gla features render`.\n# baseline:", 1))
            L += ["", "## 4. Feature availability by slot", "", features.render_table(fdata), "",
              MARK % "fill feature_availability.yaml (what each slot makes available) and render; add the course-wide ceilings here."]
        L += ["", "## 5. Environment and provenance", "",
              "- **In class:** %s" % env.get("in_class", ""), "- **At home:** %s" % env.get("at_home", ""), "- **Authorship evidence:** %s" % env.get("provenance", "")]
        L += ["", "## 6. Course-specific content rules", ""] + ["- %s" % t[0].upper() + t[1:] + "." for t in (d.get("typography") or [])]
        L += ["", MARK % "anything else true of this course only.", ""]
        if self.a.has_cp:
            L += ["## 7. Culminating project constraints", "", "See `%s/PROJECT_DECISIONS.md`." % self.cp_dir, ""]
        L += ["## 8. Pointers", "",
              "- Coverage map: `01_Standards/Curriculum_Coverage_Map.md`",
              "- Assessment plan: `00_Admin/Assessment_Plan.md`",
              "- Bootstrap decisions: `00_Admin/BOOTSTRAP_DELTAS.md`"]
        if d.get("legacy"):
            L.append("- Legacy reuse: `00_Admin/Legacy_Reuse_Map.md`")
        if d.get("deployment"):
            L.append("- Deployment: `00_Admin/Deployment_Checklist.md`")
        self.write(self.m("01_Standards/Style_Guide.md"), "\n".join(L))

    def rehydration(self):
        base = self.m(self.rh_dir)
        d = self.d
        Y = ["# %s rehydration parameters, read by the shared generator" % self.code,
             "# (the semester skill's rehydrate.py, run as `gla rehydrate`).",
             "# Rehydration_Guide.md and Compression_Table.md explain the reasoning; this",
             "# file holds the numbers and slot lists. Change both together.",
             "# Written by scaffold_course.py: week_plans name files author-week will write.",
             "schema: 1", "course: %s" % self.code, "", "sequence:",
             "  - block: INTRO", "    dir: master/00_Admin/Course_Introduction", "    days:"]
        for i, day in enumerate(d.get("intro_days") or [], 1):
            Y.append('      - { slot: INTRO.D%d, title: "%s", day_type: %s, sub_ready: false }' % (i, day["title"], day["day_type"]))
        for u in self.units:
            Y += ["  - block: %s" % u["id"], "    week_plans:"]
            Y += ["      - master/02_Units/%s/%s/week_plan.yaml" % (u["dir"], w) for w in u["weeks"]]
        if self.a.has_cp:
            cp = "master/%s" % self.cp_dir
            Y += ["  - block: CP", "    week_plans:", "      - %s/Launch_Week/week_plan.yaml" % cp]
            Y += ["      - %s/week_plan_W%d.yaml" % (cp, k) for k in range(2, self.cp_weeks() + 1)]
        sb = self.a.standby
        if sb:
            Y += ["", "modules:", "  - name: %s" % sb["config_key"], "    block: %s" % sb["block"], "    mode_key: modules.%s" % sb["config_key"], "    forms:", "      none:", "        week_plans: []"]
            for v in sb["variants"]:
                Y += ["      %s:" % v["value"], "        week_plans:"]
                weeks = v.get("weeks") or []
                if weeks:
                    Y += ["          - { path: master/%s/%s/W%d_%s/week_plan.yaml, instance_name: %s_W%d }" % (self.standby_dir, v["folder"], k, slug(w), sb["block"], k) for k, w in enumerate(weeks, 1)]
                else:
                    Y += ["          - { path: master/%s/%s/week_plan.yaml, instance_name: %s_%s }" % (self.standby_dir, v["folder"], sb["block"], slug(v["value"]).capitalize())]
            Y.append("    # TODO(bootstrap): placement_key, weights per form, outline rows, reserve_spill.")
        else:
            Y += ["", "modules: []"]
        flex, cp_flex = self.flex_slots()
        floor = self.nominal_slots() - len(self.d.get("intro_days") or []) - len(flex) - len(cp_flex)
        Y += ["", "# Tier 1 (and tier 2 for the culminating project) are the D5 flex days, which every",
              "# rhythm can lose (Standards' Compression_Framework.md). TODO(bootstrap): add any further",
              "# tiers this course's rhythms allow (Compression_Table.md); never copy a sibling's.",
              "compression:", "  floor: { slots: %d, blocks: [%s] }" % (floor, ", ".join([u["id"] for u in self.units] + (["CP"] if self.a.has_cp else []))),
              "  tiers:", "    - priority: 1", '      what: "D5 flex days, latest units first"',
              '      consequence: "Review and Q&A fold into D4\'s wrap segment"', "      slots: [%s]" % ", ".join(flex)]
        if cp_flex:
            Y += ["    - priority: 2", '      what: "Culminating project flex days"', '      consequence: "Build weeks tighten; milestones move a day earlier"',
                  "      slots: [%s]" % ", ".join(cp_flex)]
        self.write(base + "/rehydration.yaml", "\n".join(Y))
        rows = ["| %d | %s | %s | %s |" % (k, b, s, w) for k, (b, s, _, w) in enumerate(self.block_rows(), 1)]
        self.write(base + "/Rehydration_Guide.md", "\n".join([
            "# %s Rehydration Guide" % self.code, "",
            "The algorithm is `%s/rehydration/Rehydration_Framework.md`; the numbers the generator reads are in `rehydration.yaml` beside this file." % STD, "",
            "## Slot sequence", "", "| Order | Block | Slots | Notes |", "|-------|-------|-------|-------|", *rows, "",
            "Nominal size: %d slots.%s" % (self.nominal_slots(), " The %s block is a standby module (`%s`)." % (sb["block"], self.standby_dir) if sb else ""), "",
            "## Fit parameters", "", MARK % ("compression pointer and sanctioned floor, units and CP separately." if self.a.has_cp else "compression pointer and sanctioned floor."), "",
            "## Reserve-spill designation", "", MARK % "which block may spill into reserve days, if any.", "",
            "## Hard constraints", "", "- Each unit test sits in its unit's last week.", "- Assignment windows are 7 to 10 class days.",
            *(["- Culminating demos end at least 2 class days before the exam period."] if self.a.has_cp else []), "",
            MARK % ("short-unit D1 pins and CP placement." if self.a.has_cp else "short-unit D1 pins."), "",
            "## Course invariants", "", "- Weights total 100.", "- Cross-cutting anchors survive compression." if (d["curriculum"].get("cross_cutting")) else "- Load-bearing artifacts survive compression.", "",
            "## Weighting recomputation", "", MARK % "how weights fold when an artifact is cut.", "",
            "## Mid-semester adjustments", "", "Use the semester skill's mid-semester mode (`build_semester.py recalendar`).", "",
            "## Semester config", "",
            ("A course template lives beside this file (`Semester_Config_Template.yaml`)." if d["semester_config"] == "course"
             else "The shared template, `%s/rehydration/Semester_Config_Template.yaml`." % STD)]))
        self.write(base + "/Compression_Table.md", "\n".join([
            "# %s Compression Table" % self.code, "",
            "Cut in priority order, stopping as soon as the plan fits. Never cut a teach, assess, or hand-out day. The method is `%s/rehydration/Compression_Framework.md`." % STD, "",
            "Nominal size: %d slots." % self.nominal_slots(), "",
            "| Priority | Cut | Slots freed | Consequence |", "|----------|-----|-------------|-------------|",
            "| 1 | D5 flex days, latest units first | %d | Review and Q&A fold into D4's wrap segment |" % len(flex),
            *(["| 2 | Culminating project flex days | %d | Build weeks tighten; milestones move a day earlier |" % len(cp_flex)] if cp_flex else []), "",
            MARK % "any further tiers each block's rhythm allows (studio blocks free days only through flex cuts); star the manual, below-floor tiers.", "",
            "## Floor", "", "%d unit and project slots after the tiers above; rehydration.yaml holds the same number." % floor, "",
            "## After cutting", "", "Every cut is logged in the instance's GENERATION_REPORT.md."]))
        if d["semester_config"] == "course":
            src = os.path.join(paths.STANDARDS, "rehydration", "Semester_Config_Template.yaml")
            with open(src, encoding="utf-8") as f:
                self.write(base + "/Semester_Config_Template.yaml", "# %s semester config template (from the shared one).\n" % self.code + f.read())

    def master_index(self):
        rows = ["| %s | %s | %s | %s |" % r for r in self.block_rows()]
        tree = ["master/", "├── MASTER_INDEX.md", "├── 00_Admin/", "├── 01_Standards/", "├── 02_Units/"]
        tree += ["│   ├── %s/" % u["dir"] for u in self.units]
        if self.standby_dir:
            tree.append("├── %s/" % self.standby_dir)
        if self.cp_dir:
            tree.append("├── %s/" % self.cp_dir)
        tree.append("└── %s/" % self.rh_dir)
        reg = ["", "### Root", "", "- `course.yaml`: the parameters every shared skill reads.", "- `gdocs_manifest.yaml`: Google Docs conversion rules.", ""]
        sections = {}
        for rel in self.written:
            if not rel.startswith("master/") or rel.endswith("MASTER_INDEX.md"):
                continue
            top = rel.split("/")[1]
            sections.setdefault(top, []).append(rel[len("master/"):])
        for top in sorted(sections):
            reg += ["### %s" % top, ""] + ["- `%s`: skeleton (scaffold)" % r for r in sections[top]] + [""]
        self.write(self.m("MASTER_INDEX.md"), "\n".join([
            "# %s Master Index" % self.code, "",
            "The date-agnostic master course. Read in this order: `01_Standards/Style_Guide.md`, `01_Standards/Curriculum_Coverage_Map.md`, `00_Admin/Assessment_Plan.md`, then the unit overviews.", "",
            "Slot IDs are frozen at the first commit. If content moves, the week plan changes, never the IDs.", "",
            "## Slot blocks", "", "| Block | Slots | Weeks | What it is |", "|-------|-------|-------|------------|", *rows, "",
            "## Weekly rhythms", "", ", ".join(self.d.get("rhythms") or ["standard"]) + ". See `01_Standards/Style_Guide.md`.", "",
            "## Layout", "", "```", *tree, "```", "",
            "## Inside a week folder", "", "`week_plan.yaml`, `D<n>_Lesson_<Topic>.md`%s, `EX_<Name>.md` with `EX_<Name>_KEY.md`%s, `REF_<Topic>.md`." % (
                ", `D<n>_Slides_<Topic>.html` with its `_GUIDE.md`" if self.d.get("decks", True) else "",", `BRIEF_<Name>.md` with `BRIEF_<Name>_MARKING.md`" if self.d.get("studio") else ""), "",
            "## Shared standards package", "", "`%s/` in the GLA install (`gla where` prints its folder); referenced, never copied." % STD, "",
            "## Rules that live here", "", "- Register every new file below.", "- No version suffixes; git is the history.", "- No dates outside `instances/`.",
            "- Record every bootstrap decision in `00_Admin/BOOTSTRAP_DELTAS.md`.", "",
            "## File registry", *reg]))

    def readme(self):
        c = self.cfg
        L = ["# %s: %s" % (self.code, c["title"]), "",
             "A detached-master curriculum repo for the GLA course %s." % self.code, "",
             "- `master/`: the date-agnostic course (start at `master/MASTER_INDEX.md`).",
             "- `instances/`: dated semester rehydrations, made by the semester skill.",
             "- Shared standards: `%s/` in the GLA install (`gla where` prints its folder)." % STD,
             "- Curriculum source: `%s`." % gla_rel(curriculum.page_path(self.code)), "",
             "Feeder role: %s" % c.get("feeder_role", ""), "",
             "Bootstrap decisions: `master/00_Admin/BOOTSTRAP_DELTAS.md`."]
        self.write("README.md", "\n".join(L))


def abridge(text, n=90):
    t = re.sub(r"\s+", " ", text).strip().rstrip(";.")
    t = re.sub(r"\s*\((?:e\.g\.|for example)[^)]*\)", "", t)
    t = t[0].upper() + t[1:] if t else t
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."


DELTAS_SCHEMA = """## Entry schema

### D-NNN: <short title>

- **Decision:** what was decided.
- **Scope:** `agnostic` | `course-specific` | `curriculum-era-specific`
  - `agnostic`: would hold for any GLA course. The skill encodes it as a rule.
  - `course-specific`: true only for {code}. The skill ignores it, or exposes it
    as a parameter.
  - `curriculum-era-specific`: true for one curriculum era and not another. The
    skill needs a branch here.
- **Pattern bend:** did the existing course pattern need changing? If so, what was
  the pattern, and what did it become? Write `none` if it fit as-is.
- **Future-course question:** the question a future course would have to answer
  at this same point, phrased as a question. Write `none` if it doesn't
  generalize.
- **Artifacts:** files created or changed by this decision.

---"""


def deltas_text(code):
    return "\n".join([
        "# Bootstrap Deltas: %s" % code, "",
        "Running log kept while building %s. Input to the next revision of `bootstrap-gla-course`." % code, "",
        "Append one entry per decision. Do not edit past entries; if a decision is reversed, add a new entry that supersedes it and say so.", "",
        "---", "", DELTAS_SCHEMA.replace("{code}", code), "", "## Entries", ""])


# --------------------------------------------------------------------- main

def print_report(a):
    for w in a.warnings:
        print("WARN  " + w)
    for e in a.errors:
        print("ERROR " + e)
    print("%s: %d error(s), %d warning(s)" % (a.code or "answers", len(a.errors), len(a.warnings)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("code")
    i.add_argument("--out")
    k = sub.add_parser("codes")
    k.add_argument("code")
    c = sub.add_parser("check")
    c.add_argument("answers")
    b = sub.add_parser("build")
    b.add_argument("answers")
    b.add_argument("--dest", required=True)
    b.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "codes":
        try:
            print(codes_text(args.code.upper()), end="")
        except FileNotFoundError as e:
            print("ERROR: %s" % e)
            return 1
        return 0

    if args.cmd == "init":
        code = args.code.upper()
        if not os.path.exists(curriculum.page_path(code)):
            print("ERROR: %s is not in the curriculum data (%s)" % (code, curriculum.page_path(code)))
            return 1
        text = init_text(code)
        out = args.out or "%s_answers.yaml" % code
        if os.path.exists(out):
            print("ERROR: %s exists; remove it or pass another --out" % out)
            return 1
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote %s: %d TODO field(s) to fill" % (out, len(todos(yaml.safe_load(text)))))
        return 0

    with open(args.answers, encoding="utf-8") as f:
        a = Answers(yaml.safe_load(f) or {}).check()
    print_report(a)
    if a.errors:
        return 1
    if args.cmd == "check":
        return 0
    dest = os.path.abspath(args.dest)
    if os.path.isdir(dest) and os.listdir(dest) and not args.force:
        print("ERROR: %s exists and is not empty" % dest)
        return 1
    bld = Builder(a, dest).build()
    print("\nwrote %d files under %s" % (len(bld.written), dest))
    if bld.marked:
        print("\nTODO(bootstrap) prose to write (%d files):" % len(bld.marked))
        for rel in bld.marked:
            print("  " + rel)
    print("\nNext: git init and commit the scaffold (slot numbering freezes at this commit), then run"
          "\n  python3 %s --root %s --only %s" % (os.path.join(paths.SKILLS, "_tools", "check_course.py"), dest, SELF_CHECK))
    return 0


if __name__ == "__main__":
    sys.exit(main())

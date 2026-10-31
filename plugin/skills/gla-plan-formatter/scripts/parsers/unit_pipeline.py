"""
unit_pipeline: a unit plan spec from a GLA course repo (the CS pipeline shape),
for `build_plan.py --type unit --pipeline COURSE_ROOT --instance SEM --unit N`.

Sources, all under COURSE_ROOT:
  course.yaml                                   code, title, grade, type, teacher, teacher_formal
  master/02_Units/U<N>_*/unit_overview.md       title, weight line, expectations line, the slot
                                                tables, the ## Evaluations table, reference sheets
  instances/<SEM>/week_plans/U<N>_W*.yaml       dated days, learning goals, AFL/AAL, Islamic
                                                expectations, character education
  instances/<SEM>/Short_and_Long_Term_Plan.md   evaluation titles, due dates, instance weights
  instances/<SEM>/calendar.yaml                 slot -> date, when the plan above is absent
  the bundled curriculum (scripts/curriculum.py) expectation wording, numbered by position

Only the teacher's sources are written into the document. Everything that was
derived (the assessed/covered split, day counts, the compact lesson rows) is
listed under spec["review"], and every area that needs drafting (big idea,
enduring understandings, essential questions, achievement descriptions, the
variety ticks, reflection exemplars) is emitted empty with its own review note.
Claude fills those after the teacher consents, then rebuilds with --spec.

Runs in Claude Code inside a course repo; it needs PyYAML.
"""

import datetime
import glob
import os
import re

import categories
from parsers._course import dedash, load_course_yaml, semester_label

CODE_RX = re.compile(r"\b([A-Z]{1,3}\d+\.\d+)(?:\s*[–-]\s*([A-Z]{0,3}\d+\.\d+))?")
OVERALL_RX = re.compile(r"\b([A-Z]{1,3}\d+)\b(?!\.)")
SLOT_RX = re.compile(r"^\| (U\d+\.W\d+\.D\d+) \|")
ISO_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PCT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*%")

COMPACT_WORDING = {
    "teach": ("Teach with slides and live coding: {focus}",
              "Answer checkpoint questions, trace examples, and take notes"),
    "lab": ("Lead the guided lab and check each student's setup", "{focus}"),
    "assess": ("Supervise the unit test", "{focus}"),
    "handout": ("Hand out {item}; circulate and give feedback", "{focus}"),
    "due_graded": ("Circulate, give feedback, and collect {item}", "{focus}"),
    "due_formative": ("Run {item} and give descriptive feedback", "{focus}"),
    "due_assignment": ("Lead the review and collect {item}", "{focus}"),
    "other": ("Circulate, answer questions, and give feedback", "{focus}"),
}
ASSESS_WORDING = {
    "assess": "Unit test (of learning)",
    "due_assignment": "{item} due (of learning)",
    "due_graded": "{item} submitted and marked (of learning)",
    "due_formative": "{item}, feedback only (as learning)",
    "teach": "Checkpoint questions (for learning)",
    "lab": "Observation during the guided lab (for learning)",
    "flex": "Conversations during review (for learning)",
    "other": "Observation of exercise progress (for learning)",
}
# The second entry is renamed per subject (categories.names); this is the default.
ACHIEVEMENT = ["Knowledge / Understanding", "Thinking", "Communication", "Application"]
REFLECTION = ["Understanding of the big idea", "Misconceptions addressed",
              "Pacing and design", "Engagement and differentiation"]
VARIETY = [
    ("Direct Instruction", ["Slide-deck lessons with checkpoints", "Live coding", "Whiteboard analogies", "Guided lab"]),
    ("Hands-on Practice", ["Programming exercises", "Paper-based practice", "Tracing and debugging",
                           "Design with flowcharts or pseudocode"]),
    ("Discussion and Collaboration", ["Class discussion", "Think-pair-share", "Peer code review", "Case study"]),
    ("Assessment Experiences", ["Rubric-marked assignment", "Unit test", "Self-check and review sheet",
                                "Formative feedback task"]),
]


class PipelineError(ValueError):
    pass


# ----------------------------------------------------------------------------
# codes
# ----------------------------------------------------------------------------
def expand(text):
    """'A4.1-A4.5, B3.3' -> ['A4.1', 'A4.2', ..., 'B3.3']."""
    out = []
    for a, b in CODE_RX.findall(text or ""):
        if b:
            if not b[0].isalpha():
                b = re.match(r"[A-Z]+", a).group(0) + b
            pa, pb = a.rsplit(".", 1), b.rsplit(".", 1)
            if pa[0] == pb[0]:
                out.extend(f"{pa[0]}.{i}" for i in range(int(pa[1]), int(pb[1]) + 1))
            else:
                out.extend([a, b])
        else:
            out.append(a)
    return out


def _key(code):
    m = re.match(r"([A-Z]+)(\d+)\.(\d+)", code)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else (code, 0, 0)


def order(codes):
    return sorted(set(codes), key=_key)


def slot_key(slot):
    m = re.match(r"U(\d+)\.W(\d+)\.D(\d+)", slot or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ----------------------------------------------------------------------------
# sources
# ----------------------------------------------------------------------------
def _table_rows(lines, start):
    """Rows of the pipe table that begins at lines[start] (a header row): list of dicts."""
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    rows = []
    for ln in lines[start + 2:]:
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(dict(zip(header, cells)))
    return rows


def parse_overview(text):
    lines = text.splitlines()
    ov = {"title": "", "weight": None, "primary": [], "reinforced": [], "slots": [],
          "evaluations": [], "assignment_overalls": [], "refs": []}
    m = re.search(r"^# Unit \d+: (.+)$", text, re.M)
    ov["title"] = dedash(m.group(1)) if m else ""
    m = re.search(r"\*\*Weight:\*\*\s*(\d+)%", text)
    ov["weight"] = int(m.group(1)) if m else None
    m = re.search(r"\*\*Expectations \(primary\):\*\*\s*(.+)$", text, re.M)
    if m:
        main, _, reinf = m.group(1).partition("reinforces")
        ov["primary"], ov["reinforced"] = order(expand(main)), order(expand(reinf))
    for ln in lines:
        if SLOT_RX.match(ln):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln)[1:5]]
            ov["slots"].append({"slot": cells[0], "type": cells[1], "topic": cells[2],
                                "notes": cells[3] if len(cells) > 3 else ""})
    for i, ln in enumerate(lines):
        if ln.startswith("| Item ") and "Weight" in ln:
            ov["evaluations"] = _table_rows(lines, i)
            break
    m = re.search(r"\*\*Assignment hand-out:\*\*(.+)$", text, re.M)
    if m:
        ov["assignment_overalls"] = OVERALL_RX.findall(m.group(1))
    ov["refs"] = re.findall(r"- `(REF_\w+)\.md`", text)
    return ov


def _load_yaml(path):
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise PipelineError("the pipeline parser needs PyYAML (pip install pyyaml)") from e
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _week_num(path):
    m = re.search(r"_W(\d+)\.yaml$", path)
    return int(m.group(1)) if m else 0


def _pct(text):
    m = PCT_RX.search(text or "")
    return float(m.group(1)) if m else None


def _norm_name(s):
    s = re.sub(r"^(EX_|Assignment_|EX |Assignment )", "", (s or "").strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# ----------------------------------------------------------------------------
# rules
# ----------------------------------------------------------------------------
def graded_evaluations(ov, lrp_rows):
    """The overview's evaluation rows with a graded flag, the instance weight when
    the plan lists the item, and the codes declared in an Assessed column."""
    by_name = {_norm_name(r.get("title")): r for r in lrp_rows}
    out = []
    for r in ov["evaluations"]:
        item = r.get("Item", "")
        inst = by_name.get(_norm_name(item))
        weight = _pct(inst["weight"]) if inst else _pct(r.get("Weight"))
        out.append({
            "item": item, "kind": r.get("Kind", ""), "handed_out": r.get("Handed out", ""),
            "due": r.get("Due", ""), "graded": weight is not None and weight > 0,
            "weight": weight, "instance": inst, "declared": expand(r.get("Assessed", "")),
        })
    return out


def split_expectations(ov, evals):
    """(assessed, covered, rule_notes) per the documented rule."""
    slots = ov["slots"]
    idx = {s["slot"]: i for i, s in enumerate(slots)}
    primary, reinforced = ov["primary"], ov["reinforced"]
    assessed = set()
    for e in evals:
        if not e["graded"]:
            continue
        assessed.update(c for c in e["declared"] if c in primary or c in reinforced)      # (a)
        if e["handed_out"] in idx and e["due"] in idx:                                       # (b)
            wk = slot_key(e["handed_out"])[:2]
            start = next(i for i, s in enumerate(slots) if slot_key(s["slot"])[:2] == wk)
            for s in slots[start:idx[e["due"]] + 1]:
                assessed.update(c for c in expand(s["notes"]) if c in primary)
    for oc in ov["assignment_overalls"]:                                                     # (c)
        assessed.update(c for c in primary if c.startswith(oc + "."))
    for s in slots:                                                                          # (d)
        if s["type"] == "assess":
            assessed.update(c for c in expand(s["notes"]) if c in primary or c in reinforced)
    assessed = order(assessed)
    covered = [c for c in order(primary + reinforced) if c not in assessed]
    return assessed, covered


# ----------------------------------------------------------------------------
# lesson rows
# ----------------------------------------------------------------------------
def _day_event(day, evals, slots):
    """(kind, item) for the day: what the evaluations table says happens on this slot."""
    slot = day.get("slot", "")
    stype = next((s["type"] for s in slots if s["slot"] == slot), day.get("day_type"))
    if stype == "assess" or day.get("day_type") == "assess":
        return "assess", "the unit test"
    for e in evals:
        if e["due"] == slot:
            name = _pretty(e["item"])
            if e["kind"].lower().startswith("assignment"):
                return "due_assignment", name
            return ("due_graded" if e["graded"] else "due_formative"), name
    for e in evals:
        if e["handed_out"] == slot and not e["kind"].lower().startswith("assignment"):
            return "handout", _pretty(e["item"])
    t = day.get("day_type", "")
    return (t if t in ("teach", "lab", "flex") else "other"), ""


def _pretty(item):
    item = re.sub(r"^EX_", "Exercise: ", item)
    item = re.sub(r"^Assignment_", "Assignment: ", item)
    return item.replace("_", " ").replace("**", "").strip()


def compact_row(day, event, item):
    focus = dedash(day.get("focus", ""))
    kind = event if event in COMPACT_WORDING else "other"
    t, s = COMPACT_WORDING[kind]
    return t.format(focus=focus, item=item), s.format(focus=focus, item=item)


def split_activities(day):
    """Full text: activity teacher/student keys when present, else an opening-word heuristic."""
    tch, stu = [], []
    for a in day.get("activities", []) or []:
        if a.get("teacher") or a.get("student"):
            if a.get("teacher"):
                tch.append(dedash(a["teacher"]))
            if a.get("student"):
                stu.append(dedash(a["student"]))
            continue
        w = dedash(a.get("what", ""))
        if re.match(r"(Students?|Groups?|Pairs?)\b", w):
            stu.append(w)
        elif re.match(r"(Deck|Live coding|Opener|Hand out|Refresher|Walk|Checkpoint|Remind|Model|Demo|Return|Debrief|Board|Teacher)", w, re.I):
            tch.append(w)
        elif day.get("day_type") == "teach":
            tch.append(w)
        else:
            stu.append(w)
    return "; ".join(tch), "; ".join(stu)


def assess_text(event, item):
    return ASSESS_WORDING.get(event, ASSESS_WORDING["other"]).format(item=item)


# ----------------------------------------------------------------------------
# spec
# ----------------------------------------------------------------------------
def _fmt(iso, fmt):
    return datetime.date.fromisoformat(iso).strftime(fmt)


def _lrp_rows(root, instance, unit):
    path = os.path.join(root, "instances", instance, "Short_and_Long_Term_Plan.md")
    if not os.path.exists(path):
        return [], None
    from parsers import long_range_plan
    with open(path, "r", encoding="utf-8") as fh:
        spec = long_range_plan.parse(fh.read(), path)
    rows, g = [], None
    for r in (spec.get("long_term") or {}).get("rows", []):
        g = r.get("group") or g
        m = re.match(r"UNIT (\d+)", (g or "").upper())
        if m and m.group(1) == str(unit):
            rows.append(r)
    return rows, path


def _calendar_dates(root, instance):
    path = os.path.join(root, "instances", instance, "calendar.yaml")
    if not os.path.exists(path):
        return {}
    cal = _load_yaml(path)
    return {d.get("slot"): str(d.get("date")) for d in cal.get("days", []) if d.get("slot")}


def build_spec(root, instance, unit, full_activities=False):
    import curriculum

    root = os.path.abspath(root)
    unit = str(unit).lstrip("U")
    cfg_path = os.path.join(root, "course.yaml")
    if not os.path.exists(cfg_path):
        raise PipelineError(f"no course.yaml at {root}")
    cfg = load_course_yaml(cfg_path)
    code, title = str(cfg.get("code", "")), str(cfg.get("title", ""))
    grade = str(cfg.get("grade", "")) or (code[3] and {"1": "9", "2": "10", "3": "11", "4": "12"}.get(code[3], ""))

    ov_paths = glob.glob(os.path.join(root, "master", "02_Units", f"U{unit}_*", "unit_overview.md"))
    if not ov_paths:
        raise PipelineError(f"no master/02_Units/U{unit}_*/unit_overview.md under {root}")
    with open(ov_paths[0], "r", encoding="utf-8") as fh:
        ov = parse_overview(fh.read())
    unit_count = len(glob.glob(os.path.join(root, "master", "02_Units", "U*")))

    wp_paths = sorted(glob.glob(os.path.join(root, "instances", instance, "week_plans", f"U{unit}_W*.yaml")), key=_week_num)
    if not wp_paths:
        raise PipelineError(f"no week plans for U{unit} under instances/{instance}/week_plans")
    weeks = [_load_yaml(p) for p in wp_paths]
    days = [d for w in weeks for d in (w.get("daily_lessons") or []) if ISO_RX.match(str(d.get("date", "")))]
    cut = [d.get("slot") for w in weeks for d in (w.get("daily_lessons") or []) if not ISO_RX.match(str(d.get("date", "")))]
    if not days:
        raise PipelineError("no dated days in the week plans; is this an instance, not the master?")

    lrp_rows, lrp_path = _lrp_rows(root, instance, unit)
    evals = graded_evaluations(ov, lrp_rows)
    slot_dates = {} if lrp_rows else _calendar_dates(root, instance)
    wording = curriculum.specific_expectations(code)
    strands = curriculum.strand_names(code)
    assessed, covered = split_expectations(ov, evals)

    items, source_bits = [], [os.path.relpath(ov_paths[0], root),
                              f"instances/{instance}/week_plans/U{unit}_W1..W{len(weeks)}"]
    if lrp_path:
        source_bits.append(os.path.relpath(lrp_path, root))
    source_bits.append("the bundled curriculum")

    def note(section, text, risk=None):
        it = {"section": section, "text": text}
        if risk:
            it["risk"] = risk
        items.append(it)

    # overview grid
    first, last = str(days[0]["date"]), str(days[-1]["date"])
    sem = semester_label(instance)
    due_bits = []
    for e in evals:
        if e["kind"].lower().startswith(("assignment", "test")) and e["graded"]:
            if e["instance"]:
                when, w = e["instance"].get("due", ""), e["instance"].get("weight", "")
            else:
                when, w = slot_dates.get(e["due"], e["due"]), f"{e['weight']:g}%" if e["weight"] else ""
            due_bits.append(f"{_pretty(e['item'])} due {when}" + (f" ({w})" if w else ""))
    strands_used = sorted({c[0] for c in ov["primary"] + ov["reinforced"]})
    overview = {
        "Course": ", ".join(b for b in (code, title, f"Grade {grade}" if grade else "", str(cfg.get("type", ""))) if b),
        "Grade": f"Grade {grade}" if grade else "",
        "Unit Title": f"Unit {unit}: {ov['title']}",
        "Unit #": f"Unit {unit} of {unit_count}",
        "Number of Days": f"{len(days)} instructional days ({_fmt(first, '%B %-d, %Y')} to {_fmt(last, '%B %-d, %Y')})",
        "Culminating Task Due": "; ".join(due_bits),
        "Core Texts": "No textbook. Unit reference sheets: " + ", ".join(_pretty(r.replace("REF_", "")) for r in ov["refs"]) if ov["refs"] else "No textbook.",
        "Strands Addressed": "; ".join(f"{L}. {strands.get(L, '')}".rstrip(". ") for L in strands_used),
    }
    note("Overview grid", f"Number of Days counts the {len(days)} dated week-plan days" + (f"; cut by compression: {', '.join(cut)}." if cut else "."))
    note("Overview grid", "Culminating Task Due names the unit's graded assignment and test with their dates and weights; there is no single culminating task per unit.")
    note("Overview grid", "Core Texts lists the reference sheets named in the unit overview.")
    if not due_bits:
        note("Overview grid", "No graded assignment or test was found in the unit's evaluation table.", "high")
    if ov["weight"] is not None and lrp_rows:
        inst_total = sum(_pct(r.get("weight")) or 0 for r in lrp_rows)
        if abs(inst_total - ov["weight"]) > 0.01:
            note("Overview grid", f"The instance plan gives this unit {inst_total:g}% in total; the master unit overview says {ov['weight']}%. The instance value was used.", "high")
    if not lrp_rows:
        note("Overview grid", "No Short_and_Long_Term_Plan.md in the instance; due dates come from calendar.yaml and weights from the master overview.")

    # expectations
    def row(c):
        return f"{c}: {wording[c]}" if c in wording else c
    missing = [c for c in assessed + covered if c not in wording]
    exp_rows = []
    for L in strands_used:
        a = [row(c) for c in assessed if c[0] == L]
        c_ = [row(c) for c in covered if c[0] == L]
        if a or c_:
            exp_rows.append({"strand": f"{L}. {strands.get(L, '')}".rstrip(". "),
                             "assessed": a or ["None this unit"], "covered": c_ or ["None this unit"]})
    note("B. Curriculum Expectations",
         "Assessed versus covered was split by rule: a code is assessed when a graded evaluation (one with a weight) declares it, "
         "when it is taught between the start of a graded evaluation's hand-out week and its due slot, when the assignment names its "
         "overall expectation, or when a test slot names it. Everything else taught or reinforced is covered. "
         f"Assessed: {', '.join(assessed) or 'none'}. Covered: {', '.join(covered) or 'none'}. Move codes as you see fit.")
    note("B. Curriculum Expectations", "Expectation wording comes from the bundled curriculum; codes are assigned by position under each overall expectation, so spot check a few against the ministry PDF.")
    if missing:
        note("B. Curriculum Expectations", f"No wording found for {', '.join(missing)}; the code stands alone.", "high")

    # learning goals, AFL/AAL/AOL, Islamic perspective
    goal_blocks, isl_blocks = [], []
    for w in weeks:
        md = w.get("metadata", {}) or {}
        head = f"Week {md.get('week', '')}: {dedash(md.get('week_title', ''))}"
        goal_blocks.append({"type": "label", "text": head})
        for lg in w.get("learning_goals", []) or []:
            goal_blocks.append({"type": "para", "text": f"**{dedash(lg.get('goal', ''))}**"})
            goal_blocks.append({"type": "bullets", "items": [dedash(x) for x in lg.get("success_criteria", []) or []]})
        ie, ce = w.get("islamic_expectations") or {}, w.get("character_education") or {}
        isl_blocks.append({"type": "label", "text": head})
        if ie:
            isl_blocks.append({"type": "para", "text": f"**{dedash(ie.get('focus', ''))}** {dedash(ie.get('connection', ''))}".strip()})
        if ce:
            isl_blocks.append({"type": "para", "text": f"**Character education ({', '.join(ce.get('values', []) or [])}):** {dedash(ce.get('how', ''))}"})

    def gather(key):
        seen = []
        for w in weeks:
            for x in (w.get("assessment") or {}).get(key, []) or []:
                x = dedash(x)
                if x not in seen:
                    seen.append(x)
        return seen
    aol = []
    for e in evals:
        if e["graded"]:
            if e["instance"]:
                aol.append(f"{e['instance'].get('label', '').title()}: {e['instance'].get('title', '')}, due {e['instance'].get('due', '')} ({e['instance'].get('weight', '')})")
            else:
                aol.append(f"{_pretty(e['item'])}, due {slot_dates.get(e['due'], e['due'])}" + (f" ({e['weight']:g}%)" if e["weight"] else ""))
        else:
            aol.append(f"{_pretty(e['item'])}: formative, feedback only")
    note("Assessment", "Assessment for and as learning were collected from the week plans with duplicates removed; some items carry slot IDs.")
    note("Assessment", "Assessment of learning lists the instance plan's graded items plus the formative tasks in the unit overview.")

    # lesson table
    lessons = []
    slot_notes = {s["slot"]: s["notes"] for s in ov["slots"]}
    for i, day in enumerate(days, 1):
        event, item = _day_event(day, evals, ov["slots"])
        if full_activities:
            t, s = split_activities(day)
            t = t or compact_row(day, event, item)[0]
            s = s or compact_row(day, event, item)[1]
        else:
            t, s = compact_row(day, event, item)
        codes = ", ".join(order(expand(slot_notes.get(day.get("slot"), ""))))
        if not codes:
            wk = next((w for w in weeks if str(day.get("slot", "")).startswith(str((w.get("metadata") or {}).get("slot_prefix", "\0")))), None)
            codes = ", ".join((wk.get("curriculum_expectations") or {}).get("specific", []) or []) if wk else ""
        lessons.append({"num": str(i), "date": _fmt(str(day["date"]), "%a %b %-d"),
                        "topic": _pretty(dedash(day.get("title", ""))),
                        "teacher": t, "student": s, "assessment": assess_text(event, item),
                        "expectations": codes or "Review of unit expectations"})
    if full_activities:
        note("D. Lesson Sequence Overview", "Teacher and student columns carry the week plans' activities; where an activity has no teacher/student keys, an opening-word rule chose the column.")
    else:
        std = "; ".join(f"{k}: \"{v[0]}\"" for k, v in COMPACT_WORDING.items())
        note("D. Lesson Sequence Overview", f"Compact rows: the teacher column is one line of standard wording by day type ({std}); the student column is the week plan's focus line (teach days: \"{COMPACT_WORDING['teach'][1]}\"). Full activities stay in the week plans. Check that the wording fits how you run each day.")
    note("D. Lesson Sequence Overview", "The Assessment column was derived from the evaluations table and the day type, not written per lesson.")
    note("D. Lesson Sequence Overview", "Specific Expectations per row come from the unit overview's slot notes, or from the week plan's expectation list when the slot names none.")
    note("Document", "Em dashes in week plan text were replaced with commas.")

    teacher = cfg.get("teacher_formal") or cfg.get("teacher") or ""
    spec = {
        "subtitle": f"Unit Planning Template  |  Backward Design  |  {sem}".rstrip(" |"),
        "context": {"course_line": f"{code}: {title}", "context_line": f"Unit {unit}: {ov['title']}  |  Unit {unit} of {unit_count}"},
        "overview": overview,
        "sections": [
            {"kind": "step", "text": "STEP 1: IDENTIFY DESIRED RESULTS"},
            {"kind": "labeled", "label": "A. Big Idea for This Unit",
             "review": "Big idea, enduring understandings, and essential questions are empty: draft them only with the teacher's consent.",
             "blocks": [{"type": "para", "text": ""},
                        {"type": "label", "text": "Enduring Understandings:"}, {"type": "bullets", "items": []},
                        {"type": "label", "text": "Essential Questions:"}, {"type": "bullets", "items": []}]},
            {"kind": "heading", "text": "B. Curriculum Expectations"},
            {"kind": "expectations", "rows": exp_rows},
            {"kind": "labeled", "label": "C. Learning Goals and Success Criteria", "blocks": goal_blocks,
             "review": "Learning goals and success criteria were copied from the week plans."},
            {"kind": "step", "text": "STEP 2: DETERMINE ACCEPTABLE EVIDENCE"},
            {"kind": "labeled", "label": "Assessment", "blocks": [
                {"type": "label", "text": "Assessment for Learning:"}, {"type": "bullets", "items": gather("for_learning")},
                {"type": "label", "text": "Assessment as Learning:"}, {"type": "bullets", "items": gather("as_learning")},
                {"type": "label", "text": "Assessment of Learning:"}, {"type": "bullets", "items": aol}]},
            {"kind": "heading", "text": "Achievement Chart Descriptions"},
            {"kind": "achievement", "review": "All four achievement chart descriptions are empty: draft only with consent.",
             "categories": [{"name": n, "desc": ""}
                            for n in categories.names(ACHIEVEMENT, code)]},
            {"kind": "step", "text": "STEP 3: PLAN LEARNING EXPERIENCES"},
            {"kind": "heading", "text": "D. Lesson Sequence Overview"},
            {"kind": "lesson_table", "rows": lessons},
            {"kind": "labeled", "label": "E. Islamic Perspective and Character Education", "blocks": isl_blocks,
             "review": "Copied from the week plans' Islamic expectations and character education blocks."},
            {"kind": "variety", "label": "Variety of Learning Experiences",
             "review": "No experience is ticked: tick the ones the lesson table evidences, with consent.",
             "groups": [{"intro": "The following experiences are incorporated into this unit."}] +
                       [{"label": lab, "items": [[x, False] for x in xs]} for lab, xs in VARIETY]},
            {"kind": "heading", "text": "F. Unit Reflection"},
            {"kind": "reflection", "review": "Reflection exemplars are empty: draft only with consent. The evidence column stays for post-unit use.",
             "rows": [{"criteria": c, "exemplar": "", "evidence": ""} for c in REFLECTION]},
        ],
        "review": {"source": "; ".join(source_bits) + (f"; teacher {teacher}" if teacher else ""),
                   "gaps": [], "items": items},
    }
    return spec

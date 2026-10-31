"""The instance documents built from a rehydration Plan: the Assessment
Register, the Short and Long Term Plan, and the resolved Course Outline.

Per-item weights come from each unit overview's Evaluations table (kept equal
to Assessment_Plan.md by check_course.py), module items and weight moves from
rehydration.yaml, the final-evaluation buckets from course.yaml, dates from
the plan, out-of from each document's **Marks:** line, and the register's
"What it is" text from week plan evaluations' `summary`.
"""
import glob
import os
import re

from . import mdtable
from .rehydrate import fmt_long, fmt_short

MARKS_RE = re.compile(r"^\*\*(?:Marks|Points):\*\*\s*(.+)$", re.M)   # ICD2O assignments write **Points:**


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_prefix(name):
    return re.sub(r"^(EX|BRIEF|Assignment)_", "", name).replace("_", " ")


def fmt_day(d):
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def fmt_range(a, b):
    if a == b:
        return fmt_short(a)
    if (a.year, a.month) == (b.year, b.month):
        return "%s %d to %d, %d" % (a.strftime("%b"), a.day, b.day, a.year)
    return "%s to %s" % (fmt_short(a), fmt_short(b))


def out_of(marks_text):
    """'/10' -> '/10'; '20 points (rubric) + up to 2 bonus' -> '/20 (+2 bonus)';
    '40 · **Time:** 50 min' -> '/40'; 'Formative, feedback only' -> 'Formative'."""
    t = marks_text.split("·")[0].strip()
    if t.lower().startswith("formative"):
        return "Formative"
    m = re.search(r"/?\s*(\d+)", t)
    if not m:
        return t
    out = "/%s" % m.group(1)
    b = re.search(r"up to (\d+) bonus", t)
    return out + (" (+%s bonus)" % b.group(1) if b else "")


class Item:
    def __init__(self, block, name, kind, weight, due, prefix):
        self.block, self.name, self.kind, self.weight, self.due = block, name, kind, weight, due
        self.prefix = prefix
        self.date = None
        self.out_of = ""
        self.summary = ""

    @property
    def title(self):
        return strip_prefix(self.name)

    @property
    def label(self):
        return "%s - %s" % (self.prefix, self.title)


class Docs:
    def __init__(self, plan):
        self.plan = plan
        self.root = plan.root
        self.course = plan.course
        self.flags = []
        self.blocks = []
        for s in plan.seq:
            if not self.blocks or self.blocks[-1] != s.block:
                if s.block not in self.blocks:
                    self.blocks.append(s.block)
        self.slot_dates = {s.slot: s.date for s in plan.seq}
        self.block_dates = {}
        for s in plan.seq:
            lo, hi = self.block_dates.get(s.block, (s.date, s.date))
            self.block_dates[s.block] = (min(lo, s.date), max(hi, s.date))
        self.summaries = {}
        for e in plan.evaluations():
            if e.get("summary") and e["name"] not in self.summaries:
                self.summaries[e["name"]] = " ".join(str(e["summary"]).split())
        self.module = self._module()
        self.items = self._items()

    # ------------------------------------------------------------ sources
    def unit_dir(self, block):
        for w in self.plan.weeks:
            if w.block == block:
                d = os.path.join(self.root, w.master_dir)
                while d and not os.path.exists(os.path.join(d, "unit_overview.md")):
                    if os.path.basename(os.path.dirname(d)) != "02_Units" and os.path.dirname(d) != d:
                        d = os.path.dirname(d)
                        continue
                    break
                return d if os.path.exists(os.path.join(d, "unit_overview.md")) else None
        return None

    def unit_title(self, block):
        d = self.unit_dir(block)
        if not d:
            return block
        m = re.search(r"^# (?:Unit \d+|Review Week|[^:]+):\s*(.+)$", _read(os.path.join(d, "unit_overview.md")), re.M)
        return m.group(1).strip() if m else block

    def _module(self):
        """(params, form) for the included optional module, or (params, form) of 'none'."""
        for m in self.plan.params.get("modules") or []:
            mode = self.plan.module_modes.get(m["name"])
            return m, mode, (m.get("forms") or {}).get(mode) or {}
        return None, None, {}

    def _items(self):
        items = []
        mparams, mode, form = self.module
        moves = form.get("weight_moves") or {}
        for block in self.blocks:
            if mparams and block == mparams["name"]:
                for name, w in (form.get("weights") or {}).items():
                    due = next((e.get("due") for e in self.plan.evaluations() if e["name"] == name), None)
                    items.append(Item(block, name, "exercise", float(w), due, mparams.get("register_prefix", block)))
                continue
            d = self.unit_dir(block)
            if not d:
                continue
            t = mdtable.find_table(_read(os.path.join(d, "unit_overview.md")), "item", "kind", "due", "weight")
            if not t:
                self.flags.append("%s unit_overview.md has no Item | Kind | Handed out | Due | Weight table." % block)
                continue
            hdr, rows, _ = t
            ii, ki, di, wi = (mdtable.column(hdr, x) for x in ("item", "kind", "due", "weight"))
            num = re.sub(r"\D", "", block)
            prefix = ("Unit %s" % num) if num else block
            for _, c in rows:
                if len(c) <= wi or not c[ii]:
                    continue
                kind_cell = c[ki].lower()
                kind = "test" if kind_cell.startswith("test") else "assignment" if kind_cell.startswith("assignment") else "exercise"
                w = mdtable.percent(c[wi])
                name = c[ii].strip("` ")
                if name in moves and w is not None:
                    w += float(moves[name])
                due = (re.findall(r"\b[A-Z][\w.]*\.D\d+\b", c[di]) or [None])[0]
                items.append(Item(block, name, kind, w, due, prefix))
        for it in items:
            target = self.plan.land(it.due) if it.due else None
            it.date = target.date if target else None
            if it.due and not target:
                self.flags.append("%s: due slot %s is not in this semester's plan." % (it.name, it.due))
            it.out_of = self._out_of(it)
            it.summary = self.summaries.get(it.name, "")
        missing = [it.name for it in items if not it.summary]
        if missing:
            self.flags.append("No `summary` in the week plans for: %s. Fill the register's \"What it is\" cell by hand "
                              "or add the summaries to master." % ", ".join(missing))
        return items

    def _out_of(self, it):
        if it.weight is None:
            return "Formative"
        master = os.path.join(self.root, "master")
        if it.kind == "test":
            cands = [os.path.join(self.unit_dir(it.block) or "", "Assessment", "Test", "test.md")]
        elif it.kind == "assignment":
            cands = glob.glob(os.path.join(master, "**", "Assessment", it.name, "*instructions.md"), recursive=True)
        else:
            cands = [p for p in glob.glob(os.path.join(master, "**", it.name + ".md"), recursive=True)]
        for p in cands:
            if os.path.exists(p):
                m = MARKS_RE.search(_read(p))
                if m:
                    return out_of(m.group(1))
        self.flags.append("%s: no **Marks:** line found for the register's Out of column." % it.name)
        return ""

    # ------------------------------------------------------------ helpers
    def bucket(self, key):
        return (self.course.get("assessment") or {}).get(key)

    def culminating_due(self):
        dates = []
        for e in self.plan.evaluations():
            if e.get("kind") == "culminating" and e.get("due"):
                t = self.plan.land(e["due"])
                if t:
                    dates.append(t.date)
        return max(dates) if dates else None

    def exam_out_of(self):
        doc = ((self.plan.params.get("register") or {}).get("exam") or {}).get("document")
        if doc and os.path.exists(os.path.join(self.root, doc)):
            m = MARKS_RE.search(_read(os.path.join(self.root, doc)))
            if m:
                return out_of(m.group(1))
        return ""

    def classroom_check(self):
        total = sum(it.weight or 0 for it in self.items)
        want = self.bucket("classroom")
        if want is not None and abs(total - want) > 0.01:
            self.flags.append("Graded classroom items total %g%%; course.yaml classroom is %g%%." % (total, want))
        return total

    # ------------------------------------------------------------ register
    def register_md(self):
        c, sem, reg = self.course, self.plan.cfg["semester"], self.plan.params.get("register") or {}
        self.classroom_check()
        L = ["# %s Assessment Register, %s" % (c.get("code"), sem["name"]), "",
             "Every graded item in the course, in the order students meet it. Out-of comes from each document's own "
             "**Marks:** line, weights from the unit overviews (equal to `master/00_Admin/Assessment_Plan.md`), dates "
             "from `calendar.yaml`. Generated with the rest of this instance; regenerate it if master or the calendar changes.", "",
             "## Graded work", "",
             "| Assessment | Out of | Weight | Due | What it is |",
             "|------------|:------:|:------:|-----|------------|"]
        for it in sorted(self.items, key=lambda i: (i.date is None, i.date or 0, self.blocks.index(i.block))):
            w = "-" if it.weight is None else "%g%%" % it.weight
            L.append("| %s | %s | %s | %s | %s |" % (it.label, it.out_of, w, fmt_short(it.date) if it.date else "", it.summary))
        cul, ex, att = reg.get("culminating") or {}, reg.get("exam") or {}, reg.get("attendance") or {}
        cd = self.culminating_due()
        if self.bucket("culminating"):
            L.append("| %s | %s | %g%% | %s | %s |" % (cul.get("name", "Culminating Project"), cul.get("out_of", ""),
                                                      self.bucket("culminating"), fmt_short(cd) if cd else "", cul.get("summary", "")))
        if self.bucket("exam"):
            L.append("| %s | %s | %g%% | %s | %s |" % (ex.get("name", "Written Examination"), self.exam_out_of(), self.bucket("exam"),
                                                      fmt_range(self.plan.exam_start, self.plan.exam_end), ex.get("summary", "")))
        L.append("| %s | - | %g%% | %s | %s |" % (att.get("name", "Attendance and Participation"), self.bucket("attendance") or 0,
                                                  fmt_range(self.plan.first, self.plan.last), att.get("summary", "")))
        L.append("| **Total** | | **%g%%** | | |" % (sum(it.weight or 0 for it in self.items) + (self.bucket("culminating") or 0)
                                                   + (self.bucket("exam") or 0) + (self.bucket("attendance") or 0)))
        by_kind = {k: sum(i.weight or 0 for i in self.items if i.kind == k) for k in ("exercise", "assignment", "test")}
        L += ["", "## How the weights add up", "", "| Bucket | Weight |", "|--------|:------:|",
              "| Classroom work: exercises %g%%, assignments %g%%, tests %g%% | %g%% |" % (
                  by_kind["exercise"], by_kind["assignment"], by_kind["test"], sum(by_kind.values())),
              "| Final evaluation (culminating project %g%%, written exam %g%%) | %g%% |" % (
                  self.bucket("culminating") or 0, self.bucket("exam") or 0, self.bucket("final_evaluation") or 0),
              "| Attendance and participation | %g%% |" % (self.bucket("attendance") or 0), ""]
        per = []
        for b in self.blocks:
            w = sum(i.weight or 0 for i in self.items if i.block == b)
            if any(i.block == b for i in self.items):
                label = (self.module[0] or {}).get("register_prefix", b) if self.module[0] and b == self.module[0]["name"] else \
                    ("Unit %s" % re.sub(r"\D", "", b) if re.sub(r"\D", "", b) else b)
                per.append("%s %g%%" % (label, w))
        L.append("Classroom work by unit: %s." % " · ".join(per))
        if reg.get("notes"):
            L += ["", "## Notes", ""] + ["- %s" % n for n in reg["notes"]]
        return "\n".join(L) + "\n"

    # ------------------------------------------------- short and long term plan
    def plan_md(self):
        c = self.course
        head = ["**GIBRALTAR LEADERSHIP ACADEMY**", "",
                "**GRADE %s %s (%s)**" % (c.get("grade"), c.get("title"), c.get("code")), ""]
        teacher = (c.get("teacher_formal") or c.get("teacher") or "").upper()
        L = head + ["**SHORT TERM PLAN**", "", "TEACHER: %s" % teacher, "",
                    "| Unit | Unit Title | Start Time | End Time (Approx. date) | Evaluation Percentage |",
                    "| ---- | :--------: | :--------: | ----------------------- | --------------------- |"]
        mparams, mode, form = self.module
        for b in self.blocks:
            if b == "CP" or b == "INTRO":
                continue
            lo, hi = self.block_dates[b]
            its = [i for i in self.items if i.block == b]
            if mparams and b == mparams["name"]:
                num, title = "AI" if b == "ai_module" else b, form.get("plan_title", b)
            else:
                n = re.sub(r"\D", "", b)
                num, title = (n or b), self.unit_title(b).upper()
            parts = []
            for kind, label in (("test", "Test"), ("assignment", "Assignment"), ("exercise", "In-class exercises")):
                w = sum(i.weight or 0 for i in its if i.kind == kind)
                if w:
                    if kind == "exercise" and any(i.name.startswith("BRIEF_") for i in its):
                        label = "In-class ships"
                    parts.append("%g%% %s" % (w, label))
            L.append("| **%s** | **%s** | %s | %s | %s |" % (num, title, fmt_short(lo), fmt_short(hi), " ".join(parts) or "formative only"))
        if "CP" in self.block_dates and self.bucket("culminating"):
            lo, hi = self.block_dates["CP"]
            L.append("| **CULMINATING TASKS** | | %s | %s | %g%% Culminating Project |" % (fmt_short(lo), fmt_short(hi), self.bucket("culminating")))
        if self.bucket("exam"):
            L.append("| **FINAL EVALUATION** | | %s | %s | %g%% Written Examination |" % (
                fmt_short(self.plan.exam_start), fmt_short(self.plan.exam_end), self.bucket("exam")))
        L.append("| **ATTENDANCE AND PARTICIPATION** | | %s | %s | %g%% (unexcused-absence scale) |" % (
            fmt_short(self.plan.first), fmt_short(self.plan.last), self.bucket("attendance") or 0))
        L.append("| **TOTAL** | | | | **100%** |")

        L += ["", "**GIBRALTAR LEADERSHIP ACADEMY**", "", "**LONG TERM PLAN**", "", "TEACHER: %s" % teacher, "",
                            "| EVALUATIONS | DUE DATES | TITLES OF EVALUATION | % OF GRADE |",
                            "| ----------- | :-------: | :------------------: | ---------- |"]
        counters = {"exercise": 0, "assignment": 0, "test": 0}
        for b in self.blocks:
            its = sorted((i for i in self.items if i.block == b and i.weight is not None), key=lambda i: (i.date or 0))
            if not its:
                continue
            if mparams and b == mparams["name"]:
                L.append("| **%s** | | | |" % form.get("long_term_heading", b))
            else:
                L.append("| **UNIT %s: %s** | | | |" % (re.sub(r"\D", "", b) or b, self.unit_title(b).upper()))
            for i in its:
                counters[i.kind] += 1
                L.append("| **%s %d** | %s | %s | %g%% |" % (i.kind.upper(), counters[i.kind], fmt_short(i.date) if i.date else "", i.title, i.weight))
        reg = self.plan.params.get("register") or {}
        if self.bucket("culminating"):
            cd = self.culminating_due()
            L += ["| **CULMINATING TASKS** | | | |",
                  "| **CULMINATING PROJECT** | %s | %s | %g%% |" % (fmt_short(cd) if cd else "",
                                                                  (reg.get("culminating") or {}).get("plan_title", "Culminating Project"), self.bucket("culminating"))]
        if self.bucket("exam"):
            L.append("| **WRITTEN EXAMINATION** | %s to %s | Written Examination (exam period; day per school timetable) | %g%% |" % (
                fmt_short(self.plan.exam_start), fmt_short(self.plan.exam_end), self.bucket("exam")))
        L.append("| **ATTENDANCE AND PARTICIPATION** | | Attendance and Participation | %g%% |" % (self.bucket("attendance") or 0))
        L.append("| **TOTAL** | | | **100%** |")
        return "\n".join(L) + "\n"

    # ------------------------------------------------------------- outline
    def outline_md(self):
        path = os.path.join(self.root, "master", "00_Admin", "Course_Outline.md")
        if not os.path.exists(path):
            self.flags.append("master/00_Admin/Course_Outline.md is missing; no outline written.")
            return None
        text = _read(path)
        p = self.plan
        rows = []
        for h in sorted(p.cfg.get("holidays") or [], key=lambda h: str(h.get("start"))):
            if not h.get("start"):
                continue
            a, b = h["start"], h.get("end") or h["start"]
            from .rehydrate import _d
            a, b = _d(a), _d(b)
            name = h.get("name") or "Holiday"
            if b != a:
                name += " (to %s %d)" % (b.strftime("%b"), b.day)
            rows.append((a, "| No class: %s | %s |" % (name, fmt_long(a))))
        for x in p.cfg.get("pa_days") or []:
            from .rehydrate import _d
            d = _d(x["date"] if isinstance(x, dict) else x)
            label = (x.get("label") if isinstance(x, dict) else None) or "PA Day"
            rows.append((d, "| No class: %s | %s |" % (label, fmt_long(d))))
        hol = "\n".join(r for _, r in sorted(rows))
        mparams, mode, form = self.module
        name = re.sub(r"\bS(\d)\b", r"Semester \1", str(p.cfg["semester"]["name"]))
        text = text.replace("{{SEMESTER_NAME}}", name)
        text = text.replace("{{FIRST_DAY}}", fmt_day(p.first)).replace("{{LAST_DAY}}", fmt_day(p.last))
        text = text.replace("{{EXAM_START}}", fmt_day(p.exam_start)).replace("{{EXAM_END}}", fmt_day(p.exam_end))
        text = re.sub(r"^\| \{\{HOLIDAY_ROWS\}\} \|[^\n]*\n", (hol + "\n") if hol else "", text, flags=re.M)
        row = form.get("outline_row") if form else None
        text = re.sub(r"^\| \{\{AI_ROW\}\} \|[^\n]*\n", (row + "\n") if row else "", text, flags=re.M)
        left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
        if left:
            self.flags.append("Course_Outline.md placeholders the generator does not know: %s." % ", ".join(left))
        return text

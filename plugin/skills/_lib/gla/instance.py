"""Checks for a dated semester instance (instances/<name>/).

Covers the self-check in Standards/rehydration/Rehydration_Framework.md §6
that a script can decide: one date per slot and one slot per date, nothing on
a closure, calendar.yaml and Course_Calendar.md agree, hand-outs and dues sit
on the week plans' slots, test placement, assignment windows, week plans
match master apart from dates, weights total 100, and the generation
report's window table matches the calendar.
"""
import copy
import datetime as dt
import os
import re

import yaml

from . import mdtable, schoolcal, slots, weekplan

KINDS = ("slot", "buffer", "closure", "exam")
SLOT_FIELDS = ("slot", "week_key", "week_plan", "master_dir", "title", "day_type", "sub_ready", "handouts", "dues")
WINDOW_MIN, WINDOW_MAX = 7, 10
_MD_DATE = re.compile(r"^(?:[A-Z][a-z]{2} )?([A-Z][a-z]{2})[a-z]* (\d{1,2}), (\d{4})$")
_MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _date(v):
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v))


def _md_date(cell):
    """'Mon Aug 31, 2026' or 'Sep 16, 2026' -> date, else None."""
    m = _MD_DATE.match(cell.strip().replace("*", ""))
    if not m or m.group(1) not in _MONTHS:
        return None
    return dt.date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))


def _weekdays(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def _strip_dates(plan):
    p = copy.deepcopy(plan)
    (p.get("metadata") or {}).pop("dates", None)
    for d in p.get("daily_lessons") or []:
        d.pop("date", None)
    return p


class Instance:
    def __init__(self, course_root, name):
        self.root = os.path.abspath(course_root)
        self.name = name
        self.dir = os.path.join(self.root, "instances", name)
        self.cal_path = os.path.join(self.dir, "calendar.yaml")
        self.cal = None
        self.plans = {}      # instance-relative path -> plan

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def load(self, report):
        if not os.path.isdir(self.dir):
            report.error("instance-missing", self.dir, "no such instance folder")
            return False
        if not os.path.exists(self.cal_path):
            report.error("calendar-missing", self.cal_path, "no calendar.yaml; regenerate the instance (gla semester new)")
            return False
        with open(self.cal_path, encoding="utf-8") as f:
            self.cal = yaml.safe_load(f) or {}
        return True

    # ------------------------------------------------------------------ calendar
    def check_calendar(self, report, config):
        cal, p = self.cal, self.cal_path
        if cal.get("schema") != 1:
            report.error("calendar-schema", p, "schema is %r, expected 1" % cal.get("schema"))
        sem = cal.get("semester") or {}
        try:
            first, last = _date(sem["first_day"]), _date(sem["last_day"])
            ex0, ex1 = _date(sem["exam_start"]), _date(sem["exam_end"])
        except (KeyError, ValueError) as e:
            report.error("calendar-semester", p, "semester dates missing or malformed (%s)" % e)
            return
        days = cal.get("days") or []
        seen_dates, seen_slots = {}, {}
        prev = None
        for d in days:
            try:
                date = _date(d.get("date"))
            except ValueError:
                report.error("calendar-date", p, "bad date %r" % d.get("date"))
                continue
            if prev and date <= prev:
                report.error("calendar-order", p, "%s is out of order or repeated" % date)
            prev = date
            if date.weekday() >= 5:
                report.error("calendar-weekend", p, "%s is a weekend day" % date)
            if date in seen_dates:
                report.error("calendar-date", p, "%s appears twice" % date)
            seen_dates[date] = d
            kind = d.get("kind")
            if kind not in KINDS:
                report.error("calendar-kind", p, "%s: kind %r is not one of %s" % (date, kind, ", ".join(KINDS)))
                continue
            if kind == "slot":
                for f in SLOT_FIELDS:
                    if f not in d:
                        report.error("calendar-field", p, "%s: slot day missing %r" % (date, f))
                s = str(d.get("slot") or "")
                if not slots.is_slot(s):
                    report.error("calendar-slot", p, "%s: %r is not a slot ID" % (date, s))
                    continue
                if s in seen_slots:
                    report.error("calendar-slot", p, "%s is scheduled on %s and %s" % (s, seen_slots[s], date))
                seen_slots[s] = date
                if d.get("week_key") != slots.week_key(s):
                    report.error("calendar-weekkey", p, "%s: week_key %r should be %r" % (s, d.get("week_key"), slots.week_key(s)))
                if date > last:
                    report.error("calendar-range", p, "%s lands on %s, after the last instructional day" % (s, date))
                if d.get("day_type") not in weekplan.DAY_TYPES:
                    report.error("calendar-daytype", p, "%s: day_type %r" % (s, d.get("day_type")))
            elif kind in ("buffer", "closure", "exam") and not d.get("label"):
                report.warn("calendar-label", p, "%s: %s day has no label" % (date, kind))
            if kind == "exam" and not ex0 <= date <= ex1:
                report.error("calendar-exam", p, "%s is marked exam but sits outside the exam window" % date)

        for date in list(_weekdays(first, last)) + list(_weekdays(ex0, ex1)):
            if date not in seen_dates:
                report.error("calendar-gap", p, "weekday %s is missing" % date)
        for date in _weekdays(ex0, ex1):
            if date in seen_dates and seen_dates[date].get("kind") != "exam":
                report.error("calendar-exam", p, "%s is in the exam window but is %s" % (date, seen_dates[date].get("kind")))
        for date, d in seen_dates.items():
            if not (first <= date <= last or ex0 <= date <= ex1):
                report.error("calendar-range", p, "%s sits outside the semester and exam window" % date)

        closed = set()
        for h in (config or {}).get("holidays") or []:
            closed.update(_weekdays(_date(h["start"]), _date(h.get("end") or h["start"])))
        closed.update(_date(x["date"] if isinstance(x, dict) else x) for x in (config or {}).get("pa_days") or [])
        for date in sorted(closed):
            d = seen_dates.get(date)
            if d and d.get("kind") != "closure":
                report.error("calendar-closure", p, "%s is a holiday or PA day in semester_config.yaml but is %s %s" % (date, d.get("kind"), d.get("slot", "")))

        for c in cal.get("cuts") or []:
            s = str(c.get("slot") or "")
            if not slots.is_slot(s):
                report.error("calendar-cut", p, "cut %r is not a slot ID" % s)
            elif s in seen_slots:
                report.error("calendar-cut", p, "%s is listed as cut but is scheduled on %s" % (s, seen_slots[s]))
        self.days, self.by_slot = days, {d["slot"]: d for d in days if d.get("kind") == "slot" and d.get("slot")}
        self.cut_slots = {str(c.get("slot")) for c in cal.get("cuts") or []}

    def class_days_between(self, a, b):
        """Class days after slot a up to and including slot b (slot and buffer days count)."""
        da, db = _date(self.by_slot[a]["date"]), _date(self.by_slot[b]["date"])
        return sum(1 for d in self.days if d.get("kind") in ("slot", "buffer") and da < _date(d["date"]) <= db)

    # ------------------------------------------------------------- week plans
    def check_week_plans(self, report):
        rel_paths = sorted({d["week_plan"] for d in self.days if d.get("kind") == "slot" and d.get("week_plan")})
        for rel in rel_paths:
            path = self.path(rel)
            if not os.path.exists(path):
                report.error("weekplan-missing", self.cal_path, "week plan %s does not exist" % rel)
                continue
            plan = weekplan.load(path)
            self.plans[rel] = plan
            weekplan.check(plan, path, report, master=False)
            by_slot = {str(x.get("slot")): x for x in plan.get("daily_lessons") or []}
            for s, x in by_slot.items():
                if s in self.by_slot:
                    want = str(self.by_slot[s]["date"])
                    if str(x.get("date")) != want:
                        report.error("weekplan-date", path, "%s: date %r, calendar says %s" % (s, x.get("date"), want))
                elif s in self.cut_slots:
                    if not str(x.get("date") or "").startswith("CUT"):
                        report.error("weekplan-cut", path, "%s is cut but its date is %r" % (s, x.get("date")))
                else:
                    report.error("weekplan-unscheduled", path, "%s is neither scheduled nor cut" % s)
            master_dirs = {d["master_dir"] for d in self.days if d.get("week_plan") == rel}
            for md in master_dirs:
                mp = os.path.join(self.root, md, "week_plan.yaml")
                if os.path.exists(mp) and _strip_dates(weekplan.load(mp)) != _strip_dates(plan):
                    report.warn("weekplan-drift", path, "differs from %s beyond dates" % os.path.relpath(mp, self.root))
        for d in self.days:
            if d.get("kind") == "slot" and d.get("master_dir") and not os.path.isdir(os.path.join(self.root, d["master_dir"])):
                report.error("calendar-masterdir", self.cal_path, "%s: master_dir %s does not exist" % (d["slot"], d["master_dir"]))

    # ------------------------------------------------------------ evaluations
    def evaluations(self):
        out, seen = [], set()
        for rel, plan in self.plans.items():
            for e in plan.get("evaluations") or []:
                if isinstance(e, dict) and e.get("name") and (e["name"], e.get("due")) not in seen:
                    seen.add((e["name"], e.get("due")))
                    out.append((rel, e))
        return out

    def moved_off(self, cut_slot):
        """True when a day in the cut slot's week carries a '(moved from ...)' annotation for it."""
        wk, day = slots.week_key(cut_slot), "D%d" % slots.parse(cut_slot)[2]
        for d in self.days:
            if d.get("kind") == "slot" and d.get("week_key") == wk:
                for a in (d.get("handouts") or []) + (d.get("dues") or []):
                    m = re.search(r"moved from ([\w.]+)", a)
                    if m and m.group(1) in (cut_slot, day):
                        return True
        return False

    def check_evaluations(self, report):
        windows = {}
        avoid = self.avoid_test_days()
        for rel, e in self.evaluations():
            path, name, kind = self.path(rel), e["name"], e.get("kind")
            ho, due = str(e.get("handed_out") or ""), str(e.get("due") or "")
            for label, s in (("hand-out", ho), ("due", due)):
                if s and s not in self.by_slot and s not in self.cut_slots:
                    report.error("eval-slot", path, "%s: %s slot %s is not in the calendar" % (name, label, s))
            if due in self.cut_slots and not self.moved_off(due):
                report.error("eval-cut", path, "%s: due slot %s was cut and no annotation in its week says it moved" % (name, due))
            if kind == "assignment":
                if ho in self.by_slot and not self.by_slot[ho].get("handouts"):
                    report.error("eval-handout", self.cal_path, "%s: no hand-out annotation on %s, the week plan's handed_out slot" % (name, ho))
                if due in self.by_slot and not self.by_slot[due].get("dues"):
                    report.error("eval-due", self.cal_path, "%s: no due annotation on %s" % (name, due))
                if ho in self.by_slot and due in self.by_slot:
                    w = self.class_days_between(ho, due)
                    windows[name] = (ho, due, w)
                    if not WINDOW_MIN <= w <= WINDOW_MAX:
                        report.warn("eval-window", path, "%s: %s to %s is %d class days (rule: %d to %d)" % (name, ho, due, w, WINDOW_MIN, WINDOW_MAX))
            if kind == "test" and due in self.by_slot and self.by_slot[due].get("day_type") != "assess":
                report.error("eval-test", path, "%s: due on %s, a %s day, not an assess day" % (name, due, self.by_slot[due].get("day_type")))
            if kind == "test" and due in self.by_slot and avoid:
                d = _date(self.by_slot[due].get("date"))
                if d and d.weekday() in avoid and d >= dt.date.today():   # a test already given stays history
                    report.error("eval-test-day", self.cal_path, "%s falls on %s, a %s; rehydration.yaml avoids tests on %s"
                                 % (name, d.isoformat(), DAYS[d.weekday()], ", ".join(DAYS[k] for k in sorted(avoid))))
        self.windows = windows

    def avoid_test_days(self):
        """Weekday numbers rehydration.yaml's constraints.avoid_test_days names."""
        try:
            with open(os.path.join(self.root, "course.yaml"), encoding="utf-8") as f:
                rd = (yaml.safe_load(f) or {}).get("rehydration_dir")
            with open(os.path.join(self.root, "master", rd, "rehydration.yaml"), encoding="utf-8") as f:
                params = yaml.safe_load(f) or {}
        except (OSError, TypeError):
            return set()
        names = (params.get("constraints") or {}).get("avoid_test_days") or []
        return {DAYS.index(x[:3].title()) for x in names if x[:3].title() in DAYS}

    # --------------------------------------------------------- markdown files
    def check_course_calendar_md(self, report):
        p = self.path("Course_Calendar.md")
        if not os.path.exists(p):
            report.error("md-missing", p, "Course_Calendar.md is missing")
            return
        t = mdtable.find_table(_read(p), "date", "slot")
        if not t:
            report.error("md-table", p, "no Date | Slot table")
            return
        header, rows, _ = t
        ci, si = mdtable.column(header, "date"), mdtable.column(header, "slot")
        by_date = {_date(d["date"]): d for d in self.days}
        md_dates = set()
        for line, cells in rows:
            date = _md_date(cells[ci]) if ci < len(cells) else None
            if not date:
                continue
            md_dates.add(date)
            d, cell = by_date.get(date), cells[si].strip()
            if not d:
                report.error("md-calendar", p, "%s is not in calendar.yaml" % date, line)
            elif d.get("kind") == "slot" and cell != d.get("slot"):
                report.error("md-calendar", p, "%s: Course_Calendar.md says %r, calendar.yaml says %s" % (date, cell, d.get("slot")), line)
            elif d.get("kind") == "buffer" and cell.upper() != "BUFFER":
                report.error("md-calendar", p, "%s: calendar.yaml has a buffer day, Course_Calendar.md says %r" % (date, cell), line)
            elif d.get("kind") == "closure" and slots.is_slot(cell):
                report.error("md-calendar", p, "%s: calendar.yaml has a closure, Course_Calendar.md schedules %s" % (date, cell), line)
        for d in self.days:
            if d.get("kind") in ("slot", "buffer") and _date(d["date"]) not in md_dates:
                report.error("md-calendar", p, "%s (%s) has no row" % (d["date"], d.get("slot") or d.get("kind")))

    def check_register(self, report, classroom):
        p = self.path("Assessment_Register.md")
        if not os.path.exists(p):
            report.error("md-missing", p, "Assessment_Register.md is missing")
            return
        t = mdtable.find_table(_read(p), "assessment", "weight")
        if not t:
            report.error("register-table", p, "no Assessment | Weight table")
            return
        header, rows, _ = t
        wi, di = mdtable.column(header, "weight"), mdtable.column(header, "due")
        items, summary = 0.0, 0.0
        slot_dates = {_date(d["date"]) for d in self.days if d.get("kind") in ("slot", "exam")}
        for line, cells in rows:
            if mdtable.is_total(cells):
                continue
            if len(cells) >= len(header) - 1:
                w = mdtable.percent(cells[wi])
                items += w or 0
                due = _md_date(cells[di]) if di < len(cells) else None
                if due and due not in slot_dates:
                    report.error("register-due", p, "%s is due %s, which is not a class or exam day" % (cells[0], due), line)
            else:
                vals = [mdtable.percent(c) for c in cells[1:] if mdtable.percent(c) is not None]
                summary += vals[-1] if vals else 0
        if abs(items - 100) < 0.01 or (abs(summary - 100) < 0.01 and (classroom is None or abs(items - classroom) < 0.01)):
            return
        report.error("register-total", p, "graded rows total %g%%, summary rows %g%% (expected 100, or classroom %s plus summary rows totalling 100)" % (items, summary, classroom))

    def check_long_range_plan(self, report):
        p = self.path("Short_and_Long_Term_Plan.md")
        if not os.path.exists(p):
            report.error("md-missing", p, "Short_and_Long_Term_Plan.md is missing")
            return
        text = _read(p)
        t = mdtable.find_table(text, "% of grade")
        if t:
            header, rows, _ = t
            gi = mdtable.column(header, "% of grade")
            total = sum(mdtable.percent(c[gi]) or 0 for _, c in rows if gi < len(c) and not mdtable.is_total(c))
            if abs(total - 100) > 0.01:
                report.error("plan-total", p, "the evaluations table totals %g%%, not 100" % total)
        t = mdtable.find_table(text, "unit", "evaluation percentage")
        if t:
            header, rows, _ = t
            ei = mdtable.column(header, "evaluation percentage")
            total = 0.0
            for _, c in rows:
                if mdtable.is_total(c):
                    continue
                total += sum(float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", c[ei] if ei < len(c) else ""))
            if abs(total - 100) > 0.01:
                report.error("plan-total", p, "the long-range table's percentages total %g%%, not 100" % total)

    def check_report_windows(self, report):
        p = self.path("GENERATION_REPORT.md")
        if not os.path.exists(p):
            report.error("md-missing", p, "GENERATION_REPORT.md is missing")
            return
        t = mdtable.find_table(_read(p), "assignment", "hand-out", "due", "window")
        if not t:
            return
        header, rows, _ = t
        ai, hi, wi = mdtable.column(header, "assignment"), mdtable.column(header, "hand-out"), mdtable.column(header, "window")
        for line, cells in rows:
            key = re.sub(r"^Assignment_", "", cells[ai]).replace("_", " ").lower()
            match = [v for n, v in self.windows.items() if re.sub(r"^Assignment_", "", n).replace("_", " ").lower() == key]
            if not match:
                report.warn("report-window", p, "%s is not an assignment in the week plans" % cells[ai], line)
                continue
            ho, due, w = match[0]
            stated_ho = slots.find_all(cells[hi])
            if stated_ho and stated_ho[0] != ho:
                report.error("report-window", p, "%s: report says hand-out %s, the week plan says %s" % (cells[ai], stated_ho[0], ho), line)
            try:
                if int(re.sub(r"\D", "", cells[wi])) != w:
                    report.error("report-window", p, "%s: report says %s class days, the calendar gives %d" % (cells[ai], cells[wi], w), line)
            except ValueError:
                pass


def check(course_root, name, report, config=None, classroom=None, only_calendar=False):
    """only_calendar skips the register and the long-range plan, which the generator does not write yet."""
    inst = Instance(course_root, name)
    if not inst.load(report):
        return inst
    if config is None:
        cp = inst.path("semester_config.yaml")
        if os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            report.error("config-missing", cp, "semester_config.yaml is missing")
    if config:
        try:
            config = schoolcal.resolve(config)
        except schoolcal.SchoolCalendarError as e:
            report.error("school-calendar", inst.path("semester_config.yaml"), str(e))
    inst.check_calendar(report, config)
    if not hasattr(inst, "by_slot"):
        return inst
    inst.check_week_plans(report)
    inst.check_evaluations(report)
    inst.check_course_calendar_md(report)
    if not only_calendar:
        inst.check_register(report, classroom)
        inst.check_long_range_plan(report)
    inst.check_report_windows(report)
    return inst

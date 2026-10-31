"""Deterministic rehydration: a semester config plus a course's rehydration.yaml
become a dated calendar.

Implements Standards/rehydration/Rehydration_Framework.md steps 1 to 4 and the
calendar half of step 5: build the calendar, assemble the slot sequence with
modules, fit by the compression tiers and the reserve spill, place buffer
days, assign dates, and write calendar.yaml, Course_Calendar.md, the dated
week plans, and the factual parts of GENERATION_REPORT.md.

Buffer days go first on the config's named event days (events[].buffers),
then on the class day before each unit test, latest unit first, then at the
end before exams.
"""
import datetime as dt
import os
import re
import subprocess

import yaml

from . import schoolcal
from . import slots as slotmod
from . import weekplan

WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
CUT_MARK = "CUT, removed by compression (see GENERATION_REPORT.md)"


class NeedsTeacher(Exception):
    """The plan cannot fit within the sanctioned rules; a teacher must decide."""


class ConfigError(Exception):
    pass


def _d(v):
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def _get(cfg, dotted, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def fmt_long(d):
    return "%s %s %d, %d" % (d.strftime("%a"), d.strftime("%b"), d.day, d.year)


def fmt_short(d):
    return "%s %d, %d" % (d.strftime("%b"), d.day, d.year)


def pretty(name):
    return re.sub(r"^Assignment_", "", name).replace("_", " ")


class Week:
    def __init__(self, root, path, block, instance_name=None):
        self.path = path
        self.block = block
        with open(os.path.join(root, path), encoding="utf-8") as f:
            self.text = f.read()
        self.plan = yaml.safe_load(self.text) or {}
        self.prefix = (self.plan.get("metadata") or {}).get("slot_prefix") or ""
        self.instance_name = instance_name or self.prefix.replace(".", "_")
        self.master_dir = os.path.dirname(path)


class Slot:
    def __init__(self, slot, block, title, day_type, sub_ready, master_dir, week=None):
        self.slot, self.block, self.title, self.day_type, self.sub_ready = slot, block, title, day_type, sub_ready
        self.master_dir, self.week = master_dir, week
        self.week_key = slotmod.week_key(slot)
        self.date = None
        self.handouts, self.dues = [], []
        self.note = None
        self.week_plan_rel = None     # kept days of a resumed run whose week is no longer in the sequence


class Plan:
    """Everything the generator decides, before anything is written."""

    def __init__(self, root, cfg, params, course_cfg):
        self.root, self.cfg, self.params, self.course = root, cfg, params, course_cfg
        self.weeks, self.seq, self.cuts, self.flags = [], [], [], []
        self.moves, self.days, self.math, self.buffer_days = [], [], {}, []
        self.spill = 0
        self.test_moves = []  # (test name, from date, to date, how): kept off avoid_test_days
        self.module_modes = {}
        self.resume_from = None
        self.done = []        # slots taught before resume_from, kept as they were
        self.kept = {}        # date -> previous calendar day, for dates before resume_from
        self.slot_pins = {}   # slot -> date it was moved to on or after resume_from (teaching log)
        self.dropped = []     # slots skipped for the semester (teaching log): never re-planned
        self.log_changes = [] # (slot, what happened), from the teaching log, for the report

    # -------------------------------------------------------------- sequence
    def assemble(self):
        blocks = []
        for b in self.params["sequence"]:
            blocks.append((b["block"], self._block_slots(b)))
        for m in self.params.get("modules") or []:
            mode = _get(self.cfg, m["mode_key"], "none")
            forms = m.get("forms") or {}
            if mode not in forms:
                raise ConfigError("%s = %r is not one of %s" % (m["mode_key"], mode, ", ".join(forms)))
            self.module_modes[m["name"]] = mode
            wps = forms[mode].get("week_plans") or []
            if not wps:
                continue
            msl = []
            for wp in wps:
                wp = wp if isinstance(wp, dict) else {"path": wp}
                msl += self._week_slots(Week(self.root, wp["path"], m["name"], wp.get("instance_name")))
            placement = _get(self.cfg, m.get("placement_key", ""), None) or m.get("default_placement")
            after = re.sub(r"^after_", "", placement or "")
            idx = next((k for k, (name, _) in enumerate(blocks) if name == after), None)
            if idx is None:
                raise ConfigError("placement %r names no block in the sequence" % placement)
            blocks.insert(idx + 1, (m["name"], msl))
        self.seq = [s for _, b in blocks for s in b]
        self.module_blocks = {m["name"] for m in self.params.get("modules") or []}

    def _block_slots(self, b):
        if b.get("days"):
            return [Slot(d["slot"], b["block"], d.get("title", ""), d.get("day_type", "teach"),
                         bool(d.get("sub_ready")), b.get("dir")) for d in b["days"]]
        out = []
        for wp in b.get("week_plans") or []:
            wp = wp if isinstance(wp, dict) else {"path": wp}
            out += self._week_slots(Week(self.root, wp["path"], b["block"], wp.get("instance_name")))
        return out

    def _week_slots(self, week):
        self.weeks.append(week)
        return [Slot(str(d["slot"]), week.block, d.get("title", ""), d.get("day_type"), bool(d.get("sub_ready")),
                     week.master_dir, week) for d in week.plan.get("daily_lessons") or []]

    def evaluations(self):
        """Evaluations from the included week plans, first mention wins. A later week
        often restates an assignment or culminating component under a longer
        name; the same kind due on the same slot is the same item."""
        seen, out = set(), []
        for w in self.weeks:
            for e in w.plan.get("evaluations") or []:
                if not isinstance(e, dict) or not e.get("name"):
                    continue
                key = (e.get("kind"), e.get("due")) if e.get("kind") != "exercise" else (e["name"], e.get("due"))
                if key not in seen:
                    seen.add(key)
                    out.append(e)
        return out

    # -------------------------------------------------------------- calendar
    def build_calendar(self):
        sem = self.cfg["semester"]
        self.first, self.last = _d(sem["first_day"]), _d(sem["last_day"])
        self.exam_start, self.exam_end = _d(sem["exam_start"]), _d(sem["exam_end"])
        class_days = {WEEKDAYS[x] for x in _get(self.cfg, "schedule.class_days", ["Mon", "Tue", "Wed", "Thu", "Fri"])}
        self.closures = {}
        for h in self.cfg.get("holidays") or []:
            if not h.get("start"):
                continue
            d = _d(h["start"])
            while d <= _d(h.get("end") or h["start"]):
                self.closures[d] = h.get("name") or "Holiday"
                d += dt.timedelta(days=1)
        for p in self.cfg.get("pa_days") or []:
            if isinstance(p, dict):
                self.closures[_d(p["date"])] = p.get("label") or "PA Day"
            else:
                self.closures[_d(p)] = "PA Day"
        self.weekdays, self.scheduled = [], []
        d = self.first
        while d <= self.last:
            if d.weekday() < 5:
                self.weekdays.append(d)
                if d.weekday() in class_days and d not in self.closures:
                    self.scheduled.append(d)
                elif d not in self.closures:
                    self.closures[d] = "No class"
            d += dt.timedelta(days=1)
        uf = float(_get(self.cfg, "capacity.usable_fraction", 0.85))
        self.usable = int(len(self.scheduled) * uf)
        self.reserve = len(self.scheduled) - self.usable
        self.math = {"weekdays": len(self.weekdays), "closed": sum(1 for x in self.weekdays if x in self.closures),
                     "scheduled": len(self.scheduled), "usable_fraction": uf, "usable": self.usable,
                     "reserve": self.reserve, "nominal": len(self.seq)}

    # ---------------------------------------------------------------- resume
    def resume(self, previous):
        """Keep every day before resume_from exactly as the previous calendar has it,
        and re-plan the rest: the slots not yet taught, on the class days from
        resume_from on. Earlier cuts stay cut when they sit before the last taught
        slot; later ones are reconsidered."""
        rd = _d(self.cfg["resume_from"])
        self.resume_from = rd
        ids = lambda key: {str(x) for x in self.cfg.get(key) or []}  # noqa: E731
        postponed = ids("resume_postponed")   # not taught on its day: re-plan it after rd
        dropped = ids("resume_skipped")       # not taught this semester: never re-planned
        noclass = ids("resume_noclass")       # the class did not meet: a closure, the slot re-planned
        moved = {str(k): _d(v) for k, v in (self.cfg.get("resume_moved") or {}).items() if v}
        partial = {str(k): str(v or "").strip().rstrip(".") for k, v in (self.cfg.get("resume_partial") or {}).items()}
        seq_by = {s.slot: s for s in self.seq}
        weeks_by = {w.instance_name: w for w in self.weeks}
        prev = {_d(d["date"]): d for d in previous.get("days") or []}
        planned = {d["slot"]: date for date, d in prev.items() if d.get("kind") == "slot"}
        settled = postponed | dropped | noclass | set(moved)

        # A slot that ran on another past day takes that day: the day must have
        # held nothing taught (a buffer, or a slot postponed, skipped or moved).
        ran_on = {}
        for s, a in sorted(moved.items(), key=lambda x: x[1]):
            if a >= rd:
                continue
            there = prev.get(a)
            if there is None or there.get("kind") not in ("slot", "buffer") or a in self.closures \
                    or (there.get("kind") == "slot" and there["slot"] not in settled):
                what = ("%s %s" % (there.get("kind"), there.get("slot") or there.get("label", ""))).strip() if there else "no class day"
                self.flags.append("%s is logged as moved to %s, but that day holds %s; it is kept on its planned day."
                                  % (s, fmt_long(a), what))
                moved.pop(s)
                continue
            if s not in planned:
                self.flags.append("%s is logged as moved, but the previous calendar never scheduled it." % s)
                moved.pop(s)
                continue
            ran_on[a] = s
        self.slot_pins = {s: a for s, a in moved.items() if a >= rd}

        def keep_slot(date, d):
            s = seq_by.get(d["slot"])
            if s is None:
                s = Slot(d["slot"], (d.get("week_key") or "").split(".")[0], d.get("title", ""), d.get("day_type"),
                         bool(d.get("sub_ready")), d.get("master_dir"))
                name = os.path.splitext(os.path.basename(d.get("week_plan") or ""))[0]
                s.week = weeks_by.get(name)
                s.week_plan_rel = d.get("week_plan")
            s.date = date
            s.handouts, s.dues = list(d.get("handouts") or []), list(d.get("dues") or [])
            s.note = d.get("note")
            self.done.append(s)
            self.kept[date] = {"date": date.isoformat(), "kind": "slot", "slot": s.slot}

        for date in sorted(prev):
            d = prev[date]
            if date >= rd:
                continue
            slot = d.get("slot") if d.get("kind") == "slot" else None
            if date in self.closures and d.get("kind") != "closure":
                # A closure in the config wins over the old calendar's day.
                self.kept[date] = {"date": date.isoformat(), "kind": "closure", "label": self.closures[date]}
                if slot and slot not in settled:
                    self.log_changes.append((slot, "on %s, now a closure in the config: re-planned" % fmt_long(date)))
                continue
            if date in ran_on:
                s = ran_on[date]
                if slot in dropped:   # the slot it displaced was skipped for the semester
                    self.dropped.append(slot)
                    self.log_changes.append((slot, "skipped on %s: not taught this semester" % fmt_long(date)))
                keep_slot(date, dict(prev[planned[s]], date=date.isoformat()))
                self.log_changes.append((s, "planned %s, taught %s" % (fmt_long(planned[s]), fmt_long(date))))
                continue
            label = None
            if slot in moved:
                label = "%s moved to %s" % (slot, fmt_long(moved[slot]))
                if slot in self.slot_pins:
                    self.log_changes.append((slot, "planned %s, moved to %s" % (fmt_long(date), fmt_long(moved[slot]))))
            elif slot in noclass:
                self.kept[date] = {"date": date.isoformat(), "kind": "closure", "label": "No class (%s re-planned)" % slot}
                self.log_changes.append((slot, "no class on %s: re-planned" % fmt_long(date)))
                continue
            elif slot in postponed:
                label = "%s postponed, re-planned after %s" % (slot, rd.isoformat())
                self.log_changes.append((slot, "postponed from %s: re-planned" % fmt_long(date)))
            elif slot in dropped:
                label = "%s skipped, not taught this semester" % slot
                self.dropped.append(slot)
                self.log_changes.append((slot, "skipped on %s: not taught this semester" % fmt_long(date)))
            if label:
                self.kept[date] = {"date": date.isoformat(), "kind": "buffer", "label": label}
            elif slot:
                keep_slot(date, d)
            else:
                self.kept[date] = d
        for s, note in partial.items():
            if s in {x.slot for x in self.done}:
                self.flags.append("%s was only partly taught%s. Absorb the rest in the next lesson or a buffer day."
                                  % (s, ": " + note if note else ""))
                self.log_changes.append((s, "partly taught" + (" (%s)" % note if note else "")))
        for e in self.evaluations():
            hit = {f: str(e.get(f)) for f in ("handed_out", "due") if str(e.get(f)) in self.dropped}
            for slot in sorted(set(hit.values())):
                what = " and ".join("handed out" if f == "handed_out" else "due" for f, v in hit.items() if v == slot)
                self.flags.append("%s was skipped, and %s (%s) was %s on it. Give it another slot or change its weight."
                                  % (slot, e["name"], e.get("kind", ""), what))
        done = {s.slot for s in self.done}
        order = {s.slot: k for k, s in enumerate(self.seq)}
        last = max((order[x] for x in done if x in order), default=-1)
        for c in previous.get("cuts") or []:
            if c["slot"] in order and order[c["slot"]] < last:
                self.cuts.append((c["slot"], {"priority": c.get("priority"), "what": "cut in the earlier run (before the resume point)",
                                               "consequence": "history, unchanged"}))
        kept_cuts = {x for x, _ in self.cuts}
        self.seq = [s for s in self.seq if s.slot not in done and s.slot not in kept_cuts and s.slot not in self.dropped]
        # Capacity stays a whole-semester figure (with the new config's closures):
        # what is left is the semester's usable days minus the slots already taught.
        self.scheduled = [x for x in self.scheduled if x >= rd]
        self.usable = self.usable - len(self.done)
        self.math.update({"resume_from": rd, "taught": len(self.done), "remaining_days": len(self.scheduled),
                          "usable_left": self.usable, "nominal": len(self.seq)})

    # ------------------------------------------------------------------- fit
    def fit(self):
        protected = {e.get("handed_out") for e in self.evaluations() if e.get("kind") in ("assignment", "culminating")}
        by_slot = {s.slot: s for s in self.seq}
        need = len(self.seq) - self.usable
        mode = _get(self.cfg, "options.compression", "auto")
        if need > 0 and mode == "manual":
            raise NeedsTeacher("compression is manual and the plan is %d slot(s) over the usable days" % need)
        for tier in (self.params.get("compression") or {}).get("tiers") or []:
            if tier.get("manual"):
                continue
            for s in tier.get("slots") or []:
                if need <= 0:
                    break
                if s not in by_slot or s in self.slot_pins:
                    continue   # a slot the teaching log moved to a date is never cut
                if by_slot[s].day_type in ("teach", "assess") or s in protected:
                    raise ConfigError("tier %s lists %s, a %s or hand-out day; those are never cut"
                                      % (tier.get("priority"), s, by_slot[s].day_type))
                self.cuts.append((s, tier))
                need -= 1
        cut = {s for s, _ in self.cuts}
        self.seq = [s for s in self.seq if s.slot not in cut]
        floor = (self.params.get("compression") or {}).get("floor")
        if floor:
            kept = sum(1 for s in self.seq + self.done if s.block in floor.get("blocks", []))
            if kept < floor["slots"]:
                raise NeedsTeacher("compression went below the floor (%d < %d)" % (kept, floor["slots"]))
        if need > 0:
            module_slots = sum(1 for s in self.seq + self.done if s.block in self.module_blocks)
            min_reserve = min((m.get("reserve_spill") or {}).get("min_reserve", self.reserve + 1)
                              for m in self.params.get("modules") or [{}]) if self.params.get("modules") else self.reserve + 1
            allowed = max(0, min(module_slots, self.reserve - min_reserve))
            if need > allowed:
                raise NeedsTeacher("after every sanctioned cut the plan is still %d slot(s) over; the reserve spill "
                                   "allows %d. Ask the teacher which unit to thin." % (need, allowed))
            self.spill = need
        self.math.update({"slots": len(self.seq), "buffers": len(self.scheduled) - len(self.seq), "spill": self.spill})
        margin = self.params.get("expand_margin", 4)
        if len(self.seq) < self.usable - margin:
            self.flags.append("The plan uses %d slots against %d usable days; the semester has room to spare "
                              "(re-add flex days or widen project weeks by hand)." % (len(self.seq), self.usable))

    # ------------------------------------------------------- buffers and dates
    def place(self):
        nbuf = len(self.scheduled) - len(self.seq)
        sched = set(self.scheduled)
        pinned, notes = {}, {}
        # Slots the teaching log moved to a date on or after resume_from land on it.
        by_slot = {s.slot: s for s in self.seq}
        pin_at = {}
        for slot, a in sorted(self.slot_pins.items(), key=lambda x: x[1]):
            if slot not in by_slot:
                continue
            if a not in sched or a in pin_at:
                self.flags.append("%s is logged as moved to %s, which is not a free class day; it is re-planned in order."
                                  % (slot, fmt_long(a)))
                continue
            pin_at[a] = by_slot[slot]
        pinned_slots = {s.slot for s in pin_at.values()}
        for ev in self.cfg.get("events") or []:
            start = _d(ev["start"])
            end = _d(ev.get("end") or ev["start"])
            if self.resume_from and end < self.resume_from:
                continue   # already past on a resumed run: the kept days hold its buffer
            days = [x for x in self.scheduled if start <= x <= end and x not in pin_at]
            want = int(ev.get("buffers", 0) or 0)
            for x in days:
                if want and x not in pinned and len(pinned) < nbuf:
                    pinned[x] = ev["name"]
                    want -= 1
                elif ev.get("note") and x not in pinned:
                    notes[x] = ev["note"]
            if want:
                self.flags.append("%s asked for %d more buffer day(s) than were available." % (ev["name"], want))
        floating = nbuf - len(pinned)
        tests = [e for e in self.evaluations() if e.get("kind") == "test"]
        pos = {s.slot: k for k, s in enumerate(self.seq) if s.slot not in pinned_slots}
        tests = sorted((t for t in tests if t.get("due") in pos), key=lambda t: -pos[t["due"]])
        before = {}
        for t in tests[:floating]:
            before[t["due"]] = "buffer before %s" % t["name"]
        end_count = floating - len(before)
        items = []
        for s in self.seq:
            if s.slot in pinned_slots:
                continue
            if s.slot in before:
                items.append(("buffer", before[s.slot]))
            items.append(("slot", s))
        items += [("buffer", "end-of-semester buffer")] * end_count
        items = self.avoid_test_days(items, tests, {**pinned, **pin_at})
        it = iter(items)
        self.days = []
        done_by = {s.slot: s for s in self.done}
        for d in self.weekdays:
            if d in self.kept:
                k = self.kept[d]
                if k.get("kind") == "slot":
                    self.days.append({"date": d, "kind": "slot", "slot": done_by[k["slot"]]})
                else:
                    self.days.append({"date": d, "kind": k.get("kind"), "label": k.get("label", "")})
                    if k.get("kind") == "buffer":
                        self.buffer_days.append((d, k.get("label", "")))
                continue
            if self.resume_from and d < self.resume_from:
                self.days.append({"date": d, "kind": "closure", "label": self.closures.get(d, "No class")})
                continue
            if d in self.closures:
                self.days.append({"date": d, "kind": "closure", "label": self.closures[d]})
            elif d in pin_at:
                val = pin_at[d]
                val.date, val.note = d, notes.get(d)
                self.days.append({"date": d, "kind": "slot", "slot": val})
            elif d in pinned:
                self.days.append({"date": d, "kind": "buffer", "label": pinned[d]})
                self.buffer_days.append((d, pinned[d]))
            else:
                kind, val = next(it)
                if kind == "buffer":
                    self.days.append({"date": d, "kind": "buffer", "label": val})
                    self.buffer_days.append((d, val))
                else:
                    val.date = d
                    val.note = notes.get(d)
                    self.days.append({"date": d, "kind": "slot", "slot": val})
        if next(it, None) is not None:
            raise RuntimeError("slots left over after the last day; the fit step miscounted")
        order = [s.slot for s in self.seq]
        for s in pin_at.values():
            k = order.index(s.slot)
            early = [x.slot for x in self.seq[:k] if x.date > s.date]
            late = [x.slot for x in self.seq[k + 1:] if x.date < s.date]
            if early:
                self.flags.append("%s is pinned to %s, before %s, which come%s first in the course order."
                                  % (s.slot, fmt_long(s.date), ", ".join(early), "" if len(early) > 1 else "s"))
            if late:
                self.flags.append("%s is pinned to %s, after %s, which come%s later in the course order."
                                  % (s.slot, fmt_long(s.date), ", ".join(late), "" if len(late) > 1 else "s"))
        self.seq = sorted(self.done, key=lambda s: s.date) + sorted(self.seq, key=lambda s: s.date)
        exam = (self.course.get("assessment") or {}).get("exam")
        label = ("written examination (%s%%), day per school exam timetable" % exam) if exam else "final evaluation period"
        d = self.exam_start
        while d <= self.exam_end:
            if d.weekday() < 5:
                self.days.append({"date": d, "kind": "exam", "label": label})
            d += dt.timedelta(days=1)
        assert not sched - {x["date"] for x in self.days}
        if self.resume_from:
            self.buffer_days.sort()

    WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")

    def avoid_test_days(self, items, tests, pinned):
        """Keep unit tests off the weekdays in rehydration.yaml's constraints.avoid_test_days.
        A test on such a day takes a spare end-of-semester buffer in front of it (it
        moves one class day later), or gives up the buffer in front of it (one class
        day earlier), or takes a later test's buffer, or trades places with the flex
        day after it in the same block. What cannot be moved is flagged."""
        avoid = {self.WEEKDAYS.index(x[:3].title()) for x in ((self.params.get("constraints") or {}).get("avoid_test_days") or [])
                 if x[:3].title() in self.WEEKDAYS}
        if not avoid or not tests:
            return items
        free = [d for d in self.weekdays if d not in self.kept and not (self.resume_from and d < self.resume_from)
                and d not in self.closures and d not in pinned]
        names = {t["due"]: t["name"] for t in tests}
        items = list(items)
        unfixable = set()

        def where(slot):
            return next(k for k, (kind, v) in enumerate(items) if kind == "slot" and v.slot == slot)

        for _ in range(4 * len(tests) + 4):
            bad = None
            for k, (kind, v) in enumerate(items):
                if kind == "slot" and v.slot in names and k < len(free) and free[k].weekday() in avoid and v.slot not in unfixable:
                    bad = (k, v.slot)
                    break
            if not bad:
                break
            k, slot = bad
            was = free[k]
            ends = [j for j, (kind, v) in enumerate(items) if kind == "buffer" and v == "end-of-semester buffer"]
            mine = k > 0 and items[k - 1][0] == "buffer" and items[k - 1][1].startswith("buffer before")
            later = [j for j, (kind, v) in enumerate(items) if j > k and kind == "buffer" and v.startswith("buffer before")]
            if ends and k + 1 < len(free) and free[k + 1].weekday() not in avoid:
                items.pop(ends[-1])
                items.insert(k, ("buffer", "buffer before %s (keeps the test off a %s)" % (names[slot], self.WEEKDAYS[was.weekday()])))
                how = "a spare buffer day goes in front of it"
            elif mine and free[k - 1].weekday() not in avoid:
                items.pop(k - 1)
                items.append(("buffer", "end-of-semester buffer"))
                how = "its review buffer day moves to the end of the semester"
            elif later and k + 1 < len(free) and free[k + 1].weekday() not in avoid:
                j = later[-1]
                taken = items.pop(j)[1]
                items.insert(k, ("buffer", "buffer before %s (keeps the test off a %s)" % (names[slot], self.WEEKDAYS[was.weekday()])))
                how = "it takes the buffer day from %s" % taken.replace("buffer before ", "")
            elif (k + 1 < len(items) and k + 1 < len(free) and items[k + 1][0] == "slot" and items[k + 1][1].day_type == "flex"
                  and items[k + 1][1].block == items[k][1].block and free[k + 1].weekday() not in avoid):
                items[k], items[k + 1] = items[k + 1], items[k]
                how = "it trades places with %s, the flex day after it" % items[k][1].slot
            else:
                unfixable.add(slot)
                self.flags.append("%s lands on a %s (%s), a day this course avoids for tests, and no buffer or flex day could move it."
                                  % (names[slot], self.WEEKDAYS[was.weekday()], fmt_long(was)))
                continue
            self.test_moves.append((names[slot], was, free[where(slot)], how))
        return items

    # ----------------------------------------------------------- annotations
    def land(self, slot):
        """The scheduled slot an annotation for `slot` lands on: itself, or for a cut
        slot the nearest earlier day of the same week (else the week's first)."""
        by_slot = {s.slot: s for s in self.seq}
        if slot in by_slot:
            return by_slot[slot]
        if slot in {s for s, _ in self.cuts}:
            wk, day = slotmod.week_key(slot), slotmod.parse(slot)[2]
            same = [s for s in self.seq if s.week_key == wk]
            earlier = [s for s in same if slotmod.parse(s.slot)[2] < day]
            if earlier:
                return earlier[-1]
            return same[0] if same else None
        return None

    def annotate(self):
        order = {s.slot: k for k, s in enumerate(self.seq)}
        land = self.land

        evs = self.evaluations()
        assignments = sorted((e for e in evs if e.get("kind") == "assignment"),
                             key=lambda e: order.get(e.get("due"), 10 ** 6))
        numbers = {e["name"]: k + 1 for k, e in enumerate(assignments)}
        for e in evs:
            kind, name = e.get("kind"), e["name"]
            if kind == "assignment":
                text = "Assignment %d (%s)" % (numbers[name], pretty(name))
                pairs = (("handouts", e.get("handed_out")), ("dues", e.get("due")))
            elif kind == "culminating":
                text = name
                pairs = (("handouts", e.get("handed_out")), ("dues", e.get("due")))
            elif kind == "milestone":
                text = name
                pairs = (("dues", e.get("due")),)
            else:
                continue
            for field, slot in pairs:
                if not slot:
                    continue
                target = land(str(slot))
                if target is not None and self.resume_from and target.date < self.resume_from:
                    continue
                if target is None:
                    self.flags.append("%s: %s slot %s is not in this semester's plan." % (name, field[:-1], slot))
                    continue
                label = text
                if target.slot != slot:
                    label = "%s (moved from %s)" % (text, slot)
                    self.moves.append((name, field[:-1], slot, target.slot))
                if label not in getattr(target, field):
                    getattr(target, field).append(label)

    def instance_weeks(self):
        """Week plans that get a dated copy: those with a scheduled or cut slot."""
        live = {s.slot for s in self.seq} | {s for s, _ in self.cuts}
        return [w for w in self.weeks
                if any(str(d.get("slot")) in live for d in w.plan.get("daily_lessons") or [])]

    def check_constraints(self):
        lo, hi = (self.params.get("constraints") or {}).get("assignment_window", [7, 10])
        dated = [x for x in self.days if x["kind"] in ("slot", "buffer")]
        by_slot = {s.slot: s for s in self.seq}

        def between(a, b):
            return sum(1 for x in dated if a < x["date"] <= b)

        self.windows = []
        for e in self.evaluations():
            if e.get("kind") == "assignment" and e.get("handed_out") in by_slot and e.get("due") in by_slot:
                a, b = by_slot[e["handed_out"]], by_slot[e["due"]]
                w = between(a.date, b.date)
                self.windows.append((e["name"], a, b, w))
                if not lo <= w <= hi and not (self.resume_from and b.date < self.resume_from):
                    self.flags.append("%s runs %d class days (%s to %s); the rule is %d to %d."
                                      % (e["name"], w, fmt_short(a.date), fmt_short(b.date), lo, hi))
            if e.get("kind") == "test" and e.get("due") in by_slot and by_slot[e["due"]].day_type != "assess":
                self.flags.append("%s is due on %s, a %s day." % (e["name"], e["due"], by_slot[e["due"]].day_type))
        lead = (self.params.get("constraints") or {}).get("demo_lead_days")
        cdue = [by_slot[e["due"]] for e in self.evaluations() if e.get("kind") == "culminating" and e.get("due") in by_slot]
        if lead and cdue:
            last = max(s.date for s in cdue)
            gap = sum(1 for x in dated if last < x["date"] < self.exam_start)
            if gap < lead:
                self.flags.append("The last culminating submission (%s) is %d class day(s) before the exams; the rule is %d."
                                  % (fmt_short(last), gap, lead))


def build(root, cfg, params, course_cfg, previous=None):
    """previous: the instance's existing calendar.yaml (a dict); required when the
    config sets resume_from. A config that names a school_calendar has it merged in first."""
    try:
        cfg = schoolcal.resolve(cfg)
    except schoolcal.SchoolCalendarError as e:
        raise ConfigError(str(e))
    plan = Plan(root, cfg, params, course_cfg)
    plan.assemble()
    plan.build_calendar()
    if cfg.get("resume_from"):
        if not previous:
            raise ConfigError("resume_from is set but there is no existing calendar.yaml to resume from")
        plan.resume(previous)
    plan.fit()
    plan.place()
    plan.annotate()
    plan.check_constraints()
    return plan


# ======================================================================= output
def master_commit(root):
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def calendar_yaml(plan, generated_on, commit):
    days = []
    for x in plan.days:
        d = {"date": x["date"].isoformat(), "kind": x["kind"]}
        if x["kind"] == "slot":
            s = x["slot"]
            d.update({"slot": s.slot, "week_key": s.week_key,
                      "week_plan": s.week_plan_rel or (("week_plans/%s.yaml" % s.week.instance_name) if s.week else None),
                      "master_dir": s.master_dir, "title": s.title, "day_type": s.day_type,
                      "sub_ready": s.sub_ready, "handouts": list(s.handouts), "dues": list(s.dues)})
            if s.note:
                d["note"] = s.note
        else:
            d["label"] = x["label"]
        days.append(d)
    sem = plan.cfg["semester"]
    doc = {"schema": 1,
           "generated": {"on": generated_on, "master_commit": commit},
           "course": {"code": plan.course.get("code"), "name": plan.course.get("title"), "teacher": plan.course.get("teacher")},
           "semester": {k: str(sem[k]) for k in ("name", "first_day", "last_day", "exam_start", "exam_end")},
           "days": days,
           "cuts": [{"slot": s, "priority": t.get("priority")} for s, t in plan.cuts]}
    head = "# Machine-readable instance calendar. Schema: Teaching/Standards/rehydration/Calendar_Schema.yaml\n"
    head += "# Written by Skills/semester/scripts/rehydrate.py; regenerate instead of editing.\n"
    return head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)


def week_plan_text(week, dates):
    """The master week plan with dates injected; byte-identical otherwise."""
    prefix = week.prefix
    dated = sorted(v for v in dates.values() if v)
    text = week.text
    if dated:
        text = text.replace('"{{WEEK_START}}"', '"%s"' % dated[0].isoformat())
        text = text.replace('"{{WEEK_END}}"', '"%s"' % dated[-1].isoformat())

    def day(m):
        slot = "%s.D%s" % (prefix, m.group(1))
        v = dates.get(slot)
        return 'date: "%s"' % (v.isoformat() if v else CUT_MARK)
    return re.sub(r'date: "\{\{D(\d+)_DATE\}\}"', day, text)


def refresh_week_plans(root, inst_dir, params):
    """Rewrite an instance's week_plans/ from master, with the date calendar.yaml
    gives each slot (the CUT mark where it gives none), so master edits reach
    the instance without re-planning. Returns the files that changed."""
    with open(os.path.join(inst_dir, "calendar.yaml"), encoding="utf-8") as f:
        cal = yaml.safe_load(f)
    dates = {str(d["slot"]): dt.date.fromisoformat(str(d["date"])) for d in cal["days"] if d.get("kind") == "slot"}
    entries = [wp for b in params["sequence"] for wp in b.get("week_plans") or []]
    entries += [wp for m in params.get("modules") or [] for form in (m.get("forms") or {}).values()
                for wp in form.get("week_plans") or []]
    changed = []
    for wp in entries:
        wp = wp if isinstance(wp, dict) else {"path": wp}
        w = Week(root, wp["path"], None, wp.get("instance_name"))
        p = os.path.join(inst_dir, "week_plans", w.instance_name + ".yaml")
        if not os.path.exists(p):
            continue   # a module form this instance does not use
        wdates = {"%s.D%s" % (w.prefix, d.get("day")): dates.get(str(d.get("slot"))) for d in w.plan.get("daily_lessons") or []}
        text = week_plan_text(w, wdates)
        with open(p, encoding="utf-8") as f:
            if f.read() == text:
                continue
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        changed.append(p)
    return changed


def course_calendar_md(plan, commit):
    c, sem = plan.course, plan.cfg["semester"]
    lines = ["# %s Course Calendar, %s" % (c.get("code"), sem["name"]), "",
             "**Instruction:** %s to %s · **Exam period:** %s to %s" % (
                 fmt_long(plan.first), fmt_long(plan.last), fmt_long(plan.exam_start), fmt_long(plan.exam_end)),
             "**Generated from:** `master/` at commit %s (see `GENERATION_REPORT.md`)" % (commit or "unknown"), "",
             "Buffer days are planned slack: if class runs normally on one, use it for review and catch-up. "
             "Sub-ready: yes means a substitute without the subject can run the day from the week plan's materials.", "",
             "| Date | Slot | Topic / event | Type | Sub-ready |",
             "|------|------|---------------|------|-----------|"]
    for x in plan.days:
        d = fmt_long(x["date"])
        if x["kind"] == "slot":
            s = x["slot"]
            topic = s.title
            for h in s.handouts:
                topic += "; %s handed out" % h
            for h in s.dues:
                topic += "; %s due" % h
            if s.note:
                topic += " (%s)" % s.note
            lines.append("| %s | %s | %s | %s | %s |" % (d, s.slot, topic.replace("|", "/"), s.day_type, "yes" if s.sub_ready else "no"))
        elif x["kind"] == "buffer":
            lines.append("| %s | BUFFER | *Buffer day (%s): catch-up or review if class runs* | flex | yes |" % (d, x["label"]))
        elif x["kind"] == "closure":
            lines.append("| %s | - | *No class: %s* | - | - |" % (d, x["label"]))
        else:
            lines.append("| %s | EXAM | *%s* | - | - |" % (d, x["label"]))
    return "\n".join(lines) + "\n"


def report_md(plan, generated_on, commit):
    m, sem = plan.math, plan.cfg["semester"]
    L = ["# Generation Report, %s" % sem["name"], "",
         "**Generated:** %s, from `master/` at commit %s by the shared rehydration generator." % (generated_on, commit or "unknown"),
         "**Config:** `semester_config.yaml` in this folder.%s%s" % (
             " **School calendar:** %s." % plan.cfg["_school_calendar"] if plan.cfg.get("_school_calendar") else "",
             "".join(" **%s:** %s." % (k, v) for k, v in sorted(plan.module_modes.items()))), "",
         ("**Resumed from:** %s. Every day before it is kept exactly as the previous calendar had it (%d taught slot(s)); "
          "the figures below cover the re-planned part." % (fmt_long(plan.resume_from), m.get("taught", 0)) if plan.resume_from else ""),
         "## Calendar math", "", "| Quantity | Value |", "|----------|-------|",
         "| Weekdays, %s to %s | %d |" % (fmt_long(plan.first), fmt_long(plan.last), m["weekdays"]),
         "| Closed | %d |" % m["closed"],
         "| **Scheduled class days** | **%d** |" % m["scheduled"],
         "| Usable (%g factor) | %d |" % (m["usable_fraction"], m["usable"]),
         "| Disruption reserve | %d |" % m["reserve"],
         "| Nominal slots | %d |" % m["nominal"],
         "| Slots scheduled after compression | %d%s |" % (m["slots"], " (incl. %d reserve-spill day(s))" % m["spill"] if m["spill"] else ""),
         "| Buffer days | %d |" % m["buffers"],
         "| Exam period | %s to %s |" % (fmt_long(plan.exam_start), fmt_long(plan.exam_end)), ""]
    decisions = [str(x) for x in plan.cfg.get("decisions") or []]
    if decisions:
        L += ["## Decisions made with the teacher", ""] + ["%d. %s" % (k + 1, x) for k, x in enumerate(decisions)] + [""]
    if plan.log_changes:
        L += ["## From the teaching log", "", "| Slot | What happened |", "|------|---------------|"]
        L += ["| %s | %s |" % (s, w) for s, w in plan.log_changes] + [""]
    L += ["## Compression applied", ""]
    if plan.cuts:
        L += ["| Priority | Cut | Days | Consequence |", "|----------|-----|------|-------------|"]
        tiers = []
        for s, t in plan.cuts:
            if not tiers or tiers[-1][0] is not t:
                tiers.append((t, []))
            tiers[-1][1].append(s)
        for t, ss in tiers:
            L.append("| P%s | %s: %s | %d | %s |" % (t.get("priority"), t.get("what", ""), ", ".join(ss), len(ss), t.get("consequence", "")))
    else:
        L.append("None: the plan fits the usable days without cuts.")
    if plan.spill:
        L += ["", "**Reserve spill:** %d module day(s) drawn from the disruption reserve; %d reserve day(s) remain."
              % (plan.spill, m["reserve"] - plan.spill)]
    L += ["", "## Buffer days", "", "| Date | Why here |", "|------|----------|"]
    L += ["| %s | %s |" % (fmt_long(d), why) for d, why in plan.buffer_days]
    if plan.test_moves:
        L += ["", "## Tests kept off avoided days", "", "| Test | Would have been | Now | How |", "|------|-----------------|-----|-----|"]
        L += ["| %s | %s | %s | %s |" % (n, fmt_long(a), fmt_long(b), how) for n, a, b, how in plan.test_moves]
    if plan.moves:
        L += ["", "## Annotations moved off cut days", "", "| Item | Annotation | Master slot | Instance slot |",
              "|------|------------|-------------|---------------|"]
        L += ["| %s | %s | %s | %s |" % mv for mv in plan.moves]
    L += ["", "## Instance adjustments (master unchanged)", "",
          "Each assignment is handed out and due on the slots its week plan's `evaluations` entry names. "
          "Week plans are byte-identical to master apart from the injected dates; cut days carry `date: %s`." % CUT_MARK, "",
          "Assignment windows (class days after hand-out up to and including the due day; buffer days count because class runs, closures do not):", "",
          "| Assignment | Hand-out | Due | Window |", "|------------|----------|-----|--------|"]
    L += ["| %s | %s (%s) | %s (%s) | %d |" % (n, a.slot, fmt_short(a.date), b.slot, fmt_short(b.date), w) for n, a, b, w in plan.windows]
    notes = plan.cfg.get("overrides") or []
    if notes:
        L += ["", "## Notes from the semester config", ""] + ["- %s" % n for n in notes]
    L += ["", "## Flags for the teacher", ""]
    flags = list(plan.flags) + [str(x) for x in plan.cfg.get("flags") or [] if str(x) not in plan.flags]
    L += ["%d. %s" % (k + 1, f) for k, f in enumerate(flags)] or ["None."]
    L += ["", "## Files written by the generator", "",
          "- `semester_config.yaml`: the input", "- `calendar.yaml`: the machine-readable calendar",
          "- `Course_Calendar.md`: every weekday, %d slots, %d buffers, %d closures, plus the exam period" % (
              m["slots"], m["buffers"], m["closed"]),
          "- `week_plans/`: %d dated week plans" % len(plan.instance_weeks()),
          "- `Assessment_Register.md`, `Short_and_Long_Term_Plan.md`, `Course_Outline.md`: built from the unit overviews, `rehydration.yaml`, `course.yaml` and the calendar",
          "- `GENERATION_REPORT.md`: this file"]
    return "\n".join(L) + "\n"


def write(plan, out_dir, config_path, generated_on=None):
    if not generated_on:
        t = dt.date.today()
        generated_on = "%s %d, %d" % (t.strftime("%B"), t.day, t.year)
    commit = master_commit(plan.root)
    os.makedirs(os.path.join(out_dir, "week_plans"), exist_ok=True)
    dates = {s.slot: s.date for s in plan.seq}
    written = []
    for w in plan.instance_weeks():
        wdates = {"%s.D%s" % (w.prefix, d.get("day")): dates.get(str(d.get("slot"))) for d in w.plan.get("daily_lessons") or []}
        p = os.path.join(out_dir, "week_plans", w.instance_name + ".yaml")
        with open(p, "w", encoding="utf-8") as f:
            f.write(week_plan_text(w, wdates))
        written.append(p)
    from .instance_docs import Docs
    docs = Docs(plan)
    files = {"calendar.yaml": calendar_yaml(plan, generated_on, commit),
             "Course_Calendar.md": course_calendar_md(plan, commit),
             "Assessment_Register.md": docs.register_md(),
             "Short_and_Long_Term_Plan.md": docs.plan_md()}
    outline = docs.outline_md()
    if outline is not None:
        files["Course_Outline.md"] = outline
    plan.flags.extend(f for f in docs.flags if f not in plan.flags)
    files["GENERATION_REPORT.md"] = report_md(plan, generated_on, commit)
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)
    dest = os.path.join(out_dir, "semester_config.yaml")
    if os.path.abspath(config_path) != os.path.abspath(dest):
        with open(config_path, encoding="utf-8") as src, open(dest, "w", encoding="utf-8") as f:
            f.write(src.read())
    return written + [os.path.join(out_dir, n) for n in files] + [dest]


def load_params(root, course_cfg):
    path = os.path.join(root, "master", course_cfg["rehydration_dir"], "rehydration.yaml")
    if not os.path.exists(path):
        raise ConfigError("%s does not exist; this course has no machine-readable rehydration parameters yet" % path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


__all__ = ["build", "write", "load_params", "NeedsTeacher", "ConfigError", "weekplan"]

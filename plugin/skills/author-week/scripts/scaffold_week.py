#!/usr/bin/env python3
"""Scaffold one week of a GLA course master: correctly named, correctly headed starting files.

    python3 scaffold_week.py U2.W3 [--root COURSE_ROOT] [--only D3|deliverable|ref|plan] [--dry-run]

Reads course.yaml, the unit's unit_overview.md (week architecture, rhythm,
evaluations, reference sheets), the Curriculum_Coverage_Map.md and the
curriculum, then writes into master/02_Units/U<n>_*/W<m>_*/:

  week_plan.yaml                 from Standards/templates/Weekly_Plan_Schema.yaml
  D<n>_Lesson_<Topic>.md         one per teach day, from Day_Lesson_Template.md
  EX_<Topic>.md + _KEY.md        standard rhythm, from Exercise_Template.md
  BRIEF_<Topic>.md + _MARKING.md studio rhythm
  REF_<Topic>.md                 from Reference_Sheet_Template.md

Bodies stay as the templates' placeholders for the model to write. Existing
files are never overwritten. Decks are not created; the deck assembler command
is printed for each teach day. Assignments and tests are out of scope.
"""
import argparse
import copy
import glob
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
import yaml  # noqa: E402

from gla.codes import CODE, codes_in  # noqa: E402
from gla import course, coverage, curriculum, mdtable, paths, slots, weekplan  # noqa: E402

TEMPLATES = os.path.join(paths.STANDARDS, "templates")

DELIV_RE = re.compile(r"\b(EX|BRIEF)_([A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)")
WEEK_HEAD = re.compile(r"^### (W\d+):\s*(.+?)\s*(?:\(`(W\d+_[^`/]+)/?`\))?\s*$", re.M)
SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "vs", "with"}
CATEGORIES = ["Knowledge/Understanding", None, "Communication", "Application"]


# ------------------------------------------------------------------ naming
def topic_token(topic):
    """Overview topic -> the <Topic> string of a file name.

    The rule, read off the existing ICS3U, ICS4U and ICD2O pairs:
    drop markdown, a leading "Mini-teach:" and a trailing "+ studio"; drop
    parentheticals; keep the part before a " · "; for "A: B" keep A, unless A
    is a single word and B carries no comma (then keep both); "+" and "&"
    become "and"; apostrophes vanish, hyphens and slashes split words, other
    punctuation drops; words are ASCII-folded and joined with underscores,
    each starting with a capital except the small connecting words (and, of,
    the, in, ...) after the first word, which keep the case the topic gives them.
    """
    t = re.sub(r"[*`]", "", topic or "").strip()
    t = re.sub(r"^\s*mini-teach\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s*\+\s*studio\s*$", "", t, flags=re.I)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = t.split(" · ")[0]
    if ":" in t:
        head, tail = t.split(":", 1)
        t = head if (len(head.split()) > 1 or "," in tail) else head + " " + tail
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"\s*[+&]\s*", " and ", t)
    t = re.sub(r"['’]", "", t)
    t = re.sub(r"[-/]", " ", t)
    t = re.sub(r"[^A-Za-z0-9 ]", " ", t)
    out = []
    for i, w in enumerate(t.split()):
        if i and w.lower() in SMALL:
            out.append(w)
        else:
            out.append(w[0].upper() + w[1:])
    return "_".join(out)


def spaced(token):
    return token.replace("_", " ")


# ------------------------------------------------------------------ codes
# ------------------------------------------------------------------ overview
class Week:
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_week(overview_text, unit, week):
    """The week's heading, folder and rows from '## Week architecture'."""
    arch = overview_text
    m = re.search(r"^## Week architecture.*$", overview_text, re.M)
    if m:
        rest = overview_text[m.end():]
        n = re.search(r"^## ", rest, re.M)
        arch = rest[:n.start()] if n else rest
    for h in WEEK_HEAD.finditer(arch):
        if h.group(1) != "W%d" % week:
            continue
        body = arch[h.end():]
        n = re.search(r"^#{2,3} ", body, re.M)
        body = body[:n.start()] if n else body
        w = Week()
        w.title, w.folder, w.section = h.group(2).strip(), h.group(3), body
        w.days = []
        t = mdtable.find_table(body, "slot", "type", "topic")
        if t:
            hdr, rows, _ = t
            si, yi, ti = mdtable.column(hdr, "slot"), mdtable.column(hdr, "type"), mdtable.column(hdr, "topic")
            try:
                ni = mdtable.column(hdr, "notes")
            except KeyError:
                ni = None
            for _, c in rows:
                slot = c[si].strip() if si < len(c) else ""
                if not slots.is_slot(slot):
                    continue
                w.days.append({"slot": slot, "day": slots.parse(slot)[2], "type": c[yi].strip() if yi < len(c) else "",
                               "topic": c[ti].strip() if ti < len(c) else "",
                               "notes": c[ni].strip() if ni is not None and ni < len(c) else ""})
        return w
    return None


def day_type(raw):
    """'teach + studio' -> 'teach'; unknown -> None."""
    first = re.split(r"[\s+/]+", raw.strip().lower())[0] if raw.strip() else ""
    return first if first in weekplan.DAY_TYPES else None


def evaluations(overview_text):
    """{item: (handed_out, due)} from the overview's Evaluations table."""
    t = mdtable.find_table(overview_text, "item", "handed out", "due")
    out = {}
    if not t:
        return out
    hdr, rows, _ = t
    ii, hi, di = mdtable.column(hdr, "item"), mdtable.column(hdr, "handed out"), mdtable.column(hdr, "due")
    for _, c in rows:
        name = re.sub(r"[*`]", "", c[ii]).strip() if ii < len(c) else ""
        h = slots.find_all(c[hi]) if hi < len(c) else []
        d = slots.find_all(c[di]) if di < len(c) else []
        if name:
            out[name] = (h[0] if h else None, d[0] if d else None)
    return out


def reference_sheets(overview_text):
    """None when the overview has no '## Reference sheets' section, else {week: [REF_ names]}
    (a sheet belongs to the first week its parenthetical names)."""
    m = re.search(r"^## Reference sheets\s*$", overview_text, re.M)
    if not m:
        return None
    rest = overview_text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    out = {}
    for line in (rest[:n.start()] if n else rest).splitlines():
        r = re.search(r"`(REF_[A-Za-z0-9_]+)\.md`(?:\s*\((W\d+))?", line)
        if r:
            out.setdefault(r.group(2), []).append(r.group(1))
    return out


# ------------------------------------------------------------------ YAML
class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _list(dumper, data):
    flow = bool(data) and all(isinstance(x, (str, int, float, bool)) for x in data) and len(data) <= 12
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


def _str(dumper, data):
    style = '"' if (data == "" or "{" in data) else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_Dumper.add_representer(list, _list)
_Dumper.add_representer(str, _str)


def dump_plan(plan):
    """YAML text with a blank line between top-level sections."""
    return "\n".join(yaml.dump({k: v}, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100,
                               default_flow_style=False) for k, v in plan.items())


# ------------------------------------------------------------------ scaffold
class Scaffolder:
    def __init__(self, root, week_key, only=None, dry_run=False, out=sys.stdout):
        self.root = os.path.abspath(root)
        self.key = week_key
        self.only = only
        self.dry = dry_run
        self.out = out
        self.created, self.skipped, self.notes, self.unresolved, self.decks = [], [], [], [], []
        self.codes_report = []

    def say(self, *a):
        print(*a, file=self.out)

    # -- inputs
    def load(self):
        m = re.fullmatch(r"U(\d+)\.W(\d+)", self.key)
        if not m:
            raise SystemExit("ERROR: week must look like U2.W3 (got %r)" % self.key)
        self.unit, self.week = "U%s" % m.group(1), int(m.group(2))
        self.cfg = course.load(self.root)
        units = sorted(glob.glob(os.path.join(self.root, "master", "02_Units", "%s_*" % self.unit)))
        units = [u for u in units if os.path.isdir(u)]
        if not units:
            raise SystemExit("ERROR: no master/02_Units/%s_*/ folder" % self.unit)
        self.unit_dir = units[0]
        ov = os.path.join(self.unit_dir, "unit_overview.md")
        if not os.path.exists(ov):
            raise SystemExit("ERROR: %s has no unit_overview.md" % self.unit_dir)
        self.overview = read(ov)
        self.w = parse_week(self.overview, self.unit, self.week)
        if not self.w:
            raise SystemExit("ERROR: no '### W%d:' entry under '## Week architecture' in %s" % (self.week, ov))
        if not self.w.days:
            self.unresolved.append("W%d has no | Slot | Type | Topic | Notes | table rows" % self.week)
        h1 = re.search(r"^# (.+)$", self.overview, re.M)
        self.unit_name = h1.group(1).split(":", 1)[1].strip() if h1 and ":" in h1.group(1) else (h1.group(1).strip() if h1 else "")
        rh = re.search(r"\*\*Rhythm:\*\*\s*([A-Za-z]+)", self.overview)
        if not rh or rh.group(1).lower() not in weekplan.RHYTHMS:
            raise SystemExit("ERROR: %s needs a **Rhythm:** line saying %s (it %s)" % (
                os.path.relpath(ov, self.root), " or ".join(weekplan.RHYTHMS),
                "says %r" % rh.group(1) if rh else "has none"))
        self.rhythm = rh.group(1).lower()
        self.rhythm_src = "unit_overview **Rhythm:**"

        folder = self.w.folder
        if not folder:
            folder = "W%d_%s" % (self.week, topic_token(self.w.title))
            self.notes.append("week heading names no folder; using %s" % folder)
        self.dir = os.path.join(self.unit_dir, folder)

        try:
            self.cur = curriculum.load(self.cfg["code"])
            self.order = {c: i for i, c in enumerate(self.cur.specific_codes())}
        except (KeyError, FileNotFoundError):
            self.cur, self.order = None, {}
            self.unresolved.append("no curriculum data for %s; codes are not checked" % self.cfg.get("code"))
        self.cov = coverage.taught_rows(os.path.join(self.root, "master", "01_Standards", "Curriculum_Coverage_Map.md"))
        if not self.cov:
            self.unresolved.append("no Code tables in master/01_Standards/Curriculum_Coverage_Map.md")
        self.evals = evaluations(self.overview)
        self.refs = reference_sheets(self.overview)
        self.existing = os.listdir(self.dir) if os.path.isdir(self.dir) else []

    def real(self, codes, where):
        if not self.order:
            return list(codes)
        bad = [c for c in codes if c not in self.order]
        if bad:
            self.unresolved.append("%s: %s not in the %s curriculum, dropped" % (where, ", ".join(bad), self.cfg["code"]))
        return [c for c in codes if c in self.order]

    def sort(self, codes):
        return sorted(set(codes), key=lambda c: self.order.get(c, 10 ** 6))

    # -- decisions
    def plan_week(self):
        self.assess_week = any(day_type(d["type"]) == "assess" for d in self.w.days)
        self.week_codes = self.sort(self.real([c for c, cell in self.cov if coverage.mentions_week(cell, self.unit, self.week)], "coverage map"))
        self.codes_report.append(("week_plan specific", self.week_codes, "coverage map rows whose Taught in / Anchor cell names %s" % self.key))

        self.teach, self.labs = [], []
        for d in self.w.days:
            dt = day_type(d["type"])
            if dt is None:
                self.unresolved.append("%s: type %r is not a day_type; written as is" % (d["slot"], d["type"]))
            if dt == "wet_lab":
                self.labs.append({"day": d, "n": d["day"], "token": topic_token(d["topic"]), "codes": self.day_codes(d)})
            if dt != "teach":
                continue
            n = d["day"]
            token, src = self.existing_token(n)
            if not token:
                token, src = topic_token(d["topic"]), "derived from the overview topic"
            codes, csrc = self.day_codes(d, with_source=True)
            if not codes:
                self.unresolved.append("%s: no expectation codes found; header left as <codes>" % d["slot"])
            self.codes_report.append(("D%d lesson" % n, codes, csrc))
            self.teach.append({"day": d, "n": n, "token": token, "token_src": src, "codes": codes,
                               "mini": "studio" in d["type"].lower() or d["topic"].lower().startswith("mini-teach")})

        self.deliverables = self.find_deliverables()
        self.ref = self.find_ref()


    def existing_token(self, n):
        for x in sorted(self.existing):
            m = re.match(r"^D%d_(?:Lesson|Slides)_(.+?)(?:_GUIDE)?\.(?:md|html)$" % n, x)
            if m:
                return m.group(1), "reused from existing %s" % x
        return None, None

    def find_deliverables(self):
        names = []
        for d in self.w.days:
            for kind, tok in DELIV_RE.findall(d["topic"]):
                if (kind, tok) not in names:
                    names.append((kind, tok))
        for item, (h, _) in self.evals.items():
            m = DELIV_RE.fullmatch(item)
            if m and h and slots.week_key(h) == self.key and (m.group(1), m.group(2)) not in names:
                names.append((m.group(1), m.group(2)))
        out = []
        for kind, tok in names:
            name = "%s_%s" % (kind, tok)
            h, due = self.evals.get(name, (None, None))
            rows = [d for d in self.w.days if name in d["topic"]]
            if h and slots.week_key(h) != self.key:
                self.notes.append("%s is named here but handed out %s; it lives in that week's folder, not created" % (name, h))
                continue
            h = h or (rows[0]["slot"] if rows else None)
            due = due or (rows[-1]["slot"] if rows else None)
            want = "BRIEF" if self.rhythm == "studio" else "EX"
            if kind != want:
                self.notes.append("%s is a %s file in a %s-rhythm unit (named by the overview, kept)" % (name, kind, self.rhythm))
            out.append({"kind": kind, "token": tok, "src": "named in the overview", "handed": h, "due": due, "rows": rows})
        if not out and not self.assess_week and self.w.days:
            kind = "BRIEF" if self.rhythm == "studio" else "EX"
            tok = topic_token(self.w.title)
            non = [d for d in self.w.days if day_type(d["type"]) in ("exercise", "studio")]
            out.append({"kind": kind, "token": tok, "src": "not named in the overview; derived from the week title",
                        "handed": non[0]["slot"] if non else None, "due": non[-1]["slot"] if non else None, "rows": non})
            self.unresolved.append("deliverable not named in the overview; derived %s_%s from the week title" % (kind, tok))
        elif not out:
            self.notes.append("assessment week with no exercise or brief named; no deliverable created")
        for dv in out:
            name = "%s_%s" % (dv["kind"], dv["token"])
            if dv["kind"] == "BRIEF":
                dv["companion"] = "MARKING"
            elif re.search(r"\b%s_MARKING\b" % re.escape(name), self.overview) or any(x == name + "_MARKING.md" for x in self.existing):
                dv["companion"] = "MARKING"
            else:
                dv["companion"] = "KEY"
            codes = []
            for t in self.teach:
                codes += t["codes"]
            for d in dv["rows"]:
                codes += self.real(codes_in(d["notes"]), d["slot"] + " notes")
            dv["codes"] = self.sort(codes) or self.week_codes
            self.codes_report.append((name, dv["codes"], "teach-day lesson codes plus the deliverable rows' Notes"
                                      if self.sort(codes) else "week_plan specific (no lesson or notes codes)"))
        return out

    def find_ref(self):
        if self.refs is None:
            if self.assess_week:
                self.notes.append("overview lists no reference sheets; assessment week, no REF created")
                return None
            tok = topic_token(self.w.title)
            self.unresolved.append("overview has no '## Reference sheets' section; derived REF_%s from the week title" % tok)
            return {"token": tok, "src": "derived from the week title"}
        listed = self.refs.get("W%d" % self.week) or []
        if listed:
            if len(listed) > 1:
                self.notes.append("several reference sheets listed for W%d; scaffolding the first (%s)" % (self.week, listed[0]))
            return {"token": listed[0][4:], "src": "listed under ## Reference sheets"}
        if self.only == "ref":
            tok = topic_token(self.w.title)
            self.notes.append("no REF listed for W%d; --only ref derived REF_%s from the week title" % (self.week, tok))
            return {"token": tok, "src": "derived from the week title (--only ref)"}
        self.notes.append("no REF listed for W%d under ## Reference sheets; none created (an earlier week's sheet covers it, or pass --part ref)" % self.week)
        return None

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

    def day_codes(self, d, with_source=False):
        """A day's codes: its overview Notes cell, else the coverage map rows naming its
        slot, else the rows naming its week without a day."""
        codes = self.sort(self.real(codes_in(d["notes"]), d["slot"] + " notes"))
        csrc = "overview Notes cell"
        if not codes:
            slot_re = re.compile(r"(?<![\w.])%s(?!\d)" % re.escape(d["slot"]))
            codes = [c for c, cell in self.cov if slot_re.search(cell)]
            csrc = "coverage map rows naming %s" % d["slot"]
            if not codes:
                codes = [c for c, cell in self.cov if coverage.mentions_week(cell, self.unit, self.week)
                         and not re.search(r"(?<![\w.])%s\.W%d\.D\d" % (re.escape(self.unit), self.week), cell)]
                csrc = "coverage map rows naming %s without a day" % self.key
            codes = self.sort(self.real(codes, d["slot"] + " coverage"))
        return (codes, csrc) if with_source else codes

    def write_lab(self, lab):
        d = lab["day"]
        head = "# Lab: %s\n\n**Slot:** %s · **Type:** wet_lab\n**Expectations:** %s\n**Time:** ~50 min\n\n" % (
            re.sub(r"\*\*", "", d["topic"]).strip(), d["slot"], ", ".join(lab["codes"]) or "<codes>")
        self.emit("D%d_Lab_%s.md" % (lab["n"], lab["token"]), head + self.body_after_header(self.template("Lab_Template.md")))

    def body_after_header(self, tpl):
        """Template text from its first '## ' heading on."""
        m = re.search(r"^## ", tpl, re.M)
        return tpl[m.start():] if m else ""

    def ref_name(self):
        return "REF_%s.md" % self.ref["token"] if self.ref else None

    def write_lesson(self, t):
        d, n = t["day"], t["n"]
        typ = "teach (mini-teach + studio)" if t["mini"] and "studio" in d["type"].lower() else "teach"
        head = "# %s\n\n**Slot:** %s · **Type:** %s\n**Expectations:** %s\n**Time:** ~50 min\n\n" % (
            re.sub(r"\*\*", "", d["topic"]).strip(), d["slot"], typ, ", ".join(t["codes"]) or "<codes>")
        body = self.body_after_header(self.template("Day_Lesson_Template.md"))
        body = body.replace("`D__Slides_<Topic>.html` (teach days, in a course with decks)", "`D%d_Slides_%s.html`" % (n, t["token"]) if course.switch(self.cfg, "decks")
                            else "(no slide deck in this course)")
        if self.ref:
            body = body.replace("`REF_<Topic>.md` (if a reference sheet accompanies this topic)", "`%s`" % self.ref_name())
        self.emit("D%d_Lesson_%s.md" % (n, t["token"]), head + body)

    def write_deliverable(self, dv):
        name = "%s_%s" % (dv["kind"], dv["token"])
        codes = ", ".join(dv["codes"]) or "<codes>"
        h, due = dv["handed"] or "U_.W_.D_", dv["due"] or "U_.W_.D_"
        if not (dv["handed"] and dv["due"]):
            self.unresolved.append("%s: hand-out or due slot not found; left as U_.W_.D_" % name)
        if dv["kind"] == "EX":
            slot = "handed out %s, due %s" % (h, due)
            body = self.body_after_header(self.template("Exercise_Template.md"))
            if self.ref:
                body = body.replace("<ref sheet name>", self.ref_name())
            self.emit(name + ".md", "# Exercise: %s\n\n**Slot:** %s · **Type:** exercise\n**Expectations:** %s\n**Marks:** /10\n\n%s"
                      % (spaced(dv["token"]), slot, codes, body))
            if dv["companion"] == "KEY":
                self.emit(name + "_KEY.md", "# Exercise KEY: %s\n\n**Slot:** %s · **Type:** exercise (teacher key)\n"
                          "**Expectations:** %s\n**Marks:** /10\n\n## Answers\n\n<full, compiling solutions for every part>\n\n"
                          "## Marking guide\n\n<what earns 10, 7 to 9, 4 to 6, 1 to 3; accepted variations>\n" % (spaced(dv["token"]), slot, codes))
            else:
                self.emit(name + "_MARKING.md", "# Marking Notes: %s (teacher only)\n\n**Slot:** %s · **Type:** exercise (teacher marking notes)\n"
                          "**Expectations:** %s\n**Marks:** /10\n\n## What complete and correct (10) looks like\n\n<expected strong answers>\n\n"
                          "## The 7 to 9 and 4 to 6 bands\n\n<common gaps and how they map to marks>\n" % (name, slot, codes))
        else:
            slot = "%s (start and ship today)" % h if h == due else "%s (start) → %s (ship)" % (h, due)
            ref_line = " (and %s)" % self.ref_name() if self.ref else ""
            self.emit(name + ".md", "# %s\n\n**Slot:** %s · **Type:** studio brief\n**Expectations:** %s\n**Marks:** /10\n\n"
                      "| Marks | Meaning |\n|-------|---------|\n| 10 | Complete and correct (all hard requirements met) |\n"
                      "| 7–9 | Complete with minor gaps |\n| 4–6 | Substantial attempt |\n| 1–3 | Minimal attempt |\n| 0 | Not submitted |\n\n"
                      "## The brief\n\n<the creative prompt: what the piece is, in two or three sentences>\n\n"
                      "## Hard requirements (the /10 checklist)\n\n1. <requirement>\n2. <requirement>\n3. <requirement>\n\n"
                      "## Working rules\n\n- <rule>\n\n## Challenge (optional, unmarked)\n\n<one harder variation>\n\n---\n\n"
                      "> **Running this class with a substitute**\n>\n> **Hand out:** this brief%s. **Students should be doing:** <quiet studio work against the checklist>. "
                      "**\"Done\" looks like:** <one sentence>. **Collect:** <what, if anything>. If machines are down, <a paper-friendly task>.\n"
                      % (name, slot, codes, ref_line))
            self.emit(name + "_MARKING.md", "# %s: Marking Notes (teacher only)\n\n**Marks:** /10 completion scale. Aesthetics never marked.\n\n"
                      "## Fast check (in order)\n\n1. <check>\n\n## Common deductions (7 to 9 band)\n\n- <deduction>\n\n"
                      "## The 4 to 6 band\n\n<what a substantial attempt looks like>\n\n## Watch for\n\n- <pattern>\n" % name)

    def write_ref(self):
        codes = []
        for t in self.teach:
            codes += t["codes"]
        for dv in self.deliverables:
            codes += dv["codes"]
        codes = self.sort(codes) or self.week_codes
        self.codes_report.append((self.ref_name(), codes, "union of the lesson and deliverable codes" if self.sort(codes) else "week_plan specific"))
        head = "# Reference: %s\n\n**Expectations:** %s · **Course:** %s\n\n" % (spaced(self.ref["token"]), ", ".join(codes) or "<codes>", self.cfg.get("code"))
        tpl = self.template("Reference_Sheet_Template.md")
        m = re.search(r"^<One page", tpl, re.M)
        self.emit(self.ref_name(), head + (tpl[m.start():] if m else self.body_after_header(tpl)))

    def write_plan(self):
        plan = copy.deepcopy(weekplan.template())
        meta = plan["metadata"]
        meta.update({"course_code": self.cfg.get("code", ""), "course_name": self.cfg.get("title", ""),
                     "grade": self.cfg.get("grade", 0), "pathway": self.cfg.get("type", ""),
                     "teacher": self.cfg.get("teacher") or meta.get("teacher"), "unit": self.unit,
                     "unit_name": self.unit_name, "week": self.week, "week_title": self.w.title, "slot_prefix": self.key})
        subject = (self.cur.subject if self.cur else "") or self.cfg.get("department", "")
        cats = list(CATEGORIES)
        cats[1] = curriculum.thinking_name(subject)
        plan["achievement_categories"] = cats
        overall = []
        for c in self.week_codes:
            o = c.split(".")[0]
            if o not in overall:
                overall.append(o)
        plan["curriculum_expectations"] = {"overall": overall, "specific": list(self.week_codes)}
        proto = plan["daily_lessons"][0]
        days = []
        for d in self.w.days:
            e = copy.deepcopy(proto)
            dt = day_type(d["type"]) or d["type"]
            e.update({"day": d["day"], "slot": d["slot"], "date": "{{D%d_DATE}}" % d["day"], "day_type": dt,
                      "sub_ready": dt in weekplan.SUB_READY_TYPES, "title": re.sub(r"\*\*", "", d["topic"]).strip()})
            days.append(e)
        plan["daily_lessons"] = days
        head = ("# ============================================================\n"
                "# %s Weekly Lesson Plan, %s %s\n"
                "# Shared schema: Standards/templates/Weekly_Plan_Schema.yaml. Dates are\n"
                "# rehydration placeholders. Do not fill in master.\n"
                "# ============================================================\n\n" % (self.cfg.get("code"), self.key, self.w.title))
        text = head + dump_plan(plan)
        self.emit("week_plan.yaml", text)

    # -- run
    def run(self):
        self.load()
        self.plan_week()
        only = self.only
        if only and re.fullmatch(r"D\d+", only):
            picked = [t for t in self.teach if t["n"] == int(only[1:])]
            if not picked:
                self.unresolved.append("--only %s: not a teach day this week" % only)
            for t in picked:
                self.write_lesson(t)
        else:
            if only in (None, "plan"):
                self.write_plan()
            if only is None:
                for t in self.teach:
                    self.write_lesson(t)
                for lab in self.labs:
                    self.write_lab(lab)
            if only in (None, "deliverable"):
                for dv in self.deliverables:
                    self.write_deliverable(dv)
            if only in (None, "ref") and self.ref:
                self.write_ref()
        for t in self.teach if course.switch(self.cfg, "decks") else []:
            if only and only != "D%d" % t["n"]:
                continue
            deck = "D%d_Slides_%s.html" % (t["n"], t["token"])
            if deck in self.existing:
                self.decks.append("%s exists" % deck)
            else:
                self.decks.append("gla deck %s --from <slides fragment> (write the fragment with <!-- auto: title --> and <!-- auto: goals --> first)" % os.path.join(self.dir, deck))
        self.report()

    def report(self):
        s = self.say
        s("%s %s (%s) %s" % (self.cfg.get("code"), self.key, self.w.title, "[dry run]" if self.dry else ""))
        s("folder:  %s%s" % (os.path.relpath(self.dir, self.root), "" if os.path.isdir(self.dir) else " (new)"))
        s("rhythm:  %s, from %s%s" % (self.rhythm, self.rhythm_src, "; assessment week" if self.assess_week else ""))
        for t in self.teach:
            s("topic:   D%d %s (%s)" % (t["n"], t["token"], t["token_src"]))
        for dv in self.deliverables:
            s("ship:    %s_%s + _%s (%s)%s" % (dv["kind"], dv["token"], dv["companion"], dv["src"],
                                             "; _KEY by default, use _MARKING for an open-response exercise" if dv["companion"] == "KEY" else ""))
        if self.ref:
            s("ref:     %s (%s)" % (self.ref_name(), self.ref["src"]))
        s("%s (%d):" % ("would create" if self.dry else "created", len(self.created)))
        for x in self.created:
            s("  + " + x)
        s("skipped, already exists (%d):" % len(self.skipped))
        for x in self.skipped:
            s("  = " + x)
        s("codes:")
        for what, codes, src in self.codes_report:
            s("  %-34s %-28s from %s" % (what, ", ".join(codes) or "(none)", src))
        if self.decks:
            s("decks (not created; the assembler builds them):")
            for x in self.decks:
                s("  " + x)
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
    ap.add_argument("week", help="slot block such as U2.W3")
    ap.add_argument("--root", help="course repo root (default: found from the cwd)")
    ap.add_argument("--part", "--only", dest="only", help="D<n> | deliverable | ref | plan (--only is the old name)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.only and not re.fullmatch(r"D\d+|deliverable|ref|plan", args.only):
        ap.error("--part takes D<n>, deliverable, ref or plan")
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root or not os.path.exists(os.path.join(root, "course.yaml")):
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    s = Scaffolder(root, args.week, only=args.only, dry_run=args.dry_run)
    try:
        s.run()
    except SystemExit as e:   # an overview the scaffolder cannot work from
        if isinstance(e.code, str):
            print(e.code)
            return 2
        raise
    return 1 if s.unresolved else 0   # unresolved items are listed in the report


if __name__ == "__main__":
    sys.exit(main())

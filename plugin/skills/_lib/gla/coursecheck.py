"""Checks for a course repo's master.

Covers the structural half of the bootstrap-gla-course and author-week
self-checks: course.yaml, week plans against the shared schema, teach-day
lesson and deck pairs, deliverable companions, artifact header codes against
the curriculum, the coverage map against the curriculum, unit weights across
the overviews, the Assessment Plan and the Course Outline, the gdocs
manifest, and the master's date-agnostic and naming rules. Teaching quality
(teacher-note depth, analogies, misconceptions) stays a human and model job.
"""
import glob
import os
import re

import yaml

from . import course, curriculum, mdtable, placeholders, slots, weekplan

CODE_RE = re.compile(r"\b[A-Z]\d+\.\d+\b")
HEADER_FIELD = re.compile(r"\*\*(\w[\w ()-]*):\*\*\s*([^·\n]*)")
SUB_BOX = re.compile(r"^> (?:### |\*\*)Running this class with a substitute(?:\*\*)?\s*$", re.M)
TEN_TABLE = re.compile(r"^\|\s*10\s*\|\s*Complete and correct\b", re.M)
DECK_CHIP = re.compile(r'<span class="code-chip">([^<]*)</span>')
DECK_SLOT = re.compile(r'class="slot-id[^"]*">([^<]*)<')
# An optional 3D deck sits beside a teach day's main deck, built from a YAML
# source of the same name (the course's tools/deck3d/build.py).
DECK3D = "_3D.html"


def deck3d_source(deck):
    """The parsed YAML source of a 3D deck, or None when there is none."""
    path = deck[:-len(".html")] + ".yaml"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None
WEIGHT_LINE = re.compile(r"\*\*Weight:\*\*\s*(\d+(?:\.\d+)?)%")
ISO_DATE = re.compile(r"\b20\d\d-[01]\d-[0-3]\d\b")
LONG_DATE = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
                       r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.? \d{1,2}(?:, 20\d\d)?\b")
# A month named as a time ("by January", "the September demo", "you-of-September").
# May is left out: it is far more often the verb.
MONTH_PHRASE = re.compile(r"\b(?:by|in|until|before|after|since|from|through|during|of|this|next|last|the)[ -]"
                          r"(?:January|February|March|April|June|July|August|September|October|November|December)\b")
# The leading verb of an expectation that asks students to do something with code or a
# product. Such an expectation needs a submitted artifact of that kind, so a coverage
# row that names only a test or the exam gets a warning.
DOING_VERB = re.compile(r"^\s*(?:apply|build|code|create|design|develop|implement|modify|produce|program|use|write)\b", re.I)
PAPER = re.compile(r"\b(?:tests?|exam)\b", re.I)
SUBMITTED = re.compile(r"assignment|brief|ship|exercise|\bEX_|\bCP\b|project|portfolio|submission|design doc", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF]|\uFE0F")  # pictographic emoji; check marks and arrows are fine
BAD_NAME = re.compile(r"(_v\d+|_final|_enhanced|[ _-]copy)(\.|_|$)", re.I)
STATUSES = ("planned", "built", "verified")
EM_ENTITY = re.compile(r"&(?:mdash|#8212|#x2014);", re.I)


RANGE_RE = re.compile(r"\b([A-Z]\d+)\.(\d+)\s*[–-]\s*(?:\1\.)?(\d+)\b")


def expand_codes(text):
    """Codes in text, with ranges like A4.1–A4.5 expanded."""
    out = set(CODE_RE.findall(text))
    for m in RANGE_RE.finditer(text):
        out.update("%s.%d" % (m.group(1), k) for k in range(int(m.group(2)), int(m.group(3)) + 1))
    return out


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def header(text, lines=14):
    """Header-block fields from the top of an artifact: {field: value}."""
    out = {}
    for line in text.splitlines()[:lines]:
        if line.startswith("**"):
            for k, v in HEADER_FIELD.findall(line):
                out.setdefault(k.strip(), v.strip())
    return out


def header_codes(text):
    for line in text.splitlines()[:14]:
        if line.startswith("**Expectations"):
            return set(CODE_RE.findall(line))
    return None


class CourseCheck:
    def __init__(self, root, report):
        self.root = os.path.abspath(root)
        self.master = os.path.join(self.root, "master")
        self.r = report
        self.cfg = {}
        self.cur = None
        self.known = set()

    def rel(self, *parts):
        return os.path.join(self.root, *parts)

    def files(self, pattern):
        return sorted(glob.glob(os.path.join(self.master, pattern), recursive=True))

    # ------------------------------------------------------------- config
    def check_config(self):
        self.cfg = course.check(self.root, self.r) or {}
        code = self.cfg.get("code")
        if not code:
            return
        try:
            self.cur = curriculum.load(code)
        except FileNotFoundError:
            self.r.error("curriculum-missing", self.rel("course.yaml"), "no curriculum data for %s in Teaching/Curriculum" % code)
            return
        if not self.cur.positional_reliable:
            self.r.warn("curriculum-positional", self.cur.source, "positional codes are unreliable here: " + "; ".join(self.cur.notes))
        self.known = set(self.cur.specific_codes())

    # --------------------------------------------------------- week plans
    def check_week_plans(self):
        plans = self.files("**/week_plan*.yaml")
        if not plans:
            self.r.error("weekplan-none", self.master, "no week_plan.yaml files under master/")
        for path in plans:
            try:
                plan = weekplan.load(path)
            except yaml.YAMLError as e:
                self.r.error("weekplan-yaml", path, "does not parse: %s" % e)
                continue
            weekplan.check(plan, path, self.r, master=True)
            self.check_week_folder(path, plan)
            for code in (plan.get("curriculum_expectations") or {}).get("specific") or []:
                if self.known and str(code) not in self.known:
                    self.r.error("code-unknown", path, "specific expectation %s is not in the %s curriculum" % (code, self.cfg.get("code")))

    def check_week_folder(self, path, plan):
        folder = os.path.dirname(path)
        own_folder = os.path.basename(path) == "week_plan.yaml"
        names = os.listdir(folder)
        theme = self.cfg.get("deck_theme", "glass")
        for d in plan.get("daily_lessons") or []:
            n, dt = d.get("day"), d.get("day_type")
            lessons = [x for x in names if re.match(r"^D%s_Lesson_(.+)\.md$" % n, x)]
            decks = [x for x in names if re.match(r"^D%s_Slides_(.+)\.html$" % n, x) and not x.endswith(DECK3D)]
            extras = [x for x in names if re.match(r"^D%s_Slides_(.+)%s$" % (n, re.escape(DECK3D)), x)]
            if dt == "teach" and own_folder:
                if len(lessons) != 1 or len(decks) != 1:
                    self.r.error("teach-pair", path, "D%s is a teach day but the folder has %d lesson(s) and %d deck(s)" % (n, len(lessons), len(decks)))
                    continue
                lt = lessons[0][len("D%s_Lesson_" % n):-3]
                st = decks[0][len("D%s_Slides_" % n):-5]
                if lt != st:
                    self.r.error("teach-pair", path, "D%s lesson topic %r and deck topic %r differ" % (n, lt, st))
                self.check_lesson_and_deck(os.path.join(folder, lessons[0]), os.path.join(folder, decks[0]), str(d.get("slot")), theme)
                for x in extras:
                    xt = x[len("D%s_Slides_" % n):-len(DECK3D)]
                    if xt != lt:
                        self.r.error("teach-pair", path, "D%s lesson topic %r and 3D deck topic %r differ" % (n, lt, xt))
                    self.check_deck3d(os.path.join(folder, x), str(d.get("slot")), header_codes(_read(os.path.join(folder, lessons[0]))) or set())
            elif dt == "teach":
                self.r.warn("teach-pair", path, "D%s is a teach day in a plan without its own folder; no lesson or deck to check" % n)
            elif own_folder and (lessons or decks or extras):
                self.r.error("teach-pair", path, "D%s is a %s day but has %s" % (n, dt, ", ".join(lessons + decks + extras)))

    def check_deck3d(self, deck, slot, lcodes):
        """An optional 3D deck beside the main one: its YAML source names the
        same slot and the lesson's expectations."""
        src = deck3d_source(deck)
        if src is None:
            self.r.warn("deck-3d", deck, "no %s beside the 3D deck" % os.path.basename(deck[:-len(".html")] + ".yaml"))
            return
        meta = src.get("deck") or {}
        if str(meta.get("slot", "")) != slot:
            self.r.error("deck-slot", deck, "its YAML says slot %s, week plan says %s" % (meta.get("slot"), slot))
        exps = {str(c).strip() for c in meta.get("expectations") or []}
        if lcodes and exps and exps != lcodes:
            self.r.warn("deck-codes", deck, "3D deck expectations %s differ from the lesson's %s" % (", ".join(sorted(exps)), ", ".join(sorted(lcodes))))

    def check_lesson_and_deck(self, lesson, deck, slot, theme):
        lt = _read(lesson)
        h = header(lt)
        hs = slots.find_all(h.get("Slot", ""))
        if hs and hs[0] != slot:
            self.r.error("header-slot", lesson, "header slot %s, week plan says %s" % (hs[0], slot))
        lcodes = header_codes(lt) or set()
        dt = _read(deck)
        chips = {c.strip() for c in DECK_CHIP.findall(dt)}
        if lcodes and chips and chips != lcodes:
            self.r.warn("deck-codes", deck, "deck chips %s differ from the lesson's %s" % (", ".join(sorted(chips)), ", ".join(sorted(lcodes))))
        if not chips and lcodes:
            self.r.error("deck-codes", deck, "no expectation chips on the goals slide")
        ds = DECK_SLOT.findall(dt)
        if ds and ds[0].strip() != slot:
            self.r.error("deck-slot", deck, "title slide says %s, week plan says %s" % (ds[0].strip(), slot))
        root_tag = re.search(r"<html\b[^>]*>", dt)
        has_theme = bool(root_tag and 'data-deck-theme="gla"' in root_tag.group(0))
        if theme == "gla" and not has_theme:
            self.r.warn("deck-theme", deck, "course deck_theme is gla but the deck does not set data-deck-theme=\"gla\"")
        if theme == "glass" and has_theme:
            self.r.warn("deck-theme", deck, "deck sets the gla theme but course deck_theme is glass")

    # ------------------------------------------------ feature availability
    def check_features(self):
        """The Style Guide's feature table is rendered from feature_availability.yaml."""
        from . import features
        if features.load(self.root) is None:
            if features.table_rows(_read(self.rel(features.STYLE)) if os.path.exists(self.rel(features.STYLE)) else ""):
                self.r.warn("features-yaml", self.rel(features.STYLE), "the feature table has no feature_availability.yaml; run `gla features extract`")
            return
        d = features.drift(self.root)
        if d:
            self.r.error("features-drift", self.rel(features.STYLE), d)

    # ------------------------------------------------------ deck guides
    def check_guides(self):
        """Every deck has its teacher guide (Slide_Deck_Instructions.md, Companion teacher
        guide); a guide states the deck's slide count and has a paragraph for every slide."""
        for deck in sorted(glob.glob(os.path.join(self.master, "**", "D*_Slides_*.html"), recursive=True)):
            guide = deck[:-len(".html")] + "_GUIDE.md"
            if not os.path.exists(guide):
                self.r.warn("deck-guide", deck, "no companion %s" % os.path.basename(guide))
                continue
            src = deck3d_source(deck) if deck.endswith(DECK3D) else None
            n = len(src.get("slides") or []) if src else len(re.findall(r'<section class="slide[ "]', _read(deck)))
            gt = _read(guide)
            m = re.search(r"\*\*Deck:\*\*\s*(\d+)\s+slides", gt)
            if not m:
                self.r.warn("guide-slides", guide, "no '**Deck:** N slides' line")
            elif int(m.group(1)) != n:
                self.r.warn("guide-slides", guide, "says %s slides; the deck has %d" % (m.group(1), n))
            covered = set()
            for a, b in re.findall(r"^\*\*Slides? (\d+)(?:\s*(?:-|–|to|and)\s*(\d+))?\b", gt, re.M):
                covered.update(range(int(a), int(b or a) + 1))
            missing = [k for k in range(1, n + 1) if k not in covered]
            if n and missing:
                self.r.warn("guide-slides", guide, "no **Slide n** paragraph for slide(s) %s" % ", ".join(map(str, missing)))

    # ---------------------------------------------------------- artifacts
    def check_artifacts(self):
        kinds = [("**/D*_Lesson_*.md", "lesson"), ("**/EX_*.md", "exercise"), ("**/BRIEF_*.md", "brief"),
                 ("**/REF_*.md", "reference"), ("**/Assessment/**/instructions.md", "assignment"),
                 ("**/Assessment/**/test.md", "test")]
        for pattern, kind in kinds:
            for path in self.files(pattern):
                name = os.path.basename(path)
                teacher = re.search(r"_(KEY|MARKING)\.md$", name)
                text = _read(path)
                codes = header_codes(text)
                h = header(text)
                is_intro = "INTRO" in h.get("Slot", "") or "Course_Introduction" in path
                student_assessment = kind in ("assignment", "test")
                if student_assessment:
                    if codes is not None:
                        self.r.warn("header-student-codes", path, "student-facing assessment header lists expectations; "
                                    "they belong in marking_notes.md or coverage_table.md")
                elif codes is None and not teacher and not is_intro:
                    self.r.error("header-codes", path, "no **Expectations:** line in the header block")
                for c in sorted(codes or ()):
                    if self.known and c not in self.known:
                        self.r.error("code-unknown", path, "header code %s is not in the %s curriculum" % (c, self.cfg.get("code")))
                if kind in ("exercise", "brief") and not teacher:
                    self.check_deliverable(path, text, h, kind)

    def check_deliverable(self, path, text, h, kind):
        stem = path[:-3]
        if kind == "brief":
            if os.path.exists(stem + "_KEY.md"):
                self.r.error("brief-key", path, "a studio brief never has a _KEY (divergent output); use _MARKING")
            if not os.path.exists(stem + "_MARKING.md"):
                self.r.error("companion", path, "no %s_MARKING.md" % os.path.basename(stem))
        elif not (os.path.exists(stem + "_KEY.md") or os.path.exists(stem + "_MARKING.md")):
            self.r.error("companion", path, "no _KEY or _MARKING companion")
        if not SUB_BOX.search(text):
            self.r.error("sub-box", path, "no 'Running this class with a substitute' box (Style Guide Core §8)")
        if h.get("Marks", "").startswith("/10") and not TEN_TABLE.search(text):
            self.r.error("ten-table", path, "marked /10 but the printed /10 table is missing")

    # ------------------------------------------------------- placeholders
    def check_placeholders(self):
        """Template placeholders left in the files the authoring skills write (week
        plans are checked in weekplan.check). Admin templates keep theirs."""
        seen = set()
        for pattern in ("**/D*_Lesson_*.md", "**/EX_*.md", "**/BRIEF_*.md", "**/REF_*.md",
                        "**/D*_Slides_*_GUIDE.md", "**/Assessment/**/*.md"):
            for path in self.files(pattern):
                if path in seen:
                    continue
                seen.add(path)
                found = placeholders.find(_read(path))
                if found:
                    self.r.error("placeholder", path, "unfilled template placeholder(s): %s" % ", ".join(found[:6])
                                 + (" and %d more" % (len(found) - 6) if len(found) > 6 else ""))

    # ------------------------------------------------------- coverage map
    def check_coverage_map(self):
        path = os.path.join(self.master, "01_Standards", "Curriculum_Coverage_Map.md")
        if not os.path.exists(path):
            self.r.error("coverage-missing", path, "no coverage map")
            return
        text = _read(path)
        texts = self.cur.specifics() if self.cur else {}
        mapped = {}
        for hdr, rows, _ in mdtable.tables(text):
            if not hdr or hdr[0].strip().lower() != "code":
                continue
            try:
                ti = next(k for k, h in enumerate(hdr) if h.lower().startswith(("taught", "anchor")))
                ai = mdtable.column(hdr, "assessed")
                si = mdtable.column(hdr, "status")
            except (StopIteration, KeyError):
                self.r.warn("coverage-table", path, "a Code table lacks Taught/Anchor, Assessed or Status columns")
                continue
            for line, c in rows:
                code = c[0].strip()
                if not CODE_RE.fullmatch(code):
                    continue
                mapped[code] = line
                if ti >= len(c) or c[ti].strip() in ("", "-", "—"):
                    self.r.error("coverage-taught", path, "%s has no taught or anchor slot" % code, line)
                if ai >= len(c) or c[ai].strip() in ("", "-", "—"):
                    self.r.error("coverage-assessed", path, "%s has no evaluated artifact" % code, line)
                elif DOING_VERB.match(texts.get(code, "")) and PAPER.search(c[ai]) and not SUBMITTED.search(c[ai]):
                    self.r.warn("coverage-doing", path, "%s asks students to %s, but only a test or the exam assesses it; "
                                "give it a submitted artifact of that kind" % (code, texts[code].split()[0].lower()), line)
                if si < len(c) and c[si].strip().lower() not in STATUSES:
                    self.r.warn("coverage-status", path, "%s status %r is not planned, built or verified" % (code, c[si].strip()), line)
        if self.known:
            for code in sorted(self.known - set(mapped)):
                self.r.error("coverage-missing-code", path, "%s is in the curriculum but not in the map" % code)
            for code in sorted(set(mapped) - self.known):
                self.r.error("coverage-extra-code", path, "%s is not a %s curriculum code" % (code, self.cfg.get("code")), mapped[code])

    # ------------------------------------------------------------ weights
    def check_weights(self):
        classroom = (self.cfg.get("assessment") or {}).get("classroom")
        overviews = {}
        for path in self.files("02_Units/*/unit_overview.md") + self.files("0*_*Module*/module_overview.md"):
            m = WEIGHT_LINE.search(_read(path))
            block = os.path.basename(os.path.dirname(path)).split("_")[0]
            if "Module" in path:
                block = "AI" if "AI" in path else block
            if m:
                overviews[block] = (float(m.group(1)), path)
            elif "unit_overview" in path:
                self.r.warn("weight-line", path, "no **Weight:** line")
        if classroom is not None and overviews:
            total = sum(w for w, _ in overviews.values())
            if abs(total - classroom) > 0.01:
                self.r.error("weight-overviews", self.rel("master", "02_Units"),
                             "unit overview weights total %g%% (%s); course.yaml classroom is %g%%"
                             % (total, ", ".join("%s %g" % (k, v[0]) for k, v in sorted(overviews.items())), classroom))
        plan = os.path.join(self.master, "00_Admin", "Assessment_Plan.md")
        plan_w = self.unit_weights(plan, ("unit", "weight"), r"^(U\d+|AI|R)\b")
        outline = os.path.join(self.master, "00_Admin", "Course_Outline.md")
        out_w = self.unit_weights(outline, ("unit", "title", "weight"), r"^(\d+|CP|R|AI)\b", prefix_digits="U")
        if plan_w is not None and classroom is not None:
            total = sum(v for k, v in plan_w.items() if k != "CP")
            if abs(total - classroom) > 0.01:
                self.r.error("weight-plan", plan, "classroom breakdown totals %g%%, course.yaml classroom is %g%%" % (total, classroom))
        for block, (w, path) in sorted(overviews.items()):
            if plan_w and block in plan_w and abs(plan_w[block] - w) > 0.01:
                self.r.error("weight-mismatch", path, "%s overview says %g%%, Assessment_Plan.md says %g%%" % (block, w, plan_w[block]))
        for block, w in sorted((out_w or {}).items()):
            if plan_w and block in plan_w and abs(plan_w[block] - w) > 0.01:
                self.r.error("weight-mismatch", outline, "%s outline says %g%%, Assessment_Plan.md says %g%%" % (block, w, plan_w[block]))

    def unit_weights(self, path, headers, id_re, prefix_digits=""):
        if not os.path.exists(path):
            self.r.error("admin-missing", path, "missing")
            return None
        t = mdtable.find_table(_read(path), *headers)
        if not t:
            self.r.warn("weight-table", path, "no %s table" % " | ".join(headers))
            return None
        hdr, rows, _ = t
        wi = mdtable.column(hdr, "weight")
        out = {}
        for _, c in rows:
            m = re.match(id_re, c[0].replace("*", "").strip())
            if not m or mdtable.is_total(c) or wi >= len(c):
                continue
            key = m.group(1)
            key = prefix_digits + key if key.isdigit() else key
            w = mdtable.percent(c[wi])
            if w is not None:
                out[key] = w
        return out

    # ------------------------------------------------------------ rubrics
    def check_rubrics(self):
        """Assignment rubrics: present, valid Google Classroom CSVs, Level 4 equal to the
        assignment's points, and the Markdown copy matching the CSV. Uses gc-rubric's checker."""
        import importlib.util
        from decimal import Decimal
        from . import paths
        spec = importlib.util.spec_from_file_location("build_rubric", os.path.join(paths.SKILLS, "gc-rubric", "scripts", "build_rubric.py"))
        br = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(br)
        for folder in self.files("**/Assessment/Assignment_*/"):
            for need in ("rubric.csv", "rubric.md"):
                if not os.path.exists(os.path.join(folder, need)):
                    self.r.error("rubric-missing", folder, "no %s" % need)
        for path in self.files("**/*rubric.csv"):
            faults = br.check_csv(path)
            fmt = [f for f in faults if not f.startswith("Level 4 points total")]
            if fmt:
                self.r.warn("rubric-format", path, "%d format fault(s), first: %s" % (len(fmt), fmt[0]))
            folder = os.path.dirname(path)
            inst = os.path.join(folder, "instructions.md")
            if os.path.basename(path) == "rubric.csv" and os.path.exists(inst):
                m = re.search(r"^\*\*(?:Marks|Points):\*\*\s*(\d+(?:\.\d+)?)", _read(inst), re.M)
                try:
                    crits = br.import_csv(path)
                except br.SpecError as e:
                    self.r.error("rubric-format", path, str(e))
                    continue
                total = sum(Decimal(str(c["points"])) for c in crits)
                if m and total != Decimal(m.group(1)):
                    self.r.error("rubric-total", path, "Level 4 points total %s; instructions.md says %s" % (total, m.group(1)))
            md = path[:-4] + ".md"
            if os.path.exists(md):
                try:
                    crits = br.import_csv(path)
                except br.SpecError:
                    continue
                mdt = _read(md)
                missing = [d for c in crits for d in c["levels"] if " ".join(d.split()) not in " ".join(mdt.split())]
                md_pts = [Decimal(x) for x in re.findall(r"^\| (?:Level [1-4]|Below Level 1|Not Yet Demonstrated) \| ([\d.]+) \|", mdt, re.M)]
                with open(path, encoding="utf-8-sig") as f:
                    import csv as _csv
                    rows = list(_csv.reader(f))[2:]
                csv_pts = [Decimal(x) for k in range(0, len(rows) - len(rows) % 5, 5) for x in rows[k + 2][1:6]]
                if missing:
                    self.r.warn("rubric-md", md, "%d descriptor(s) in the CSV are not in the Markdown copy" % len(missing))
                if md_pts and md_pts != csv_pts:
                    self.r.warn("rubric-md", md, "level points differ from the CSV (for example %s vs %s)"
                                % next(((a, b) for a, b in zip(md_pts, csv_pts) if a != b), (len(md_pts), len(csv_pts))))

    # ------------------------------------------------- assessment coverage
    def check_assessment_coverage(self):
        """The map's Assessed-in claims against each test's coverage_table.md and each
        assignment's criterion table in marking_notes.md, both ways."""
        from . import coverage
        claims = coverage.claims(self.root)
        mp = coverage.map_path(self.root)
        for folder in self.files("02_Units/*/Assessment/Test/"):
            u = os.path.basename(os.path.dirname(os.path.dirname(folder.rstrip("/")))).split("_")[0]
            ct_path = os.path.join(folder, "coverage_table.md")
            if not os.path.exists(ct_path):
                continue
            t = mdtable.find_table(_read(ct_path), "question", "marks")
            if not t:
                continue
            hdr, rows, _ = t
            ci = next((k for k, h in enumerate(hdr) if "code" in h.lower() or "expectation" in h.lower()), None)
            have = set()
            for _, c in rows:
                if ci is not None and ci < len(c) and re.match(r"\**[AB]\d", c[0].strip()):
                    have |= expand_codes(c[ci])
            self._compare(mp, ct_path, "%s test" % u, claims.get(("test", u), set()), have, "map-test")
        for folder in self.files("02_Units/*/Assessment/Assignment_*/"):
            u = os.path.basename(os.path.dirname(os.path.dirname(folder.rstrip("/")))).split("_")[0]
            mn = os.path.join(folder, "marking_notes.md")
            if not os.path.exists(mn):
                continue
            t = mdtable.find_table(_read(mn), "criterion", "code")
            if not t:
                self.r.error("assignment-coverage", mn, "no | Rubric criterion | Category | Expectation codes | table")
                continue
            hdr, rows, _ = t
            ci = next(k for k, h in enumerate(hdr) if "code" in h.lower())
            ri = next((k for k, h in enumerate(hdr) if "criterion" in h.lower()), 0)
            have, named = set(), []
            for line, c in rows:
                if mdtable.is_total(c) or ci >= len(c):
                    continue
                codes = expand_codes(c[ci])
                have |= codes
                named.append(c[ri].replace("*", "").strip().lower())
                for code in sorted(codes):
                    if self.known and code not in self.known:
                        self.r.error("code-unknown", mn, "%s is not a %s curriculum code" % (code, self.cfg.get("code")), line)
            rub = os.path.join(folder, "rubric.csv")
            if os.path.exists(rub):
                with open(rub, encoding="utf-8-sig") as f:
                    import csv as _csv
                    body = list(_csv.reader(f))[2:]
                titles = [body[k][0] for k in range(0, len(body) - len(body) % 5, 5)]
                focuses = [re.sub(r"^.*? - ", "", tt).strip().lower() for tt in titles]
                for fcs in focuses:
                    if not any(fcs in n or n in fcs for n in named if n):
                        self.r.error("assignment-coverage", mn, "rubric criterion %r has no row in the table" % fcs)
            self._compare(mp, mn, "%s assignment" % u, claims.get(("assignment", u), set()), have, "map-assignment")

    def _compare(self, map_file, record, what, claimed, have, code):
        for c in sorted(claimed - have):
            self.r.error(code, map_file, "the map says the %s assesses %s; %s does not" % (what, c, os.path.basename(record)))
        for c in sorted(have - claimed):
            self.r.error(code, record, "the %s assesses %s; the map's Assessed in cell does not say so" % (what, c))

    # -------------------------------------------------------------- tests
    def check_tests(self):
        """Every unit Test folder through author-assessment's check_test.py."""
        import importlib.util
        from . import paths
        spec = importlib.util.spec_from_file_location("check_test", os.path.join(paths.SKILLS, "author-assessment", "scripts", "check_test.py"))
        ct = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ct)
        for folder in self.files("02_Units/*/Assessment/Test/"):
            known, primary = ct.unit_context(folder)
            self.r.categories = {}
            ct.check(folder, self.r, known or self.known, primary)

    # ---------------------------------------------------------- manifest
    def check_manifest(self):
        name = self.cfg.get("gdocs_manifest") or "gdocs_manifest.yaml"
        path = self.rel(name)
        if not os.path.exists(path):
            return
        data = yaml.safe_load(_read(path)) or {}
        for rule in data.get("rules") or []:
            g = rule.get("glob", "")
            if not glob.glob(os.path.join(self.root, g), recursive=True):
                self.r.warn("manifest-glob", path, "glob %r matches no file" % g)

    # ---------------------------------------------- master hygiene and style
    def check_master_files(self, style=True):
        index = os.path.join(self.master, "MASTER_INDEX.md")
        index_text = _read(index) if os.path.exists(index) else ""
        if not index_text:
            self.r.error("index-missing", index, "no MASTER_INDEX.md")
        for unit in sorted(glob.glob(os.path.join(self.master, "02_Units", "*/"))):
            name = os.path.basename(unit.rstrip("/"))
            if index_text and name not in index_text:
                self.r.warn("index-unit", index, "unit folder %s is not named in the index" % name)
        for dirpath, dirs, files in os.walk(self.master):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in files + dirs:
                if n.startswith("."):
                    continue
                full = os.path.join(dirpath, n)
                if " " in n:
                    self.r.error("name-space", full, "file or folder name contains a space")
                if BAD_NAME.search(n):
                    self.r.error("name-version", full, "version suffix in a name; git is the history")
            if not style:
                continue
            for n in files:
                if not n.endswith((".md", ".yaml", ".html")):
                    continue
                full = os.path.join(dirpath, n)
                text = _read(full)
                if n.endswith(".html"):
                    text = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S)
                found = ISO_DATE.findall(text) + LONG_DATE.findall(text) + MONTH_PHRASE.findall(LONG_DATE.sub("", text))
                if found:
                    self.r.warn("master-date", full, "looks like a calendar date or month in a master: %s" % ", ".join(sorted(set(found))[:4]))
                em = text.count("—") + len(EM_ENTITY.findall(text))   # also &mdash;, &#8212;, &#x2014;
                if em:
                    self.r.warn("style-em-dash", full, "%d em dash(es)" % em)
                if EMOJI.search(text):
                    self.r.warn("style-emoji", full, "contains an emoji")


def check(root, report, style=True):
    c = CourseCheck(root, report)
    c.check_config()
    if not os.path.isdir(c.master):
        report.error("master-missing", c.master, "no master/ folder")
        return c
    c.check_week_plans()
    c.check_artifacts()
    c.check_placeholders()
    c.check_coverage_map()
    c.check_weights()
    c.check_rubrics()
    c.check_tests()
    c.check_assessment_coverage()
    c.check_manifest()
    c.check_guides()
    c.check_features()
    c.check_master_files(style=style)
    return c

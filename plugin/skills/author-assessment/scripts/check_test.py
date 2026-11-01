#!/usr/bin/env python3
"""Check a unit test folder (Assessment/Test/) against the house rules.

    python3 check_test.py TEST_FOLDER [--strict]

The parts are course.yaml's test_parts (A and B when it is absent). Part A,
when listed, is multiple choice; every other part is written items numbered
with its letter (B1, C1, ...).

Errors (exit 1):
  - test.md has exactly the course's parts, their marks add up to its
    **Marks:** header, and each part matches the marks its own heading states
  - every Part A question has four options A to D, and the key gives exactly one
    letter for it
  - the key has an entry for every written question (Part B and after)
  - coverage_table.md has one row per question with the question's marks, the
    rows total the test, categories are K/T/C/A, and every code is a real
    curriculum code
  - test_KEY.md, coverage_table.md and test.md agree on slot and marks
  - review_sheet.md and test_reference.md exist
  - test.md shows no answers: no **Answer:** line, no bolded or ticked option
Warnings:
  - a code the unit overview lists as primary is not on the test
  - a Part A question appears word for word in the review sheet
  - Part A falls outside about 40 to 50% of the marks (A and B tests only)
  - three or more Part A questions in a row share the same key letter
Also prints the marks per category.
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
from gla import course as coursemod  # noqa: E402
from gla import coverage, curriculum, findings, mdtable  # noqa: E402

CODE = re.compile(r"\b[A-Z]\d+\.\d+\b")
RANGE = re.compile(r"\b([A-Z]\d+)\.(\d+)\s*[–-]\s*(?:\1\.)?(\d+)\b")
MARKS_HDR = re.compile(r"^\*\*(?:Marks|Points):\*\*\s*(\d+(?:\.\d+)?)", re.M)
SLOT_HDR = re.compile(r"^\*\*Slot:\*\*\s*([A-Z][\w.]*\.D\d+)", re.M)
PART_HEAD = re.compile(r"^## Part ([A-Z])\b[^\n]*?(?:\((\d+(?:\.\d+)?) marks?)?", re.M)
A_QUESTION = re.compile(r"^(\d+)\.\s+\S", re.M)
OPTION = re.compile(r"^\s+[-*]\s+([A-D])\.\s", re.M)
# Part B items: "**B1.** (3 marks)", "**B1. Tracing (5 marks)**", "### B1. Output tracing (3 marks: ...)",
# "21. (5 marks)" or "21. (5)" (questions numbered on from Part A).
# Answers that belong in test_KEY.md only (author-assessment's hard rules).
SHOWN_ANSWER = re.compile(r"^\s*(?:[-*]\s+)?\**(?:Answer|Correct answer|Solution)s?\**\s*:"
                          r"|^\s+[-*]\s+(?:\*\*[A-D]\.|[A-D]\.\s+\*\*[^*\n]+\*\*\s*$)"
                          r"|^\s+[-*]\s+[A-D]\..*(?:\u2713|\u2714|\(correct\))", re.M | re.I)
# Every part after A is written like Part B, with its own letter (C1, D1, ...).
# Part A, when the course's test_parts has it, is the multiple-choice part.
ITEM = r"^(?:\*\*|### )%s(\d+)\.\**[^\n(]*?\((\d+(?:\.\d+)?)\s*(?:marks?)?\s*[,:;)]|^(\d+)\.\s*\((\d+(?:\.\d+)?)\s*(?:marks?)?\)"
B_ITEM = re.compile(ITEM % "B", re.M)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def expand(text):
    """Codes in text, with ranges like A4.1–A4.5 expanded."""
    out = set(CODE.findall(text))
    for m in RANGE.finditer(text):
        out.update("%s.%d" % (m.group(1), k) for k in range(int(m.group(2)), int(m.group(3)) + 1))
    return out


def sections(text):
    """{'A': text of Part A, 'B': text of Part B} (up to the next level-2 heading or the companion list)."""
    out, heads = {}, {}
    for m in PART_HEAD.finditer(text):
        start = m.end()
        nxt = re.search(r"^## (?!#)|^### Companion|^---\s*$", text[start:], re.M)
        out[m.group(1)] = text[start:start + nxt.start()] if nxt else text[start:]
        heads[m.group(1)] = float(m.group(2)) if m.group(2) else None
    return out, heads


def part_a(sec):
    """[(number, options)] for each Part A question."""
    qs = list(A_QUESTION.finditer(sec))
    out = []
    for k, m in enumerate(qs):
        body = sec[m.start():qs[k + 1].start() if k + 1 < len(qs) else len(sec)]
        out.append((int(m.group(1)), OPTION.findall(body), body))
    return out


def part_b(sec, letter="B"):
    """[(id, marks)]: id 'B1' for **B1.** items, 'B21' for '21. (5 marks)' items
    (another written part uses its own letter: C1, C21)."""
    out = []
    for m in re.finditer(ITEM % letter, sec, re.M):
        num = m.group(1) or m.group(3)
        marks = m.group(2) or m.group(4)
        out.append(("%s%s" % (letter, num), float(marks)))
    return out


def course_parts(folder):
    """The test's part letters from the course's course.yaml (test_parts), default A and B."""
    root = coursemod.find_root(folder)
    try:
        cfg = coursemod.load(root) if root else {}
    except Exception:  # noqa: BLE001  a broken course.yaml is check_course's finding
        cfg = {}
    return list(coursemod.switch(cfg, "test_parts"))


def key_answers(key):
    """{question number: [letters]} from a table (| 1 | B |) or inline (1. **B**)."""
    ans = {}
    for line in key.splitlines():
        if line.lstrip().startswith("|"):
            cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
            for k in range(len(cells) - 1):      # | 1 | A | 7 | D | 13 | B | holds several pairs
                if cells[k].isdigit() and re.fullmatch(r"[A-D]", cells[k + 1]):
                    ans.setdefault(int(cells[k]), []).append(cells[k + 1])
    for m in re.finditer(r"(?:^|·)\s*(\d+)\.\s*\*\*([A-D])\*\*", key, re.M):
        ans.setdefault(int(m.group(1)), []).append(m.group(2))
    return ans


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", t)).strip().lower()


def check(folder, report, known=None, primary=None, parts=None):
    """Add findings for one Test folder. known: the course's curriculum codes;
    primary: the unit's primary codes from unit_overview; parts: the test's part
    letters (course.yaml test_parts when None)."""
    parts = parts or course_parts(folder)
    written = [x for x in parts if x != "A"]
    paths = {n: os.path.join(folder, n) for n in ("test.md", "test_KEY.md", "coverage_table.md", "review_sheet.md", "test_reference.md")}
    for n, p in paths.items():
        if not os.path.exists(p):
            report.error("test-missing", folder, "no %s" % n)
    if not os.path.exists(paths["test.md"]):
        return None
    test = read(paths["test.md"])
    tp = paths["test.md"]
    m = MARKS_HDR.search(test)
    total = float(m.group(1)) if m else None
    if total is None:
        report.error("test-header", tp, "no **Marks:** line")
    secs, heads = sections(test)
    missing = [x for x in parts if x not in secs]
    if missing:
        report.error("test-structure", tp, "needs %s (course.yaml test_parts: %s); missing %s" % (
            ", ".join("'## Part %s'" % x for x in parts), ", ".join(parts), ", ".join(missing)))
        return None
    for x in sorted(set(secs) - set(parts)):
        report.error("test-structure", tp, "Part %s is not in course.yaml test_parts (%s)" % (x, ", ".join(parts)))
    qa = part_a(secs["A"]) if "A" in parts else []
    qparts = {x: part_b(secs[x], x) for x in written}
    qb = [q for x in written for q in qparts[x]]
    if "A" in parts and not qa:
        report.error("test-structure", tp, "Part A has no numbered questions")
    for x in written:
        if not qparts[x]:
            report.error("test-structure", tp, "Part %s has no questions with marks (\"**%s1.** (3 marks)\" or \"21. (5 marks)\")" % (x, x))
    nums = [n for n, _, _ in qa]
    if nums != list(range(nums[0], nums[0] + len(nums))) if nums else False:
        report.error("test-structure", tp, "Part A questions are not numbered consecutively: %s" % nums)
    for n, opts, _ in qa:
        if opts != ["A", "B", "C", "D"]:
            report.error("test-options", tp, "Part A question %d has options %s, not A to D" % (n, "".join(opts) or "none"))
    for m in SHOWN_ANSWER.finditer(test):
        line = test.count("\n", 0, m.start()) + 1
        report.error("test-answer", tp, "the student paper shows an answer: %s" % m.group(0).strip()[:60], line)
    a_marks, b_marks = float(len(qa)), sum(mk for _, mk in qb)
    marks = dict([("A", a_marks)] if "A" in parts else [])
    marks.update({x: sum(mk for _, mk in qparts[x]) for x in written})
    if "A" in parts and heads.get("A") is not None and heads["A"] != a_marks:
        report.error("test-marks", tp, "Part A heading says %g marks; it has %d one-mark questions" % (heads["A"], len(qa)))
    for x in written:
        if heads.get(x) is not None and abs(heads[x] - marks[x]) > 0.01:
            report.error("test-marks", tp, "Part %s heading says %g marks; its questions total %g" % (x, heads[x], marks[x]))
    if total is not None and abs(sum(marks.values()) - total) > 0.01:
        report.error("test-marks", tp, "%s = %g, but the header says %g" % (
            " + ".join("Part %s (%g)" % (x, marks[x]) for x in parts), sum(marks.values()), total))
    if total and parts == ["A", "B"] and not 0.35 <= a_marks / total <= 0.55:
        report.warn("test-balance", tp, "Part A is %d%% of the marks (the template says about 40 to 50%%)" % round(100 * a_marks / total))

    if os.path.exists(paths["test_KEY.md"]):
        key, kp = read(paths["test_KEY.md"]), paths["test_KEY.md"]
        ans = key_answers(key)
        for n, _, _ in qa:
            got = ans.get(n, [])
            if len(set(got)) != 1:
                report.error("key-answer", kp, "Part A question %d: key gives %s" % (n, ", ".join(sorted(set(got))) or "no answer"))
        letters = [(n, ans.get(n, [None])[0]) for n, _, _ in qa]
        k = 0
        while k < len(letters):
            j = k
            while j + 1 < len(letters) and letters[j + 1][1] and letters[j + 1][1] == letters[k][1]:
                j += 1
            if letters[k][1] and j - k + 1 >= 3:
                report.warn("key-run", kp, "Part A questions %d to %d all have key %s" % (letters[k][0], letters[j][0], letters[k][1]))
            k = j + 1
        heads_text = "\n".join(l for l in key.splitlines() if l.startswith(("#", "**")))
        for qid, _ in qb:
            n = qid[1:]
            if not re.search(r"\b[%sQ]%s\b|^(?:#+|\*\*)\s*%s[.:)]" % (qid[0], re.escape(n), re.escape(n)), heads_text, re.M):
                report.error("key-missing", kp, "no key entry for %s" % qid)
        km = MARKS_HDR.search(key)
        if km and total is not None and float(km.group(1)) != total:
            report.error("test-header", kp, "key says %s marks, test says %g" % (km.group(1), total))

    covered = set()
    if os.path.exists(paths["coverage_table.md"]):
        cov, cp = read(paths["coverage_table.md"]), paths["coverage_table.md"]
        t = mdtable.find_table(cov, "question", "marks")
        if not t:
            report.error("coverage-table", cp, "no | Question | ... | Marks | table")
        else:
            hdr, rows, _ = t
            qi, mi = mdtable.column(hdr, "question"), mdtable.column(hdr, "marks")
            ci = next((k for k, h in enumerate(hdr) if "code" in h.lower() or "expectation" in h.lower()), None)
            gi = next((k for k, h in enumerate(hdr) if "categor" in h.lower()), None)
            want = {"A%d" % n: 1.0 for n, _, _ in qa}
            want.update(dict(qb))
            seen, total_rows, cats = {}, 0.0, {}
            for line, c in rows:
                if mdtable.is_total(c) or qi >= len(c):
                    continue
                qid = re.match(r"\**([%s]\d+)" % "".join(parts), c[qi].strip())   # B5a and B5b are parts of B5
                if not qid:
                    continue
                qid = qid.group(1)
                mk = mdtable.percent(c[mi]) if mi < len(c) else None
                seen[qid] = (seen.get(qid) or 0) + (mk or 0)
                total_rows += mk or 0

                if ci is not None and ci < len(c):
                    codes = expand(c[ci])
                    covered.update(codes)
                    for code in sorted(codes):
                        if known and code not in known:
                            report.error("coverage-code", cp, "%s: %s is not a curriculum code" % (qid, code), line)
                if gi is not None and gi < len(c):
                    letters = [x.strip() for x in re.split(r"[,/]", re.sub(r"\([^)]*\)", "", c[gi])) if x.strip()]
                    bad = [x for x in letters if x not in ("K", "T", "C", "A")]
                    if bad:
                        report.error("coverage-category", cp, "%s: category %s is not K, T, C or A" % (qid, ", ".join(bad)), line)
                    for x in letters:
                        if x in ("K", "T", "C", "A") and mk:
                            cats[x] = cats.get(x, 0) + mk / len(letters)
            for qid, mk in seen.items():
                if qid in want and abs(mk - want[qid]) > 0.01:
                    report.error("coverage-marks", cp, "%s is %g marks in the table, %g in the test" % (qid, mk, want[qid]))
            for qid in want:
                if qid not in seen:
                    report.error("coverage-row", cp, "no row for %s" % qid)
            for qid in seen:
                if qid not in want:
                    report.error("coverage-row", cp, "row %s matches no question in test.md" % qid)
            if total is not None and abs(total_rows - total) > 0.01:
                report.error("coverage-marks", cp, "rows total %g, the test is %g" % (total_rows, total))
            report.categories = cats
        cm = MARKS_HDR.search(cov)
        if cm and total is not None and float(cm.group(1)) != total:
            report.error("test-header", cp, "coverage table says %s marks, test says %g" % (cm.group(1), total))
        for other in ("test_KEY.md", "coverage_table.md"):
            if os.path.exists(paths[other]):
                a, b = SLOT_HDR.search(test), SLOT_HDR.search(read(paths[other]))
                if a and b and a.group(1) != b.group(1):
                    report.error("test-header", paths[other], "slot %s, test says %s" % (b.group(1), a.group(1)))
    if primary:
        missing = sorted(primary - covered)
        if missing:
            report.warn("coverage-primary", paths["coverage_table.md"], "unit primary codes that nothing assesses (not this test, the unit assignment, or the map): %s" % ", ".join(missing))
    if os.path.exists(paths["review_sheet.md"]):
        review = norm(read(paths["review_sheet.md"]))
        for n, _, body in qa:
            stem = norm(re.sub(r"^\d+\.\s*", "", body.strip().splitlines()[0]))
            if len(stem) >= 30 and stem in review:
                report.warn("review-copy", paths["review_sheet.md"], "Part A question %d appears word for word" % n)
    return {"a_marks": a_marks, "b_marks": b_marks, "marks": marks, "total": total}


def unit_context(folder):
    """(known curriculum codes, unit primary codes) for a Test folder inside a course repo."""
    root = coursemod.find_root(folder)
    known, primary = set(), set()
    if root:
        try:
            known = set(curriculum.load(coursemod.load(root)["code"]).specific_codes())
        except (KeyError, FileNotFoundError):
            pass
        ov = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(folder))), "unit_overview.md")
        if os.path.exists(ov):
            m = re.search(r"^\*\*Expectations \(primary\):\*\*(.*)$", read(ov), re.M)
            if m:
                primary = expand(m.group(1))
        primary -= assessed_elsewhere(root, os.path.dirname(os.path.abspath(folder)))
    return known, primary


def assessed_elsewhere(root, assessment_dir):
    """Codes evaluated outside this unit test: in the unit assignment's criterion table,
    or by an evaluation the map's Assessed in cell names outside this unit (another
    unit, the culminating project, the exam, an exercise or brief). A cell that names
    only this unit's test or assignment does not count; the map checks compare those."""
    out = set()
    for mn in sorted(glob.glob(os.path.join(assessment_dir, "Assignment_*", "marking_notes.md"))):
        t = mdtable.find_table(read(mn), "criterion", "code")
        if t:
            hdr, rows, _ = t
            ci = next(k for k, h in enumerate(hdr) if "code" in h.lower())
            for _, c in rows:
                if ci < len(c):
                    out |= expand(c[ci])
    unit = os.path.basename(os.path.dirname(assessment_dir)).split("_")[0]
    own = {os.path.basename(a) for a in glob.glob(os.path.join(assessment_dir, "Assignment_*"))}
    for code, cell in coverage.assessed_cells(root).items():
        if names_other(cell, unit, own):
            out.add(code)
    return out


OTHER_EVAL = re.compile(r"\b(?:CP|culminating|exam|EX_\w+|BRIEF_\w+|exercises?|briefs?|every)\b", re.I)


def names_other(cell, unit, own_assignments=()):
    """True when a map Assessed in cell names an evaluation outside unit's test and assignment."""
    if OTHER_EVAL.search(cell):
        return True
    if any(u != unit for u in re.findall(r"\bU\d+\b", cell)):
        return True
    if any("Unit %s" % n != "Unit %s" % unit[1:] for n in re.findall(r"\bUnit (\d+)\b", cell)):
        return True
    return any("Assignment_" + n not in own_assignments for n in re.findall(r"\bAssignment_(\w+)", cell))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    known, primary = unit_context(a.folder)
    root = coursemod.find_root(a.folder)
    report = findings.Report(root)
    report.categories = {}
    info = check(a.folder, report, known, primary)
    report.apply_allows()
    report.print(title="Test check: %s" % os.path.relpath(os.path.abspath(a.folder), root or "."))
    if info and report.categories:
        print("marks: %s; by category: %s" % (", ".join("Part %s %g" % kv for kv in info["marks"].items()),
              ", ".join("%s %g" % (k, round(v, 1)) for k, v in sorted(report.categories.items()))))
    return report.exit_code(a.strict)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Regression check for build_rubric.py; make_skill_bundle.py runs it before bundling.

Builds each worked example, compares every level's points with the expected
table, checks the CSV with --check, confirms the Markdown carries every
descriptor, and confirms --check catches planted faults. Prints OK or exits 1.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import build_rubric as br  # noqa: E402

LEVELS = ["You do it at Level 4.", "You do it at Level 3.", "You do it at Level 2.", "You do it at Level 1.", "You have not yet done it."]


def spec(name, total, typ, cats=None, points=None, course=None):
    cats = cats or [["ku"], ["thinking"], ["communication"], ["application"]]
    crits = []
    for k, c in enumerate(cats):
        crit = {"category": c if len(c) > 1 else c[0], "focus": "Focus %d" % (k + 1),
                "description": "What criterion %d assesses." % (k + 1), "levels": ["%s (%d)" % (x, k) for x in LEVELS]}
        if points:
            crit["points"] = points[k]
        crits.append(crit)
    s = {"assignment": name, "total": total, "type": typ, "criteria": crits}
    if course:
        s["course"] = course
    return s


# (spec, expected [L4, L3, L2, L1, BL1] per criterion), from references/rubric_format_guide.md
CASES = [
    (spec("Six Point Programming", 6, "programming"),
     [["1.5", "1.1", "0.9", "0.8", "0.2"], ["2", "1.5", "1.2", "1", "0.3"], ["1", "0.8", "0.6", "0.5", "0.1"], ["1.5", "1.1", "0.9", "0.8", "0.2"]]),
    (spec("Twenty Point Programming", 20, "programming"),
     [["5", "3.8", "3", "2.5", "0.6"], ["6", "4.5", "3.6", "3", "0.8"], ["4", "3", "2.4", "2", "0.5"], ["5", "3.8", "3", "2.5", "0.6"]]),
    (spec("Ten Point Balanced", 10, "balanced"),
     [["2.5", "1.9", "1.5", "1.3", "0.3"]] * 4),
    # 27/27/26/20 of 10 is 2.7/2.7/2.6/2.0; rounding each to 0.5 gives 9.5, so the
    # largest remainder (a tie, broken toward K/U) takes the last half point.
    (spec("Ten Point Research", 10, "research"),
     [["3", "2.3", "1.8", "1.5", "0.4"], ["2.5", "1.9", "1.5", "1.3", "0.3"], ["2.5", "1.9", "1.5", "1.3", "0.3"], ["2", "1.5", "1.2", "1", "0.3"]]),
    (spec("Two Point Exercise", 2, "balanced", cats=[["ku", "thinking"], ["communication", "application"]], points=[1, 1]),
     [["1", "0.8", "0.6", "0.5", "0.1"]] * 2),
]


def main():
    failures = []
    tmp = tempfile.mkdtemp(prefix="gc_rubric_verify_")
    for s, expected in CASES:
        csv_path, md_path, crits, _ = br.build(s, tmp)
        got = [br.level_points(c["points"]) for c in crits]
        if got != expected:
            failures.append("%s: points %s, expected %s" % (s["assignment"], got, expected))
        if br.check_csv(csv_path, s["total"]):
            failures.append("%s: CSV check failed: %s" % (s["assignment"], br.check_csv(csv_path, s["total"])))
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        for c in crits:
            for d in c["levels"]:
                if d not in md:
                    failures.append("%s: Markdown is missing a descriptor" % s["assignment"])
                    break
        with open(csv_path, encoding="utf-8") as f:
            rows = f.read().split("\n")
        if len(rows) != 2 + 5 * len(crits):
            failures.append("%s: %d rows" % (s["assignment"], len(rows)))
    # Second category naming.
    _, md_path, _, _ = br.build(spec("Science Lab", 10, "research", course="SBI4U"), tmp)
    with open(md_path, encoding="utf-8") as f:
        if "Thinking and Investigation - Focus 2" not in f.read():
            failures.append("SBI4U rubric does not name Thinking and Investigation")
    _, md_path, _, _ = br.build(spec("CS Lab", 10, "programming", course="ICS3U"), tmp)
    with open(md_path, encoding="utf-8") as f:
        if "Thinking and Investigation" in f.read():
            failures.append("ICS3U rubric uses the Science category name")
    # --check catches planted faults.
    good, _, _, _ = br.build(spec("Planted", 10, "balanced"), tmp)
    with open(good, encoding="utf-8") as f:
        text = f.read()
    bad = os.path.join(tmp, "bad.csv")
    for label, broken in [("CRLF", text.replace("\n", "\r\n")), ("trailing newline", text + "\n"),
                          ("level title", text.replace("Some Effectiveness (Level 2)", "Some Effectiveness")),
                          ("ratio", text.replace('"2.5","1.9"', '"2.5","2"', 1)),
                          ("columns", text.replace(',""\n', "\n", 1))]:
        with open(bad, "w", encoding="utf-8", newline="") as f:
            f.write(broken)
        if not br.check_csv(bad, 10):
            failures.append("--check missed a planted fault: %s" % label)
    # Two decimal places are a fault (the guide rounds to one).
    with open(bad, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace('"2.5","1.9"', '"2.5","1.88"', 1))
    if not br.check_csv(bad, 10):
        failures.append("--check missed two decimal places")
    # Round trip: a built CSV imports back to the same criteria.
    s0 = spec("Round Trip", 10, "programming", course="ICS3U")
    built, _, crits0, _ = br.build(s0, tmp)
    back = br.import_csv(built)
    if [(c["focus"], c["description"], c["levels"], c["points"]) for c in back] != \
       [(c["focus"], c["description"], c["levels"], float(c["points"])) for c in crits0]:
        failures.append("import_csv did not round-trip a built rubric")
    # Course mode: an assignment folder in a course repo.
    repo = os.path.join(tmp, "COURSE")
    folder = os.path.join(repo, "master", "02_Units", "U1_X", "Assessment", "Assignment_Demo")
    os.makedirs(folder)
    with open(os.path.join(repo, "course.yaml"), "w", encoding="utf-8") as f:
        f.write('code: SBI4U\ndepartment: Science\n')
    with open(os.path.join(folder, "instructions.md"), "w", encoding="utf-8") as f:
        f.write("# Assignment: Enzyme Lab\n\n**Slot:** handed out U1.W1.D1, due U1.W2.D3 (7 days) · **Type:** assignment\n"
                "**Expectations:** B1.1, B2.3\n**Marks:** 20 points (Google Classroom rubric) + up to 2 bonus\n")
    sk = br.from_assignment(folder)
    if (sk["assignment"], sk["total"], sk["course"], sk["house"]["slot"]) != ("Enzyme Lab", 20.0, "SBI4U", "handed out U1.W1.D1, due U1.W2.D3"):
        failures.append("from_assignment read the folder wrongly: %r" % {k: sk[k] for k in ("assignment", "total", "course", "house")})
    sk["criteria"] = spec("x", 20, "research")["criteria"]
    sk["type"] = "research"
    csv_path, md_path, _, _ = br.build(sk, folder, "rubric")
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    if not (os.path.basename(csv_path) == "rubric.csv" and "**Expectations:** B1.1, B2.3" in md and "Thinking and Investigation" in md):
        failures.append("course-mode build did not write the house rubric.csv and rubric.md")
    # Invalid specs are refused.
    for label, s in [("missing category", spec("X", 10, "balanced", cats=[["ku"], ["thinking"], ["communication"], ["ku"]])),
                     ("points sum", spec("X", 10, "balanced", cats=[["ku", "thinking"], ["communication", "application"]], points=[4, 4])),
                     ("half point", dict(spec("X", 10, "balanced"), total=10.25))]:
        try:
            br.load_spec(s)
            failures.append("spec not refused: %s" % label)
        except br.SpecError:
            pass
    if failures:
        print("\n".join(failures))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

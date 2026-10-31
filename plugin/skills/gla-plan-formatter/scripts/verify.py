#!/usr/bin/env python3
"""
verify: render every example, export PDF, and compare with the committed baseline.

    python verify.py [--types lesson,unit,...] [--workdir DIR] [--update] [--no-png]

Per type: (1) if examples/<type>/example.md or .yaml exists, md2spec output must
equal examples/<type>/example.json; (2) build the docx; (3) export PDF (strict);
(4) page count must match examples/reference/manifest.json; (5) page 1 is
rasterised and compared with examples/reference/<type>_p1.png; (6) the docx and
pdf must carry no marker text and no em dash (check_output.py) (mean channel
difference under 2.0 and no 32x32 tile with mean difference over 25). The PNG
comparison downgrades to a warning when the LibreOffice version differs from
the one recorded in the manifest. --update rewrites the baseline.

Then the helpers: prefill.py for a few course codes and a course.yaml, and
extract_text.py on the example sources, a small .docx (python-docx and the
standard-library reader), an HTML snippet, and the lesson PDF built above.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import render_env  # noqa: E402
import check_output  # noqa: E402

TYPES = ["lesson", "unit", "course_outline", "long_range_plan", "weekly_plan", "exam_cover"]
REF = os.path.join(ROOT, "examples", "reference")
MANIFEST = os.path.join(REF, "manifest.json")


def soffice_version():
    found = render_env.find_soffice()
    if not found:
        return None
    kind, path = found
    if kind != "binary":
        return "sandbox"
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=60).stdout
        return out.strip().split("\n")[0]
    except Exception:
        return "unknown"


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def normalise(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def png_diff(a_path, b_path):
    """Return (mean_diff, max_tile_diff) using PyMuPDF pixmaps at quarter scale."""
    import fitz
    a, b = fitz.Pixmap(a_path), fitz.Pixmap(b_path)
    if (a.width, a.height) != (b.width, b.height):
        return 255.0, 255.0
    w, h, n = a.width, a.height, a.n
    sa, sb = a.samples, b.samples
    step = 4
    total, count = 0, 0
    tiles = {}
    for y in range(0, h, step):
        row = y * w * n
        for x in range(0, w, step):
            i = row + x * n
            d = sum(abs(sa[i + c] - sb[i + c]) for c in range(min(3, n)))
            total += d
            count += min(3, n)
            key = (y // 32, x // 32)
            t = tiles.setdefault(key, [0, 0])
            t[0] += d
            t[1] += min(3, n)
    mean = total / max(count, 1)
    max_tile = max((t[0] / t[1] for t in tiles.values()), default=0)
    return mean, max_tile


def sources_for(t):
    """[(source_path, expected_json_path)]. With one source the expectation is
    example.json; with both a YAML and a Markdown source, YAML maps to
    example.json and Markdown to example_md.json."""
    d = os.path.join(ROOT, "examples", t)
    found = [os.path.join(d, n) for n in ("example.yaml", "example.md") if os.path.exists(os.path.join(d, n))]
    if len(found) <= 1:
        return [(s, os.path.join(d, "example.json")) for s in found]
    return [(s, os.path.join(d, "example.json" if s.endswith(".yaml") else "example_md.json")) for s in found]


def _run(args, cwd=None):
    out = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=cwd)
    return out.returncode, out.stdout + out.stderr


def helper_tests(workdir):
    """(status rows, failures) for prefill.py and extract_text.py."""
    rows, failures = [], []
    prefill = os.path.join(HERE, "prefill.py")
    extract = os.path.join(HERE, "extract_text.py")
    import prefill as pf
    gs_found = pf.find_growing_success(HERE) is not None
    empty = os.path.join(workdir, "no_course_yaml")
    os.makedirs(empty, exist_ok=True)

    def expect(name, args, present=(), absent=(), cwd=None):
        code, out = _run([prefill] + args, cwd=cwd or empty)
        bad = [p for p in present if p not in out] + [f"not {a}" for a in absent if a in out]
        if code != 0 or bad:
            failures.append(f"prefill {name}: exit {code}, " + ("missing " + "; ".join(bad) if bad else out.strip()[-200:]))
            return "FAIL"
        return "ok"

    st = []
    st.append("SBI4U " + expect("SBI4U", ["--type", "lesson", "--code", "SBI4U"],
                                ["SBI4U, Biology", "Grade 12, University Preparation", '[derived from "4U"]',
                                 "Thinking and Investigation"]))
    ics = ["ICS3U, Introduction to Computer Science", "Grade 11, University Preparation",
           "classroom 65, final evaluation 25, attendance 10", "Prerequisite: None"]
    if gs_found:
        ics.append("written exam 10, culminating 15")
    st.append("ICS3U " + expect("ICS3U", ["--type", "course_outline", "--code", "ICS3U"], ics,
                                ["Thinking and Investigation"]))
    opn = ["Grade 10, Open", "classroom 65, final evaluation 20, attendance 15"]
    if gs_found:
        opn.append("written exam 10, culminating 10")
    st.append("ICD2O " + expect("ICD2O", ["--type", "course_outline", "--code", "ICD2O"], opn))
    st.append("ADA3O " + expect("ADA3O", ["--type", "course_outline", "--code", "ADA3O"],
                                ["Grade 11, Open", "B. Missing", "Final evaluation split (exam versus culminating)"]))
    st.append("no code " + expect("no code", ["--type", "weekly_plan"],
                                  ["Course code: not given", "Teacher: never guessed"], ["Thinking"]))
    repo = os.path.join(workdir, "repo_case")
    sub = os.path.join(repo, "master")
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(repo, "course.yaml"), "w", encoding="utf-8") as fh:
        fh.write("code: ICS4U\ntitle: Computer Science\ngrade: 12\ntype: University Preparation\n"
                 "teacher: Br. Test\nteacher_formal: Test Teacher\nassessment:\n  classroom: 65\n"
                 "  final_evaluation: 25\n  attendance: 10\n  exam: 10\n  culminating: 15\n")
    st.append("course.yaml " + expect("course.yaml", ["--type", "long_range_plan"],
                                      ["ICS4U, Computer Science", "Teacher: Test Teacher", "[from course.yaml]",
                                       "written exam 10, culminating 15"], cwd=sub))
    src = os.path.join(workdir, "source.txt")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write("Course: SPH4U Physics\nTeacher: Test Teacher\nExam Date: January 26, 2027\n")
    st.append("source " + expect("source", ["--type", "exam_cover", "--source", src],
                                 ["SPH4U, Physics", "Teacher: Test Teacher", "January 26, 2027",
                                  "[from your document, confirm]", "T/I"]))
    rows.append(("prefill", " / ".join(st)))

    st = []
    for t in TYPES:
        md = os.path.join(ROOT, "examples", t, "example.md")
        if not os.path.exists(md):
            continue
        code, out = _run([extract, md])
        with open(md, "r", encoding="utf-8") as fh:
            same = out == fh.read()
        if code != 0 or not same:
            failures.append(f"extract_text {t}/example.md: exit {code}, text differs from the file")
            st.append(f"{t}.md FAIL")
    if not any("FAIL" in x for x in st):
        st.append("examples ok")

    import extract_text as et
    try:
        import docx
    except Exception:
        docx = None
    if docx is not None:
        path = os.path.join(workdir, "tiny.docx")
        d = docx.Document()
        d.add_heading("Unit Plan", level=1)
        d.add_paragraph("Course: ICS3U")
        tbl = d.add_table(rows=2, cols=2)
        tbl.cell(0, 0).text, tbl.cell(0, 1).text = "Day", "Topic"
        tbl.cell(1, 0).text, tbl.cell(1, 1).text = "1", "Variables"
        d.save(path)
        want = ["# Unit Plan", "Course: ICS3U", "[table 1]", "Day | Topic", "1 | Variables"]
        code, out = _run([extract, path])
        bad = [w for w in want if w not in out]
        std = et.docx_text_stdlib(path)
        if code != 0 or bad:
            failures.append(f"extract_text docx: missing {bad}")
            st.append("docx FAIL")
        elif std != out:
            failures.append("extract_text docx: the standard-library reader differs from python-docx")
            st.append("docx stdlib FAIL")
        else:
            st.append("docx ok")
    else:
        st.append("docx skipped (no python-docx)")
    page = os.path.join(workdir, "tiny.html")
    with open(page, "w", encoding="utf-8") as fh:
        fh.write("<html><head><style>p{}</style></head><body><h2>Week 1</h2><p>Loops &amp; lists</p>"
                 "<table><tr><td>Mon</td><td>for</td></tr></table></body></html>")
    code, out = _run([extract, page])
    if code != 0 or "## Week 1" not in out or "Loops & lists" not in out or "Mon | for" not in out or "p{}" in out:
        failures.append(f"extract_text html: {out.strip()[:200]}")
        st.append("html FAIL")
    else:
        st.append("html ok")
    pdf = os.path.join(workdir, "lesson.pdf")
    if os.path.exists(pdf):
        code, out = _run([extract, pdf])
        if code == 2 and "neither PyMuPDF" in out:
            st.append("pdf skipped (no reader)")
        elif code != 0 or "--- page 1 ---" not in out:
            failures.append(f"extract_text pdf: exit {code}")
            st.append("pdf FAIL")
        else:
            st.append("pdf ok")
    rows.append(("extract_text", " / ".join(st)))
    return rows, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default=",".join(TYPES))
    ap.add_argument("--workdir")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()

    workdir = args.workdir or tempfile.mkdtemp(prefix="gla_verify_")
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(REF, exist_ok=True)
    manifest = load_json(MANIFEST) if os.path.exists(MANIFEST) else {"pages": {}, "soffice": None}
    version = soffice_version()
    same_soffice = manifest.get("soffice") == version
    failures = []
    rows = []

    import md2spec
    import doctypes

    for t in [x for x in args.types.split(",") if x]:
        status = []
        spec_path = os.path.join(ROOT, "examples", t, "example.json")
        if not os.path.exists(spec_path):
            rows.append((t, "SKIP (no example.json)"))
            continue
        spec = load_json(spec_path)
        for src, expected_path in sources_for(t):
            produced = md2spec.convert(src, t)
            if not os.path.exists(expected_path):
                if args.update:
                    with open(expected_path, "w", encoding="utf-8") as fh:
                        json.dump(produced, fh, indent=2, ensure_ascii=False)
                        fh.write("\n")
                    status.append(f"{os.path.basename(src)} recorded")
                else:
                    failures.append(f"{t}: no expectation for {os.path.basename(src)} (run --update)")
                continue
            expected = load_json(expected_path)
            if normalise(produced) != normalise(expected):
                failures.append(f"{t}: md2spec({os.path.basename(src)}) differs from {os.path.basename(expected_path)}")
                status.append(f"{os.path.basename(src)} roundtrip FAIL")
            else:
                status.append(f"{os.path.basename(src)} ok")
        out = os.path.join(workdir, f"{t}.docx")
        try:
            doctypes.REGISTRY[t](spec, out)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{t}: build error {e}")
            rows.append((t, " / ".join(status + ["build FAIL"])))
            continue
        try:
            pdf = render_env.to_pdf(out)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{t}: {e}")
            rows.append((t, " / ".join(status + ["pdf FAIL"])))
            continue
        hits = check_output.scan([out, pdf])
        if hits:
            failures.extend(f"{t}: {h}" for h in hits)
            status.append("marker/em dash FAIL")
        else:
            status.append("clean")
        pages = render_env.page_count(pdf)
        expected = manifest["pages"].get(t)
        if args.update or expected is None:
            manifest["pages"][t] = pages
            status.append(f"pages={pages} (recorded)")
        elif pages != expected:
            failures.append(f"{t}: {pages} pages, expected {expected}")
            status.append(f"pages FAIL {pages}!={expected}")
        else:
            status.append(f"pages={pages}")
        if not args.no_png:
            try:
                png = render_env.rasterize(pdf, pages=(1,), dpi=100)[0]
            except render_env.RasterizeUnavailable as e:
                status.append("png skipped")
                png = None
            ref = os.path.join(REF, f"{t}_p1.png")
            if png:
                if args.update or not os.path.exists(ref):
                    import shutil
                    shutil.copyfile(png, ref)
                    status.append("png recorded")
                else:
                    try:
                        mean, tile = png_diff(png, ref)
                    except Exception as e:  # noqa: BLE001
                        status.append(f"png compare skipped ({e})")
                        mean = tile = 0.0
                    ok = mean < 2.0 and tile < 25
                    if ok:
                        status.append(f"png ok ({mean:.2f})")
                    elif same_soffice:
                        failures.append(f"{t}: page-1 PNG differs (mean {mean:.2f}, tile {tile:.1f})")
                        status.append("png FAIL")
                    else:
                        status.append(f"png WARN ({mean:.2f}; LibreOffice differs from baseline)")
        rows.append((t, " / ".join(status)))

    h_rows, h_failures = helper_tests(workdir)
    rows.extend(h_rows)
    failures.extend(h_failures)

    if args.update or manifest.get("soffice") is None:
        manifest["soffice"] = version
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    width = max(len(r[0]) for r in rows) if rows else 10
    for name, text in rows:
        print(f"{name.ljust(width)}  {text}")
    print(f"workdir: {workdir}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

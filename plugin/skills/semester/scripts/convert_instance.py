#!/usr/bin/env python3
"""convert_instance.py — batch-convert student-facing master docs into
Google-Docs-ready .docx files inside an instance's gdocs/ tree, driven by a
per-course gdocs_manifest.yaml. Needs PyYAML, like the calendar builder.

Usage:
    python3 convert_instance.py SEMESTER [--root REPO_ROOT] [--only SUBSTR]
                                [--manifest PATH]

    SEMESTER    instance folder name (must exist under <root>/instances/)
    --root      course repo root (default: current working directory)
    --only      only convert sources whose path contains SUBSTR
    --no-verify skip the check that every written .docx parses and opens
    --manifest  manifest path (default: the gdocs_manifest key in
                <root>/course.yaml, else <root>/gdocs_manifest.yaml)

Manifest format (a `rules:` list of flat key/value maps):

    rules:
      - glob: "master/02_Units/U*_*/W*_*/EX_*.md"
        base: "master/02_Units"
        dest: "{relparent}/{stem}.docx"
      - glob: "master/02_Units/U*_*/Assessment/Test/test.md"
        base: "master/02_Units"
        dest: "{unit}/Assessment/{uprefix}_Test.docx"
        strip_teacher_note: true
        doc_kind: test
      - glob: "master/03_Module/Short/**/EX_*.md"
        base: "master/03_Module/Short"
        dest: "Module/{relparent}/{stem}.docx"
        when_config_regex: "some_module:\\s*short"

Rule fields:
    glob                path glob relative to --root (required)
    base                reference point for {relparent}/{unit} (required)
    dest                output path template relative to gdocs/ (required)
    strip_teacher_note  strip the teacher-copy note (default false)
    doc_kind            document-type layout hint handed to the converter; the
                        only value defined is `test` (see md2docx.py)
    when_config_regex   apply only if instances/<SEM>/semester_config.yaml
                        matches this regex

Dest placeholders:
    {stem}        source filename stem
    {Stem}        Title_Cased stem (assignment_instructions -> Assignment_Instructions)
    {parentname}  immediate parent folder name
    {relparent}   source parent relative to base ("." collapses to nothing)
    {unit}        first path component under base
    {uprefix}     {unit} up to its first underscore (U1_Foo -> U1)

Teacher-only files are never converted regardless of manifest:
*_KEY.md, *_MARKING.md, marking_notes.md, rubric.md, rubric.csv.

Every run also writes gdocs/index.yaml, a flat "<source>": "<docx>" map
(merged on --only runs) that the calendar builder uses to attach docx
links to materials whose docx name differs from the source name.
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required (python3 -c 'import yaml' failed)")

sys.path.insert(0, str(Path(__file__).parent))
from md2docx import convert, format_date  # noqa: E402

INDEX_NAME = "index.yaml"   # gdocs/index.yaml: "<master source path>": "<docx path under gdocs/>"

TEACHER_ONLY_STEMS = ("marking_notes", "rubric")
TEACHER_ONLY_SUFFIXES = ("_KEY", "_MARKING")


def titlecase_name(stem):
    """assignment_instructions -> Assignment_Instructions"""
    return "_".join(w.capitalize() for w in stem.split("_"))


def parse_manifest(path):
    """Return the manifest's `rules:` list."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = data.get("rules")
    if not isinstance(rules, list) or not all(isinstance(r, dict) for r in rules):
        raise ValueError("%s: expected a `rules:` list of maps" % path)
    return rules


def is_teacher_only(path):
    if path.stem.endswith(TEACHER_ONLY_SUFFIXES):
        return True
    return any(path.stem == s or path.stem.startswith(s) for s in TEACHER_ONLY_STEMS)


def build_jobs(root, semester, rules, cfg_text):
    jobs, seen = [], set()
    for rule in rules:
        for field in ("glob", "base", "dest"):
            if field not in rule:
                raise ValueError("manifest rule missing %r: %r" % (field, rule))
        cond = rule.get("when_config_regex")
        if cond and not re.search(cond, cfg_text):
            continue
        base = root / rule["base"]
        for src in sorted(root.glob(rule["glob"])):
            if not src.is_file() or is_teacher_only(src) or src in seen:
                continue
            seen.add(src)
            try:
                rel = src.parent.relative_to(base)
            except ValueError:
                rel = Path(".")
            relparent = "" if str(rel) == "." else str(rel)
            unit = rel.parts[0] if rel.parts else ""
            subs = {
                "stem": src.stem,
                "Stem": titlecase_name(src.stem),
                "parentname": src.parent.name,
                "relparent": relparent,
                "unit": unit,
                "uprefix": unit.split("_")[0] if unit else "",
            }
            dest = rule["dest"].format(**subs)
            dest = re.sub(r"/{2,}", "/", dest).lstrip("/")
            jobs.append((src, Path(dest),
                         bool(rule.get("strip_teacher_note", False)),
                         rule.get("doc_kind") or None))
    return jobs


def load_slot_dates(instance):
    """Map slot ID -> formatted date from instances/<sem>/calendar.yaml, so the
    converter can replace U.W.D indicators with real dates."""
    cal = instance / "calendar.yaml"
    if not cal.exists():
        return {}
    days = (yaml.safe_load(cal.read_text(encoding="utf-8")) or {}).get("days") or []
    return {d["slot"]: format_date(str(d["date"])) for d in days if d.get("slot")}


def read_index(path):
    """Read gdocs/index.yaml (a flat "source": "dest" map written by this
    script) so scoped --only runs merge into the existing index instead of
    replacing it."""
    if not path.exists():
        return {}
    return {str(k): str(v) for k, v in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items()}


def write_index(path, index):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# master source -> docx under gdocs/ (written by convert_instance.py; read by the calendar builder)"]
    for src in sorted(index):
        lines.append("%s: %s" % (json.dumps(str(src)), json.dumps(str(index[src]))))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def course_manifest_name(root):
    """The manifest path course.yaml names (relative to the repo root), or the default."""
    cfg = root / "course.yaml"
    if cfg.exists():
        name = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("gdocs_manifest")
        if name:
            return str(name)
    return "gdocs_manifest.yaml"


def verify(paths):
    """[(path, reason)] for written .docx files whose XML does not parse or that a
    real reader cannot open (macOS textutil, when present)."""
    import shutil
    import subprocess
    import tempfile
    import xml.dom.minidom
    import zipfile
    reader = shutil.which("textutil")
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for p in paths:
            try:
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        if n.endswith((".xml", ".rels")):
                            xml.dom.minidom.parseString(z.read(n))
            except Exception as e:  # noqa: BLE001 (report any failure)
                bad.append((p, "XML: %s" % e))
                continue
            if reader and subprocess.run([reader, "-convert", "txt", str(p), "-output", os.path.join(tmp, "x.txt")],
                                         capture_output=True).returncode:
                bad.append((p, "textutil cannot read it"))
    return bad


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    semester = args[0]
    root = Path.cwd()
    only = manifest_path = None
    for i, a in enumerate(argv):
        if a == "--root" and i + 1 < len(argv):
            root = Path(argv[i + 1])
        if a == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
        if a == "--manifest" and i + 1 < len(argv):
            manifest_path = Path(argv[i + 1])

    instance = root / "instances" / semester
    if not instance.is_dir():
        existing = ", ".join(p.name for p in (root / "instances").glob("*") if p.is_dir())
        print("ERROR: no instance at %s (existing: %s)" % (instance, existing or "none"))
        return 1

    if manifest_path is None:
        manifest_path = root / course_manifest_name(root)
    if not manifest_path.exists():
        print("ERROR: manifest not found at %s (set gdocs_manifest in "
              "course.yaml, or keep gdocs_manifest.yaml at the repo root)." % manifest_path)
        return 1

    cfg = instance / "semester_config.yaml"
    cfg_text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""

    jobs = build_jobs(root, semester, parse_manifest(manifest_path), cfg_text)
    if only:
        jobs = [j for j in jobs if only in str(j[0])]
    if not jobs:
        print("ERROR: nothing matched.")
        return 1

    out_root = instance / "gdocs"
    failures = 0
    slot_dates = load_slot_dates(instance)
    index = read_index(out_root / INDEX_NAME)
    for src, rel, strip, kind in jobs:
        try:
            convert(src, out_root / rel, strip_teacher_note=strip,
                    slot_dates=slot_dates, doc_kind=kind)
            print("  %s  ->  gdocs/%s" % (src.relative_to(root), rel))
            index[str(src.relative_to(root))] = rel
        except Exception as e:  # keep going; report at end
            failures += 1
            print("  FAILED %s: %s" % (src.relative_to(root), e))

    write_index(out_root / INDEX_NAME, index)
    if "--no-verify" not in argv:
        bad = verify([out_root / rel for _, rel, _, _ in jobs])
        for path, why in bad:
            print("  VERIFY FAILED %s: %s" % (path, why))
        failures += len(bad)
    print("\n%d converted, %d failed -> %s (index: gdocs/%s, %d entries)"
          % (len(jobs) - failures, failures, out_root, INDEX_NAME, len(index)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

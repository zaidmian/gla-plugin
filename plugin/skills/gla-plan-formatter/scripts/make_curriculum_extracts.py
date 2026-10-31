#!/usr/bin/env python3
"""
make_curriculum_extracts: compact Ontario curriculum pages, bundled so draft
mode can quote expectations inside the sandbox.

    python3 make_curriculum_extracts.py [--source DIR] [--courses ICD2O,ICS3U,...]

Source: every Teaching/Curriculum/docs/knowledge-graph/courses/*.md (default,
resolved relative to this skill's real location: ../../Curriculum). Output: one
file per subject in assets/curriculum/<subject>.md, each course under its own
H1, plus COURSES.txt, an index of "code<TAB>file<TAB>title". Files are packed
by subject because the claude.ai skill uploader allows at most 200 files per
bundle, and filenames are ASCII-only because it rejects anything else.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = SKILL_ROOT.parents[1] / "Curriculum" / "docs" / "knowledge-graph" / "courses"
OUT_DIR = SKILL_ROOT / "assets" / "curriculum"
INDEX = OUT_DIR / "COURSES.txt"

_LINK_RX = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_SUB_RX = re.compile(r"<sub>.*?</sub>\s*", flags=re.S)
_UNSAFE_RX = re.compile(r"[^A-Za-z0-9._-]+")
_SOFT_HYPHEN = "­"
META_KEYS = ("code", "subject", "grade", "course_type", "year_issued")


def safe_name(stem):
    """ASCII letters, digits, dot, underscore, hyphen; runs collapse to one hyphen."""
    stem = stem.replace("–", "-").replace("—", "-")
    return re.sub(r"-{2,}", "-", _UNSAFE_RX.sub("-", stem)).strip("-")


def extract(text):
    """Front matter dict and cleaned body (links flattened, navigation sections dropped)."""
    front, body = {}, text
    if text.startswith("---"):
        end = text.index("\n---", 3)
        for line in text[3:end].splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                front[k.strip()] = v.strip().strip('"')
        body = text[end + 4:]
    body = _SUB_RX.sub("", body)
    body = _LINK_RX.sub(r"\1", body)
    body = body.replace(_SOFT_HYPHEN, "")
    keep, skip = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().lower()
            skip = title.startswith(("where this course", "related", "pathway", "see also"))
        if not skip:
            keep.append(line.rstrip())
    body = "\n".join(keep).strip()
    if not body.startswith("# "):
        body = f"# {front.get('title', '')}\n\n{body}"
    meta = "  |  ".join(f"{k}: {front[k]}" for k in META_KEYS if front.get(k))
    head, _, rest = body.partition("\n")
    return front, f"{head}\n\n*{meta}*\n{rest}".rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--courses", help="comma-separated codes to include (default: every source file)")
    args = ap.parse_args()
    sources = sorted(Path(args.source).glob("*.md"))
    if args.courses:
        wanted = {safe_name(c.strip()).lower() for c in args.courses.split(",") if c.strip()}
        sources = [f for f in sources if safe_name(f.stem).lower() in wanted]
        missing = wanted - {safe_name(f.stem).lower() for f in sources}
        for m in sorted(missing):
            print(f"missing: {m}", file=sys.stderr)
    if not sources:
        ap.error(f"no course files under {args.source}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.md"):
        old.unlink()
    by_subject, index = defaultdict(list), []
    for f in sources:
        front, body = extract(f.read_text(encoding="utf-8"))
        subject = safe_name(front.get("subject") or "Other").replace("-", "_")
        by_subject[subject].append(body)
        index.append((safe_name(front.get("code") or f.stem), f"{subject}.md", front.get("title", "")))

    total = 0
    for subject, bodies in sorted(by_subject.items()):
        out = OUT_DIR / f"{subject}.md"
        text = f"<!-- Ontario curriculum extracts, subject: {subject.replace('_', ' ')}. One course per H1. -->\n\n"
        text += "\n\n---\n\n".join(bodies)
        out.write_text(text, encoding="utf-8")
        total += len(text.encode("utf-8"))
        print(f"{subject}.md: {len(bodies)} courses, {len(text.encode('utf-8'))//1024} KB")
    index.sort(key=lambda r: r[0].lower())
    INDEX.write_text("".join(f"{c}\t{f}\t{t}\n" for c, f, t in index), encoding="utf-8")
    print(f"{len(index)} courses in {len(by_subject)} files, {total//1024} KB total")


if __name__ == "__main__":
    main()

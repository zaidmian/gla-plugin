#!/usr/bin/env python3
"""
curriculum: look up Ontario curriculum expectations from the bundled extracts
without reading a whole subject file (the largest is 1.3 MB, which would fill
the context on its own).

    python3 curriculum.py --find SNC          list codes and titles matching a fragment
    python3 curriculum.py ICS3U               overview: description, strands, overall expectations
    python3 curriculum.py ICS3U --strand A    one strand in full (overall and specific expectations)
    python3 curriculum.py ICS3U --full        the whole course (prints a size line first)
    python3 curriculum.py ICS3U --strand A --raw   the extract as bundled, bullets unnumbered

Specific expectations print with their codes (A1.1, A1.2, ...) assigned by
position under each overall expectation, which is how the ministry numbers
them. Documents issued before 2020 carry no printed codes, so spot check
against the ministry PDF when a code matters. Codes are case-insensitive. Multi-code courses use the packed name in
COURSES.txt (for example LBACU-LDYCU); elementary documents use their slug
(mathematics-grade-4).
"""

import argparse
import re
import sys
from pathlib import Path

CUR = Path(__file__).resolve().parent.parent / "assets" / "curriculum"
INDEX = CUR / "COURSES.txt"
_STRAND_RX = re.compile(r"^### ([A-Z])\. (.+)$")
_OVERALL_RX = re.compile(r"^\*\*([A-Z]\d+)(?:\s[^*]*)?\*\*\s")   # **A1** text, or **A1 Title.** text
_BULLET_RX = re.compile(r"^- (.+)$")
_CODED_BULLET_RX = re.compile(r"^- [A-Z]\d+\.\d+\b")
_YEAR_RX = re.compile(r"year_issued: (\d{4})")
POSITION_NOTE = ("Codes are assigned by position within each overall expectation; "
                 "spot check against the ministry PDF.")


def index():
    rows = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(tuple(parts))
    return rows


def find(fragment):
    frag = fragment.lower()
    return [r for r in index() if frag in r[0].lower() or frag in r[2].lower()]


def course_text(code):
    hits = [r for r in index() if r[0].lower() == code.lower()]
    if not hits:
        near = find(code)[:8]
        hint = ("; did you mean " + ", ".join(r[0] for r in near) + "?") if near else ""
        sys.exit(f"no course '{code}' in the bundled curriculum{hint}")
    _, fname, title = hits[0]
    text = (CUR / fname).read_text(encoding="utf-8")
    parts = re.split(r"^(?=# )", text, flags=re.M)
    for part in parts:
        if part.startswith(f"# {title}\n"):
            return part.rstrip() + "\n"
    sys.exit(f"course '{code}' is indexed but its section was not found in {fname}")


def number_specifics(lines):
    """Prefix each specific-expectation bullet with its code (A1.1, A1.2, ...),
    counting from the overall expectation above it. Bullets that already start
    with a code are left alone."""
    out, code, n = [], None, 0
    for line in lines:
        m = _OVERALL_RX.match(line)
        if m:
            code, n = m.group(1), 0
            out.append(line)
            continue
        if _STRAND_RX.match(line):
            code, n = None, 0
        b = _BULLET_RX.match(line)
        if b and code and not _CODED_BULLET_RX.match(line):
            n += 1
            out.append(f"- {code}.{n} {b.group(1)}")
        else:
            out.append(line)
    return out


def position_note(text):
    """The caveat line for documents issued before 2020 (no printed codes)."""
    m = _YEAR_RX.search(text)
    if m and int(m.group(1)) < 2020:
        return "\n" + POSITION_NOTE + "\n"
    return ""


def specific_expectations(code):
    """{'A1.1': wording, ...} for a course, trailing ; or . removed."""
    out = {}
    for line in number_specifics(course_text(code).splitlines()):
        m = re.match(r"^- ([A-Z]\d+\.\d+) (.+)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().rstrip(";.").strip()
    return out


def strand_names(code):
    """{'A': 'Programming Concepts And Skills', ...} as the extract prints them."""
    return {m.group(1): m.group(2).strip()
            for m in map(_STRAND_RX.match, course_text(code).splitlines()) if m}


def overview(text):
    """Everything above the strands, then per strand: heading, lead line, overall expectations."""
    out, in_strands, strand_open = [], False, False
    for line in text.splitlines():
        m = _STRAND_RX.match(line)
        if m:
            in_strands, strand_open = True, True
            out.append(f"\n{line}")
            continue
        if not in_strands:
            out.append(line)
        elif strand_open and _OVERALL_RX.match(line):
            out.append(line)
    out.append("\nSpecific expectations: run with --strand <letter>.")
    return "\n".join(out).strip() + "\n"


def strand(text, letter, raw=False):
    letter = letter.upper()
    lines, keep = text.splitlines(), []
    if not raw:
        lines = number_specifics(lines)
    on = False
    for line in lines:
        m = _STRAND_RX.match(line)
        if m:
            on = m.group(1) == letter
        if on:
            keep.append(line)
    if not keep:
        letters = [m.group(1) for m in map(_STRAND_RX.match, lines) if m]
        sys.exit(f"no strand {letter}; this course has strands {', '.join(letters) or 'none'}")
    return "\n".join(keep).strip() + "\n" + ("" if raw else position_note(text))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("code", nargs="?")
    ap.add_argument("--find", metavar="FRAGMENT")
    ap.add_argument("--strand", metavar="LETTER")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--raw", action="store_true", help="print bullets as bundled, without codes")
    a = ap.parse_args()
    if a.find:
        for code, fname, title in find(a.find):
            print(f"{code}\t{title}")
        return
    if not a.code:
        ap.error("give a course code, or --find FRAGMENT")
    text = course_text(a.code)
    if a.full:
        body = text if a.raw else "\n".join(number_specifics(text.splitlines())) + "\n" + position_note(text)
        print(f"[{len(body)//1024} KB, about {len(body)//4000}k tokens]")
        print(body)
    elif a.strand:
        print(strand(text, a.strand, raw=a.raw))
    else:
        print(overview(text))


if __name__ == "__main__":
    main()

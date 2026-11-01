"""Curriculum expectation codes in text: A1.2, and ranges such as A4.1–A4.5 or A4.1-5.

One home for the pattern the checks, the scaffolders and the coverage reader
share. RANGE expands only within one overall expectation and at most 20 codes
apart, so a stray "B1.2-9.0" is never read as a range.
"""
import re

CODE = re.compile(r"\b[A-Z]\d+\.\d+\b")
RANGE = re.compile(r"\b([A-Z])(\d+)\.(\d+)\s*[–-]\s*(?:([A-Z])(\d+)\.)?(\d+)\b")


def codes_in(text):
    """Codes mentioned in text, ranges expanded, in order of first mention, unique."""
    found = []
    for m in RANGE.finditer(text or ""):
        l1, o1, a, l2, o2, b = m.groups()
        if (l2 or l1) == l1 and (o2 or o1) == o1 and int(a) < int(b) <= int(a) + 20:
            found += ["%s%s.%d" % (l1, o1, k) for k in range(int(a), int(b) + 1)]
    found += CODE.findall(text or "")
    return list(dict.fromkeys(found))


def expand(text):
    """The set of codes in text, ranges expanded."""
    return set(codes_in(text))

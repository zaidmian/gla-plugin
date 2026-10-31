"""Slot IDs: INTRO.D1, U2.W3.D1, CP.W1.D5, AI.W1.D2, AI.S.D3, R.D1 (a flat review week).

A slot is a block, an optional week (W<n>, or S for a module's short form),
and a day D<n>. Slot IDs are permanent once a course is scaffolded.
"""
import re

SLOT_RE = re.compile(r"\b(?P<block>INTRO|U\d+|CP|R|[A-Z]{2,})(?:\.(?P<week>W\d+|S))?\.D(?P<day>\d+)\b")
_FULL = re.compile(r"^%s$" % SLOT_RE.pattern.replace(r"\b", ""))
WEEK_KEY_RE = re.compile(r"^(INTRO|U\d+|CP|R|[A-Z]{2,})(\.(W\d+|S))?$")


def is_slot(s):
    return bool(_FULL.match(s or ""))


def parse(s):
    """'U2.W3.D1' -> ('U2', 'W3', 1); raises ValueError on anything else."""
    m = _FULL.match(s or "")
    if not m:
        raise ValueError("not a slot ID: %r" % s)
    return m.group("block"), m.group("week"), int(m.group("day"))


def week_key(s):
    """'U2.W3.D1' -> 'U2.W3'; 'INTRO.D2' -> 'INTRO'."""
    block, week, _ = parse(s)
    return "%s.%s" % (block, week) if week else block


def find_all(text):
    """Every slot ID mentioned in a piece of text, in order."""
    return [m.group(0) for m in SLOT_RE.finditer(text or "")]

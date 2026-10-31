"""
Shared helpers for sources that live inside a GLA course repo (a course.yaml at
the root, master/ and instances/ beneath it). Used by the pipeline unit parser
and by the long range plan parser when its source sits in an instance folder.
"""

import os
import re

from gla_docx import PATHWAYS

_SEM_RX = re.compile(r"(\d{4}-\d{2})_S([12])")
_SEM_SHORT_RX = re.compile(r"_S([12])(?:\b|_)")
_PATHWAY_LONG = {
    "D": "Academic", "P": "Applied", "U": "University Preparation", "C": "College Preparation",
    "M": "University/College Preparation", "O": "Open", "W": "De-streamed",
    "E": "Workplace Preparation", "L": "Locally Developed",
}


def find_course_yaml(start, levels=8):
    """Walk up from a file or folder to the nearest course.yaml; None when absent."""
    here = os.path.abspath(start)
    if os.path.isfile(here):
        here = os.path.dirname(here)
    for _ in range(levels):
        cand = os.path.join(here, "course.yaml")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return None


def load_course_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        from mdparse import parse_simple_yaml
        return parse_simple_yaml(text) or {}


def semester_label(name):
    """'2026-27_S1' -> '2026-27 Semester 1'; a bare '_S1' still gives 'Semester 1'."""
    m = _SEM_RX.search(name or "")
    if m:
        return f"{m.group(1)} Semester {m.group(2)}"
    m = _SEM_SHORT_RX.search(name or "")
    if m:
        return f"Semester {m.group(1)}"
    return ""


def pathway_for_code(code, long=True):
    """'University Preparation' (or the badge form 'University Prep') from the code's fifth character."""
    code = (code or "").strip().upper()
    if len(code) < 5:
        return ""
    return (_PATHWAY_LONG if long else PATHWAYS).get(code[4], "")


def dedash(s):
    """House prose rule: no em dashes. ' — ' and '—' become ', '; a letter-en dash-letter
    join becomes a hyphen; whitespace collapses."""
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\s*—\s*", ", ", s)
    s = re.sub(r"(?<=[A-Za-z])–(?=[A-Za-z])", "-", s)
    return " ".join(s.split())

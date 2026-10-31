"""
The second achievement-chart category is named per subject.

Ontario gives three of the four categories the same name in every curriculum
document. The second one varies: Science (SNC, SBI, SCH, SPH, SVN) and Science
and Technology in Grades 1 to 8 call it "Thinking and Investigation", and every
other subject, Computer Studies included, calls it "Thinking".

Computer Studies is the one people get wrong, because it sits next to science
and because the ICD2O curriculum document itself contains a stray "Thinking and
Investigation" in its Descriptors paragraph, boilerplate copied from the Science
template and contradicted by the achievement chart on the facing page. Both
Computer Studies documents (2008 for ICS3U and ICS4U, 2023 for ICD2O) name the
category "Thinking". The rule lives in
Standards/assessment/Grading_Conventions.md, section "Naming the second
category".

The subject comes from the course code, resolved through the bundled
assets/curriculum/COURSES.txt index, so nothing new has to be authored in a
plan. A caller that already knows the subject (a course.yaml department, say)
can pass it instead. Anything unresolved falls back to "Thinking".
"""

import re

THINKING = "Thinking"
THINKING_INVESTIGATION = "Thinking and Investigation"

# Abbreviations as they appear on an exam cover's Categories table.
ABBREV = "T"
ABBREV_INVESTIGATION = "T/I"

# The curriculum extracts whose courses use the longer name.
_SCIENCE_FILES = {"Science.md", "Science_and_Technology.md"}
_SCIENCE_SUBJECTS = {"science", "scienceandtechnology"}

_index_cache = None


def _key(s):
    return re.sub(r"[^a-z]", "", str(s or "").lower())


def _code_to_file():
    """{course code -> curriculum extract filename} from the bundled index.

    Returns {} when the extracts are not present, which keeps a bare checkout
    and a trimmed bundle working: everything then falls back to "Thinking".
    """
    global _index_cache
    if _index_cache is None:
        try:
            import curriculum
            _index_cache = {code.strip().upper(): fname.strip()
                            for code, fname, _title in curriculum.index()}
        except Exception:
            _index_cache = {}
    return _index_cache


def is_science(code=None, subject=None):
    """True when this course's curriculum document says "Thinking and Investigation"."""
    if subject and _key(subject) in _SCIENCE_SUBJECTS:
        return True
    code = (code or "").strip().upper()
    if not code:
        return False
    return _code_to_file().get(code) in _SCIENCE_FILES


def thinking_name(code=None, subject=None):
    """The second category's name for this course."""
    return THINKING_INVESTIGATION if is_science(code, subject) else THINKING


def thinking_abbrev(code=None, subject=None):
    """The second category's abbreviation on an exam cover ("T/I" or "T")."""
    return ABBREV_INVESTIGATION if is_science(code, subject) else ABBREV


def names(base, code=None, subject=None):
    """`base` with its second entry renamed for this course.

    Each doctype keeps its own house spelling of the first category ("Knowledge
    & Understanding" in a lesson, "Knowledge / Understanding" in a unit plan),
    so only the second entry is substituted.
    """
    out = list(base)
    if len(out) > 1:
        out[1] = thinking_name(code, subject)
    return out

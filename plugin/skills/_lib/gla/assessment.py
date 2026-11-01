"""The 2026 Growing Success final-mark model as data.

Source: Standards/assessment/growing-success-summary.md (September 2026
requirements) and Standards/assessment/Grading_Conventions.md §Final
evaluation. Change it there first, then here.
"""
import re

# classroom / final evaluation / attendance, by grade band
BUCKETS = {"9-10": (65, 20, 15), "11-12": (65, 25, 10)}

# subject group -> (exam, culminating) per grade band
SPLITS = {
    "english_math_science": {"9-10": (20, 0), "11-12": (25, 0)},
    "arts_cs_hpe_tech":     {"9-10": (10, 10), "11-12": (10, 15)},
    "cws":                  {"9-10": (20, 0), "11-12": (15, 10)},   # Grade 9 Geography, Grade 10 History and Civics
    "business_social":      {"9-10": (10, 10), "11-12": (15, 10)},
    "languages":            {"9-10": (10, 10), "11-12": (10, 15)},
    "fnmi":                 {"9-10": (10, 10), "11-12": (10, 15)},
}

_GROUPS = {
    "english": "english_math_science", "mathematics": "english_math_science", "science": "english_math_science",
    "thearts": "arts_cs_hpe_tech", "arts": "arts_cs_hpe_tech", "computerstudies": "arts_cs_hpe_tech",
    "healthandphysicaleducation": "arts_cs_hpe_tech", "technologicaleducation": "arts_cs_hpe_tech",
    "canadianandworldstudies": "cws",
    "businessstudies": "business_social", "socialsciencesandhumanities": "business_social",
    "classicalstudiesandinternationallanguages": "languages", "classicalandinternationallanguages": "languages",
    "frenchasasecondlanguage": "languages", "french": "languages", "nativelanguages": "languages",
    "firstnationsmetisandinuitstudies": "fnmi", "firstnationsmtisandinuitstudies": "fnmi",
}
_EXEMPT_SUBJECTS = ("guidanceandcareereducation", "cooperativeeducation", "interdisciplinarystudies",
                    "americansignlanguageasasecondlanguage")


def _key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def band(grade):
    return "9-10" if grade in (9, 10) else "11-12"


def expected(code, grade, subject):
    """The buckets and the exam/culminating split this course must use.

    Returns a dict: classroom, final_evaluation, attendance, exam, culminating,
    exempt (bool), and note. exam and culminating are None when the matrix has
    no row for the subject (decide by hand)."""
    code = (code or "").upper()
    b = band(grade)
    classroom, final, attendance = BUCKETS[b]
    out = {"classroom": classroom, "final_evaluation": final, "attendance": attendance,
           "exam": None, "culminating": None, "exempt": False, "note": ""}
    sk = _key(subject)
    if code == "GLC2O":
        out.update(exam=0, culminating=15, note="GLC2O: 15% culminating plus the 5% financial literacy requirement")
        return out
    if code in ("NBE3U", "NBE3C"):
        out.update(exam=25, culminating=0, note="NBE3U and NBE3C require a 25% written exam")
        return out
    # Grades 11-12 workplace (E) and open (O), Grades 9-10 locally developed (L); Grade 9-10 open is not exempt.
    if (b == "11-12" and code[-1:] in ("E", "O")) or (b == "9-10" and code[-1:] == "L") or sk in _EXEMPT_SUBJECTS:
        out.update(exempt=True, note="exempt from the written exam; the final evaluation is still %d%%" % final)
        return out
    group = _GROUPS.get(sk)
    if group:
        out["exam"], out["culminating"] = SPLITS[group][b]
    else:
        out["note"] = "subject %r has no row in the matrix" % subject
    return out

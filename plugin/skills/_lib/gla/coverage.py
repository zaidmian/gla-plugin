"""What a course's Curriculum_Coverage_Map.md says each unit assessment assesses.

The "Assessed in" cells are prose ("U2 assignment, U2 test", "U1 Test,
Assignment_Masjid_Library", "U2/U3/U5 assignment rubric rows", "every
assignment rubric (Communication row)"). claims() reads them into
{("test", "U2"): {codes}, ("assignment", "U2"): {codes}}; codes claimed for
every assignment or every test are added to every unit that has one.
"""
import glob
import os
import re

from . import mdtable

from .codes import CODE
UNIT_ITEM = re.compile(r"(?<![\w./])((?:U\d+\s*/\s*)*U\d+)\s+(assignments?|tests?)\b", re.I)
UNIT_TEST = re.compile(r"\bUnit (\d+) Test\b")
NAMED_ASSIGNMENT = re.compile(r"\bAssignment_(\w+)")
EVERY = re.compile(r"\bevery\s+(?:later\s+)?(assignment|test)", re.I)


def map_path(root):
    return os.path.join(root, "master", "01_Standards", "Curriculum_Coverage_Map.md")


def assessed_rows(path):
    """[(code, Assessed in cell, line)] from every Code table of the map at path."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    out = []
    for hdr, rows, _ in mdtable.tables(text):
        if not hdr or hdr[0].strip().lower() != "code":
            continue
        try:
            ai = mdtable.column(hdr, "assessed")
        except KeyError:
            continue
        for line, r in rows:
            code = r[0].strip()
            if CODE.fullmatch(code) and ai < len(r):
                out.append((code, r[ai], line))
    return out


def taught_rows(path):
    """[(code, Taught in or Anchor cell)] from every Code table of the map at path."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows = []
    for hdr, body, _ in mdtable.tables(text):
        if not hdr or hdr[0].strip().lower() != "code":
            continue
        ti = next((k for k, h in enumerate(hdr) if h.lower().startswith(("taught", "anchor"))), None)
        if ti is None:
            continue
        for _, c in body:
            code = c[0].strip()
            if CODE.fullmatch(code) and ti < len(c):
                rows.append((code, c[ti]))
    return rows


def mentions_week(cell, unit, week):
    """True when a coverage-map cell names this week (U2.W3, U2.W3.D1, U2.W2–W3)."""
    for m in re.finditer(r"(?<![\w.])%s\.W(\d+)(?:\s*[–-]\s*W(\d+))?(?!\d)" % re.escape(unit), cell or ""):
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        if lo <= week <= hi:
            return True
    return False


def assessed_cells(root):
    """{code: Assessed in cell} for every code row of the map."""
    return {code: cell for code, cell, _ in assessed_rows(map_path(root))}


def units(root):
    """{unit: {"test": bool, "assignment": assignment folder name or None}}."""
    out = {}
    for ud in sorted(glob.glob(os.path.join(root, "master", "02_Units", "U*_*"))):
        u = os.path.basename(ud).split("_")[0]
        a = sorted(glob.glob(os.path.join(ud, "Assessment", "Assignment_*")))
        out[u] = {"test": os.path.isdir(os.path.join(ud, "Assessment", "Test")),
                  "assignment": os.path.basename(a[0]) if a else None}
    return out


def claims(root):
    """{("test"|"assignment", unit): set of codes the map says that assessment assesses}."""
    us = units(root)
    by_name = {v["assignment"]: u for u, v in us.items() if v["assignment"]}
    out = {}
    for code, cell in assessed_cells(root).items():
        for m in UNIT_ITEM.finditer(cell):
            kind = "test" if m.group(2).lower().startswith("test") else "assignment"
            for u in re.findall(r"U\d+", m.group(1)):
                out.setdefault((kind, u), set()).add(code)
        for m in UNIT_TEST.finditer(cell):
            out.setdefault(("test", "U" + m.group(1)), set()).add(code)
        for m in NAMED_ASSIGNMENT.finditer(cell):
            u = by_name.get("Assignment_" + m.group(1))
            if u:
                out.setdefault(("assignment", u), set()).add(code)
        for m in EVERY.finditer(cell):
            kind = m.group(1).lower()
            for u, v in us.items():
                if (kind == "test" and v["test"]) or (kind == "assignment" and v["assignment"]):
                    out.setdefault((kind, u), set()).add(code)
    return out

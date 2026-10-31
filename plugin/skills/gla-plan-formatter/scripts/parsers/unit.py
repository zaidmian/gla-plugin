"""
Markdown -> unit spec (references/unit_schema.md).

Conventions: references/markdown_conventions.md, section "unit".
Worked example: examples/unit/example.md == examples/unit/example.json.
"""

import re

from mdparse import cell_lines, split_front_matter, tokenize
from parsers._blocks import as_str, para_block, spec_blocks

OVERVIEW_KEYS = ["Course", "Grade", "Unit Title", "Unit #", "Number of Days",
                 "Culminating Task Due", "Core Texts", "Strands Addressed"]
_ALIASES = {"unit_number": "Unit #", "unit_no": "Unit #", "unit_num": "Unit #",
            "days": "Number of Days", "due": "Culminating Task Due",
            "texts": "Core Texts", "strands": "Strands Addressed"}
_LESSON_COLS = ["num", "topic", "teacher", "student", "assessment", "expectations"]
_TABLE_KINDS = ("expectations", "achievement", "lesson_table", "reflection")


def _norm(k):
    return re.sub(r"[\s\-]+", "_", as_str(k).strip().lower())


def _overview(fm):
    lookup = {_norm(k): k for k in OVERVIEW_KEYS}
    lookup.update(_ALIASES)
    found = {}
    for k, v in fm.items():
        name = lookup.get(_norm(k))
        if name and v is not None:
            found[name] = as_str(v)
    return {k: found[k] for k in OVERVIEW_KEYS if k in found}


def _lines(cell):
    return [re.sub(r"^(?:[-*•]\s+)", "", ln) for ln in cell_lines(cell)]


def _pad(row, n):
    return list(row) + [""] * (n - len(row))


def _infer_kind(table):
    header = [h.lower() for h in (table.get("header") or [])]
    rows = table.get("rows") or []
    if header:
        if "strand" in header[0] or any("assessed" in h for h in header):
            return "expectations"
        if "criteria" in header[0]:
            return "reflection"
        if len(header) == 6:
            return "lesson_table"
        if len(rows) == 1 and len(header) >= 3:
            return "achievement"
    raise ValueError("unit: a section-level table needs a directive line before it, one of: "
                     + ", ".join("<!-- gla: %s -->" % k for k in _TABLE_KINDS))


def _table_section(tok):
    table = tok.table
    kind = tok.directive or _infer_kind(table)
    header, rows = table.get("header"), table.get("rows") or []
    if kind == "expectations":
        return {"kind": "expectations",
                "rows": [{"strand": r[0], "assessed": _lines(r[1]), "covered": _lines(r[2])}
                         for r in (_pad(r, 3) for r in rows)]}
    if kind == "achievement":
        names, descs = (header, rows[0] if rows else []) if header else \
                       (rows[0] if rows else [], rows[1] if len(rows) > 1 else [])
        descs = _pad(descs, len(names))
        return {"kind": "achievement",
                "categories": [{"name": n, "desc": d} for n, d in zip(names, descs)]}
    if kind == "lesson_table":
        return {"kind": "lesson_table",
                "rows": [dict(zip(_LESSON_COLS, _pad(r, 6))) for r in rows]}
    if kind == "reflection":
        return {"kind": "reflection",
                "rows": [{"criteria": r[0], "exemplar": r[1], "evidence": r[2]}
                         for r in (_pad(r, 3) for r in rows)]}
    raise ValueError("unit: unknown table directive '%s' (expected one of %s)"
                     % (kind, ", ".join(_TABLE_KINDS)))


def _is_variety(heading, body):
    if heading.lower().startswith("variety"):
        return True
    return any(t.directive == "variety" for t in body)


def _variety(label, body):
    groups, intro, cur = [], [], None
    for t in body:
        if t.kind == "h4":
            cur = {"label": t.text, "items": []}
            groups.append(cur)
        elif t.kind in ("checks", "ul"):
            if cur is None:
                cur = {"label": "", "items": []}
                groups.append(cur)
            if t.kind == "checks":
                cur["items"].extend([[txt, bool(c)] for txt, c in t.items])
            else:
                cur["items"].extend([[it["text"] if isinstance(it, dict) else it, True]
                                     for it in t.items])
        elif t.kind in ("p", "pi") and cur is None:
            intro.append(para_block(t.text)["text"])
    if intro:
        groups.insert(0, {"intro": " ".join(intro)})
    return {"kind": "variety", "label": label, "groups": groups}


def _para_section(tok):
    b = para_block(tok.text, italic=(tok.kind == "pi"))
    sec = {"kind": "para", "text": b["text"]}
    if b.get("italic"):
        sec["italic"] = True
    if b.get("bold"):
        sec["bold"] = True
    return sec


def _sections(tokens):
    out, i, n = [], 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t.kind in ("h1", "hr"):
            i += 1
        elif t.kind == "h2":
            kind = "step" if t.text.lower().startswith("step") else "heading"
            out.append({"kind": kind, "text": t.text})
            i += 1
        elif t.kind == "h3":
            j = i + 1
            while j < n and tokens[j].kind not in ("h1", "h2", "h3", "table"):
                j += 1
            body = tokens[i + 1:j]
            if _is_variety(t.text, body):
                out.append(_variety(t.text, body))
            else:
                out.append({"kind": "labeled", "label": t.text, "blocks": spec_blocks(body)})
            i = j
        elif t.kind == "table":
            out.append(_table_section(t))
            i += 1
        elif t.kind in ("p", "pi"):
            out.append(_para_section(t))
            i += 1
        elif t.kind == "label":
            out.append({"kind": "para", "text": t.text, "bold": True})
            i += 1
        else:
            raise ValueError("unit: a '%s' block cannot sit at section level; put it under a "
                             "'### ' heading so it renders in a labeled row" % t.kind)
    return out


def parse(text, path=None):
    fm, body = split_front_matter(text)
    fm = fm or {}
    toks = tokenize(body)
    spec = {}
    if fm.get("school"):
        spec["school"] = as_str(fm["school"])
    subtitle = next((t.text for t in toks if t.kind == "h1"), None)
    if subtitle:
        spec["subtitle"] = subtitle
    spec["overview"] = _overview(fm)
    if fm.get("footer"):
        spec["footer"] = as_str(fm["footer"])
    spec["sections"] = _sections(toks)
    return spec

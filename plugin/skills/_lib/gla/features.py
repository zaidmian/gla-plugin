"""Feature availability by slot, as data.

master/01_Standards/feature_availability.yaml is the source: one row per
slot ("from") with the cell text of the Style Guide's "Feature availability
by slot" table, plus the baseline tokens every student already has. The
Style Guide's table is rendered from it between two markers
(`gla features render`); run_samples.py reads the YAML; check_course flags
a table that has drifted from it.
"""
import os
import re

import yaml

REL = os.path.join("master", "01_Standards", "feature_availability.yaml")
STYLE = os.path.join("master", "01_Standards", "Style_Guide.md")
BEGIN = "<!-- feature table: rendered from feature_availability.yaml by `gla features render`; edit the YAML -->"
END = "<!-- end feature table -->"


def path(root):
    return os.path.join(root, REL)


def load(root):
    """{'baseline': [...], 'rows': [{'from', 'available'}]} or None when the course has no YAML."""
    p = path(root)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("baseline", [])
    data.setdefault("rows", [])
    return data


def _section(lines):
    """(start, end) line indexes of the Feature availability section, or None."""
    start = next((i for i, ln in enumerate(lines) if ln.startswith("#") and "feature availability" in ln.lower()), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    return start, end


def table_rows(text):
    """[(from, cell)] from the Style Guide's feature table."""
    lines = text.splitlines()
    sec = _section(lines)
    if not sec:
        return []
    rows = []
    for ln in lines[sec[0] + 1:sec[1]]:
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: ") or cells[0].lower() == "from":
            continue
        rows.append((cells[0], "|".join(cells[1:]).strip()))
    return rows


def baseline_tokens(text):
    """Backticked tokens under any heading that mentions a baseline."""
    out, heading = [], ""
    for ln in text.splitlines():
        if ln.startswith("#"):
            heading = ln.lower()
        elif "baseline" in heading:
            for t in re.findall(r"`([^`]+)`", ln):
                if t.strip() not in out:
                    out.append(t.strip())
    return out


def render_table(data):
    lines = [BEGIN, "", "| From | Newly available |", "|------|-----------------|"]
    lines += ["| %s | %s |" % (r["from"], r["available"]) for r in data.get("rows") or []]
    lines += ["", END]
    return "\n".join(lines)


def extract(text):
    """The YAML data a Style Guide's table and baseline section hold today."""
    return {"baseline": baseline_tokens(text), "rows": [{"from": f, "available": a} for f, a in table_rows(text)]}


def dump(data, code=""):
    head = ("# %s feature availability by slot: the source of the Style Guide's table.\n"
            "# Edit here, then run `gla features render`. run_samples.py reads this file.\n"
            "# rows: from = the first slot a row applies to (U2.W1, U3, INTRO); available = the\n"
            "#   table cell, with code features in backticks (those are what run_samples checks).\n"
            "# baseline: tokens every student already has; never flagged.\n" % code)
    body = yaml.safe_dump({"schema": 1, "baseline": data.get("baseline") or [], "rows": data.get("rows") or []},
                          sort_keys=False, allow_unicode=True, width=1000)
    return head + body


def with_rendered_table(text, data):
    """The Style Guide text with its feature table replaced by the rendering (markers added
    around the table the first time). None when there is no feature section."""
    lines = text.splitlines()
    rendered = render_table(data)
    if BEGIN in text and END in text:
        a, b = text.index(BEGIN), text.index(END) + len(END)
        return text[:a] + rendered + text[b:]
    sec = _section(lines)
    if not sec:
        return None
    idx = [i for i in range(sec[0] + 1, sec[1]) if lines[i].strip().startswith("|")]
    if not idx:
        return None
    first, last = idx[0], idx[-1]
    out = lines[:first] + rendered.splitlines() + lines[last + 1:]
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def drift(root):
    """None when the Style Guide's table matches the YAML; else a description."""
    data = load(root)
    sg = os.path.join(root, STYLE)
    if data is None or not os.path.exists(sg):
        return None
    with open(sg, encoding="utf-8") as f:
        text = f.read()
    if BEGIN not in text or END not in text:
        return "the Style Guide's feature table has no render markers; run `gla features render`"
    a, b = text.index(BEGIN), text.index(END) + len(END)
    if text[a:b] != render_table(data):
        return "the Style Guide's feature table differs from feature_availability.yaml; run `gla features render`"
    return None

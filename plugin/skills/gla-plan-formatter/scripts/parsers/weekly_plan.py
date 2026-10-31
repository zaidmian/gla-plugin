"""weekly_plan parser: CS-pipeline week_plan.yaml (Weekly_Plan_Schema v3 to v5)
or the house Markdown dialect -> the spec in references/weekly_plan_schema.md.

    parse(text, path) -> dict
"""

import re
from datetime import date

import categories
from mdparse import (
    blocks_to_spec_blocks, find_section, list_items, paragraphs, parse_simple_yaml,
    section_map, split_front_matter, strip_inline, tokenize,
)

LEARNING_SKILLS = ["Responsibility", "Organization", "Independent Work",
                   "Collaboration", "Initiative", "Self-Regulation"]
# The second entry is renamed per subject (categories.names); this is the default.
ACHIEVEMENT = ["Knowledge & Understanding", "Thinking", "Communication", "Application"]

_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


# ----------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------
def _norm(s):
    """Loose key for matching skill and category names ('Knowledge/Understanding',
    'Independent work', 'self regulation' all land on their canonical entry)."""
    s = re.sub(r"[^a-z]", "", str(s or "").lower())
    return s.replace("and", "")


def _flags(names, canon, given):
    """Map a list of names (or a list of [name, bool]) onto canonical booleans."""
    lookup = {_norm(c): c for c in canon}
    out = {c: False for c in canon}
    for item in given or []:
        if isinstance(item, (list, tuple)):
            name, checked = item[0], bool(item[1])
        else:
            name, checked = item, True
        key = lookup.get(_norm(name))
        if key is None:
            # 'Knowledge/Understanding' vs 'Knowledge & Understanding'
            for k, c in lookup.items():
                if _norm(name) and (_norm(name) in k or k in _norm(name)):
                    key = c
                    break
        if key:
            out[key] = checked
    return out


def _clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _iso(s):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", _clean(s))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _long_date(d, year=True):
    s = f"{_MONTHS[d.month - 1]} {d.day}"
    return f"{s}, {d.year}" if year else s


def _date_range(start, end):
    a, b = _iso(start), _iso(end)
    if a and b:
        if a.year == b.year and a.month == b.month:
            return f"{_MONTHS[a.month - 1]} {a.day} to {b.day}, {a.year}"
        if a.year == b.year:
            return f"{_long_date(a, year=False)} to {_long_date(b)}"
        return f"{_long_date(a)} to {_long_date(b)}"
    if a:
        return _long_date(a)
    return ""


# ----------------------------------------------------------------------------
# YAML (CS pipeline week_plan.yaml)
# ----------------------------------------------------------------------------
def _load_yaml(text):
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return parse_simple_yaml(text)
    except Exception:
        return None


def _unit_label(unit, unit_name):
    unit = _clean(unit)
    m = re.fullmatch(r"[Uu](?:nit)?\s*(\d+)", unit)
    label = f"Unit {m.group(1)}" if m else unit
    return f"{label}: {unit_name}" if unit_name else label


def _yaml_days(dl):
    days = []
    for i, d in enumerate(dl or [], start=1):
        num = str(d.get("day") or i)
        title = _clean(d.get("title") or d.get("focus") or "")
        left = []
        if d.get("title") and d.get("focus"):
            left.append({"type": "para", "text": _clean(d["focus"]), "italic": True})
        acts = []
        for a in d.get("activities") or []:
            if isinstance(a, dict):
                what = _clean(a.get("what"))
                mins = a.get("minutes")
                acts.append(f"{mins} min: {what}" if mins not in (None, "", 0) else what)
            else:
                acts.append(_clean(a))
        if acts:
            left.append({"type": "numbered", "items": acts})
        right = []
        if d.get("materials"):
            right.append({"type": "bullets", "items": [_clean(x) for x in d["materials"]]})
        day = {"num": num, "title": title}
        when = _iso(d.get("date"))
        if when:
            day["time"] = _long_date(when, year=False)
        day["left"] = {"label": "Teacher Actions", "blocks": left}
        day["right"] = {"label": "Materials", "blocks": right}
        days.append(day)
    return days


def _from_yaml(data):
    md = data.get("metadata") or {}
    code = _clean(md.get("course_code"))
    name = _clean(md.get("course_name"))
    grade = md.get("grade")
    grade_s = f"Grade {grade}" if grade not in (None, "", 0) else ""
    pathway = _clean(md.get("pathway"))
    unit_label = _unit_label(md.get("unit"), _clean(md.get("unit_name")))
    week_n = md.get("week")
    week_s = f"Week {week_n}" if week_n not in (None, "") else ""
    dates = md.get("dates") or {}

    course_line = code
    if name:
        course_line += f": {name}"
    if grade_s:
        course_line += f", {grade_s}"
    context_line = unit_label.split(":")[0]
    if week_s:
        context_line += f"  |  {week_s}"

    minutes = []
    for d in data.get("daily_lessons") or []:
        tot = sum(int(a.get("minutes") or 0) for a in (d.get("activities") or [])
                  if isinstance(a, dict))
        if tot:
            minutes.append(tot)
    duration = f"{max(minutes)} minutes per class" if minutes else ""

    spec = {
        "context": {"course_line": course_line, "context_line": context_line},
        "badge": " | ".join(x for x in (grade_s, pathway) if x),
        "title": _clean(md.get("week_title")),
        "meta": {
            "teacher": _clean(md.get("teacher")),
            "course_code": code,
            "grade": grade_s,
            "subject": name,
            "unit": unit_label,
            "week": week_s,
            "dates": _date_range(dates.get("start"), dates.get("end")),
            "duration": duration,
        },
    }
    if md.get("school"):
        spec["school"] = _clean(md["school"]).upper()

    ie = data.get("islamic_expectations") or {}
    if isinstance(ie, dict):
        blocks = []
        if ie.get("focus"):
            blocks.append({"type": "para", "text": _clean(ie["focus"]), "bold": True})
        if ie.get("connection"):
            blocks.append({"type": "para", "text": _clean(ie["connection"])})
        spec["islamic_expectations"] = blocks
    else:
        spec["islamic_expectations"] = _clean(ie)

    ce = data.get("character_education") or {}
    if isinstance(ce, dict):
        spec["character_education"] = {"values": [_clean(v) for v in ce.get("values") or []],
                                       "text": _clean(ce.get("how"))}
    else:
        spec["character_education"] = _clean(ce)

    spec["learning_skills"] = _flags("skills", LEARNING_SKILLS, data.get("learning_skills"))
    cur = data.get("curriculum_expectations") or {}
    spec["curriculum"] = {
        "overall": ", ".join(_clean(x) for x in cur.get("overall") or []),
        "specific": ", ".join(_clean(x) for x in cur.get("specific") or []),
        "achievement_categories": _flags("cats", categories.names(ACHIEVEMENT, code),
                                         data.get("achievement_categories")),
    }
    spec["resources"] = [_clean(r) for r in data.get("resources") or []]

    goals, criteria = [], []
    for g in data.get("learning_goals") or []:
        if isinstance(g, dict):
            if g.get("goal"):
                goals.append(_clean(g["goal"]))
            criteria.extend(_clean(c) for c in g.get("success_criteria") or [])
        else:
            goals.append(_clean(g))
    spec["learning_goals"] = goals
    spec["success_criteria"] = criteria

    spec["days"] = _yaml_days(data.get("daily_lessons"))

    asm = data.get("assessment") or {}
    of = asm.get("of_learning") or []
    if isinstance(of, dict):
        of = {k: [_clean(x) for x in v or []] for k, v in of.items()}
    else:
        of = [_clean(x) for x in of]
    spec["assessment"] = {
        "for_learning": [_clean(x) for x in asm.get("for_learning") or []],
        "as_learning": [_clean(x) for x in asm.get("as_learning") or []],
        "of_learning": of,
    }

    notes = []
    if data.get("notes"):
        notes.append({"type": "para", "text": _clean(data["notes"])})
    evals = []
    for ev in data.get("evaluations") or []:
        if not isinstance(ev, dict) or not ev.get("name"):
            continue
        bits = [_clean(ev["name"])]
        if ev.get("kind"):
            bits[0] += f" ({_clean(ev['kind'])})"
        tail = []
        if ev.get("handed_out"):
            tail.append(f"handed out {_clean(ev['handed_out'])}")
        if ev.get("due"):
            tail.append(f"due {_clean(ev['due'])}")
        if ev.get("marks"):
            tail.append(f"marked {_clean(ev['marks'])}")
        evals.append(bits[0] + (": " + ", ".join(tail) if tail else ""))
    if evals:
        notes.append({"type": "label", "text": "Evaluations this week:"})
        notes.append({"type": "bullets", "items": evals})
    if notes:
        spec["notes"] = notes
    return spec


# ----------------------------------------------------------------------------
# Markdown
# ----------------------------------------------------------------------------
_DAY_RX = re.compile(r"^day\s+(\d+)\s*[:.]?\s*(.*?)\s*(?:\(([^)]*)\))?\s*$", re.I)


def _text_or_blocks(blocks):
    """A single plain paragraph collapses to a string; anything else stays blocks."""
    spec_blocks = blocks_to_spec_blocks(blocks)
    if len(spec_blocks) == 1 and spec_blocks[0].get("type") == "para" \
            and set(spec_blocks[0].keys()) == {"type", "text"}:
        return spec_blocks[0]["text"]
    return spec_blocks


def _names_from(blocks):
    """Checklist -> [(name, bool)]; a bullet list or comma line -> names (all checked)."""
    for b in blocks:
        if b.kind == "checks":
            return [(strip_inline(t), c) for t, c in b.items]
    items = list_items(blocks)
    if items:
        return [strip_inline(x) for x in items]
    out = []
    for p in paragraphs(blocks):
        out.extend(x.strip() for x in re.split(r"[,;]", strip_inline(p)) if x.strip())
    return out


def _labelled(blocks, *names):
    """Value for '**Name:** text' inline lines or a '**Name:**' label line followed
    by content up to the next label. Returns a string, blocks, or None."""
    want = [n.lower() for n in names]
    for i, b in enumerate(blocks):
        if b.kind == "p":
            m = re.match(r"^\*\*([^*]+?):?\*\*:?\s*(.*)$", b.text)
            if m and any(m.group(1).strip().lower().startswith(w) for w in want):
                if m.group(2).strip():
                    return m.group(2).strip()
                b = type(b)("label", m.group(1).strip() + ":")
        if b.kind == "label" and any(b.text.rstrip(":").lower().startswith(w) for w in want):
            run = []
            for nb in blocks[i + 1:]:
                if nb.kind in ("label", "h3", "h4", "checks"):
                    break
                if nb.kind == "p" and re.match(r"^\*\*[^*]+\*\*", nb.text):
                    break
                run.append(nb)
            return _text_or_blocks(run) if run else None
    return None


def _sub_blocks(blocks, label):
    """Blocks under one h4 -> {label, blocks}."""
    return {"label": label, "blocks": blocks_to_spec_blocks(blocks)}


def _md_days(blocks):
    days = []
    for title, body in section_map(blocks, level="h3"):
        if title is None:
            continue
        m = _DAY_RX.match(strip_inline(title))
        if m:
            num, dtitle, time = m.group(1), m.group(2), m.group(3)
        else:
            num, dtitle, time = str(len(days) + 1), strip_inline(title), None
        parts = section_map(body, level="h4")
        lead = [b for t, b in parts if t is None]
        subs = [(t, b) for t, b in parts if t is not None]
        day = {"num": num, "title": dtitle.strip()}
        if time:
            day["time"] = time.strip()
        if subs:
            day["left"] = _sub_blocks(subs[0][1], strip_inline(subs[0][0]))
            if lead and lead[0]:
                day["left"]["blocks"] = blocks_to_spec_blocks(lead[0]) + day["left"]["blocks"]
            if len(subs) > 1:
                day["right"] = _sub_blocks(subs[1][1], strip_inline(subs[1][0]))
                for extra_t, extra_b in subs[2:]:
                    day["right"]["blocks"].append({"type": "label", "text": strip_inline(extra_t)})
                    day["right"]["blocks"].extend(blocks_to_spec_blocks(extra_b))
            else:
                day["right"] = {"blocks": []}
        else:
            day["left"] = {"label": "Teacher Actions",
                           "blocks": blocks_to_spec_blocks(lead[0] if lead else [])}
            day["right"] = {"blocks": []}
        days.append(day)
    return days


def _md_assessment(blocks):
    out = {"for_learning": [], "as_learning": [], "of_learning": []}
    keys = {"for": "for_learning", "as": "as_learning", "of": "of_learning"}
    for title, body in section_map(blocks, level="h3"):
        if title is None:
            continue
        t = strip_inline(title).lower()
        m = re.match(r"^(?:assessment\s+)?(for|as|of)\b", t) or re.match(r"^(a[fao])l\b", t)
        if not m:
            continue
        key = keys.get(m.group(1)) or {"afl": "for_learning", "aal": "as_learning",
                                        "aol": "of_learning"}[m.group(1)]
        groups = [(gt, gb) for gt, gb in section_map(body, level="h4") if gt is not None]
        if key == "of_learning" and groups:
            out[key] = {strip_inline(gt): [strip_inline(x) for x in list_items(gb)]
                        for gt, gb in groups}
        else:
            items = [strip_inline(x) for x in list_items(body)]
            if not items:
                items = [x.strip() for p in paragraphs(body) for x in p.split(";") if x.strip()]
            out[key] = items
    return out


def _md_differentiation(blocks):
    diff = {}
    for title, body in section_map(blocks, level="h3"):
        if title is None:
            continue
        diff[strip_inline(title)] = [strip_inline(x) for x in list_items(body)]
    return diff


def _from_markdown(text):
    front, body = split_front_matter(text)
    blocks = tokenize(body)
    secs = section_map(blocks, level="h2")
    lead = [b for t, b in secs if t is None]
    h1 = next((b.text for b in (lead[0] if lead else []) if b.kind == "h1"), None)

    meta_keys = ["teacher", "course_code", "grade", "subject", "unit", "week", "dates", "duration"]
    meta = {k: _clean(front.get(k)) for k in meta_keys if front.get(k) not in (None, "")}
    spec = {
        "context": {"course_line": str(front.get("course_line") or "").strip()},
        "badge": _clean(front.get("badge")),
        "title": _clean(front.get("title") or h1),
        "meta": meta,
    }
    if front.get("school"):
        spec["school"] = _clean(front["school"])
    if front.get("context_line"):
        spec["context"]["context_line"] = str(front["context_line"]).strip()
    if front.get("footer"):
        spec["footer"] = _clean(front["footer"])

    s = find_section(secs, "islamic")
    if s is not None:
        spec["islamic_expectations"] = _text_or_blocks(s)
    s = find_section(secs, "character")
    if s is not None:
        values = _labelled(s, "values")
        rest = [b for b in s if not (b.kind == "p" and re.match(r"^\*\*values", b.text, re.I))]
        if isinstance(values, str):
            spec["character_education"] = {
                "values": [v.strip() for v in values.split(",") if v.strip()],
                "text": _text_or_blocks(rest)}
        else:
            spec["character_education"] = _text_or_blocks(s)

    s = find_section(secs, "learning skills")
    spec["learning_skills"] = _flags("skills", LEARNING_SKILLS, _names_from(s) if s else [])

    cur_blocks = find_section(secs, "curriculum") or []
    cats_blocks = find_section(secs, "achievement") or cur_blocks
    spec["curriculum"] = {
        "overall": _labelled(cur_blocks, "overall") or "",
        "specific": _labelled(cur_blocks, "specific") or "",
        "achievement_categories": _flags("cats",
                                         categories.names(ACHIEVEMENT, meta.get("course_code")),
                                         _names_from(cats_blocks) if cats_blocks else []),
    }

    s = find_section(secs, "resources")
    spec["resources"] = [strip_inline(x) for x in list_items(s)] if s else []

    s = find_section(secs, "learning goals") or []
    lead_p = [b.text for b in s if b.kind in ("p", "label")]
    if lead_p:
        spec["learning_goals_lead"] = strip_inline(lead_p[0])
    spec["learning_goals"] = [strip_inline(x) for x in list_items(s)]
    s = find_section(secs, "success criteria") or []
    spec["success_criteria"] = [strip_inline(x) for x in list_items(s)]

    s = find_section(secs, "daily lessons", "lessons", "days") or []
    spec["days"] = _md_days(s)

    s = find_section(secs, "assessment") or []
    spec["assessment"] = _md_assessment(s)

    s = find_section(secs, "differentiation", "teacher notes")
    if s:
        d = _md_differentiation(s)
        if d:
            spec["differentiation"] = d
    s = find_section(secs, "notes")
    if s:
        spec["notes"] = blocks_to_spec_blocks(s)
    return spec


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def parse(text, path=None):
    is_yaml = bool(path) and str(path).lower().endswith((".yaml", ".yml"))
    if not is_yaml and re.search(r"^metadata:\s*$", text, re.M):
        is_yaml = True
    if is_yaml:
        data = _load_yaml(text)
        if isinstance(data, dict) and "metadata" in data:
            return _from_yaml(data)
        if isinstance(data, dict) and "meta" in data and "days" in data:
            return data     # already the spec, expressed in YAML
        raise ValueError(f"{path or 'source'}: not a week_plan.yaml (no 'metadata:' block)")
    return _from_markdown(text)

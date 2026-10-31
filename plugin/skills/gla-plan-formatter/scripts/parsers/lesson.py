"""
Markdown -> lesson spec (references/lesson_schema.md).

Conventions: references/markdown_conventions.md, section "lesson".
Worked example: examples/lesson/example.md == examples/lesson/example.json.
"""

import re

import categories
from mdparse import find_section, list_items, section_map, split_front_matter, tokenize
from parsers._blocks import as_str, spec_blocks, string_or_blocks

# The second entry is renamed per subject (categories.names); this is the default.
ACHIEVEMENT = ["Knowledge & Understanding", "Thinking", "Communication", "Application"]
DIFF_DEFAULT = ["ELL Students", "IEP / Accommodation", "Advanced / Extension"]

# "1. Minds On (10 minutes): Hook & Warm-Up"  ->  num, phase, time?, subtitle?
_PHASE_RX = re.compile(r"^(\d+)[.)]?\s+(.+?)(?:\s*\(([^)]*)\))?(?:\s*:\s*(.*))?$")


def _key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _categories(listed, code=None):
    listed = listed or []
    if isinstance(listed, str):
        listed = [x for x in re.split(r"[,;|]", listed) if x.strip()]
    keys = [_key(x) for x in listed]
    canon_names = categories.names(ACHIEVEMENT, code)
    aliases = {"ku": canon_names[0], "understanding": canon_names[0]}
    out = {}
    for name in canon_names:
        canon = _key(name)
        head = canon[:9]  # "knowledge", "thinking", "communica", "applicati"
        out[name] = any(k == canon or k.startswith(head) or aliases.get(k) == name
                        or (len(k) >= 4 and canon.startswith(k)) for k in keys)
    return out


def _split_h4(tokens):
    """[(label|None, tokens)] split on '#### ' headings; a leading unlabeled run is kept."""
    groups, label, buf = [], None, []
    for t in tokens:
        if t.kind == "h4":
            if label is not None or buf:
                groups.append((label, buf))
            label, buf = t.text, []
        else:
            buf.append(t)
    if label is not None or buf:
        groups.append((label, buf))
    return groups


def _side(label, tokens):
    side = {}
    if label:
        side["label"] = label
    side["blocks"] = spec_blocks(tokens)
    return side


def _phase(heading, tokens):
    m = _PHASE_RX.match(heading.strip())
    ph = {}
    if m:
        ph["num"] = m.group(1)
        ph["phase"] = m.group(2).strip().upper()
        if m.group(3) and m.group(3).strip():
            ph["time"] = m.group(3).strip()
        if m.group(4) and m.group(4).strip():
            ph["subtitle"] = m.group(4).strip()
    else:
        ph["phase"] = heading.strip()
    groups = _split_h4(tokens)
    if groups:
        ph["left"] = _side(*groups[0])
    if len(groups) > 1:
        right = _side(*groups[1])
        for label, extra in groups[2:]:
            right["blocks"].append({"type": "label", "text": label})
            right["blocks"].extend(spec_blocks(extra))
        ph["right"] = right
    return ph


def _materials(tokens):
    mats = {}
    for title, toks in section_map(tokens, "h3"):
        if title is None:
            continue
        key = "teacher" if title.lower().startswith("teacher") else \
              "student" if title.lower().startswith("student") else None
        if key is None:
            continue
        mats[key] = list_items(toks)
        extra = spec_blocks([t for t in toks if t.kind not in ("ul", "ol")])
        if extra:
            mats[key + "_extra"] = extra
    mats.setdefault("teacher", [])
    mats.setdefault("student", [])
    return mats


def parse(text, path=None):
    fm, body = split_front_matter(text)
    fm = fm or {}
    toks = tokenize(body)
    secs = section_map(toks, "h2")
    title = next((t.text for t in toks if t.kind == "h1"), None)

    spec = {}
    gaps = []

    def _gap(section, field, value):
        """Record an empty required field; the document renders it blank."""
        if not value:
            gaps.append({"section": section, "field": field})
        return value or ""

    if fm.get("school"):
        spec["school"] = as_str(fm["school"])
    context = {"course_line": _gap("Masthead", "course", as_str(fm.get("course") or fm.get("course_line")))}
    if fm.get("context_line"):
        context["context_line"] = as_str(fm["context_line"])
    spec["context"] = context
    spec["badge"] = as_str(fm.get("badge"))
    spec["title"] = _gap("Title", "title", title)
    spec["meta"] = {k: _gap("Meta", k, as_str(fm.get(k)))
                    for k in ("course_code", "unit", "lesson", "duration")}

    cur = section_map(find_section(secs, "curriculum") or [], "h3")
    spec["curriculum"] = {
        "overall": _gap("Curriculum", "overall", string_or_blocks(find_section(cur, "overall") or [])),
        "specific": _gap("Curriculum", "specific", string_or_blocks(find_section(cur, "specific") or [])),
        "achievement_categories": _categories(fm.get("achievement_categories"),
                                             spec["meta"].get("course_code")),
    }

    lg = find_section(secs, "learning goal") or []
    lead = next((t for t in lg if t.kind in ("p", "label")), None)
    if lead is not None:
        spec["learning_goals_lead"] = lead.text
    spec["learning_goals"] = list_items(lg)
    spec["success_criteria"] = list_items(find_section(secs, "success criteria") or [])
    spec["materials"] = _materials(find_section(secs, "materials") or [])

    seq = find_section(secs, "lesson sequence", "sequence") or []
    spec["sequence"] = [_phase(t, ptoks) for t, ptoks in section_map(seq, "h3") if t is not None]

    d_toks = find_section(secs, "differentiation") or []
    diff = {}
    for t, dtoks in section_map(d_toks, "h3"):
        if t is None:
            if list_items(dtoks):
                raise ValueError("lesson: Differentiation bullets must sit under '### ' column "
                                 "headings (e.g. ### ELL Students)")
            continue
        diff[t] = list_items(dtoks)
    if not diff:
        for k in DIFF_DEFAULT:
            _gap("Differentiation", k, None)
    spec["differentiation"] = diff or {k: [] for k in DIFF_DEFAULT}

    gc = list_items(find_section(secs, "google classroom", "connections to google classroom") or [])
    if gc:
        spec["google_classroom"] = gc
    if fm.get("footer"):
        spec["footer"] = as_str(fm["footer"])
    if gaps:
        spec["review"] = {"gaps": gaps}
    return spec

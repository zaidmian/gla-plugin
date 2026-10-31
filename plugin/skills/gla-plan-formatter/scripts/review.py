#!/usr/bin/env python3
"""
review: the teacher's review list for a build.

    python3 review.py --spec plan.spec.json --name ICS3U_Unit2 --out ICS3U_Review.md [--title "..."]

No document carries a marker. Instead, every run that drafts, derives, or
changes content writes (or updates) one Markdown review file beside the
outputs. It lists, per document and per section, each area the teacher must
check before the documents are submitted, and opens with the gaps that were
left blank because they had no source and no consent.

The build collects three things from a spec:

  * spec["review"]["gaps"]:  [{"section": ..., "field": ...}]   required fields left blank
  * spec["review"]["items"]: [{"section": ..., "text": ..., "risk": "high"?}]
  * a string "review" key on any nested dict (a section, a block, a row):
    the item text, with the section label taken from the enclosing dict.

Risk "high" is reserved for statements of fact about the teacher, the school,
or the students; those items print in bold.

Each document's section ends in an HTML comment holding its record, so a later
run can rebuild the file without re-reading documents it did not touch.
Hand-written sections (a title that is not a document name) are kept as they are.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

GAPS_HEADING = "Gaps: not filled"
_DATA_RX = re.compile(r"<!-- review-data: (.*?) -->", re.S)
_H2_RX = re.compile(r"^## (.+?)\s*$", re.M)
_NUMBERED_RX = re.compile(r"^\d+\.\s+(.*)$")
_LABEL_KEYS = ("label", "title", "name", "strand", "criteria")


def _label_of(d, fallback, seen):
    label = None
    for k in _LABEL_KEYS:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            label = v.strip()
            break
    if label is None and d.get("kind") in ("step", "heading") and isinstance(d.get("text"), str):
        label = d["text"].strip()
    if label is not None and label not in seen:
        seen.append(label)
    return label or fallback


def _walk(node, section, out, seen):
    """Collect nested review strings. A list of sections keeps a running label:
    a step or heading names the sections that follow it until the next one."""
    if isinstance(node, dict):
        here = _label_of(node, section, seen)
        rv = node.get("review")
        if isinstance(rv, str) and rv.strip():
            out.append({"section": here, "text": rv.strip()})
        for k, v in node.items():
            if k != "review":
                _walk(v, here, out, seen)
    elif isinstance(node, list):
        running = section
        for v in node:
            if isinstance(v, dict) and v.get("kind") in ("step", "heading") and isinstance(v.get("text"), str):
                running = v["text"].strip()
                if running not in seen:
                    seen.append(running)
            _walk(v, running, out, seen)


def collect(spec, doc_name):
    """One record: {"name", "source", "gaps", "items"} for a spec. Items are ordered as
    the document reads: sections named nowhere in the spec first (headers, grids),
    then in the order their sections appear, with "Document" last."""
    top = spec.get("review") if isinstance(spec.get("review"), dict) else {}
    items, seen = [], []
    for it in top.get("items", []) or []:
        item = {"section": it.get("section") or "Document", "text": str(it.get("text", "")).strip()}
        if it.get("risk"):
            item["risk"] = it["risk"]
        if item["text"]:
            items.append(item)
    _walk({k: v for k, v in spec.items() if k != "review"}, "Document", items, seen)

    def rank(it):
        s = it["section"]
        if s == "Document":
            return len(seen) + 1
        return seen.index(s) if s in seen else -1
    items.sort(key=rank)
    gaps = [{"section": g.get("section") or "Document", "field": g.get("field") or ""}
            for g in (top.get("gaps", []) or [])]
    return {"name": doc_name, "source": top.get("source") or "", "gaps": gaps, "items": items}


def _render_doc(doc, index):
    high = sum(1 for it in doc["items"] if it.get("risk") == "high")
    lines = [f"## {index}. {doc['name']}", ""]
    src = f"Source: {doc['source']}. " if doc.get("source") else ""
    lines.append(f"{src}{len(doc['items'])} items, {high} high-risk.")
    lines.append("")
    n = 0
    current = None
    for it in doc["items"]:
        if it["section"] != current:
            current = it["section"]
            if n:
                lines.append("")
            lines.append(f"**{current}**")
            lines.append("")
        n += 1
        text = it["text"]
        if it.get("risk") == "high":
            text = f"**{text}**"
        lines.append(f"{n}. {text}")
    if doc["items"]:
        lines.append("")
    else:
        lines.append("No drafted or derived content.")
        lines.append("")
    record = {k: doc[k] for k in ("name", "source", "gaps", "items")}
    lines.append(f"<!-- review-data: {json.dumps(record, ensure_ascii=False)} -->")
    lines.append("")
    return "\n".join(lines)


def render(docs, title=None, extra_sections=()):
    """The whole review file from a list of document records."""
    names = [d["name"] for d in docs]
    title = title or "plan documents"
    out = [f"# Review List: {title}", ""]
    count = len(names)
    listed = ", ".join(names)
    out.append(f"This file covers {count} document{'s' if count != 1 else ''}: {listed}. "
               "Every area listed below was drafted, derived, or changed from its source during the build "
               "and needs your check before the documents are submitted. Areas not listed were carried over "
               "from your sources with light cleanup only.")
    out.append("")
    out.append(f"## {GAPS_HEADING}")
    out.append("")
    any_gap = False
    for d in docs:
        for g in d["gaps"]:
            any_gap = True
            out.append(f"- **{d['name']}**: {g['section']}, {g['field']} (blank in the document; no source and no consent)")
    if not any_gap:
        out.append("None.")
    out.append("")
    for i, d in enumerate(docs, 1):
        out.append(_render_doc(d, i))
    for title_, body in extra_sections:
        out.append(f"## {title_}")
        out.append("")
        out.append(body.strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _parse(text):
    """Existing file -> (title, [doc records], [(title, body)] for hand-written sections)."""
    m = re.match(r"# Review List: (.+)", text)
    title = m.group(1).strip() if m else None
    docs, extras = [], []
    parts = _H2_RX.split(text)
    # parts: [preamble, h2 title, body, h2 title, body, ...]
    for i in range(1, len(parts), 2):
        h, body = parts[i].strip(), parts[i + 1]
        if h == GAPS_HEADING:
            continue
        dm = _DATA_RX.search(body)
        if dm:
            try:
                docs.append(json.loads(dm.group(1)))
                continue
            except json.JSONDecodeError:
                pass
        nm = _NUMBERED_RX.match(h)
        extras.append((nm.group(1) if nm else h, body))
    return title, docs, extras


def merge(path, doc, title=None):
    """Write or update the review file so that `doc` replaces any earlier record with the same name."""
    docs, extras, old_title = [], [], None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            old_title, docs, extras = _parse(fh.read())
    docs = [d for d in docs if d.get("name") != doc["name"]] + [doc]
    text = render(docs, title or old_title, extras)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return len(doc["items"]), len(doc["gaps"])


def main():
    ap = argparse.ArgumentParser(description="Write or update a review list from a spec.")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--name", required=True, help="document name, normally the .docx stem")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    a = ap.parse_args()
    with open(a.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    items, gaps = merge(a.out, collect(spec, a.name), a.title)
    print(f"Wrote {a.out} ({items} items, {gaps} gaps)")


if __name__ == "__main__":
    main()

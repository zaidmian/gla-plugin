#!/usr/bin/env python3
"""
mdparse: the house Markdown dialect, tokenised once for every document type.

    front, body = split_front_matter(text)      # optional --- key: value --- block
    blocks = tokenize(body)                      # list of Block(kind, text, items, table, level, directive)

Block kinds: h1 h2 h3 h4 p pi (wholly italic line) label (wholly **Bold:** line)
ul ol checks quote table hr. A `<!-- gla: NAME -->` comment before a table (or
list) is recorded on that block as .directive. Tables carry {"header": row|None,
"rows": [...]}. Cells keep inline **bold**; '<br>' inside a cell marks in-cell
line breaks. See references/markdown_conventions.md.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_DIRECTIVE_RX = re.compile(r"^<!--\s*gla:\s*([a-z_]+)\s*-->\s*$")
_OL_RX = re.compile(r"^(\d+)[.)]\s+(.*)$")
_CHECK_RX = re.compile(r"^[-*]\s+\[( |x|X)\]\s+(.*)$")


@dataclass
class Block:
    kind: str
    text: str = ""
    items: List[Any] = field(default_factory=list)
    table: Optional[Dict[str, Any]] = None
    directive: Optional[str] = None
    level: int = 0


# ----------------------------------------------------------------------------
# Front matter
# ----------------------------------------------------------------------------
def _parse_scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [s.strip().strip("'\"") for s in inner.split(",")] if inner else []
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.lower() in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def parse_simple_yaml(text):
    """Flat or one-level-nested key: value YAML without PyYAML."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except Exception:
        pass
    data = {}
    stack = [(0, data)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        if line.startswith("- "):
            if isinstance(container, dict) and "__list__" not in container:
                container["__list__"] = []
            container.setdefault("__list__", []).append(_parse_scalar(line[2:]))
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            if v.strip() == "":
                new = {}
                container[k] = new
                stack.append((indent + 1, new))
            else:
                container[k] = _parse_scalar(v)
    def _fix(d):
        if isinstance(d, dict):
            if list(d.keys()) == ["__list__"]:
                return [_fix(x) for x in d["__list__"]]
            return {k: _fix(v) for k, v in d.items()}
        return d
    return _fix(data)


def split_front_matter(text):
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return parse_simple_yaml("\n".join(lines[1:i])), "\n".join(lines[i + 1:])
    return {}, text


# ----------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------
def split_md_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def is_table_sep(cells):
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells if c != "")


def parse_table(lines):
    rows = [split_md_row(x) for x in lines]
    if len(rows) >= 2 and is_table_sep(rows[1]):
        return {"header": rows[0], "rows": [r for r in rows[2:] if not is_table_sep(r)]}
    return {"header": None, "rows": [r for r in rows if not is_table_sep(r)]}


def cell_lines(cell):
    """Split a cell on <br> (or ' / ') into trimmed non-empty lines."""
    parts = re.split(r"<br\s*/?>", cell or "", flags=re.I)
    return [p.strip() for p in parts if p.strip()]


def strip_inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", s or "").strip()


# ----------------------------------------------------------------------------
# Tokeniser
# ----------------------------------------------------------------------------
def tokenize(text):
    lines = text.splitlines()
    blocks: List[Block] = []
    pending_directive = None
    i = 0
    para_buf: List[str] = []

    def flush_para():
        nonlocal para_buf
        if para_buf:
            s = " ".join(x.strip() for x in para_buf).strip()
            para_buf = []
            if not s:
                return
            if s.startswith("*") and s.endswith("*") and not s.startswith("**"):
                blocks.append(Block("pi", s.strip("*").strip()))
            elif re.fullmatch(r"\*\*[^*]+\*\*:?", s):
                blocks.append(Block("label", s.strip("*").rstrip(":").strip() + ":"))
            else:
                blocks.append(Block("p", s))

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        m = _DIRECTIVE_RX.match(s)
        if m:
            flush_para()
            pending_directive = m.group(1)
            i += 1
            continue
        if s == "":
            flush_para()
            i += 1
            continue
        if s == "---" or s == "***":
            flush_para()
            blocks.append(Block("hr"))
            i += 1
            continue
        hm = re.match(r"^(#{1,4})\s+(.*)$", s)
        if hm:
            flush_para()
            blocks.append(Block("h%d" % len(hm.group(1)), hm.group(2).strip(), level=len(hm.group(1))))
            i += 1
            continue
        if s.startswith("|"):
            flush_para()
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            blocks.append(Block("table", table=parse_table(tbl), directive=pending_directive))
            pending_directive = None
            continue
        cm = _CHECK_RX.match(s)
        if cm:
            flush_para()
            items = []
            while i < len(lines):
                cm = _CHECK_RX.match(lines[i].strip())
                if not cm:
                    break
                items.append([cm.group(2).strip(), cm.group(1).lower() == "x"])
                i += 1
            blocks.append(Block("checks", items=items, directive=pending_directive))
            pending_directive = None
            continue
        if re.match(r"^[-*]\s+", s):
            flush_para()
            items = []
            while i < len(lines):
                cur = lines[i]
                cs = cur.strip()
                if re.match(r"^[-*]\s+", cs) and not _CHECK_RX.match(cs):
                    indent = len(cur) - len(cur.lstrip())
                    txt = re.sub(r"^[-*]\s+", "", cs)
                    if indent >= 2 and items:
                        items[-1] = {"text": items[-1]["text"] if isinstance(items[-1], dict) else items[-1],
                                     "sub": (items[-1].get("sub", []) if isinstance(items[-1], dict) else []) + [txt]}
                    else:
                        items.append(txt)
                    i += 1
                elif cs and not re.match(r"^(#{1,4}\s|\||\d+[.)]\s|<!--)", cs) and (len(cur) - len(cur.lstrip())) >= 2:
                    # continuation line of the previous item
                    if items:
                        if isinstance(items[-1], dict):
                            items[-1]["text"] += " " + cs
                        else:
                            items[-1] += " " + cs
                    i += 1
                else:
                    break
            blocks.append(Block("ul", items=items, directive=pending_directive))
            pending_directive = None
            continue
        om = _OL_RX.match(s)
        if om:
            flush_para()
            items, start = [], int(om.group(1))
            while i < len(lines):
                om = _OL_RX.match(lines[i].strip())
                if not om:
                    break
                items.append(om.group(2).strip())
                i += 1
            b = Block("ol", items=items, directive=pending_directive)
            b.level = start
            blocks.append(b)
            pending_directive = None
            continue
        if s.startswith(">"):
            flush_para()
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append(Block("quote", " ".join(q)))
            continue
        para_buf.append(s)
        i += 1
    flush_para()
    return blocks


def blocks_to_spec_blocks(blocks):
    """Convert a run of tokens into the shared block vocabulary (references/blocks.md)."""
    out = []
    for b in blocks:
        if b.kind == "p":
            out.append({"type": "para", "text": b.text})
        elif b.kind == "pi":
            out.append({"type": "para", "text": b.text, "italic": True})
        elif b.kind == "label":
            out.append({"type": "label", "text": b.text})
        elif b.kind == "quote":
            out.append({"type": "quote", "text": b.text})
        elif b.kind == "ul":
            out.append({"type": "bullets", "items": [it["text"] if isinstance(it, dict) else it for it in b.items]})
        elif b.kind == "ol":
            out.append({"type": "numbered", "items": b.items, "start": b.level or 1})
        elif b.kind == "checks":
            out.append({"type": "checks", "items": b.items})
        elif b.kind == "h4":
            out.append({"type": "label", "text": b.text})
        elif b.kind == "h3":
            out.append({"type": "subsection", "title": b.text})
        elif b.kind == "table":
            out.append({"type": "table", "header": b.table["header"], "rows": b.table["rows"],
                        **({"kind": b.directive} if b.directive else {})})
        elif b.kind == "hr":
            continue
    return out


def section_map(blocks, level="h2"):
    """Group tokens under their headings: returns list of (title, [blocks])."""
    sections, current, buf = [], None, []
    for b in blocks:
        if b.kind == level:
            if current is not None or buf:
                sections.append((current, buf))
            current, buf = b.text, []
        else:
            buf.append(b)
    if current is not None or buf:
        sections.append((current, buf))
    return sections


def find_section(sections, *names):
    """Case-insensitive lookup by heading text (prefix match)."""
    want = [n.lower() for n in names]
    for title, blocks in sections:
        if title and any(title.lower().startswith(w) for w in want):
            return blocks
    return None


def first_table(blocks):
    for b in blocks:
        if b.kind == "table":
            return b.table
    return None


def list_items(blocks):
    items = []
    for b in blocks:
        if b.kind in ("ul", "ol"):
            items.extend(it["text"] if isinstance(it, dict) else it for it in b.items)
    return items


def paragraphs(blocks):
    return [b.text for b in blocks if b.kind in ("p", "pi")]

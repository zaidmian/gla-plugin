"""Markdown -> course_outline spec. Conventions: references/course_outline_schema.md.

    # <Course Title>, Grade <n> (<CODE>)      the H1; CODE drives the footer
    | | | + |---|---| + | **Key** | value |   first 2-col table = metadata grid
    ## Section / ### Subsection                maroon bar / blush sub-bar
    pipe tables, "- " bullets, *italic line*   table / bullets / italic para
    a paragraph containing ____ under Acknowledgement -> the signature block
"""

import os
import re

from mdparse import (
    blocks_to_spec_blocks, section_map, split_front_matter, strip_inline, tokenize,
)

_CODE_RX = re.compile(r"\(([A-Z]{3}[0-9][A-Z0-9])\)\s*$")
_FILE_CODE_RX = re.compile(r"([A-Z]{3}[0-9][A-Z0-9])")
_CONNECTIONS_RX = re.compile(r"^Curriculum Connections:", re.I)


def _own_paragraph(text):
    """A 'Curriculum Connections:' line that closes a unit description is its
    own paragraph even when the author wrote it directly under the prose."""
    out, prev = [], ""
    for line in text.splitlines():
        if _CONNECTIONS_RX.match(line.strip()) and prev.strip():
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def _code_from(title, path, front):
    if front.get("code"):
        return str(front["code"])
    m = _CODE_RX.search(title or "")
    if m:
        return m.group(1)
    m = _FILE_CODE_RX.search(os.path.basename(path or ""))
    return m.group(1) if m else ""


def _metadata(table):
    data = {}
    for row in table["rows"]:
        if not any(c.strip() for c in row):
            continue
        key = strip_inline(row[0]).rstrip(":").strip()
        if not key:
            continue
        data[key] = strip_inline(" ".join(row[1:])) if len(row) > 1 else ""
    return data


def _section_blocks(title, tokens):
    blocks = blocks_to_spec_blocks(tokens)
    if (title or "").strip().lower() != "acknowledgement":
        return blocks
    out, signed = [], False
    for b in blocks:
        if b.get("type") == "para" and "____" in b.get("text", ""):
            if not signed:
                out.append({"type": "signature"})
                signed = True
            continue
        out.append(b)
    return out


def parse(text, path=None):
    front, body = split_front_matter(text)
    tokens = tokenize(_own_paragraph(body))

    title = ""
    rest = list(tokens)
    for i, b in enumerate(rest):
        if b.kind == "h1":
            title = b.text
            rest = rest[:i] + rest[i + 1:]
            break

    metadata = {}
    preamble, sections = [], []
    for name, blocks in section_map(rest):
        if name is None:
            preamble = blocks
        else:
            sections.append((name, blocks))
    for b in preamble:
        if b.kind == "table" and not metadata:
            metadata = _metadata(b.table)
    stray = [b for b in preamble if b.kind not in ("table", "hr")]

    out_sections = []
    for name, blocks in sections:
        out_sections.append({"kind": "section", "title": name,
                             "blocks": _section_blocks(name, blocks)})
    if stray and out_sections:
        out_sections[0]["blocks"] = blocks_to_spec_blocks(stray) + out_sections[0]["blocks"]

    spec = {
        "title": title or metadata.get("Course Title", ""),
        "code": _code_from(title, path, front) or metadata.get("Course Code", ""),
        "metadata": metadata,
        "sections": out_sections,
    }
    for key in ("school", "footer"):
        if front.get(key):
            spec[key] = front[key]
    return spec

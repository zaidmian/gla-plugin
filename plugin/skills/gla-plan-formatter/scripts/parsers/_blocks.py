"""
Shared token -> block conversion for the lesson and unit Markdown parsers.

Extends mdparse.blocks_to_spec_blocks with the conventions documented in
references/markdown_conventions.md:

  * a trailing attribute group on a paragraph line, e.g.
        https://example.org {color=8C6D2A}
        Some emphasised sentence. {bold}
    keys: bold, italic, color=HEX, size=N
  * a line wholly wrapped in __double underscores__ is a bold paragraph
    (a line wholly wrapped in **stars** is a label, per the tokeniser)
  * a list whose every item is wholly **bold** becomes a bold list
  * '#### Heading' inside a cell becomes a label block, text verbatim
"""

import re

_ATTR_RX = re.compile(r"\s+\{([^{}]+)\}\s*$")
_HEX_RX = re.compile(r"[0-9A-Fa-f]{6}")
_ATTR_KEYS = ("bold", "italic", "color", "size")
_BOLD_STARS_RX = re.compile(r"\*\*([^*]+)\*\*")
_BOLD_UNDER_RX = re.compile(r"__(.+)__", re.S)
_ITALIC_RX = re.compile(r"\*([^*].*)\*", re.S)


def split_attrs(text):
    """Return (text without a trailing {..} group, attrs dict).

    The group is only honoured when every token is a known attribute, so a
    paragraph that happens to end in braces is left alone.
    """
    text = text or ""
    m = _ATTR_RX.search(text)
    if not m:
        return text, {}
    attrs = {}
    for tok in m.group(1).split():
        k, _, v = tok.partition("=")
        k = k.strip().lower()
        v = v.strip()
        if k not in _ATTR_KEYS:
            return text, {}
        if k in ("bold", "italic"):
            attrs[k] = v.lower() not in ("false", "0", "no") if v else True
        elif k == "color":
            v = v.lstrip("#")
            if not _HEX_RX.fullmatch(v):
                return text, {}
            attrs[k] = v
        elif k == "size":
            try:
                attrs[k] = float(v) if "." in v else int(v)
            except ValueError:
                return text, {}
    return text[:m.start()].rstrip(), attrs


def para_block(text, italic=False):
    """Build a para block from one paragraph line (attributes and wrappers applied)."""
    text, attrs = split_attrs(text)
    bold = False
    m = _BOLD_UNDER_RX.fullmatch(text)
    if m:
        text, bold = m.group(1).strip(), True
    else:
        m = _BOLD_STARS_RX.fullmatch(text)
        if m:
            text, bold = m.group(1).strip(), True
        else:
            m = _ITALIC_RX.fullmatch(text)
            if m and not text.startswith("**"):
                text, italic = m.group(1).strip(), True
    block = {"type": "para", "text": text}
    if bold or attrs.get("bold"):
        block["bold"] = True
    if italic or attrs.get("italic"):
        block["italic"] = True
    if "color" in attrs:
        block["color"] = attrs["color"]
    if "size" in attrs:
        block["size"] = attrs["size"]
    return block


def is_plain_para(tok):
    """True when a 'p' token carries no attributes or bold/italic wrapper."""
    if tok.kind != "p":
        return False
    return para_block(tok.text) == {"type": "para", "text": tok.text}


def _item_texts(items):
    return [it["text"] if isinstance(it, dict) else it for it in items]


def _unbold_items(items):
    texts = _item_texts(items)
    if texts and all(_BOLD_STARS_RX.fullmatch(t) for t in texts):
        return [t[2:-2].strip() for t in texts], True
    return texts, False


def spec_blocks(tokens):
    """Convert cell-level tokens into the block vocabulary (references/blocks.md)."""
    out = []
    for b in tokens:
        if b.kind == "p":
            out.append(para_block(b.text))
        elif b.kind == "pi":
            out.append(para_block(b.text, italic=True))
        elif b.kind == "label":
            out.append({"type": "label", "text": b.text})
        elif b.kind in ("h1", "h2", "h3", "h4"):
            out.append({"type": "label", "text": b.text})
        elif b.kind == "quote":
            out.append({"type": "quote", "text": b.text})
        elif b.kind == "ul":
            items, bold = _unbold_items(b.items)
            blk = {"type": "bullets", "items": items}
            if bold:
                blk["bold"] = True
            out.append(blk)
        elif b.kind == "ol":
            items, bold = _unbold_items(b.items)
            blk = {"type": "numbered", "items": items}
            if bold:
                blk["bold"] = True
            if b.level and b.level != 1:
                blk["start"] = b.level
            out.append(blk)
        elif b.kind == "checks":
            out.append({"type": "checks", "items": [[t, bool(c)] for t, c in b.items]})
        elif b.kind == "hr":
            out.append({"type": "rule"})
        elif b.kind == "table":
            raise ValueError("a table cannot sit inside a cell; move it to section level "
                             "(unit) or express it with labels and bullets")
    return out


def string_or_blocks(tokens):
    """One plain paragraph -> string; anything else -> block list; nothing -> ""
    (the caller records the gap under spec["review"]["gaps"])."""
    if not tokens:
        return ""
    if len(tokens) == 1 and is_plain_para(tokens[0]):
        return tokens[0].text
    return spec_blocks(tokens)


def as_str(v):
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)

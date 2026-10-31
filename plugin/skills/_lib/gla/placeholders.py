"""Template placeholders left in authored files.

The Standards templates and scaffold_week.py mark what the author still has to
write as <...> (`<codes>`, `<marks>`, `<goal>`, `<one sentence>`) and a slot
as U_.W_.D_. Code, inline code and HTML comments are skipped, and so are HTML
tags such as <br> or <span class="x">.
"""
import re

HTML_TAGS = {
    "a", "b", "body", "br", "button", "canvas", "center", "code", "del", "details", "div", "em", "figcaption",
    "figure", "font", "h1", "h2", "h3", "h4", "h5", "h6", "head", "hr", "html", "i", "iframe", "img", "input",
    "ins", "kbd", "label", "li", "link", "mark", "meta", "ol", "option", "p", "pre", "s", "script", "section",
    "select", "small", "span", "strong", "style", "sub", "summary", "sup", "svg", "table", "tbody", "td", "th",
    "thead", "title", "tr", "u", "ul", "video", "audio",
}
ANGLE = re.compile(r"(?<![\w`])<([^\s<>/!=][^<>\n]{0,80})>")
SLOT = re.compile(r"\bU_\.W_\.D_\b|\bU_\.W_\b")
FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.S | re.M)
INLINE = re.compile(r"`[^`\n]*`")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def _is_tag(inner):
    if "=" in inner or '"' in inner:
        return True
    m = re.match(r"[A-Za-z][\w-]*", inner)
    return bool(m and m.group(0).lower() in HTML_TAGS and inner.strip().lower() == m.group(0).lower())


def find(text, markdown=True):
    """The placeholders in text, in order, without repeats. markdown=False skips
    the fence and inline-code stripping (for YAML values)."""
    if markdown:
        text = COMMENT.sub("", text)
        text = FENCE.sub("", text)
        text = INLINE.sub("", text)
    out = []
    for m in ANGLE.finditer(text):
        if not _is_tag(m.group(1)) and m.group(0) not in out:
            out.append(m.group(0))
    for m in SLOT.finditer(text):
        if m.group(0) not in out:
            out.append(m.group(0))
    return out

#!/usr/bin/env python3
"""
md2html.py — render a house-dialect markdown file to a self-contained,
GLASS-styled HTML page for on-screen reading.

    python3 md2html.py SOURCE.md OUT.html

Reuses the shared parser from md2docx.py (same restricted
markdown dialect: headings, the bold-label header block, paragraphs, bullet /
numbered / lettered / checkbox lists, pipe tables, fenced code, blockquotes,
horizontal rules, inline code / bold / italic / links), so anything the docx
converter accepts renders here too. Stdlib only.

Library use (what build_calendar.py does):

    from md2html import render
    render(md_path, out_path, title=None, source_href=None, link_rewriter=None)

`link_rewriter(target)` maps a link target found inside the markdown to the
href the page should use (e.g. another .md file's rendered twin); return None
to keep the original.
"""
import base64
import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # md2docx.py sits beside this file
from md2docx import IMAGE_TYPES, parse_blocks, parse_inline  # noqa: E402

CSS = """
:root {
  --page:#f7f8fa; --surface:#fff; --surface-alt:#eff1f4; --edge:#e3e6eb; --edge-strong:#d2d6dd;
  --heading:#171a1f; --body:#2c313a; --muted:#626977; --faint:#858c99;
  --accent:#0e7c87; --accent-hover:#0b626b; --primary-100:#c3e5e8; --primary-700:#094c53;
  --tile-primary-bg:#e6f4f5; --tile-primary-fg:#0b626b; --warning-bg:#fbefd6; --warning-fg:#8f5e13;
  --code-bg:#171a1f; --code-fg:#eef1f5; --shadow-md:0 4px 12px rgba(23,26,31,.08),0 1px 3px rgba(23,26,31,.05);
}
* { box-sizing:border-box; }
html { color-scheme:light; }
body { margin:0; background:var(--page); color:var(--body); font:16px/1.55 'Public Sans',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif; }
.top { position:sticky; top:0; background:var(--surface); border-bottom:1px solid var(--edge); font-size:13px; color:var(--muted); }
.top div { max-width:860px; margin:0 auto; padding:7px 24px; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
.top a { color:var(--accent); text-decoration:none; }
.top a:hover { text-decoration:underline; }
.top .path { font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace; font-size:12px; color:var(--faint); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:60%; }
.top button { margin-left:auto; border:1px solid var(--edge-strong); background:var(--surface); border-radius:6px; padding:3px 9px; font:inherit; font-size:12px; cursor:pointer; color:var(--body); }
article { max-width:860px; margin:0 auto; padding:28px 24px 90px; background:var(--surface); min-height:100vh; box-shadow:var(--shadow-md); }
h1 { font-size:30px; line-height:1.2; color:var(--heading); margin:0 0 14px; letter-spacing:-.01em; }
h2 { font-size:22px; color:var(--primary-700); margin:34px 0 10px; padding-bottom:4px; border-bottom:2px solid var(--primary-100); }
h3 { font-size:17px; color:var(--heading); margin:24px 0 6px; }
h4, h5, h6 { font-size:15px; color:var(--muted); margin:18px 0 4px; text-transform:uppercase; letter-spacing:.04em; }
p { margin:0 0 12px; }
a { color:var(--accent); }
.meta { background:var(--tile-primary-bg); border-left:4px solid var(--accent); border-radius:0 8px 8px 0; padding:10px 14px; margin:0 0 18px; font-size:14.5px; color:var(--tile-primary-fg); }
.meta div { margin:2px 0; }
code { font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.9em; background:var(--surface-alt); border:1px solid var(--edge); border-radius:4px; padding:0 4px; color:var(--heading); }
pre { background:var(--code-bg); color:var(--code-fg); border-radius:10px; padding:14px 16px; overflow-x:auto; font-size:13.5px; line-height:1.5; margin:0 0 16px; }
pre code { background:none; border:none; padding:0; color:inherit; font-size:inherit; }
ul, ol { margin:0 0 12px; padding-left:26px; }
li { margin:3px 0; }
li > ul, li > ol { margin:3px 0 0; }
ul.check { list-style:none; padding-left:6px; }
ul.check li::before { content:attr(data-mark); display:inline-block; width:22px; color:var(--accent); }
ol.alpha { list-style:lower-alpha; }
li .box { color:var(--accent); margin-right:4px; }
table { border-collapse:collapse; width:100%; margin:0 0 18px; font-size:14.5px; }
th, td { border:1px solid var(--edge-strong); padding:6px 9px; vertical-align:top; }
th { background:var(--surface-alt); text-align:left; color:var(--heading); }
tr:nth-child(even) td { background:#fbfbfc; }
blockquote { margin:0 0 18px; padding:12px 16px; background:var(--warning-bg); border-left:4px solid var(--warning-fg); border-radius:0 8px 8px 0; color:#4a3a14; }
blockquote h3 { margin-top:0; color:var(--warning-fg); }
blockquote p:last-child { margin-bottom:0; }
hr { border:none; border-top:1px solid var(--edge-strong); margin:26px 0; }
@media print { .top { display:none; } article { box-shadow:none; padding:0; max-width:none; } pre { white-space:pre-wrap; } }
"""


def esc(s):
    return html.escape(s, quote=True)


def runs_html(runs, link_rewriter=None):
    out = []
    for r in runs:
        t = esc(r["text"])
        if r.get("code"):
            t = f"<code>{t}</code>"
        if r.get("bold"):
            t = f"<strong>{t}</strong>"
        if r.get("italic"):
            t = f"<em>{t}</em>"
        if r.get("link"):
            href = r["link"]
            if link_rewriter:
                href = link_rewriter(href) or href
            ext = href.startswith(("http://", "https://"))
            t = f'<a href="{esc(href)}"{" target=_blank rel=noopener" if ext else ""}>{t}</a>'
        out.append(t)
    return "".join(out)


def inline(text, link_rewriter=None):
    return runs_html(parse_inline(text), link_rewriter)


def image_html(b, base):
    """An image from the document's images/ folder, inlined so the page stays one file."""
    path = Path(base or ".") / b["src"]
    mime = IMAGE_TYPES.get(path.suffix.lower())
    if not mime or not path.is_file():
        return '<p class="missing-image">[image not found: %s]</p>' % esc(b["src"])
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return '<p class="image"><img src="data:%s;base64,%s" alt="%s" style="max-width:100%%"></p>' % (mime, data, esc(b["alt"]))


def render_blocks(blocks, link_rewriter=None, base=None):
    out = []
    i = 0
    n = len(blocks)
    while i < n:
        b = blocks[i]
        t = b["type"]
        if t == "heading":
            lvl = min(b["level"], 6)
            out.append(f"<h{lvl}>{inline(b['text'], link_rewriter)}</h{lvl}>")
        elif t == "meta":
            out.append('<div class="meta">' + "".join(f"<div>{inline(l, link_rewriter)}</div>" for l in b["lines"]) + "</div>")
        elif t == "para":
            out.append(f"<p>{inline(b['text'], link_rewriter)}</p>")
        elif t == "hr":
            out.append("<hr>")
        elif t == "code":
            out.append("<pre><code>" + esc("\n".join(b["lines"])) + "</code></pre>")
        elif t == "quote":
            out.append("<blockquote>" + render_blocks(b["blocks"], link_rewriter, base) + "</blockquote>")
        elif t == "image":
            out.append(image_html(b, base))
        elif t == "table":
            rows = b["rows"]
            aligns = b["aligns"]
            def cell(tag, ci, txt):
                a = aligns[ci] if ci < len(aligns) else "left"
                style = f' style="text-align:{a}"' if a != "left" else ""
                return f"<{tag}{style}>{inline(txt, link_rewriter)}</{tag}>"
            head = "<tr>" + "".join(cell("th", ci, c) for ci, c in enumerate(rows[0])) + "</tr>"
            body = "".join("<tr>" + "".join(cell("td", ci, c) for ci, c in enumerate(r)) + "</tr>" for r in rows[1:])
            out.append(f"<table><thead>{head}</thead><tbody>{body}</tbody></table>")
        elif t == "li":
            # gather the run of consecutive list items and nest by level
            items = []
            while i < n and blocks[i]["type"] == "li":
                items.append(blocks[i])
                i += 1
            out.append(render_list(items, link_rewriter))
            continue
        i += 1
    return "\n".join(out)


def list_tag(marker):
    if marker in ("☐", "☑"):
        return "ul", ' class="check"'
    if marker.endswith(")"):
        return "ol", ' class="alpha"'
    if marker.endswith("."):
        return "ol", ""
    return "ul", ""


def render_list(items, link_rewriter):
    """items: flat li blocks with level; build nested lists."""
    def build(start, level):
        tag, cls = list_tag(items[start]["marker"])
        parts = [f"<{tag}{cls}>"]
        j = start
        while j < len(items) and items[j]["level"] >= level:
            it = items[j]
            if it["level"] > level:
                sub, j = build(j, it["level"])
                parts[-1] = parts[-1][:-5] + sub + "</li>" if parts[-1].endswith("</li>") else parts[-1] + sub
                continue
            mark = f' data-mark="{it["marker"]}"' if it["marker"] in ("☐", "☑") else ""
            val = ""
            if tag == "ol" and it["marker"][:-1].isdigit():
                val = f' value="{it["marker"][:-1]}"'
            text = it["text"]
            prefix = ""
            if tag == "ol" and text.startswith(("[ ]", "[x]", "[X]")):
                # numbered checklist steps: the shared parser only turns bullets into
                # checkbox items, so render the box here
                prefix = '<span class="box">' + ("☐" if text.startswith("[ ]") else "☑") + "</span> "
                text = text[3:].strip()
            parts.append(f"<li{mark}{val}>{prefix}{inline(text, link_rewriter)}</li>")
            j += 1
        parts.append(f"</{tag}>")
        return "".join(parts), j
    # a run can open deeper than it continues (sub-items resumed after a fenced
    # code block inside a list item), so keep building until every item is used
    parts, j = [], 0
    while j < len(items):
        html_, j = build(j, items[j]["level"])
        parts.append(html_)
    return "".join(parts)


def render(md_path, out_path, title=None, source_href=None, link_rewriter=None, crumbs=None):
    text = Path(md_path).read_text(encoding="utf-8")
    blocks = parse_blocks(text.split("\n"))
    if title is None:
        title = next((b["text"] for b in blocks if b["type"] == "heading" and b["level"] == 1), Path(md_path).stem)
    body = render_blocks(blocks, link_rewriter, Path(md_path).parent)
    top = []
    if crumbs:
        top.append(" / ".join(esc(c) for c in crumbs))
    top.append(f'<span class="path" title="{esc(str(md_path))}">{esc(Path(md_path).name)}</span>')
    if source_href:
        top.append(f'<a href="{esc(source_href)}">raw .md</a>')
    top.append(f'<button onclick="navigator.clipboard.writeText({esc(repr(str(md_path)))}).then(()=>{{this.textContent=\'copied\';setTimeout(()=>this.textContent=\'copy path\',900)}})">copy path</button>')
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><div class="top"><div>{"".join(top)}</div></div>
<article>
{body}
</article></body></html>
"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = render(argv[0], argv[1], source_href=os.path.relpath(argv[0], os.path.dirname(os.path.abspath(argv[1]))))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

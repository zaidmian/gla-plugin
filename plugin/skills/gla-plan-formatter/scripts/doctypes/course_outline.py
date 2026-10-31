"""Course outline (19-section GLA structure). Schema: references/course_outline_schema.md.

An outline is a title block, a compact metadata grid, then a run of sections.
Each section is a maroon section bar followed by paragraphs, bullets, blush
sub-bars, short-row tables, and (in Acknowledgement) the signature block.
Paragraph bars are right here: what follows a bar is short, so keepNext on the
bar paragraph is enough to hold it to its content.
"""

from gla_docx import (
    CONTENT_WIN, MAROON, SCHOOL_TITLE, SpecError, _keep_with_next,
    add_row, body_para, bullet, derive_badge, finish, make_table, masthead,
    footer_text, metadata_grid, new_document, render_blocks, render_table, require,
    section_bar, signature_block, sub_bar,
)

TITLE = "COURSE OUTLINE"

# Two label/value pairs per row; long fields span the full width. Ported from
# the v1 renderer so an outline keeps the same eight-row grid.
META_FULL = ("Prerequisite", "Department", "Curriculum Document")
META_LAYOUT = [
    ("Course Title", "Course Code"),
    ("Course Type", "Grade"),
    ("Credit Value", "Corequisite"),
    ("Prerequisite", None),
    ("Department", None),
    ("Curriculum Document", None),
    ("Developed By", "Date Developed"),
    ("Revised By", "Date Revised"),
]

SIGNATORIES = ["Student's Name", "Parent / Guardian's Name"]


def _cell_fallback(doc, blocks):
    """Block kinds with no document-level helper (checks, quote) render inside a
    single borderless full-width cell so the shared cell renderer does the work."""
    t = make_table(doc, [CONTENT_WIN])
    row = add_row(t, borders=False)
    render_blocks(row.cells[0], blocks)
    return t


def render_section_blocks(doc, blocks):
    blocks = list(blocks or [])
    for idx, b in enumerate(blocks):
        if isinstance(b, str):
            b = {"type": "para", "text": b}
        t = b.get("type", "para")
        nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
        next_is_signature = isinstance(nxt, dict) and nxt.get("type") == "signature"
        if t == "para":
            # the acknowledgement statement stays with the signature lines below it
            body_para(doc, b.get("text", ""), italic=b.get("italic", False),
                      bold=b.get("bold", False), keep_next=next_is_signature)
        elif t == "label":
            body_para(doc, b.get("text", ""), bold=True, color=MAROON, keep_next=True)
        elif t == "subsection":
            sub_bar(doc, b.get("title") or b.get("text", ""))
        elif t == "bullets":
            for item in b.get("items", []):
                bullet(doc, item, bold=b.get("bold", False))
        elif t == "numbered":
            start = b.get("start", 1)
            for i, item in enumerate(b.get("items", [])):
                bullet(doc, item, numbered=start + i, bold=b.get("bold", False))
        elif t == "table":
            render_table(doc, b.get("header"), b.get("rows", []),
                         widths=b.get("widths"), label_first=b.get("label_first"))
        elif t == "signature":
            signature_block(doc, b.get("signatories") or SIGNATORIES)
            # signature_block opens with a spacer paragraph; binding it to the
            # table completes the keepNext chain from the statement above, so
            # the statement and both signature rows move to a new page together.
            _keep_with_next(doc.paragraphs[-1])
        elif t in ("checks", "quote"):
            _cell_fallback(doc, [b])
        else:
            raise SpecError(f"course_outline: unknown block type '{t}'")


def build(spec, out_path):
    require(spec, "title", "sections", where="course_outline")
    doc = new_document(spec.get("school"))
    meta = spec.get("metadata") or {}
    rh = spec.get("context", {}) or {}
    code = spec.get("code") or meta.get("Course Code") or ""
    ctx_bits = [x for x in (meta.get("Department"), meta.get("Course Type")) if x]
    masthead(doc, title=TITLE, subtitle=spec.get("title"),
             course_line_text=rh.get("course_line")
             or (f"{code}: {meta['Course Title']}" if meta.get("Course Title") else code or None),
             context_line=rh.get("context_line") or "  |  ".join(ctx_bits),
             badge=spec.get("badge") or derive_badge(code, grade=meta.get("Grade")), code=code)

    if meta:
        metadata_grid(doc, meta, META_LAYOUT, full_keys=META_FULL)

    for sec in spec.get("sections", []):
        kind = sec.get("kind", "section")
        if kind != "section":
            raise SpecError(f"course_outline: unknown section kind '{kind}'")
        section_bar(doc, sec.get("title") or "")
        render_section_blocks(doc, sec.get("blocks", []))

    code = spec.get("code") or meta.get("Course Code") or ""
    footer = footer_text(SCHOOL_TITLE, "Course Outline", code)
    return finish(doc, spec, "course_outline", out_path, default_footer=footer)

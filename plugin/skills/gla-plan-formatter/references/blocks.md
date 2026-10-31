# Blocks: the shared content vocabulary

Every document type fills its cells and columns with the same small set of
content blocks. They are rendered by `render_blocks` in `scripts/gla_docx.py`
and written by hand in a JSON spec or produced from Markdown by
`scripts/md2spec.py` (see `references/markdown_conventions.md`). Where a schema
says "blocks", it means a list of the objects below.

## Bare-string shorthand

A bare string anywhere a block is expected is a plain paragraph:

```json
"blocks": ["Students read the excerpt aloud.", {"type": "bullets", "items": ["..."]}]
```

is the same as `{"type": "para", "text": "Students read the excerpt aloud."}`.

## Block types

| type       | fields                                   | renders as |
|------------|------------------------------------------|------------|
| `para`     | `text`, `bold?`, `italic?`, `color?`, `size?` | one paragraph in the body face; `bold` and `italic` set the base weight and slant for the whole paragraph |
| `label`    | `text`, `size?`                          | bold maroon sub-heading line, kept with the paragraph that follows it |
| `quote`    | `text`, `size?`                          | italic maroon line (student prompts, quotations, questions to pose) |
| `bullets`  | `items` (list of strings), `bold?`, `size?` | bulleted list, one item per entry |
| `numbered` | `items` (list of strings), `bold?`, `size?`, `start?` | numbered list; `start` is the first number (default 1) |
| `checks`   | `items` (list of `[text, bool]`), `size?` | checkbox list, a filled box for `true` and an empty box for `false`; a bare string item counts as checked |
| `rule`     | (none)                                   | a thin horizontal line with space above it (signature or write-in lines) |

Field notes:

- `text` and list items accept inline `**bold**` and `*italic*` runs; the
  markup is converted to Word runs, so it never prints literally.
- `color` is a six-digit hex string without `#`. Two values recur in the
  examples: `8C6D2A` (the gold used for links) and `888888` (muted grey for a
  placeholder the teacher will replace).
- `size` is a point size and overrides the body size for that block only.
  Leave it out unless a cell is visibly overflowing.
- `bold: false` and `italic: false` are the defaults; omit them.

## Where blocks appear

- Lesson plan: `curriculum.overall` and `curriculum.specific` (a string or a
  block list), `materials.teacher_extra` and `materials.student_extra`, and
  each `sequence[].left.blocks` / `sequence[].right.blocks`.
- Unit plan: `sections[].blocks` of every `labeled` section. The `variety`
  section is built from `label` + `checks` pairs internally.
- The other document types name their block lists in their own schema files.

Tables are not blocks. A table inside a cell is rejected by `render_blocks`;
the unit type carries its tables as sections of their own (`expectations`,
`achievement`, `lesson_table`, `reflection`).

## Gaps and review

No marker text is written into a document, because a marked document could be
submitted by accident. Two things replace the old markers:

- A required field with no source and no consent renders **blank**. The builders
  print an empty cell or line; the author leaves the value `""` or the list `[]`
  and records the gap as `{"section": ..., "field": ...}` under
  `spec["review"]["gaps"]`. Never invent content to fill it.
- Content drafted or derived from a related document (a course outline, a
  previous unit, the curriculum, a rule) is written plainly and recorded for
  review: either as an item `{"section": ..., "text": ..., "risk": "high"?}`
  under `spec["review"]["items"]`, or as a `"review": "..."` string on the
  section, block, or row that carries it. `risk: high` is reserved for
  statements of fact about the teacher, the school, or the students.

Every builder ignores `review` keys when rendering. `build_plan.py --review
PATH` (or `scripts/review.py`) collects them into the teacher's review list,
and `scripts/check_output.py` proves the finished .docx and PDF carry no marker
text and no em dash.

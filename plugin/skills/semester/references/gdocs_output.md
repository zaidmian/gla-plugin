# Google Docs handouts: what convert_instance.py produces

Reference for maintenance and for answering "why does the handout look like this". A normal run does not need it; `convert_instance.py` and `md2docx.py` implement all of it. Colours and fonts are constants at the top of `md2docx.py`; change them there (a shared change: CHANGELOG it), never per document.

## What gets converted (and what never does)

The course's `gdocs_manifest.yaml` (or the path in `course.yaml` `gdocs_manifest`) is the authority. Teacher-only files are never converted regardless of the manifest: `*_KEY.md`, `*_MARKING.md`, `marking_notes.md`, `rubric.md`/`rubric.csv` (rubrics are gc-rubric's job), lesson and activity day files, week plans, overviews, and HTML slide decks. For a teacher-side document on request, convert that one file directly with `md2docx.py` and say it is not a student handout.

## Styling contract (what the output looks like)

- Body Roboto 11pt; code (inline + blocks) Roboto Mono; page Letter, 1"
  margins.
- md `#` → Title, `##` → Heading 1 (GLA maroon), `###` → Heading 2, `####` →
  Heading 3, so the Google Docs outline sidebar works.
- The header block renders as a shaded box with a maroon left bar. For the
  student copy it is rewritten (see below), not shown verbatim.
- Tables: bold shaded header row, light grey borders, full width.
- Fenced code: shaded grey box, spaces preserved (ASCII diagrams survive).
- Blockquotes render as a gold-tinted box.
- Lists keep their **literal source numbering**. `- [ ]` renders as ☐.
- Colors/fonts are constants at the top of the shared `md2docx.py`; retheme
  there (a shared change; CHANGELOG it), never per-document.

## Student-copy transforms

The .docx is handed to students, so `md2docx.py` rewrites the master markdown
as it converts (the calendar page's HTML twins keep the master verbatim):

- **Dates, not slot IDs.** `U1.W2.D1` and the like become the calendar date
  (`September 8, 2026`) everywhere in the document. The map comes from the
  instance's `calendar.yaml`, so slot substitution only happens on an instance
  run through `convert_instance.py`, not a bare `md2docx.py SOURCE.md` call.
- **The top box** shows a fill-in `Name:` line (exercises, assignments, and
  tests), the `Due:` date, and `Marks:`. The slot IDs, the type, and the
  expectation codes are dropped (they mean nothing to a student).
- **References read as titles, in italics.** `` `REF_Hardware_Terms.md` ``
  becomes *Reference: Hardware Terms* (the referenced file's H1, italicised so
  it stays distinct), resolved beside the source file.
- **Teacher content is removed**: the "Running this class with a substitute"
  box, the "How this is marked" section (covered once at the start of the
  semester, identical for every exercise), and any sentence that points a
  student at a teacher-only file (`marking_notes`, `rubric`, `*_KEY`,
  `*_MARKING`).
- **Em-dashes become commas** (a colon in a heading), matching the house prose
  rule. Only running prose is touched; em-dashes inside fenced code blocks are
  left alone (rewriting code is unsafe). The lasting fix is cleaning the master
  source and the Style Guide so they stop being authored in.
- **A trailing horizontal rule is dropped** (usually the `---` that sat above
  the removed substitute box).
- **A footer** on every page reads `Page X of Y` (PAGE / NUMPAGES fields).
- **The `Name:` line** is a long fill-in rule.

### Test papers

A manifest rule carrying `doc_kind: test` turns on a layout meant for a paper a
student writes on. Only the unit `test.md` rule sets it; review sheets,
reference sheets, exercises, and assignments are untouched.

- **The `Structure` section goes.** Both forms: the `## Structure` heading of
  `Test_Template.md`, and the inline `**Structure:** Part A, 16 multiple
  choice ...` paragraph. It is teacher planning, not student instruction.
- **The `### Companion files` section goes**, whole. The key, the coverage
  table, and the review sheet are none of a student's business on test day.
- **Answers left in the teacher copy are stripped**: the bolding on a correct
  multiple-choice option, whole lines leading with `**Answer:**`, `**Error
  (1):**`, `**Fix (1):**`, `**Output:**`, `**Model answer:**`, `**Accept:**` or
  `**Marking:**`, and the bolded cells of a trace table. This is a safety net,
  not a licence: answers belong in `test_KEY.md`, and a `test.md` that needs
  the net is a source to fix.
- **The option letter is the marker.** `- A. RAM` renders as `A.` followed by
  the option, never as a bullet plus a letter.
- **Short options lay out in columns**, using a borderless table so the letters
  align without a grid appearing on the paper. Four across when the longest
  option is at most `MC_COL4_MAX` printed characters (16), two across when it
  is at most `MC_COL2_MAX` (36), otherwise the plain vertical list. Both
  constants are at the top of `md2docx.py`. Author one option per source line:
  an option wrapped onto a second line breaks the group and falls back to the
  vertical list.
- **Questions get air.** 13pt above each numbered question and each Part B
  `**B1.**` paragraph, with the options tightened under it, so the paper reads
  as grouped questions rather than a wall.

A single-file run gets the same layout with `--kind=test`.

## Limitations

- Images: a line holding only `![alt](images/file.png)` becomes a centred
  picture scaled to the page (PNG, JPEG or GIF). The file must sit beside the
  document, as Style Guide Core §4 requires; a missing file or a web address
  stops that document's conversion with a message. An image inside a paragraph
  or table is not converted.
- Slide decks (`D*_Slides_*.html`) are out of scope, since they are already HTML.
- The converter reads markdown as written per the shared Style Guide Core §11;
  wildly different markdown may need a spot-check of the output.

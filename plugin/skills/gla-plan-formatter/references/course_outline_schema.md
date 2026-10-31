# Course Outline, content JSON schema and Markdown conventions

The spec passed to `build_plan.py --type course_outline`. A complete worked
example is `examples/course_outline/example.json`, produced by the parser from
`examples/course_outline/example.md`; read the pair side by side. The house
structure (the 19 sections and what each contains) is
`Teaching/Standards/templates/Course_Outline_Template.md`. Visual design is not
part of the spec; the shared house style is described in
`references/design_system.md` and the builder only composes its furniture.

Two ways in:

1. **Markdown** (the normal path): `build_plan.py --type course_outline --md outline.md`
   runs `parsers/course_outline.py` and writes `<out>.spec.json` beside the output.
2. **JSON** (canonical): `--spec outline.json` with the shape below.

## JSON spec

```jsonc
{
  "title": "Challenge and Change in Society, Grade 12 (HSB4U)",  // required; subtitle under COURSE OUTLINE
  "code": "HSB4U",                                               // footer; falls back to metadata["Course Code"]
  "school": "GIBRALTAR LEADERSHIP ACADEMY",                      // optional (default)
  "footer": "...",                                               // optional; default is
                                                                 // "Gibraltar Leadership Academy  |  Course Outline  |  <code>"
  "metadata": {                                                  // optional; the compact grid under the title
    "Course Title": "...", "Course Code": "HSB4U", "Course Type": "...",
    "Grade": "12", "Credit Value": "1.0", "Prerequisite": "...",
    "Corequisite": "None", "Department": "...",
    "Curriculum Document": "...",
    "Developed By": "...", "Date Developed": "...",
    "Revised By": "", "Date Revised": ""
  },
  "sections": [                                                  // required; ordered body
    { "kind": "section", "title": "Course Description",
      "blocks": [ {"type": "para", "text": "..."} ] },
    { "kind": "section", "title": "Acknowledgement",
      "blocks": [ {"type": "para", "text": "I have read and understood ..."},
                  {"type": "signature"} ] }
  ]
}
```

### metadata grid
Rendered with `metadata_grid` two pairs per row in this layout:

| left | right |
|---|---|
| Course Title | Course Code |
| Course Type | Grade |
| Credit Value | Corequisite |
| Prerequisite | (full width) |
| Department | (full width) |
| Curriculum Document | (full width) |
| Developed By | Date Developed |
| Revised By | Date Revised |

A row appears when either of its keys is present. Keys outside the layout are
appended as full-width rows, so nothing supplied is dropped. Empty strings
render as blank cells (the Revised pair is normally blank on a first edition).

### sections
Every entry is `{"kind": "section", "title": ..., "blocks": [...]}`. The title
renders as a maroon section bar; the blocks follow in order. Sections carry no
fixed identity, the builder renders whatever order the spec gives, and the
template order is the convention:

Course Description; Overall Curriculum Expectations; Considerations for Program
Planning; Units of Study and Time Allocation; Unit Descriptions; Teaching and
Learning Strategies; Assessment and Evaluation Strategies; Achievement Chart
Categories; Evaluation and Reporting; Learning Skills and Work Habits; Course
Policies; Support for Diverse Learners; Program Planning in (Subject); Required
Materials and Resources; Classroom Expectations; Accessibility; Islamic
Perspective; Important Dates (optional, see below); Acknowledgement.

### blocks
The shared block vocabulary (`references/blocks.md`) plus three outline-specific
types.

| type | fields | renders as |
|---|---|---|
| `para` | `text`, `italic?`, `bold?` | body paragraph; inline `**bold**` and `*italic*` honoured; a paragraph ending in a colon is kept with the block after it |
| `label` | `text` | bold maroon lead line, kept with what follows |
| `bullets` | `items[]` | bullet list |
| `numbered` | `items[]`, `start?` | numbered list |
| `subsection` | `title` | blush sub-bar (an H3) |
| `table` | `header?`, `rows[][]`, `widths?`, `label_first?` | `render_table`: maroon header row when `header` is present; per-column alignment (a non-first column is centred only when every body cell is short); a row whose first cell starts with `Total` is bold on blush; a first column headed Unit, Category, Level, Component or Criteria is washed blush unless `label_first` says otherwise |
| `signature` | `signatories?` | `signature_block`; default signatories are "Student's Name" and "Parent / Guardian's Name"; the paragraph before it is kept on the same page |
| `checks`, `quote` | as in blocks.md | rendered inside a borderless full-width cell |

### Deltas the schema allows for
- **Units table with a Chapters column.** `| Unit | Title | Chapters | Hours |`
  (or `Textbook reference`) is an ordinary table; the width algorithm gives the
  extra column room from content length. The Total row still washes blush.
- **Optional policy sub-sections.** "Obtaining Extra Help" and "Homework" are
  extra `subsection` + `para` pairs under Course Policies alongside "Late and
  Missed Assignments" and "Academic Honesty".
- **Developed / Revised pairs** stay as paired rows in the metadata grid.
  Extra metadata keys (Teacher, Semester) render as full-width rows.
- **Important Dates.** An optional section between Islamic Perspective and
  Acknowledgement: a `| What | When |` table (first day, holidays and PA days,
  last instructional day, exam period) and one closing paragraph pointing to the
  Short and Long Term Plan for evaluation dates. Write dates with "to", not a dash.
- **Hours for Units of Study.** Instance calendars never total 110 hours, so the
  hours column is an allocation, not a measurement: hours in proportion to each
  unit's scheduled class days, course introduction days folded into Unit 1,
  rounded to integers that sum to 110 (adjust the largest unit by one to close
  the sum). The allocation is derived content and is listed in the review file.
- **A pipeline instance `Course_Outline.md`** (the short student-facing outline
  `semester` writes) has a different structure from this template. It
  is a draft-mode source: map its description, unit table, grade calculation,
  class rhythm, policies, and important dates into the sections above, and read
  the nine program-planning considerations and section contents from
  `Standards/templates/Course_Outline_Template.md` and the attendance scale and
  credit rule from `Standards/assessment/growing-success-summary.md`. Do not feed
  it to `--md`.
- **Assessment model.** The 2026 three-bucket final grade (Classroom Work,
  Final Evaluation, Attendance and Participation) and the shared 25/30/20/25
  achievement-chart weighting are the defaults an outline is written to. An
  older 70/30 policy or 35/25/20/20 weighting is a content choice; the builder
  renders whatever the tables say.

## Markdown conventions (what `parsers/course_outline.py` reads)

- Optional front matter (`---` block) may carry `code`, `school`, `footer`.
- `# <Course Title>, Grade <n> (<CODE>)`: the single H1. Becomes the subtitle
  under "COURSE OUTLINE". `<CODE>` in the trailing parentheses drives the footer;
  when absent, the first `AAA0A`-shaped token in the filename is used.
- The **metadata block** is the first pipe table before the first `##`, two
  columns, keys in column 1 (inline `**bold**` on keys is stripped). A
  `| | |` header row with its `|---|---|` separator is allowed and ignored.
- `---` separates the metadata block from the body and is otherwise avoided.
- `## Name` -> section. `### Name` -> `subsection`. `#### Name` -> `label`.
- Standard pipe tables -> `table`. A header row (with a `|---|` line) becomes
  `header`; without one the table has `header: null` and no maroon row.
- `- item` -> `bullets`; `1. item` -> `numbered`. Inline `**bold**` is kept in
  paragraphs, bullets, and cells.
- A line that is wholly italic (`*...*`, not `**...**`) -> `para` with
  `italic: true` (maroon italic lead-in). A line that is wholly bold and ends in
  a colon -> `label`.
- Consecutive lines join into one paragraph, as in Markdown. The exception is
  a `Curriculum Connections:` line closing a unit description: it starts its own
  paragraph even without a blank line before it.
- Under `## Acknowledgement`, the first paragraph containing `____` becomes the
  `signature` block; later `____` paragraphs are dropped. The statement
  paragraph before it is kept on the same page as the signature lines.

Column widths are derived from content length, so no width hints are needed.

## Masthead (shared)

Every document opens with the shared masthead: the maroon course strip with the gold grade badge, then the title block. It is derived from the spec (course code, title, grade, unit or semester) and needs no keys. To override, add `"context": {"course_line": "...", "context_line": "..."}` and `"badge": "Grade 12  |  University Prep"` at the top level.

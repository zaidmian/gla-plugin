# Markdown conventions for GLA plan sources

`scripts/md2spec.py --type TYPE source.md` turns a Markdown file into the JSON
spec that `build_plan.py` renders. The JSON stays canonical; Markdown is the
authoring front end. `scripts/mdparse.py` tokenises every type the same way,
and `scripts/parsers/<type>.py` maps the tokens onto that type's schema. The
worked examples in `examples/<type>/example.md` convert to exactly
`examples/<type>/example.json`, so read the pair for your type before writing.

## Common conventions

### Front matter

A `---` block at the top holds the scalar fields (course, codes, dates, badge,
footer). Keys are `snake_case`; values are plain YAML. Quote any value that
contains `: `, ` #`, or starts with a quote mark or bracket:

```yaml
---
course_code: CLN4U
context_line: "Unit 1: Foundations of Law  |  Lesson 1"
achievement_categories: [Knowledge & Understanding, Thinking, Application]
---
```

`school` and `footer` are accepted by every type and are optional. Double
spaces inside a quoted value are preserved (the house footer uses two spaces
around each `|`).

### Headings become bars

- `# Title` is the document title (lesson) or subtitle line (unit).
- `## Section` is a maroon section bar, or a step banner where the type has
  them. The parsers match section names by case-insensitive prefix, so
  `## Materials & Resources` finds the `Materials` section.
- `### Sub-section` is a sub-bar, a phase heading, or a labeled row depending
  on the type.
- `#### Label` inside a cell is a bold maroon label with the text taken
  verbatim (no colon added).

### Paragraphs and inline markup

- Consecutive lines are one paragraph; a blank line starts a new one.
- Inline `**bold**` and `*italic*` are kept in the text and rendered as runs.
- A line wholly wrapped in `*single stars*` is an italic paragraph.
- A line wholly wrapped in `**double stars**` is a **label**: bold maroon, and
  a trailing colon is added when missing. Use it for lead-ins such as
  `**Task Overview:**`. For a label without a colon use `#### Heading`.
- A line wholly wrapped in `__double underscores__` is a **bold paragraph**
  (a sentence in bold that is not a label).
- A paragraph may end with an attribute group in braces:
  `{bold}`, `{italic}`, `{color=8C6D2A}`, `{size=9}`, or several separated by
  spaces. The group is removed from the text. Braces holding anything else are
  left in the text untouched.

### Lists

- `- item` or `* item` lines are bullets; `1. item` lines are a numbered list
  (the first number sets `start`).
- A list whose every item is wholly `**bold**` becomes a bold list.
- A wrapped item continues on the next line when that line is indented by at
  least two spaces.
- `- [x] item` / `- [ ] item` lines are a checklist; `x` means checked.

### Quotes

`> text` is a quote block (italic maroon). Several `>` lines join into one.

### Tables

Pipe tables with a header row and a `|---|` separator. Cells keep inline
markup. `<br>` inside a cell marks an in-cell line break; parsers that read a
cell as a list split on it (a leading `- ` on each line is tolerated and
stripped). Pipes cannot appear inside cell text. A table is only meaningful
where the type expects one (see the per-type sections); the parser rejects a
table inside a cell.

### Directives

A comment of the form `<!-- gla: name -->` on its own line tags the next table
or list with `name`, which tells the parser which schema shape to build. Names
are lower-case letters and underscores. The unit type uses `expectations`,
`achievement`, `lesson_table`, `reflection`, and `variety`.

### Rules and horizontal lines

A `---` line outside the front matter is ignored at section level. Inside a
cell (lesson phase sides, unit labeled rows) it becomes a `rule` block.

### Gaps and drafted content

No marker text is ever written into a document. A required field the source
does not supply is left empty, and the parser records it under
`spec["review"]["gaps"]`; content filled from a related document is recorded
under `spec["review"]["items"]` or as a `review` string on the section that
carries it. `build_plan.py --review PATH` turns those into the teacher's review
list. See `references/blocks.md`.

## lesson

Parser: `scripts/parsers/lesson.py`. Schema: `references/lesson_schema.md`.
Example: `examples/lesson/example.md`.

Front matter keys: `course_code`, `course` (the banner course line: the code
followed by the full course name), `unit`, `lesson`,
`duration`, `badge`, `context_line`, `achievement_categories` (a list; any of
the four Ontario category names, matched loosely, so `Knowledge` or `K/U` both
tick the first box), and optionally `school` and `footer`.

Body, in this order (sections may be omitted only where the schema marks them
optional; a missing required section produces the marker):

```markdown
# Lesson title

## Curriculum Expectations
### Overall
One paragraph, or several blocks.
### Specific
A1.1 – first expectation.

A1.2 – second expectation.

## Learning Goals
By the end of this lesson, I can:
- goal
- goal

## Success Criteria
- criterion

## Materials
### Teacher
- item
### Student
- item

**Suggested Video (optional enrichment):**
Anything after the bullets becomes the extra blocks under that column.

## Lesson Sequence
### 1. Minds On (10 minutes): Hook & Warm-Up
#### Teacher Actions
Blocks for the left column.
#### Assessment for Learning
Blocks for the right column.

## Differentiation
### ELL Students
- item
### IEP / Accommodation
- item
### Advanced / Extension
- item

## Google Classroom
- item
```

Details:

- `### Overall` / `### Specific` with a single plain paragraph yield a string;
  anything else yields a block list.
- In `## Learning Goals` the first paragraph (or `**bold**` line) before the
  bullets becomes `learning_goals_lead`; the bullets become the list.
- Phase headings follow `N. Phase Name (time): Subtitle`. The number, the
  phase name, an optional parenthesised time, and an optional colon-subtitle
  are read in that order; the phase name is upper-cased for the bar. A heading
  that does not fit the pattern is used whole as the phase text.
- Inside a phase the first `####` is the left column and its label, the second
  is the right column. Any further `####` headings become label blocks inside
  the right column. Content before the first `####` becomes the left column
  with no label.
- Differentiation column names are the `###` headings, in order, and the
  schema expects three. Bullets placed directly under `## Differentiation`
  without a `###` are an error.
- `## Google Classroom` (or `## Connections to Google Classroom`) is optional
  and is emitted only when it has bullets.

## unit

Parser: `scripts/parsers/unit.py`. Schema: `references/unit_schema.md`.
Example: `examples/unit/example.md`.

Front matter carries the overview grid. Either spelling of each key works, the
display name (`Unit Title`) or snake_case (`unit_title`); the parser also
accepts `unit_number`, `days`, `due`, `texts`, and `strands`:

```yaml
course: ENG3U, English, Grade 11, University Preparation
grade: Grade 11
unit_title: "Unit 1: The Power of Storytelling"
unit_number: Unit 1 of 4
number_of_days: Approximately 15–18 instructional days
culminating_task_due: End of Unit 1 (TBD by teacher)
core_texts: "..."
strands_addressed: "Oral Communication  |  Writing"
```

Only the keys present are emitted, in the grid's own order. `# ...` after the
front matter is the subtitle under the UNIT PLAN title (omit it to use the
default).

The body is read top to bottom into `sections`:

- `## Step 1: ...`: an H2 whose text starts with `Step` is a step banner
  (`{"kind": "step"}`); any other H2 is a plain heading (`{"kind": "heading"}`).
- `### A. Big Idea`: an H3 opens a labeled row (`{"kind": "labeled"}`). Its
  blocks are every token up to the next heading or the next table. Use
  `#### Strand` for colon-less labels, `**Lead-in:**` for colon labels,
  `__sentence__` for bold paragraphs, `*sentence*` for italic ones, and
  `- [x]` lines for checklists.
- A standalone paragraph at section level is `{"kind": "para"}`; a wholly
  italic or bold line keeps that flag. Lists at section level are an error:
  put them under a `###` heading.
- Tables at section level are typed by the directive on the preceding line.
  The header row is for human readers except where noted; columns are read
  by position.
  - `<!-- gla: expectations -->` then `| Strand | Assessed | Covered |`.
    The second and third cells are split on `<br>` into bullet lists.
  - `<!-- gla: achievement -->` then a table whose header cells are the
    category names and whose single body row holds the descriptions.
  - `<!-- gla: lesson_table -->` then six columns: `#`, topic, teacher,
    student, assessment, expectations and resources.
  - `<!-- gla: reflection -->` then `| Criteria | Exemplars | Evidence |`.
    Leave the evidence cell empty so the template prints its placeholder.
  - Without a directive the parser guesses from the header (`Strand`,
    `Criteria`, six columns, or a one-row table) and otherwise stops with an
    error naming the directives.
- `<!-- gla: variety -->` before `### Variety of Learning Experiences` (the
  heading prefix alone also works) builds the variety section: an optional
  intro paragraph, then `#### Group` labels each followed by a `- [x]`
  checklist.

## course_outline

See `references/course_outline_schema.md`.

## long_range_plan

See `references/long_range_plan_schema.md`.

## weekly_plan

See `references/weekly_plan_schema.md`.

## exam_cover

See `references/exam_cover_schema.md`.

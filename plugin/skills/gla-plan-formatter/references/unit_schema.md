# Unit Plan: Content JSON Schema

The spec passed to `build_plan.py --type unit`. A complete worked example is
`examples/unit/example.json` (the parser's output for `examples/unit/example.md`);
read the pair side by side. A required field with no source content stays empty
and is recorded under `spec["review"]["gaps"]`; no marker text is ever written
(see `references/blocks.md`). Omit optional sections entirely when the source has
nothing for them.

Two ways in, plus one for GLA course repos:

1. **Markdown**: `build_plan.py --type unit --md unit.md` (conventions in
   `references/markdown_conventions.md`).
2. **JSON** (canonical): `--spec unit.json` with the shape below.
3. **Pipeline** (Claude Code, inside a course repo that has `course.yaml`,
   `master/02_Units/U<n>_*/unit_overview.md`, and dated
   `instances/<sem>/week_plans/U<n>_W*.yaml`; needs PyYAML):
   `build_plan.py --type unit --pipeline <course_root> --instance <sem> --unit <n>`.
   The parser (`scripts/parsers/unit_pipeline.py`) fills the overview grid,
   expectations, learning goals, assessment lists, the lesson table, and the
   Islamic perspective row from the teacher's sources, leaves the drafted areas
   (big idea, enduring understandings, essential questions, achievement
   descriptions, variety ticks, reflection exemplars) empty, and records every
   derivation under `review`. Edit the emitted `.spec.json` after the teacher's
   consent and rebuild with `--spec`. Add `--full-activities` for the week plans'
   full activity text in the lesson table instead of compact rows.

## Top level
```jsonc
{
  "school": "GIBRALTAR LEADERSHIP ACADEMY",   // optional (default)
  "subtitle": "Unit Planning Template · Backward Design ...",  // required: under the title
  "overview": { ... },     // required: the info grid
  "footer": "Gibraltar Leadership Academy  |  ENG3U ...",      // optional
  "sections": [ ... ]      // required: ordered body, rendered top to bottom
}
```

## overview (info grid)
The first six keys render two-per-row as label/value pairs, in this order.
`Core Texts` and `Strands Addressed` (if present) render as full-width rows.
Include the keys the source provides; missing required ones get the marker.
```jsonc
"overview": {
  "Course": "ENG3U, English, Grade 11, University Preparation",
  "Grade": "Grade 11",
  "Unit Title": "Unit 1: The Power of Storytelling",
  "Unit #": "Unit 1 of 4",
  "Number of Days": "Approximately 15–18 instructional days",
  "Culminating Task Due": "End of Unit 1 (TBD by teacher)",
  "Core Texts": "...",          // optional, full-width
  "Strands Addressed": "..."    // optional, full-width
}
```
The masthead's course strip is the `Course` value unless `context.course_line`
is set. A long `Course` value wraps the strip onto two lines, so give the strip
`"context": {"course_line": "ENG3U: English"}` and keep the full value in the grid.

## sections (ordered list)
Each item has a `kind`. Render order = list order, so sequence the
backward-design steps and their contents exactly as the unit should read.

| kind          | fields | renders as |
|---------------|--------|-----------|
| `step`        | `text` | centered maroon STEP banner with gold rule |
| `heading`     | `text` | maroon bold heading with gold underline (sub-headings like "E. Lesson Sequence Overview") |
| `para`        | `text`, `italic?`, `bold?` | a standalone paragraph |
| `labeled`     | `label`, `blocks` | tall maroon left-label cell + right content (the A./B./C./D. blocks, Learning Goals, Success Criteria, Assessment sections) |
| `expectations`| `rows` | 3-col Specific Expectations / Assessed / Covered table |
| `achievement` | `categories` | 4-col achievement-chart table |
| `lesson_table`| `rows` | 6-col lesson sequence table |
| `variety`     | `label`, `groups` | labeled row of grouped checkbox lists |
| `reflection`  | `rows` | 3-col Criteria / Exemplars / Evidence table |

### labeled
```jsonc
{ "kind": "labeled", "label": "A. Big Idea for This Unit",
  "blocks": [ {"type":"label","text":"Enduring Understandings:"},
              {"type":"bullets","items":[ "...", ... ]}, ... ] }
```
`blocks` uses the same block types as the lesson schema (`para`, `label`,
`quote`, `bullets`, `numbered`, `checks`). Use `label` blocks for strand names
or sub-headings inside the right column.

GLA unit plans carry two more `labeled` rows by convention, with no kind of
their own: "C. Learning Goals and Success Criteria" (one `label` per week, the
goal as a bold `para`, its success criteria as `bullets`) and "E. Islamic
Perspective and Character Education" (one `label` per week, the focus and
connection as a `para`, character education as a second `para`).

### expectations
```jsonc
{ "kind": "expectations", "rows": [
    { "strand": "Reading & Literature Studies",
      "assessed": [ "R1.1: ...", ... ],   // bulleted
      "covered":  [ "R1.2: ...", ... ] }, // bulleted, gold-accented column
    ...
] }
```
**Assessed versus covered, the rule the pipeline parser applies** (and the one
to follow by hand for a CS pipeline course). Graded evaluations are the rows of
the unit overview's `## Evaluations` table whose Weight cell is a percentage
(the instance Short and Long Term Plan's percentage wins when it lists the item);
formative rows carry `-`. A code is assessed when (a) the table's optional
`Assessed` column lists it for a graded row, which is authoritative; (b) it is
taught in a slot from the start of a graded evaluation's hand-out week through
its due slot; (c) the assignment hand-out line names its overall expectation; or
(d) a test slot names it in its notes. Every other primary or reinforced code is
covered; reinforced codes never move to assessed by rule (b). The split and the
rule go into the review list so the teacher can move codes.

### achievement
```jsonc
{ "kind": "achievement", "categories": [
    { "name": "Knowledge / Understanding", "desc": "..." },
    { "name": "Thinking", "desc": "..." },
    { "name": "Communication", "desc": "..." },
    { "name": "Application", "desc": "..." }
] }
```

### lesson_table
```jsonc
{ "kind": "lesson_table", "rows": [
    { "num": "1–2",
      "date": "Tue Nov 3",                // optional; printed as the first line of the topic cell
      "topic": "Unit Launch: ...",
      "teacher": "What the teacher will do ...",
      "student": "What the student will do ...",
      "assessment": "Assessment (say / write / do) ...",
      "expectations": "R1.1, R2.1 · Text: ..." },
    ...
] }
```
Keep `num` to the row number; a date packed into it wraps in the narrow column.
**Compact rows** keep a fifteen-row unit at eight pages: the teacher cell is one
line of standard wording chosen by day type (teach: "Teach with slides and live
coding:" plus the day's focus; hand-out, submit, formative, review, lab, and test
days each have a fixed line), and the student cell is the day's focus line. Full
activity text stays in the week plans. The standard wording is drafted text, so
it is listed in the review file.

### variety
The first group may be an intro: `{"intro": "..."}`. Remaining groups each have a
`label` and `items` as `[text, bool]` pairs (checkboxes).
```jsonc
{ "kind": "variety", "label": "Variety of Learning Experiences", "groups": [
    { "intro": "The following experiences are incorporated ..." },
    { "label": "Discussion & Dialogue",
      "items": [ ["Class Discussion (Socratic)", true], ["Think-Pair-Share", true] ] },
    ...
] }
```

### reflection
`exemplar` is the teacher's pre-unit intention. Leave `evidence` as `""` so the
template prints the standard post-unit placeholder for the teacher to complete
later.
```jsonc
{ "kind": "reflection", "rows": [
    { "criteria": "Questioning", "exemplar": "...", "evidence": "" },
    ...
] }
```

## review (optional, never rendered)

`"review": {"source": "...", "gaps": [{"section": "...", "field": "..."}],
"items": [{"section": "...", "text": "...", "risk": "high"}]}` at the top level,
and `"review": "..."` strings on any section, block, or row. `build_plan.py
--review PATH` collects them into the teacher's review list. See
`references/blocks.md`.

## Masthead (shared)

Every document opens with the shared masthead: the maroon course strip with the gold grade badge, then the title block. It is derived from the spec (course code, title, grade, unit or semester) and needs no keys. To override, add `"context": {"course_line": "...", "context_line": "..."}` and `"badge": "Grade 12  |  University Prep"` at the top level.

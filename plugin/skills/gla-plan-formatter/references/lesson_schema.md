# Lesson Plan: Content JSON Schema

The spec passed to `build_plan.py --type lesson`. A complete worked example is
`examples/lesson/example.json` (the parser's output for `examples/lesson/example.md`);
read the pair side by side. Required keys are marked; omit optional ones entirely
when the source has nothing for them (do not emit empty shells). A required field
with no source content stays empty (`""` or `[]`) and is recorded under
`spec["review"]["gaps"]`; no marker text is ever written (see `references/blocks.md`).

## Top level
```jsonc
{
  "school": "GIBRALTAR LEADERSHIP ACADEMY",   // optional, this is the default
  "context": { ... },          // required: the course/grade banner
  "badge": "Grade 12 | University Prep",       // required: gold badge text
  "title": "What Is Law? Purposes and Functions",  // required: lesson title
  "meta": { ... },             // required: the 4-up meta grid
  "curriculum": { ... },       // required
  "learning_goals_lead": "By the end of this lesson, I can:",  // optional lead line
  "learning_goals": [ "...", ... ],     // required: list of strings
  "success_criteria": [ "...", ... ],   // required: list of strings
  "materials": { ... },        // required
  "sequence": [ ... ],         // required: the lesson phases
  "differentiation": { ... },  // required: three named columns
  "google_classroom": [ "...", ... ],   // optional: omit if none in source
  "footer": "Gibraltar Leadership Academy  |  CLN4U  |  Lesson 1"  // optional
}
```

## context (banner)
```jsonc
"context": {
  "course_line": "CLN4U: Canadian and International Law",  // required
  "context_line": "Unit 1: Foundations of Law  |  Lesson 1" // optional 2nd line
}
```

## meta (4 columns: Course Code | Unit | Lesson | Duration)
```jsonc
"meta": {
  "course_code": "CLN4U",
  "unit": "Unit 1 – Foundations of Law",
  "lesson": "Lesson 1 of 16",
  "duration": "70 minutes"
}
```

## curriculum
`overall` and `specific` accept either a plain string or a list of **blocks**
(see Blocks below) when there are multiple expectations. `achievement_categories`
is the four Ontario categories mapped to booleans (checked = addressed in this
lesson). Always include all four keys.

The second category is named per subject: Science (SNC, SBI, SCH, SPH, SVN) and
Science and Technology call it "Thinking and Investigation", every other subject,
Computer Studies included, calls it "Thinking". The parser resolves the name from
`course_code` through the bundled curriculum index and writes the resolved keys into
the spec; a source that writes either spelling is matched either way. See
`scripts/categories.py`.
```jsonc
"curriculum": {
  "overall": "A1. Legal Foundations: ...",
  "specific": [ {"type":"para","text":"A1.1 – ..."}, {"type":"para","text":"A1.2 – ..."} ],
  "achievement_categories": {
    "Knowledge & Understanding": true,
    "Thinking": true,
    "Communication": false,
    "Application": true
  }
}
```

## materials
`teacher` and `student` are lists of strings (rendered as bullets).
`teacher_extra` / `student_extra` are optional **block** lists appended under
the bullets (used for things like a labelled "Suggested Video" note).
```jsonc
"materials": {
  "teacher": [ "Slide deck ...", "12 Sort Cards ..." ],
  "student": [ "Worksheet 1.1 ...", "Notebook" ],
  "student_extra": [
    {"type":"label","text":"Suggested Video (optional enrichment):"},
    {"type":"para","text":"“Why Do We Have Laws?” – TED-Ed"}
  ]
}
```

## sequence (the lesson phases)
Each phase renders a light-blush sub-bar (built from `num` + `phase` + `time` +
`subtitle`) followed by a two-column table. `left` and `right` each have an
optional `label` (bold maroon heading inside the cell) and a list of `blocks`.
```jsonc
"sequence": [
  {
    "num": "1",
    "phase": "MINDS ON",
    "time": "10 minutes",          // optional
    "subtitle": "Hook & Warm-Up",  // optional
    "left":  { "label": "Teacher Actions", "blocks": [ ... ] },
    "right": { "label": "Assessment for Learning", "blocks": [ ... ] }
  },
  ...
]
```
Use the right-hand column for whatever the source pairs with teacher actions , 
assessment notes, teacher notes, grouping tips, or student tasks. Keep the
source's own labels.

## differentiation (three columns)
An object of exactly three named keys → list of strings. Keep the source's
category names; these are the conventional defaults:
```jsonc
"differentiation": {
  "ELL Students": [ "...", ... ],
  "IEP / Accommodation": [ "...", ... ],
  "Advanced / Extension": [ "...", ... ]
}
```

## Blocks
Reusable content units for cells and block lists. A bare string is shorthand for
a plain paragraph.
| type       | fields | renders as |
|------------|--------|-----------|
| `para`     | `text`, `bold?`, `italic?`, `color?`, `size?` | a paragraph |
| `label`    | `text` | bold maroon sub-label line |
| `quote`    | `text` | italic maroon line (student prompts / quotations) |
| `bullets`  | `items` (list), `bold?` | bulleted list |
| `numbered` | `items` (list), `bold?`, `start?` | numbered list |
| `checks`   | `items` (list of `[text, bool]`) | checkbox list (☑/☐) |

`color` is a hex string without `#` (e.g. `"8C6D2A"`, gold_text, for a link).

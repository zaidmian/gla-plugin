# Weekly Lesson Plan: Content JSON Schema

The spec passed to `build_plan.py --type weekly_plan`. A worked example is
`examples/weekly_plan/example.json` (the parser's output for
`examples/weekly_plan/example.yaml`); `examples/weekly_plan/example.md` shows the
same type written in the house Markdown dialect. Required keys are marked; omit
optional ones when the source has nothing for them. A required field with no
source content stays empty and is recorded under `spec["review"]["gaps"]`; no
marker text is ever written (see `references/blocks.md`).

The type carries the official GLA HS Lesson Plan Template's fields (Islamic
Expectations, Character Education, Learning Skills, Achievement Categories,
AFL / AAL / AOL) on the v1 lesson furniture teachers already accepted. See
`references/SAMPLE_DELTAS.md` section 2 for the merged design.

## Top level
```jsonc
{
  "school": "GIBRALTAR LEADERSHIP ACADEMY",   // optional, this is the default
  "context": { ... },            // required: the course banner
  "badge": "Grade 11 | University Preparation",   // required: gold badge text
  "title": "Arithmetic and Input/Output",         // required: the week's title
  "meta": { ... },               // required: the two-row meta grid
  "islamic_expectations": "...", // string or blocks
  "character_education": "...",  // string, blocks, or {values, text}
  "learning_skills": { ... },    // six booleans
  "curriculum": { ... },         // overall, specific, achievement_categories
  "resources": [ "...", ... ],   // strings, rendered as bullets
  "learning_goals_lead": "By the end of this week, I can:",  // optional
  "learning_goals": [ "...", ... ],
  "success_criteria": [ "...", ... ],
  "days": [ ... ],               // DAY 1 to DAY 5
  "assessment": { ... },         // AFL, AAL, AOL
  "differentiation": { ... },    // optional: three named columns
  "notes": [ ... ],              // optional: string or blocks
  "footer": "Gibraltar Leadership Academy  |  ICS3U  |  Week 2"   // optional
}
```

## context (banner)
```jsonc
"context": {
  "course_line": "ICS3U: Introduction to Computer Science, Grade 11",  // required
  "context_line": "Unit 2  |  Week 2"                                   // optional
}
```

## meta (two rows of four)
Row one: Teacher | Course Code | Subject | Unit. Row two: Week | Dates |
Duration | Grade. A missing value renders the missing-information string.
```jsonc
"meta": {
  "teacher": "Br. Zaid",
  "course_code": "ICS3U",
  "subject": "Introduction to Computer Science",
  "unit": "Unit 2: Programming Fundamentals",
  "week": "Week 2 of 17",
  "dates": "September 1 to 5, 2025",
  "duration": "70 minutes per class",
  "grade": "Grade 11"
}
```

## islamic_expectations and character_education
Two cells of one table under the bar "Islamic Expectations & Character
Education". Each accepts a plain string or a list of **blocks**.
`character_education` also accepts an object whose `values` list renders as a
bold lead line ("Honesty, Responsibility") above `text` (string or blocks).
```jsonc
"islamic_expectations": [
  {"type": "para", "text": "Accuracy and fairness in calculation.", "bold": true},
  {"type": "para", "text": "The Quran repeatedly commands giving full measure ..."}
],
"character_education": {
  "values": ["Honesty", "Responsibility"],
  "text": "Students verify their programs' arithmetic by hand ..."
}
```

## learning_skills
The six Ontario learning skills mapped to booleans. Include all six keys; the
row renders as two lines of three checkboxes.
```jsonc
"learning_skills": {
  "Responsibility": false, "Organization": true, "Independent Work": true,
  "Collaboration": false, "Initiative": false, "Self-Regulation": true
}
```

## curriculum
`overall` and `specific` accept a string or a list of blocks.
`achievement_categories` is the four categories mapped to booleans; always
include all four keys. Rendered inside the "Content Standards" table after the
Learning Skills row, followed by the Resources / Worksheets row.

The second category is named per subject: Science (SNC, SBI, SCH, SPH, SVN) and
Science and Technology call it "Thinking and Investigation", every other subject,
Computer Studies included, calls it "Thinking". The parser resolves the name from
`course_code` through the bundled curriculum index and writes the resolved keys into
the spec; a source that writes either spelling is matched either way. See
`scripts/categories.py`.
```jsonc
"curriculum": {
  "overall": "A1, A2, B1, B3",
  "specific": [ {"type": "bullets", "items": ["A1.3: ...", "A1.4: ..."]} ],
  "achievement_categories": {
    "Knowledge & Understanding": true, "Thinking": true,
    "Communication": false, "Application": true
  }
}
```

## days
Same shape as a lesson phase. Each day renders a blush sub-bar built from
`num`, `time`, and `title` ("1.  DAY 1  (September 24): Math in Java") over a
two-column table. `left` defaults to the label "Teacher Actions"; `right` has
no default label. The section bar "Daily Lessons" is fused into the first day's
table so it cannot be orphaned. `text` overrides the generated bar text.
```jsonc
"days": [
  {
    "num": "1",
    "title": "Math in Java: Expressions and Order of Operations",
    "time": "September 24",          // optional; any short text in parentheses
    "left":  { "label": "Teacher Actions", "blocks": [ ... ] },
    "right": { "label": "Materials", "blocks": [ ... ] }
  }
]
```

## assessment
Three columns, AFL | AAL | AOL, one row of bullets. `of_learning` is either a
list of strings or an object keyed Observation / Conversation / Product (each a
list); the object form renders the three as labelled groups in the AOL column.
```jsonc
"assessment": {
  "for_learning": ["Prediction votes during the D1 opener", "Deck checkpoints on D1 and D3"],
  "as_learning": ["Part A of EX_Calculator_Corner is self-checked"],
  "of_learning": {
    "Observation": ["Participation and classification reasoning"],
    "Conversation": ["Focused questioning during stations"],
    "Product": ["Comparison chart", "Biomolecules quiz"]
  }
}
```
The official template's checklist vocabulary, for the interview to offer:
AFL: Journal / Notebook / Logbook, Diagnostic, Brainstorming, Participation,
Performance Task, Performance Problem, KWL Chart. AAL: Journal / Notebook,
Homework Check, Self / Peer Evaluation, Participation, Performance Task,
Performance Problem. AOL, an evaluation component grouped as Observation
(running record, list of books read, notes, anecdotal comments), Conversation
(conferencing, questioning, interview, oral presentation), Product (test, quiz,
assignment, project, portfolio, essay, lab report).

## differentiation (optional)
Rendered only when present: an object of three named keys to lists of strings,
under the bar "Teacher Notes & Differentiation Summary".
```jsonc
"differentiation": {
  "ELL Students": [ "..." ],
  "IEP / Accommodation": [ "..." ],
  "Advanced / Extension": [ "..." ]
}
```

## notes (optional)
A string or blocks under the bar "Notes". The YAML parser writes the week's
`notes` paragraph here plus an "Evaluations this week:" bullet list built from
`evaluations`.

## footer
Defaults to `Gibraltar Leadership Academy  |  <course_code>  |  <week>`.

## Blocks
The shared vocabulary for cells and block lists; a bare string is a paragraph.
| type       | fields | renders as |
|------------|--------|-----------|
| `para`     | `text`, `bold?`, `italic?`, `color?`, `size?` | a paragraph |
| `label`    | `text` | bold maroon sub-label line |
| `quote`    | `text` | italic maroon line |
| `bullets`  | `items` (list), `bold?` | bulleted list |
| `numbered` | `items` (list), `bold?`, `start?` | numbered list |
| `checks`   | `items` (list of `[text, bool]`) | checkbox list |

## Sources the parser accepts (`scripts/parsers/weekly_plan.py`)

**CS pipeline `week_plan.yaml`** (Weekly_Plan_Schema v3 to v5; chosen when the
path ends in `.yaml` / `.yml` or the text has a top-level `metadata:` key):
`metadata` fills context, badge, title, and meta (course line
"CODE: Course Name, Grade N"; unit "Unit N: Name"; dates from `dates.start` and
`dates.end` as "September 24 to October 1, 2026", left empty while they are
`{{...}}` placeholders; duration from the largest daily activity-minutes total);
`islamic_expectations.focus` (bold) and `connection`; `character_education.values`
and `how`; the `learning_skills` and `achievement_categories` lists become the
booleans ("Knowledge/Understanding" maps to "Knowledge & Understanding", and a
plain "Thinking" maps to "Thinking and Investigation" in a Science course);
expectation code lists are joined with commas; goals and their success criteria
are flattened; `daily_lessons` become days (bar time from `date` when it is a
real date, focus as an italic lead line, activities numbered "5 min: ...",
materials on the right); `assessment` maps directly; `notes` and `evaluations`
fill the Notes block. Days are carried through as written, including a day
whose `date` reads CUT after compression.

**Markdown**: front matter supplies `title`, `course_line`, `context_line`,
`badge`, `school`, `footer`, and the meta keys (`teacher`, `course_code`,
`grade`, `subject`, `unit`, `week`, `dates`, `duration`). Sections:
`## Islamic Expectations`; `## Character Education` (an optional
`**Values:** a, b` line becomes the bold lead); `## Learning Skills` and
`## Achievement Categories` as a `- [x]` checklist, a bullet list, or a comma
line (listed names are checked); `## Curriculum Expectations` with
`**Overall:** ...` and `**Specific:** ...` (inline text, or a label line followed
by a list); `## Resources`; `## Learning Goals` (an optional lead paragraph plus
a list); `## Success Criteria`; `## Daily Lessons` with `### Day 1: Title (time)`
headings, the first `####` sub-block going left and the second right (the
`####` text is the cell label); `## Assessment` with `### For Learning`,
`### As Learning`, `### Of Learning` (optionally `#### Observation`,
`#### Conversation`, `#### Product`); optional `## Differentiation` with one
`###` per column; optional `## Notes`.

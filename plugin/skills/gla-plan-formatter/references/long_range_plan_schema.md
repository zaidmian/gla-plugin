# Short and Long Term Plan (`long_range_plan`): Content JSON Schema

The spec passed to `build_plan.py --type long_range_plan`. The worked example is
`examples/long_range_plan/example.json` (the CLU3M sample), produced from
`examples/long_range_plan/example.md` by `parsers/long_range_plan.py`. The
output is the school's "Short and Long Term Plan": a centred header block, the
short-term table, a second header block, the long-term table, optional notes,
and the four signature lines.

## Top level
```jsonc
{
  "school": "GIBRALTAR LEADERSHIP ACADEMY",   // optional, this is the default
  "semester": "Semester 1",                   // optional; rendered uppercase
  "course": { ... },                          // required
  "teacher": "Humzah Ilahie",                 // required; rendered "TEACHER: HUMZAH ILAHIE"
  "short_term": { ... },                      // required
  "long_term": { ... },                       // required
  "notes": [ "...", ... ],                    // optional bullets after the long-term table
  "signatures": true,                         // optional, default true
  "footer": "Gibraltar Leadership Academy  |  Short and Long Term Plan  |  CLU3M"  // optional
}
```

## course
Composed into the header line `GRADE 11, CANADIAN LAW (CLU3M)`. `pathway`, when
given, is appended after the code. A bare string is used verbatim (uppercase).
```jsonc
"course": {
  "code": "CLU3M",             // required
  "title": "Canadian Law",     // rendered uppercase
  "grade": "11",
  "pathway": "University/College Preparation"   // optional
}
```

## short_term
One row per unit plus any non-unit rows (Mock Trial, FINAL EXAM, Culminating
Tasks, Attendance), which leave `unit` empty. `evaluation` is a string or a list
of strings; a list renders one line per entry inside the cell.
```jsonc
"short_term": {
  "columns": ["Unit", "Unit Title", "Start", "End (approx.)", "Evaluation Percentage"],  // optional override
  "rows": [
    { "unit": "1", "title": "Legal Foundations", "start": "Feb 3, 2020",
      "end": "Feb 20, 2020", "evaluation": ["6% Quizzes", "10% Assignments"] },
    { "unit": "", "title": "FINAL EXAM", "start": "", "end": "TBA", "evaluation": "15%" }
  ],
  "total": "100%"              // optional, default "100%"; rendered as the washed Total row
}
```

## long_term
One row per evaluation. `group` is the unit the evaluation belongs to; it renders
as a bold maroon first line in the first cell, above the evaluation label, on
the first row of each run of rows that share it (so a unit with four
evaluations names itself once). Rows without a group (Quizzes, ISU, FINAL EXAM)
show the label alone.
```jsonc
"long_term": {
  "columns": ["Evaluations", "Due Dates", "Titles of Evaluation", "% of Grade"],  // optional override
  "rows": [
    { "group": "UNIT 1: Legal Foundations", "label": "Assignment 1",
      "due": "Mar 27, 2020", "title": "History of Law", "weight": "10%" },
    { "label": "Quizzes", "due": "Weekly", "title": "Quiz", "weight": "30%" }
  ],
  "total": "100%"              // optional, default "100%"
}
```

## Validation
The builder raises `SpecError` when the percentages do not total 100:
- `short_term`: every percentage found in every row's `evaluation` is summed
  (a row like "6% Quizzes / 10% Assignments" contributes 16). If any row has no
  percentage at all (for example "TBA"), the check is skipped.
- `long_term`: every row's `weight` is summed; if any weight has no percentage,
  the check is skipped.

## Rendering notes
- Header block (both tables): school in maroon, SEMESTER and the course line in
  bold, the plan name ("SHORT TERM PLAN" / "LONG TERM PLAN") in maroon,
  then the teacher line. Each header keeps with its table.
- The Unit and Evaluations columns are washed blush; short columns centre.
- `signatures` renders Teacher's and Principal's Signature on one line, then
  Student's and Parent's.
- Default footer: `Gibraltar Leadership Academy  |  Short and Long Term Plan  |  <code>`.

## Markdown source
`parsers/long_range_plan.py` accepts two shapes.

Front-matter shape:
```markdown
---
semester: Semester 2
course:
  code: CLU3M
  title: Canadian Law
  grade: 11
teacher: Humzah Ilahie
---

## Short Term Plan

| Unit | Unit Title | Start | End (approx.) | Evaluation Percentage |
|---|---|---|---|---|
| 1 | Legal Foundations | Feb 3, 2020 | Feb 20, 2020 | 6% Quizzes<br>10% Assignments |
| | FINAL EXAM | | TBA | 15% |
| **TOTAL** | | | | **100%** |

## Long Term Plan

| Evaluations | Due Dates | Titles of Evaluation | % of Grade |
|---|---|---|---|
| **UNIT 1: Legal Foundations**<br>Assignment 1 | Mar 27, 2020 | History of Law | 10% |
| Quizzes | Weekly | Quiz | 30% |
| **TOTAL** | | | **100%** |

## Notes

- Optional bullets.
```

CS-pipeline shape (the `Short_and_Long_Term_Plan.md` a semester instance
already carries): bold header lines `**GIBRALTAR LEADERSHIP ACADEMY**`,
`**GRADE 11 Introduction to Computer Science (ICS3U)**`, `**SHORT TERM PLAN**`,
a `TEACHER: NAME` line, then the table; repeated for `**LONG TERM PLAN**`.

Table rules, either shape:
- Short term: a row whose title cell is empty takes its first cell as the title
  (`**CULMINATING TASKS** | | Dec 11, 2026 | ...`). An evaluation cell splits on
  `<br>`, or, failing that, before each `NN%`, so `4% Test 3% Assignment` becomes
  two lines.
- Long term: a bold row with the other cells empty is a group header for the
  rows that follow; a first cell written `**GROUP**<br>Label` carries its group
  inline. A first cell starting with `TOTAL` closes the table and supplies
  `total`.
- Front matter may also use the flat keys `course_code`, `course_title`,
  `grade`, `pathway`, plus `school`, `signatures`, `footer`, and a `notes` list.
- When the source has no semester, the parser reads it from a parent folder
  named like `2026-27_S1` ("2026-27 Semester 1"). When a `course.yaml` sits above
  the source (a GLA course repo), the parser fills `pathway` from its `type`,
  `title` and `grade` when the plan lacks them, and replaces the plan's teacher
  line with `teacher_formal` when that key exists; without one, `pathway` comes
  from the course code. Each fill is recorded under `review` for the teacher.
- To correct anything the parser derived, build once with `--md`, edit the
  `.spec.json` it writes (in the artifacts folder), and rebuild with `--spec`.

## Masthead (shared)

Every document opens with the shared masthead: the maroon course strip with the gold grade badge, then the title block. It is derived from the spec (course code, title, grade, unit or semester) and needs no keys. To override, add `"context": {"course_line": "...", "context_line": "..."}` and `"badge": "Grade 12  |  University Prep"` at the top level.

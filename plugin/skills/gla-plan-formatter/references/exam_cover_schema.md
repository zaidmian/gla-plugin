# Exam Cover Page (`exam_cover`): Content JSON Schema

The spec passed to `build_plan.py --type exam_cover`. The worked example is
`examples/exam_cover/example.json`, produced from `examples/exam_cover/example.md`
by `parsers/exam_cover.py`. The output is a single page: the running crest
header, the bismillah line, three centred lines (division, exam period, month
and year), a two-column field grid, the Categories table, and the numbered
instructions.

## Top level
```jsonc
{
  "school": "GIBRALTAR LEADERSHIP ACADEMY",   // optional, this is the default
  "division": "Secondary Division",           // optional, this is the default
  "exam_period": "Final Exams: Semester 1",   // required
  "month_year": "January 2026",               // required
  "bismillah": true,                          // optional, default true; false omits the line,
                                              // a string replaces the default text
  "fields": { ... },                          // optional; missing values render as fill rules
  "categories": [ ... ],                      // optional; default K/U, T or T/I, COMM, APP, FINAL
  "instructions": [ "...", ... ],             // optional; default the five standard lines
  "footer": "Gibraltar Leadership Academy  |  Examination"   // optional, this is the default
}
```

Default bismillah text: `In the name of Allah the Most Gracious, the Most Merciful`.

## fields
Rendered two per row in this order. Every key is optional; an empty or missing
value renders as `Label:  ____________________` so the teacher or student can
fill it by hand.
```jsonc
"fields": {
  "name": "",                       // the student's name line, normally blank
  "course_teacher": "Z. Mian",
  "course_name": "Introduction to Computer Science",
  "course_code": "ICS3U",
  "exam_date": "January 20, 2027",
  "exam_time": "9:00 a.m.",
  "exam_room": "Gym",
  "exam_pages": "8"
}
```

## categories
One column per entry, in order. When `categories` is absent the builder supplies the
default row, abbreviating the second category `T/I` for a Science course (SNC, SBI,
SCH, SPH, SVN) and `T` for every other subject including Computer Studies, decided by
`fields.course_code`. An authored table is used exactly as written.

`marks` is the raw mark denominator line
(rendered bold at the section size, centred); `weight` is the percentage line
beneath it. Leave the template placeholders when the values are not yet known.
```jsonc
"categories": [
  { "name": "K/U",   "marks": "/XX", "weight": "XX%" },
  { "name": "T/I",   "marks": "/XX", "weight": "XX%" },   // "T" outside Science
  { "name": "COMM",  "marks": "/XX", "weight": "XX%" },
  { "name": "APP",   "marks": "/XX", "weight": "XX%" },
  { "name": "FINAL", "marks": "/XX", "weight": "____%" }
]
```

## instructions
Rendered under the bold label "Instructions for students:" as a numbered list.
Blanks stay as `___` when the teacher has not supplied the page count or weight.
The defaults:
1. Complete, well-written answers are required for all questions.
2. Read all questions carefully to avoid losing marks unnecessarily.
3. This exam is made up of ___ pages (including this page or the answer sheet). Check that all pages are included.
4. This exam is worth ___ % of your final mark.
5. Check your answers before submitting your exam - do not leave any questions blank!

## Markdown source
```markdown
---
division: Secondary Division
exam_period: "Final Exams: Semester 1"     # quote it: the value holds a colon
month_year: January 2026
fields:
  course_teacher: Z. Mian
  course_code: ICS3U
  exam_room: Gym
---

## Categories

| K/U | T/I | COMM | APP | FINAL |
|---|---|---|---|---|
| /XX | /XX | /XX | /XX | /XX |
| XX% | XX% | XX% | XX% | ____% |

## Instructions

1. Complete, well-written answers are required for all questions.
2. ...
```
Field keys may also sit flat in the front matter (`course_code: ICS3U`). Omit
`## Categories` or `## Instructions` to take the defaults.

## Masthead (shared)

Every document opens with the shared masthead: the maroon course strip with the gold grade badge, then the title block. It is derived from the spec (course code, title, grade, unit or semester) and needs no keys. To override, add `"context": {"course_line": "...", "context_line": "..."}` and `"badge": "Grade 12  |  University Prep"` at the top level.

# GLA Grading Conventions

Shared assessment rules for all GLA course repos. Per-course weighting tables (what each unit/test/assignment is worth) live in the course's `Assessment_Plan.md`; this file governs the *form* of every graded item. The governing Ontario policy, with the September 2026 amendments folded in, is `growing-success-summary.md` in this same folder; where a weighting rule below cites a percentage, that policy is its source.

## Exercises: the /10 completion scale

- Exercises have **no rubric**. They are graded on the /10 completion scale, and the anchors are **printed on every exercise sheet**:

| Marks | Meaning |
|-------|---------|
| 10 | Complete and correct |
| 7–9 | Complete with minor errors |
| 4–6 | Substantial attempt |
| 1–3 | Minimal attempt |
| 0 | Not submitted |

- The raw scale is /10 everywhere (sheets, keys, week-plan `marks:` fields, marking notes). An exercise's *percent weight* in the course grade is set by the course's `Assessment_Plan.md` and is independent of the raw scale.
- Exercises are submitted to Google Classroom by the end of class on the due day.
- Exercise sheets include an optional, unmarked **Challenge** section for early finishers.

## Assignments

- Every assignment opens with a **`## Learning goals`** section, placed between the header block and the scenario: 3 to 5 student-facing bullets under "By the end of this assignment you will be able to ...", derived from the assignment's expectation codes and the learning goals of the week lessons it follows. Expectation codes stay in the header block, the goals are written in student language. See `templates/Assignment_Template.md`.
- **Default: one per unit**; a course's `Assessment_Plan.md` may set a different per-unit count with justification (courses with one dominant strand should first consider slicing it into sub-units instead). Google Classroom rubric (CSV + Markdown pair) using the Ontario Growing Success achievement chart: **5 levels** (Below Level 1 → Level 4, Level 3 = provincial standard) × **4 categories** (Knowledge/Understanding, Thinking, Communication, Application).
- Rubric CSVs must pass Google Classroom import checks: 7 columns, all 5 levels per criterion, and criterion point totals that sum exactly to the assignment's stated points. The CSV level-title strings are exactly: `High Degree of Effectiveness (Level 4)` · `Considerable Effectiveness (Level 3)` · `Some Effectiveness (Level 2)` · `Limited Effectiveness (Level 1)` · `Not Yet Demonstrated` (the house rendering of "Below Level 1").
- Students get **1.5–2 weeks** (7–10 class days) from hand-out to due slot. Extensions must be requested before the due date.
- Every assignment includes **stretch goals** worth bonus marks (harder challenges or deeper self-directed exploration of the current topic, with citation of what was used to learn it). Combined stretch bonus is capped at ~10% of the assignment's points, and a unit's assignment component is capped at 100%.
- Every assignment includes an **academic-integrity note**: discussing ideas is fine; submitting code/work you did not produce (from a classmate, a website, or an AI tool) is not; you must be able to explain every line of your submission.
- Teacher-side `marking_notes.md` accompanies every assignment (common shortcuts, integrity red flags, level anchors).

### Rubric level points

Each rubric level is worth a fixed share of its criterion's points. gc-rubric's builder applies the shares and rounds half-up to one decimal. The shares come from the Grades 7 to 12 percentage bands in `growing-success-summary.md` (Chapter 5):

| Level | Growing Success band | Share | Where the share sits |
|-------|----------------------|-------|----------------------|
| Level 4 | 80–100% | 100% | the top of the band (4+) |
| Level 3 | 70–79% | 75% | the middle (3) |
| Level 2 | 60–69% | 60% | the floor (2−) |
| Level 1 | 50–59% | 50% | the floor (1−) |
| Below Level 1 | below 50% | 12.5% | well below the pass line |

Every share passes one test. A student who earns the same level on every criterion gets an assignment total inside that level's band. Google Classroom records the total, so a share outside its band would report a level the student never showed.

Level 4 is worth the whole criterion so that full marks can be earned. At 90%, no student could reach 100% on an assignment without the stretch-goal bonus.

Level 3 is the provincial standard. Its share sits in the middle of the band, so work at the standard on every criterion totals 75%, a plain 3.

Levels 2 and 1 sit at the floor of their bands. A rubric gives a criterion one level, and "some effectiveness" runs from work just past Level 1 to work just short of Level 3; the floor keeps a Level 2 judgement from claiming more than the weakest work at that level shows. Level 1 at 50% keeps limited but real achievement at a pass, which is what Level 1 means.

Below Level 1 is worth 12.5% of the criterion, never zero. Work that was handed in but shows less than Level 1 still counts for something. Work not handed in is a separate matter, handled by the Growing Success rules on late and missing work. The share is one eighth, so a 4-point criterion's lowest level is exactly 0.5.

Mixed results land between bands. Two criteria at Level 3 and two at Level 2, equally weighted, total 67.5%, a 2+. The total is evidence; the report-card grade still follows the student's most consistent achievement and the teacher's judgement.

**Small criteria.** One decimal place cannot hold the bands on a criterion under 1.5 points. On a 1-point criterion, Level 3 rounds to 0.8, which is a Level 4 share. Under the house category splits, an assignment of 7 points or more keeps every criterion at 1.5 points or above.

## Tests

- **One per unit**, in the parts course.yaml's `test_parts` lists (A and B when it is absent):
  - Part A: multiple choice, 1 mark each, 4 options, exactly one correct; ~40–50% of marks in a two-part test.
  - Part B: short answer / applied, ~50–60% of marks in a two-part test. For coding courses: trace-this-code, find-the-error, write-a-fragment, explain-in-your-own-words. For science: label-the-diagram, calculations, explain. For history: source analysis, short response.
  - Parts C and later, when listed: written items numbered with their letter, for example an extended response.
- Ship with: `test_KEY.md` (full answers incl. accepted variations), `coverage_table.md` (Question | Expectation codes | Category K/T/C/A | Marks; every taught expectation of the unit appears at least once), `review_sheet.md` (student-facing, used on the preceding review day; sample questions differ from the test), and `test_reference.md` (student-facing aid sheet handed out **with** the test paper: the syntax, tables, formulas and conversions students may consult while writing, drawn from the unit's reference sheets, with no worked examples and no practice questions).
- Written for a 50-minute period. The teacher copy carries answers inline or via KEY; the student copy is generated by stripping answers, so questions must stay self-contained.
- **No ministry document names in student-facing test text.** A question may assess a work habit, a safety practice, or an achievement category, but it names the skill rather than the document it comes from. "Which work habit is she demonstrating?" is fine; "Which Ontario Skills Passport work habit ..." is not. The same applies to Growing Success and to the curriculum document. Expectation codes belong in `coverage_table.md`, never on the paper.
- The `## Structure` section and the `### Companion files` section are teacher-only. The student handout generated by the `semester` skill's Google Docs step drops both, letters the multiple-choice options (the letter is the marker, there is no bullet), lays short option sets out in columns, and spaces the questions apart. Author one option per source line so that layout can do its work.

## Final grade structure (2026 model)

Effective 2026-27, the old 70% term / 30% final split is replaced for every Grade 9 to 12 course by a three-bucket final mark. The buckets always total 100.

| Component | Grades 9-10 | Grades 11-12 |
|-----------|:-----------:|:------------:|
| Classroom work | 65% | 65% |
| Final evaluation | 20% | 25% |
| Attendance and participation | 15% | 10% |

The course's `Assessment_Plan.md` sets the per-unit classroom-work breakdown (summing to 65%) and the final-evaluation split. Category weighting inside any single summative item is a separate question (see below).

## Final evaluation

Final evaluation is a **written exam** and, for most subjects, a **culminating task**. The split is fixed by subject area and grade band, not chosen per course:

| Subject area | Gr 9-10 (of 20%) | Gr 11-12 (of 25%) |
|--------------|------------------|-------------------|
| English, Mathematics, Science | 20% exam | 25% exam |
| Canadian and World Studies | Geography (Gr 9), History and Civics (Gr 10): 20% exam | 15% exam + 10% culminating |
| The Arts; **Computer Studies**; Health and Physical Education; Technological Education | 10% exam + 10% culminating | 10% exam + 15% culminating |
| Business Studies; Social Sciences and Humanities | 10% exam + 10% culminating | 15% exam + 10% culminating |
| Classical and International Languages; French / Native Languages | 10% exam + 10% culminating | 10% exam + 15% culminating |
| First Nations, Métis, and Inuit Studies | 10% exam + 10% culminating | 10% exam + 15% culminating |

Special cases: NBE3U and NBE3C require a 25% written exam; for MTH1W the EQAO Grade 9 mathematics assessment is the 20% written exam; Grade 10 Career Studies (GLC2O) uses a 15% culminating task plus the 5% TVO financial-literacy graduation requirement (70% to pass). Exam-exempt courses still carry a 20% (Gr 9-10) or 25% (Gr 11-12) final evaluation with no written exam: Gr 9-10 locally-developed compulsory credits; Gr 11-12 workplace (E) and open (O) courses; Guidance and Career Education (except GLC2O); Co-operative Education; Interdisciplinary Studies; American Sign Language. Note that Gr 9-10 open (O) courses are **not** exempt. Written exams are written in the designated exam period, except the EQAO Grade 9 mathematics assessment, which counts as a fixed 20% of the final math mark.

Governed in detail by the course's `Assessment_Plan.md` and (for the culminating task) its `PROJECT_DECISIONS.md`. Culminating milestones stay formative (feedback only) but are assessed summatively via rubric rows at final submission.

**GLA CS note:** the Computer Studies courses (ICD2O, ICS3U, ICS4U) previously ran a 30% culminating project with no exam. Computer Studies is not exempt under the 2026 policy, so their final evaluation is now a 10% written exam plus a culminating task (10% at Grade 10, 15% at Grades 11-12).

## Attendance and participation

A graded component worth 15% (Grades 9-10) or 10% (Grades 11-12), scored on **unexcused** absences. Excused absences never lower the mark.

| Level | Mark range | Unexcused absences |
|-------|:----------:|--------------------|
| 4 | 80-100% | 0 to 2.5% |
| 3 | 70-79% | 2.5 to 5% |
| 2 | 60-69% | 5 to 7.5% |
| 1 | 50-59% | 7.5 to 10% |
| Below 1 | below 50% | more than 10% |

## Category weighting

- Default Growing Success category weighting for summative work: **K/U 25 · Thinking 30 · Communication 20 · Application 25**. A course may set its own in course.yaml (`assessment.category_weights`), with the reason in its `Assessment_Plan.md`; gc-rubric uses it, and this default otherwise. The 2026 amendment changed only the final-mark structure above; the four-category achievement chart itself is unchanged, so this default and the gc-rubric levels stand.

## Naming the second category

The second achievement-chart category is called **Thinking** in Computer Studies and **Thinking and Investigation** in Science. A rubric, coverage table, or course outline uses the name printed in that course's own curriculum document, never the name from a neighbouring subject.

- **ICD2O, ICS3U, ICS4U and every other Computer Studies course: `Thinking`.** Both Computer Studies curriculum documents (2008 for ICS3U/ICS4U, 2023 for ICD2O) name the category Thinking in the achievement chart, the prose definition, and the criteria list. Its criteria are use of planning skills, use of processing skills, use of critical/creative thinking processes.
- **Science courses (SNC, SBI, SCH, SPH, SVN) and Science and Technology, Grades 1-8: `Thinking and Investigation`.**

Computer Studies sits close enough to science that the longer name gets applied to it by mistake, and the ICD2O document contains one stray sentence using the Science wording in its Descriptors paragraph. That sentence is boilerplate, contradicted by the chart on the facing page. `growing-success-summary.md` records the full picture under "Category names by subject". Nothing in the GLA CS repos should read "Thinking and Investigation"; the `K/T/C/A` shorthand used in test coverage tables is unaffected either way.

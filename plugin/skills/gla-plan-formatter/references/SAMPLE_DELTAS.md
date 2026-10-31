# Sample reconciliation (2026-09-06)

Eight samples were supplied from `~/Downloads/Formatter Samples`. Each is compared with the schema the skill would use for that type. "Delta" means the schema or renderer changes to match the sample; "keep" means the sample confirms the current design.

## 1. Unit plan: `SBI4U_Unit1_Biochemistry.pdf`, `SBI4U_Unit2_MetabolicProcesses.pdf`

Both are v1 `unit` renders (overview grid, STEP banners, labeled rows, Assessed/Covered table, achievement chart, lesson sequence, variety checklist, reflection). Structure is identical to the bundled ENG3U example.

- **Keep** the `unit` schema unchanged.
- Style deltas come from the design system only (brand palette, header table, page-break control, repeated header rows on the long tables).

## 2. Weekly plan: `SBI4U_Week01.pdf`, `SBI4U_Week02.pdf` plus the official `Copy of HS Lesson Plan Template.docx`

The two SBI4U files are v1 `lesson` renders used as weekly plans: the Lesson cell reads "Week 2 of 17 | September 1–5, 2025", Duration reads "70 minutes per class", the sequence is DAY 1 to DAY 5, and the right-hand column carries "Leadership & Character Focus", "Character Education", and an "Assessment Summary" with AFL / AAL / AOL. The official HS template is a one-table form with these fields: Teacher Name, Course Code/Grade, Subject, Date, Unit, Islamic Expectations, Character Education, Learning Skills (six checkboxes), Achievement Categories (four checkboxes), Overall Expectations, Specific Expectations, Resources/Worksheets, Learning Goals | Success Criteria, Lessons/Activities alongside AFL / AAL / AOL checklists (AOL split into Observation, Conversation, Product).

The `weekly_plan` type therefore becomes the v1 lesson furniture carrying the official template's fields as first-class sections, rather than the draft I sketched from `Weekly_Plan_Schema.yaml` alone:

| Section | Source | Rendering |
|---|---|---|
| Banner and title | v1 lesson | course line, "Unit N: Title \| Week N", grade badge, title "WEEKLY LESSON PLAN" (v1 says "LESSON PLAN"), week title |
| Meta grid | v1 lesson + template | Teacher, Course Code / Grade, Subject, Unit, Week (N of M), Dates, Duration per class |
| Islamic Expectations and Character Education | template | one two-column table: Islamic Expectations \| Character Education |
| Content Standards | template | Learning Skills checkbox row (Responsibility, Organization, Independent Work, Collaboration, Initiative, Self-Regulation); Achievement Categories checkbox row; Overall Expectations; Specific Expectations; Resources / Worksheets |
| Learning Goals and Success Criteria | v1 lesson | unchanged two-column table |
| Daily lessons | v1 lesson sequence | one blush bar per day ("1. DAY 1 — topic"), teacher actions left, right column per day (assessment note or character focus) |
| Assessment | template | three-column AFL \| AAL \| AOL; each column lists the strategies used (the template's checklist items become the vocabulary the interview offers), AOL grouped Observation / Conversation / Product |
| Teacher Notes and Differentiation | v1 lesson | unchanged three-column table (optional) |

Deltas to confirm: (a) the title "WEEKLY LESSON PLAN"; (b) Islamic Expectations and Character Education as a section of their own rather than a right-column note; (c) the AFL/AAL/AOL section as a three-column table at the end rather than inside Day 5; (d) Learning Skills checkboxes as a row like the achievement categories. Input path: `week_plan.yaml` from the CS pipeline maps onto this directly (it already has islamic_expectations, character_education, learning_skills, achievement_categories, assessment for/as/of).

## 3. Lesson plan (single period)

No sample supplied. The v1 `lesson` schema stays as the single-period type. Because the weekly plan now owns the day-by-day sequence, a `lesson` keeps its phase sequence (Minds On, Direct Instruction, and so on). Delta to confirm: should a single-period lesson also carry Islamic Expectations, Character Education, and Learning Skills (the official template has them on every plan)? Proposed: yes, as optional sections rendered only when supplied.

## 4. Short and long term plan: `GLA CLU3m Short and Long Term Plan Sample.docx`

Matches the draft `long_range_plan` schema closely. Structure: centred header (school, SEMESTER 1, "GRADE- 11, CANADIAN LAW CLU3M", SHORT TERM PLAN, TEACHER), short-term table `Units | Unit Title | Start Time | End Time (Approx. date) | Evaluation Percentage` with extra non-unit rows (Mock Trial 15%, FINAL EXAM TBA 15%, Total 100%), then a second header (LONG TERM PLAN) and the table `EVALUATIONS | DUE DATES | TITLES OF EVALUATION | % OF GRADE` where the first cell carries the unit name and the evaluation label (two lines), plus Quizzes / ISU / FINAL EXAM rows and a TOTAL row, then four signature lines: Teacher, Principal, Student, Parent.

Deltas: (a) add a `signatures` block (Teacher's Signature, Principal's Signature on one line; Student's, Parent's on the next); (b) long-term rows carry `group` (unit) and `label` (evaluation) in the same first cell rather than a separate merged group row; (c) the semester appears in the header; (d) the second table gets its own header block (school, semester, course, LONG TERM PLAN, teacher) rather than a plain section bar. Validation stays: weights total 100%. Under the 2026 model the interview prefills the three buckets; the sample's 70/30 split is the pre-2026 model and is not carried forward.

## 5. Course outline: `SBI4U Course Outline 2025_26.docx`

An older GLA outline (2017 origin, revised 2025). Cover page: horizontal logo, "Course Outline", a metadata table (Course Title, Code, Type, Grade, Credit Value, Prerequisites, Co-requisites, developed by / date, revised by / date, Ministry document). Then: Course Description / Rationale; Overall Curriculum Expectations (codes as inline bold); Outline of Course Content (`Unit | Topic | Chapters | In class Hours`, total 110); Teaching and Learning Strategies; Learning Skills; Obtaining Extra Help; Late Assignment Submission Policy (Growing Success quotation); Achievement Policy (the old 70/30); Homework; Overall Assessment Breakdown (term-work categories and achievement-chart weights K/U 35, T/I 25, C 20, A 20); assessment tools tables (Observation / Conversation / Product); Some Considerations for Program Planning (Instructional Approaches, Health and Safety, Environmental Education, Critical Thinking, Career Education, ELL); Resources; Plagiarism; the nine Considerations for Program Planning.

The 19-section `Course_Outline_Template.md` already covers all of this. Deltas: (a) the units table gains an optional `Chapters` (or `Textbook reference`) column; (b) add optional sub-sections "Obtaining Extra Help" and "Homework" under Course Policies; (c) the metadata grid keeps "Developed By / Date" and "Revised By / Date" as paired rows (already in the template); (d) the cover-page treatment (metadata table alone on page 1) is a layout option the interview can offer, default off; (e) the 70/30 achievement policy and the 35/25/20/20 category weights are the sample's values, not defaults: the interview prefills the 2026 buckets and the shared 25/30/20/25 weighting and asks the teacher to confirm or override.

## 6. Exam cover page: `Copy of Exam cover page Template.docx`

Not one of the five planned types. Structure: horizontal logo, "In the name of Allah the Most Gracious, the Most Merciful", "Secondary Division / Final Exams – Semester N / Month Year", a two-column field grid (Name, Course Teacher, Course Name, Course Code, Exam Date, Exam Time, Exam Room, Exam Pages), a Categories table (K/U, T/I, COMM, APP, FINAL with "/XX" and "XX%" cells), and a numbered "Instructions for students" list with blanks for page count and weight.

Proposed: add `exam_cover` as a sixth type. It is one page, reuses the metadata grid and a generic table, and its interview is short (semester, month and year, course, teacher, date, time, room, page count, weight, category marks). Blanks stay as fill-in rules when the teacher leaves them.

## Cross-cutting observations

- The official GLA documents use the horizontal wordmark (crest plus "GIBRALTAR LEADERSHIP ACADEMY" in the logo typeface) on outlines and exam covers, and the crest alone on plans. The formatter's header (crest plus the school name set in Arial) is the v1 convention; keeping it across all types is consistent with the plans the school already accepted (the SBI4U files).
- Every sample carries the teacher's name. The interview never guesses it.
- No sample uses the "Toronto • Ajax" tag.

## Decisions (2026-09-06)

- Weekly plan: the merged design above is adopted.
- Lesson plan: unchanged; no Islamic Expectations, Character Education, or Learning Skills sections.
- `exam_cover` is added as the sixth document type.
- Crest: cropped to its content with a small pad (`Standards/brand/GLA_Logo.jpg`; the original is kept as `GLA_Logo_uncropped.jpg`).

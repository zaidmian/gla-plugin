# The interview

One round, before any file is built. It makes the teacher's document predictable: they see what was found, what was derived, what is missing, and they decide what may be filled in. Never ask about something the source already states. Never split into a second round unless an answer contradicts the source.

## Protocol

1. Read the source and map it to the schema privately (a scratch file, never in the reply).
2. Build three lists:
   - **Confirm**: values found in the source or safely derivable. Each is shown with its origin: `[found]`, `[derived from "4U"]`, `[from course.yaml]`.
   - **Gaps**: required content the source does not supply. Each gap names what would be drafted if permitted.
   - **Output**: formats (Word and PDF), the file name proposed from course code and title, and the review file (`<Course>_Review.md`) that lists everything drafted, derived, or changed.
3. Send exactly one message in the shape below.
4. Apply the reply. A gap the teacher did not approve stays blank in the document and is listed under "Gaps: not filled" in the review file. An approved gap is drafted plainly and listed in the review file under its section. Nothing is marked inside the document.
5. "go" accepts everything as shown. "just build it" skips the message: Confirm values are used, gaps stay blank and are listed, nothing is drafted.

## Message shape

```
Before I build the <type>, three quick things.

A. Confirm (from your document; reply "ok" or correct any line)
  1. Course: CLN4U, Canadian and International Law        [found]
  2. Duration: 70 minutes                                 [found]
  3. Achievement categories: K/U, Thinking, Application   [found]
  4. Grade band: Grade 12 | University Prep               [derived from "4U"]

B. Missing. May I fill these in? (reply with the numbers to fill, "fill all", or "leave blank")
  5. Success criteria: I would write three or four "I can" statements from your learning goals.
  6. Differentiation, IEP column: I would adapt your ELL notes.

C. Output: Word and PDF, named CLN4U_Lesson01_What_Is_Law.docx, plus CLN4U_Review.md listing
   everything drafted or derived for you to check before submitting. Say if you want something different.

Reply "go" to accept everything as shown.
```

## Clickable choices

Where the interface can put choices in front of the teacher (the AskUserQuestion tool in Claude Code, or clickable choices on claude.ai when they appear), send part A as the text above and offer the rest as choices in the same round: part B as one multi-select question ("Which of these may I fill in?", one option per gap, up to four; more gaps stay in the text with their numbers), and part C as one question (Word and PDF, Word only, PDF only). The teacher's reply to the choices is the round's answer, and a typed answer counts the same. Where no such tool is available, the one text message above is the whole interview.

## Draft mode

When the teacher asks for a type they do not have (weekly plans from an outline, a unit plan from a course code and a topic), say so plainly, then interview for the facts only the teacher knows and draft the rest from the related documents and the bundled curriculum (`python3 scripts/curriculum.py <CODE>` and `--strand <letter>`; never open the files under `assets/curriculum/` directly). Every drafted section is listed in the review file. If the course code is not in the bundle, ask the teacher to paste the expectations, or leave the field blank and list it as a gap. Draft mode never invents a person's name, a date, or a mark weight.

## Several documents in one request

When the teacher asks for more than one type at once (a long range plan, a course outline, and the unit plans), run one combined interview: part A grouped by document, part B numbered continuously across the documents, and one C line naming every output file and the single review file. The teacher replies by item number. Do not run one interview per document.

## Derivations that need no question

- Grade band from the course code suffix: D Academic, P Applied, U University Preparation, C College Preparation, M University/College Preparation, O Open, W De-streamed, E Workplace Preparation. Grade from the fourth character: 1 = 9, 2 = 10, 3 = 11, 4 = 12.
- Final-mark buckets from the grade (2026 Growing Success model, `Teaching/Standards/assessment/growing-success-summary.md`): Grades 9 and 10: classroom 65, final evaluation 20, attendance 15. Grades 11 and 12: 65, 25, 10. The exam versus culminating split comes from the subject matrix in that document; exam-exempt categories are listed there.
- Achievement-chart default weighting: K/U 25, Thinking 30, Communication 20, Application 25.
- The second category's name follows the course's own curriculum document: "Thinking and Investigation" for Science (SNC, SBI, SCH, SPH, SVN) and Science and Technology, "Thinking" everywhere else including Computer Studies. The course code decides it, so never ask; correct a source that uses the other subject's name rather than confirming it.
- Credit value 1.0 and 110 hours unless the source says otherwise.
- When running inside a course repo with `course.yaml`, every field in it prefills Confirm. `teacher_formal` is the name for the document; when the sources disagree on the teacher's name (an upper-case plan header, a `Br.` form in week plans, a formal name in `course.yaml`), show the formal name under Confirm with all the forms found, so the teacher settles it once.
- A course's instance (`instances/<sem>/`) outranks its master when they disagree on weights or dates: use the instance values and show the disagreement under Confirm, marked high-risk in the review file.

## Question sets by type

Only the items the source lacks become gaps; the rest are prefilled and confirmed.

### lesson
Confirm: course code and title; unit; lesson N of M; duration; badge; achievement categories; phase names and minutes (flag when the minutes do not sum to the duration). Gaps: success criteria; differentiation columns; Google Classroom connections; the teacher/student split of materials.

### unit
Confirm: course; grade; unit title and number; number of days; culminating task and its due point; core texts; strands. Gaps: big idea, enduring understandings, essential question; the assessed versus covered split ("may I split the listed expectations by which ones your assessment tasks name?"; for a pipeline build the parser applies the rule in `unit_schema.md` and shows the result under Confirm); achievement descriptions; reflection exemplars; the variety-of-experiences checklist ("may I tick the strategies your lesson table names?"). A pipeline build also shows under Confirm: the compact lesson-row wording, and any unit weight where the instance plan differs from the master overview.

### course_outline
Confirm: title, code, type, grade, prerequisite, curriculum document (from the curriculum extract when available); department; Developed By (default the school) and Date Developed (default this month and year); Revised By and Date (blank unless given); the three final-mark buckets for the grade band and whether the final evaluation is exam only or exam plus culminating; the achievement-chart weighting; the unit list with hours, which must total 110 (shown with its sum). Gaps: the unit sequence itself ("may I propose four to six units from the strands, hours summing to 110?"); the nine program-planning considerations tailored to the subject; the Islamic Perspective bullets; textbook and online resources; whether to include the optional Chapters column, and the optional "Obtaining Extra Help" and "Homework" policy sub-sections.

### long_range_plan
Confirm: course line and code; semester (read from the instance folder name when the plan lacks it); pathway (from `course.yaml` or the course code); teacher (never guessed; a gap if absent; the formal name when `course.yaml` has one); unit start and end dates; the weights (shown with their sum, which must reach 100). Gaps: evaluation titles missing for a row; due dates given as slot IDs without a calendar ("may I leave these as slot IDs, or is there a calendar to convert them with?"); approximate unit end dates.

### weekly_plan
Confirm: course, unit, week N of M, dates, duration per class, teacher; day titles and their order; learning skills and achievement categories; expectation codes. Gaps: Islamic expectations and character education (offered, but they default to "leave blank" even on "fill all" unless the teacher numbers them, because teachers usually prefer their own words); expectation wording beside bare codes; success criteria; the AFL / AAL / AOL lists; differentiation.

### exam_cover
Confirm: division; semester and exam period; month and year; course name and code; teacher; date, time, room; page count; total weight; category marks. Everything else is a fill-in rule, not a gap: this document is meant to be completed by hand where the teacher leaves blanks.

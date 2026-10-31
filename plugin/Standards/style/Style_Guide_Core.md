# GLA Course Standards: Style Guide Core

**Purpose:** the shared rulebook for anyone (human or AI) writing or editing GLA master course materials. Every content decision that applies across *all* GLA courses lives here. Course-specific decisions live in each course repo's local Style Guide (the *course layer*, see §13). If a rule is in neither place, it isn't a rule.

**School:** Gibraltar Leadership Academy (GLA)
**Teacher:** Br. Zaid

---

## 1. The master/instance model

- Each course repo has a **master** (`master/`) that is date-agnostic. No file in `master/` may contain a calendar date, a weekday name tied to content, or a semester-specific reference. Dates belong only to generated instances (`instances/<semester>/`).
- Every day of a course has a stable **slot ID**: `U<unit>.W<week>.D<day>` (e.g., `U2.W3.D1`), with course-defined prefixes for non-unit blocks (e.g., `CP.W1.D1` for a culminating project, `INTRO.D1` for course-intro days, `R.D1` for a review week). The course layer lists its slot blocks.
- Slot IDs are frozen once the course architecture phase is committed. Never renumber. If content moves, update the week plan, not the ID scheme.
- Rehydration (see `rehydration/Rehydration_Framework.md` here, plus the course's parameter layer) maps slots to dates and generates an instance. Nothing in a master ever needs editing to start a new semester.

## 2. Weekly rhythm

Each unit week follows this **default** pattern (60-minute periods; **plan all lesson flows for ~50 usable minutes**, attendance and settling eat the rest). A course layer may declare per-block rhythm variants (e.g., a studio rhythm for practice-heavy units), provided every variant preserves the invariants: D4 is the submission day, D5 is flex (designed slack, first to cut), and the sub-readiness duties of §8.

| Day | Type | What happens | Sub-ready? |
|-----|------|--------------|------------|
| D1 | `teach` | New concept: whiteboard + analogy, slide deck, live demo | No |
| D2 | `exercise` | In-class exercise on D1's concept | **Yes** |
| D3 | `teach` or `lab` | Second concept teach (with deck) or guided lab/practice | No (teach) / Yes (lab) |
| D4 | `exercise` | Exercise work + submission; includes a 5-minute refresher recap of the week's concept | **Yes** |
| D5 | `flex` | Review, Q&A, catch-up, extension | **Yes** |

- `day_type` values: `teach`, `lab`, `exercise`, `studio`, `flex`, `assess`.
- `studio` days are self-directed work periods producing **divergent output**: students apply the current technique to their own piece, working from a `BRIEF_` sheet (a creative prompt with hard technical requirements, see §5). `lab` remains guided, convergent practice. Studio days are sub-ready like exercise days; studio submissions use the /10 scale, with the brief's `_MARKING.md` defining "complete."
- D5 flex days are the designed slack: rehydration cuts them first when the calendar is tight. Never put unique required content on a flex day.
- Assessment weeks replace days with `assess`/review days as defined in the week plan (typical pattern: D1 teach · D2 formative exercise · D3 review + assignment due · D4 test · D5 flex).

## 3. Voice and tone

**Student-facing materials** (exercises, assignments, tests, reference sheets, slides):
- Direct address ("you"), clear and encouraging, grade-appropriate for the course.
- Humor and creative scenarios welcome, they can be far-fetched if it helps engagement.
- Explain technical terms on first use. No unexplained jargon, no condescension.
- **No emojis.**

**Punctuation (all materials, student-facing and teacher-facing, and the templates authors copy from):**
- No em-dashes. Use a comma or parentheses instead. En-dashes are fine for numeric ranges (7-10 days).

**Teacher-facing materials** (lesson files, marking notes, week plans):
- Concise and practical. Write for a teacher skimming 5 minutes before class.
- Include the whiteboard diagram descriptions, analogies, and live-coding/demo scripts explicitly, these are the heart of the teaching style.

## 4. Content rules

- **Islamic names in all examples and scenarios** (e.g., Omar, Khalid, Maryam, Yusuf, Aisha, Bilal, Zaynab, Hamza). Refer to the teacher as "Br. Zaid".
- **Avoid:** music references, dating/romance themes, food-based activities, LEGO activities.
- Content stays within Islamic norms (this also governs any game/story scenarios).
- **No course narrative.** Scenarios are standalone per document, no recurring storyline, company, or career arc, and no references to "your journey" across documents.
- **Self-contained documents.** No "as you saw last week", no "coming up next unit", no references to specific assignments/tests from lessons or slides (the week plan carries the schedule, not the content).
- Real-world analogies encouraged everywhere.

## 5. File naming and layout

- Folders: `U1_<Unit_Name>/W2_<Week_Title>/`, unit-relative week numbers, Title_Case_With_Underscores.
- Day lessons: `D1_Lesson_<Topic>.md`.
- Slide decks: `D1_Slides_<Topic>.html`, one per `teach` day, same topic string as the lesson.
- Exercises: `EX_<Topic>.md` + `EX_<Topic>_KEY.md` (live in the week folder they're assigned in).
- Studio briefs: `BRIEF_<Topic>.md` + `BRIEF_<Topic>_MARKING.md` (studio weeks; never a `_KEY`, output is divergent by design).
- Reference sheets: `REF_<Topic>.md`.
- Week plans: `week_plan.yaml` (one per week folder). Weeks without their own folder (e.g., project build weeks) use `week_plan_W<n>.yaml` at the module root.
- Other sanctioned day-file types: `D<n>_Lab_<Topic>.md` (guided labs), `D<n>_Activity_<Topic>.md` and `D<n>_Workshop_<Topic>.md` (structured non-exercise days), `D<n>_Exercise_Work_Time.md` / `D<n>_Submission_and_Debrief.md` (brief plan-style sheets). Open-response exercises may ship `EX_<Topic>_MARKING.md` (marking notes) instead of a `_KEY.md`.
- Unit assessment: `Assessment/Assignment_<Name>/` (instructions.md, rubric.csv, rubric.md, marking_notes.md) and `Assessment/Test/` (test.md, test_KEY.md, coverage_table.md, review_sheet.md).
- No version suffixes (`_v2`, `_final`, `_enhanced`), ever. Git is the version history.

## 6. Curriculum expectation codes

- Each course keeps a `Curriculum_Coverage_Map.md` with its local canonical numbering of Ministry expectations (the Ministry leaves specific expectations unnumbered; the course's numbering is the local convention).
- **Every lesson, exercise, assignment, and test carries its expectation codes in its header block.** This makes compliance mechanically greppable (`grep -r "A1.2" master/`).
- If you touch what a document covers, update the course's coverage map in the same change.

## 7. Grading conventions

Shared grading rules, the /10 exercise scale, assignment and Google Classroom rubric conventions, test format, stretch goals, academic integrity, live in `assessment/Grading_Conventions.md` in this package. Per-course weighting tables and evaluation calendars live in the course's `Assessment_Plan.md`.

## 8. Substitute-teacher readiness

- Every `exercise`, `lab`, `studio`, and `flex` day must be runnable by a substitute with no subject background.
- Every exercise sheet and studio brief ends with a boxed section titled **"Running this class with a substitute"**: what to hand out, what students should be doing, what "done" looks like, and what to collect. Write it for someone who has never seen the course.
- `teach` days are **not** sub-ready by design. If the teacher is absent on a teach day, the rehydrated calendar's guidance is to swap the teach day with the week's next exercise/flex day.
- Generic any-day packets live in each course's `master/00_Admin/Emergency_Sub_Packets/` for unplanned absences.

## 9. Slide decks

- One deck per `teach` day. Authored per `decks/Slide_Deck_Instructions.md` (the authoritative deck prompt), styled by `decks/Slide_Deck_Template.html` (GLASS design system tokens).
- Deck carries ~25–35 minutes of the ~50-minute lesson; the rest is discussion and live work outside the deck.
- First non-title slide is always learning goals + curriculum expectations.
- Minimal text, visual-first, one major point per slide, 15–25 slides, 2–3 interactive checkpoints.

## 10. Code conventions

- Every code sample in any course material must compile/run as written, no pseudocode presented as real code.
- Only use language features already taught by that slot. Each course layer defines its feature-availability ordering (what is known by which unit/week).
- Language-specific conventions for GLA's Java courses live in `style/Java_Conventions.md` in this package.

## 11. Markdown document headers

Every content document starts with a header block:

```markdown
# <Title>

**Slot:** U2.W3.D1 · **Type:** teach
**Expectations:** A1.3, A3.1
**Time:** ~50 min
```

(Exercises add `**Marks:** /10`; assignments add points and window length; tests add total marks. Reference sheets carry expectations plus a `**Course:**` line.)

Student-facing assessment documents (an assignment's `instructions.md`; a test's `test.md`, `review_sheet.md` and `test_reference.md`) carry no `**Expectations:**` line. Their codes live in the teacher-side records: the `## Expectations assessed` table in the assignment's `marking_notes.md` (one row per rubric criterion) and the test's `coverage_table.md`. The coverage map's Assessed in cells must agree with both.

## 12. Consistency duties

- When you change one document, check its week plan, unit overview, and the coverage map for knock-on updates.
- New files must be added to the course's `MASTER_INDEX.md`.
- Flag (don't silently fix) anything that contradicts this guide, the course layer, or the approved plan.

## 13. The course-layer contract

Each course repo's `master/01_Standards/Style_Guide.md` is a thin local layer that **references this file by absolute path** and supplies only:

1. **Course identity:** course code, full name, grade, pathway, language/tools line.
2. **Slot blocks:** the course's unit/week structure and any non-unit prefixes (INTRO, R, CP, standby modules), plus where its architecture is frozen.
3. **Feature-availability ordering:** what students know by which slot (governs §10's only-taught-features rule). The data lives in `master/01_Standards/feature_availability.yaml`; the course Style Guide's table is rendered from it (`gla features render`), and `run_samples.py` checks code samples against it.
4. **Course-specific content rules:** anything true of this course only (e.g., prerequisite assumptions, project constraints, pointers to `PROJECT_DECISIONS.md`).
5. **Pointers:** to the course's `Curriculum_Coverage_Map.md`, `Assessment_Plan.md`, and rehydration parameter documents.

A course layer may **tighten** a shared rule; it may not contradict one. If a shared rule needs to change, change it here (with a CHANGELOG entry), never fork it locally.

# GLA Course Standards: Style Guide Core

**Purpose:** the shared rulebook for anyone (human or AI) writing or editing GLA master course materials. Every content decision that applies across *all* GLA courses lives here. Course-specific decisions live in each course repo's local Style Guide (the *course layer*, see §13). If a rule is in neither place, it isn't a rule.

**School:** Gibraltar Leadership Academy (GLA)
**Teacher:** the course's `teacher` in course.yaml (Br. Zaid in the Computer Studies courses)

---

## 1. The master/instance model

- Each course repo has a **master** (`master/`) that is date-agnostic. No file in `master/` may contain a calendar date, a weekday name tied to content, or a semester-specific reference. Dates belong only to generated instances (`instances/<semester>/`).
- Every day of a course has a stable **slot ID**: `U<unit>.W<week>.D<day>` (e.g., `U2.W3.D1`), with course-defined prefixes for non-unit blocks (e.g., `CP.W1.D1` for a culminating project, `INTRO.D1` for course-intro days, `R.D1` for a review week). The course layer lists its slot blocks.
- Slot IDs are frozen once the course architecture phase is committed. Never renumber. If content moves, update the week plan, not the ID scheme.
- Rehydration (see `rehydration/Rehydration_Framework.md` here, plus the course's parameter layer) maps slots to dates and generates an instance. Nothing in a master ever needs editing to start a new semester.

## 2. Weekly rhythm

Each unit week follows this **standard** rhythm (60-minute periods; **plan all lesson flows for ~50 usable minutes**, attendance and settling eat the rest). The other rhythm is **studio**, for practice-heavy units (see `studio` below). Every unit overview names its rhythm on a `**Rhythm:** standard` or `**Rhythm:** studio` line, and the checks refuse any other value. Both rhythms keep the invariants: D4 is the submission day, D5 is flex (designed slack, first to cut), and the sub-readiness duties of §8.

| Day | Type | What happens | Sub-ready? |
|-----|------|--------------|------------|
| D1 | `teach` | New concept: whiteboard + analogy, slide deck, live demo | No |
| D2 | `exercise` | In-class exercise on D1's concept | **Yes** |
| D3 | `teach` or `lab` | Second concept teach (with deck) or guided lab/practice | No (teach) / Yes (lab) |
| D4 | `exercise` | Exercise work + submission; includes a 5-minute refresher recap of the week's concept | **Yes** |
| D5 | `flex` | Review, Q&A, catch-up, extension | **Yes** |

- `day_type` values: `teach`, `lab`, `wet_lab`, `exercise`, `studio`, `seminar`, `debate`, `field_trip`, `flex`, `assess`.
- `lab` is guided, convergent practice with no hazard beyond an ordinary classroom's (a computer lab, a dry lab, a data or worksheet lab). It is sub-ready.
- `wet_lab` is a hands-on lab with real hazards: chemicals, specimens, heat, glassware, sharps. It is never sub-ready, because a substitute cannot run it safely. Its `D<n>_Lab_<Topic>.md`, from `templates/Lab_Template.md`, carries the safety block and the non-lab activity a substitute runs instead.
- `seminar` and `debate` are student-led discussion days the teacher facilitates and assesses. `field_trip` is a day off-site, with forms, supervision and transport arranged ahead. None of the three is sub-ready; the week plan's `sub_fallback` names what a substitute runs instead (for a field trip, the in-class work for students who stay).
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
- Include the whiteboard diagram descriptions, analogies, and the demo script explicitly, these are the heart of the teaching style. The demo is live coding in a programming course, a technique demonstration in a science course, and a walkthrough of a source in a history course.

## 4. Content rules

- **Islamic names for every invented person** in examples and scenarios (e.g., Omar, Khalid, Maryam, Yusuf, Aisha, Bilal, Zaynab, Hamza). Real people (historical figures, authors, scientists, public figures) keep their real names. Refer to the teacher by the course's `teacher` value in course.yaml (for example "Br. Zaid").
- **Avoid:** music references, dating/romance themes, LEGO activities.
- **No food or drink in an activity.** Computer courses run in a lab, where food and drink near the machines is a hazard, so no activity has students bring, handle or eat food. Food is fine everywhere else: in examples, scenarios and analogies, and as a science-lab material when an expectation needs it (enzymes, digestion), never eaten.
- Content stays within Islamic norms (this also governs any game/story scenarios).
- **No course narrative.** Scenarios are standalone per document, no recurring storyline, company, or career arc, and no references to "your journey" across documents.
- **Self-contained documents.** A document may refer back to content taught earlier by name (a period, an event, a concept: "the Treaty of Versailles", "osmosis"). It never points at a specific week, lesson, assignment or test ("as you saw last week", "coming up next unit", "on the Unit 2 test"); the week plan carries the schedule, not the content.
- **Images.** An image is a local file in an `images/` folder beside the document or deck that uses it, referenced by relative path, with a credit line directly under it: `*Credit: <creator>, <source>, <licence>.*` Use public-domain or openly licensed images (CC0, CC BY, CC BY-SA) or the teacher's own. Never hotlink: a deck shown offline and a Google Docs handout both need the file.
- **Sources.** A lesson or handout that quotes or shows a primary or secondary source lists each one under a `## Sources` heading with a full citation.
- **Sensitive topics.** A lesson on a topic that can distress students (residential schools, genocide, racism, violence, abuse) carries a "Sensitive topic" block in its teacher notes: how to open the topic, how to respond to a disclosure, who to refer a student to, and the perspective guidance the lesson follows (for First Nations, Métis and Inuit histories, the curriculum's and the community's).
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
- Unit assessment: `Assessment/Assignment_<Name>/` (instructions.md, rubric.csv, rubric.md, marking_notes.md) and `Assessment/Test/` (test.md, test_KEY.md, coverage_table.md, review_sheet.md, test_reference.md).
- No version suffixes (`_v2`, `_final`, `_enhanced`), ever. Git is the version history.

## 6. Curriculum expectation codes

- Each course keeps a `Curriculum_Coverage_Map.md` with its local canonical numbering of Ministry expectations (the Ministry leaves specific expectations unnumbered; the course's numbering is the local convention).
- **Every lesson, exercise, brief and reference sheet carries its expectation codes in its header block.** An assignment or test keeps them in its teacher-side record instead (§11), since its student copy carries none. Either way compliance stays greppable (`grep -r "A1.2" master/`).
- If you touch what a document covers, update the course's coverage map in the same change.

## 7. Grading conventions

Shared grading rules, the /10 exercise scale, assignment and Google Classroom rubric conventions, test format, stretch goals, academic integrity, live in `assessment/Grading_Conventions.md` in this package. Per-course weighting tables and evaluation calendars live in the course's `Assessment_Plan.md`.

## 8. Substitute-teacher readiness

- Every `exercise`, `lab`, `studio`, and `flex` day must be runnable by a substitute with no subject background.
- Every exercise sheet and studio brief ends with a boxed section titled **"Running this class with a substitute"**: what to hand out, what students should be doing, what "done" looks like, and what to collect. Write it for someone who has never seen the course.
- `teach`, `wet_lab`, `seminar`, `debate` and `field_trip` days are **not** sub-ready by design. If the teacher is absent on one, the rehydrated calendar's guidance is to swap it with the week's next sub-ready day. When no swap fits, the substitute runs the day's fallback: the wet lab's non-lab activity, or the week plan's `sub_fallback`.
- Generic any-day packets live in each course's `master/00_Admin/Emergency_Sub_Packets/` for unplanned absences.

## 9. Slide decks

- One deck per `teach` day. Authored per `decks/Slide_Deck_Instructions.md` (the authoritative deck prompt), styled by `decks/Slide_Deck_Template.html` (GLASS design system tokens).
- Deck carries ~25–35 minutes of the ~50-minute lesson; the rest is discussion and live work outside the deck.
- First non-title slide is always learning goals + curriculum expectations.
- Minimal text, visual-first, one major point per slide, 15–25 slides, 2–3 interactive checkpoints.

## 10. Code and calculations

These apply to programming courses (course.yaml `language` set), except the last rule, which applies to every course.

- Every code sample in any course material must compile/run as written, no pseudocode presented as real code.
- Only use language features already taught by that slot. Each course layer defines its feature-availability ordering (what is known by which unit/week).
- A worked calculation in a key or a lesson (a Punnett ratio, a unit conversion, a concentration) sits in a fenced `calc` block, one `expression = answer` per line, so `gla samples` can evaluate it. An answer is never worked out by hand.
- Language-specific conventions for GLA's Java courses live in `style/Java_Conventions.md` in this package.

## 11. Markdown document headers

Every content document starts with a header block:

```markdown
# <Title>

**Slot:** U2.W3.D1 · **Type:** teach
**Expectations:** A1.3, A3.1
**Time:** ~50 min
```

(Exercises add `**Marks:** /10`; assignments add points and window length; tests add total marks. Reference sheets carry expectations plus a `**Course:**` line. A history, geography or civics lesson may add a `**Thinking concepts:**` line naming the curriculum's thinking concepts it uses, for example historical significance, cause and consequence.)

Student-facing assessment documents (an assignment's `instructions.md`; a test's `test.md`, `review_sheet.md` and `test_reference.md`) carry no `**Expectations:**` line. Their codes live in the teacher-side records: the `## Expectations assessed` table in the assignment's `marking_notes.md` (one row per rubric criterion) and the test's `coverage_table.md`. The coverage map's Assessed in cells must agree with both.

## 12. Consistency duties

- When you change one document, check its week plan, unit overview, and the coverage map for knock-on updates.
- New files must be added to the course's `MASTER_INDEX.md`.
- Flag (don't silently fix) anything that contradicts this guide, the course layer, or the approved plan.

## 13. The course-layer contract

Each course repo's `master/01_Standards/Style_Guide.md` is a thin local layer that **references this file as `GLA_ROOT/Standards/style/Style_Guide_Core.md`** and supplies only:

1. **Course identity:** course code, full name, grade, pathway, language/tools line.
2. **Slot blocks:** the course's unit/week structure and any non-unit prefixes (INTRO, R, CP, standby modules), plus where its architecture is frozen.
3. **Feature-availability ordering** (programming courses): what students know by which slot (governs §10's only-taught-features rule). The data lives in `master/01_Standards/feature_availability.yaml`; the course Style Guide's table is rendered from it (`gla features render`), and `run_samples.py` checks code samples against it.
4. **Course-specific content rules:** anything true of this course only (e.g., prerequisite assumptions, project constraints, pointers to `PROJECT_DECISIONS.md`).
5. **Pointers:** to the course's `Curriculum_Coverage_Map.md`, `Assessment_Plan.md`, and rehydration parameter documents.

A course layer may **tighten** a shared rule; it may not contradict one. If a shared rule needs to change, change it here (with a CHANGELOG entry), never fork it locally.

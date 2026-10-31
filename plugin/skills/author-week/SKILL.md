---
name: author-week
argument-hint: "U<n>.W<m> [D<n> | deliverable | ref | plan | guides]"
description: Author one week of a GLA course's master content — its week_plan.yaml, teach-day lesson docs, slide decks and their teacher guides, the week's exercise or studio deliverable, and its reference sheet. Use when the user wants to build out, write, draft, or author a specific week or unit's lessons (e.g. "author U5.W1", "write the Loops week", "build out Unit 3 week 2", "draft next week's lessons"), or the deck teacher guides on their own ("write the guides for U2"). For a single day or a single artifact, still use this skill scoped to that file.
---

# author-week — build one week of master content

## Locations

Every script runs through one command, written `gla` below: run it as `python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" <command> ...` from the course folder (on Windows, `python` when `python3` is not found). Run `gla where` once before the first command: it prints `GLA_ROOT`, the folder that holds the shared `Standards/`, `Curriculum/` and `Calendars/`, and paths written `GLA_ROOT/...` below are under it. A script that stops on a missing module means the computer needs `gla setup` (ask the teacher first; it installs Python packages). This skill is course-agnostic: every course-specific value comes from `course.yaml` at the root of the course repo you are working in (schema: `GLA_ROOT/Standards/templates/Course_Config_Schema.yaml`).

**Step 0, always:** read `course.yaml` from the course repo root. If it is missing, stop and tell the user the repo has no `course.yaml` (it predates the shared-skill layout, or it is not a GLA course repo). Do not guess course parameters.


You are authoring (or revising) one week of the master course named in `course.yaml`:
the date-agnostic teaching materials for a single `U<unit>.W<week>` block. The
output lands in that week's folder under `master/02_Units/`. This skill scaffolds
and writes the week's content; it does not touch dates, instances, or the
rehydration parameters.

## Authority documents (read these first, in order)

Shared package (the rules; never copy them into this repo):

1. `GLA_ROOT/Standards/style/Style_Guide_Core.md` — the rulebook. §2 weekly rhythm, §3 voice, §4 content rules, §5 file naming, §8 substitute-readiness, §9 slide decks, §11 header blocks.
2. `GLA_ROOT/Standards/style/<conventions_file>` — the code conventions for the course's language (`language` and `conventions_file` in `course.yaml`; a non-programming course sets both to null and this item does not apply). Every code sample must compile/run as written.
3. `GLA_ROOT/Standards/assessment/Grading_Conventions.md` — the /10 completion scale (exercises and studio ships) and its printed anchor table.
4. `GLA_ROOT/Standards/decks/Slide_Deck_Instructions.md` — the authoritative deck-authoring prompt; `decks/Slide_Deck_Template.html` supplies the byte-protected machinery.
5. The shared templates in `GLA_ROOT/Standards/templates/` — copy and fill: `Weekly_Plan_Schema.yaml`, `Day_Lesson_Template.md`, `Exercise_Template.md`, `Reference_Sheet_Template.md`.

Course layer (the parameters; read from this repo):

6. `master/01_Standards/Style_Guide.md` — this course's rhythms (which units are standard vs studio or other variants), feature-availability-by-slot table (rendered from `master/01_Standards/feature_availability.yaml`, the file to edit), and course-specific content rules.
7. `master/01_Standards/Curriculum_Coverage_Map.md` — the expectation codes this week teaches and assesses. Every artifact you write carries its codes in its header block; if you change what the week covers, update the map in the same edit.
8. `master/02_Units/U<n>_.../unit_overview.md` — the unit's frozen week architecture: what this specific week is for, its day-by-day slot notes, and the unit's evaluations.
9. `master/00_Admin/Assessment_Plan.md` — whether this week ships a graded artifact and what it is worth.

## Inputs

- **Which week** (required): a slot block like `U5.W1`, a unit + week, or a named week ("the Loops week"). Resolve it to the week folder under `master/02_Units/`. If ambiguous, ask. Invoked as `/author-week U3.W2 D3`, the arguments are `$ARGUMENTS`: take the week and the scope from them.
- **Scope** (optional): a single day (`D3`), a single artifact (`the reference sheet`, `just the deck`), or a revision of an existing week. Default is the whole week.

## What a week folder contains

Files sit flat in `master/02_Units/U<n>_<Name>/W<n>_<Title>/`. A fully authored week is:

- `week_plan.yaml` — one per week, filled from `Weekly_Plan_Schema.yaml`.
- `D<n>_Lesson_<Topic>.md` + `D<n>_Slides_<Topic>.html` — a lesson doc and its deck, **for teach days only** (typically D1 and D3; the `<Topic>` string matches across the pair).
- The week's deliverable, determined by the week's rhythm (from the course layer):
  - **exercise-rhythm week:** `EX_<Topic>.md` + `EX_<Topic>_KEY.md` (teacher key).
  - **studio-rhythm week:** `BRIEF_<Topic>.md` + `BRIEF_<Topic>_MARKING.md` (teacher marking notes; never a `_KEY` — studio output is divergent by design).
- `REF_<Topic>.md` — the week's student reference sheet.

Non-teach days (exercise, studio, flex) generate no per-day file: they run off the deliverable and the reference sheet. **Assignments and tests are NOT authored here** (use `author-assessment`): they live in the unit-level `master/02_Units/U<n>_.../Assessment/` folder and are a separate job.

## Workflow

0. **Scaffold the week.** Run `gla week U<n>.W<m>` from the course root (`--dry-run` first if the week already has files; `--only D3` for a single day). It resolves the folder, rhythm, teach days, file names, and the codes the coverage map assigns, then writes `week_plan.yaml` and correctly named lesson, deliverable, and reference stubs with their header blocks filled. It never overwrites a file. Check its report: it names where each code came from and anything it could not resolve. Rename a `<Topic>` token when the course's short form differs (both files of a teach-day pair together).
1. **Resolve and read context.** Identify the week folder. Read the unit's `unit_overview.md` for this week's purpose and day-by-day plan, the course `Style_Guide.md` for the week's rhythm and the features available by this slot, and the coverage map for the expectation codes this week owns. Never introduce a language feature not yet available by this slot (Style Guide Core §10). Then run `gla backlog --slot U<n>.W<m>`: it lists the teaching-log notes the teacher marked "fix in master" for this week and the days logged as partly taught. Make each requested change that falls in this run's scope, and after it, record it with `--resolve <semester> <slot> --change "<one line>"` (which writes `master/backlog.yaml`). Name any request you leave open in the review sheet.
2. **Plan the week.** From the rhythm, list the days and their `day_type`s, which days are teach days (get a lesson + deck), and the single deliverable. Confirm the plan with the user before writing if the unit_overview leaves the week's shape open: offer the two or three shapes that fit the rhythm as one AskUserQuestion. **Asking the teacher.** In Claude Code, ask a decision that has a few known answers with the AskUserQuestion tool (up to four questions per call, two to four options each, your recommendation first and marked; the teacher can always type another answer). Ask free values (names, dates, counts) in a plain message. Where the tool is not available, ask in one message.
3. **Write `week_plan.yaml`** from the schema: fill metadata, the Islamic-expectations and character-education blocks, learning skills, achievement categories, the expectation codes (codes only — wording lives in the coverage map), learning goals with success criteria, the daily_lessons array (one entry per day, ~50 usable minutes, 3–4 timed activities each; on teach days give each activity its `teacher` and `student` keys beside `what`, so unit plans can split their teacher and student columns), assessment strategies, and the evaluations entry for the week's ship. Dates stay as `{{...}}` placeholders — this is a master.
4. **Write the teach-day lesson docs** from `Day_Lesson_Template.md`: header block, learning goals + success criteria, materials, the lesson-flow table, and the teacher notes that are the heart of the style — whiteboard diagram descriptions, the core analogy, the live-coding/demo script (including any deliberate bug to debug), common misconceptions, checkpoint questions with answers, and the end-of-week refresher blurb.
5. **Author the decks** for each teach day per `Slide_Deck_Instructions.md`: plan the chapters and slides first, then write only the slides as a fragment file (start it with `<!-- auto: title -->` and `<!-- auto: goals -->`, which the assembler builds from the lesson) and assemble with `gla deck <week folder>/D<n>_Slides_<Topic>.html --from <fragment>`. Set `data-deck-theme` nowhere by hand: the assembler reads `deck_theme` from `course.yaml`. To revise an existing deck, edit its slides and run `--rebuild`. Fix every ERROR it prints; WARN lines (slide count, code over 6 lines, a slide pointing past this lesson) need a reason to stay.
5a. **Write each deck's teacher guide**, `D<n>_Slides_<Topic>_GUIDE.md` beside the deck, per `Slide_Deck_Instructions.md` (Companion teacher guide), from the deck (`build_deck.py --extract` lists its slides) and the lesson only: the `**Deck:** N slides` header line, Before you start, Timing waypoints, a `**Slide n (name).**` paragraph for every slide with its checkpoints' expected and common wrong answers, the lesson's misconceptions, and checkpoint answers at a glance. Any change to a deck's slides updates its guide in the same change (numbering included). **Guides-only mode** ("guides for U2", "write the missing deck guides"): do just this step for every deck in scope that lacks a guide or whose guide `check_course.py` flags (`deck-guide`, `guide-slides`); change no deck or lesson.
6. **Write the deliverable.** Exercise-rhythm: `EX_<Topic>.md` (from `Exercise_Template.md`, with the printed /10 table and the "Running this class with a substitute" box) plus its `_KEY.md` with full, compiling solutions and a marking guide. Studio-rhythm: `BRIEF_<Topic>.md` (the creative prompt with hard technical requirements, the /10 checklist, and the substitute box) plus its `_MARKING.md` teacher companion.
7. **Write `REF_<Topic>.md`** from `Reference_Sheet_Template.md`: one page, dense and scannable, tables and minimal compiling examples, a common-mistakes list.
8. **Register and cross-check.** Add every new file to `master/MASTER_INDEX.md`. Confirm the coverage map reflects what this week teaches/assesses. Verify header blocks, expectation codes, feature-availability, and sub-readiness boxes per the self-check below.

## Hard rules

- **Date-agnostic.** No calendar date, weekday, or semester reference in any master file. Dates are `{{...}}` placeholders that rehydration fills.
- **Only-taught features.** Every code sample uses only language features available by this slot (course layer's feature-availability ordering) and must compile/run as written — no pseudocode dressed as code.
- **Executed output only.** Run `gla samples <week folder>` before handing back: it compiles and runs every Java sample with `main`, feeds shown input, compares shown output, `node --check`s p5.js, and warns on features used before their slot. Any code shown together with its textual output — demo scripts, exercise keys, deck examples — must have that output produced by actually running the code (in the scratchpad) and pasted verbatim. Never hand-write expected output. Where output is visual and cannot be pasted (canvas, GUI), describe the behaviour instead (a `describe()` string or a one-line caption) — never fabricate a screenshot or invent console text that a visual program does not print.
- **Teacher notes are the deliverable, not a formality.** Every teach-day lesson's teacher-notes section carries all six elements with real substance: concretely drawable whiteboard diagram(s) (what boxes, what labels, what arrows, drawn when); the core analogy spelled out in a sentence or two, not merely named; an ordered live-coding/demo script including a deliberate error to surface and fix wherever the topic supports one; common misconceptions each paired with its correction; checkpoint questions with expected answers; and the end-of-week refresher blurb. A lesson with a bare demo script or a hand-waved analogy is incomplete — hold it to the depth of the strongest existing lessons in the course, not to the presence of the headings.
- **Category names come from the course's own curriculum document.** The second achievement-chart category is **Thinking** in Computer Studies (ICD2O, ICS3U, ICS4U) and **Thinking and Investigation** in Science. Write it that way in `achievement_categories` and anywhere a coverage table or rubric spells the category out. The `K/T/C/A` shorthand is the same in both. See `Standards/assessment/Grading_Conventions.md` §Naming the second category.
- **Codes in every header, map stays in sync.** Every lesson, exercise, brief, and reference sheet carries its expectation codes in its header block; changing coverage means editing `Curriculum_Coverage_Map.md` in the same change.
- **Legacy codes are never reused.** When a lesson adapts legacy material (an Adapt or Mine verdict in `master/00_Admin/Legacy_Reuse_Map.md`), take its codes from the coverage map and the curriculum data. Codes printed in the legacy file are dropped, however plausible they look; they often come from a superseded curriculum.
- **Rhythm decides the deliverable.** Exercise weeks ship `EX_`/`_KEY`; studio weeks ship `BRIEF_`/`_MARKING`. A studio brief never has a `_KEY` — its output is divergent by design.
- **Teach days only get lesson + deck.** Do not author per-day files for exercise/studio/flex days; they run off the deliverable and the reference sheet.
- **Substitute-readiness.** Every exercise sheet and studio brief ends with the boxed "Running this class with a substitute" section, written for someone with no subject background (Style Guide Core §8).
- **Content rules.** Islamic names in every scenario, Br. Zaid for the teacher; standalone documents with no course-wide narrative and no cross-references to other weeks/units/assignments; no emojis; plus every rule the course layer tightens.
- **No assignments or tests here.** Those are unit-level artifacts in `Assessment/`, authored with the `author-assessment` skill; do not create them in the week folder.
- **No version suffixes** (`_v2`, `_final`) — git is the history. Register new files in `MASTER_INDEX.md`.

## Self-check (run before handing back)

Run `gla check --changed` and `gla samples <week folder>` from the course root first. `--changed` keeps the findings in the files git shows as changed or new, so old warnings elsewhere in the course stay out of the way. In a course folder without git, pass the files this run wrote with `--paths FILE...` instead. It checks the structural items below (lesson and deck pairs, deliverable companions, header codes against the curriculum, the week plan schema and its unfilled values, template placeholders left in a body, the substitute box, the /10 table, em dashes and emojis). Fix every error it reports in the files you wrote; report findings in files you did not touch instead of fixing them. A warning you keep needs a reason in the file itself: `<!-- gla-allow: deck-length short studio deck -->` (in YAML, `# gla-allow: weekplan-minutes double period`). The check then lists it as allowed with that reason. Errors cannot be allowed. The script cannot judge teacher-note depth, analogies, or whether code runs; those items stay yours.

- Every teach day has a matching `D<n>_Lesson_` and `D<n>_Slides_` with the same `<Topic>` string; no per-day file exists for non-teach days.
- `week_plan.yaml` day count and `day_type`s match the course rhythm; `sub_ready` is true for exercise/lab/studio/flex days; activity minutes total ~50, and each teach day's lesson-flow table agrees with that day's `week_plan.yaml` activities.
- Every teach-day lesson's teacher notes carry all six elements with real substance: drawable diagram(s), the analogy spelled out, a demo script (with a deliberate error where the topic supports one), misconceptions each with a correction, checkpoint questions with answers, and a refresher blurb.
- Every expectation code in the week plan appears in at least one artifact's header, and each is a code the coverage map assigns to this week.
- Deck opens in a browser, first non-title slide is goals + codes, 15–25 slides, machinery copied byte-for-byte.
- All code compiles; no feature is used before its slot; any code paired with textual output was actually run and its output pasted verbatim (visual output is described, not fabricated).
- Deliverable carries the printed /10 table and the substitute box; a `_KEY` (exercise) or `_MARKING` (studio) companion exists.
- New files are in `MASTER_INDEX.md`.

## Review sheet (end every run with it)

Close the reply with this block, filled in, so the teacher can review the week in one screen:

```markdown
**Review sheet: U<n>.W<m>**
- Slots: U<n>.W<m>.D1 to D<k> (teach days D1, D3)
- Codes: the codes this week teaches and assesses, from the coverage map
- Files written: one per line, new or changed
- Warnings kept: each with its code, file and the gla-allow reason (or "none")
- Backlog: requests resolved in this run, and any left open with why
- Assumed without asking: choices the teacher did not make (an example's context, topic order, a feature held back)
- Check by eye: claims no script verifies (a fact or statistic, a described visual output, a timing estimate)
```

---
name: author-assessment
argument-hint: "U<n> [assignment | test]"
description: Author a GLA course unit's summative assessments in its master. The unit assignment (instructions.md, marking_notes.md, and its rubric through gc-rubric) and the unit test (test.md, test_KEY.md, coverage_table.md, review_sheet.md, test_reference.md). Use when the user wants to write, draft, build, revise, or check a unit assignment or a unit test, its answer key, coverage table, review sheet, or test aid sheet (e.g. "write the Unit 3 test", "draft the U2 assignment", "make the test key for Unit 4", "build the review sheet", "check the U1 test adds up"). Do NOT use for weekly exercises, studio briefs, lessons, or decks (author-week), for a rubric on its own (gc-rubric), for the culminating project or the final exam, or for Google Docs handouts (semester).
---

# author-assessment: a unit's assignment and test

## Locations

Every script runs through one command, written `gla` below: run it as `python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" <command> ...` from the course folder (on Windows, `python` when `python3` is not found). Run `gla where` once before the first command: it prints `GLA_ROOT`, the folder that holds the shared `Standards/`, `Curriculum/` and `Calendars/`, and paths written `GLA_ROOT/...` below are under it. A script that stops on a missing module means the computer needs `gla setup` (ask the teacher first; it installs Python packages). This skill is course-agnostic: every course-specific value comes from `course.yaml` at the root of the course repo you are working in (schema: `GLA_ROOT/Standards/templates/Course_Config_Schema.yaml`).

**Step 0, always:** read `course.yaml` from the course repo root. If it is missing, stop and tell the user the repo has no `course.yaml` (it predates the shared-skill layout, or it is not a GLA course repo). Do not guess course parameters.

You are authoring the summative work for one unit of the master course: its assignment folder `master/02_Units/U<n>_*/Assessment/Assignment_<Name>/` and its test folder `master/02_Units/U<n>_*/Assessment/Test/`. Both are date-agnostic: slots, never dates.

## Authority documents

Read item 4 and the course layer (5 to 8) first. Read items 1 to 3 at the step that uses them, and only the part named: they are long, and most of each is not about this job.

Shared package (the rules; never copy them into the course):

1. `GLA_ROOT/Standards/templates/Assignment_Template.md` (writing the assignment): every assignment opens with `## Learning goals`, then the scenario, requirements, a sample run, stretch goals, submission, integrity, and how it is assessed.
2. `GLA_ROOT/Standards/templates/Test_Template.md` and `Test_Reference_Template.md` (writing the test): the test's parts (course.yaml `test_parts`, A and B by default: A multiple choice, every later part written), the companion files, and the one-page aid sheet.
3. `GLA_ROOT/Standards/assessment/Grading_Conventions.md`, its Assignments and Tests sections and "Naming the second category" (the category name, levels, and what never goes into a mark: learning skills, lateness). The Growing Success summary is the source behind it; open it only for a policy question those sections do not answer.
4. `GLA_ROOT/Standards/style/Style_Guide_Core.md` §3 voice, §4 content rules, §5 naming, §11 header blocks, and the course's `<conventions_file>` for code.

Course layer (read from the repo):

5. `master/02_Units/U<n>_*/unit_overview.md`: the unit's `**Weight:**` split and its `## Evaluations` table (the assignment's hand-out and due slots, the test's slot).
6. `master/00_Admin/Assessment_Plan.md`: points, bonus, and test marks for this course.
7. `master/01_Standards/Curriculum_Coverage_Map.md`: the codes this unit's assignment and test assess ("Assessed in").
8. The unit's lessons, exercises, and `REF_*.md` sheets: an assessment tests only what the unit taught, at the slot it was taught.

## Workflow

Invoked as `/author-assessment U3 test`, the arguments are `$ARGUMENTS`: take the unit and the assessment from them, and ask only for what is missing. Before writing either assessment, run `gla backlog --slot U<n>`. A day logged as partly taught names content the class may not have had; tell the teacher which questions or requirements touch it, and ask (AskUserQuestion in Claude Code) whether to keep, soften, or drop each. Record what you changed with `--resolve` only when the change settles the note in master.

### Assignment

1. **Scaffold.** `gla assessment U<n> assignment [--name <Name>]` from the course root. It reads the overview's Evaluations table, the Assessment Plan, and the coverage map, and writes `instructions.md` and `marking_notes.md` with their headers filled. It never overwrites; `--dry-run` shows what it would write. It exits 1 when its report lists something it could not resolve, and 2 when the unit or its Evaluations row cannot be worked from. Read its report for where each code and number came from.
2. **Write `instructions.md`** from the template: 3 to 5 learning goals in student language, a self-contained scenario (Islamic names, no course-wide storyline), requirements as observable behaviour with checkboxes, a sample run produced by actually running a model solution (a programming assignment; a lab report or essay states what the finished piece contains instead), two stretch goals, submission, integrity, assessment.
3. **Write `marking_notes.md`** (teacher only): a marking workflow (run it first, with the inputs to feed), the requirements checklist, what each level looks like per category, common errors, and how bonus is applied. It ends with `## Expectations assessed`: one row per rubric criterion (`| Rubric criterion | Category | Expectation codes |`), naming the codes that criterion evaluates. This table, not the student-facing header, is the assignment's coverage record.
4. **Build the rubric** with gc-rubric: `gla rubric --from-assignment <folder> --spec-out /tmp/rubric.json`, write the criteria and descriptors into the spec, then `... /tmp/rubric.json --out <folder> --name rubric`. Follow gc-rubric's SKILL.md for the descriptors and the type (`lab_report` for a science lab report, `essay` for an argued written piece).

### Test

1. **Scaffold.** `gla assessment U<n> test` writes `test.md`, `test_KEY.md`, `coverage_table.md`, `review_sheet.md`, and `test_reference.md` with their headers.
2. **Write `test.md`** with exactly the parts in `course.yaml`'s `test_parts`. Part A: one-mark questions, four options lettered A to D, one option per source line, exactly one correct. Part B and any later part: written items, each headed with its letter and marks (`**B1. Tracing (5 marks)**`, `**C1. Extended response (10 marks)**`). The item kinds follow the subject: trace, find-the-error, write-a-fragment and explain in a programming course; label-the-diagram, calculations and explain in science; source analysis, short and extended response in history. In a two-part test Part A is about 40 to 50% of the marks. An image follows Style Guide Core §4 (a local file with its credit). Questions are self-contained, use only what the unit taught by its test slot, and carry no answers (the student copy is made mechanically).
3. **Write `test_KEY.md`**: every Part A letter, every written answer with accepted variations and how marks are split. Any code with its output: run it. Every calculation sits in a `calc` block, which `gla samples` evaluates.
4. **Write `coverage_table.md`**: `gla test <Test folder> --skeleton` prints one row per question with its marks to start from; fill one row per question, `| Question | Expectation codes | Category | Marks |`; split a question into rows (B5a, B5b) when its parts assess different codes. Every code the unit teaches appears at least once, on the test or (say so) on the assignment.
5. **Write `review_sheet.md`** (student-facing, used on the review day): topics, sample questions that are not the test's questions, and pointers to the unit's reference sheets.
6. **Write `test_reference.md`** from its template: one page of syntax and tables the unit taught, condensed from the `REF_*` sheets; nothing the test asks students to recall.

## Hard rules

- **No codes on student-facing documents.** `instructions.md`, `test.md`, `review_sheet.md`, and `test_reference.md` carry no `**Expectations:**` line (Style Guide Core §11). The codes live in `marking_notes.md`'s table and the test's `coverage_table.md`.
- **The coverage map agrees.** Every code in an assignment's table or a test's coverage table appears in that code's Assessed in cell of the coverage map, and every assessment the map names really evaluates the code. When you add or drop a code, edit the map in the same change. `check_course.py` checks both directions.
- **Answers live in the key.** `test.md` never bolds or ticks a correct option or carries `**Answer:**` lines (`check_test.py` errors on them); the semester skill's Google Docs conversion strips them as a safety net only.
- **Marks add up everywhere.** The parts together equal the header; each part equals the marks its heading states; the coverage table's rows total the test; the rubric's Level 4 totals the assignment's points.
- **Only what was taught, when it was taught.** No feature before its slot (the course's `feature_availability.yaml`, rendered as the Style Guide's table); no expectation the unit did not teach.
- **Executed output only.** Every sample run, trace answer, and predict-the-output answer is produced by running the code (`run_samples.py`), never written by hand. `run_samples.py` runs each fragment of a test question that asks for output against its answer in `test_KEY.md` under the same question ID. Label each fragment of a multi-fragment question in both files ("Fragment A", or "a)") and write its answer as backticked output right after the label (`` - **A:** `13` `` or `` a) `4` ``). Write a single fragment's answer on an `Output:` line or in an output fence. State givens in the question as `` `points = 120` ``; they become declarations. A Part A question takes the option its key letter names. A trace question it cannot pair is listed as shown output that was not verified.
- **A unit shorter than 3 weeks hands its assignment out on day 1.** No later slot leaves the 7 to 10 class days the window needs. So its opening part must be doable before the unit teaches anything (an audit, research, or planning first, the analysis after), and its instructions never assume content taught later in the unit before the part that needs it.
- **Category names come from the course's curriculum document** ("Thinking" in Computer Studies, "Thinking and Investigation" in Science).
- **No learning skills in a mark** (lateness, effort, participation): Growing Success reports them separately.
- **Content rules.** Islamic names for every invented person, real people under their real names, the teacher as `course.yaml` names them, no emojis, no em dashes, standalone documents that do not refer to other assignments.

## Self-check (run before handing back)

From the course root:

```bash
gla test master/02_Units/U<n>_*/Assessment/Test
gla samples master/02_Units/U<n>_*/Assessment
gla check --changed --only rubric,test,coverage,code,map,assignment,header-student,style
```

`check_test.py` checks the marks arithmetic, Part A's options and key letters, runs of three or more identical key letters, answers shown in `test.md`, that the test has exactly the course's parts, a key entry for every written question, the coverage table against the questions and the curriculum, header agreement across the files, review-sheet copies, and the unit's primary codes. `gla check --changed` keeps the findings in the files git shows as changed or new (in a course folder without git, pass the files you wrote with `--paths FILE...`). Fix every error. A warning you keep needs a reason in the file: `<!-- gla-allow: test-key-run the three answers are B by design -->`. Errors cannot be allowed. The scripts cannot judge whether a question is fair, clear, or at the right level; that stays yours.

## Review sheet (end every run with it)

Close the reply with this block, filled in:

```markdown
**Review sheet: U<n> <assignment | test>**
- Codes: the codes it evaluates, with marks per category
- Files written: one per line, new or changed
- Warnings kept: each with its code, file and the gla-allow reason (or "none")
- Assumed without asking: choices the teacher did not make (a scenario, a mark split, a question format)
- Check by eye: claims no script verifies (a fact in a scenario, an answer `run_samples.py` listed as unverified)
```

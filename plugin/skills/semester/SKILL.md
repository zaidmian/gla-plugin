---
name: semester
argument-hint: "[init | new | recalendar | refresh | audit] <semester, e.g. 2027-28 S1>"
description: Run a GLA course's semester instance end to end. Generate (rehydrate) a dated instance from master and a semester config, recalendar it mid-semester after disruptions, refresh its outputs (Google-Docs-ready .docx handouts in instances/<semester>/gdocs/, the teacher calendar page Course_Calendar.html, optional GLA-branded plan documents), and audit the teaching log. Use when the user sets up a new semester or gives semester dates, asks to rehydrate, recalendar, or resume after lost days or a module switch, wants the Google Docs or docx handouts, wants the HTML calendar built or rebuilt, or asks what was taught, skipped, or moved this semester. Do NOT use to author lessons, decks, exercises (author-week), assignments or tests (author-assessment), rubrics (gc-rubric), or to start a new course (bootstrap-gla-course).
---

# semester — a course's dated instance, from config to calendar

## Locations

Every script runs through one command, written `gla` below: run it as `python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" <command> ...` from the course folder (on Windows, `python` when `python3` is not found). Run `gla where` once before the first command: it prints `GLA_ROOT`, the folder that holds the shared `Standards/`, `Curriculum/` and `Calendars/`, and paths written `GLA_ROOT/...` below are under it. A script that stops on a missing module means the computer needs `gla setup` (ask the teacher first; it installs Python packages). This skill is course-agnostic: every course-specific value comes from `course.yaml` at the root of the course repo you are working in (schema: `GLA_ROOT/Standards/templates/Course_Config_Schema.yaml`).

**Step 0, always:** read `course.yaml` from the course repo root. If it is missing, stop and tell the user the repo has no `course.yaml` (it predates the shared-skill layout, or it is not a GLA course repo). Do not guess course parameters.

## Authority documents

1. `GLA_ROOT/Standards/rehydration/Rehydration_Framework.md`: the algorithm, the instance files, the report contract, mid-semester rules.
2. `master/<rehydration_dir>/rehydration.yaml` (the parameters the generator reads), with `Rehydration_Guide.md` and `Compression_Table.md` beside it for the reasoning.
3. The config template: `master/<rehydration_dir>/Semester_Config_Template.yaml` if the course has one, else `GLA_ROOT/Standards/rehydration/Semester_Config_Template.yaml`.

## Modes

Invoked with arguments (`/semester new 2027-28 S1`, `/semester recalendar 2026-27_S1`), they are `$ARGUMENTS`: the first names the mode and the rest the semester. Without them, infer the mode from the request.

**Asking the teacher.** In Claude Code, ask a decision that has a few known answers with the AskUserQuestion tool (up to four questions per call, two to four options each, your recommendation first and marked; the teacher can always type another answer). Ask free values (names, dates, counts) in a plain message. Where the tool is not available, ask in one message.

### New semester

1. **Get the config.** `gla semester init "<name>" [--from <previous instance>]` writes `<folder>_semester_config.yaml` at the course root from the course's template (or the shared one). When `GLA_ROOT/Calendars/<year>.yaml` exists for the name's school year, the config says `school_calendar: "<year> <term>"` and takes the semester dates, holidays, PA days and school events from that file; only the course's own events keep `TODO` dates. Without one, every date is `TODO` and the holiday and event names and PA-day labels are carried from the latest instance. Either way it carries the module choices, the events whose buffer day was lost, and a `usable_fraction` from the teaching log. A school calendar with `TODO` dates for the term is the office's data: ask the teacher for them and write them into `Calendars/<year>.yaml` (its own git repo), never into the course config. Then settle the course's choices with the teacher: the module options and how many buffer days each event takes are AskUserQuestion questions; the course's own extra closures and events are free values. Show the config for confirmation. `new` refuses a config with a `TODO` left, in it or in the school calendar it names.
2. **Build.** `gla semester new <config> [--plans]`, then delete the root copy (the instance keeps its own `semester_config.yaml`). It generates the instance (`rehydrate.py`), checks it (`check_instance.py`), converts the Google Docs handouts (`convert_instance.py`, which verifies every .docx it writes), renders the GLA plan documents into `gdocs/Admin/` when `--plans` is given (with the formatter's review file at `instances/<name>/Admin_Plans_Review.md`; give it to the teacher with the plans), and builds the teacher calendar last (it reads `gdocs/index.yaml`). It stops at the first failing step.
   - Exit 3: the plan cannot fit within the sanctioned rules. Show the message and ask the teacher which unit to thin (an AskUserQuestion with the units as options).
   - A course without `rehydration.yaml`: write it first from its `Rehydration_Guide.md` and `Compression_Table.md` (ICS3U's is the model) and confirm it with the teacher.
   - An existing instance: pass `--force`. Never hand-edit generated files; change the config, the week plans, or `rehydration.yaml`, and rerun.
3. **Finish what the generator cannot.** Fill any register description it flags as missing (and add the `summary` to the master week plan), and record the decisions made with the teacher and any flags of your own in the config's `decisions:` and `flags:` lists, then rerun with `--force`. The report renders them on every run, so never edit `GENERATION_REPORT.md` by hand. Show the user the report summary and the first two weeks of the calendar.
4. **Hand over** the calendar: open `instances/<name>/Course_Calendar.html` in Chrome as a `file://` page; the first visit needs **Connect folder** (the instance folder), later visits one **Reconnect** click.

### Mid-semester recalendar

Run `gla semester recalendar <name>`. It takes `resume_from` and the `resume_*` keys from the teaching log, by the status the teacher gave each day on the calendar page: **Postponed** is re-planned after the resume date, **Skipped** is not taught this semester, **No class** becomes a closure with its slot re-planned, **Moved** goes to its date (kept there if past, pinned if later), **Partial** counts as taught and is flagged. `--resume-from DATE`, `--postpone`, `--skip`, `--no-class` and `--move SLOT=DATE` replace what the log gives when it is incomplete. It re-plans in a scratch folder and prints what would move: slots with their tests, hand-outs and dues, cuts, buffers, and the generator's flags. Nothing is written. Show that to the teacher and ask (AskUserQuestion: apply, change something first, or stop); only after they agree, rerun it with `--apply`: it sets those keys in the instance's `semester_config.yaml` and runs `new --force`. Every day before `resume_from` stays exactly as it was; exit 3 means the remainder cannot fit. A change that is not a lost day (a closure announced ahead, a module switched on) goes into the config before the dry run.

### Refresh outputs

After master materials change: `gla semester refresh <name> --weekplans [--plans]` re-copies the master week plans into the instance with their existing dates, reconverts the handouts and rebuilds the calendar. For one handout: `gla gdocs <name> --only <file or folder fragment>`, then rebuild the calendar with `gla calendar instances/<name>`. For an arbitrary file: `gla md2docx SOURCE.md OUT.docx [--strip-teacher-note] [--kind=test]`.

Uploading `gdocs/` to Google Drive is an external action: if a Drive connector is available, offer it and confirm first; otherwise tell the teacher to drag the folder into Drive (structure is kept) and open files with Google Docs. The calendar's **+URL** button records each handout's Google Doc link in `material_links.yaml`.

### Audit

`gla audit instances/<name> [--md]`: per-unit tally, every deviation from the plan, buffer-day outcomes, and the config patch (a mid-semester resume, and events and a `usable_fraction` suggestion for next year's config, with next year's dates left blank). Show the patch; the teacher decides what goes in. The notes the teacher marked "fix in master" on the calendar page, and the days logged as partly taught, are the course backlog: `gla backlog` lists them by master folder. This skill never edits master; author-week and author-assessment work through the backlog.

## Hard rules

- Never edit `master/` here. If master content looks wrong, flag it.
- Never hardcode or guess holiday or event dates; they come from the config every time.
- Never cut a teach, assess, or hand-out day; only the course's compression tiers cut.
- Never edit `teaching_log.jsonl` or `material_links.yaml`; the page writes them, and a rebuild preserves them.
- Teacher-only files (`_KEY`, `_MARKING`, marking notes, rubrics, lessons, plans, decks) never go into `gdocs/` as student handouts.
- Percentages total exactly 100 under the 2026 model (classroom 65; final evaluation 20 or 25; attendance 15 or 10). Assignment windows 7 to 10 class days; culminating demos at least 2 class days before `exam_start`. The generator and `check_instance.py` check these; their warnings go into the report's flags.

## Reference

- `references/gdocs_output.md`: what the handouts look like and why (styling, student-copy transforms, test-paper layout, limitations).
- `references/calendar_page.md`: the calendar page's files, links, and Google Docs link handling.
- Calendar schema: `GLA_ROOT/Standards/rehydration/Calendar_Schema.yaml`.

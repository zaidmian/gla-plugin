# Rehydration Framework

How a dated semester instance is generated from a date-agnostic course master. This is the shared algorithm; each course supplies a thin **parameter layer** (its `master/<nn>_Rehydration/Rehydration_Guide.md`) defining the concrete numbers. The shared `semester` skill automates the whole flow; this document is the specification and the manual fallback.

## The generator

`Teaching/Skills/semester/scripts/rehydrate.py` implements steps 1 to 4 and the calendar half of step 5 deterministically. It reads the semester config and the course's `master/<rehydration_dir>/rehydration.yaml` (the parameter layer below as data: the slot sequence by week plan, modules and their forms, compression tiers as explicit slot lists, the floor, the reserve-spill minimum, and the constraints) and writes `calendar.yaml`, `Course_Calendar.md`, the dated week plans, `Assessment_Register.md`, `Short_and_Long_Term_Plan.md`, the resolved `Course_Outline.md`, and the factual parts of `GENERATION_REPORT.md`. It stops with exit code 3 when the teacher must decide: the plan cannot fit within the sanctioned rules (the answer goes in the config's `extra_cuts`), or an assignment window or the culminating demo rule breaks on a date still ahead (the config changes, or the item goes in `accept_rule_breaks`). The report's decisions and the teacher-facing flags beyond the generator's own come from the config's `decisions` and `flags` lists, so a rerun keeps them; a register description a week plan lacks is taken from master (an assignment's first learning goal, an exercise's opening sentence), and only what still has none is flagged.

## Course parameter layer (what each course must define)

1. **Slot sequence:** the ordered blocks and their nominal slot counts (e.g., `INTRO(2) → R(5) → U1(20) → … → CP(15)`), including any optional/standby modules and their placement options.
2. **Compression table:** the course's concrete cut tiers (see `Compression_Framework.md`), with the floor.
3. **Weighting table** and any module-dependent redistribution rules (in the course's `Assessment_Plan.md`, referenced from the parameter layer).
4. **Reserve-spill designation** (optional): which module slots, if any, may consume disruption-reserve days, and the minimum reserve that must remain.
5. **Hard-constraint specifics:** which slots are assessment anchors (unit-final tests), assignment hand-out→due windows, final-evaluation lead time before exams.

## Inputs

1. A completed `semester_config.yaml` (copy this package's `Semester_Config_Template.yaml`; the course may extend it with course-specific module options). With `school_calendar: "<year> <term>"` it takes the term's dates, the holidays and PA days that fall in it, and the school-wide events from `Teaching/Calendars/<year>.yaml`, the school year's file shared by every course; the config then lists only the course's own closures and events, and gives a school event buffer days by naming it with no dates. A value in the config wins over the school file.
2. The course master (`master/`), untouched.

## Algorithm

### 1. Build the calendar
- Enumerate every date from `first_day` to `last_day` that falls on a `class_day` and is not inside a holiday range or a PA day. This is the **scheduled-day list**.
- Compute **usable days** = floor(scheduled × `usable_fraction`). The difference is the *disruption reserve*: days that will predictably be lost to assemblies, trips, and events not known at planning time.

### 2. Assemble the slot sequence
- Take the course's slot sequence from its parameter layer, inserting any optional modules per the config.

### 3. Fit
- If slots > usable days: apply the course's Compression Table in priority order until it fits (or stop and ask, if `compression: manual`).
- **Reserve spill (if the course designates it):** if the plan still overflows after all sanctioned cuts, only the designated module slots may consume disruption-reserve days, and only down to the course's stated reserve minimum. `GENERATION_REPORT.md` must state how many reserve days were consumed. If the plan still overflows, stop and ask the teacher which unit to thin manually. Never cut below the Compression Table's floor.
- If slots < usable days − 4: re-add flex days (reverse cut priority), then widen project work weeks.
- **Do not schedule content into the disruption reserve.** It gets consumed silently during the semester; that's the built-in flexibility.

### 4. Assign dates
- Map the final slot sequence onto the scheduled-day list in order, with the buffer days (scheduled days minus slots) placed in this order: on the first class days of the config's `events` that ask for them; then one on the class day before each unit test, latest unit first; then at the end before the exam window.
- Hard constraints (defaults; course layer may tighten): a unit's test lands on the unit's final `assess` slot; assignment hand-out → due spans **7–10 class days** (1.5–2 weeks); final-evaluation demos land ≥2 class days before `exam_start`. A course may also name weekdays that never hold a unit test (`constraints.avoid_test_days`, for example `[Fri]`): the generator moves such a test by one buffer day, reports the move, and flags it when no buffer day is free; `check_instance.py` reports a future test on one of those days as an error. No unit test sits on the first class day after a closure (a holiday, PA day or closed event day; weekends do not count): the generator moves it the same way. A course turns this off with `constraints.no_test_after_break: false`.

### 5. Generate the instance (`instances/<name>/`)
- `semester_config.yaml`: the input, copied verbatim.
- `Course_Calendar.md`: every date, with slot ID, title, day_type, sub_ready flag, evaluations due; holidays and buffer days marked.
- `Short_and_Long_Term_Plan.md`: from the course's `00_Admin` template with real dates and recomputed percentages (must total exactly 100%).
- `Course_Outline.md`: from the master outline with `{{...}}` placeholders resolved.
- Per-week `week_plan.yaml` copies with `dates` and per-day `date` fields injected (content otherwise byte-identical to master). Days removed by compression carry an explicit `date: "CUT, removed by compression (see GENERATION_REPORT.md)"` marker.
- `Assessment_Register.md`: one table of every graded item in course order, columns Assessment | Out of | Weight | Due | What it is. Names carry a unit prefix (`Unit 1 - Binary Practice`). The out-of comes from each document's own `**Marks:**` line, the weight from the course's `Assessment_Plan.md` after module-mode redistribution, the date from the calendar, and the description is one or two lines saying what the item is. Formative items appear with a `-` weight. The culminating task, the written exam, and the attendance bucket are rows too, so the weight column totals exactly 100.
- `GENERATION_REPORT.md`: see the report contract below.
- `calendar.yaml`: the machine-readable calendar per `Calendar_Schema.yaml` in this folder: every weekday (slot / buffer / closure / exam), each slot's week plan, master folder, title, day type, sub-ready flag, hand-outs and dues, plus the compression cuts. It is the input to the shared `semester` skill, so the generator writes it from the same data that produced `Course_Calendar.md`, and the two must agree. Each slot's hand-outs and dues come from the week plans' `evaluations` entries and land on exactly the `handed_out` and `due` slots those entries name. The generator does not move a hand-out to a neighbouring day on pedagogical judgment (for example onto the prior exercise's submit day). When an evaluation should hand out on a different day, its `handed_out` slot in the week plan is what changes, not the calendar. `Course_Calendar.md` carries the same annotation on the same day.
- `Course_Calendar.html`: built last by running the shared builder, `gla calendar instances/<name>`. A rebuild never touches the instance's `teaching_log.jsonl` or `material_links.yaml` (written by the page itself), so mid-semester re-runs preserve the teaching log.
- **Content files are NOT copied**: the calendar and week plans reference master paths. (Master files are date-agnostic by construction, so they serve every instance simultaneously. If a semester needs a modified document, copy just that file into the instance folder and note it in the report.)
- Apply `overrides` (free-text instructions) last; document every resulting deviation in the report.

### 6. Self-check (must pass before handing to the teacher)
- Every slot has exactly one date; no date has two slots; nothing lands on a holiday/PA day.
- `calendar.yaml` lists every weekday exactly once and its slot rows match `Course_Calendar.md` row for row.
- Every evaluation has a due date; percentages total exactly 100%.
- Each evaluation's hand-out and due annotations sit on the `handed_out` and `due` slots its week-plan `evaluations` entry names, in both `calendar.yaml` and `Course_Calendar.md`. No hand-out is relocated to a neighbouring day.
- Assignment windows are 7–10 class days; tests sit at unit ends; final demos ≥2 days before exams.
- Any course-specific invariants from the parameter layer (e.g., "if module X is omitted, its compliance-baseline slots must survive compression").

## GENERATION_REPORT.md contract

Header (generated-from commit + module modes) → calendar-math table (weekdays → closures → scheduled → usable → reserve → slots → buffers) → decisions made with the teacher → compression-applied table → instance adjustments (master unchanged) → weighting table totaling 100 → flags for the teacher → file manifest. Every cut, spill, and override lands here. Silent deviations are defects.

## Mid-semester adjustments

Disruptions beyond the reserve, or deploying an optional module mid-semester:
- `build_semester.py recalendar <semester>` sets `resume_from` and the `resume_*` keys from the teaching log, re-plans in a scratch folder and prints every date that would change; `--apply` writes the keys into the instance's config and reruns the generator on the same instance. A change that is not a lost day (a new closure announced ahead, a module switched on) goes into the config first.
- Every day before `resume_from` is kept exactly as the existing `calendar.yaml` has it, except where the teaching log says otherwise. A **postponed** slot's day becomes a buffer and the slot is re-planned after `resume_from`. A **skipped** slot's day becomes a buffer and the slot is not taught this semester; the report flags any evaluation it carried. A **no class** day becomes a closure and its slot is re-planned. A slot **moved** to a past day is kept on the day it ran (which must have held nothing taught) and its planned day becomes a buffer; a slot moved to a later date is pinned there and the rest fills around it. A **partial** slot counts as taught and is flagged. A closure in the config wins over the old calendar's day. `audit_log.py` prints the keys (`resume_postponed`, `resume_skipped`, `resume_noclass`, `resume_moved`, `resume_partial`) from the log, which applies an entry only to the date it was logged for. The remaining slots are re-fitted to the remaining class days; capacity is the whole semester's usable days minus the slots already taught, so the reserve already spent is not counted twice. A module switched on after its placement point lands at the front of what remains.

## Weighting recomputation

- The course's `Assessment_Plan.md` is the weighting authority; the generated Short & Long Term Plan restates it with real dates and must total exactly 100%.
- Any compression that removes a graded exercise folds its weight into the unit's remaining exercises: **a unit's subtotal never changes**.
- Module-dependent redistributions (e.g., "module omitted → its % moves to units A and B") are defined per course and applied automatically.

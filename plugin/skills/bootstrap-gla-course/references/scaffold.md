# Scaffold: folder tree, document skeletons, registry, manifest

The structure `scripts/scaffold_course.py build` produces (workflow step 3), and the
coverage-map shape you refine in step 4. Everything here is derived from the three built courses; treat it as the
skeleton to fill from the interview answers, never as content to copy verbatim.

## The repo tree

```
<CODE>/
├── README.md                         # repo intro (skeleton below)
├── .gitignore                        # empty or minimal; vendored libs etc. per Batch E
├── course.yaml            (schema: Standards/templates/Course_Config_Schema.yaml; read by every shared skill)
├── gdocs_manifest.yaml    (conversion rules for the semester skill's Google Docs step)
├── master/
│   ├── MASTER_INDEX.md
│   ├── 00_Admin/
│   │   ├── Assessment_Plan.md
│   │   ├── Course_Outline.md
│   │   ├── Short_and_Long_Term_Plan_Template.md
│   │   ├── BOOTSTRAP_DELTAS.md        # fresh, schema only
│   │   ├── Course_Introduction/       # INTRO block: skeleton folder only
│   │   ├── Emergency_Sub_Packets/     # skeleton folder only
│   │   ├── Legacy_Reuse_Map.md        # CONDITIONAL (Batch E)
│   │   └── Deployment_Checklist.md    # CONDITIONAL (Batch E)
│   ├── 01_Standards/
│   │   ├── Style_Guide.md             # thin course layer
│   │   └── Curriculum_Coverage_Map.md # refined first, step 4
│   ├── 02_Units/
│   │   └── U<n>_<Name>/               # one per unit
│   │       ├── unit_overview.md
│   │       ├── W<n>_<Title>/          # one empty-ish folder per week (author-week fills)
│   │       └── Assessment/            # Assignment_<Name>/ + Test/ skeletons
│   ├── [0N_<Standby_Module>/]         # CONDITIONAL (Batch B); see renumbering note
│   ├── 0N_Culminating_Project/        # PROJECT_DECISIONS.md, cp_overview.md, Launch_Week/, ...
│   └── 0N_Rehydration/
│       ├── Rehydration_Guide.md
│       ├── Compression_Table.md
│       └── (semester config: use shared template unless Batch F says otherwise)
└── instances/                        # empty; the semester skill fills it
```

### Standby-module renumbering

The numbered folders are *positional*. With no standby module (ICS4U, ICD2O):
`00_Admin, 01_Standards, 02_Units, 03_Culminating_Project, 04_Rehydration`. With
an optional standby module (ICS3U's AI module): it takes `03_`, and Culminating
Project and Rehydration shift to `04_`/`05_`. Decide from Batch B answer 7, place
the standby folder after `02_Units`, and renumber Culminating Project and
Rehydration accordingly. `00`–`02` never move. Whichever numbering results,
`Rehydrate_Guide`'s `rehydration_dir` (from `course.yaml`) and the rehydrate skill's authority
paths must match it.

## The coverage map (step 4): `01_Standards/Curriculum_Coverage_Map.md`

The most important document; written before anything else. Structure:

- **Preamble:** title + one-line role ("the compliance authority for the master
  course"); the authoritative curriculum source path; the **numbering-convention
  statement** (modern: "the curriculum numbers its own specific expectations,
  used directly"; 2008: declare the local convention); and, if legacy material
  exists, the D-009 warning that legacy codes are from a different scheme and are
  never carried over.
- **Rules block (numbered):** (1) every specific expectation gets ≥1 teach/anchor
  slot AND ≥1 evaluated artifact; (2) every artifact header carries its codes so
  the map is grep-checkable; (3) the map is updated in the same change as any
  coverage change; (4) the cross-cutting model, **only if** a cross-cutting strand
  exists. A tightened form of rule 1: an artifact's *kind* must match the
  expectation's verb — a write/use/apply expectation needs a submitted doing-artifact,
  not only a test question.
- **Status legend:** `planned → built → verified`.
- **Body:** one `##` section per strand, `###` per overall expectation, each with
  a coverage table.
  - Regular strand table columns: `| Code | Expectation (abridged) | Taught in | Assessed in | Status |`
  - Cross-cutting strand table columns (the "second view", expectation → slot):
    `| Code | Expectation (abridged) | Anchor slot | Woven thread (named artifacts) | Assessed in | Status |`
    Every row names a concrete anchor slot and either a named woven artifact or `-`.
- **Reverse index:** `| Unit | Primary codes |`, one row per unit + CP.
- **Cross-cutting notes** (if applicable): the load-bearing invariants — a
  cross-cutting strand has no unit; anchors may never dissolve into "covered
  throughout"; woven threads are named rubric rows.

At bootstrap this is populated with every expectation from the curriculum data at
`Status: planned`, mapped to units per Batch B. Anchor-slot assignment for a
cross-cutting strand and artifact-kind matching are `[BUILD]` refinements; get the
expectation-to-unit mapping right and mark the per-slot detail as planned.

## Course-layer `01_Standards/Style_Guide.md`

Thin layer per Style Guide Core §13. Open with "**This file is a thin course
layer.**" then a bulleted list of absolute-path references into the shared
package (Style_Guide_Core, the language conventions file, Grading_Conventions),
and the closing "This layer adds only what is true of `<CODE>` specifically. It
may tighten shared rules; it never contradicts them." Then the sections (from the
interview):

1. **Course identity** — code, full name, grade, pathway, prerequisite/assumed
   knowledge, curriculum + source-of-truth path, language/environment, feeder role.
2. **Slot blocks** (frozen; never renumber) — the `| Block | Slots | What it is |`
   table (INTRO, each unit, standby if any, CP), nominal slot count.
3. **Weekly rhythms** — only if the course declares variants (Batch B): the
   standard rhythm and each variant as a day-by-day table, with the preserved
   invariants stated.
4. **Feature availability by slot** — for a skills-building course, the
   `| From | Newly available |` table, rendered from
   `01_Standards/feature_availability.yaml` (the scaffold writes one row per unit week; fill
   the cells there and run `gla features render`), plus course-wide ceilings; governs the
   only-taught-features rule. (Omit or adapt for non-programming courses.)
5. **Environment and provenance** — only if Batch D warrants it: in-class and
   at-home environment, the authorship-evidence protocol.
6. **Course-specific content rules** — anything true of this course only, plus the
   teacher typography rules from Batch D (e.g. no em-dashes, no emojis).
7. **Culminating project constraints** — pointer to `PROJECT_DECISIONS.md`.
8. **Pointers** — to the coverage map, Assessment_Plan, BOOTSTRAP_DELTAS, and any
   conditional docs.

## Parameter-layer documents

- **`00_Admin/Assessment_Plan.md`:** `## Final grade structure` (the 2026
  three-bucket model: classroom work 65%, final evaluation 20% at Gr 9-10 or 25% at
  Gr 11-12, attendance and participation 15% or 10%); `## Classroom work breakdown`
  with the weighting table `| Unit | Weight | Test | Assignment | Exercises/Ships |`
  summing to 65%, plus a bold total row and notes on ships, assignment count, and
  the compression-fold rule; `## Final evaluation` (the written exam and, where the
  subject requires it, the culminating task, with the exam/culminating split taken
  from the Grading_Conventions matrix, plus a short exam spec at
  `00_Admin/Final_Exam/exam_spec.md`); `## Culminating project`; `## Attendance and
  participation` (the unexcused-absence scale); `## Marking schemes` (exercises/
  ships, assignments, stretch goals, tests); `## Assessment-week pattern`; `##
  Achievement categories across the course` (name the second category the way this
  course's curriculum document names it: "Thinking" for Computer Studies, "Thinking
  and Investigation" for Science, per Grading_Conventions §Naming the second
  category). The three buckets total 100.
- **`0N_Rehydration/Rehydration_Guide.md`:** points to the shared framework, then
  `## Slot sequence` (`| Order | Block | Slots | Notes |` + nominal count +
  standby declaration); `## Fit parameters` (compression pointer + sanctioned
  floor, split unit vs CP); `## Reserve-spill designation`; `## Hard constraints`
  (test-slot pins, assignment windows per unit, short-unit D1 pin, CP placement);
  `## Course invariants` (self-check additions: cross-cutting anchors survive
  compression, weights total 100, load-bearing artifacts survive); `## Weighting
  recomputation`; `## Mid-semester adjustments`; `## Semester config` (which
  course-specific options exist, if any).
- **`0N_Rehydration/Compression_Table.md`:** preamble (cut-in-order rule, never
  cut teach/assess/hand-out days, pointer to the shared Compression_Framework);
  nominal size; the tier table `| Priority | Cut | Slots freed | Consequence |`
  (starred priorities = manual, below-floor); a rhythm caveat paragraph (derive
  tiers from each block's rhythm — studio blocks free days only via flex cuts,
  merge-exercise tiers apply only to standard-rhythm blocks); the floor; the
  after-cutting logging requirement. **Do not copy a sibling's tier list** — derive
  it from this course's rhythms.
- **`00_Admin/Course_Outline.md`:** student/parent-facing, with `{{...}}`
  placeholders rehydration fills. Metadata table, `## Course description`,
  `## Units of study` (`| Unit | Title | Length | Weight |`), `## How your grade is
  calculated`, `## How class works`, `## Course policies`, `## Materials`,
  `## Support`, `## Islamic perspective`, `## Important dates` (placeholder rows).
- **`00_Admin/Short_and_Long_Term_Plan_Template.md`:** an HTML rehydration comment
  (fill `{{...}}`, recompute %, must total 100) plus the two branded GLA tables
  (short-term: `| Unit | Unit Title | Start Time | End Time | Evaluation Percentage |`;
  long-term: `| EVALUATIONS | DUE DATES | TITLES OF EVALUATION | % OF GRADE |`),
  each ending in a bold TOTAL 100% row.

## Unit and CP folders

- **`unit_overview.md`** per unit: H1 title (`# Unit <n>: <Title>`); a header
  line `**Weeks:** <n> (slots U<n>.W1.D1 – U<n>.W<m>.D5) · **Weight:** <p>% (test a,
  assignment b, exercises c)` whose unit weights, across all units plus any standby
  module, sum to the `classroom` bucket in `course.yaml`; an
  `**Expectations (primary):** <codes>; reinforces <codes>` line; `## Story of the
  unit`; `## Week architecture (frozen ...)` with a `### W<n>` subsection per week
  giving day-by-day slot notes (a `| Slot | Type | Topic | Notes |` table, codes in
  Notes); `## Evaluations` as a `| Item | Kind | Handed out | Due | Weight |` table
  (formative rows carry `-` as their weight; an optional sixth column `Assessed`
  lists the codes an item formally evaluates, which the unit-plan formatter takes
  as authoritative); `## Reference sheets`; `## Content sources` (legacy pointers,
  "adapt facts only, re-derive all codes") if Batch E applies.
- **Week folders** `W<n>_<Title>/`: created empty (or with just a placeholder).
  `author-week` fills them. Do not author their content.
- **`Assessment/`** per unit: `Assignment_<Name>/` (instructions.md,
  rubric.csv, rubric.md, marking_notes.md) and `Test/` (test.md, test_KEY.md,
  coverage_table.md, review_sheet.md, test_reference.md) as skeleton folders —
  content is a later job. When that content is authored it follows
  `Standards/templates/Assignment_Template.md` (which requires a `## Learning
  goals` section opening every assignment) and `Test_Template.md` /
  `Test_Reference_Template.md`.
- **Culminating Project folder:** `PROJECT_DECISIONS.md` (authoritative
  constraints: `## What it is`, `## Technical constraints`, `## Prompt directions`,
  `## Components and evaluation`, `## Expectations assessed here`, `## Makeup
  variant`), `cp_overview.md`, and `Launch_Week/` / `Individual_Makeup/` skeletons.

## `MASTER_INDEX.md`

Navigation + file registry: preamble (role, reading order, core model, weighting
summary, frozen-slot-IDs rule); `## Slot blocks` (`| Block | Slots | Weeks | What
it is |`); `## Weekly rhythms`; `## Layout` (an ASCII tree of `master/`); `##
Inside a week folder` (the naming conventions per rhythm); `## Shared standards
package` (absolute-path pointer); `## Rules that live here` (register new files,
no version suffixes, no dates outside `instances/`, deltas-log rule); `## File
registry` (a `###` subsection per top-level folder, each a bulleted list of
`` `path`: description `` with build-status annotations); `## Legacy materials`
(if applicable).

## `README.md`

Short repo intro: the course title + a one-line "detached-master curriculum repo"
statement; a `master/` / `instances/` / shared-standards / curriculum-source
bullet list (shared standards referenced by absolute path); the feeder-role line;
a `BOOTSTRAP_DELTAS.md` pointer; and legacy-materials pointers if any.

## Conditional stubs (Batch E)

- **`Legacy_Reuse_Map.md`:** "Approved by <teacher> before content build" line; a
  hard-rules block led by "No legacy expectation code may be carried over" (codes
  re-derived from the curriculum source); a strip-on-adaptation list; and the map
  table `| Legacy asset | Verdict | New home |` with verdicts Adapt / Mine /
  Discard. Populate from the teacher's audit; leave the table headed and ready.
- **`Deployment_Checklist.md`:** the one-time, per-deployment lab/environment
  setup, framed as the physical-world counterpart of rehydration. Sectioned by
  concern (tooling install/licensing, version control identity, software
  vendoring, per-unit tool decisions marked `(decision)`, home access, print
  stock, classroom platform), each a checkbox list. Populate from Batch D/E.

## gdocs_manifest.yaml generation

Generate from the course's actual doc types and unit structure (see a built
course's manifest for the shape). Rules are `{glob, base, dest}` triples mapping
student-facing master markdown to `.docx` destinations. Include a rule per doc
type the course actually has: `EX_*.md`, `BRIEF_*.md` (studio courses), `REF_*.md`
under the week folders; `Assessment/Assignment_*/instructions.md` and
`Assessment/Test/test.md` (+ `review_sheet.md` and `test_reference.md`) per unit;
and the CP student docs. The `test.md` rule carries `strip_teacher_note: true` and
`doc_kind: test` (the test-paper layout, see `semester/SKILL.md`).
The converter hard-excludes `*_KEY.md`, `*_MARKING.md`, `marking_notes.md`, and
`rubric.*` regardless of the manifest — do not add rules for those. Scripts are
never copied; the skill invokes the shared `convert_instance.py`/`md2docx.py` by
absolute path.

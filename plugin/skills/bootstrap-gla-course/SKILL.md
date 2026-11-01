---
name: bootstrap-gla-course
argument-hint: "<COURSE CODE>"
description: Scaffold a brand-new GLA course repository from its Ontario curriculum, at the moment the course is first created, before any folder for it exists. Use when the user wants to start, set up, stand up, scaffold, bootstrap, or kick off a NEW course from scratch, or rebuild a course from the ground up: for example "start a new course", "bootstrap ICS4C", "stand up the TAS1O repo", "scaffold TAS2O from the curriculum", "create the ICS4C repo", or "set it up the way ICD2O is set up". It interviews for course parameters, detects the curriculum era, writes the coverage map, and scaffolds the master/instances structure, the standards layer, and the course.yaml the shared skills read. Decisive test: if no repository for this course code exists yet, this is the skill; if the course repo already exists, it is not. Do NOT use for work inside a course that already exists, even when the request says "set up", "build out", "create a new", or "start": setting up a semester instance or rehydrating dates is the semester skill; building out or authoring a unit, week, lesson, deck, exercise, brief, or culminating project is author-week; editing an existing coverage map is ordinary work; and generating Google Docs or docx handouts is the semester skill. This runs once, at course creation.
---

# bootstrap-gla-course — stand up a new GLA course from an Ontario curriculum

You are creating the initial repository for a new GLA course: the detached-master
structure, the standards layer that wires it to the shared package, the course's
compliance and parameter documents, and the `course.yaml` that the shared skills read. You do this
**before any course folder exists**, driven by an interview and the Ontario
curriculum data for the course code.

You scaffold structure and the standards layer. **You do not author teaching
content** (lessons, exercises, briefs, decks, tests): that is `author-week`'s job,
run per week after the scaffold exists. Your deliverable is a repo a content
author can start filling, with the coverage map as the contract they build
against.

## The three built courses are exemplars, not templates

Every script runs through one command, written `gla` below: run it as
`python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" <command> ...` (on Windows, `python`
when `python3` is not found). Run `gla where` once before the first command: it
prints `GLA_ROOT`, the folder that holds the shared `Standards/`, `Curriculum/`
and `Calendars/`, and paths written `GLA_ROOT/...` below are under it. A script
that stops on a missing module means the computer needs `gla setup` (ask the
teacher first; it installs Python packages).

When `GLA_ROOT/Courses/` exists (the maintainer's own setup), `ICS3U`, `ICS4U`,
and `ICD2O` in it show what a finished repo looks like. A teacher's install
carries no courses; then `references/scaffold.md` is the shape to follow. Read them to see shape and voice. **Never copy their
files** — every course-specific choice in them (language, unit names, project
topics, weights, rhythms) is a parameter you gather in the interview, not a
default you inherit. ICD2O is the post-2008 exemplar; ICS3U/ICS4U are the 2008
exemplars. When they disagree, that difference is usually a curriculum-era branch
or a course parameter, and the interview below asks for it.

## Authority documents

Shared package (the rules; reference by absolute path, **never copy into the new repo**):

1. `GLA_ROOT/Standards/README.md` — the detached-master architecture and the package's change discipline.
2. `GLA_ROOT/Standards/style/Style_Guide_Core.md` — §13 defines the course-layer contract you are instantiating; §1 the master/instance model; §5 file naming.
3. `GLA_ROOT/Standards/assessment/Grading_Conventions.md` — the assessment defaults (one assignment/unit, /10 scale, category weighting) the interview may override per course.
4. `GLA_ROOT/Standards/rehydration/Rehydration_Framework.md` and `Compression_Framework.md` — the algorithm the course's parameter layer feeds; `rehydration/Semester_Config_Template.yaml` — the shared config.
5. `GLA_ROOT/Standards/templates/` and `decks/` — the artifact templates and deck machinery the course will use.
6. The shared skills (`author-week`, `author-assessment`, `semester`), installed beside this one. They are course-agnostic and are never copied into a repo; they read the repo's `course.yaml`, whose schema is `GLA_ROOT/Standards/templates/Course_Config_Schema.yaml`.

Curriculum data (the source of truth for expectations and era):

7. `GLA_ROOT/Curriculum/docs/knowledge-graph/courses/<CODE>.md` — always present; carries the era metadata.
8. `GLA_ROOT/Curriculum/data/curriculum/<CODE>.json` — present only for modern (post-2008) courses.

This skill's own references (read when you reach that step):

9. `references/curriculum.md` — era detection, and how to read strands/expectations from the JSON vs the `.md`.
10. `references/scaffold.md` — the exact folder tree, per-document skeletons, and the `MASTER_INDEX.md` registry shape.

## Workflow

The interview lives in a file. `gla course` (this skill's `scripts/scaffold_course.py`) writes it prefilled, checks it, and builds the mechanical part of the repo from it; you write the prose it marks.

### 0. Preconditions

Invoked as `/bootstrap-gla-course TAS1O`, the course code is `$ARGUMENTS`.

- Confirm `GLA_ROOT/Curriculum/docs/knowledge-graph/courses/<CODE>.md` exists. If it is missing, stop: this course is not in the curriculum dataset and there is nothing authoritative to build from.
- Confirm `GLA_ROOT/Standards` resolves (`gla where`). Decide the new course folder's path with the teacher: any folder they keep their work in, for example `Documents/GLA Courses/<CODE>` (the maintainer's are under `GLA_ROOT/Courses/`). Never inside `GLA_ROOT`, which the plugin replaces on every update.

### 1. Write the answers file

`gla course init <CODE> --out <CODE>_answers.yaml` (in the scratchpad, never inside a course). It detects the era (JSON present: modern, Ministry codes; page only: 2008, positional local codes, see `references/curriculum.md`), the cross-cutting strand, title, grade, type, prerequisite, and the exam/culminating split from the Growing Success matrix, marking each `DETECT`. A subject with no culminating task (English, Mathematics, Science) gets `culminating: null`, and the build makes no CP block. Outside Computer Studies and Technological Education it detects `language: null`. It prefills one unit per strand that is not cross-cutting (the strand's codes, weeks from its share of the expectations, an even share of the classroom 65%), each line marked `CONFIRM` and each strand's overall expectations printed above its unit; reshape them with the teacher. Strands the Ministry left unlettered (2007 English, Business) get letters by position, and the file says so. Everything else the teacher decides is `TODO`, grouped by the batches below. `gla course codes <CODE>` prints every expectation with its code, for a teacher choosing which codes a unit carries.

### 2. Interview through the file

Tell the teacher the file's path and the detected era and cross-cutting finding, and ask them to fill the TODOs in an editor; or ask the batches in chat and write their answers into the file yourself. In Claude Code, ask a batch's choices with AskUserQuestion, one call per batch (up to four questions, two to four options each, your recommendation first and marked; the teacher can always type another answer): the cross-cutting strand to confirm, the rhythm per block, studio work, a standby block and its coverage, the deck theme, a shared or course semester config. Ask free values (unit names and lengths, the teacher's names, weights) in a plain message. Where the tool is not available, ask each batch in one message. Either way, **an unanswered question stops the build**: surface the shared default if one exists, never assume it. Run `gla course check <file>` until it reports no errors (it checks TODOs, the era, codes, weights against the classroom bucket, a home for every specific expectation, the standby-coverage rule, the matrix split, the conventions file, the deck theme). Then confirm the whole answer set back to the teacher.

### 3. Build the scaffold

`gla course build <file> --dest <repo path>`. It writes the tree in `references/scaffold.md` (positional numbering, the standby folder when there is one, empty week and Assessment folders), `course.yaml`, `gdocs_manifest.yaml`, `rehydration.yaml`'s sequence, the coverage map with every specific expectation at `planned`, the unit overviews' header lines and Evaluations rows, the Assessment Plan and Course Outline tables, the plan template, `MASTER_INDEX.md`, `README.md`, a fresh `BOOTSTRAP_DELTAS.md`, and the conditional stubs. It prints every file that still has `<!-- TODO(bootstrap): ... -->` prose.

### 4. Write what the build marks

Work through the printed list. The coverage map comes first: refine Taught in from blocks to week slots where the answers allow, give each cross-cutting expectation a concrete anchor slot and, where relevant, a named woven thread, and match each write/use/apply expectation to a doing-artifact. Then the course-layer prose: the Style Guide's rhythms and feature availability, the Rehydration Guide's rationale, the Compression Table's tiers derived from this course's rhythms (and the same tiers in `rehydration.yaml`), and the story of each unit. Leave Assessed in as `(to assign)`: author-assessment records the real artifacts. Record each decision that confirms, bends, or parameterizes the pattern in `BOOTSTRAP_DELTAS.md`.

### 5. Commit and hand off

When git is installed (`gla doctor` says so), `git init` and commit the scaffold: slot and block numbering freezes at this commit, and the authoring skills' `gla check --changed` reads git to find the files a run touched. Without git, tell the teacher that the numbering is frozen from now on, and that installing git (`gla doctor` gives the command) keeps a history of their course. Run the self-check below. Then summarize for the user: the scaffold produced, the coverage map as the authored-against contract, which documents still carry TODO prose, and that content authoring (per week, via `author-week`; assessments via `author-assessment`) is the next job. Do not author content.

---

## The interview

Grouped for batch answers. `[ASK]` = the teacher answers; `[DETECT]` = read from
the curriculum data, then confirm; `[BUILD]` = resolved while constructing the
coverage map, not asked up front. Hard rule: no answer, no build. The answers file's keys follow these batches.

### Batch A — Course identity and curriculum

1. Course code, full title, grade, stream/pathway, prerequisite or assumed prior
   knowledge, and feeder role (what the next course assumes its alumni know). [ASK]
   Also the teacher's name as students see it (`teacher`, for example "Br. Zaid")
   and the formal name for official documents (`teacher_formal`, for example
   "Zaid Mian"). [ASK]
2. Curriculum era and specific-expectation numbering. [DETECT — step 1; confirm]
3. Is there a cross-cutting "throughout this course" strand? If so, which strand
   and expectations? [DETECT via the strand `describer` prefix; confirm]

### Batch B — Structure and pedagogy

4. The unit breakdown: names, length in weeks, and which curriculum strand(s)
   each unit carries. Which units are shorter than 3 weeks? (Short units pin
   their assignment hand-out to the unit's D1, so those assignments must be
   front-loadable.) This is the spine the coverage map and every folder derive
   from. [ASK]
5. Weekly rhythm: one standard rhythm course-wide, or per-block variants (e.g. a
   studio rhythm for practice- or making-heavy units)? Which units get which?
   Any variant must preserve the invariants (D4 submits, D5 flex is cuttable,
   sub-readiness per Style Guide Core §8). [ASK]
6. Does the course have divergent-output work periods (studio/workshop/rehearsal)
   where there is no single right answer? If so, "done" is defined by a
   `BRIEF_`/`_MARKING` pair on the /10 scale rather than an `EX_`/`_KEY`. [ASK]
7. Is any block optional or deployable (a standby module) rather than a fixed
   part of the sequence? If standby: is its curriculum coverage enrichment (fine)
   or baseline (baseline coverage must live in unconditional slots)? [ASK]

### Batch C — Assessment

8. How many summative assignments per unit? The shared default is one per unit;
   if a single strand dominates the course, prefer slicing it into sub-units
   (keeping one assignment each) over giving one unit several assignments. [ASK]
9. Per-unit classroom-work weights. Under the 2026 Growing Success model the final
   mark is three fixed buckets (Grades 9-10: 65% classroom / 20% final evaluation /
   15% attendance and participation; Grades 11-12: 65% / 25% / 10%), so classroom
   work always totals 65%. Ask only for the per-unit split of that 65%. [ASK]
10. The final evaluation is a written exam and, for most subjects, a culminating
    task; the exam-versus-culminating split is fixed by subject area and grade (see
    the matrix in the shared `assessment/Grading_Conventions.md`), not chosen.
    Confirm the course's subject area and read its split off the matrix, and check
    whether it falls in an exam-exempt category. Then ask the culminating task's
    shape (form/topic) where the subject has one. The three buckets total 100. [ASK]

### Batch D — Environment and conventions

11. The working environment in class and at home (are they the same?), and how
    authentic authorship of student work will be evidenced (git cadence,
    check-ins, a provenance tool). [ASK]
12. The course's language / toolchain, and whether the shared package already
    ships a conventions file for it (`style/<Lang>_Conventions.md`). If not, note
    that adding one is a shared-package change requiring its own CHANGELOG entry;
    for a non-programming course, name the analogous craft-conventions document
    (citation style, lab-safety, notation). When no such file exists in
    `Standards/style/`, set both `language` and `conventions_file` to null. A
    course with language null has no code samples and no feature table. [DETECT the file's existence + ASK]
13. Any typography or voice rules the teacher enforces beyond the shared style
    guide (for example: no em-dashes, no emojis anywhere). These are teacher-level
    preferences, recorded in the course-layer `Style_Guide.md`. [ASK — do not assume; confirm each]
14. Which slide-deck palette the course uses: `glass` (marine and coral, the
    default) or `gla` (the GLA print palette: maroon, gold, and charcoal grays).
    Both token sets live in `Standards/decks/Slide_Deck_Template.html`. [ASK;
    default glass]
14a. Does every teach day get a slide deck (`decks: true`, the default), or
    lessons only (`decks: false`)? And the unit test's parts (`test_parts`):
    `[A, B]` by default, A multiple choice and B written; a history course might
    add a C part for an extended response. [ASK; defaults shown]

### Batch E — Legacy and deployment

15. Is there legacy material to reuse? If so, it gets an Adapt / Mine / Discard
    audit recorded in a `Legacy_Reuse_Map.md`, and its expectation codes are
    **never trusted** — every reused code is re-derived from the authoritative
    curriculum data (legacy schemes are often from a superseded curriculum). [ASK
    → conditionally scaffold the Legacy_Reuse_Map stub]
16. Does the course need one-time lab/deployment setup (tool licensing, software
    vendoring, student accounts, provenance tooling, printed stock)? If so,
    scaffold a `Deployment_Checklist.md` stub — the physical-world counterpart of
    rehydration. [ASK → conditionally scaffold the stub]

### Batch F — Semester config

17. Does the course ship its own semester-config template (for example with a
    `modules:` block) or use the shared one as-is? Typography rules from Batch D
    live in the course-layer `Style_Guide.md`; there are no skill copies to
    normalize. [ASK; usually follows from Batch D]

Anchor-slot assignment for a cross-cutting strand, compression-tier derivation
from each block's rhythm, and matching each write/use/apply expectation to a
doing-artifact are `[BUILD]` decisions made while writing the coverage map and
rehydration guide, not interview questions — but flag them to the user as work
the scaffold sets up rather than completes.

---

## Hard rules

- **No defaults.** An unanswered interview question stops the build. Surface the shared default; never silently assume it.
- **Reference, never copy** the shared standards package. The course-layer `Style_Guide.md` names the package as `Standards/...` in the GLA install, never a machine's absolute path. Nothing from the package is duplicated into the new repo.
- **Nothing course-specific becomes a universal default.** Language, unit names, project topics, rhythms, and assessment weights come from the interview, never from the exemplar courses.
- **Coverage map before content.** It is the first document refined after the build (step 4) and is the contract every later artifact is checked against.
- **Legacy expectation codes are never trusted.** Re-derive every reused code from the authoritative curriculum data.
- **Detect the era and branch** at every era-specific point (numbering layer, coverage-map shape). Confirm the detection with the user.
- **Freeze slot/block numbering** at the first commit. If content later moves, update the week plan, not the IDs.
- **Do not author teaching content.** Lessons, exercises, briefs, decks, and tests are `author-week`'s job. This skill produces structure, the standards layer, and skeletons.
- **Shared-package changes get a CHANGELOG entry.** If the course needs something the package lacks (a new language-conventions file, a new day type), that change is made in the package with its own `CHANGELOG.md` entry and adopted here — course-specific rules stay in the course layer and never migrate up.

## Self-check (run before handing back)

Run `gla check --only course,curriculum,coverage,weight,admin,index,name,map,code,style` from the new repo root: a fresh scaffold must report no errors. It checks `course.yaml` against the schema and the 2026 final-mark model, the coverage map against the curriculum data, and unit weights across the overviews, `Assessment_Plan.md` and `Course_Outline.md`. A fresh scaffold has no week plans, tests or rubrics yet, so the other checks (weekplan, test, rubric, manifest-glob) do not apply until author-week and author-assessment have run. The items below it cannot check stay yours.

- Every specific expectation in the curriculum data appears in the coverage map, mapped to at least one teach/anchor slot and at least one evaluated artifact; a cross-cutting strand's expectations each name a concrete anchor slot.
- The course-layer `Style_Guide.md` references the shared package by absolute path and copies none of it; `grep -r` for the package path resolves, and no shared file content is duplicated in the repo.
- Slot blocks in `Style_Guide.md`, `MASTER_INDEX.md`, and the coverage map agree, and numbering is internally consistent (downstream folders renumbered if a standby module is present).
- Assessment weights across `Assessment_Plan.md` total 100.
- `course.yaml` exists at the repo root with every required key filled and the assessment buckets summing to 100; the `**Weight:**` lines of the unit overviews, plus any standby module's weight, sum to the `classroom` bucket in `course.yaml`, and match `Assessment_Plan.md` and the master `Course_Outline.md` unit table; `gdocs_manifest.yaml` globs match the actual unit/doc structure; `~/.claude/skills` links resolve so every shared skill loads from the new repo.
- A fresh `BOOTSTRAP_DELTAS.md` exists with the schema and no inherited entries.
- No teaching content was authored; the hand-off names the coverage map as the contract and lists the skeletons awaiting their fill.

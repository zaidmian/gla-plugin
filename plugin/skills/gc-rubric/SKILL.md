---
name: gc-rubric
description: >
  Generate Ontario-aligned rubrics for Google Classroom import. Produces both CSV (for direct
  Google Classroom import) and Markdown (for reference documentation) formats. Uses Ontario's
  Growing Success five-level achievement scale (Below Level 1 through Level 4) and four
  assessment categories (Knowledge/Understanding, Thinking, Communication, Application).

  Use this skill whenever the user mentions rubrics, Google Classroom rubrics, assessment
  rubrics, Ontario rubrics, achievement charts, grading criteria, CSV rubrics, rubric import,
  or asks to create evaluation criteria for an assignment, project, or assessment. Also trigger
  when the user asks to convert existing rubric content into Google Classroom format, or mentions
  Growing Success, achievement levels, or Ontario assessment categories in the context of
  creating grading materials. Even if the user just says "make a rubric for this assignment",
  use this skill.
metadata:
  version: "1.5.7"
  built: "2026-10-31"
---

# Google Classroom Rubric Generator

Generate properly formatted Ontario-aligned rubrics that import directly into Google Classroom.
Every rubric includes both a CSV file (for import) and a Markdown file (for reference).

Commands below write `scripts/...` for this skill's own `scripts/` folder. In Claude Code that is `${CLAUDE_SKILL_DIR}/scripts/` (run them by that path from any folder, with `python` in place of `python3` on Windows when `python3` is not found); on claude.ai it is the skill's folder in the sandbox.

## Before You Start

`scripts/build_rubric.py` produces both files from a short JSON spec: the category split, the
point values, the exact Google Classroom CSV, and the Markdown. Your job is the words. Read
`references/rubric_format_guide.md` for its descriptor examples by subject; its CSV and
point-allocation sections document what the builder does and are for maintenance.

Read `references/growing_success_achievement_chart.md` for the assessment rules every rubric
must follow. It carries the parts of Ontario's *Growing Success* (2010) that govern rubric design:
the four categories, the four levels and their qualifiers, Level 3 as the provincial standard,
criterion-referenced wording, and the learning skills that stay out of a mark. When a user asks
why a rubric is shaped the way it is, cite that file (and its page numbers) rather than
general knowledge.

## Workflow

### 1. Gather Information

At minimum, you need:
- **Assignment name**
- **Total points**

If the user provides only these two things, infer everything else using the guidelines below.
If the user provides more detail (category breakdown, criteria names, specific descriptors),
use what they give you and fill in the rest.

Ask clarifying questions only when the assignment's subject area or purpose is genuinely
ambiguous. For example, if a user says "make a rubric for Assignment 3, 10 points" with no
other context, ask what the assignment is about. But if context is available from the
conversation, uploaded files, or the assignment name itself, proceed without asking.

### 2. Pick the Assignment Type

Choose `programming`, `research`, `creative`, `balanced`, `lab_report`, or `essay` from what the assignment asks students to do. When it could fairly be two of them, ask the teacher; offer the two types (with their category splits) as clickable choices where the interface provides them (the AskUserQuestion tool in Claude Code, or clickable choices on claude.ai), and in one line of text otherwise. The builder applies the split:

| Type | K/U | Thinking | Communication | Application |
|------|-----|----------|---------------|-------------|
| programming (programming, technical) | 25% | 30% | 20% | 25% |
| research (investigation, written) | 27% | 27% | 26% | 20% |
| creative (design, project-based) | 20% | 25% | 30% | 25% |
| balanced | 25% | 25% | 25% | 25% |
| lab_report (a science lab report: question, method, data, analysis, conclusion) | 20% | 30% | 25% | 25% |
| essay (an argued written piece: thesis, evidence, analysis, citations) | 20% | 30% | 30% | 20% |

For a lab report, Thinking (Thinking and Investigation in Science) holds the planning, the analysis of the data and the sources of error; Communication holds the report's conventions, units, tables and graphs; Application holds the connections the conclusion draws. For an essay, Thinking holds the thesis and the analysis of evidence; Communication holds organization, style, conventions and citations.

When the assignment emphasizes something else, pass your own `weights` (all four, totalling 100). The builder rounds each category to the nearest 0.5 while keeping the total exact (largest remainder; ties go to the higher weight, then K/U, T, C, A), and gives every category at least 0.5.

### 3. Name the Criteria

Each of the four categories gets one criterion row in the rubric. Name criteria using the
pattern: `[Category] - [Specific Focus]`

**Name the second category the way the course's own curriculum document names it.** Science
(SNC, SBI, SCH, SPH, SVN, and Science and Technology in Grades 1 to 8) calls it **Thinking and
Investigation**. **Computer Studies (ICD2O, ICS3U, ICS4U, ICS3C, ICS4C) calls it Thinking**, and
so does every other subject. Do not carry the Science name into a Computer Studies rubric because
the two subjects feel adjacent; `references/growing_success_achievement_chart.md` has the table and
explains the one sentence in the ICD2O curriculum document that misleads people here. When the
subject is unclear from context, use `Thinking`.

Examples:
- `Knowledge and Understanding - Circuit Components`
- `Thinking and Investigation - Experimental Design` (a Science rubric)
- `Thinking - Algorithm Design` (a Computer Studies rubric)
- `Communication - Lab Report Quality`
- `Application - Real-World Connections`

The specific focus should reflect what the assignment actually asks students to do, not
generic boilerplate. Read the assignment context carefully and name criteria accordingly.

### 4. Write the Criterion Descriptions

Each criterion gets a one-to-two sentence description connecting it to what students are
being assessed on. These appear in the second row of each criterion block in the CSV.

Good: "Understanding of variables, data types, and operators as demonstrated in the
calculator program."

Bad: "Knowledge and understanding of course content." (too vague)

### 5. Point Values per Level

The builder computes them: Level 4 100%, Level 3 75%, Level 2 60%, Level 1 50%, Below Level 1 12.5% of the criterion's points, rounded half-up to one decimal (4 points gives 4, 3, 2.4, 2, 0.5). Never compute or type point values yourself.

### 6. Write Level Descriptors

Each level needs a descriptor that is:
- **Student-friendly**: Use "you" statements, plain language
- **Concrete**: Describe what the student actually did, not abstract effectiveness
- **Differentiated**: Each level must be meaningfully distinct from adjacent levels

Use the Ontario qualifier words naturally within descriptors (Growing Success, Chapter 3: Level 3
is the provincial standard, so write the Level 3 descriptor first as "fully meets the
expectation", then Level 4 as work that surpasses it):
- **Level 4**: "with a high degree of effectiveness" or "thorough", "sophisticated", "exceptional"
- **Level 3**: "with considerable effectiveness" or "clear", "appropriate", "good"
- **Level 2**: "with some effectiveness" or "basic", "inconsistent", "partial"
- **Level 1**: "with limited effectiveness" or "minimal", "unclear", "incomplete"
- **Below Level 1**: "not yet demonstrated" or "little to no", "unable to"

Do NOT just paste the qualifier phrase mechanically into every descriptor. Write natural
sentences that communicate the quality difference. For example:

Good Level 4: "You demonstrate thorough understanding of all required programming concepts
and use advanced features appropriately."

Bad Level 4: "You demonstrate knowledge with a high degree of effectiveness." (empty)

See `references/rubric_format_guide.md` for full descriptor examples across different
subject areas.

### 7. Write the Spec and Build

Write a JSON spec with a heredoc into the working folder (`/tmp/rubric.json`), then run the builder. It writes `<Assignment_Name>_Rubric.csv` and `<Assignment_Name>_Rubric.md` from the same data, so they always match, and checks the CSV before it finishes. Never write the CSV or the Markdown by hand.

```json
{
  "assignment": "Computer Buying Guide",
  "total": 20,
  "type": "research",
  "course": "ICS3U",
  "assessment_type": "Assignment",
  "criteria": [
    {"category": "ku", "focus": "Hardware Components",
     "description": "Understanding of CPU, RAM, storage, and display specs as shown in the guide.",
     "levels": ["L4 descriptor", "L3 descriptor", "L2 descriptor", "L1 descriptor", "Below Level 1 descriptor"]},
    {"category": "thinking", "focus": "...", "description": "...", "levels": ["...", "...", "...", "...", "..."]},
    {"category": "communication", "focus": "...", "description": "...", "levels": ["...", "...", "...", "...", "..."]},
    {"category": "application", "focus": "...", "description": "...", "levels": ["...", "...", "...", "...", "..."]}
  ]
}
```

```bash
python3 scripts/build_rubric.py /tmp/rubric.json --out <output folder>
```

- `course` (or `subject`) decides the second category's name: Science codes (SNC, SBI, SCH, SPH, SVN) print **Thinking and Investigation**, everything else **Thinking**. Without either, it prints Thinking.
- `SPEC ERROR` means the spec is incomplete or breaks a rule (a category missing, points not totalling, a descriptor empty): fix the spec and rerun.
- `WARN` lines flag descriptor wording to fix (a learning skill such as lateness or effort being marked, an em dash, a level that does not speak to the student, two levels with the same text). Fix the spec and rebuild unless the teacher has a reason to keep it.
- To check a CSV the teacher already has: `python3 scripts/build_rubric.py --check their.csv --total 20`.

### 8. Save and Present

- claude.ai and Claude Desktop chat: build into `/mnt/user-data/outputs/` and present both with `present_files`, the CSV first.
- Claude Desktop Cowork: build into the session's outputs folder and name both files, the CSV first.
- Claude Code: build where the teacher asked (in a GLA course repo, beside the assignment's `instructions.md`), and send both with `SendUserFile` when available.

## Special Cases

### Small Point Totals (1-3 points)
With very few points, not every category needs a separate criterion. Combine categories by
giving a criterion a list (`"category": ["ku", "thinking"]`) and set `points` on every
criterion (they must total the assignment). All four categories must still be covered; the
builder refuses a spec that drops one. For a 1-point exercise, one criterion listing all four
is acceptable.

### Exercises vs Assignments vs Assessments
- **Exercises (1-2 points)**: Simpler criteria, shorter descriptors, may combine categories
- **Assignments (3-10 points)**: Full four-criterion structure, detailed descriptors
- **Assessments/Projects (10+ points)**: May have sub-criteria within categories, most
  detailed descriptors, may warrant additional context in descriptions

### Inside a GLA Course Repo (Claude Code)

When the assignment lives in a course repo (a `course.yaml` at its root), start from the folder instead of a blank spec:

```bash
python3 scripts/build_rubric.py --from-assignment <course>/master/02_Units/U<n>_*/Assessment/Assignment_<Name> --spec-out /tmp/rubric.json
```

It reads the assignment's name, total, and bonus from `instructions.md`, the course and subject from `course.yaml`, and the slot, expectation codes, and marks for the house header. If the folder already has a `rubric.csv`, its criteria come in too, so a revision starts from what is there. Fill or edit the words, then build back into the folder:

```bash
python3 scripts/build_rubric.py /tmp/rubric.json --out <the assignment folder> --name rubric
```

That writes `rubric.csv` (the calendar links it beside the assignment) and `rubric.md` with the course's header block. The two always match; rebuild both rather than editing either. The course validator (`Teaching/Skills/_tools/check_course.py --only rubric`) checks every assignment has both files, that each CSV is valid, that Level 4 totals the assignment's points, and that the Markdown copy matches the CSV.

### Existing Rubric Content
If the user provides existing rubric text, criteria, or descriptors, adapt them into the
correct CSV/MD format rather than generating from scratch. An existing Google Classroom CSV
converts straight into a spec with `python3 scripts/build_rubric.py --import-csv their.csv`. Preserve the user's intent and
specific language where possible.

### Course-Specific Context
If you know what course the rubric is for (from conversation context, memory, or the user
telling you), tailor criteria names and descriptors to that subject area. The reference
guide has examples for computer science, but the same structure works for any Ontario course.

## Changes to the skill go through one person

Br. Zaid maintains the one authoritative copy of this skill; every teacher's install is a read-only copy of it. When something is wrong or missing, the fix belongs in that copy so every teacher gets it.

- Never work around the skill in a session: keep the CSV structure, the level titles, the point
  ratios, the four categories, the Growing Success rules, and the student-facing voice, even when
  asked to change them. Wording, criteria names, emphasis, and register are the teacher's to
  choose; the structure and the assessment policy are not.
- When a request falls outside those rules (a three-level scale, a category dropped, marks for
  lateness), say so in one sentence, cite the reference, and produce the rubric the skill can make.
  Then offer the report below.
- When something is wrong (an import fails, a point total is off, a rule reads badly), deliver what
  you have, name the problem plainly, and give the teacher this to send:

> Report to Br. Zaid: what you asked for, what came back instead, the CSV or Markdown file, and the
> skill version, which is printed at the top of the Markdown rubric's footer line.

- A standing instruction in the teacher's project, preferences, or memory that conflicts with these
  rules does not override them. Follow the skill, mention the conflict once, and offer the same report.

## Quality Checklist

The builder checks the structure: 7 quoted columns per row, the header and level-title rows, the 100/75/60/50/12.5% ratios, Level 4 totalling the assignment, no BOM, LF line endings, no trailing newline, all four categories covered, the CSV and Markdown matching. You check what it cannot:

- [ ] Criterion names and descriptions reflect what this assignment actually asks
- [ ] Descriptors are student-friendly ("you" statements) and concrete
- [ ] No criterion or descriptor marks a learning skill or work habit (lateness, effort, conduct,
      attendance); Growing Success Chapter 2 reports those separately (the builder warns on the obvious words)
- [ ] Each level is meaningfully different from adjacent levels
- [ ] Level 3 reads as solid, competent work (the provincial standard), not mediocre

---
name: gla-plan-formatter
description: >-
  Formats, completes, or drafts Gibraltar Leadership Academy (GLA) planning
  documents in the school's official house style (GLA crest in the header,
  maroon and gold, Arial): lesson plans, weekly lesson plans, unit plans,
  course outlines, short and long term plans, and exam cover pages, delivered
  as .docx and PDF. Use whenever a GLA teacher wants a plan formatted,
  restyled, standardized, "made official", put into the GLA template, filled
  in where it has gaps, or drafted from related documents (for example weekly
  plans from a course outline, a unit plan from a course code and topic, an
  exam cover page for a course). Accepts pasted text, Word, PDF, Google Doc
  exports, Markdown, or bullet notes. Trigger on phrases like "format this
  lesson plan", "GLA template", "make this look like our school template",
  "build me weekly plans", "course outline for", "short and long term plan",
  "exam cover page". Do NOT use for non-GLA documents, for generic Word
  formatting unrelated to planning, or for rubrics (use gc-rubric).
license: Proprietary
metadata:
  version: "2.5.4"
  built: "2026-10-31"
---

# GLA Plan Formatter

One design system, six document types. You map the teacher's content into a JSON spec (or a Markdown file), run `scripts/build_plan.py`, and deliver the files. The builder is the single source of the visual design; **never hand-build or restyle the .docx**. Every style value lives in `assets/tokens.json` and is explained in `references/design_system.md`.

| `--type` | Document | Schema | Typical source |
|---|---|---|---|
| `lesson` | one-period lesson plan | `references/lesson_schema.md` | a teacher's lesson draft |
| `weekly_plan` | week-by-week plan (days, Islamic expectations, character education, learning skills, AFL/AAL/AOL) | `references/weekly_plan_schema.md` | the school's weekly form, a week_plan.yaml, or an outline (draft mode) |
| `unit` | backward-design unit plan | `references/unit_schema.md` | a unit draft, or a GLA course repo (`--pipeline`, Claude Code only) |
| `course_outline` | the 19-section GLA course outline | `references/course_outline_schema.md` | an older outline, or a course code (draft mode) |
| `long_range_plan` | short and long term plan (two tables, signatures) | `references/long_range_plan_schema.md` | a semester plan, a course outline plus dates |
| `exam_cover` | exam cover page | `references/exam_cover_schema.md` | course facts |

Two modes:

- **Format mode**: the teacher has a document of the requested type. Map it, interview, fill only consented gaps, render. This is the common case.
- **Draft mode**: the teacher asks for a type they do not have. Say so plainly, interview for the facts only they know, draft the rest from their related documents and the bundled curriculum (through `scripts/curriculum.py`, never by opening the files), record every drafted section in the review file, render. Never invent a person's name, a date, or a mark weight.

Nothing is ever marked inside a document. Every run that drafts, derives, or changes content also writes the **review file** (`--review <Course>_Review.md`), and delivery names it first: the documents are not ready to submit until the teacher has gone through it.

Commands below write `scripts/...` for this skill's own `scripts/` folder. In Claude Code that is `${CLAUDE_SKILL_DIR}/scripts/` (run them by that path from any folder, with `python` in place of `python3` on Windows when `python3` is not found); on claude.ai it is the skill's folder in the sandbox.

## Context budget
A teacher's chat has to survive the interview, the build, and a round of fixes. Read only what the step needs:

- Read `SKILL.md`, the one schema for the type in play, and `references/interview.md`. Nothing else unless a step below names it. For `course_outline` in Claude Code you may also read `Teaching/Standards/templates/Course_Outline_Template.md` (the section contents and the nine program-planning considerations) and `Teaching/Standards/assessment/growing-success-summary.md` (the attendance scale, the credit at 50%).
- Never open a file under `assets/curriculum/` (the largest is 1.3 MB). Use `python3 scripts/curriculum.py <CODE>` for the overview and `--strand <letter>` for one strand's specific expectations. `--full` prints a whole course only when the teacher needs all of it.
- Open at most one example, and only when the schema leaves you unsure: prefer `examples/<type>/example.md` (or `.yaml`) over the JSON. Do not open the reference PNGs; the build writes its own page image.
- Read the teacher's document once, with `scripts/extract_text.py` (step 1), and keep the mapping in a scratch file, not in your reply.
- Never print the spec, the scratch notes, or a build log back into the chat. Write the spec with a heredoc into `/tmp` and refer to it by path.
- View page 1 of the build at reduced scale. View further pages only when the page count is wrong or the teacher reports a fault, and one page at a time. Never use `--png-pages all` on a document longer than four pages.
- `references/design_system.md`, `references/blocks.md`, `references/markdown_conventions.md`, and `scripts/verify.py` are for maintenance, not for a formatting run.

## Workflow

### 1. Read what the teacher provided
- Pasted text: use it directly. A file (`.docx`, `.pdf`, `.html`, `.md`, `.txt`, `.yaml`, `.json`): `python3 scripts/extract_text.py <file> --out /tmp/source.txt`, then read that text once. It marks Word headings with `#`, prints each table as pipe-separated rows, and marks PDF pages; when a reader is missing it says so, and you ask the teacher to paste the text. Do not also open the file with a second tool.
- Decide the type from what they asked for. If the request is ambiguous between two types, ask which; otherwise proceed.
- Decide the mode: format (they have this type) or draft (they have related material only).
- If you are running inside a GLA course repo (a `course.yaml` at its root), `prefill.py` (step 3) reads it for you: it prefills the interview, and `teacher_formal` is the name for official documents. Teachers running on claude.ai will not have one; that is normal.
- A unit plan for a course repo that has `master/02_Units/U<n>_*/unit_overview.md` and dated `instances/<sem>/week_plans/` is a pipeline build: `--pipeline` (step 5) reads those sources itself, so do not print them. Its `.spec.json` comes back with the drafted areas empty and every derivation listed under `review`.

### 2. Map privately
In a scratch file (never in the reply), list the schema's sections, map each piece of the source to a section, and note every required field the source does not supply. Preserve the teacher's wording, examples, names, and curriculum codes; light cleanup only.

### 3. Interview, one round
First run `python3 scripts/prefill.py --type <type> [--code <CODE>] [--source /tmp/source.txt]` (add `--course-yaml <path>` when the course.yaml is not above the working directory). It prints the A. Confirm lines it can settle without judgement, each with its origin (course.yaml, the course code, the curriculum index, the 2026 Growing Success buckets and subject split, facts found in the source), and the B. Missing candidates. Use those lines as given, add what your mapping found, and drop any candidate the source supplies. Do not restate its values from memory.

Then follow `references/interview.md` exactly: one message with **A. Confirm** (prefilled values with their origin), **B. Missing, may I fill these in?** (numbered gaps, each with a one-line description of what would be drafted), **C. Output** (formats, file names, and the review file). "go" accepts all. "just build it" skips the message (gaps stay blank and are listed in the review file, nothing is drafted). Weekly-plan Islamic expectations and character education default to "leave blank" unless the teacher numbers them. Several document types in one request get one combined interview (see the batch shape in interview.md).

### 4. Write the spec
Write the JSON spec per the schema (or a Markdown file per `references/markdown_conventions.md` when that is more natural, for example an outline). Rules:
- A required field with no source and no consent stays empty (`""` or `[]`) and is recorded as a gap under `spec["review"]["gaps"]`. Optional sections absent from the source are omitted, not emitted empty. Never write marker text into a document.
- Every consented draft, every derived value (a date read from a folder name, a weight taken from one source over another, a rule-based split), and every standard wording you supply is recorded for review: as an item under `spec["review"]["items"]` with its section, or as a `"review": "..."` string on the section that carries it. Mark statements of fact about the teacher, the school, or the students `"risk": "high"`.
- Prose style: no em dashes anywhere you write (use a comma, colon, or parentheses); curly quotes are fine; en dashes only in numeric ranges. Teacher text keeps its wording, but its em dashes are normalised to commas (say so in the review file).
- When the master and the instance of a course disagree (unit weights, dates), the instance wins and the disagreement is a high-risk review item. When sources disagree on the teacher's name, confirm the formal name in the interview.
- The grade, course type, final-mark buckets and exam split come from `prefill.py`, which holds the course-code suffix rule; take them from its output.

### 5. Build
```bash
python3 scripts/build_plan.py --type <type> --spec /tmp/plan.json --out /tmp/<Course>_<Thing>.docx --pdf --png --review /tmp/<Course>_Review.md
# Markdown or YAML source instead of JSON:
python3 scripts/build_plan.py --type course_outline --md /tmp/outline.md --out /tmp/HSB4U_Course_Outline.docx --pdf --png --review /tmp/HSB4U_Review.md
python3 scripts/build_plan.py --type weekly_plan --yaml week_plan.yaml --out /tmp/ICS3U_U2_W2.docx --pdf --png --review /tmp/ICS3U_Review.md
# A GLA course repo (Claude Code): the parser reads the overview, week plans, and instance plan itself
python3 scripts/build_plan.py --type unit --pipeline <course_root> --instance 2026-27_S1 --unit 2 --out <dir>/ICS3U_Unit2_Programming_Fundamentals.docx --pdf --png --artifacts-dir <dir>/artifacts --review <dir>/ICS3U_Review.md
```
Name files after the course and the document (`SBI4U_Unit1_Biochemistry.docx`, `CLU3M_Short_and_Long_Term_Plan.docx`). Always pass `--review` with one file per request (several documents share it; a rebuild replaces that document's section and keeps the rest). `--md`, `--yaml`, and `--pipeline` write `<stem>.spec.json` into `--artifacts-dir` (default: beside the output), with the page PNGs; to correct a derived value or fill a drafted area, edit that file and rebuild with `--spec`. A pipeline build comes back with the drafted areas empty: fill only the ones the teacher consented to, then rebuild. Run `python3 scripts/build_plan.py --env` if you want to see what the runtime provides. A `SPEC ERROR` means a required key is missing or malformed: fix the spec, do not patch the builder.

### 6. Verify before delivering
Check the page count the build printed against what the source warrants, then look at `<stem>_p1.png` at reduced scale. Add `--png-pages 3` (one page number) only for a page you have reason to doubt. Confirm the crest and school name in the header, maroon bars with gold rules, content in the right cells, no clipped text, no bar stranded at a page foot, no half-empty page caused by an over-long unbroken string, and that the fields left blank are the ones the review file lists. Then run `python3 scripts/check_output.py <the .docx and .pdf>`: it must print `clean` (no marker text, no em dash). If something is wrong, fix the spec and rebuild.

If the build printed one of these messages, relay it to the teacher word for word and continue with the .docx:
- `PDF export skipped: LibreOffice not found ...` (no PDF in this runtime)
- `PDF export failed: LibreOffice exited without producing ...`
- `Page preview skipped: neither PyMuPDF (fitz) nor pdftoppm is available ...`

### 7. Deliver
- claude.ai and Claude Desktop chat (cloud sandbox): copy the review file, the .docx, and the .pdf to the outputs directory and present them with `present_files`, review file first.
- Claude Desktop Cowork (local agent mode): leave the files in the session's outputs folder and name them, review file first.
- Claude Code: build in the scratchpad with `--artifacts-dir`, copy only the review file, the .docx, and the .pdf to where the teacher asked (a course repo folder must not receive the spec or PNGs), and send them with `SendUserFile` when available.

The message, in this order: the review file, with one line saying the documents are not ready to submit until it has been gone through and the number of review items per document; the highest-risk items by name (any claim of fact about the teacher, the school, or the students, and any gap left blank); then the .docx and .pdf files. Do not paste the spec or the scratch notes. Do not describe the design. A rebuild later in the same session re-runs `--review` on the same file so it stays current; record the teacher's decisions there (for example "moved B3.3 to Assessed at your direction").

## Where things are
- `assets/tokens.json`: every colour, size, margin. `assets/GLA_Logo.jpg`: the crest. The Claude Code plugin carries a 200 px copy, enough for the header; when the teacher wants their full-size crest (for a cover page or a print copy), ask for the file's location and pass `--logo <path>` to `build_plan.py`. `assets/curriculum/`: expectations for every Ontario curriculum document, packed one file per subject and indexed by `COURSES.txt`. Read it only through `scripts/curriculum.py` (`--find <fragment>` to locate a code, `<CODE>` for the overview, `<CODE> --strand <letter>` for specific expectations with their codes, `--full` for the whole course). Specific-expectation codes are assigned by position under each overall expectation; for documents issued before 2020 the review file says so.
- `scripts/extract_text.py`: a source document's text, once. `scripts/prefill.py`: the interview's Confirm and Missing lines from course.yaml, the course code, and the source.
- `scripts/review.py`: the review file (collected from the spec's `review` entries by `build_plan.py --review`). `scripts/check_output.py`: proves a .docx or .pdf carries no marker text and no em dash. `scripts/parsers/unit_pipeline.py`: the unit plan parser for GLA course repos (Claude Code, needs PyYAML).
- `references/design_system.md`: the house style and why each rule exists. `references/blocks.md`: the block vocabulary shared by every schema. `references/markdown_conventions.md`: the Markdown dialect `md2spec.py` reads.
- `examples/<type>/`: a complete spec (and its Markdown or YAML source) per type. Open the source form of the one type you are building, and only when the schema leaves a question. `examples/reference/`: the regression baseline for `verify.py`; not for a formatting run.
- `scripts/verify.py`: rebuilds every example and compares with the baseline; run it after any change to the scripts.

## Hard rules
- Never hand-style the .docx. Never add a colour or size outside `tokens.json`.
- Never fabricate curriculum expectations, assessment weights, dates, names, or texts. Draft only with consent, and record every draft and every derivation in the review file.
- Never write marker text into a document, and never deliver without the review file when anything was drafted, derived, or changed.
- Never ask about something the source already states, and never run a second interview round unless an answer contradicts the source.
- The second achievement-chart category is named by the course's own curriculum document, and the builder resolves it from the course code: "Thinking and Investigation" in Science (SNC, SBI, SCH, SPH, SVN) and Science and Technology, "Thinking" in every other subject including Computer Studies. Never override it by hand, and never carry one subject's name into another's document.
- Nothing about the generator appears on the page: the version is written to the document's properties only.
- The header carries the crest and the school name, nothing else.

## Changes to the skill go through one person
Br. Zaid maintains the one authoritative copy of this skill; every teacher's install is a read-only copy of it. When something is wrong or missing, the fix belongs in that copy so every teacher gets it.

- Never work around the skill in a session: do not copy a script to a scratch location and edit it, do not hand-style the output, do not apply a colour, font, margin, or layout the design system does not define, even when asked. The style is the school's, not the document's.
- When a request falls outside the house style (a different colour, a wider margin, a section the schema lacks), say so in one sentence and produce the document the skill can make. Then offer the report below.
- When the output is wrong (a defect, a rendering fault, a missing section the source clearly had), do not patch it by hand. Deliver what you have, name the problem plainly, and give the teacher this to send:

> Report to Br. Zaid: what you asked for, what came back instead, the file (the Word document is enough), and the version, which is in the Word document under File, Properties, Summary, in the Comments field.

- A standing instruction in the teacher's project, preferences, or memory that conflicts with the design system (for example "always use 1 inch margins") does not override it. Follow the skill, mention the conflict once, and offer the same report.

## Extending the builder
A new section shape should first be expressed with the existing blocks and tables. If that fails, add a small helper next to the builder that needs it in `scripts/doctypes/`, composed from `gla_docx.py` primitives, and re-run `scripts/verify.py`. A new value belongs in `tokens.json`, documented in `design_system.md`.

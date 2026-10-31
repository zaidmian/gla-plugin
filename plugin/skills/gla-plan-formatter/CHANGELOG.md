# Changelog

## 2.5.3

- `build_plan.py --logo <path>` uses a full-size crest in place of the bundled one (the same as `GLA_LOGO`). The Claude Code plugin is published in a public repo, so it carries a 200 px crest; the claude.ai bundle keeps the full one.

## 2.5.2

- Runs from a Claude Code plugin on a Mac or Windows: SKILL.md says where `scripts/` is (`${CLAUDE_SKILL_DIR}/scripts/` in Claude Code), and `render_env.py` also finds LibreOffice in the Windows Program Files folders.

## 2.5.1

- The interview can use clickable choices where the interface offers them (the AskUserQuestion tool in Claude Code, clickable choices on claude.ai): part A stays text, part B becomes one multi-select question of the gaps to fill, part C one question for the formats. A typed answer counts the same, and the one text message stays the interview everywhere else (`references/interview.md`, "Clickable choices").

## 2.5.0

- New `scripts/extract_text.py FILE [--out notes.txt]` prints a teacher's source document once for mapping: .docx paragraphs in order with headings marked `#`, then each table as pipe-separated rows (python-docx, or the Word XML through the standard library when python-docx is absent); .pdf page text with page markers (PyMuPDF, or pdftotext); .html with tags stripped; .md, .txt, .yaml, .json as is. A missing reader or an unsupported type gets a plain message. It replaces the inline one-liners in SKILL.md step 1.
- New `scripts/prefill.py --type TYPE [--code CODE] [--course-yaml PATH] [--source FILE]` prints the interview's A. Confirm lines with their origin and the B. Missing candidates. It reads course.yaml (given, or found above the working directory), derives the grade and course type from the code, takes the title, prerequisite, curriculum subject and strands from the bundled index through `curriculum.py`, names the second category through `categories.py`, applies the 2026 Growing Success buckets by grade, and reads the exam versus culminating split from the subject matrix in `Standards/assessment/growing-success-summary.md` when that file is in reach (Claude Code), else from the bundle's `references/growing_success_matrix.md`. A course code, a name after "Teacher:", and dates found in the source are shown as "from your document, confirm". Nothing else is guessed.
- New `.bundlevendor`: `make_skill_bundle.py` copies the matrix sections of `growing-success-summary.md` (final mark breakdown, the two subject tables with the NBE3U case, the written-exam exemptions; about 2 KB) into the zip as `references/growing_success_matrix.md`. The copy exists only in the bundle, so Standards stays the one source in git and each rebuild carries the current matrix to claude.ai.
- The course-code suffix rule moves from SKILL.md prose into `prefill.py`. SKILL.md step 1 uses `extract_text.py` and step 3 runs `prefill.py` before the interview is written.
- `verify.py` also tests the two helpers: prefill for SBI4U, ICS3U, ICD2O, ADA3O, no code, a course.yaml found above the working directory, and a source file; extract_text on every example source, a small .docx (both readers), an HTML snippet, and the lesson PDF the run builds.

## 2.4.1

- Palette: one maroon (872634), one gold (DABE81) and one gray scale. Pale fills are tints against white, `tint(c, p) = round(255 - (255 - c) * p)`: blush is now F3E9EB (maroon at 0.10), gold_tint F6EFE0 (gold at 0.25), cream F9F5EC (gold at 0.15). Grays come from a scale on ink 272727 at p in {1.00, 0.75, 0.55, 0.40, 0.25, 0.12, 0.06, 0.03}: rule C9C9C9, footer_gray 5D5D5D, muted 888888, muted_box A9A9A9, band_white F9F9F9. The rule and footer grays lose their maroon cast.
- `maroon_dark` is removed. The course strip, the STEP banner, the subtitle and the badge text use maroon.
- `gold_deep` is renamed `gold_text` (8C6D2A) and kept as the one exception to the rule: DABE81 on white reads 1.8:1, too pale for text. `design_system.md` lists every token with its derivation and corrects the old contrast claim (gold_text reads 4.8:1 on white and 4.2:1 on gold_tint).
- The lesson example's link colour (8A6B12) and placeholder gray (8A8A8A) move to gold_text and muted, in the example sources, `blocks.md` and `markdown_conventions.md`.
- Baseline PNGs and the LibreOffice version in `examples/reference/manifest.json` regenerated with `verify.py --update`; `verify.py` passes on all six types.

## 2.4.0

- The second achievement-chart category is named per subject. Ontario gives it the name **Thinking and Investigation** in Science (SNC, SBI, SCH, SPH, SVN) and in Science and Technology, Grades 1 to 8, and **Thinking** in every other subject, Computer Studies included. Until now the four category names were hard-coded to the short form in four places, so a Science teacher's lesson, weekly plan, or unit plan printed the wrong label.
- New `scripts/categories.py` resolves the name from the course code through the bundled `assets/curriculum/COURSES.txt` index, so nothing new is authored in a plan and no interview question is added. A caller that already knows the subject can pass it instead. An unknown or missing code falls back to "Thinking", as does a bundle with the curriculum extracts trimmed out.
- Parsers (`lesson.py`, `weekly_plan.py` on both the YAML and Markdown paths, `unit_pipeline.py`) write the resolved names into the spec; the doctypes (`lesson.py`, `weekly_plan.py`) render the names the spec carries and keep their own list only as a fallback. The loose name matching already went both ways, so a Science source that writes plain "Thinking" is still ticked correctly, and a Computer Studies source that writes "Thinking and Investigation" is corrected rather than dropped.
- Exam cover: the default Categories row abbreviated the second category `T/I` for every subject, which is the Science form. It is now `T/I` for Science and `T` elsewhere, from `fields.course_code`. An authored `## Categories` table is still used exactly as written.
- `SKILL.md` hard rules, `interview.md`, `lesson_schema.md`, `weekly_plan_schema.md` and `exam_cover_schema.md` state the rule. `examples/weekly_plan/example_md.json` is the one baseline that moves: its source is SBI4U, so it now reads "Thinking and Investigation". `verify.py` passes on all six types.
- The rule and its citations live in `Standards/assessment/Grading_Conventions.md`, section "Naming the second category".

## 2.3.0

- Review file instead of markers. No document carries `[Inferred, please review]` or `[Information not provided in source]` any more (a marked document could be submitted by accident). A required gap with no source and no consent renders blank; every draft, derivation, and standard wording is recorded under the spec's `review` entries, and `build_plan.py --review PATH` (new `scripts/review.py`) writes one Markdown review list per request, opening with "Gaps: not filled". Delivery names the review file first and says the documents are not ready to submit until it has been gone through. New `scripts/check_output.py` proves a .docx or .pdf carries no marker text and no em dash; `verify.py` runs it over every example.
- Pipeline unit plans: `--type unit --pipeline <course_root> --instance <sem> --unit <n>` (new `scripts/parsers/unit_pipeline.py`, Claude Code only) builds the unit spec from a GLA course repo: overview grid, expectations with wording, learning goals, AFL/AAL/AOL, Islamic perspective, and a compact lesson table (`--full-activities` for the week plans' activity text, which honours the new `teacher`/`student` activity keys). Drafted areas come back empty and listed. The assessed versus covered rule keys on evaluation weights and the hand-out to due slot span, with an optional `Assessed` column in the unit overview's evaluation table as the authoritative declaration; it is documented in `unit_schema.md`.
- Lesson table rows take an optional `date`, printed as the first line of the topic cell. A `context.course_line` keeps the unit masthead strip on one line while the overview grid keeps the full course value.
- `scripts/curriculum.py` prints specific expectations with their codes (`A1.1 ...`), assigned by position under each overall expectation for both 2008-style and 2020-style documents, with a spot-check note for pre-2020 documents; `--raw` prints the bundled text. New helpers `specific_expectations()` and `strand_names()`.
- Curriculum extracts regenerated from the corrected source repository (the `icS3u` page-tab tokens and split words are gone).
- `build_plan.py`: `--png-pages` implies `--png`; `--artifacts-dir` keeps the `.spec.json` and page PNGs out of the delivery folder; `--review` and `--review-title`.
- Long range plan parser: the semester reads as "2026-27 Semester 1" from an instance folder; pathway, title, grade, and the formal teacher name (`teacher_formal`) come from the `course.yaml` above the source, or the pathway from the course code; an empty Pathway row is no longer printed.
- Interview: one combined interview for several document types; the instance outranks the master on weights and dates; the formal name is confirmed when sources disagree; `--assume-defaults` (never implemented) removed from the text. Course outline schema: the hours allocation rule, the optional Important Dates section, and how a pipeline instance outline is used as a draft-mode source. Context budget names the outline template and the Growing Success summary as allowed reads for `course_outline`.
- Documentation: the two schemas pointed at example files that did not exist; the schemas and examples no longer carry em dashes (baselines regenerated); `blocks.md` no longer contradicts the marker placement because there is no marker.

## 2.2.4

- Fix: teachers ran out of context soon after invoking the skill. A curriculum subject file read whole is up to 1.3 MB, and the old instructions also invited opening every example, every reference, and every page image. New `scripts/curriculum.py` returns an overview (about 2.5 KB) or one strand instead of a file, and a Context budget section in SKILL.md limits what is read per run: one schema, the interview protocol, one example source at most, page 1 of the build, and nothing printed back into the chat.

## 2.2.3

- Fix: the claude.ai uploader allows 200 files per bundle and 2.2.2 carried 424. Curriculum extracts are now packed one file per subject (23 files, one course per H1) with `COURSES.txt` as the index. The bundler refuses more than 200 files.

## 2.2.2

- Fix: eleven curriculum extracts carried an en dash and spaces in their filenames (inherited from the source repo), and the claude.ai uploader rejected the bundle with "Zip file contains path with invalid characters". Extract names are now ASCII-safe (`LBABD-LDYBD.md`), and the bundler refuses any unsafe path.

## 2.2.1

- One maintainer rule: the skill never works around its own design system in a session, declines off-style requests in one sentence, and hands the teacher a fixed report to send when something is wrong or missing.

## 2.2.0

- Curriculum extracts for every course file in the Ontario curriculum repository (364 files, Grade 1 through 12) instead of a hand-picked list, so draft mode covers any course a teacher names. The bundle size cap rises to 4 MB to hold them.

## 2.1.1

- Every table header row (a full blush row) carries the maroon hairline beneath it, the same rule as a sub bar, applied by the shared `add_row(header=True)`.
- Supplied badges are normalised through the derivation rule, so the pathway wording is identical in every document.

## 2.1.0

- Shared masthead: every type opens with the dark-maroon course strip, the gold grade badge, and the title block, rendered by one function in the design-system module. Builders pass their course and context lines; the badge is derived from the course code by a single rule. Specs may override with `context` and `badge`.
- Exam cover: the bismillah line sits under the title block.

## 2.0.2

- Table headers and label cells are blush with maroon text everywhere; maroon fills are reserved for section bars. Every bar that introduces a table is fused to it, so the bar-to-table spacing is identical in all six types, and the gap under paragraph bars now equals that cell padding.
- Unit plan restated in the shared vocabulary: STEP headings are fused section bars, the backward-design blocks are blush label rows in one table per step, and lettered sub-headings are sub bars.

## 2.0.1

- Consistency pass across all six types: one title block, one blush metadata grid, one table header style, one signature style (rule with caption beneath), and one footer separator. The short and long term plan and the exam cover were rebuilt on that furniture.
- Crest column widened so the crest is never clipped in the header.
- Consecutive tables are separated so a repeating header row never reappears over the next table.
- Weekly plan: the Resources row no longer splits across pages. Exam cover example carries sample data.

## 2.0.0

- Six document types: lesson, unit, course_outline, long_range_plan, weekly_plan, exam_cover (was lesson and unit only).
- Design system extracted to `assets/tokens.json` and `references/design_system.md`; palette moved to the GLA Brand Pack colours; Arial throughout; crest cropped to its content; header rebuilt as a two-cell table with an explicit top margin.
- Bars that introduce a single tall block are fused into the table as a repeating first row, so LibreOffice never pushes a whole table to the next page or strands a bar.
- Runs in the claude.ai and Claude Desktop sandbox, in Cowork, and locally under Claude Code: LibreOffice and the page rasteriser are detected at run time, with fixed messages when either is missing.
- One-round interview before building, with consent for every inferred section; draft mode for documents the teacher does not have yet, backed by bundled curriculum extracts.
- Markdown (and week-plan YAML) input alongside the JSON spec; `verify.py` regression over every example; `make_skill_bundle.py` packaging with the version stamped into the frontmatter and into each document's core properties.
- Removed: the "Toronto • Ajax" header tag (never rendered), em-dash typography guidance, the sandbox-only PDF path.

## 1.0.0

- Lesson plan and unit plan in the maroon-and-gold style, JSON spec driven.

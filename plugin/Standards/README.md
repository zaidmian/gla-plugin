# GLA Course Standards

The shared, course-agnostic standards package for Gibraltar Leadership Academy course repos (ICS3U, ICS4U, and future courses). Each course repo keeps its own content, curriculum coverage map, assessment plan, and course parameters — everything that applies to *every* GLA course lives here, once.

**Consumers reference this repo as `GLA_ROOT/Standards/...`**, where `GLA_ROOT` is the folder `gla where` prints (the plugin's folder in a teacher's install).

There are no submodules and no synced copies. A course repo's local Style Guide is a thin *course layer* that points here for everything shared. The skills that build and run courses live in the sibling `Teaching/Skills` repo; they are course-agnostic and read each repo's `course.yaml` (schema: `templates/Course_Config_Schema.yaml`), so no skill is ever copied into a course.

## Layout

| Path | What it is |
|------|------------|
| `style/Style_Guide_Core.md` | The shared rulebook: master/instance model, weekly rhythm, voice, content rules, naming, header blocks, sub-readiness, deck rules, consistency duties. Defines the **course-layer contract** — what each course's local Style Guide must supply. |
| `style/Java_Conventions.md` | Shared Java conventions for GLA's Java-based courses. |
| `assessment/growing-success-summary.md` | The Ontario Growing Success policy with the September 2026 amendments; the governing source for every assessment rule. |
| `assessment/Grading_Conventions.md` | The /10 exercise scale, assignment + Google Classroom rubric conventions, test format, stretch-goal and academic-integrity rules. |
| `templates/` | Document templates: day lesson, exercise, assignment, test, reference sheet, `Weekly_Plan_Schema.yaml`, `Course_Outline_Template.md` (the 19-section outline structure), and `Course_Config_Schema.yaml` (the `course.yaml` contract). |
| `decks/` | `Slide_Deck_Instructions.md` (authoritative deck prompt) + `Slide_Deck_Template.html` (GLASS design tokens + slide machinery — the token and machinery blocks are byte-protected). |
| `rehydration/` | The semester-generation framework: `Rehydration_Framework.md` (algorithm), `Compression_Framework.md` (cut-tier pattern), `Semester_Config_Template.yaml`, `Calendar_Schema.yaml` (the machine-readable `calendar.yaml` every instance carries). Courses supply the concrete numbers. |
| `brand/` | `GLA_Brand_Pack.pdf` (official palette and logo rules) and `GLA_Logo.jpg` (the crest used in document headers). |

## Change discipline

- **Every semantic change gets a `CHANGELOG.md` entry.** A semantic change is anything that alters what a consuming course should produce (a rule, a scale, a template field) — as opposed to typo fixes.
- When a course repo adopts a shared change, its commit message says so (e.g. `adopt Standards: /10 exercise scale`).
- Course-specific rules never migrate here. If a rule only makes sense for one course, it belongs in that course's local layer.

# Curriculum data: era detection and parsing

How to read the Ontario curriculum data for a course code and decide the
era branch. `scaffold_course.py init` applies these rules; read this to confirm its
findings with the teacher (workflow steps 1 and 2).

## Two files, two roles

For a course code `<CODE>`:

- `GLA_ROOT/Curriculum/docs/knowledge-graph/courses/<CODE>.md`
  — the knowledge-graph file. **Always present.** Carries the era metadata in its
  YAML frontmatter and a human-readable rendering of the strands.
- `GLA_ROOT/Curriculum/data/curriculum/<CODE>.json`
  — the structured expectations. **Present only for modern (post-2008) courses**
  (the web-native `cms` tier). A 2008 Computer Studies course such as ICS3U or
  ICS4U has **no JSON at all**.

The era is **not** encoded inside the JSON — every JSON in the dataset is the
modern schema. Era lives in the `.md` frontmatter. So the presence or absence of
the JSON is itself the primary era signal.

## Era detection

1. Read the `.md` frontmatter. The authoritative fields are `tier` (`cms` =
   web-native/modern, `pdf` = scanned/2008-era) and `year_issued` (the precise
   year, e.g. `"2008"` or `"2023"`).
2. Cross-check with file availability:
   - **Modern branch** — JSON exists and `tier: cms`. Specific expectations carry
     their own dotted codes (`A1.1`, `A1.2`, ...). Use the Ministry's numbering
     directly; there is **no local numbering layer** and no risk of local/Ministry
     drift.
   - **2008 branch** — no JSON, `tier: pdf`. Overall expectations are numbered
     (`A1`, `A2`, ...) but **specific expectations are unnumbered bullets** and
     overall expectations have no titles. The course must **declare a local
     canonical numbering convention** in the coverage-map preamble (state it
     explicitly, e.g. "specific expectations numbered A1.1, A1.2... in document
     order; this is a local convention, the Ministry leaves them unnumbered").
3. Confirm the detected era with the user before building the coverage map.

## Reading strands and expectations

**Modern (JSON):** top-level `strands[]`. Each strand has `index` ("A"), `title`,
`describer`, and `overall_expectations[]`. Each overall expectation has `index`
("A1"), `title`, `text`, and `specific_expectations[]`; each specific expectation
has `index` ("A1.1"), `text`, and `elaborations[]`. Pull expectation text from
here verbatim for the coverage map's abridged-expectation column.

**2008 (`.md` only):** parse the strand sections from the markdown. Each `### A.
<title>` heading, an italic describer line, then `**A1** <text>` bold lines for
overall expectations and `-` bullets for the (unnumbered) specific expectations.
Assign your local numbering to the bullets in document order.

## Cross-cutting strand

A cross-cutting strand is one the Ministry designates "throughout this course"
rather than "by the end of this course." Detect it, do not assume it from the era:

- **Modern:** test whether a strand's (or overall expectation's) `describer`
  starts with **"Throughout this course"** (vs "By the end of this course").
- **2008:** the same distinction appears as the strand's italic describer line.

A cross-cutting strand exists per specific curriculum, independent of era. ICD2O
(2023) has one (Strand A). TAS1O (2024, also modern) has **none** — its Strand A
uses "By the end of this course." ICS3U/ICS4U (2008) have none. When a
cross-cutting strand is present, the coverage map uses the anchored + woven model
(see `scaffold.md`); when absent, every strand maps to contiguous units the
normal way.

## What to hand to the coverage-map step

- The era and numbering decision (Ministry-native vs local convention).
- The full strand → overall → specific expectation tree, with each specific
  expectation's code and abridged text.
- Which strand (if any) is cross-cutting, and its expectation list.
- The authoritative source path, to cite in the coverage-map preamble and the
  course-layer `Style_Guide.md` identity section.

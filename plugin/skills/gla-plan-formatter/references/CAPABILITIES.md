# gla-plan-formatter v1: capability audit (2026-09-06)

What the skill does today, verified by rendering its two bundled examples locally (`build_plan.py`, LibreOffice 24, PyMuPDF). The docx it produces is byte-identical to the shipped `Lesson_Plan_Template.docx` and `Unit_Plan_Template.docx`, so the builder is the design, not the templates.

## Document types

Two. Type is inferred from the source; the skill asks only when the source is ambiguous.

| Type | Structure rendered | Example |
|---|---|---|
| `lesson` | course/grade banner with gold badge, title block, 4-up meta grid (Course Code, Unit, Lesson, Duration), Curriculum Expectations (overall, specific, four achievement-category checkboxes), Learning Goals and Success Criteria (two columns), Materials (teacher and student, optional extra blocks), Lesson Sequence (numbered blush phase bars, each with a two-column teacher-actions / assessment table), Teacher Notes and Differentiation (three named columns), optional Google Classroom connections | CLN4U "What Is Law?", 4 pages |
| `unit` | title block with subtitle, overview grid (Course, Grade, Unit Title, Unit #, Number of Days, Culminating Task Due, plus full-width Core Texts and Strands Addressed), then an ordered list of sections: STEP banners, plain headings, tall maroon left-label rows (Big Idea, Overall Expectations, Learning Goals and so on), the three-column Assessed / Covered expectations table, four-column achievement chart, six-column lesson sequence, "Variety of Learning Experiences" checklist groups, post-unit reflection table | ENG3U "The Power of Storytelling", 9 pages |

## Content model

JSON spec per type (`references/lesson_schema.md`, `references/unit_schema.md`). Shared block vocabulary for any cell or list: `para` (with bold, italic, colour, size), `label` (bold maroon sub-label), `quote` (italic maroon), `bullets`, `numbered` (with start), `checks` (checkbox list). A bare string is a paragraph. Inline bold inside text is not parsed; emphasis is per block.

## What it asks, infers, and refuses

- Asks: nothing, unless lesson-vs-unit is ambiguous.
- Infers: the document type; the mapping of source sections to template sections (done privately, never shown).
- Refuses to invent: any required content the source lacks stays blank in the document and is listed under "Gaps: not filled" in the review file. Optional sections absent from the source are omitted. No marker text is ever written into a document.
- Preserves the teacher's wording, names, and curriculum codes; light cleanup only. Mandates curly quotes, en dashes in ranges, and em dashes for breaks in the JSON (conflicts with the GLA prose rule of no em dashes).

## Output and delivery

`.docx` always; `.pdf` via `--pdf`. Verification step renders page images with `pdftoppm` and eyeballs crest, colours, sections, cells, markers. Delivery copies both files to the outputs directory and calls `present_files`, docx first.

## Design language (as implemented)

- Arial 10.5pt body, 1.08 line spacing. Checkbox glyphs in DejaVu Sans 12pt (maroon when checked, grey when not).
- Palette: maroon `76202E`, dark maroon `5A1622`, gold `C19A2E`, deep gold `8A6B12`, blush `F3E8EA`, gold tint `FAEFD3`, ink `262626`, rule `D8C5C8`, footer grey `7A5C61`. `CREAM` is declared and unused.
- Letter page, margins 0.8" left and right, 0.6" top, 0.65" bottom; header distance 0.35".
- Running header: crest (0.42" tall) and school name in one paragraph with a maroon rule. Footer: centred grey breadcrumb under a gold rule.
- Section bars are shaded paragraphs (maroon, white uppercase text, gold underline). Phase bars are blush with a maroon underline. Tables are fixed-layout with maroon header rows, blush label cells, hairline rule borders, 110/55 dxa cell padding, indented 110 dxa to align with the bars.

## Gaps and defects found

1. **PDF export only works in the claude.ai sandbox.** `to_pdf` shells out to `/mnt/skills/public/docx/scripts/office/soffice.py`, which does not exist locally, and swallows stderr. Locally `--pdf` fails.
2. **Verification and input reading assume sandbox tools**: `pdftoppm` and `extract-text` are not on this Mac (PyMuPDF and python-docx are).
3. **Silent crest fallback.** If `assets/GLA_Logo.jpg` is missing the document builds without a crest and without a warning.
4. **`design_spec.md` promises a "Toronto • Ajax" tag** in the header that the code never renders. Decision: it must not appear; the spec line goes.
5. **Header sits inside the top margin.** With a 0.6" top margin and a 0.42" crest, Word and LibreOffice grow the margin themselves, so where the body starts depends on the renderer. In the local render the body starts about 1.1" down regardless of the declared 0.6".
6. **Bars can orphan at a page foot.** No `keepNext` on section or phase bars; no `cantSplit` on rows. The outline renderer solved both.
7. **Bullet hanging indent is off**: left 0.27" with first-line -0.16" leaves wrapped lines 0.11" to the right of the text after the marker.
8. **Long tables do not repeat their header row** on page 2+ (the unit's expectations and lesson-sequence tables span pages).
9. **Palette differs from the GLA Brand Pack** (`872634` maroon, `DABE81` gold, `272727` ink). Decision: adopt the brand palette with derived tints.
10. **Em dashes are mandated** in the JSON typography guidance, against the house prose rule.
11. **No interview.** Gaps are marked, never negotiated. Nothing is drafted.
12. **No Markdown input path.** Everything goes through hand-written JSON.
13. **Two types only**: course outlines, long-range plans, and weekly plans have no home; the outline renderer lives outside the skill with duplicated primitives.
14. **Version is not recorded anywhere** in the skill or the output.

## What v2 keeps

The JSON-spec-then-build discipline ("never hand-style the docx"), the block vocabulary, the honest-gap marker, voice preservation, the lesson and unit layouts as the base for reconciliation against the user's samples, and the verify-before-deliver step.

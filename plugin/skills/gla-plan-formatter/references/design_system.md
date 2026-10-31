# GLA print design system

The house style for every document the formatter produces: lesson plan, unit plan, course outline, short and long term plan, weekly lesson plan, exam cover. One identity, six layouts. It is implemented once, in `scripts/gla_docx.py`, and parameterised once, in `assets/tokens.json`. Builders in `scripts/doctypes/` compose furniture; they never declare a colour, size, or margin. If a future change would make two document types look like they came from different schools, it is wrong.

## Where values live

`assets/tokens.json` has six blocks: `palette`, `type`, `page`, `spacing`, `rules` (border weights in eighths of a point), and `strings`. `gla_docx.py` reads it at import and binds the old constant names (`MAROON`, `GOLD`, `BLUSH`, ...) so renderer code reads naturally. Point `GLA_TOKENS` at another file, or pass `--tokens`, to render the same spec under a different palette for comparison. A palette change is an edit to the `palette` block, a run of `verify.py --update`, and a version bump.

## Palette

Source: the GLA Brand Pack (`Teaching/Standards/brand/GLA_Brand_Pack.pdf`, page 4). One maroon, one gold and one gray scale. Every maroon is 872634 and every gold is DABE81. A pale fill of either is a tint against white, computed per channel as `tint(c, p) = round(255 - (255 - c) * p)`, where `p` is the share of the base colour. Every gray comes from one scale built the same way on ink (272727), with `p` in {1.00, 0.75, 0.55, 0.40, 0.25, 0.12, 0.06, 0.03}: 272727, 5D5D5D, 888888, A9A9A9, C9C9C9, E5E5E5, F2F2F2, F9F9F9. No other grays exist.

| Token | Hex | Derivation | Used for |
|---|---|---|---|
| maroon | 872634 | brand (Pantone 202 C) | section bars, the course strip, the document title and subtitle, the badge text, the text of table headers and labels, the running header name and rule, bullet markers |
| gold | DABE81 | brand (Pantone 14-0935 TPG) | accents only: the grade badge fill, rules under titles and bars, the footer rule, the context line on the course strip |
| gold_text | 8C6D2A | contrast exception | gold text that must read on a light fill: the unit plan's "Covered" header and links. DABE81 on white is 1.8:1, too pale for text, so this darker gold is the one colour outside the rule. It reads 4.8:1 on white and 4.2:1 on gold_tint. |
| gold_tint | F6EFE0 | tint(gold, 0.25) | gold-accent cells |
| blush | F3E9EB | tint(maroon, 0.10) | table header rows, label cells, sub bars, Total rows |
| cream | F9F5EC | tint(gold, 0.15) | reserved |
| ink | 272727 | gray 1.00 (Direwolf) | body text |
| footer_gray | 5D5D5D | gray 0.75 | footer breadcrumb, signature captions |
| muted | 888888 | gray 0.55 | unchecked category labels, placeholder text |
| muted_box | A9A9A9 | gray 0.40 | unchecked checkbox glyphs |
| rule | C9C9C9 | gray 0.25 | hairline table borders |
| band_white | F9F9F9 | gray 0.03 | reserved |
| white | FFFFFF | white | text on maroon; the page |
| bullet_marker | 872634 | maroon | bullet markers |

Gold is never a background for body text. The badge carries maroon text on gold (4.9:1).

## Type

Arial throughout (available in Word, Google Docs, and LibreOffice without embedding). Body 10.5pt at 1.08 line spacing; small 9.5pt for dense tables and metadata labels; micro 8.5pt for the footer and signature captions. Document title 26pt bold maroon; subtitle 15pt bold maroon; section bars 12pt bold white uppercase; sub bars 11pt bold maroon; plain headings 12.5pt bold maroon uppercase; the header school name 12.5pt bold maroon. Checkbox glyphs (☑ ☐) are set in DejaVu Sans at 12pt, maroon when checked and grey when not; Word substitutes a symbol font if DejaVu Sans is absent, which is acceptable. Inline `**bold**` and `*italic*` are honoured everywhere text is rendered.

Prose rule: no em dashes in anything the skill writes (a colon, comma, or parentheses instead); en dashes stay in numeric ranges. Teacher-supplied text is preserved as written.

## Page

US Letter. Margins: left and right 0.8", top 1.2", bottom 0.7". Header distance 0.4", footer distance 0.35". The content width is therefore 6.9". The top margin is deliberately larger than the running header so the body start does not depend on the renderer.

## Running header and footer

Header on every page: a two-cell table on a shared centre line, the crest (0.42" tall, `assets/GLA_Logo.jpg`, cropped to its content) in a 0.78" column with no side padding and the school name beside it, with a maroon rule beneath. Nothing else appears in the header. If the crest file is missing the build continues and prints a warning on stderr. Footer on every page: a centred grey breadcrumb under a gold hairline, for example `Gibraltar Leadership Academy | CLN4U | Lesson 1`. The generator version is written to the document's core properties (comments field), never onto the page.

## Masthead

Every document opens the same way, through one function (`masthead` in `gla_docx.py`): the maroon course strip (course line in white, a context line in gold beneath it) with the gold grade badge on the right, then the title block (26pt title, gold rule, 15pt subtitle). Builders supply only their course line and context line; the badge is derived from the course code by one rule (`derive_badge`: grade from the fourth character, pathway from the fifth); a badge supplied by a spec is normalised through the same rule (`normalize_badge`), so "University Preparation" and "University Prep" render identically. Per type the context line is: lesson, unit and lesson number; weekly plan, unit and week; unit plan, unit title and number; course outline, department and course type; short and long term plan, semester and teacher; exam cover, the division.

## Bars

Section bar: maroon fill, white bold uppercase text, gold rule beneath (2pt), at least 18pt tall, text inset to the shared guide. Sub bar (phase, day, H3, lettered unit heading): blush fill, maroon bold text, maroon hairline beneath, at least 15pt tall. No other heading furniture exists; `step_banner` and `plain_heading` remain in the module for compatibility but no builder uses them.

Two constructions exist and the choice is deliberate:

- A **paragraph bar** (`section_bar`, `sub_bar`) carries `keepNext` and `keepLines`. Use it when a run of paragraphs or a table with short rows follows: outlines, plan tables, the Lesson Sequence heading. LibreOffice keeps the bar with the first line that follows.
- A **fused bar** (`make_table(..., bar=text)`) is the table's own first row: merged, filled, repeating as a header row, and unable to split. Use it whenever a bar introduces a table, in every type: the spacing between bar and table is then the cell padding and is identical everywhere. The unit plan's STEP headings, the plans' two tables, the exam cover's categories and instructions, and every block table in the lesson and weekly plan are fused. LibreOffice cannot keep a paragraph with a following row taller than the space left, so a paragraph bar there would push whole tables to the next page and leave half-empty pages. The fused bar stays with its content, and if the row continues on a second page the bar repeats at the top.

## The shared guide

Bar text, body paragraphs, bullet markers, and table cell text all start 110 dxa (0.076") in from the content edge. That value is the table cell padding, so it is derived once (`TEXT_INSET`), and tables are indented by the same amount (`tblInd`) so their borders sit on the content edge and their text on the guide.

## Tables

Fixed layout with explicit column widths summing to 6.9" (then the table is also pinned to 100% so viewers that ignore the grid still fill the width). Cell padding 55 dxa top and bottom, 110 left and right; the metadata grid uses 42 top and bottom. Hairline `rule` borders on every cell. Header rows and label cells are the same thing: blush fill, maroon bold text. Header rows repeat on later pages, never split, and carry the same maroon hairline beneath them as a sub bar (applied by `add_row(header=True)`, so no builder draws it itself); a label column beside content rows does not. Maroon fills belong to section bars only, so a table never stacks a second maroon band under the bar that introduces it. The one accent exception is the unit plan's "Covered" header cell in gold tint with gold_text, which encodes meaning. A body row whose first cell starts with "Total" is bold on blush. Alignment is decided per column: a non-first column is centred only when every body cell is short (14 characters or fewer), so one long value never breaks a column's alignment. Generic tables (outlines, plans) derive column widths from content: every column gets at least its longest word, the remainder is shared by content length. Fixed-spec tables (lesson meta grid, unit lesson sequence) keep their hand-chosen widths.

Row splitting: rows in generic tables, metadata grids, and plan tables cannot split across pages. Rows holding block content (phase tables, labeled rows) may split, because a row taller than a page would otherwise overflow.

## Lists

Bullets and numbered items use a true hanging indent of 0.25" with an explicit tab stop, so wrapped lines align under the text, not under the marker. Markers are maroon. Inside cells the indent starts at the cell edge; at document level it starts at the shared guide. Checklists use the checkbox glyphs with a 0.24" hang.

## Unit plan vocabulary

The unit plan uses no furniture of its own: STEP headings are section bars fused to the table beneath, the backward-design blocks (A. Big Idea, B. Overall Expectations, Learning Goals, Assessment Tasks, and so on) are blush label rows sharing one table per step, and the lettered sub-headings are sub bars.

## Page-break rules

Titles, bars, headings, and labels keep with what follows. A body paragraph that ends in a colon keeps with the list or table it introduces. Signature rows keep together. Header rows repeat. See "Bars" for the one place where keepNext is replaced by structure.

## Preview

Judge layout in LibreOffice or Word. macOS QuickLook shrinks fixed tables to their content and drops paragraph shading, so a QuickLook thumbnail is not evidence of a defect. `build_plan.py --png` renders pages through LibreOffice and PyMuPDF (or pdftoppm) for inspection.

## The screen design system

GLA also has an on-screen system for slide decks and the teacher calendar: `Teaching/Standards/decks/Slide_Deck_Instructions.md` and `Slide_Deck_Template.html` (Public Sans and IBM Plex Mono, GLASS tokens, byte-protected machinery) and the `semester` skill. It is separate from this print system and this skill does not touch it. The Google Docs handouts produced by `semester` use Roboto because Google Docs resolves it natively; that is a product constraint, not a second print style.

# Slide Deck Instructions

These are the authoritative instructions for creating any GLA course slide deck. One deck exists per `teach` day. Styling and technical scaffolding come from `Slide_Deck_Template.html` (GLASS design system); these instructions govern content and structure. `{{COURSE_CODE}}` below means the consuming course's code (e.g., ICS3U, ICS4U).

You will create a complete HTML slideshow presentation based on the day's lesson document. The presentation is optimized for in-person delivery with maximum visual impact and minimal text.

## Your task

**Phase 1: Planning.** Analyze the lesson and produce a proposed structure before writing any HTML:

- Identify the main chapters/sections you will create
- List the key points that will become individual slides under each chapter
- Identify the interactive exercises you plan to include
- Estimate the total number of slides (target: 15–25)
- Verify that the first non-title slide includes learning goals and curriculum expectations

**Phase 2: Generation.** Write the slides as a fragment file and assemble the deck with `gla deck DECK.html --from SLIDES.html`. The fragment holds only slide content: `<!-- chapter: Name -->` markers, `<!-- auto: title -->` and `<!-- auto: goals -->` (built from the lesson's title, slot, learning goals and expectation codes), the `<section class="slide">` elements, and optional deck-specific `<style>` and `<script>`. The assembler supplies the token blocks, the machinery, the sidebar and its slide indices, the counter, and the theme attribute, then checks the deck. To change an existing deck, edit its slides and run `gla deck DECK.html --rebuild`; `--extract` prints a deck's fragment source and `--check` reports problems without writing.

## Content requirements

1. **First non-title slide** MUST contain the learning goals (primary focus) and curriculum expectation codes (secondary focus). Text limits don't apply to this slide.
2. **Extract all key content**: every key lesson, concept, and important point from the lesson document appears in the deck.
3. **Minimal text per slide**: key numbers, single impactful phrases, short labels. No paragraphs, no long sentences. Code samples (programming courses): **6 lines maximum** per slide; split longer examples across slides.
4. **Visual-first**: each slide emphasizes diagrams, charts, icons, illustrations, images, or large impactful numbers. Build diagrams and charts in CSS/SVG with the template's tokens. A photograph, micrograph, map or primary-source image is a file in an `images/` folder beside the deck, shown as `<img src="images/<file>" alt="<what it shows>">` with a line under it that starts `Credit:` and gives the creator, source and licence (Style Guide Core §4). Never link an image from another site.
5. **One major point per slide.** Split rather than combine.
6. **Self-contained presentation**: no "up next" or "coming next week" slides; no references to other presentations, tests, units, or assignments.
7. **Interactive exercises**: include 2–3 short, simple interactive checkpoints (predict-the-output, click-to-reveal, quick poll, trace-this-code, label-the-diagram, which-source-says-this) where they aid engagement.
8. **Time and slide limits**: the deck carries **~25–35 minutes** of the ~50-minute lesson (the live demo and discussion happen outside the deck). The slide range is course.yaml's `deck_slides`, 15–25 by default.
9. **Audience attention**: assume a limited attention span. Keep it engaging and concise.
10. All Style Guide Core content rules apply (Islamic names, no emojis, no music/dating/LEGO content, no food or drink in an activity, standalone scenarios), plus the course layer's rules.

## Visual design requirements

1. **Typography**: small text (slide numbers, navigation) 18–24px; all text highly readable from the back of a classroom.
2. **Layout**: clean and minimal; generous white space (minimum 40px padding on all sides); clear visual hierarchy; centered content when appropriate.
3. **Visual elements**: use CSS to build simple diagrams, charts, and visual representations; strong visual impact per slide; consistent styling for similar elements.
4. **Theme**: use the design tokens defined in `Slide_Deck_Template.html` (Public Sans + IBM Plex Mono). The template carries two token sets, and the course's `course.yaml` key `deck_theme` picks one:
   - `glass` (the default, also used when the key is absent): marine primary, coral secondary accents, cool neutrals. The root element stays `<html lang="en">` with no theme attribute.
   - `gla`: the GLA print palette, maroon `#872634` primary, gold `#dabe81` secondary, grays from `#272727`. Set the attribute on the root element: `<html lang="en" data-deck-theme="gla">`.

   Do not invent new palettes. Under `gla`, `--secondary-500` is gold at 1.8:1 on white: use it for fills and borders, and use `--tile-warm-fg` or `--accent` for text.

## Technical requirements

1. **Self-contained file**: one HTML file with all CSS and JavaScript embedded; its images are the only files beside it (`images/`). External dependencies (e.g., three.js) only when they genuinely serve a purpose.
2. **Keyboard navigation**: left/right arrow keys move between slides.
3. **Slide counter**: current/total in the top-right corner, exact format: `3/12`.
4. **Chapter navigation**: left sidebar listing all major sections; chapter names clickable to jump; current chapter highlighted, updating automatically as slides advance.
5. **Transitions**: smooth CSS transitions between slides (fade or slide).
6. **Fullscreen support**: presentation works well in fullscreen for in-person delivery.
7. **Browser compatibility**: opens directly in any modern browser.
8. **Template machinery is byte-protected**: the token blocks for both themes (GLASS: `:root` / `[data-theme="dark"]`; GLA: `:root[data-deck-theme="gla"]` / `:root[data-deck-theme="gla"][data-theme="dark"]`) and the blocks marked `TEMPLATE MACHINERY (do not modify)` (layout CSS for `#sidebar`/`#counter`/`#stage`/`.slide` and the bottom `<script>` engine) are byte-identical to the template; `build_deck.py` writes them on every assembly, so never edit them inside a deck (a template change reaches every deck on its next `--rebuild`). Only the root element's `data-deck-theme` attribute, sidebar chapter entries, the counter's initial text, and `<section class="slide">` content change per deck.

## Planning output format

Present the plan as:

```
Chapter 1: <name>
  - Slide 1: Title slide
  - Slide 2: Learning goals and curriculum expectations
  - Slide 3: <point> with <visual>
Chapter 2: <name>
  - Slide 4: ...
  ...
Interactive Exercises:
  - Exercise 1: <description>
Total Estimated Slides: <n> (within 15-25)
Learning Goals Slide: Confirmed as Slide 2
```

## Companion teacher guide

Every deck gets a companion prep document: `D<n>_Slides_<Topic>_GUIDE.md`, in the same folder as the deck. The slides rightly carry only a few words per slide; the guide gives the teacher the full context to review beforehand and to glance at during delivery:

- Per slide (or slide range): what the slide is doing pedagogically, the talking points behind its few words, and the intended transition to the next slide.
- For each interactive checkpoint: the expected answers, the common wrong answers worth surfacing, and how long to let it run.
- Timing waypoints ("by slide 9 you should be ~15 minutes in").
- Anything the presenter must set up or have open before this slide arrives (demo files, sketches, board diagrams).

The guide is teacher-only (never distributed), and is written from the deck plus the lesson document; it must not introduce content that contradicts either. **Status:** in force. author-week writes the guide with its deck (and has a guides-only mode for decks without one), and `check_course.py` warns when a deck has no guide (`deck-guide`) or when a guide's `**Deck:** N slides` line or its `**Slide n**` paragraphs do not match the deck (`guide-slides`). Every deck in ICD2O, ICS3U and ICS4U has its guide.

## File conventions

- Filename: `D<n>_Slides_<Topic>.html`, matching the lesson's topic string.
- Optional 3D deck: `D<n>_Slides_<Topic>_3D.html`, built from `D<n>_Slides_<Topic>_3D.yaml` by a course's own deck3d tool, with its own `_3D_GUIDE.md`. It sits beside the main deck and never replaces it; its YAML names the same slot and the lesson's expectations, and its guide's slide count matches the YAML's `slides` list.
- Title slide shows the topic, "{{COURSE_CODE}} · Gibraltar Leadership Academy", and the slot ID in small text.
- The sidebar deck label reads "{{COURSE_CODE}} · Deck".
- No dates anywhere in the deck.

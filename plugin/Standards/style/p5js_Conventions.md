# GLA p5.js Conventions

Applies to every p5.js example, starter, brief solution sketch, and key in GLA's p5.js-based courses (ICD2O). The course layer defines *which* features are available at each slot; this file defines *how* p5.js/JavaScript is written whenever it appears.

- p5.js **global mode**, single `sketch.js` per sketch. The standard project is two files, `index.html` (loads a locally vendored `p5.min.js`) + `sketch.js`, with no build system, and `sketch.js` runs unmodified in the p5.js web editor.
- `let` for values that change, `const` for values that don't; never `var`. Variables/functions `lowerCamelCase`; deliberate constants `UPPER_SNAKE_CASE`.
- 2-space indentation; semicolons always.
- Sketch structure, top to bottom: constants and top-level variables → `setup()` → `draw()` → event functions (`mousePressed()`, `keyPressed()`, …) → custom functions.
- Every sketch begins with a short comment header (title + one-line purpose) and calls `describe()` in `setup()`. The accessibility habit is part of house style, not an add-on.
- Comments explain sections and non-obvious logic, not every line.
- Repeated or meaningful numbers get named variables/constants; canvas-relative positioning (`width`, `height`) is preferred over hard-coded coordinates where it doesn't obscure the lesson.
- **Every sketch must run as written**: no pseudocode presented as JavaScript. Screenshots or described visual outcomes in materials must come from actually running the sketch.
- Only use language/library features already taught by that slot (check the course layer's feature-availability list).
- Editor-agnostic: nothing may depend on a specific IDE feature; everything must work in both the WebStorm template project and the p5.js web editor.

# GLA Java Conventions

Applies to every Java example, starter, key, and solution in GLA's Java-based courses (ICS3U, ICS4U). The course layer defines *which* features are available at each slot; this file defines *how* Java is written whenever it appears.

- Java 17+ compatible, console only (no GUI frameworks) unless the course layer says otherwise.
- Class names `UpperCamelCase`, methods/variables `lowerCamelCase`, constants `UPPER_SNAKE_CASE`.
- 4-space indentation.
- Comments explain sections and non-obvious logic — not every line.
- **Every code sample must compile (`javac`)** — no pseudocode presented as Java. Predicted outputs shown in materials must be verified by actually running the code.
- Only use language features already taught by that slot (check the unit overview's concept order and the course layer's feature-availability list).
- IDE-agnostic: nothing may depend on a specific IDE (IntelliJ IDEA and VS Code are both in use). No build tools (Maven/Gradle) unless a course layer introduces them.
- Sample console transcripts use realistic input values and show prompts exactly as the program prints them.

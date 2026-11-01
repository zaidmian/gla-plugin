# GLA Course Outline: Canonical Structure

This is the house structure for a Gibraltar Leadership Academy course outline. It is the integrated
form drawn from GLA's own full outlines (the ICS3U and BBB4M samples), the bootstrap
`Course_Outline.md` skeleton, and the `gla-plan-formatter` design language. Every outline in this
folder follows it. `build_outline.py` parses the conventions marked **[parser]** below to render the
GLA-branded document, so keep those exact.

## Writing rules
- Prose style: no em dashes (use commas, parentheses, or a colon), no emojis. Numeric ranges use a
  hyphen (80-100%). Vary sentence length.
- Assessment must match the 2026 Growing Success model and the course's row in `ASSESSMENT_MATRIX.md`.
  The shared authority is `Teaching/Standards/assessment/growing-success-summary.md`.
- Curriculum content (description, strands, overall expectations, prerequisite, ministry document)
  comes verbatim (lightly trimmed) from the course's GLASS file:
  `GLA_ROOT/Curriculum/docs/knowledge-graph/courses/<CODE>.md`. Do not
  invent expectations.
- Credit value is 1.0 and total instructional time is 110 hours for every course here.

## Parser conventions [parser]
- Title line: a single H1 `# <Course Title>, Grade <n> (<CODE>)`.
- The metadata block is a two-column Markdown table immediately under the H1 (keys in column 1).
- Top-level sections are H2 (`## Section Name`) rendered as maroon section bars.
- Subsections are H3 (`### Name`) rendered as blush sub-bars.
- Tables use standard Markdown pipes. Bullet lists use `- `. Bold uses `**...**`.
- A horizontal rule `---` separates the metadata block from the body and is otherwise avoided.

---

## Section order (H2 sections, in this order)

1. **Metadata block** (table under the H1). Rows, in order:
   `Course Title` · `Course Code` · `Course Type` · `Grade` · `Credit Value` (1.0) ·
   `Prerequisite` · `Corequisite` (None) · `Department` · `Curriculum Document` (ministry doc + year) ·
   `Developed By` · `Date Developed` · `Revised By` · `Date Revised`.

2. **Course Description**: the GLASS course description, one to two paragraphs.

3. **Overall Curriculum Expectations**: grouped by strand (H3 per strand). Under each strand, the
   overall expectations as a bulleted list, using the course's own expectation codes (A1, A2, ...).

4. **Considerations for Program Planning**: the nine GLA considerations, each a short paragraph,
   tailored to the subject: Student Well-Being; Equity, Diversity and Human Rights; Support for All
   Learners; Experiential Learning; Instructional Approaches; Education and Career/Life Planning;
   Indigenous Knowledge and Perspectives; Health and Safety; Roles and Responsibilities.

5. **Units of Study and Time Allocation**: an intro line stating six-ish units totaling 110 hours,
   then a table `| Unit | Title | Hours |` ending in a bold `Total ... 110` row. Derive a sensible
   4-6 unit sequence from the strands and expectations. For skills-based subjects (English, French)
   whose strands are interwoven, units are thematic and note that all strands run through each.

6. **Unit Descriptions**: H3 per unit (`### Unit N: Title (H hours)`), a short paragraph each, ending
   with a `Curriculum Connections:` line naming the expectation codes the unit carries.

7. **Teaching and Learning Strategies**: four H3 groups: Teacher-Directed, Student-Centered,
   Technology-Enhanced, Differentiation, each a bulleted list tailored to the subject.

8. **Assessment and Evaluation Strategies**: H3 `Growing Success Framework` (a short paragraph naming
   the 2026 policy), then H3 `Assessment FOR Learning`, `Assessment AS Learning`, `Assessment OF
   Learning` (purpose, methods, graded/not graded), then H3 `Assessment Tools` (student products,
   observations, conversations).

9. **Achievement Chart Categories**: a table `| Category | Weight | Description |` for the four
   categories, named as this course's own curriculum document names them (Computer Studies says
   "Thinking", Science says "Thinking and Investigation").
   Default weighting K/U 25% · Thinking 30% · Communication 20% · Application 25% unless
   the subject convention differs (state it). Follow with the four achievement levels and the note
   that Level 3 is the provincial standard.

10. **Evaluation and Reporting**: the 2026 final-grade model. H3 `Final Grade Calculation` with a
    table `| Component | Weight | Description |` showing the three buckets for this grade band
    (Classroom Work 65%; Final Evaluation 20% or 25%; Attendance and Participation 15% or 10%). Then
    H3 `Final Evaluation` breaking that bucket into the written exam and/or culminating task from the
    matrix, and H3 `Attendance and Participation` with the unexcused-absence scale table. State that a
    credit is granted at a final mark of 50% or higher.

11. **Learning Skills and Work Habits**: the six skills, the E/G/S/N scale, and the note that they
    are reported separately and are not part of the percentage grade.

12. **Course Policies**: H3 `Late and Missed Assignments` and H3 `Academic Honesty`.

13. **Support for Diverse Learners**: H3 `Students with Special Education Needs` (IEP accommodations
    vs modifications, the IEP box) and H3 `English Language Learners (ESL/ELD)`.

14. **Program Planning in <Subject>**: subject-specific H3 subsections drawn from the ministry
    program-planning guidance for the subject, for example: Literacy, Numeracy and Inquiry/Research
    Skills; The Role of Technology (ICT); Career Education; Cooperative Education and Experiential
    Learning; The Ontario Skills Passport and Essential Skills; Health and Safety; Ethics and
    Antidiscrimination Education.

15. **Required Materials and Resources**: H3 `Required Materials`, H3 `Textbooks and Resources`, H3
    `Online Resources`, tailored to the subject.

16. **Classroom Expectations**: a bulleted list.

17. **Accessibility**: a short paragraph (WCAG-aligned digital resources, alternative formats on
    request).

18. **Islamic Perspective**: the GLA statement that the Islamic perspective may be referenced where
    applicable and appropriate, with two to four subject-relevant bullets.

19. **Acknowledgement**: the sign-off paragraph and the student/parent signature lines.

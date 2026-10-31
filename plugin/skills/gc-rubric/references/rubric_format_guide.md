# Google Classroom Rubric Format Guide

Authoritative reference for CSV structure, point allocation, and descriptor patterns.

## Table of Contents

1. [Ontario Assessment Framework](#ontario-assessment-framework)
2. [CSV Format Specification](#csv-format-specification)
3. [Point Allocation Tables](#point-allocation-tables)
4. [Descriptor Writing Guide](#descriptor-writing-guide)
5. [Complete CSV Example](#complete-csv-example)
6. [Category Descriptions by Subject Area](#category-descriptions-by-subject-area)
7. [Common Mistakes](#common-mistakes)

---

## Ontario Assessment Framework

### Five-Level Achievement Scale

| Level             | Percentage | Qualifier                        | Meaning                              |
|-------------------|-----------|----------------------------------|--------------------------------------|
| **Below Level 1** | 0-49%     | **Not Yet Demonstrated**         | Needs intensive support              |
| **Level 1**       | 50-59%    | **Limited** effectiveness        | Requires significant improvement     |
| **Level 2**       | 60-69%    | **Some** effectiveness           | Approaching standard, needs support  |
| **Level 3**       | 70-79%    | **Considerable** effectiveness   | Provincial standard -- ready for next steps |
| **Level 4**       | 80-100%   | **High degree of** effectiveness | Surpasses standard                   |

Level 3 is always the provincial standard. Rubric descriptors should reflect this: Level 3
is "good, solid work" not "mediocre."

### Four Categories of Knowledge and Skills

These are mandated by Ontario for all courses. Every rubric must assess all four, though
they may be combined in very small rubrics.

**1. Knowledge and Understanding**
- Knowledge of content (facts, terminology, concepts, definitions)
- Understanding of content (processes, relationships, how things work)

**2. Thinking** (Science calls this category **Thinking and Investigation**; Computer Studies
and every other subject call it **Thinking**. Use the name from the course's own curriculum
document, and see `growing_success_achievement_chart.md`.)
- Planning skills (identifying problems, gathering info, selecting strategies). Science reads
  this criterion as *initiating and planning*, which is where its longer category name comes from.
- Processing skills (analyzing, carrying out plans, implementing)
- Critical/creative thinking (problem solving, evaluating, designing)

**3. Communication**
- Expression and organization (clarity, logical flow, structure)
- Communication for audiences/purposes (appropriate tone, format)
- Use of conventions (proper terminology, standards, formatting rules)

**4. Application**
- Application in familiar contexts (using skills in expected ways)
- Transfer to new contexts (adapting skills to unfamiliar situations)
- Making connections (real-world links, cross-curricular ties)

---

## CSV Format Specification

### Exact Structure

Every Google Classroom rubric CSV follows this exact structure. Do not deviate.

**Row 1 (warning header):**
```
"It is recommended that you do not edit rubrics in spreadsheet format","","","","","",""
```

**Row 2 (version header):**
```
"v1.0-s","","","","","",""
```

**For each criterion, exactly 5 rows:**

**Row A -- Criterion Title:**
```
"[Category] - [Specific Criterion Name]","","","","","",""
```

**Row B -- Criterion Description:**
```
"[1-2 sentence description of what is being assessed]","","","","","",""
```

**Row C -- Point Values (Level 4 through Below Level 1, left to right):**
```
"","[L4 points]","[L3 points]","[L2 points]","[L1 points]","[Below L1 points]",""
```

**Row D -- Level Titles (exact strings, do not modify):**
```
"","High Degree of Effectiveness (Level 4)","Considerable Effectiveness (Level 3)","Some Effectiveness (Level 2)","Limited Effectiveness (Level 1)","Not Yet Demonstrated",""
```

**Row E -- Level Descriptors:**
```
"","[L4 descriptor]","[L3 descriptor]","[L2 descriptor]","[L1 descriptor]","[Below L1 descriptor]",""
```

### Column Rules

- Every row has exactly 7 columns separated by commas
- Every cell value is enclosed in double quotes
- Empty cells are `""`
- The 7th column is always empty: `,""`
- If a cell value itself contains a double quote character, escape it by doubling: `""`
  inside the quoted string. Example: `"She said ""hello"" to the class"`
- Commas inside quoted values are safe and do not need escaping
- No BOM (byte order mark) at the start of the file
- Line endings: use `\n` (LF), not `\r\n` (CRLF)
- No trailing newline after the last row

### Standard Rubric Dimensions

- **4 criteria** (one per Ontario category) = 20 rows of criterion data
- **2 header rows**
- **Total: 22 rows**

For rubrics with sub-criteria (rare, large projects only), add 5 rows per additional
criterion. The total point values across all Level 4 entries must equal the assignment total.

---

## Point Allocation Tables

### Assignment Type Weightings

**Programming / Technical:**
K/U 25%, T 30%, C 20%, A 25%

**Research / Written:**
K/U 27%, T 27%, C 26%, A 20%

**Creative / Design / Project:**
K/U 20%, T 25%, C 30%, A 25%

**Balanced / Mixed:**
K/U 25%, T 25%, C 25%, A 25%

### Level Point Ratios

| Level         | Ratio  |
|---------------|--------|
| Level 4       | 100%   |
| Level 3       | 75%    |
| Level 2       | 60%    |
| Level 1       | 50%    |
| Below Level 1 | 12.5%  |

### Worked Examples

**6-point programming assignment:**
| Category | L4   | L3   | L2  | L1  | Below L1 |
|----------|------|------|-----|-----|----------|
| K/U      | 1.5  | 1.1  | 0.9 | 0.8 | 0.2      |
| Thinking | 2    | 1.5  | 1.2 | 1   | 0.3      |
| Comm     | 1    | 0.8  | 0.6 | 0.5 | 0.1      |
| App      | 1.5  | 1.1  | 0.9 | 0.8 | 0.2      |
| **Total**| **6**| 4.5  | 3.6 | 3.1 | 0.8      |

**10-point balanced assignment:**
| Category | L4   | L3   | L2  | L1  | Below L1 |
|----------|------|------|-----|-----|----------|
| K/U      | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| Thinking | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| Comm     | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| App      | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| **Total**| **10**| 7.6 | 6   | 5.2 | 1.2      |

**20-point programming project:**
| Category | L4   | L3   | L2   | L1  | Below L1 |
|----------|------|------|------|-----|----------|
| K/U      | 5    | 3.8  | 3    | 2.5 | 0.6      |
| Thinking | 6    | 4.5  | 3.6  | 3   | 0.8      |
| Comm     | 4    | 3    | 2.4  | 2   | 0.5      |
| App      | 5    | 3.8  | 3    | 2.5 | 0.6      |
| **Total**| **20**| 15.1| 12   | 10  | 2.5      |

**10-point research assignment** (27/27/26/20 gives 2.7/2.7/2.6/2.0; rounding each to 0.5
would total 9.5, so the largest remainder takes the last half point, ties toward K/U):
| Category | L4   | L3   | L2  | L1  | Below L1 |
|----------|------|------|-----|-----|----------|
| K/U      | 3    | 2.3  | 1.8 | 1.5 | 0.4      |
| Thinking | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| Comm     | 2.5  | 1.9  | 1.5 | 1.3 | 0.3      |
| App      | 2    | 1.5  | 1.2 | 1   | 0.3      |
| **Total**| **10**| 7.6 | 6   | 5.1 | 1.3      |

Level values are rounded half-up to one decimal place (1.25 becomes 1.3). If the total at
Level 3 or Level 2 is off by a small amount from rounding, that is acceptable.
`scripts/build_rubric.py` does all of this; this section documents what it does.

---

## Descriptor Writing Guide

### Principles

1. **Use "you" statements.** Write directly to the student.
2. **Be concrete.** Describe observable work, not abstract qualities.
3. **Differentiate meaningfully.** Each level must describe genuinely different quality.
4. **Incorporate Ontario qualifiers naturally.** Do not just paste them in mechanically.
5. **Match the assignment.** Descriptors should reference what students actually do.

### Pattern for Writing a Descriptor Set

Start with Level 3 (the standard). Describe solid, competent work. Then:
- Level 4: What does exceptional look like? More depth, sophistication, independence.
- Level 2: What is missing compared to Level 3? Inconsistency, gaps, basic only.
- Level 1: What does struggling look like? Minimal, unclear, incomplete.
- Below Level 1: What does insufficient look like? Not attempted or fundamentally wrong.

### Example Descriptor Sets

**Computer Science -- Programming Concepts (Knowledge/Understanding, 5 pts):**

| Level | Descriptor |
|-------|------------|
| L4 | You demonstrate thorough understanding of all required programming concepts and use advanced features appropriately. Your code shows deep comprehension of how concepts work together. |
| L3 | You demonstrate considerable understanding of programming concepts with appropriate application. You use most concepts correctly and show good comprehension of their relationships. |
| L2 | You demonstrate some understanding of basic programming concepts with inconsistent application. You use simple concepts with occasional errors. |
| L1 | You demonstrate limited understanding of programming concepts with minimal application. You show basic recognition of concepts but struggle with implementation. |
| Below L1 | You show little to no understanding of fundamental programming concepts. Basic concepts are not implemented or contain significant misconceptions. |

**Science -- Experimental Design (Thinking and Investigation, 4 pts):**

| Level | Descriptor |
|-------|------------|
| L4 | You design a thorough experiment with well-controlled variables, detailed procedures, and sophisticated consideration of potential sources of error. |
| L3 | You design a clear experiment with appropriate controls, logical procedures, and good consideration of variables. |
| L2 | You design a basic experiment with some controls identified, though procedures may lack detail or miss some variables. |
| L1 | You design an incomplete experiment with minimal attention to controls, limited procedures, and few variables identified. |
| Below L1 | You have not yet demonstrated the ability to design a functional experiment. Key components are missing or fundamentally flawed. |

**English -- Essay Organization (Communication, 3 pts):**

| Level | Descriptor |
|-------|------------|
| L4 | Your essay is exceptionally well-organized with a compelling introduction, cohesive paragraphs, smooth transitions, and a strong conclusion that ties everything together. |
| L3 | Your essay is well-organized with a clear introduction, focused paragraphs, appropriate transitions, and a conclusion that summarizes key points. |
| L2 | Your essay shows some organization with a basic introduction and conclusion, though paragraphs may lack focus and transitions may be abrupt. |
| L1 | Your essay has limited organization. The introduction or conclusion may be missing or unclear, and ideas are not logically sequenced. |
| Below L1 | Your essay lacks meaningful organization. There is no clear structure, and ideas are presented without logical connection. |

**Geography -- Real-World Connections (Application, 2 pts):**

| Level | Descriptor |
|-------|------------|
| L4 | You make sophisticated connections between geographic concepts and real-world issues, demonstrating insightful analysis of how the concepts apply beyond the classroom. |
| L3 | You make clear connections between geographic concepts and real-world examples with considerable understanding of their relevance. |
| L2 | You make some connections to real-world examples, though your analysis may be surface-level or lack depth. |
| L1 | You make limited connections to the real world with minimal analysis or explanation. |
| Below L1 | You do not yet make meaningful connections between geographic concepts and real-world applications. |

---

## Complete CSV Example

A 10-point balanced assignment for a generic course:

```csv
"It is recommended that you do not edit rubrics in spreadsheet format","","","","","",""
"v1.0-s","","","","","",""
"Knowledge and Understanding - Key Concepts","","","","","",""
"Understanding of core concepts, terminology, and facts as demonstrated in the assignment.","","","","","",""
"","2.5","1.9","1.5","1.3","0.3",""
"","High Degree of Effectiveness (Level 4)","Considerable Effectiveness (Level 3)","Some Effectiveness (Level 2)","Limited Effectiveness (Level 1)","Not Yet Demonstrated",""
"","You demonstrate thorough understanding of all key concepts with accurate use of terminology and detailed explanations.","You demonstrate considerable understanding of key concepts with appropriate use of terminology and clear explanations.","You demonstrate some understanding of basic concepts with inconsistent use of terminology and partial explanations.","You demonstrate limited understanding of concepts with minimal use of correct terminology and unclear explanations.","You show little to no understanding of the key concepts. Terminology is absent or used incorrectly.",""
"Thinking - Analysis and Problem Solving","","","","","",""
"Application of critical thinking, analysis, and problem-solving strategies in completing the assignment.","","","","","",""
"","2.5","1.9","1.5","1.3","0.3",""
"","High Degree of Effectiveness (Level 4)","Considerable Effectiveness (Level 3)","Some Effectiveness (Level 2)","Limited Effectiveness (Level 1)","Not Yet Demonstrated",""
"","You analyze the problem thoroughly, consider multiple approaches, and develop a well-reasoned solution with sophisticated critical thinking.","You analyze the problem clearly, consider appropriate approaches, and develop a sound solution with good critical thinking.","You show some analysis of the problem with a basic approach, though your reasoning may have gaps.","You show limited analysis with a minimal approach and incomplete reasoning.","You have not yet demonstrated problem-solving or analytical thinking for this task.",""
"Communication - Clarity and Organization","","","","","",""
"Quality of expression, organization, and use of appropriate conventions and terminology in the work.","","","","","",""
"","2.5","1.9","1.5","1.3","0.3",""
"","High Degree of Effectiveness (Level 4)","Considerable Effectiveness (Level 3)","Some Effectiveness (Level 2)","Limited Effectiveness (Level 1)","Not Yet Demonstrated",""
"","Your work is exceptionally clear and well-organized with precise use of conventions and terminology throughout.","Your work is clear and well-organized with appropriate use of conventions and terminology.","Your work shows some clarity and organization with basic use of conventions, though inconsistencies are present.","Your work has limited clarity and organization with minimal or incorrect use of conventions.","Your work lacks meaningful organization and does not use appropriate conventions or terminology.",""
"Application - Connections and Transfer","","","","","",""
"Ability to apply knowledge and skills to the given context and make connections to broader applications.","","","","","",""
"","2.5","1.9","1.5","1.3","0.3",""
"","High Degree of Effectiveness (Level 4)","Considerable Effectiveness (Level 3)","Some Effectiveness (Level 2)","Limited Effectiveness (Level 1)","Not Yet Demonstrated",""
"","You apply concepts with exceptional effectiveness, making insightful connections and adapting your approach creatively to meet all requirements.","You apply concepts with considerable effectiveness, making clear connections and meeting most requirements appropriately.","You apply concepts with some effectiveness, making basic connections and meeting some requirements.","You apply concepts with limited effectiveness, making few connections and only partially meeting requirements.","You have not yet demonstrated the ability to apply concepts or make meaningful connections.",""
```

---

## Category Descriptions by Subject Area

These are starting points for criterion descriptions. Adapt to the specific assignment.

### Computer Science
- **K/U**: Understanding of [specific concepts: variables, data types, control structures, etc.] as demonstrated in the [assignment type].
- **Thinking**: Application of problem-solving strategies (decomposition, algorithm design, debugging) in planning and developing the solution.
- **Communication**: Quality of code organization, commenting, variable naming, and documentation following professional conventions.
- **Application**: Ability to apply programming concepts to solve the given problem and connect to real-world applications.

### Science
- **K/U**: Understanding of [specific scientific concepts, laws, terminology] as demonstrated through [lab report / investigation / test].
- **Thinking**: Quality of experimental design, hypothesis formation, data analysis, and scientific reasoning.
- **Communication**: Clarity of scientific communication including proper use of terminology, data presentation, and report organization.
- **Application**: Ability to connect scientific concepts to real-world phenomena, technology, and societal issues.

### English
- **K/U**: Understanding of [literary devices / text structures / language conventions] as demonstrated in the [essay / analysis / creative piece].
- **Thinking**: Quality of critical analysis, interpretation, and creative thinking in developing ideas and arguments.
- **Communication**: Effectiveness of writing organization, voice, style, and adherence to conventions of the form.
- **Application**: Ability to make connections between texts, personal experience, and the wider world.

### Mathematics
- **K/U**: Understanding of [mathematical concepts, procedures, formulas] as demonstrated through problem solutions.
- **Thinking**: Quality of mathematical reasoning, problem-solving strategies, and logical argumentation.
- **Communication**: Clarity of mathematical communication including proper notation, diagrams, and justification of solutions.
- **Application**: Ability to apply mathematical concepts to solve problems in familiar and unfamiliar contexts.

### Social Studies / Geography / History
- **K/U**: Understanding of [key events, concepts, geographic features, historical significance] and relevant terminology.
- **Thinking**: Quality of inquiry, analysis of evidence, evaluation of perspectives, and critical thinking.
- **Communication**: Effectiveness of written/oral communication, use of evidence, and organization of arguments.
- **Application**: Ability to make connections to current events, personal experience, and broader societal implications.

---

## Common Mistakes

1. **Wrong column count.** Every row must have exactly 7 columns. Count the commas: 6 per row.

2. **Modified level title strings.** Row D must use the exact strings:
   - `High Degree of Effectiveness (Level 4)`
   - `Considerable Effectiveness (Level 3)`
   - `Some Effectiveness (Level 2)`
   - `Limited Effectiveness (Level 1)`
   - `Not Yet Demonstrated`

3. **Points don't sum correctly.** All Level 4 values must sum to the total assignment points.

4. **Vague descriptors.** "Demonstrates knowledge with considerable effectiveness" is empty.
   Instead: "You explain how photosynthesis converts light energy into chemical energy with
   clear, accurate detail."

5. **Levels that don't differentiate.** If Level 2 and Level 3 sound the same except for
   one qualifier word, rewrite them to describe genuinely different quality of work.

6. **Missing double quotes.** Every cell, including empty ones, must be quoted.

7. **Descriptors too long.** Keep each descriptor to 1-3 sentences. Google Classroom truncates
   very long text in the rubric view.

8. **Forgetting the trailing empty column.** Every row ends with `,""`.

9. **Wrong level order.** Points go from highest to lowest: L4, L3, L2, L1, Below L1.
   This is left-to-right in the CSV.

10. **Using "the student" instead of "you".** All descriptors should address the student
    directly in second person.

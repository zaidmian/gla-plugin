# Changelog

## 1.5.8

- With no type and no weights, the builder uses the school default, K/U 25, Thinking 30, Communication 20, Application 25 (it used 25/25/25/25). `--from-assignment` puts a course's `assessment.category_weights` in the spec and no longer picks `programming` for Computer Studies.
- The Thinking-category name covers the Grades 1 to 8 Science and Technology documents.
- Short-task guidance no longer calls GLA exercises rubric items: they use the /10 scale.

## 1.5.7

- `references/rubric_format_guide.md` says why the level shares are 100/75/60/50/12.5% (each keeps a uniform result inside its Growing Success band) and that a criterion needs at least 1.5 points for the bands to hold. The shares are unchanged.

## 1.5.6

- Two assignment types: `lab_report` (20/30/25/25) for a science lab report and `essay` (20/30/30/20) for an argued written piece, with what each category holds.

## 1.5.5

- Runs from a Claude Code plugin: SKILL.md says where `scripts/` is (`${CLAUDE_SKILL_DIR}/scripts/` in Claude Code).

## 1.5.4

- When an assignment could fairly be two assignment types, the skill asks the teacher, offering the two types with their category splits as clickable choices where the interface provides them (AskUserQuestion in Claude Code, clickable choices on claude.ai), and in one line of text otherwise.

## 1.5.3

- In house mode, `rubric.md` leaves out the Expectations line when the assignment states no codes (student-facing assignment headers no longer list them).

## 1.5.2

- `--from-assignment` reads the whole slot when it contains a `·` of its own (ICD2O's `handed out U1.W1.D1 · due U1.W2.D3`); it used to stop at "handed out".

## 1.5.1

- House-mode specs can keep a rubric's own title and header lines (`title`, `house.header_lines`) and carry free Markdown before the overview, after it, under a criterion, and after the criteria (`intro_md`, `overview_note_md`, `criteria[].note`, `extra_md`), so rebuilding an existing course rubric keeps its stretch goals and notes.
- The learning-skill warning no longer fires on "behaviour", which in these courses means program behaviour.

## 1.5.0

- Course-repo mode: `--from-assignment DIR` starts a spec from an assignment folder (name, total, bonus from `instructions.md`; course and subject from `course.yaml`; the house header; the criteria of an existing `rubric.csv`), and `--name rubric` writes `rubric.csv` and `rubric.md` back into the folder with the course header block.
- `--import-csv` turns any Google Classroom rubric CSV into a spec; `verify.py` checks the round trip.
- `--check` now reports points with more than one decimal place (the guide rounds to one).

## 1.4.0

- `scripts/build_rubric.py` builds the CSV and the Markdown from a JSON spec: category split by assignment type (or custom weights), half-point rounding that keeps the total exact, level points at 100/75/60/50/12.5% rounded half-up, the second category named from the course code or subject, Google Classroom's exact CSV format, and warnings for learning-skill wording. `--check` validates an existing CSV. The model writes only the criterion focus, description, and descriptors.
- `scripts/verify.py` rebuilds the worked examples and checks every point value; the bundler runs it.
- The format guide's "10-point research" example was a balanced split; it is relabelled, and the research case (which rounded to 9.5 before) has its own table.
- Delivery covers claude.ai, Cowork, and Claude Code.

## 1.3.1

- The Research / Investigation / Written split summed to 101%. Communication drops from 27% to 26%, so the split is now K/U 27%, T 27%, C 26%, A 20% in SKILL.md step 2 and in `references/rubric_format_guide.md`.

## 1.3.0

- The second achievement-chart category is named per subject. Science (SNC, SBI, SCH, SPH, SVN, and Science and Technology in Grades 1 to 8) calls it **Thinking and Investigation**; Computer Studies (ICD2O, ICS3U, ICS4U, ICS3C, ICS4C) and every other subject call it **Thinking**. SKILL.md step 3 states the rule and the criterion examples now show one of each. `references/growing_success_achievement_chart.md` carries the table, the reason Science has the longer name, and the one sentence in the ICD2O curriculum document (Science boilerplate in its Descriptors paragraph) that leads people to mislabel Computer Studies rubrics. `references/rubric_format_guide.md` annotates category 2 and relabels its Science example.

## 1.2.1

- One maintainer rule: the skill keeps its structure and assessment policy fixed in a session, declines off-policy requests in one sentence with a citation, and hands the teacher a fixed report to send. The Markdown rubric's footer now names the skill version.

## 1.2.0

- Growing Success is cited directly: a new reference carries Chapter 3 (achievement chart, levels, qualifiers, Level 3 as the provincial standard), the rubric definitions from the glossary, the Chapter 1 principles behind student-facing wording, and the Chapter 2 rule that learning skills stay out of a mark. SKILL.md reads it before building and checks for learning-skill criteria.

## 1.1.0

- Initial release.

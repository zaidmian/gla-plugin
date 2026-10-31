---
name: setup
description: Check and finish this computer's setup for the GLA skills. Use when the teacher asks to set up, install, check, or repair the GLA skills, when a GLA script stops on a missing module (yaml, docx) or a missing tool (javac, node, LibreOffice), or when the teacher asks which version they have.
---

# Set up the GLA skills on this computer

1. Run `python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" doctor` (on Windows, use `python` if `python3` is not found; if neither runs, Python is not installed: send the teacher to https://www.python.org/downloads/ and, on Windows, have them tick "Add python.exe to PATH" in the installer).
2. If it lists a required Python package as MISSING, ask the teacher before installing (it runs pip for their user account only), then run `python3 "${CLAUDE_SKILL_DIR}/../_tools/gla" setup --yes`.
3. An optional tool matters only for some courses and outputs: a JDK for Java courses, Node.js for p5.js courses, LibreOffice for PDF copies of plans, Chrome or Edge for the calendar page, git for a course's history. Show the teacher the lines that apply to the course they teach, with the install command doctor printed. Installing a program is the teacher's step; never run an installer yourself.
4. Run doctor again and report what is ready, what is still missing, and the version line. A teacher reporting a problem sends that version line with it.

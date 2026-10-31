# GLA skills for Claude Code

The Gibraltar Leadership Academy course skills, packaged as one Claude Code
plugin: starting a course from its Ontario curriculum, authoring weeks and
assessments, running a semester calendar, and formatting plans and rubrics in
the school's house style.

## Install (once)

1. Install Claude Code (the desktop app's Code tab, or the terminal version)
   and Python 3.9 or newer (https://www.python.org/downloads/; on Windows tick
   "Add python.exe to PATH").
2. In Claude Code, run:

       /plugin install gla --marketplace zaidmian/gla-plugin

3. Then run `/gla:setup`. It checks the computer and installs the two Python
   packages the skills need, after asking.
4. Turn on updates: `/plugin`, Marketplaces, gla-teaching, Enable auto-update.

## Use

Open Claude Code in the folder where you keep a course (or an empty folder for
a new one) and ask, or type a command:

- `/gla:bootstrap-gla-course ICS4C`: start a new course
- `/gla:author-week U1.W1`: write a week of lessons
- `/gla:author-assessment U1 test`: write a unit test or assignment
- `/gla:semester new 2026-27 S2`: build a semester calendar
- `/gla:gla-plan-formatter`, `/gla:gc-rubric`: plans and rubrics

On a Chromebook, or anywhere without Claude Code, only the plan formatter and
the rubric skill work: upload their `.skill` files to claude.ai instead.

Problems and change requests go to Br. Zaid, with the version line `/gla:setup` prints.

# The teacher calendar page: what build_calendar.py produces

Reference for maintenance and for answering questions about the page. `build_calendar.py`, `md2html.py` and `audit_log.py` implement all of it.

The page shows one instance week by week, Monday to Friday, with closures, buffer days and the exam window in place; a summary at the top of each week (topics, evaluations handed out or due, a prep checklist from the materials lists); a card per day linking the slides, lesson, exercise sheet and key, assignment sheet with its rubric CSV, reference sheet, docx handout and Google Doc, colour-coded by kind; a chip on any day an assignment is handed out or due; the current day highlighted; and per-day status logging (taught, partial, postponed, moved, skipped, no class, plus a note; a buffer day ran, ran partly, was lost, or had no class) written through Chrome's File System Access API.

## Files in the instance folder

| File | Written by | Purpose |
|------|-----------|---------|
| `calendar.yaml` | `rehydrate.py` | every weekday: slot / buffer / closure / exam, plus hand-outs and dues |
| `week_plans/*.yaml` | `rehydrate.py` | titles, day types, activities, materials, evaluations |
| `Course_Calendar.html` | `build_calendar.py` | the page; safe to rebuild any time |
| `html/` | `build_calendar.py` | read-only HTML twins of every markdown file the page links (lessons, guides, sheets, keys, reference sheets, sub packets), styled for on-screen reading; regenerated on every build (`--no-prerender` links raw .md instead) |
| `teaching_log.jsonl` | the page (Chrome) | append-only status events: `{ts, key, date, status, actual, note}`, plus `master: true` when the note asks for a master change; never edited by scripts |
| `material_links.yaml` | the page (Chrome) | flat `"<material repo path>": "<Google Docs URL>"` map (a bare filename key still works when no other material shares that filename); hand-editable |

A rebuild embeds the current log and links as the page's initial state, so the
page shows the right statuses even before the folder is reconnected. It never
overwrites either file.

An event applies only to the date it was logged for. After a recalendar moves a
slot, its old event no longer shows (a move whose actual date is the slot's new,
past date reads as taught); `audit_log.py` reads the log the same way. Statuses
recorded while the folder was not connected are kept in the browser and written
to the log on the next connect, when they are newer than its last event. A note
is saved when the teacher leaves its box, or when the page closes. A lesson
day's note has a **fix in master** box; ticking it marks the note as a
request for the course's master, and `_tools/backlog.py` lists those requests
(with every day logged as partial) for author-week and author-assessment.

## Google Docs links

The builder cannot know Google Docs URLs. Two ways in:
- In the page, the **+URL** button beside any handout opens a small dialog;
  the URL is saved to `material_links.yaml` and shown first from then on.
- If a Google Drive connector is available in the session, offer to pre-fill
  `material_links.yaml` by searching Drive for the gdocs .docx names (the
  files keep their names when uploaded), keying each entry by the source
  material's repo path. Show the matches and confirm before
  writing; searching Drive reads the user's data, writing the file is local.

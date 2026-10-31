"""Teaching-log notes that ask for a change in master, and which are settled.

The calendar page logs a note per day; ticking "fix in master" marks it as a
request for the course's master. A day logged as partial is a request too:
its content was not all taught, so the next authoring pass (and the unit
test) must know. items() reads every instance's teaching log through
audit_log's rule (an event counts only for the date it was logged for) and
leaves out what master/backlog.yaml records as resolved. An entry there names
the semester, the slot key and the log timestamp it settles, so a note the
teacher edits later comes back.
"""
import datetime as dt
import glob
import os
import sys

import yaml

from . import paths

FILE = os.path.join("master", "backlog.yaml")
HEADER = """# Teaching-log notes that asked for a change in master, and how each was settled.
# `_tools/backlog.py --resolve` adds an entry; author-week and author-assessment
# do this when they make the change. An entry matches one logged note by its
# semester, slot key and log timestamp.
"""


def _audit():
    sys.path.insert(0, os.path.join(paths.SKILLS, "semester", "scripts"))
    import audit_log
    return audit_log


def resolved(root):
    p = os.path.join(root, FILE)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("resolved") or []


def items(root, today=None):
    """Open requests, oldest first: dicts with semester, key, logged (the event's
    ts), date, status, note, kind ("note" or "partial"), master_dir, title."""
    audit = _audit()
    done = {(str(r.get("semester")), str(r.get("key")), str(r.get("logged"))) for r in resolved(root)}
    out = []
    for inst in sorted(glob.glob(os.path.join(root, "instances", "*", "teaching_log.jsonl"))):
        idir = os.path.dirname(inst)
        if not os.path.exists(os.path.join(idir, "calendar.yaml")):
            continue
        sem = os.path.basename(idir)
        cal, state = audit.read_state(idir, today)
        days = {d.get("slot"): d for d in cal.get("days") or [] if d.get("slot")}
        for key, e in state.items():
            note = (e.get("note") or "").strip()
            kind = "note" if e.get("master") and note else ("partial" if e.get("status") == "partial" else None)
            if not kind or (sem, key, str(e.get("ts"))) in done:
                continue
            d = days.get(key) or {}
            out.append({"semester": sem, "key": key, "logged": e.get("ts"), "date": d.get("date") or e.get("date"),
                        "status": e.get("status"), "note": note, "kind": kind,
                        "master_dir": d.get("master_dir"), "title": d.get("title")})
    return sorted(out, key=lambda i: (str(i["key"]), str(i["logged"])))


def resolve(root, semester, key, change, today=None):
    """Record the open request for (semester, key) as settled; returns the entry."""
    match = [i for i in items(root) if i["semester"] == semester and i["key"] == key]
    if not match:
        raise KeyError("no open backlog item for %s %s" % (semester, key))
    item = match[-1]
    entry = {"semester": semester, "key": key, "logged": item["logged"],
             "resolved": (today or dt.date.today()).isoformat(), "change": change}
    p = os.path.join(root, FILE)
    data = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data.setdefault("resolved", []).append(entry)
    with open(p, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=200)
    return entry

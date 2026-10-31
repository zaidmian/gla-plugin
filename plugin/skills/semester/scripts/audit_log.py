#!/usr/bin/env python3
"""
audit_log.py — semester-end (or any-time) audit of what actually happened.

    python3 audit_log.py <instance_dir> [--md]

Reads <instance_dir>/calendar.yaml and <instance_dir>/teaching_log.jsonl (the
append-only log written by Course_Calendar.html) and prints:
  1. per-unit tally (planned slots vs taught / partial / skipped / moved / unlogged)
  2. every slot whose status is not a plain "taught on the planned day"
  3. buffer days: ran vs lost
  4. a config patch: resume_from and the resume_* keys for a mid-semester re-run,
     and events and usable_fraction suggestions for next year, built from the skipped
     and moved slots and their notes
Read-only. Course-agnostic (uses only the calendar schema and log format).
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys

import yaml


def current(cal, state, today):
    """Only the events that describe the calendar as it stands. The log is keyed by
    slot, so after a recalendar an old event would follow its slot to a new date:
    an event logged for another date is dropped, except a move whose actual date
    is the slot's current (past) date, which reads as taught."""
    where = {}
    for d in cal["days"]:
        if d["kind"] == "slot":
            where[d["slot"]] = str(d["date"])
        elif d["kind"] == "buffer":
            where["BUFFER:" + str(d["date"])] = str(d["date"])
    out = {}
    for key, e in state.items():
        date, now = e.get("date"), where.get(key)
        if now is None:
            continue
        if date and date != now:
            if e.get("status") == "moved" and e.get("actual") == now and now < today:
                e = dict(e, status="taught", date=now)
            else:
                continue
        out[key] = e
    return out


def read_state(inst, today=None):
    """(calendar, {key: latest log event that still applies}) for an instance folder."""
    with open(os.path.join(inst, "calendar.yaml"), encoding="utf-8") as f:
        cal = yaml.safe_load(f)
    state = {}
    lp = os.path.join(inst, "teaching_log.jsonl")
    if os.path.exists(lp):
        with open(lp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("status") == "clear":
                    state.pop(e["key"], None)
                else:
                    state[e["key"]] = e
    return cal, current(cal, state, today or dt.date.today().isoformat())


def config_patch(cal, state, today):
    """What the log says should carry into a config: resume_from and the resume_*
    keys (mid-semester), lost buffer days and a usable_fraction (next year), slot
    notes. Postponed slots and slots moved without a date are re-planned; skipped
    ones are dropped; no-class days are closures; partial ones count as taught."""
    slots = [d for d in cal["days"] if d["kind"] == "slot"]
    buffers = [d for d in cal["days"] if d["kind"] == "buffer"]
    out = {"resume_from": "", "resume_postponed": [], "resume_skipped": [], "resume_noclass": [], "resume_moved": {},
           "resume_partial": {}, "lost": [], "ran": 0, "past": 0, "usable_fraction": None, "notes": []}
    logged = [d["date"] for d in slots if d["slot"] in state] + [b["date"] for b in buffers if "BUFFER:" + b["date"] in state]
    if logged:
        nxt = dt.date.fromisoformat(max(logged)) + dt.timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += dt.timedelta(days=1)
        out["resume_from"] = nxt.isoformat()
        for d in slots:
            e = state.get(d["slot"])
            if not e:
                continue
            st, actual = e.get("status"), e.get("actual")
            if st == "postponed" or (st == "moved" and not actual):
                out["resume_postponed"].append(d["slot"])
            elif st == "skipped":
                out["resume_skipped"].append(d["slot"])
            elif st == "noclass":
                out["resume_noclass"].append(d["slot"])
            elif st == "moved" and actual != str(d["date"]):
                out["resume_moved"][d["slot"]] = actual
            elif st == "partial":
                out["resume_partial"][d["slot"]] = e.get("note") or ""
    out["lost"] = [(b.get("label", ""), b["date"]) for b in buffers
                   if state.get("BUFFER:" + b["date"], {}).get("status") in ("skipped", "noclass")]
    past = [d for d in slots if d["date"] < today]
    if past:
        out["past"] = len(past)
        out["ran"] = sum(1 for d in past if state.get(d["slot"], {}).get("status") in ("taught", "partial"))
        out["usable_fraction"] = max(0.70, min(0.95, round(out["ran"] / len(past), 2)))
    out["notes"] = [f'{d["slot"]}: {state[d["slot"]]["note"]}' for d in slots if state.get(d["slot"], {}).get("note")]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_dir")
    ap.add_argument("--md", action="store_true", help="markdown tables instead of plain text")
    a = ap.parse_args()
    inst = os.path.abspath(a.instance_dir.rstrip("/"))
    cal = yaml.safe_load(open(os.path.join(inst, "calendar.yaml")))
    lp = os.path.join(inst, "teaching_log.jsonl")
    events = []
    if os.path.exists(lp):
        for line in open(lp):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"skipping unparseable log line: {line[:80]}", file=sys.stderr)
    state = {}
    for e in events:
        if e.get("status") == "clear":
            state.pop(e["key"], None)
        else:
            state[e["key"]] = e
    today = dt.date.today().isoformat()
    state = current(cal, state, today)
    days = cal["days"]
    slots = [d for d in days if d["kind"] == "slot"]
    buffers = [d for d in days if d["kind"] == "buffer"]

    def unit_of(d):
        wk = d.get("week_key") or ""
        return wk.split(".")[0] if wk else d["slot"].split(".")[0]

    tally = collections.OrderedDict()
    for d in slots:
        u = unit_of(d)
        t = tally.setdefault(u, collections.Counter())
        t["planned"] += 1
        s = state.get(d["slot"])
        if not s:
            if d["date"] < today:
                t["unlogged"] += 1
            else:
                t["ahead"] += 1
        else:
            t[s.get("status", "?")] += 1

    sep = "|" if a.md else "  "
    print(f"# {cal.get('course', {}).get('code', '')} {cal.get('semester', {}).get('name', '')} — teaching log audit ({len(events)} events, as of {today})\n")
    print("## Per-unit tally\n")
    cols = ["unit", "planned", "taught", "partial", "postponed", "moved", "skipped", "noclass", "unlogged", "ahead"]
    if a.md:
        print("| " + " | ".join(cols) + " |")
        print("|" + "|".join(["---"] * len(cols)) + "|")
    else:
        print("  ".join(c.ljust(9) for c in cols))
    for u, t in tally.items():
        row = [u] + [str(t.get(c, 0)) for c in cols[1:]]
        print(("| " + " | ".join(row) + " |") if a.md else "  ".join(x.ljust(9) for x in row))

    print("\n## Deviations from the plan\n")
    rows = []
    for d in slots:
        s = state.get(d["slot"])
        if not s:
            if d["date"] < today:
                rows.append((d["date"], d["slot"], d.get("title", ""), "UNLOGGED", "", ""))
            continue
        actual = s.get("actual") or ""
        if s.get("status") == "taught" and (not actual or actual == d["date"]) and not s.get("note"):
            continue
        rows.append((d["date"], d["slot"], d.get("title", ""), s.get("status", ""), actual if actual != d["date"] else "", s.get("note", "")))
    if not rows:
        print("none — every past slot is logged as taught on its planned day")
    for r in rows:
        if a.md:
            print("| " + " | ".join(r) + " |")
        else:
            print(f"{r[0]}  {r[1]:<10} {r[3]:<9} {('→ ' + r[4]) if r[4] else '':<13} {r[2]}" + (f"\n{'':>12}note: {r[5]}" if r[5] else ""))

    print("\n## Buffer days\n")
    for b in buffers:
        s = state.get("BUFFER:" + b["date"])
        status = {"taught": "class ran", "skipped": "lost", "partial": "partly", "noclass": "no class"}.get(s.get("status"), s.get("status")) if s else ("unlogged" if b["date"] < today else "ahead")
        print(f"{b['date']}  {status:<10} {b.get('label', '')}" + (f"  — {s['note']}" if s and s.get("note") else ""))

    print("\n## Config patch\n")
    print("Paste what applies into semester_config.yaml. Dates for next year move: fill them in, never copy last year's.\n")
    p = config_patch(cal, state, today)
    lines = []
    if p["resume_from"]:
        lines += ["# Mid-semester re-run of this instance (rerun the generator on it):",
                  'resume_from: "%s"   # the first weekday after the last logged day' % p["resume_from"]]
        for key, why in (("resume_postponed", "postponed: re-planned after resume_from"),
                         ("resume_skipped", "skipped: not taught this semester"),
                         ("resume_noclass", "the class did not meet: a closure, the slot re-planned"),
                         ("resume_moved", "taught, or to be taught, on another date"),
                         ("resume_partial", "partly taught: counted as taught, flagged")):
            if p[key]:
                lines.append("%s: %s   # %s" % (key, json.dumps(p[key]), why))
    if p["lost"]:
        lines += ["", "# Next year's config: these events cost a day this year (confirm next year's dates):", "events:"]
        for label, date in p["lost"]:
            lines.append('  - { name: "%s", start: "", buffers: 1 }   # lost a buffer on %s' % (label, date))
    if p["past"]:
        lines += ["", "# Next year's config: %d of %d past slots ran (taught or partial)." % (p["ran"], p["past"]),
                  "capacity: { usable_fraction: %.2f }" % p["usable_fraction"]]
    if p["notes"]:
        lines += ["", "overrides:   # notes only; the generator does not act on them"] + ['  - "%s"' % n.replace('"', "'") for n in p["notes"]]
    print("\n".join(lines) if lines else "(nothing to carry forward)")

if __name__ == "__main__":
    main()

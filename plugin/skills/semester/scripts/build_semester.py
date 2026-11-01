#!/usr/bin/env python3
"""Build a semester instance end to end, in the right order.

    python3 build_semester.py init NAME [--from SEMESTER | --no-from] [--out PATH]
    python3 build_semester.py new CONFIG [--force] [--plans] [--date "September 1, 2026"]
    python3 build_semester.py refresh SEMESTER [--plans] [--weekplans]
    python3 build_semester.py recalendar SEMESTER [--resume-from DATE] [--postpone SLOT ...] [--skip SLOT ...]
                                         [--no-class SLOT ...] [--move SLOT=DATE ...] [--apply] [--plans]

init     write a semester_config.yaml for the teacher to edit: the course's
         template (or the shared one), the semester name, every date TODO.
         From the latest instance (or --from), it carries holiday and event
         names, PA-day labels and module choices (dates TODO), adds the events
         whose buffer day was lost, and takes usable_fraction from the
         teaching log (audit_log.py). When Teaching/Calendars/<year>.yaml
         exists for the name's school year ("2026-27 S2"), it sets
         school_calendar instead: the dates, holidays, PA days and school
         events come from that file, and only the course's own events keep
         TODO dates. Default --out: <folder>_semester_config.yaml.
new      generate the instance from a filled semester_config.yaml (with
         resume_from set, a mid-semester re-run of an existing instance), check
         it, convert the Google Docs handouts, optionally render the branded
         plan documents, and build the teacher calendar.
refresh  the outputs only, for an existing instance after master materials
         change: Google Docs handouts, optional plan documents, calendar.
         --weekplans first re-copies master week plans into the instance with
         the dates calendar.yaml already gives them (no re-planning).
recalendar  re-plan an existing instance from a date onward, after lost days.
         Takes resume_from and the resume_* keys from the teaching log
         (audit_log): postponed slots are re-planned, skipped ones dropped,
         no-class days become closures, moved slots go to their date, partial
         ones are flagged. An option replaces its key from the log. It
         regenerates into a scratch
         folder, and prints what moves: slots, tests, dues, cuts, buffers, and
         the generator's flags. Nothing is written without --apply, which then
         sets the two keys in the instance's semester_config.yaml and runs `new`.

Order matters: the calendar reads gdocs/index.yaml, so it is built last.
Run from the course root. Stops at the first failing step and says which.
Exit codes: 0 done; 1 a step failed; 2 cannot run (no course.yaml, no instance,
TODO left in the config); 3 the plan needs a teacher decision.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.realpath(__file__))
SKILLS = os.path.realpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(SKILLS, "_lib"))
PLAN_FORMATTER = os.path.join(SKILLS, "gla-plan-formatter", "scripts", "build_plan.py")


GLA_NAMES = {"rehydrate.py": "rehydrate", "check_instance.py": "instance", "convert_instance.py": "gdocs",
             "build_calendar.py": "calendar", "build_plan.py": "plan"}


def shown(cmd):
    """A step's command as the teacher would type it: the gla command, paths relative to the course."""
    out = []
    for a in cmd[1:]:
        name = os.path.basename(a)
        if a.endswith(".py") and name in GLA_NAMES:
            out.append("gla " + GLA_NAMES[name])
        elif os.path.isabs(a) and a.startswith(os.getcwd() + os.sep):
            out.append(os.path.relpath(a))
        else:
            out.append(a)
    return " ".join(out)


def step(title, cmd, ok=(0,)):
    print("\n== %s\n$ %s" % (title, shown(cmd)), flush=True)
    rc = subprocess.run(cmd).returncode
    if rc not in ok:
        print("\nSTOPPED at '%s' (exit %d)." % (title, rc))
    return rc


def instance_name(config):
    with open(config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return (cfg.get("output") or {}).get("instance_folder") or cfg["semester"]["name"].replace(" ", "_")


def todos(obj, at=""):
    """Dotted paths whose value still says TODO."""
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in todos(v, "%s.%s" % (at, k) if at else str(k))]
    if isinstance(obj, list):
        return [p for i, v in enumerate(obj) for p in todos(v, "%s[%d]" % (at, i))]
    return [at] if isinstance(obj, str) and "TODO" in obj else []


def template_path():
    with open("course.yaml", encoding="utf-8") as f:
        cy = yaml.safe_load(f) or {}
    own = os.path.join("master", cy.get("rehydration_dir") or "", "Semester_Config_Template.yaml")
    return own if cy.get("rehydration_dir") and os.path.exists(own) else os.path.join(
        SKILLS, "..", "Standards", "rehydration", "Semester_Config_Template.yaml")


def latest_instance():
    found = sorted(d for d in glob.glob(os.path.join("instances", "*")) if os.path.exists(os.path.join(d, "semester_config.yaml")))
    return os.path.basename(found[-1]) if found else None


def _flow(d):
    return "{ " + ", ".join("%s: %s" % (k, json.dumps(v)) for k, v in d.items()) + " }"


def school_calendar_for(name):
    """("2026-27 S2", the school calendar) when the name's school year has a file in Teaching/Calendars."""
    from gla import schoolcal
    ref = " ".join(name.split()[:2])
    if not schoolcal.REF.match(ref):
        return None
    try:
        return ref, schoolcal.load(ref.split()[0])
    except schoolcal.SchoolCalendarError:
        return None


def init_config(name, prev=None, today=None):
    """The text of a new semester_config.yaml, and notes on what was carried."""
    with open(template_path(), encoding="utf-8") as f:
        text = f.read()
    folder = name.replace(" ", "_")
    tp = os.path.realpath(template_path())
    shared = os.path.realpath(os.path.join(SKILLS, ".."))
    notes = ["template: %s" % ("GLA_ROOT/" + os.path.relpath(tp, shared).replace(os.sep, "/") if tp.startswith(shared + os.sep)
                               else os.path.relpath(tp))]
    pcfg, patch = {}, None
    if prev:
        pdir = os.path.join("instances", prev)
        with open(os.path.join(pdir, "semester_config.yaml"), encoding="utf-8") as f:
            pcfg = yaml.safe_load(f) or {}
        if os.path.exists(os.path.join(pdir, "calendar.yaml")):
            sys.path.insert(0, HERE)
            import audit_log
            cal, state = audit_log.read_state(pdir)
            patch = audit_log.config_patch(cal, state, today or dt.date.today().isoformat())
        notes.append("carried from instances/%s" % prev)

    def sub(pattern, repl, count=1):
        nonlocal text
        new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
        if not n:
            raise SystemExit("init: the template has no line matching %r" % pattern)
        text = new

    sub(r'^(\s+name:\s*)""', r'\g<1>"%s"' % name)
    school = school_calendar_for(name)
    if school:
        ref, scal = school
        where = "Calendars/%s.yaml" % ref.split()[0]
        line = 'school_calendar: "%s"   # dates, holidays, PA days and school events come from %s' % (ref, where)
        if re.search(r"^school_calendar:", text, re.M):
            sub(r"^school_calendar:.*$", line)
        else:
            sub(r"^semester:", line + "\n\nsemester:")
        notes.append("school_calendar: %s (%s)" % (ref, where))
        school_events = {e.get("name") for e in scal.get("events") or []}
    else:
        for k in ("first_day", "last_day", "exam_start", "exam_end"):
            sub(r'^(\s+%s:\s*)""' % k, r'\g<1>"TODO"')
        school_events = set()
    if school:
        sub(r"^holidays:\n(?:  .*\n)+", "holidays: []   # this course's own closures only; the school's come from %s\n" % where)
        sub(r"^pa_days:.*$", "pa_days: []   # this course's own only")
    else:
        hol = [h.get("name") for h in pcfg.get("holidays") or [] if h.get("name")]
        rows = ['  - { name: "%s", start: "TODO", end: "TODO" }' % h for h in hol] or ['  - { name: "TODO", start: "TODO", end: "TODO" }']
        rows.append("  # TODO: this year's Ramadan break and Eid dates, and any holiday not listed")
        sub(r"^holidays:\n(?:  .*\n)+", "holidays:\n" + "\n".join(rows) + "\n")
        labels = [p["label"] for p in pcfg.get("pa_days") or [] if isinstance(p, dict) and p.get("label")]
        pa = 'pa_days: "TODO"   # ["YYYY-MM-DD", ...]; [] if none'
        if labels:
            pa = "pa_days:   # TODO: the unlabelled PA days too\n" + "\n".join('  - { date: "TODO", label: "%s" }' % l for l in labels)
        sub(r"^pa_days:.*$", pa)

    def carried(name_, buffers, note=None):
        if name_ in school_events:   # dates from the school calendar
            return dict(name=name_, buffers=buffers, **({"note": note} if note else {}))
        return dict(name=name_, start="TODO", end="TODO", buffers=buffers, **({"note": note} if note else {}))
    events = [carried(e["name"], e.get("buffers", 0), e.get("note")) for e in pcfg.get("events") or [] if e.get("name")]
    have = {e["name"] for e in events}
    for label, date in (patch or {}).get("lost", []):
        if label and label not in have:
            events.append(carried(label, 1))
            have.add(label)
            notes.append("event %r: its buffer day was lost on %s" % (label, date))
    if events:
        head = "events:   # TODO: this year's dates; add new events" if any(e.get("start") for e in events) else \
            "events:   # school events by name take their dates from the school calendar"
        sub(r"^events:.*$", head + "\n" + "\n".join("  - " + _flow(e) for e in events))
    elif school:
        sub(r"^events:.*$", "events: []   # name a school event here to give it buffer days; add the course's own")
    else:
        sub(r"^events:.*$", 'events: "TODO"   # [] if none, else - { name: "", start: "YYYY-MM-DD", end: "YYYY-MM-DD", buffers: 1, note: "" }')
    frac = (patch or {}).get("usable_fraction") or ((pcfg.get("capacity") or {}).get("usable_fraction"))
    if frac:
        why = "the teaching log: %d of %d past slots ran" % (patch["ran"], patch["past"]) if patch and patch.get("usable_fraction") else "the previous config"
        sub(r"^(\s+usable_fraction:\s*)[0-9.]+.*$", r"\g<1>%.2f   # from %s" % (frac, why))
        notes.append("usable_fraction %.2f from %s" % (frac, why))
    for k, v in (pcfg.get("modules") or {}).items():
        if re.search(r"^\s+%s:" % re.escape(k), text, re.M):
            sub(r"^(\s+%s:\s*)\S+" % re.escape(k), r"\g<1>%s" % v)
            notes.append("modules.%s: %s (as last time)" % (k, v))
    sub(r'^(\s+instance_folder:\s*)""', r'\g<1>"%s"' % folder)
    yaml.safe_load(text)
    return text, notes


def outputs(sem, plans):
    py = sys.executable
    if step("Google Docs handouts", [py, os.path.join(HERE, "convert_instance.py"), sem]):
        return 1
    if plans:
        inst = os.path.join("instances", sem)
        out = os.path.join(inst, "gdocs", "Admin")
        os.makedirs(out, exist_ok=True)
        # The formatter's spec and page PNGs stay out of the repo; its review file
        # lists what it derived and sits beside the instance, not among the handouts.
        extra = ["--pdf", "--artifacts-dir", tempfile.mkdtemp(prefix="gla_plans_"),
                 "--review", os.path.join(inst, "Admin_Plans_Review.md")]
        if step("Short and Long Term Plan (GLA format)", [py, PLAN_FORMATTER, "--type", "long_range_plan", "--md",
                os.path.join(inst, "Short_and_Long_Term_Plan.md"), "--out", os.path.join(out, "Short_and_Long_Term_Plan.docx")] + extra):
            return 1
        for wp in sorted(glob.glob(os.path.join(inst, "week_plans", "*.yaml"))):
            name = os.path.splitext(os.path.basename(wp))[0]
            if step("Weekly plan %s (GLA format)" % name, [py, PLAN_FORMATTER, "--type", "weekly_plan", "--yaml", wp,
                    "--out", os.path.join(out, "Weekly_Plan_%s.docx" % name)] + extra):
                return 1
    if step("Teacher calendar", [py, os.path.join(HERE, "build_calendar.py"), os.path.join("instances", sem)]):
        return 1
    return 0


def set_top_key(text, key, value):
    """Set a top-level key in YAML text to a one-line value, keeping every other
    line (and its comments) as it is. Replaces the key and any indented lines
    under it, or appends it; never leaves a second copy of the key."""
    line = "%s: %s" % (key, json.dumps(value))
    pat = re.compile(r"^%s:.*\n?(?:[ \t]+.*\n?|[ \t]*\n)*?(?=^\S|\Z)" % re.escape(key), re.M)
    if pat.search(text):
        text = pat.sub(lambda m: line + "\n", text, count=1)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    got = yaml.safe_load(text).get(key)
    if got != value:
        raise SystemExit("could not set %s in the config (read back %r)" % (key, got))
    return text


def _days(cal):
    return {str(d["slot"]): d for d in cal["days"] if d.get("kind") == "slot"}


def calendar_diff(old, new, since):
    """Lines describing how new differs from old on and after `since`."""
    o, n = _days(old), _days(new)
    fmt = lambda v: dt.date.fromisoformat(str(v)).strftime("%a %b %d").replace(" 0", " ")  # noqa: E731
    out, moved = [], []
    for slot, d in n.items():
        if slot in o and str(o[slot]["date"]) != str(d["date"]):
            tags = (["test"] if d.get("day_type") == "assess" else []) + ["due: %s" % x for x in d.get("dues") or []] + \
                   ["handed out: %s" % x for x in d.get("handouts") or []]
            moved.append((str(d["date"]), "  %-10s %-36s %s -> %s%s" % (slot, (d.get("title") or "")[:36], fmt(o[slot]["date"]),
                                                                      fmt(d["date"]), ("  [%s]" % "; ".join(tags)) if tags else "")))
    out.append("Moved: %d slot(s)" % len(moved))
    out += [m for _, m in sorted(moved)]
    cut = [s for s in o if s not in n and str(o[s]["date"]) >= since]
    back = [s for s in n if s not in o]
    if cut:
        out.append("Now cut: " + ", ".join(cut))
    if back:
        out.append("Back in: " + ", ".join(back))
    buf = lambda cal: {(str(d["date"]), d.get("label", "")) for d in cal["days"] if d.get("kind") == "buffer" and str(d["date"]) >= since}  # noqa: E731
    gone, added = sorted(buf(old) - buf(new)), sorted(buf(new) - buf(old))
    if gone:
        out.append("Buffers removed: " + ", ".join("%s (%s)" % (fmt(d), l) for d, l in gone))
    if added:
        out.append("Buffers added: " + ", ".join("%s (%s)" % (fmt(d), l) for d, l in added))
    if len(out) == 1 and not moved:
        out.append("No dates change.")
    return out


def recalendar(a):
    import shutil
    sys.path.insert(0, HERE)
    import audit_log
    inst = os.path.join("instances", a.semester)
    cpath = os.path.join(inst, "semester_config.yaml")
    if not os.path.exists(cpath) or not os.path.exists(os.path.join(inst, "calendar.yaml")):
        print("ERROR: %s needs semester_config.yaml and calendar.yaml" % inst)
        return 2
    with open(cpath, encoding="utf-8") as f:
        text = f.read()
    cal, state = audit_log.read_state(inst)
    patch = audit_log.config_patch(cal, state, dt.date.today().isoformat())
    resume = a.resume_from or patch["resume_from"]
    if not resume:
        print("ERROR: the teaching log has nothing logged yet; pass --resume-from YYYY-MM-DD")
        return 2
    keys = {"resume_postponed": a.postpone, "resume_skipped": a.skip, "resume_noclass": a.no_class,
            "resume_moved": dict(x.split("=", 1) for x in a.move) if a.move is not None else None,
            "resume_partial": None}
    keys = {k: (v if v is not None else patch[k]) for k, v in keys.items()}
    text = set_top_key(text, "resume_from", resume)
    for k, v in keys.items():
        text = set_top_key(text, k, v)
    print("Re-plan from %s" % resume)
    for k, what in (("resume_postponed", "postponed, re-planned"), ("resume_skipped", "skipped, not taught this semester"),
                    ("resume_noclass", "no class, re-planned"), ("resume_partial", "partly taught (flagged)")):
        if keys[k]:
            print("  %s: %s" % (what, ", ".join(keys[k])))
    for slot, date in sorted(keys["resume_moved"].items()):
        print("  moved: %s to %s" % (slot, date))
    scratch = tempfile.mkdtemp(prefix="gla_recal_")
    try:
        shutil.copy(os.path.join(inst, "calendar.yaml"), scratch)
        tcfg = os.path.join(scratch, "semester_config.yaml")
        with open(tcfg, "w", encoding="utf-8") as f:
            f.write(text)
        r = subprocess.run([sys.executable, os.path.join(HERE, "rehydrate.py"), tcfg, "--out", scratch, "--force"],
                           capture_output=True, text=True)
        breaks = [ln for ln in r.stdout.splitlines() if ln.startswith("RULE BREAK: ")]
        if r.returncode == 2 or (r.returncode == 3 and not breaks):
            print(r.stdout.strip())
            return r.returncode
        with open(os.path.join(scratch, "calendar.yaml"), encoding="utf-8") as f:
            new = yaml.safe_load(f)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for line in calendar_diff(cal, new, resume):
        print(line)
    flags = [ln.strip()[len("flag: "):] for ln in r.stdout.splitlines() if ln.strip().startswith("flag: ")]
    if flags:
        print("Generator flags:")
        for fl in flags:
            print("  - " + fl)
    if breaks:
        print("Rule breaks on dates still ahead (the teacher decides; see the semester skill):")
        for ln in breaks:
            print("  - " + ln[len("RULE BREAK: "):])
        if a.apply:
            print("\nNot applied. Change the config or list the items in accept_rule_breaks, then rerun.")
            return 3
    if not a.apply:
        print("\nDry run: nothing written. To apply: gla semester recalendar %s%s%s --apply"
              % (a.semester, " --resume-from %s" % a.resume_from if a.resume_from else "",
                 "".join(" --%s %s" % (opt, " ".join(v)) for opt, v in (("postpone", a.postpone), ("skip", a.skip),
                         ("no-class", a.no_class), ("move", a.move)) if v)))
        return 0
    with open(cpath, "w", encoding="utf-8") as f:
        f.write(text)
    print("\nset resume_from and the resume_* keys in %s" % cpath)
    return main(["new", cpath, "--force"] + (["--plans"] if a.plans else []))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    i = sub.add_parser("init")
    i.add_argument("name")
    i.add_argument("--from", dest="prev")
    i.add_argument("--no-from", action="store_true")
    i.add_argument("--out")
    n = sub.add_parser("new")
    n.add_argument("config")
    n.add_argument("--force", action="store_true")
    n.add_argument("--plans", action="store_true")
    n.add_argument("--date")
    r = sub.add_parser("refresh")
    r.add_argument("semester")
    r.add_argument("--plans", action="store_true")
    r.add_argument("--weekplans", action="store_true")
    rc_ = sub.add_parser("recalendar")
    rc_.add_argument("semester")
    rc_.add_argument("--resume-from")
    rc_.add_argument("--postpone", nargs="*", metavar="SLOT")
    rc_.add_argument("--skip", nargs="*", metavar="SLOT")
    rc_.add_argument("--no-class", nargs="*", metavar="SLOT")
    rc_.add_argument("--move", nargs="*", metavar="SLOT=DATE")
    rc_.add_argument("--apply", action="store_true")
    rc_.add_argument("--plans", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.exists("course.yaml"):
        print("ERROR: run from a course repo root (no course.yaml here)")
        return 2
    py = sys.executable
    if a.mode == "recalendar":
        return recalendar(a)
    if a.mode == "init":
        prev = None if a.no_from else (a.prev or latest_instance())
        if prev and not os.path.exists(os.path.join("instances", prev, "semester_config.yaml")):
            print("ERROR: no instances/%s/semester_config.yaml" % prev)
            return 2
        out = a.out or "%s_semester_config.yaml" % a.name.replace(" ", "_")
        if os.path.exists(out):
            print("ERROR: %s exists" % out)
            return 2
        text, notes = init_config(a.name, prev)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        left = todos(yaml.safe_load(text))
        print("wrote %s (%d TODO field(s))" % (out, len(left)))
        for n_ in notes:
            print("  " + n_)
        print("Fill every TODO, then: gla semester new %s" % out)
        return 0
    if a.mode == "new":
        with open(a.config, encoding="utf-8") as f:
            left = todos(yaml.safe_load(f) or {})
        if left:
            print("ERROR: %s still has TODO in: %s" % (a.config, ", ".join(left)))
            return 2
        from gla import schoolcal
        with open(a.config, encoding="utf-8") as f:
            try:
                schoolcal.resolve(yaml.safe_load(f) or {})
            except schoolcal.SchoolCalendarError as e:
                print("ERROR: %s" % e)
                return 2
        cmd = [py, os.path.join(HERE, "rehydrate.py"), a.config] + (["--force"] if a.force else []) + (["--date", a.date] if a.date else [])
        rc = step("Generate the instance", cmd)
        if rc == 3:
            return 3
        if rc:
            return 1
        sem = instance_name(a.config)
        if step("Check the instance", [py, os.path.join(SKILLS, "_tools", "check_instance.py"), sem]):
            return 1
    else:
        sem = a.semester
        if not os.path.isdir(os.path.join("instances", sem)):
            print("ERROR: no instances/%s" % sem)
            return 2
        if a.weekplans:
            from gla import course, rehydrate
            root = os.getcwd()
            changed = rehydrate.refresh_week_plans(root, os.path.join("instances", sem),
                                                   rehydrate.load_params(root, course.load(root)))
            print("== Week plans from master: %d changed%s" % (len(changed), "".join("\n  " + os.path.relpath(p) for p in changed)))
    rc = outputs(sem, a.plans)
    if not rc:
        print("\nDone: instances/%s. Next: add decisions and flags to semester_config.yaml (decisions:, flags:) and fill any flagged register descriptions." % sem
              if a.mode == "new" else "\nDone: instances/%s outputs refreshed." % sem)
    return rc


if __name__ == "__main__":
    sys.exit(main())

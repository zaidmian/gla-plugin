#!/usr/bin/env python3
"""Generate a dated semester instance's calendar from master.

    python3 rehydrate.py CONFIG [--root COURSE_ROOT] [--out DIR] [--force] [--date "September 1, 2026"]

CONFIG is a filled semester_config.yaml. With `resume_from: YYYY-MM-DD` in it,
the existing instance's calendar.yaml supplies every day before that date
unchanged and only the rest is re-planned (mid-semester recalendaring). The course's parameters come from
master/<rehydration_dir>/rehydration.yaml. Writes calendar.yaml,
Course_Calendar.md, week_plans/, GENERATION_REPORT.md and a copy of the
config into --out (default instances/<output.instance_folder>). Refuses to
write into an existing instance without --force; it never touches
teaching_log.jsonl, material_links.yaml, gdocs/ or html/.

Exit codes: 0 written, 2 bad config or parameters, 3 the plan needs a
teacher decision (floor reached or manual compression), 1 the written
instance failed check_instance.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
from gla import course, findings, instance, rehydrate  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--date", help="the 'generated on' date to record (default today)")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root:
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    ccfg = course.load(root)
    folder = rehydrate._get(cfg, "output.instance_folder") or cfg["semester"]["name"].replace(" ", "_")
    out = os.path.abspath(args.out or os.path.join(root, "instances", folder))
    previous = None
    if cfg.get("resume_from"):
        prev_path = os.path.join(out, "calendar.yaml")
        if not os.path.exists(prev_path):
            print("ERROR: resume_from is set but %s does not exist" % prev_path)
            return 2
        with open(prev_path, encoding="utf-8") as f:
            previous = yaml.safe_load(f)
    try:
        params = rehydrate.load_params(root, ccfg)
        plan = rehydrate.build(root, cfg, params, ccfg, previous)
    except rehydrate.ConfigError as e:
        print("ERROR: %s" % e)
        return 2
    except rehydrate.NeedsTeacher as e:
        print("STOP: %s" % e)
        return 3
    if os.path.exists(os.path.join(out, "calendar.yaml")) and not args.force and not previous:
        print("ERROR: %s already has a calendar; pass --force to regenerate it" % out)
        return 2
    rehydrate.write(plan, out, args.config, args.date)
    m = plan.math
    print("%s %s: %d scheduled, %d usable, %d slots (%d cut, %d spill), %d buffers -> %s"
          % (ccfg.get("code"), cfg["semester"]["name"], m["scheduled"], m["usable"], m["slots"],
             len(plan.cuts), plan.spill, m["buffers"], out))
    for flag in plan.flags:
        print("  flag: " + flag)
    report = findings.Report(root)
    if os.path.dirname(out) == os.path.join(root, "instances"):
        instance.check(root, os.path.basename(out), report, classroom=(ccfg.get("assessment") or {}).get("classroom"),
                       only_calendar=True)
        errors = [i for i in report.items if i[0] == findings.ERROR]
        if errors:
            report.print(title="check_instance (calendar files)")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check a dated semester instance against the rehydration rules.

    python3 check_instance.py [SEMESTER] [--root COURSE_ROOT] [--strict]

Run from inside a course repo, or pass --root. With no SEMESTER and exactly
one instance, that one is checked. Errors exit 1; --strict also fails on
warnings. Covers Rehydration_Framework.md §6 as far as a script can decide.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
from gla import course, findings, instance  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("semester", nargs="?")
    ap.add_argument("--root")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root:
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    sem = args.semester
    if not sem:
        found = sorted(d for d in os.listdir(os.path.join(root, "instances"))
                       if os.path.isdir(os.path.join(root, "instances", d))) if os.path.isdir(os.path.join(root, "instances")) else []
        if len(found) != 1:
            print("ERROR: name the semester (instances found: %s)" % (", ".join(found) or "none"))
            return 2
        sem = found[0]
    report = findings.Report(root)
    cfg = course.load(root) if os.path.exists(os.path.join(root, "course.yaml")) else {}
    instance.check(root, sem, report, classroom=(cfg.get("assessment") or {}).get("classroom"))
    report.print(title="%s instance %s" % (cfg.get("code", os.path.basename(root)), sem))
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main())

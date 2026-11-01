#!/usr/bin/env python3
"""List the teaching-log notes that ask for a change in a course's master.

    python3 backlog.py [--root COURSE_ROOT] [--slot PREFIX] [--json]
    python3 backlog.py --resolve SEMESTER KEY --change "what changed in master"

A note counts when the teacher ticked "fix in master" on the calendar page,
and a day logged as partial always counts (its content was not all taught).
Items are grouped by master folder; --slot keeps keys that start with a
prefix (U3, U3.W2). --resolve records one item as settled in
master/backlog.yaml so it stops being listed (gla.backlog).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
from gla import backlog, course  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--slot", help="keep keys starting with this prefix, for example U3 or U3.W2")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--resolve", nargs=2, metavar=("SEMESTER", "KEY"))
    ap.add_argument("--change", help="with --resolve: one line on what changed in master")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root:
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    if args.resolve:
        if not args.change:
            print("ERROR: --resolve needs --change")
            return 2
        try:
            e = backlog.resolve(root, args.resolve[0], args.resolve[1], args.change)
        except KeyError as err:
            print("ERROR: %s" % err.args[0])
            return 1
        print("resolved %s %s (logged %s) in %s" % (e["semester"], e["key"], e["logged"], backlog.FILE))
        return 0
    found = backlog.items(root)
    if args.slot:
        found = [i for i in found if i["key"] == args.slot or i["key"].startswith(args.slot.rstrip(".") + ".")]
    if args.json:
        json.dump(found, sys.stdout, indent=2, default=str)
        print()
        return 0
    if not found:
        print("No open backlog items%s." % (" for " + args.slot if args.slot else ""))
        return 0
    by_dir = {}
    for i in found:
        by_dir.setdefault(i["master_dir"] or "(slot not in the calendar)", []).append(i)
    for d in sorted(by_dir):
        print(d)
        for i in by_dir[d]:
            what = "partly taught" if i["kind"] == "partial" else "fix in master"
            print("  %s  %s, %s (%s): %s" % (i["key"], i["semester"], i["date"], what, i["note"] or "(no note)"))
    print("%d open item(s). Resolve one: gla backlog --resolve SEMESTER KEY --change \"...\"" % len(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())

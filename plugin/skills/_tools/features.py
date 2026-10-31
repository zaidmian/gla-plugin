#!/usr/bin/env python3
"""Feature availability by slot: the course's YAML and the Style Guide table rendered from it.

    python3 features.py extract [--root R]   write feature_availability.yaml from today's Style Guide
                                             table and baseline section, then render the table
    python3 features.py render  [--root R]   rewrite the Style Guide table from the YAML
    python3 features.py check   [--root R]   exit 1 when the table has drifted from the YAML

Run from a course repo root, or pass --root.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
from gla import course, features  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("extract", "render", "check"))
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root) if a.root else course.find_root()
    if not root:
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    sg = os.path.join(root, features.STYLE)
    if not os.path.exists(sg):
        print("ERROR: no %s" % features.STYLE)
        return 2
    with open(sg, encoding="utf-8") as f:
        text = f.read()
    code = course.load(root).get("code", "")
    if a.cmd == "extract":
        if os.path.exists(features.path(root)):
            print("ERROR: %s exists; edit it and run render" % features.REL)
            return 1
        data = features.extract(text)
        if not data["rows"]:
            print("ERROR: the Style Guide has no feature availability table")
            return 1
        with open(features.path(root), "w", encoding="utf-8") as f:
            f.write(features.dump(data, code))
        print("wrote %s: %d rows, %d baseline tokens" % (features.REL, len(data["rows"]), len(data["baseline"])))
    if a.cmd in ("extract", "render"):
        data = features.load(root)
        if data is None:
            print("ERROR: no %s; run extract first" % features.REL)
            return 1
        new = features.with_rendered_table(text, data)
        if new is None:
            print("ERROR: the Style Guide has no Feature availability section with a table to replace")
            return 1
        if new != text:
            with open(sg, "w", encoding="utf-8") as f:
                f.write(new)
            print("rendered the table in %s" % features.STYLE)
        else:
            print("the table in %s is already current" % features.STYLE)
        return 0
    d = features.drift(root)
    if features.load(root) is None:
        print("no %s" % features.REL)
        return 1
    print(d or "the Style Guide's table matches %s" % features.REL)
    return 1 if d else 0


if __name__ == "__main__":
    sys.exit(main())

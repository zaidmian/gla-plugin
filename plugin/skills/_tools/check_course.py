#!/usr/bin/env python3
"""Check a GLA course repo's course.yaml and master content.

    python3 check_course.py [--root COURSE_ROOT] [--strict] [--no-style] [--only CODE[,CODE]]
                            [--paths FILE... | --changed]

Run from inside a course repo, or pass --root. Errors exit 1; --strict also
fails on warnings. --no-style drops the em dash, emoji and master-date
warnings. --only keeps findings whose code starts with one of the given
prefixes (for example --only weight,coverage); an unknown prefix exits 2.
--paths keeps the findings on the named files and folders (and on a folder
that holds one of them); --changed does the same for the files git reports
as changed or new. A warning a file allows with a gla-allow comment is
listed as allowed and does not count (findings.py).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
from gla import course, coursecheck, findings  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--no-style", action="store_true")
    ap.add_argument("--only")
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--paths", nargs="+", metavar="FILE")
    scope.add_argument("--changed", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else course.find_root()
    if not root:
        print("ERROR: no course.yaml here or above; pass --root")
        return 2
    prefixes = tuple(p.strip() for p in args.only.split(",") if p.strip()) if args.only else ()
    unknown = findings.unknown_prefixes(prefixes)
    if unknown:
        print("ERROR: --only %s matches no finding code" % ", ".join(unknown))
        return 2
    keep = args.paths
    if args.changed:
        try:
            keep = findings.changed_files(root)
        except (RuntimeError, OSError) as e:
            print("ERROR: --changed needs a git repo: %s" % e)
            return 2
        if not keep:
            print("No changed files under %s" % root)
            return 0
    report = findings.Report(root)
    c = coursecheck.check(root, report, style=not args.no_style)
    if prefixes:
        report.items = [i for i in report.items if i[1].startswith(prefixes)]
    if keep is not None:
        report.keep_paths(keep)
    report.apply_allows()
    report.print(title="%s course check" % (c.cfg.get("code") or os.path.basename(root)))
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main())

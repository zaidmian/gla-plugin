"""Collect validator findings and print them in one format.

An error breaks a hard rule (a sum that is not 100, a missing file, a slot on
a closure). A warning breaks a soft rule (minutes near 50, a style tell).
--strict turns warnings into errors.

A file can keep one of its warnings with a reason, in an HTML comment
(`<!-- gla-allow: deck-length short studio deck -->`) or, in YAML, a
comment (`# gla-allow: weekplan-minutes double period`). The code matches
the warning's code or a prefix of it. An allowed warning no longer counts;
the report lists it with its reason. Errors are never allowed, and an allow
without a reason does nothing.
"""
import os
import re
import sys

ERROR, WARN = "error", "warning"

# Finding codes are <area>-<thing>, so --only can select an area:
#   admin, assignment, code, course, coverage, curriculum, day (per-day files:
#   teach-pair, wet-lab), deck, deliverable (exercise and brief sheets and their
#   companions), eval (instance evaluations), features, guide, header, image,
#   index, map, master, md (instance documents), name, rubric, style, test,
#   unit, week/weekplan, weight; and calendar, instance and plan for instances.
# Codes renamed for that scheme; an allow comment or --only prefix that names
# the old code still works.
ALIASES = {"companion": "deliverable-companion", "sub-box": "deliverable-sub-box", "ten-table": "deliverable-ten-table",
           "brief-key": "deliverable-brief-key", "placeholder": "style-placeholder", "teach-pair": "day-teach-pair",
           "wet-lab": "day-wet-lab", "plan-total": "md-plan-total", "review-copy": "test-review-copy",
           "key-missing": "test-key-missing", "key-answer": "test-key-answer", "key-run": "test-key-run",
           "key": "test-key", "coverage-extra-code": "code-unknown", "coverage-code": "code-unknown",
           "config-missing": "instance-config-missing"}


def canonical(code):
    """A finding code or --only prefix under its current name."""
    return ALIASES.get(code, code)


_EMIT = re.compile(r"\.(?:error|warn|_compare)\(")
_CODE = re.compile(r'"([a-z]+(?:-[a-z0-9]+)+)"')
ALLOW = re.compile(r"gla-allow:[ \t]*([a-z][a-z0-9-]*)[ \t]*(.*?)[ \t]*(?:-->|$)", re.M)


def known_codes():
    """Every finding code the Skills tools can emit, read from their sources:
    the string literals on lines that call error(), warn() or _compare()."""
    from . import paths
    out = set()
    for dirpath, dirs, files in os.walk(paths.SKILLS):
        dirs[:] = [d for d in dirs if d not in ("tests", "gla-plan-formatter", "__pycache__") and not d.startswith(".")]
        for name in files:
            if name.endswith(".py"):
                with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                    for line in f:
                        if _EMIT.search(line):
                            out.update(_CODE.findall(line))
    return out


def unknown_prefixes(prefixes):
    """The prefixes in an --only list that no finding code starts with."""
    codes = known_codes()
    return [p for p in prefixes if not any(c.startswith(canonical(p)) for c in codes)]


def allows(path):
    """{code: reason} from the gla-allow comments in a file."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return {}
    return {m.group(1): m.group(2) for m in ALLOW.finditer(text) if m.group(2).strip()}


def changed_files(root):
    """Files git reports as changed or new under root (staged, unstaged or untracked)."""
    import subprocess
    out = subprocess.run(["git", "-C", root, "status", "--porcelain", "-uall", "--", "."],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "git status failed")
    top = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    files = []
    for line in out.stdout.splitlines():
        name = line[3:].split(" -> ")[-1].strip('"')
        files.append(os.path.join(top, name))
    return files


class Report:
    def __init__(self, root=None):
        self.root = root
        self.items = []
        self.allowed = []

    def _add(self, level, code, path, msg, line=None):
        self.items.append((level, code, path, line, msg))

    def error(self, code, path, msg, line=None):
        self._add(ERROR, code, path, msg, line)

    def warn(self, code, path, msg, line=None):
        self._add(WARN, code, path, msg, line)

    def keep_paths(self, paths):
        """Keep the findings on the given files or folders, and the findings on a
        folder that holds one of them."""
        want = [os.path.abspath(p).rstrip(os.sep) for p in paths]

        def inside(a, b):
            return a == b or a.startswith(b + os.sep)
        self.items = [i for i in self.items if i[2] and any(
            inside(os.path.abspath(str(i[2])).rstrip(os.sep), w) or inside(w, os.path.abspath(str(i[2])).rstrip(os.sep))
            for w in want)]

    def apply_allows(self):
        """Move the warnings a file allows (see the module docstring) to self.allowed."""
        cache, kept = {}, []
        for item in self.items:
            level, code, path = item[0], item[1], item[2]
            if level == WARN and path:
                rules = cache.setdefault(path, allows(str(path)))
                reason = next((r for c, r in rules.items() if code.startswith(canonical(c))), None)
                if reason is not None:
                    self.allowed.append(item + (reason,))
                    continue
            kept.append(item)
        self.items = kept

    def count(self, level):
        return sum(1 for i in self.items if i[0] == level)

    def _where(self, path, line):
        if not path:
            return ""
        p = os.path.relpath(path, self.root) if self.root and os.path.isabs(path) else path
        return "%s:%s" % (p, line) if line else p

    def print(self, out=sys.stdout, title=None):
        if title:
            print(title, file=out)
        for level, code, path, line, msg in sorted(self.items, key=lambda i: (i[0] != ERROR, str(i[2]), i[3] or 0)):
            where = self._where(path, line)
            print("  %-7s %-24s %s%s" % (level, code, (where + "  ") if where else "", msg), file=out)
        for _, code, path, line, msg, reason in self.allowed:
            where = self._where(path, line)
            print("  %-7s %-24s %s%s (%s)" % ("allowed", code, (where + "  ") if where else "", msg, reason), file=out)
        tail = ", %d allowed" % len(self.allowed) if self.allowed else ""
        print("%d error(s), %d warning(s)%s" % (self.count(ERROR), self.count(WARN), tail), file=out)

    def exit_code(self, strict=False):
        if self.count(ERROR) or (strict and self.count(WARN)):
            return 1
        return 0

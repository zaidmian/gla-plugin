#!/usr/bin/env python3
"""Compile and run the code samples in GLA course files.

Usage:
    python3 run_samples.py PATH... [--root COURSE_ROOT] [--json] [--jobs N]

PATH is a .md lesson/key/reference/test file, a D*_Slides_*.html deck, a
.java or .js file, or a folder (searched recursively). COURSE_ROOT is the
course repo (the folder holding course.yaml); by default it is found by
walking up from each PATH.

What it checks, per the author-week hard rules ("Only-taught features",
"Executed output only"):

Java
  * ```java fences in Markdown and <pre class="code"> blocks in decks.
  * A block whose top-level class has main() is compiled and run (javac and
    java from PATH, temp dir, timeouts). Classes it uses that are declared in
    other blocks of the same file (or of a sibling .md in the same folder) are
    compiled with it.
  * A complete class without main() is compiled only.
  * A statement-only snippet is wrapped in a main() only when the file shows
    its output (a deck console-out box or an output label), because that is
    the one case where the course presents a snippet as something that runs.
    Any other snippet is reported as not runnable.
  * Shown output is taken from: a bare/text/output/console fence right after
    the code (optionally behind a label line such as "Output:", "Verified
    output:" or "**Expected output:**"); an inline label line such as
    "Output: `malas`" or "Verified output: `A` / `B`" (" / " separates
    lines); a deck <div class="console-out"> after the <pre>; and, for
    *_KEY.md files, sample runs in the sibling student sheet under the
    heading that names `ClassName.java`.
  * In a unit test's test.md, a fragment under a question that asks for
    output (output, print, trace, display) takes its answer from the sibling
    test_KEY.md under the same question ID: the line naming its label
    ("Fragment A", "Segment 2", "(b)"), else the question's "Output: `...`"
    line or output fence. A Part A question takes the option its key letter
    names, when that option is backticked code. Givens written in the
    question as `name = value` become `var` declarations in the wrapper. A
    trace question whose answer cannot be found is listed as shown output
    that was not verified.
  * Shown input is taken from "inputs `a`, `b`" / "user types `a` then `b`"
    prose after the code, an "Input:" fence, or from a sample-run transcript
    (the text after a System.out.print("prompt") literal). When input is fed
    the program sees it line by line and the typed text is echoed into stdout,
    so the result reads like the transcript a student sees.
  * Programs that read System.in with no shown input are compiled only.
  * Nondeterministic programs (unseeded random, clock) are run but their
    output is not compared.
  * Blocks presented as broken on purpose (bug hunts, find-the-error
    questions, "Expected output once fixed", deck err-line boxes) have their
    failures reported as expected, never as failures.

Calculations (any course)
  * ```calc fences hold one `expression = answer` per line (a ` # note` may
    follow). The expression is arithmetic: numbers, + - * / // % ** (or ^, ×,
    ÷), brackets, pi, e, sqrt, log, log10, exp, the trig functions, round. The
    answer may be rounded to the decimal places it shows and may end in %. A
    line that does not hold is a mismatch.

p5.js
  * ```javascript / ```js fences and deck <pre class="code"> blocks get
    `node --check` (syntax only; nothing is ever run).

Feature availability (warnings only)
  * The file's slot comes from its **Slot:** header, a deck slot-id, the
    folder's week_plan.yaml slot_prefix, or the U#_/W#_ folder names.
  * The course's master/01_Standards/feature_availability.yaml (else the
    Style_Guide.md "Feature availability by slot" table) gives, per row, the
    backticked features. A feature from a
    row later than the slot that appears in a sample is flagged.
  * False positives are limited by scanning code with comments and string
    literals blanked out, matching keywords and class names as whole words,
    matching other lower-case names only as calls or member access, skipping
    tokens listed in a "baseline" section, and skipping slots the table does
    not order (CP, R, AI, "any").

Exit status: 1 when any block has an output mismatch, a compile error, or a
JS syntax error (outside intentional-error blocks); 0 otherwise.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import difflib
import html
import json
import math
import operator
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
from gla import slots as slotmod  # noqa: E402

COMPILE_TIMEOUT = 60
RUN_TIMEOUT = 10
JAVA_LANGS = {"java"}
JS_LANGS = {"javascript", "js", "p5", "p5js"}
OUTPUT_LANGS = {"", "text", "output", "console", "plaintext", "txt", "shell-session"}
INPUT_LANGS = {"input", "stdin"}

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+.-]*)[^\n]*$")
SLOT_RE = slotmod.MENTION_RE   # slots and weeks in prose; module blocks come from the course
OUTPUT_LABEL_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*|__)?\s*(?:verified\s+(?:same\s+)?output|expected\s+output|sample\s+output|"
    r"actual\s+output|output|console\s+output|prints|it\s+prints|result)"
    r"(?P<rest>[^:\n]{0,60}?)\s*:?\s*(?:\*\*|__)?\s*:?\s*(?P<tail>.*)$",
    re.I,
)
SAMPLE_RUN_LABEL_RE = re.compile(r"(sample\s+run|sample\s+transcript|transcript|example\s+run)", re.I)
INPUT_LABEL_RE = re.compile(r"^\s*(?:\*\*)?\s*(?:sample\s+)?input\s*(?:\*\*)?\s*:\s*(?:\*\*)?\s*$", re.I)
FIXED_RE = re.compile(r"\b(once|after|when|if)\b[^.\n]{0,25}\bfix", re.I)
BROKEN_PROSE_RE = re.compile(
    r"\b(bugs?|buggy|broken|crash(?:es|ing)?|does\s*n[o']t\s+compile|won't\s+compile|will\s+not\s+compile|"
    r"doesn't\s+compile|not\s+compile|compile\s+error|compiler\s+error|syntax\s+error|runtime\s+error|"
    r"logic\s+error|find\s+the\s+(?:bug|error|mistake)|find\s+(?:\*\*)?\w+\s+(?:errors|bugs|mistakes)|spot\s+the|what(?:'s|\s+is)\s+wrong|"
    r"fix\s+(?:it|this|the)|error\s*\(|errors?\s*:|"
    r"(?:contains|has)\b[^.\n]{0,30}\b(?:errors?|bugs?|mistakes?)\b)",
    re.I,
)
BROKEN_COMMENT_RE = re.compile(
    r"//\s*(?:<--\s*)?(?:bug|error|compile\s+error|does\s*n[o']t\s+compile|won't\s+compile|crash|throws|"
    r"wrong|oops|broken|exception|infinite)", re.I)
# The first line after a block that explains what is wrong with it.
AFTER_BROKEN_RE = re.compile(
    r"^\(?\s*(?:it|this|this one|the code|the program)\s+(?:contains|has|will\s+not|won't|does\s*n[o']t|"
    r"compiles,\s+then|crashes|throws)|\bdeliberate(?:ly)?\b", re.I)
NONDET_RE = re.compile(
    r"Math\.random\s*\(|new\s+Random\s*\(\s*\)|ThreadLocalRandom|currentTimeMillis|nanoTime|"
    r"LocalDate(?:Time)?\.now|LocalTime\.now|Instant\.now|new\s+Date\s*\(\s*\)|hashCode\s*\(|UUID")
STDIN_RE = re.compile(r"System\.in\b")
JAVA_KEYWORDS = {
    "abstract", "boolean", "break", "byte", "case", "catch", "char", "class", "continue", "default",
    "do", "double", "else", "enum", "extends", "final", "finally", "float", "for", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "new", "package", "private", "protected",
    "public", "return", "short", "static", "super", "switch", "this", "throw", "throws", "try",
    "void", "while", "var", "record", "null", "true", "false",
}
JS_KEYWORDS = {
    "let", "const", "var", "function", "if", "else", "for", "while", "do", "return", "class", "new",
    "this", "switch", "case", "break", "continue", "true", "false", "null", "undefined", "typeof",
}
P5_VARIABLES = {
    "width", "height", "mouseX", "mouseY", "pmouseX", "pmouseY", "mouseIsPressed", "frameCount",
    "key", "keyCode", "keyIsPressed", "deltaTime", "windowWidth", "windowHeight", "PI", "TWO_PI",
}
P5_CALLBACKS = {
    "setup", "draw", "preload", "mousePressed", "mouseReleased", "mouseClicked", "mouseMoved",
    "mouseDragged", "doubleClicked", "mouseWheel", "keyPressed", "keyReleased", "keyTyped",
    "windowResized", "touchStarted", "touchMoved", "touchEnded",
}
# Feature-table rows describe some features in prose instead of backticks.
# Each entry: (language, phrase in the row text, regex over stripped code).
PHRASE_RULES = [
    ("java", "1-d arrays", r"\b\w+\s*\[\s*\]\s*[A-Za-z_]\w*(?!\s*\[)|\bnew\s+\w+\s*\[[^\]]+\]\s*(?!\[)"),
    ("java", "2-d arrays", r"\]\s*\[|\[\s*\]\s*\[\s*\]"),
    ("java", "student-written static methods",
     r"\bstatic\s+(?!void\s+main\b)[\w<>]+(?:\s*\[\s*\])*\s+(?!main\b)[a-z]\w*\s*\("),
    ("js", "writing functions",
     r"\bfunction\s+(?!(?i:" + "|".join(sorted(P5_CALLBACKS)) + r")\b)\w+\s*\("),
]


# ---------------------------------------------------------------- data model

@dataclass
class Block:
    file: str
    index: int
    line: int
    lang: str                 # java | js
    origin: str               # md | deck | file
    code: str
    expected: list = field(default_factory=list)   # list of (label, text, stdin or None)
    stdin: str | None = None
    intentional: str = ""     # why the block is presented as broken, if it is
    context: str = ""
    sheet_runs: list = field(default_factory=list)  # transcripts from a paired student sheet
    prelude: str = ""         # declarations for a test fragment's givens, put before it when wrapped
    unpaired: str = ""        # a test trace question whose answer was not found in test_KEY.md


@dataclass
class Result:
    index: int
    line: int
    lang: str
    status: str
    detail: str = ""
    diff: str = ""
    features: list = field(default_factory=list)
    intentional: str = ""
    shown_output: bool = False


# ---------------------------------------------------------------- utilities

def blank_java(code: str, keep_strings: bool = False) -> str:
    """Blank out comments (and string/char literals unless keep_strings), preserving length."""
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if code.startswith("//", i):
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", code[i:j]))
            i = j
        elif code.startswith('"""', i):
            j = code.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append(code[i:j] if keep_strings else '"' + re.sub(r"[^\n]", " ", code[i + 1:j - 1]) + '"')
            i = j
        elif c in "\"'`":
            j = i + 1
            while j < n and code[j] != c and code[j] != "\n":
                j += 2 if code[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(code[i:j] if keep_strings else c + " " * max(0, j - i - 2) + (code[j - 1] if j - i >= 2 else ""))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def norm_output(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return lines


def outputs_match(expected: str, actual: str) -> bool:
    exp, act = norm_output(expected), norm_output(actual)
    if exp == act:
        return True
    # "..." or "…" on its own line elides part of the output.
    if any(ln.strip() in ("...", "…") for ln in exp):
        parts, cur = [], []
        for ln in exp:
            if ln.strip() in ("...", "…"):
                parts.append(cur)
                cur = []
            else:
                cur.append(ln)
        parts.append(cur)
        pos = 0
        for k, part in enumerate(parts):
            if not part:
                continue
            found = -1
            for s in range(pos, len(act) - len(part) + 1):
                if act[s:s + len(part)] == part:
                    found = s
                    break
            if found < 0 or (k == 0 and found != 0):
                return False
            pos = found + len(part)
        return not parts[-1] or act[-len(parts[-1]):] == parts[-1]
    return False


def short_diff(expected: str, actual: str, limit: int = 14) -> str:
    d = list(difflib.unified_diff(norm_output(expected), norm_output(actual),
                                  "shown", "actual", n=0, lineterm=""))
    d = [ln for ln in d if not ln.startswith("@@")]
    if len(d) > limit:
        d = d[:limit] + [f"... ({len(d) - limit} more diff lines)"]
    return "\n".join(d)


def find_course_root(path: str) -> str | None:
    p = os.path.realpath(path)
    if os.path.isfile(p):
        p = os.path.dirname(p)
    while True:
        if os.path.isfile(os.path.join(p, "course.yaml")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def course_language(root: str | None) -> str:
    if not root:
        return ""
    try:
        with open(os.path.join(root, "course.yaml"), encoding="utf-8") as fh:
            for ln in fh:
                m = re.match(r"\s*language\s*:\s*['\"]?([^'\"#\n]+)", ln)
                if m:
                    lang = m.group(1).strip().lower()
                    return "js" if ("p5" in lang or "javascript" in lang) else ("java" if "java" in lang else lang)
    except OSError:
        pass
    return ""


# ---------------------------------------------------------------- slots and features

def parse_slot(text: str):
    m = SLOT_RE.search(text or "")
    if not m:
        return None
    unit = m.group(1)
    week = m.group(2)
    wk = int(week[1:]) if week and week.startswith("W") else None
    return unit, wk


def file_slot(path: str, text: str):
    head = "\n".join(text.splitlines()[:25])
    m = re.search(r"\*\*Slot:\*\*\s*([^\n]*)", head)
    if m:
        val = m.group(1)
        val = re.split(r"\s+·\s+|\*\*Type", val)[0]
        if re.search(r"\bany\b", val, re.I) and not SLOT_RE.search(val):
            return None, "any"
        s = parse_slot(val)
        if s:
            return s, val.strip()
    m = re.search(r'class="slot-id[^"]*"[^>]*>([^<]+)<', text)
    if m and parse_slot(m.group(1)):
        return parse_slot(m.group(1)), m.group(1).strip()
    d = os.path.dirname(os.path.realpath(path))
    wp = os.path.join(d, "week_plan.yaml")
    if os.path.isfile(wp):
        with open(wp, encoding="utf-8") as fh:
            m = re.search(r"slot_prefix\s*:\s*['\"]?([^'\"\n]+)", fh.read())
        if m and parse_slot(m.group(1)):
            return parse_slot(m.group(1)), m.group(1).strip() + " (week_plan.yaml)"
    parts = os.path.realpath(path).split(os.sep)
    unit = week = None
    for comp in parts:
        mu = re.match(r"(U\d+)_", comp)
        mw = re.match(r"W(\d+)_", comp)
        if mu:
            unit, week = mu.group(1), None
        elif mw and unit:
            week = int(mw.group(1))
    if unit:
        return (unit, week), unit + (f".W{week}" if week else "") + " (folder)"
    return None, ""


@dataclass
class Feature:
    token: str
    row: str
    order: tuple
    regex: re.Pattern


def token_regex(tok: str, lang: str) -> str | None:
    tok = tok.strip()
    if not tok or tok in ("//", "/*", "*/", "+", "-", "*", "/", "%", "="):
        return None
    if tok == "&&":
        return r"&&"
    if tok == "||":
        return r"\|\|"
    if tok == "!":
        return r"!(?!=)"
    if re.fullmatch(r"[A-Za-z_]\w*(\s+[A-Za-z_]\w*)+", tok):        # "else if"
        return r"\b" + r"\s+".join(tok.split()) + r"\b"
    had_parens = tok.endswith("()")
    core = tok[:-2] if had_parens else tok
    if core.endswith(".*"):
        return r"\b" + re.escape(core[:-2]) + r"\."
    if "." in core:
        parts = core.split(".")
        if not all(re.fullmatch(r"[A-Za-z_]\w*", p) for p in parts):
            return None
        if parts[0] == "java":                                       # java.util.Random
            return r"\b" + re.escape(parts[-1]) + r"\b"
        if parts[0] == "String" and len(parts) == 2:                  # String.compareTo
            return r"\." + re.escape(parts[1]) + r"\s*\("
        return r"\b" + r"\s*\.\s*".join(map(re.escape, parts)) + (r"\s*\(" if had_parens else r"\b")
    if not re.fullmatch(r"[A-Za-z_]\w*", core):
        return None
    kws = JAVA_KEYWORDS if lang == "java" else JS_KEYWORDS
    if core in kws or core[0].isupper() or (lang == "js" and core in P5_VARIABLES):
        return r"\b" + core + r"\b"
    if lang == "js" and core in P5_CALLBACKS:
        return r"\b" + core + r"\s*\("
    return r"(?:(?<![\w.])" + core + r"\s*\(|\." + core + r"\b)"


def _features_yaml(root):
    """The course's feature_availability.yaml through the shared library, or None."""
    lib = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from gla import features  # noqa: E402
    return features.load(root)


def _style_guide_rows(text: str):
    """(rows, baseline) from a Style Guide's table, for a course without the YAML."""
    lines = text.splitlines()
    baseline = set()
    cur_heading = ""
    for ln in lines:
        if ln.startswith("#"):
            cur_heading = ln.lower()
        elif "baseline" in cur_heading:
            baseline.update(t.strip() for t in re.findall(r"`([^`]+)`", ln))
    start = next((i for i, ln in enumerate(lines) if ln.startswith("#") and "feature availability" in ln.lower()), None)
    if start is None:
        return None, baseline
    rows = []
    for ln in lines[start + 1:]:
        if ln.startswith("#"):
            break
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: ") or cells[0].lower() == "from":
            continue
        rows.append((cells[0], cells[1]))
    return rows, baseline


def load_features(root: str | None, lang: str):
    """Return (features, unit_order, note)."""
    if not root:
        return [], [], "no course root"
    data = _features_yaml(root)
    if data is not None:
        rows = [(str(r.get("from", "")), str(r.get("available", ""))) for r in data["rows"]]
        baseline = set(str(t) for t in data["baseline"])
    else:
        sg = os.path.join(root, "master", "01_Standards", "Style_Guide.md")
        if not os.path.isfile(sg):
            return [], [], "no Style_Guide.md"
        rows, baseline = _style_guide_rows(read_text(sg))
        if rows is None:
            return [], [], "no feature table"
    unit_order = []
    for key, _ in rows:
        u = key.split(".")[0]
        if u not in unit_order:
            unit_order.append(u)
    feats, seen = [], set()
    demo = set()
    for key, desc in rows:
        if "teacher demo" in desc.lower() and parse_slot(key):
            demo.add(parse_slot(key))
        slot = parse_slot(key)
        if not slot:
            continue
        order = (unit_order.index(slot[0]), slot[1] or 0)
        toks = []
        for t in re.findall(r"`([^`]+)`", desc):
            if "/" in t and not t.startswith("/") and all(re.fullmatch(r"[\w.()]+", p) for p in t.split("/")):
                toks.extend(t.split("/"))
            else:
                toks.append(t)
        for t in toks:
            if t in baseline or t in seen:
                continue
            rx = token_regex(t, lang)
            if rx:
                seen.add(t)
                feats.append(Feature(t, key, order, re.compile(rx)))
        low = desc.lower()
        for plang, phrase, rx in PHRASE_RULES:
            if plang == lang and phrase in low and phrase not in seen:
                seen.add(phrase)
                feats.append(Feature(phrase, key, order, re.compile(rx)))
    DEMO_SLOTS[id(feats)] = demo
    return feats, unit_order, ""


# Slots whose table row says the code there is a teacher demo (no warnings), keyed by feature list.
DEMO_SLOTS: dict = {}


def feature_warnings(code: str, lang: str, slot, feats, unit_order) -> list[str]:
    if not slot or not feats or slot[0] not in unit_order:
        return []
    demo = DEMO_SLOTS.get(id(feats), ())
    if slot in demo or (slot[0], None) in demo:
        return []
    s_order = (unit_order.index(slot[0]), slot[1] if slot[1] is not None else 99)
    scan = blank_java(code)
    if lang == "java":
        scan = re.sub(r"String\s*(?:\[\s*\]|\.\.\.)\s*args", "String args", scan)
    out = []
    for f in feats:
        if f.order <= s_order:
            continue
        m = f.regex.search(scan)
        if m:
            ln = scan.count("\n", 0, m.start()) + 1
            out.append(f"`{f.token}` (available from {f.row}) at code line {ln}")
    return out


# ---------------------------------------------------------------- extraction

def _backtick_items(s: str) -> list[str]:
    return re.findall(r"`([^`\n]+)`", s)


def _inline_output(tail: str) -> str | None:
    m = re.match(r"\s*((?:`[^`\n]+`)(?:\s*(?:/|,\s*then|then)\s*`[^`\n]+`)*)", tail)
    if not m or re.match(r"\s*(?:→|->|=>|=)", tail[m.end():]):
        return None
    return "\n".join(_backtick_items(m.group(1)))


def _input_from_prose(text: str) -> str | None:
    m = re.search(r"\b(?:inputs?|user\s+(?:types|enters|types in)|typing|entering)\b[^`\n.]{0,30}?"
                  r"((?:`[^`\n]*`\s*(?:,|and|then|,\s*then|/)?\s*)+)", text, re.I)
    if m:
        items = _backtick_items(m.group(1))
        if items:
            return "\n".join(items) + "\n"
    m = re.search(r"\bwith\s+inputs?\s+((?:-?\d+(?:\.\d+)?\s*,\s*)+-?\d+(?:\.\d+)?)", text, re.I)
    if m:
        return "\n".join(x.strip() for x in m.group(1).split(",")) + "\n"
    return None


def parse_md_fences(lines: list[str]):
    """Yield (start, end, lang) for fenced blocks; end is the closing fence line index."""
    out, i = [], 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            mark = m.group(2)
            close = re.compile(r"^\s*" + re.escape(mark[0]) + "{" + str(len(mark)) + r",}\s*$")
            j = i + 1
            while j < len(lines) and not close.match(lines[j]):
                j += 1
            out.append((i, j, m.group(3).lower()))
            i = j + 1
        else:
            i += 1
    return out


def fence_body(lines: list[str], start: int, end: int) -> str:
    """Body of the fence opened at `start`, with the fence's own indentation removed."""
    ind = len(lines[start]) - len(lines[start].lstrip())
    return "\n".join(ln[ind:] if ln[:ind].strip() == "" else ln.lstrip() for ln in lines[start + 1:end])


def _dedent(body: list[str]) -> str:
    ind = min((len(b) - len(b.lstrip()) for b in body if b.strip()), default=0)
    return "\n".join(b[ind:] for b in body)


def _heading_before(lines, idx):
    for k in range(idx, -1, -1):
        if lines[k].startswith("#"):
            return lines[k].lstrip("#").strip()
    return ""


def _prose_before(lines, start, limit=4):
    out, k = [], start - 1
    while k >= 0 and len(out) < limit:
        s = lines[k].strip()
        if s.startswith("```") or s.startswith("~~~"):
            break
        if s:
            out.append(s)
            if s.startswith("#"):
                break
        elif out:
            break
        k -= 1
    return " ".join(reversed(out))


def extract_md(path: str, text: str, default_lang: str) -> list[Block]:
    lines = text.splitlines()
    fences = parse_md_fences(lines)
    blocks = []
    # Keys hold the repaired model answers: their headings name the bugs and their
    # code carries "// BUG 1 (syntax): ..." comments, so neither marks a key block as broken.
    is_key = path.endswith("_KEY.md")
    for fi, (s, e, lang) in enumerate(fences):
        if lang in JAVA_LANGS:
            blang = "java"
        elif lang in JS_LANGS:
            blang = "js"
        elif lang == "calc":
            blocks.append(Block(path, len(blocks) + 1, s + 1, "calc", "md", "\n".join(lines[s + 1:e])))
            continue
        else:
            continue
        b = Block(path, len(blocks) + 1, s + 1, blang, "md", _dedent(lines[s + 1:e]))
        b.context = _heading_before(lines, s)
        before = _prose_before(lines, s)
        # Look after the block: label lines, inline outputs, output fences, input prose.
        k = e + 1
        label = ""
        prose_after = []
        nxt = fences[fi + 1] if fi + 1 < len(fences) else None
        scanned = 0
        while k < len(lines) and scanned < 6:
            ln = lines[k]
            st = ln.strip()
            if nxt and k == nxt[0]:
                if nxt[2] in OUTPUT_LANGS or nxt[2] in INPUT_LANGS:
                    body = fence_body(lines, nxt[0], nxt[1])
                    if nxt[2] in INPUT_LANGS or INPUT_LABEL_RE.match(label or ""):
                        b.stdin = body.rstrip("\n") + "\n"
                        # an output fence may follow the input fence
                        fi2 = fi + 2
                        if fi2 < len(fences) and fences[fi2][2] in OUTPUT_LANGS and \
                                all(not x.strip() or OUTPUT_LABEL_RE.match(x) for x in lines[nxt[1] + 1:fences[fi2][0]]):
                            n2 = fences[fi2]
                            lbl = " ".join(x.strip() for x in lines[nxt[1] + 1:n2[0]] if x.strip())
                            b.expected.append((lbl or "output fence", fence_body(lines, n2[0], n2[1]), None))
                    elif label or nxt[2] in ("text", "output", "console", "plaintext", "txt") or scanned == 0 or \
                            not "".join(prose_after).strip():
                        b.expected.append((label or "output fence", body, None))
                break
            if st.startswith("#") or (st.startswith("|") and not label):
                break
            if st:
                scanned += 1
                prose_after.append(st)
                if INPUT_LABEL_RE.match(st):
                    label = st
                else:
                    m = OUTPUT_LABEL_RE.match(st)
                    if m and len(m.group("rest")) < 45:
                        inline = _inline_output(m.group("tail"))
                        if inline is not None and not FIXED_RE.search(st[:m.start("tail")]):
                            b.expected.append((st[:m.start("tail")].strip() or "inline", inline, None))
                            break
                        if not m.group("tail").strip() or m.group("tail").strip() in ("**", "__"):
                            label = st
                        elif inline is None and scanned > 1:
                            break
                    elif scanned >= 2 and not label:
                        break
            k += 1
        after = " ".join(prose_after[:3])
        stdin = _input_from_prose(after) or _input_from_prose(before if re.search(r"verified|sample", before, re.I) else "")
        if stdin and not b.stdin:
            b.stdin = stdin
        # Was the block presented as broken on purpose?
        why = ""
        if label and FIXED_RE.search(label):
            why = f"output labelled '{label.strip('*: ')}'"
            b.expected = []
        elif BROKEN_PROSE_RE.search(before) and not (is_key and before.startswith("|")):
            why = "prose: " + BROKEN_PROSE_RE.search(before).group(0)
        elif not is_key and BROKEN_PROSE_RE.search(b.context):
            why = "heading: " + BROKEN_PROSE_RE.search(b.context).group(0)
        elif not is_key and BROKEN_COMMENT_RE.search(b.code):
            why = "comment: " + BROKEN_COMMENT_RE.search(b.code).group(0)
        elif prose_after and AFTER_BROKEN_RE.search(prose_after[0]):
            why = "prose after: " + AFTER_BROKEN_RE.search(prose_after[0]).group(0)
        b.intentional = why
        blocks.append(b)
    return blocks


PRE_RE = re.compile(r'<pre\s+class="code"[^>]*>(.*?)</pre>', re.S)
CONSOLE_RE = re.compile(r'<div\s+class="console-out"[^>]*>(.*?)</div>', re.S)


def html_to_text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).replace("\xa0", " ")


def extract_deck(path: str, text: str, default_lang: str) -> list[Block]:
    blocks = []
    pres = list(PRE_RE.finditer(text))
    for n, m in enumerate(pres):
        code = html_to_text(m.group(1))
        line = text.count("\n", 0, m.start()) + 1
        lang = default_lang or ("java" if re.search(r"System\.out|public\s+class|\bint\s+\w", code) else "js")
        b = Block(path, len(blocks) + 1, line, lang, "deck", code)
        sec_end = text.find("</section>", m.end())
        sec_end = len(text) if sec_end < 0 else sec_end
        nxt = pres[n + 1].start() if n + 1 < len(pres) else len(text)
        window = text[m.end():min(sec_end, nxt)]
        sec_start = text.rfind("<section", 0, m.start())
        h = re.search(r"<h2[^>]*>(.*?)</h2>", text[sec_start:m.start()], re.S) if sec_start >= 0 else None
        b.context = html_to_text(h.group(1)).strip() if h else ""
        c = CONSOLE_RE.search(window)
        if c:
            if "err-line" in c.group(1):
                b.intentional = "deck err-line output"
            else:
                typed = [html_to_text(t) for t in re.findall(r'<span\s+class="user-typed"[^>]*>(.*?)</span>', c.group(1), re.S)]
                if typed:
                    b.stdin = "\n".join(typed) + "\n"
                b.expected.append(("console-out", html_to_text(c.group(1)), None))
        if not b.intentional:
            ctx = b.context + " " + html_to_text(window[:400])
            if BROKEN_COMMENT_RE.search(code):
                b.intentional = "comment: " + BROKEN_COMMENT_RE.search(code).group(0)
            elif re.search(r"\b(bugs?|broken|wrong|errors?|crash|fix|mistakes?|spot|compile)\b", b.context, re.I):
                b.intentional = "slide title: " + b.context
            elif re.search(r'class="badge bad', window[:300]):
                b.intentional = "bad badge"
            _ = ctx
        blocks.append(b)
    return blocks


def looks_like_java(text: str) -> bool:
    return bool(re.search(r"\b(?:public\s+)?class\s+\w+\s*\{|System\.out\.|;\s*$", text, re.M))


def pair_sheet_runs(path: str, blocks: list[Block]):
    """For X_KEY.md, attach sample runs from X.md under the heading naming ClassName.java."""
    if not path.endswith("_KEY.md"):
        return
    sheet = path[:-len("_KEY.md")] + ".md"
    if not os.path.isfile(sheet):
        return
    lines = read_text(sheet).splitlines()
    fences = parse_md_fences(lines)
    for b in blocks:
        if b.lang != "java":
            continue
        cls = main_class_name(b.code)
        if not cls:
            continue
        hidx = next((i for i, ln in enumerate(lines) if ln.startswith("#") and f"{cls}.java" in ln), None)
        if hidx is None:
            continue
        level = len(lines[hidx]) - len(lines[hidx].lstrip("#"))
        end = next((i for i in range(hidx + 1, len(lines)) if lines[i].startswith("#")
                    and len(lines[i]) - len(lines[i].lstrip("#")) <= level), len(lines))
        for s, e, lang in fences:
            if hidx < s < end and lang in OUTPUT_LANGS:
                body = fence_body(lines, s, e)
                if looks_like_java(body):
                    continue        # the broken program handed to students, not a sample run
                b.sheet_runs.append((f"{os.path.basename(sheet)} line {s + 1}", body))

# ---------------------------------------------------------------- unit tests

TEST_Q_HEAD = re.compile(r"^(?:\*\*|#{2,4}\s+)B(\d+)\.|^(\d+)\.\s")
TRACE_Q = re.compile(r"\b(?:output|outputs|print|prints|printed|trace|display|displays)\b", re.I)
FRAG_LABEL = re.compile(r"\b(Fragment|Segment|Snippet|Code|Program|Part)\s+([A-Z0-9]{1,2})\b|^\(?([a-h])\)(?:\s|$)", re.I)
GIVEN = re.compile(r"`\s*([A-Za-z_]\w*)\s*=\s*([^`=;][^`;]*?)\s*;?\s*`")
KEY_LETTER = re.compile(r"(?:^|·)\s*(\d+)\.\s*\*\*([A-D])\*\*", re.M)


def _key_letters(key: str) -> dict:
    out = {}
    for line in key.splitlines():
        if line.lstrip().startswith("|"):
            cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
            for k in range(len(cells) - 1):
                if cells[k].isdigit() and re.fullmatch(r"[A-D]", cells[k + 1]):
                    out.setdefault(int(cells[k]), cells[k + 1])
    for m in KEY_LETTER.finditer(key):
        out.setdefault(int(m.group(1)), m.group(2))
    return out


def _key_section(klines: list[str], qid: str):
    """Lines of test_KEY.md under the heading for question qid ('B1', or '21' for numbered Part B)."""
    n = qid[1:] if qid.startswith("B") else qid
    head = re.compile(r"^(?:#+\s*|\*\*)(?:B|Q)?%s[.:)\s*]" % re.escape(n))
    start = next((i for i, ln in enumerate(klines) if head.match(ln)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(klines)) if klines[i].startswith("#")
                or re.match(r"^\*\*(?:B|Q)?\d+[.:)]", klines[i])), len(klines))
    return klines[start:end]


NOT_OUTPUT = re.compile(r"\b(?:no output|nothing|compile|error|both|infinite|crash|exception|because|never)\b", re.I)


def _option_output(rest: str):
    """A Part A option as program output: backticked code, or a plain word or phrase
    that does not describe the run instead of showing it."""
    if rest.startswith("`"):
        return _inline_output(rest)
    if rest and not NOT_OUTPUT.search(rest) and not re.search(r"[*_]", rest):
        return rest
    return None


def _label_patterns(label):
    """Regexes for a fragment label in the key: its full form ("Fragment A"), then the bare
    id at the start of a line ("- **A:", "a)", "(a)")."""
    word, ident = label
    pats = []
    if word:
        pats.append(re.compile(r"\b%s\s+%s\b\s*(?:\*\*)?\s*[:.)]?\s*(?:\*\*)?" % (re.escape(word), re.escape(ident)), re.I))
    pats.append(re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?\(?%s[:.)]\s*(?:\*\*)?" % re.escape(ident)))
    return pats


def _answer_in_section(sec: list[str], label):
    """The expected output in a key section: after the label, else an Output line, else an output fence."""
    fences = parse_md_fences(sec)
    if label:
        for pat in _label_patterns(label):
            for i, ln in enumerate(sec):
                m = pat.search(ln)
                if not m:
                    continue
                tail = re.sub(r"^\s*(?:output\s*:?\s*)?", "", ln[m.end():], flags=re.I)
                got = _inline_output(tail)
                if got is not None:
                    return got
                f = next((f for f in fences if f[0] > i and f[2] in OUTPUT_LANGS), None)
                if f and f[0] - i <= 3 and not any(pat.search(x) for x in sec[i + 1:f[0]]):
                    return fence_body(sec, f[0], f[1])
        return None
    for ln in sec:
        m = re.search(r"\b(?:final\s+)?output\b[^`\n]{0,20}?((?:`[^`\n]+`)(?:\s*(?:/|,\s*then|then)\s*`[^`\n]+`)*)", ln, re.I)
        if m:
            return "\n".join(_backtick_items(m.group(1)))
    for s0, e0, lang in fences:
        if lang in OUTPUT_LANGS:
            body = fence_body(sec, s0, e0)
            if not looks_like_java(body):
                return body
    return None


def pair_test_answers(path: str, text: str, blocks: list[Block]):
    """For a unit test.md, attach each output question's answer from test_KEY.md (see the module docstring)."""
    if os.path.basename(path) != "test.md":
        return
    keyp = os.path.join(os.path.dirname(path), "test_KEY.md")
    if not os.path.isfile(keyp):
        return
    key = read_text(keyp)
    klines = key.splitlines()
    letters = _key_letters(key)
    lines = text.splitlines()
    part, heads = None, []          # (line index, qid, part)
    for i, ln in enumerate(lines):
        m = re.match(r"^## Part ([AB])\b", ln)
        if m:
            part = m.group(1)
            continue
        m = TEST_Q_HEAD.match(ln)
        if m and part:
            num = m.group(1) or m.group(2)
            heads.append((i, ("B" + num) if (m.group(1) or part == "B") else num, part))
    java = [b for b in blocks if b.lang == "java" and not b.intentional]
    per_q: dict = {}
    for b in java:
        q = next((h for h in reversed(heads) if h[0] < b.line - 1), None)
        if q:
            per_q.setdefault(q, []).append(b)
    for (qi, qid, part), qblocks in per_q.items():
        for b in qblocks:
            prose = "\n".join(lines[qi:b.line - 1])
            qtext = lines[qi]
            if not TRACE_Q.search(qtext if part == "B" else prose):
                continue
            givens = [(n, v) for n, v in GIVEN.findall(prose)
                      if not re.search(r"\b(?:[A-Z]\w*|int|double|long|float|char|boolean|byte|short|var)(?:\[\])*\s+%s\b" % n, b.code)]
            b.prelude = "\n".join("var %s = %s;" % (n, v.strip()) for n, v in givens)
            got = None
            if part == "A":
                letter = letters.get(int(qid))
                end = next((h[0] for h in heads if h[0] > qi), len(lines))
                opt = next((ln for ln in lines[b.line:end] if re.match(r"^\s+[-*]\s+%s\.\s" % letter, ln)), None) if letter else None
                if opt:
                    got = _option_output(re.sub(r"^\s+[-*]\s+[A-D]\.\s+", "", opt).strip())
                where = "test_KEY.md question %s (%s)" % (qid, letter)
            else:
                sec = _key_section(klines, qid)
                before = _prose_before(lines, b.line - 1)
                lm = FRAG_LABEL.search(before) if before != qtext.strip() else None
                label = ((lm.group(1), lm.group(2)) if lm.group(1) else (None, lm.group(3))) if lm else None
                if label is None and len(qblocks) > 1:
                    b.unpaired = "test question %s: %d fragments and no label (Fragment A, Segment 1) to pair them with the key" % (qid, len(qblocks))
                    continue
                got = _answer_in_section(sec, label) if sec else None
                where = "test_KEY.md %s%s" % (qid, (" " + label[1]) if label else "")
            if got is None:
                b.unpaired = "test question %s: no answer found in test_KEY.md" % qid
            else:
                b.expected.append((where, got, None))


# ---------------------------------------------------------------- java analysis

TYPE_DECL_RE = re.compile(
    r"^[ \t]*(?:@\w+(?:\([^)]*\))?\s+)*((?:public|protected|private|abstract|final|static|sealed|non-sealed|strictfp)\s+)*"
    r"(class|interface|enum|record)\s+([A-Za-z_]\w*)", re.M)
MAIN_RE = re.compile(r"\bstatic\s+(?:final\s+)?void\s+main\s*\(\s*(?:final\s+)?String\s*(?:\[\s*\]|\.\.\.)\s*\w*\s*(?:\[\s*\])?\s*\)"
                     r"|\bvoid\s+main\s*\(\s*String\s*\[\s*\]\s*\w+\s*\)")


@dataclass
class JavaUnit:
    header: str               # package + imports
    package: str
    types: list               # list of (name, source, is_public, has_main)
    stray: str                # depth-0 text outside types (snippet code)


def split_java(code: str) -> JavaUnit:
    blank = blank_java(code)
    header_lines, pkg = [], ""
    for m in re.finditer(r"^\s*(package\s+[\w.]+\s*;|import\s+(?:static\s+)?[\w.*]+\s*;)", blank, re.M):
        header_lines.append(code[m.start(1):m.end(1)])
        pm = re.match(r"package\s+([\w.]+)", code[m.start(1):m.end(1)])
        if pm:
            pkg = pm.group(1)
    types, stray = [], []
    depth, i, n = 0, 0, len(blank)
    last = 0
    while i < n:
        if depth == 0:
            m = TYPE_DECL_RE.match(blank, i) if (i == 0 or blank[i - 1] == "\n") else None
            if m:
                j = blank.find("{", m.end())
                if j < 0:
                    break
                d, k = 0, j
                while k < n:
                    if blank[k] == "{":
                        d += 1
                    elif blank[k] == "}":
                        d -= 1
                        if d == 0:
                            break
                    k += 1
                stray.append(blank[last:i])
                src = code[i:k + 1]
                mods = m.group(1) or ""
                full_mods = blank[m.start():m.start(2)]
                types.append((m.group(3), src, "public" in full_mods or "public" in mods,
                              bool(MAIN_RE.search(blank[i:k + 1]))))
                i = k + 1
                last = i
                continue
            if blank[i] == "{":
                depth += 1
        else:
            if blank[i] == "{":
                depth += 1
            elif blank[i] == "}":
                depth -= 1
        i += 1
    stray.append(blank[last:])
    rest = "".join(stray)
    rest = re.sub(r"^\s*(package|import)\s+[^;]*;", "", rest, flags=re.M)
    return JavaUnit("\n".join(header_lines), pkg, types, rest.strip())


def main_class_name(code: str) -> str | None:
    u = split_java(code)
    mains = [t for t in u.types if t[3]]
    if not mains:
        return None
    pub = [t for t in mains if t[2]]
    return (pub or mains)[0][0]


def has_placeholder(code: str) -> bool:
    b = blank_java(code)
    b = re.sub(r"\w\s*\.\.\.\s*\w", "", b)            # varargs
    return bool(re.search(r"\.\.\.|…|\?\?\?|<[a-z][^>]*>(?!\s*\()", b)) and bool(re.search(r"\.\.\.|…|\?\?\?", b))


def referenced_names(code: str) -> set[str]:
    return set(re.findall(r"\b([A-Z]\w*)\b", blank_java(code)))


class TypeIndex:
    """Top-level Java types declared in program blocks, by file."""

    def __init__(self):
        self.cache: dict[str, list] = {}

    def types_in(self, path: str, blocks: list[Block] | None = None) -> list:
        if path in self.cache:
            return self.cache[path]
        if blocks is None:
            try:
                text = read_text(path)
            except OSError:
                return []
            if path.endswith(".md"):
                blocks = extract_md(path, text, "java")
            elif path.endswith(".java"):
                blocks = [Block(path, 1, 1, "java", "file", text)]
            else:
                blocks = []
        out = []
        for b in blocks:
            if b.lang != "java" or b.intentional:
                continue
            u = split_java(b.code)
            if u.stray:
                continue
            for name, src, pub, hm in u.types:
                out.append((name, src, u.header, b.index, b.line, path))
        self.cache[path] = out
        return out


def resolve_deps(block: Block, unit: JavaUnit, tindex: TypeIndex, file_blocks: list[Block]):
    """Return (extra sources [(name, src, header)], foreign files used)."""
    have = {t[0] for t in unit.types}
    extra, foreign = [], set()
    pending = referenced_names(block.code)
    local = tindex.types_in(block.file, file_blocks)
    folder = os.path.dirname(block.file)
    siblings = None
    seen = set()
    while pending:
        name = pending.pop()
        if name in have or name in seen:
            continue
        seen.add(name)
        cands = [t for t in local if t[0] == name and t[3] != block.index]
        src_file = block.file
        if not cands and block.origin in ("md", "file"):
            if siblings is None:
                siblings = []
                want = ".md" if block.origin == "md" else ".java"
                for fn in sorted(os.listdir(folder)):
                    fp = os.path.join(folder, fn)
                    if fn.endswith(want) and fp != block.file:
                        siblings.extend(tindex.types_in(fp))
            cands = [t for t in siblings if t[0] == name]
            if cands:
                src_file = cands[0][5]
        if not cands:
            continue
        best = min(cands, key=lambda t: abs(t[4] - block.line) if t[5] == block.file else 0)
        extra.append((best[0], best[1], best[2]))
        if src_file != block.file:
            foreign.add(os.path.basename(src_file))
        have.add(name)
        pending |= referenced_names(best[1])
    return extra, sorted(foreign)


def data_files_for(block: Block, file_text: str | None) -> dict[str, str]:
    """Text files the code opens: from a fence after a line naming the file, or from disk next to the doc."""
    names = set(re.findall(r'"([\w./-]+\.(?:txt|csv|dat))"', block.code))
    out = {}
    if not names:
        return out
    lines = file_text.splitlines() if file_text else []
    fences = parse_md_fences(lines) if lines else []
    for name in names:
        base = os.path.basename(name)
        for s, e, lang in fences:
            if lang in OUTPUT_LANGS and base in _prose_before(lines, s, 2):
                out[name] = fence_body(lines, s, e) + "\n"
                break
        if name not in out:
            for cand in (os.path.join(os.path.dirname(block.file), base),):
                if os.path.isfile(cand):
                    out[name] = read_text(cand)
    return out


HARNESS = r"""
import java.io.*;
import java.lang.reflect.*;
public class GlaEchoHarness {
    public static void main(String[] a) throws Throwable {
        final byte[] data = System.in.readAllBytes();
        final PrintStream out = System.out;
        System.setIn(new InputStream() {
            int pos = 0;
            public int read() {
                if (pos >= data.length) return -1;
                int b = data[pos++] & 0xff; out.write(b); out.flush(); return b;
            }
            public int read(byte[] buf, int off, int len) {
                if (len == 0) return 0;
                if (pos >= data.length) return -1;
                int end = pos;
                while (end < data.length && end - pos < len) { end++; if (data[end - 1] == '\n') break; }
                int n = end - pos;
                System.arraycopy(data, pos, buf, off, n);
                out.write(data, pos, n); out.flush();
                pos = end;
                return n;
            }
            public int available() { return 0; }
        });
        Method m = Class.forName(a[0]).getMethod("main", String[].class);
        try { m.invoke(null, (Object) new String[0]); }
        catch (InvocationTargetException e) { throw e.getCause(); }
    }
}
"""


def write_sources(d: str, unit: JavaUnit, extra) -> list[str]:
    paths = []
    written = set()
    for name, src, pub, hm in unit.types:
        if name in written:
            continue
        written.add(name)
        p = os.path.join(d, name + ".java")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(unit.header + "\n" + src + "\n")
        paths.append(p)
    for name, src, header in extra:
        if name in written:
            continue
        written.add(name)
        p = os.path.join(d, name + ".java")
        hdr = "\n".join(h for h in header.splitlines() if not h.startswith("package")) if not unit.package else header
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(hdr + "\n" + src + "\n")
        paths.append(p)
    return paths


def compile_errors_summary(stderr: str, tmp: str) -> str:
    stderr = stderr.replace(tmp + os.sep, "")
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    errs = [ln for ln in lines if ": error:" in ln]
    head = errs[:3] if errs else lines[:3]
    more = f" (+{len(errs) - 3} more)" if len(errs) > 3 else ""
    return "; ".join(h.strip() for h in head) + more


def missing_classes(stderr: str) -> set[str]:
    return set(re.findall(r"symbol:\s+class\s+(\w+)", stderr))


def only_missing_symbol_errors(stderr: str) -> bool:
    errs = re.findall(r": error: (.*)", stderr)
    return bool(errs) and all(e.startswith("cannot find symbol") or e.startswith("package ") for e in errs)


def run_java(block: Block, file_blocks: list[Block], tindex: TypeIndex, file_text: str | None) -> Result:
    r = Result(block.index, block.line, "java", "", intentional=block.intentional)
    if not (shutil.which("javac") and shutil.which("java")):
        r.status, r.detail = "not_runnable", "javac or java not found on PATH"
        return r
    code = block.code
    unit = split_java(code)
    wrapped = False
    if unit.stray:
        if unit.types:
            r.status, r.detail = "not_runnable", "mixes declarations and loose code"
            return r
        if has_placeholder(code):
            r.status, r.detail = "not_runnable", "snippet with a placeholder"
            return r
        is_statements = not re.search(
            r"^\s*(?:(?:public|private|protected|static|final|abstract)\s+)+[\w<>\[\]]+\s+\w+\s*\(|"
            r"^\s*[\w<>\[\]]+\s+[a-z]\w*\s*\([^)]*\)\s*\{", blank_java(code), re.M)
        if not ((block.expected or block.sheet_runs) and is_statements):
            r.status = "not_runnable"
            r.detail = block.unpaired or ("snippet (no class with main)" if is_statements else "method or member snippet (no class)")
            return r
        wrapped = True
        imports = "import java.util.*;\nimport java.io.*;\n"
        body = (block.prelude + "\n" + code) if block.prelude else code
        # Deck snippets read from the conventional `input` Scanner without declaring it.
        mi = re.search(r"\b(\w+)\.(?:next\w*|hasNext\w*)\s*\(", blank_java(code))
        if mi and not re.search(r"\bScanner\s+" + mi.group(1) + r"\b", code):
            body = f"Scanner {mi.group(1)} = new Scanner(System.in);\n" + body
        code = imports + "public class GlaSnippet {\n    public static void main(String[] args) throws Exception {\n" + \
            "\n".join("        " + ln for ln in body.splitlines()) + "\n    }\n}\n"
        unit = split_java(code)
    if not unit.types:
        r.status, r.detail = "not_runnable", "no type declaration"
        return r
    if has_placeholder(block.code):
        r.status, r.detail = "not_runnable", "code with a placeholder"
        return r
    extra, foreign = ([], []) if wrapped else resolve_deps(block, unit, tindex, file_blocks)
    main_cls = None
    mains = [t for t in unit.types if t[3]]
    if mains:
        main_cls = ([t for t in mains if t[2]] or mains)[0][0]
    tmp = tempfile.mkdtemp(prefix="gla_samples_")
    try:
        src_dir = os.path.join(tmp, "src")
        out_dir = os.path.join(tmp, "out")
        run_dir = os.path.join(tmp, "run")
        for d in (src_dir, out_dir, run_dir):
            os.makedirs(d)
        paths = write_sources(src_dir, unit, extra)
        needs_input = bool(STDIN_RE.search(blank_java(code)))
        runs = []                       # (label, expected, stdin, stdin recovered from a transcript)
        for label, exp, sin in block.expected:
            runs.append((label, exp, sin or block.stdin, False))
        if needs_input:
            for label, transcript in block.sheet_runs:
                for k, (part, inp) in enumerate(split_transcript(transcript, code)):
                    if inp is not None:
                        runs.append((label + (f" run {k + 1}" if k else ""), part, inp, True))
            fixed = []
            for l, e, sn, dv in runs:
                if sn is None:
                    sn, dv = derive_inputs(e, code), True
                fixed.append((l, e, sn, dv))
            runs = fixed
        elif block.sheet_runs:
            runs.extend((label, t, None, False) for label, t in block.sheet_runs)
        harness_needed = needs_input and (any(r_[2] for r_ in runs) or block.stdin)
        if harness_needed:
            hp = os.path.join(src_dir, "GlaEchoHarness.java")
            with open(hp, "w") as fh:
                fh.write(HARNESS)
            paths.append(hp)
        try:
            cp = subprocess.run(["javac", "-encoding", "UTF-8", "-nowarn", "-d", out_dir] + paths,
                                capture_output=True, text=True, timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            r.status, r.detail = "compile_error", "javac timed out"
            return r
        if cp.returncode != 0:
            miss = missing_classes(cp.stderr)
            if only_missing_symbol_errors(cp.stderr) and miss and not wrapped:
                r.status = "not_runnable"
                r.detail = "depends on " + ", ".join(sorted(miss)) + " (not declared in this file or folder)"
                return r
            if wrapped:
                r.status = "not_runnable"
                r.detail = "snippet with shown output does not compile on its own: " + \
                    compile_errors_summary(cp.stderr, src_dir)
                return r
            r.status = "compile_error"
            r.detail = compile_errors_summary(cp.stderr, src_dir)
            if foreign:
                r.detail += f" [compiled with classes from {', '.join(foreign)}]"
            return r
        if not main_cls:
            r.status, r.detail = "compiled", "no main(), compiled only"
            return r
        stubs = [n for n, src_, _ in extra if re.search(r"//\s*TODO", src_)]
        if re.search(r"//\s*TODO", code) or stubs:
            r.status = "compiled"
            r.detail = "starter code with TODO stubs" + (f" ({', '.join(stubs)})" if stubs else "") + ", compiled only"
            return r
        if needs_input and not any(r_[2] for r_ in runs) and not block.stdin:
            r.status, r.detail = "compiled", "reads System.in and the file shows no input, compiled only"
            return r
        for name, content in data_files_for(block, file_text).items():
            p = os.path.join(run_dir, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)
        qual = (unit.package + "." if unit.package else "") + main_cls
        if not runs:
            runs = [("", None, block.stdin, False)]
        nondet = bool(NONDET_RE.search(blank_java(code))) or any(NONDET_RE.search(e[1]) for e in extra)
        mism, details = [], []
        for label, exp, sin, derived in runs:
            cmd = ["java", "-Xshare:auto", "-XX:TieredStopAtLevel=1", "-cp", out_dir]
            cmd += ["GlaEchoHarness", qual] if (needs_input and sin) else [qual]
            try:
                pr = subprocess.run(cmd, input=sin or "", capture_output=True, text=True,
                                    timeout=RUN_TIMEOUT, cwd=run_dir)
            except subprocess.TimeoutExpired:
                r.status, r.detail = "runtime_error", f"timed out after {RUN_TIMEOUT}s" + (f" ({label})" if label else "")
                return r
            if pr.returncode != 0 and derived and "NoSuchElementException" in pr.stderr:
                r.status = "not_runnable"
                r.detail = f"[{label}] typed input recovered from the transcript ran out (prompt not matched)"
                return r
            if pr.returncode != 0:
                err = [ln for ln in pr.stderr.splitlines() if ln.strip() and not ln.startswith("\tat ")]
                r.status = "runtime_error"
                r.detail = (f"[{label}] " if label else "") + "exit " + str(pr.returncode) + ": " + " | ".join(err[:2])
                if exp is not None and not nondet and not outputs_match(exp, pr.stdout):
                    r.diff = short_diff(exp, pr.stdout)
                return r
            if exp is None:
                continue
            if nondet:
                details.append(f"{label}: nondeterministic, not compared")
                continue
            if outputs_match(exp, pr.stdout):
                details.append(f"{label}: matched")
                continue
            if sin and needs_input:
                # Also accept output shown without the typed input echoed.
                plain = subprocess.run(["java", "-cp", out_dir, qual], input=sin, capture_output=True,
                                       text=True, timeout=RUN_TIMEOUT, cwd=run_dir)
                if outputs_match(exp, plain.stdout):
                    details.append(f"{label}: matched (input not echoed)")
                    continue
            mism.append((label, short_diff(exp, pr.stdout)))
        if mism:
            r.status = "mismatch"
            r.detail = "; ".join(m[0] for m in mism)
            r.diff = "\n".join(f"[{l}]\n{d}" for l, d in mism)
        else:
            r.status = "passed"
            r.detail = "; ".join(details) or ("ran, no output shown" + (" (with shown input)" if block.stdin else ""))
            if wrapped:
                r.detail = "wrapped snippet; " + r.detail
        return r
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def prompt_patterns(code: str) -> list[re.Pattern]:
    """Regexes for the prompts a program prints with System.out.print (not println).

    A prompt built by concatenation, such as "Enter amount from class " + count + ": ",
    becomes  Enter amount from class .*?:  so it still matches the transcript line.
    """
    blank = blank_java(code)
    pats = []
    for m in re.finditer(r"System\.out\.print\s*\(", blank):
        i, d = m.end(), 1
        while i < len(blank) and d:
            d += {"(": 1, ")": -1}.get(blank[i], 0)
            i += 1
        arg = code[m.end():i - 1]
        pieces = re.split(r'("(?:[^"\\\n]|\\.)*")', arg)
        rx, lit_total = "", ""
        for k, pc in enumerate(pieces):
            if k % 2 == 1:
                try:
                    lit = json.loads(pc)
                except ValueError:
                    lit = pc[1:-1]
                if "\n" in lit:
                    rx = None
                    break
                rx += re.escape(lit)
                lit_total += lit
            elif pc.strip().strip("+").strip():
                rx += ".*?"
        if rx and lit_total.strip():
            # the typed text follows the prompt; tolerate the prompt's trailing space being trimmed
            pats.append(re.compile("^" + rx.rstrip("\\ ") + r"\s*(?=\S)"))
    return pats


def derive_inputs(transcript: str, code: str) -> str | None:
    pats = prompt_patterns(code)
    if not pats:
        return None
    vals = []
    for ln in transcript.splitlines():
        best = None
        for p in pats:
            m = p.match(ln)
            if m and (best is None or m.end() > best):
                best = m.end()
        if best is not None:
            vals.append(ln[best:].strip())
    return ("\n".join(vals) + "\n") if vals else None


def split_transcript(transcript: str, code: str):
    """Split a fence holding several sample runs (blank line, then the first prompt again)."""
    pats = prompt_patterns(code)
    lines = transcript.splitlines()
    first = next((p for ln in lines for p in pats if p.match(ln)), None)
    if first is None:
        return [(transcript, None)]
    parts, cur = [], []
    for k, ln in enumerate(lines):
        if cur and first.match(ln) and k > 0 and not lines[k - 1].strip():
            parts.append("\n".join(cur))
            cur = []
        cur.append(ln)
    parts.append("\n".join(cur))
    return [(p, derive_inputs(p, code)) for p in parts]


# ---------------------------------------------------------------- js

def check_js(block: Block) -> Result:
    r = Result(block.index, block.line, "js", "", intentional=block.intentional)
    if not shutil.which("node"):
        r.status, r.detail = "not_runnable", "node not found on PATH"
        return r
    if re.search(r"(?<![\w.])\.\.\.(?![\w\[({])|…", blank_java(block.code)):
        r.status, r.detail = "not_runnable", "snippet with a placeholder"
        return r
    if re.match(r"\s*<", block.code):
        r.status, r.detail = "not_runnable", "HTML markup, not JavaScript"
        return r
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(block.code)
        p = fh.name
    try:
        pr = subprocess.run(["node", "--check", p], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        r.status, r.detail = "syntax_error", "node --check timed out"
        return r
    finally:
        os.unlink(p)
    if pr.returncode == 0:
        r.status, r.detail = "passed", "node --check ok (syntax only)"
    else:
        msg = [ln for ln in pr.stderr.splitlines() if ln.strip()]
        err = next((ln for ln in msg if "Error" in ln), msg[-1] if msg else "syntax error")
        where = next((ln for ln in msg if p in ln), "")
        lm = re.search(r":(\d+)", where)
        r.status = "syntax_error"
        r.detail = err.strip() + (f" (code line {lm.group(1)})" if lm else "")
        code_only = blank_java(block.code).strip()
        if "Unexpected end of input" in err and "{" not in code_only and code_only.endswith(")"):
            r.status, r.detail = "not_runnable", "statement header fragment (no body)"
    return r


# ---------------------------------------------------------------- calc blocks

CALC_FUNCS = {n: getattr(math, n) for n in ("sqrt", "log", "log10", "log2", "exp", "sin", "cos", "tan",
                                             "asin", "acos", "atan", "radians", "degrees", "floor", "ceil")}
CALC_FUNCS.update({"abs": abs, "round": round})
CALC_NAMES = {"pi": math.pi, "e": math.e}


def calc_eval(text: str) -> float:
    """The value of an arithmetic expression: numbers, + - * / // % **, brackets,
    pi, e and the math functions above. Anything else raises ValueError."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.BinOp):
            ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
                   ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
            if type(n.op) in ops:
                return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Name) and n.id in CALC_NAMES:
            return CALC_NAMES[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in CALC_FUNCS and not n.keywords:
            return CALC_FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError("not arithmetic: %s" % ast.dump(n)[:60])
    t = text.replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-")
    try:
        return float(ev(ast.parse(t.strip(), mode="eval")))
    except (SyntaxError, ZeroDivisionError, OverflowError, TypeError) as exc:
        raise ValueError(str(exc)) from exc


def check_calc(block: Block) -> Result:
    """Each line `expression = answer` (a `# note` may follow) must hold: the answer
    may be rounded to the decimal places it shows, and may end in %."""
    r = Result(block.index, block.line, "calc", "passed")
    bad, n = [], 0
    for k, raw in enumerate(block.code.splitlines(), 1):
        ln = raw.split(" #", 1)[0].strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^(.*?[^=<>!])=([^=].*)$", ln)
        if not m:
            bad.append("line %d has no `= answer`: %s" % (k, ln))
            continue
        n += 1
        expr, ans = m.group(1).strip(), m.group(2).strip().rstrip("%").strip()
        try:
            got, want = calc_eval(expr), calc_eval(ans)
        except ValueError as exc:
            bad.append("line %d: %s (%s)" % (k, ln, exc))
            continue
        dm = re.search(r"\.(\d+)\s*$", ans)
        tol = 0.5 * 10 ** -(len(dm.group(1)) if dm else 0) if re.fullmatch(r"[-+]?\d+(\.\d+)?", ans) else 1e-9
        if abs(got - want) > tol + 1e-9 * max(1.0, abs(want)):
            bad.append("line %d: %s, but the expression is %.6g" % (k, ln, got))
    if bad:
        r.status, r.detail = "mismatch", "; ".join(bad)
    else:
        r.detail = "%d calculation(s) checked" % n
    return r


# ---------------------------------------------------------------- driver

FAIL_STATUSES = {"mismatch", "compile_error", "syntax_error"}


def collect(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        if os.path.isdir(p):
            for dp, dns, fns in os.walk(p):
                dns[:] = sorted(d for d in dns if not d.startswith("."))
                for fn in sorted(fns):
                    if fn.endswith((".md", ".java", ".js")) or re.match(r"D\d+.*_Slides_.*\.html$", fn) \
                            or (fn.endswith(".html") and "Slides" in fn):
                        out.append(os.path.join(dp, fn))
        elif os.path.isfile(p):
            out.append(p)
        else:
            print(f"warning: no such path {p}", file=sys.stderr)
    return out


def blocks_for(path: str, text: str, lang: str) -> list[Block]:
    if path.endswith(".md"):
        bl = extract_md(path, text, lang)
        pair_sheet_runs(path, bl)
        pair_test_answers(path, text, bl)
        return bl
    if path.endswith(".html"):
        return extract_deck(path, text, lang)
    if path.endswith(".java"):
        return [Block(path, 1, 1, "java", "file", text)]
    if path.endswith(".js"):
        return [Block(path, 1, 1, "js", "file", text)]
    return []


def process_file(path: str, root_override: str | None, feat_cache: dict, tindex: TypeIndex, jobs: int) -> dict:
    root = root_override or find_course_root(path)
    lang = course_language(root)
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError) as exc:
        return {"file": path, "error": str(exc), "blocks": []}
    blocks = blocks_for(path, text, lang)
    rep = {"file": path, "slot": "", "blocks": [], "feature_note": ""}
    if not blocks:
        return rep
    slot, slot_text = file_slot(path, text)
    rep["slot"] = slot_text
    key = (root, lang)
    if key not in feat_cache:
        feat_cache[key] = {l: load_features(root, l) for l in ("java", "js")}

    def one(b: Block) -> Result:
        if b.lang == "calc":
            return check_calc(b)
        res = run_java(b, blocks, tindex, text) if b.lang == "java" else check_js(b)
        res.shown_output = bool(b.expected or b.sheet_runs or b.unpaired)
        feats, order, note = feat_cache[key][b.lang]
        res.features = feature_warnings(b.code, b.lang, slot, feats, order)
        if b.intentional and res.status in FAIL_STATUSES | {"runtime_error"}:
            res.detail = f"expected failure ({b.intentional}): {res.status}: {res.detail}"
            res.status = "expected_failure"
        return res

    if jobs > 1 and len(blocks) > 1:
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(one, blocks))
    else:
        results = [one(b) for b in blocks]
    code_blocks = [b for b in blocks if b.lang != "calc"]
    feats, order, note = feat_cache[key][code_blocks[0].lang] if code_blocks else ({}, [], "")
    if not code_blocks:
        pass
    elif not slot or (order and slot[0] not in order):
        rep["feature_note"] = "feature check skipped: slot " + (f"'{slot_text}'" if slot_text else "unknown") + \
            " is not ordered by the course table"
    elif note:
        rep["feature_note"] = "feature check skipped: " + note
    rep["blocks"] = [asdict(r) for r in results]
    return rep


def summarize(rep: dict) -> dict:
    bl = rep["blocks"]
    s = {
        "found": len(bl),
        "run": sum(1 for b in bl if b["status"] in ("passed", "mismatch", "runtime_error", "syntax_error")),
        "passed": sum(1 for b in bl if b["status"] == "passed"),
        "mismatched": sum(1 for b in bl if b["status"] == "mismatch"),
        "compile_errors": sum(1 for b in bl if b["status"] in ("compile_error", "syntax_error")),
        "runtime_errors": sum(1 for b in bl if b["status"] == "runtime_error"),
        "compiled_only": sum(1 for b in bl if b["status"] == "compiled"),
        "not_runnable": sum(1 for b in bl if b["status"] == "not_runnable"),
        "expected_failures": sum(1 for b in bl if b["status"] == "expected_failure"),
        "shown_output_unverified": sum(1 for b in bl if b["shown_output"] and b["status"] in ("not_runnable", "compiled")),
        "feature_warnings": sum(len(b["features"]) for b in bl),
    }
    return s


def print_report(reports: list[dict], verbose: bool, base: str | None):
    total = {}
    for rep in reports:
        if not rep["blocks"]:
            continue
        s = summarize(rep)
        for k, v in s.items():
            total[k] = total.get(k, 0) + v
        total["files"] = total.get("files", 0) + 1
        name = os.path.relpath(rep["file"], base) if base else rep["file"]
        print(f"{name}  [slot {rep['slot'] or '?'}]")
        print("  found {found}, run {run}, passed {passed}, mismatched {mismatched}, compile errors {compile_errors}, "
              "runtime errors {runtime_errors}, compiled only {compiled_only}, not runnable {not_runnable}, "
              "expected failures {expected_failures}, feature warnings {feature_warnings}, "
              "shown output not verified {shown_output_unverified}".format(**s))
        if rep.get("feature_note") and s["found"]:
            print("  " + rep["feature_note"])
        for b in rep["blocks"]:
            show = verbose or b["status"] in FAIL_STATUSES | {"runtime_error"} or b["features"] or \
                (b["shown_output"] and b["status"] in ("not_runnable", "compiled"))
            if not show:
                continue
            note = " [shows output that was not verified]" if b["shown_output"] and b["status"] in ("not_runnable", "compiled") else ""
            print(f"  block {b['index']} (line {b['line']}, {b['lang']}): {b['status']}" + (f", {b['detail']}" if b["detail"] else "") + note)
            if b["diff"]:
                for ln in b["diff"].splitlines():
                    print("      " + ln)
            for f in b["features"]:
                print("      feature warning: " + f)
    if total:
        print("\nTOTAL files {files}: found {found}, run {run}, passed {passed}, mismatched {mismatched}, "
              "compile errors {compile_errors}, runtime errors {runtime_errors}, compiled only {compiled_only}, "
              "not runnable {not_runnable}, expected failures {expected_failures}, "
              "feature warnings {feature_warnings}, shown output not verified {shown_output_unverified}".format(**total))
    else:
        print("no code samples found")
    return total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", metavar="PATH")
    ap.add_argument("--root", help="course root (folder with course.yaml); default: found from each PATH")
    ap.add_argument("--json", action="store_true", help="print a JSON report")
    ap.add_argument("--verbose", "-v", action="store_true", help="list every block, not only problems")
    ap.add_argument("--jobs", "-j", type=int, default=min(8, os.cpu_count() or 2))
    a = ap.parse_args(argv)
    for tool in ("javac", "java", "node"):
        if not shutil.which(tool):
            print(f"warning: {tool} not found on PATH", file=sys.stderr)
    files = collect(a.paths)
    feat_cache: dict = {}
    tindex = TypeIndex()
    reports = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        futs = [ex.submit(process_file, f, a.root, feat_cache, tindex, 1) for f in files]
        reports = [f.result() for f in futs]
    failed = any(b["status"] in FAIL_STATUSES for r in reports for b in r["blocks"])
    if a.json:
        out = {"files": [dict(r, summary=summarize(r)) for r in reports if r["blocks"]]}
        tot = {}
        for r in out["files"]:
            for k, v in r["summary"].items():
                tot[k] = tot.get(k, 0) + v
        out["total"] = tot
        out["failed"] = failed
        json.dump(out, sys.stdout, indent=2)
        print()
    else:
        base = os.path.commonpath([os.path.realpath(p) for p in a.paths]) if a.paths else None
        if base and os.path.isfile(base):
            base = os.path.dirname(base)
        print_report(reports, a.verbose, base)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

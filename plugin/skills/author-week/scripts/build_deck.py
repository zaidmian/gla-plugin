#!/usr/bin/env python3
"""Assemble GLA slide decks from slide fragments and the shared template.

    python3 build_deck.py DECK.html --rebuild          re-assemble an existing deck in place
    python3 build_deck.py DECK.html --from SRC.html    build DECK.html from a fragment file
    python3 build_deck.py DECK.html --extract          print the deck's fragment source
    python3 build_deck.py DECK.html --check            report problems, change nothing

The model writes only slides. The assembler supplies everything the template
protects: the token blocks, the machinery CSS and script, the sidebar with
its chapter indices, the counter, the root theme attribute from course.yaml
deck_theme, and (on request) the title and goals slides from the lesson.

Fragment source format:

    <!-- deck-title: Variables and Data Types · ICS3U -->     optional (default: lesson title + course)
    <style> .my-diagram { ... } </style>                      optional deck-specific CSS
    <!-- chapter: Welcome -->                                 starts a sidebar chapter
    <!-- auto: title -->                                      title slide from the lesson and week plan
    <!-- auto: goals -->                                      goals slide: lesson goals + header codes
    <section class="slide"> ... </section>                    every other slide, as written
    <script> ... </script>                                    optional deck-specific script

Exit 0 written or clean; 1 --check found errors; 2 bad input.
"""
import argparse
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
from gla import course as coursemod  # noqa: E402
from gla import paths  # noqa: E402

TEMPLATE = os.path.join(paths.STANDARDS, "decks", "Slide_Deck_Template.html")
SECTION_RE = re.compile(r"(?:<!--(?:(?!-->).)*-->[ \t]*\n[ \t]*)?<section\b[^>]*class=\"[^\"]*\bslide\b[^\"]*\"[^>]*>.*?</section>", re.S)  # with the comment just above it
CHAPTER_RE = re.compile(r'<div class="chapter" data-slide="(\d+)">(.*?)</div>', re.S)
CODE_RE = re.compile(r'<pre class="code"[^>]*>(.*?)</pre>', re.S)
KICKER_RE = re.compile(r'<div class="kicker">(.*?)</div>', re.S)
CHIP_RE = re.compile(r'<span class="code-chip">([^<]*)</span>')
SLOT_RE = re.compile(r'class="slot-id[^"]*">([^<]*)<')
NEXT_RE = re.compile(r"\b(up next|coming up next|next (week|lesson|class|unit)|in the next (lesson|unit))\b", re.I)
DATE_RE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b")
CODE_LINES_MAX = 6
SLIDES_MIN, SLIDES_MAX = 15, 25


class DeckError(Exception):
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------- CSS
def css_chunks(css):
    """Split CSS into (normalized rule, raw text with its leading comments)."""
    out, pos = [], 0
    for m in re.finditer(r"\}", css):
        raw = css[pos:m.end()]
        pos = m.end()
        body = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
        if "{" in body:
            out.append((re.sub(r"\s+", " ", body).strip(), raw.strip("\n")))
    return out, css[pos:]


def template_parts():
    t = read(TEMPLATE)
    style = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
    script = re.search(r"<script>(.*?)</script>", t, re.S).group(1)
    return t, style, script


# ----------------------------------------------------------------- extract
def extract(deck):
    """A deck as its fragment parts."""
    _, tstyle, tscript = template_parts()
    tnorm = {n for n, _ in css_chunks(tstyle)[0]}
    title = html.unescape(re.search(r"<title>(.*?)</title>", deck, re.S).group(1).strip())
    style = (re.search(r"<style>(.*?)</style>", deck, re.S) or [None, ""])[1]
    extra_css = "\n".join(raw for n, raw in css_chunks(style)[0] if n not in tnorm).strip()
    extra_css = re.sub(r"^/\* =+ DECK STYLES =+ \*/\s*", "", extra_css)
    stage = re.search(r'<main id="stage">(.*?)</main>', deck, re.S)
    if not stage:
        raise DeckError("no <main id=\"stage\"> element")
    slides = SECTION_RE.findall(stage.group(1))
    chapters = [(int(k), html.unescape(re.sub(r"<[^>]+>", "", n)).strip()) for k, n in CHAPTER_RE.findall(deck)]
    label = re.search(r'<div class="deck-label">(.*?)</div>', deck, re.S)
    scripts = [s for s in re.findall(r"<script\b[^>]*>(.*?)</script>", deck, re.S)
               if re.sub(r"\s+", " ", s).strip() != re.sub(r"\s+", " ", tscript).strip()]
    return {"title": title, "extra_css": extra_css, "slides": slides, "chapters": chapters,
            "label": label.group(1).strip() if label else None, "scripts": scripts}


def to_source(parts):
    L = ["<!-- deck-title: %s -->" % parts["title"]]
    if parts.get("label"):
        L.append("<!-- deck-label: %s -->" % parts["label"])
    if parts["extra_css"]:
        L += ["<style>", parts["extra_css"], "</style>"]
    starts = dict(parts["chapters"])
    for k, s in enumerate(parts["slides"]):
        if k in starts:
            L.append("<!-- chapter: %s -->" % starts[k])
        L.append(s)
    for s in parts["scripts"]:
        L += ["<script>", s.strip("\n"), "</script>"]
    return "\n".join(L) + "\n"


def parse_source(src):
    """Fragment source -> parts (auto slides are left as markers for render())."""
    title = re.search(r"<!--\s*deck-title:\s*(.*?)\s*-->", src)
    label = re.search(r"<!--\s*deck-label:\s*(.*?)\s*-->", src)
    css = "\n".join(m.strip("\n") for m in re.findall(r"<style>(.*?)</style>", src, re.S)).strip()
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", src, re.S)
    body = re.sub(r"<style>.*?</style>|<script\b[^>]*>.*?</script>", "", src, flags=re.S)
    token = re.compile(r"<!--\s*chapter:\s*(.*?)\s*-->|<!--\s*auto:\s*(title|goals)\s*-->|" + SECTION_RE.pattern, re.S)
    slides, chapters = [], []
    for m in token.finditer(body):
        if m.group(1) is not None:
            chapters.append((len(slides), m.group(1)))
        elif m.group(2):
            slides.append({"auto": m.group(2)})
        else:
            slides.append(m.group(0))
    if not slides:
        raise DeckError("the source has no slides")
    return {"title": title.group(1) if title else None, "label": label.group(1) if label else None,
            "extra_css": css, "slides": slides, "chapters": chapters, "scripts": scripts}


# ------------------------------------------------------------------ context
def lesson_for(deck_path):
    m = re.match(r"^(D\d+)_Slides_(.+)\.html$", os.path.basename(deck_path))
    if not m:
        return None
    p = os.path.join(os.path.dirname(deck_path), "%s_Lesson_%s.md" % (m.group(1), m.group(2)))
    return p if os.path.exists(p) else None


def context(deck_path):
    root = coursemod.find_root(os.path.dirname(os.path.abspath(deck_path)))
    cfg = coursemod.load(root) if root else {}
    ctx = {"code": cfg.get("code", ""), "theme": cfg.get("deck_theme", "glass"), "lesson": None, "slot": "",
           "topic": "", "codes": [], "goals": [], "slides": coursemod.switch(cfg, "deck_slides")}
    lp = lesson_for(deck_path)
    if lp:
        t = read(lp)
        ctx["lesson"] = lp
        h1 = re.search(r"^# (.+)$", t, re.M)
        ctx["topic"] = re.sub(r"^(Day \d+|D\d+)\s*[:,-]\s*", "", h1.group(1)).strip() if h1 else ""
        slot = re.search(r"^\*\*Slot:\*\*\s*([A-Z][\w.]*\.D\d+)", t, re.M)
        ctx["slot"] = slot.group(1) if slot else ""
        exp = re.search(r"^\*\*Expectations:\*\*(.*)$", t, re.M)
        ctx["codes"] = re.findall(r"\b[A-Z]\d+\.\d+\b", exp.group(1)) if exp else []
        sec = re.search(r"^## Learning goals.*?\n(.*?)(?=^## )", t, re.M | re.S | re.I)
        if sec:
            ctx["goals"] = [re.sub(r"^\s*[-*]\s+|\*\*", "", l).strip() for l in sec.group(1).splitlines()
                            if re.match(r"^\s*[-*]\s+", l) and not re.match(r"^\s*[-*]\s+\*\*Success", l)][:3]
    return ctx


def auto_slide(kind, ctx):
    e = html.escape
    if kind == "title":
        return ('<section class="slide">\n    <div class="kicker">%s · Gibraltar Leadership Academy</div>\n'
                '    <h1>%s</h1>\n    <div class="slot-id mono">%s</div>\n  </section>') % (e(ctx["code"]), e(ctx["topic"]), e(ctx["slot"]))
    goals = "\n".join('      <div class="goal">%s</div>' % e(g) for g in ctx["goals"]) or '      <div class="goal"></div>'
    chips = "".join('<span class="code-chip">%s</span>' % e(c) for c in ctx["codes"])
    return ('<section class="slide">\n    <h2>Today\'s Goals</h2>\n    <div class="goals-card">\n%s\n'
            '      <div class="expectations">\n        %s\n        Curriculum expectations addressed today\n'
            '      </div>\n    </div>\n  </section>') % (goals, chips)


# ------------------------------------------------------------------- render
def render(parts, ctx):
    t, tstyle, tscript = template_parts()
    slides = [auto_slide(s["auto"], ctx) if isinstance(s, dict) else s for s in parts["slides"]]
    title = parts.get("title") or ("%s · %s" % (ctx["topic"], ctx["code"]) if ctx["topic"] else ctx["code"])
    label = parts.get("label") or "%s · Deck" % ctx["code"]
    chapters = parts["chapters"] or [(0, "Lesson")]
    out = t.replace("{{COURSE_CODE}}", ctx["code"] or "")
    out = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % html.escape(title, quote=False), out, count=1, flags=re.S)
    out = re.sub(r"<!--\s*\n\s*\S+ SLIDE DECK TEMPLATE.*?-->\n", "<!-- Assembled by Skills/author-week/scripts/build_deck.py from "
                 "Standards/decks/Slide_Deck_Template.html. Edit the slides, then run build_deck.py --rebuild. -->\n",
                 out, count=1, flags=re.S)
    if parts.get("extra_css"):
        out = out.replace("</style>", "/* ============ DECK STYLES ============ */\n%s\n</style>" % parts["extra_css"], 1)
    nav = "\n".join(['  <div class="deck-label">%s</div>' % label] +
                    ['  <div class="chapter" data-slide="%d">%s</div>' % (k, html.escape(n, quote=False)) for k, n in chapters])
    out = re.sub(r'(<nav id="sidebar">).*?(</nav>)', lambda m: "%s\n%s\n%s" % (m.group(1), nav, m.group(2)), out, count=1, flags=re.S)
    out = re.sub(r'<div id="counter">.*?</div>', '<div id="counter">1/%d</div>' % len(slides), out, count=1)
    body = "\n\n".join("  " + s.strip() for s in slides)
    out = re.sub(r'(<main id="stage">).*?(</main>)', lambda m: "%s\n\n%s\n\n%s" % (m.group(1), body, m.group(2)), out, count=1, flags=re.S)
    if parts.get("scripts"):
        extra = "\n".join("<script>\n%s\n</script>" % s.strip("\n") for s in parts["scripts"])
        out = out.replace("</body>", "%s\n</body>" % extra, 1)
    if ctx["theme"] == "gla":
        out = out.replace('<html lang="en">', '<html lang="en" data-deck-theme="gla">', 1)
    return out


# -------------------------------------------------------------------- check
def check(deck, ctx):
    """(errors, warnings) for an assembled deck."""
    errors, warns = [], []
    _, tstyle, tscript = template_parts()
    style = (re.search(r"<style>(.*?)</style>", deck, re.S) or [None, ""])[1]
    have = {n for n, _ in css_chunks(style)[0]}
    lost = [n for n, _ in css_chunks(tstyle)[0] if n not in have]
    if lost:
        errors.append("%d template CSS rule(s) missing or edited (first: %s)" % (len(lost), lost[0][:60]))
    if re.sub(r"\s+", " ", tscript).strip() not in re.sub(r"\s+", " ", deck):
        errors.append("the template's machinery script is missing or edited")
    parts = extract(deck)
    n = len(parts["slides"])
    lo, hi = (ctx or {}).get("slides") or (SLIDES_MIN, SLIDES_MAX)
    if not lo <= n <= hi:
        warns.append("%d slides (the course's range is %d to %d, course.yaml deck_slides)" % (n, lo, hi))
    if not parts["chapters"] or parts["chapters"][0][0] != 0:
        errors.append("the first chapter must start at slide 0")
    if any(k >= n for k, _ in parts["chapters"]) or [k for k, _ in parts["chapters"]] != sorted(k for k, _ in parts["chapters"]):
        errors.append("chapter indices are out of range or out of order")
    names = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip().lower()
    for k, name in parts["chapters"]:
        kicker = KICKER_RE.search(parts["slides"][k - 1]) if 0 < k <= n else None
        if kicker and names(kicker.group(1)) == names(name):
            warns.append("slide %d's kicker names chapter %r, which starts on slide %d; "
                         "the chapter marker may belong one slide earlier" % (k, name, k + 1))
    counter = re.search(r'<div id="counter">([^<]*)</div>', deck)
    if counter and counter.group(1).strip() != "1/%d" % n:
        warns.append("counter reads %s; the script resets it, but it should be 1/%d" % (counter.group(1).strip(), n))
    if n > 1:
        chips = CHIP_RE.findall(parts["slides"][1])
        if not chips:
            errors.append("slide 2 must carry the learning goals and expectation chips")
        elif ctx["codes"] and set(chips) != set(ctx["codes"]):
            warns.append("slide 2 chips %s differ from the lesson's %s" % (", ".join(chips), ", ".join(ctx["codes"])))
    slot = SLOT_RE.findall(parts["slides"][0]) if parts["slides"] else []
    if ctx["slot"] and (not slot or slot[0].strip() != ctx["slot"]):
        errors.append("title slide slot %s, lesson says %s" % (slot[0].strip() if slot else "missing", ctx["slot"]))
    for k, s in enumerate(parts["slides"], 1):
        for code in CODE_RE.findall(s):
            lines = [l for l in html.unescape(re.sub(r"<[^>]+>", "", code)).strip("\n").splitlines()]
            if len(lines) > CODE_LINES_MAX:
                warns.append("slide %d: a code block has %d lines (max %d)" % (k, len(lines), CODE_LINES_MAX))
        text = html.unescape(re.sub(r"<[^>]+>", " ", s))
        if NEXT_RE.search(text):
            warns.append("slide %d points beyond this lesson (%r)" % (k, NEXT_RE.search(text).group(0)))
        if DATE_RE.search(text):
            warns.append("slide %d has a calendar date (%s)" % (k, DATE_RE.search(text).group(0)))
    root_tag = re.search(r"<html\b[^>]*>", deck)
    theme_on = bool(root_tag and 'data-deck-theme="gla"' in root_tag.group(0))
    if (ctx["theme"] == "gla") != theme_on:
        warns.append("deck theme attribute does not match course.yaml deck_theme (%s)" % ctx["theme"])
    return errors, warns


def build(deck_path, parts):
    ctx = context(deck_path)
    if not ctx["code"]:
        raise DeckError("no course.yaml above %s" % deck_path)
    out = render(parts, ctx)
    with open(deck_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out, ctx


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("deck")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rebuild", action="store_true")
    g.add_argument("--from", dest="src")
    g.add_argument("--extract", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.extract:
            sys.stdout.write(to_source(extract(read(a.deck))))
            return 0
        if a.check:
            errors, warns = check(read(a.deck), context(a.deck))
        else:
            parts = extract(read(a.deck)) if a.rebuild else parse_source(read(a.src))
            out, ctx = build(a.deck, parts)
            errors, warns = check(out, ctx)
            print("wrote %s (%d slides)" % (a.deck, len(extract(out)["slides"])))
    except (DeckError, OSError) as e:
        print("ERROR: %s" % e)
        return 2
    for e in errors:
        print("ERROR: " + e)
    for w in warns:
        print("WARN: " + w)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

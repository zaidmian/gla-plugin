#!/usr/bin/env python3
"""
build_calendar.py — render a semester instance into a self-contained teacher
calendar: instances/<semester>/Course_Calendar.html

    python3 build_calendar.py <instance_dir> [--out PATH] [--editor vscode|idea]

Inputs (all read-only): <instance_dir>/calendar.yaml (see
rehydration/Calendar_Schema.yaml), <instance_dir>/semester_config.yaml,
<instance_dir>/week_plans/*.yaml, the master folders those files name, and, when
present, <instance_dir>/gdocs/ (docx handouts), teaching_log.jsonl and
material_links.yaml (embedded as the page's initial state). The page itself
appends to teaching_log.jsonl and rewrites material_links.yaml through the
File System Access API; this script never touches either file.

Course-agnostic: nothing here knows unit names, slot prefixes, or file layouts
beyond the shared week-plan schema and the calendar schema.
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import urllib.parse

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required (python3 -c 'import yaml' failed)")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md2html import render as render_md  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "_lib"))
from gla import schoolcal  # noqa: E402

PATH_RE = re.compile(r"((?:\.\./)*[A-Za-z0-9_][A-Za-z0-9_./-]*?\.(?:html|md|java|yaml|csv|txt|py|js|pdf|docx)|[A-Za-z0-9_]+/)(?![A-Za-z0-9_.-])")


def kind_of(basename):
    b = basename
    if re.match(r"D\d+_Slides_.*\.html$", b):
        return "slides"
    if b.endswith("_GUIDE.md"):
        return "guide"
    if b.endswith("_KEY.md") or b.endswith("_MARKING.md"):
        return "key"
    if re.match(r"D\d+_(Lesson|Lab|Activity|Workshop|Design|Exercise|Submission)_.*\.md$", b) or re.match(r"D\d+_.*\.md$", b):
        return "lesson"
    if b.startswith("EX_") or b.startswith("BRIEF_"):
        return "sheet"
    if b.startswith("REF_") or b == "test_reference.md":
        return "ref"
    if b in ("instructions.md", "assignment_instructions.md") or b.startswith("Assignment_"):
        return "assignment"
    if b in ("test.md", "review_sheet.md", "exam.md"):
        return "test"
    if b.endswith("rubric.md") or b.endswith("rubric.csv"):
        return "rubric"
    if b.endswith("/"):
        return "folder"
    return "doc"


def die(msg):
    """Stop with exit 2: the instance cannot be built from what is on disk."""
    print("ERROR: " + msg)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_dir")
    ap.add_argument("--out")
    ap.add_argument("--editor", choices=["vscode", "idea"], help="add open-in-editor links for markdown files")
    ap.add_argument("--no-prerender", action="store_true", help="link raw .md files instead of rendering HTML twins under <instance>/html/")
    a = ap.parse_args()

    inst = os.path.abspath(a.instance_dir.rstrip("/"))
    root = os.path.dirname(os.path.dirname(inst))
    if not os.path.isdir(os.path.join(root, "master")):
        die(f"{inst} does not look like <course>/instances/<semester> (no master/ two levels up)")
    cal_path = os.path.join(inst, "calendar.yaml")
    if not os.path.exists(cal_path):
        die(f"{cal_path} not found; this instance predates calendar.yaml, so regenerate it with the semester skill (gla semester new)")
    cal = yaml.safe_load(open(cal_path))
    if cal.get("schema") != 1:
        die(f"calendar.yaml schema {cal.get('schema')!r} is not supported (expected 1)")
    cfg = schoolcal.resolve(yaml.safe_load(open(os.path.join(inst, "semester_config.yaml"))) or {})

    # ---- master file index (basename -> repo-relative paths) ----
    index = {}
    for dp, dns, fns in os.walk(os.path.join(root, "master")):
        dns[:] = [d for d in dns if not d.startswith(".")]
        for f in fns:
            index.setdefault(f, []).append(os.path.relpath(os.path.join(dp, f), root))
    docx = {}
    for p in glob.glob(os.path.join(inst, "gdocs", "**", "*.docx"), recursive=True):
        docx[os.path.splitext(os.path.basename(p))[0]] = os.path.relpath(p, inst)
    docx_by_source = {}  # gdocs/index.yaml (written by convert_instance.py): master path -> docx under gdocs/
    ip = os.path.join(inst, "gdocs", "index.yaml")
    if os.path.exists(ip):
        for line in open(ip, encoding="utf-8"):
            m = re.match(r'^\s*"([^"]+)"\s*:\s*"([^"]+)"\s*$', line)
            if m and os.path.exists(os.path.join(inst, "gdocs", m.group(2))):
                docx_by_source[m.group(1)] = os.path.join("gdocs", m.group(2))

    def rel_href(repo_rel):
        return urllib.parse.quote(os.path.relpath(os.path.join(root, repo_rel), inst))

    def editor_href(repo_rel):
        absf = os.path.join(root, repo_rel)
        if a.editor == "vscode":
            return "vscode://file" + urllib.parse.quote(absf)
        if a.editor == "idea":
            return "idea://open?file=" + urllib.parse.quote(absf)
        return None

    def resolve(token, master_dir):
        """token -> repo-relative path or None.
        Tries the week folder, then its parent and grandparent (unit folders keep
        Assessment/ beside the week folders), then a unique basename match, then
        the basename match closest to the week folder."""
        here = master_dir
        for _ in range(3):
            cand = os.path.normpath(os.path.join(here, token))
            if os.path.exists(os.path.join(root, cand)):
                return cand
            here = os.path.dirname(here)
        base = os.path.basename(token.rstrip("/"))
        hits = index.get(base, [])
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            def shared(p):
                a, b = p.split("/"), master_dir.split("/")
                n = 0
                while n < min(len(a), len(b)) and a[n] == b[n]:
                    n += 1
                return n
            best = sorted(hits, key=lambda h: (-shared(h), len(h)))
            if shared(best[0]) > shared(best[1]):
                return best[0]
        return None

    html_root = os.path.join(inst, "html")
    twins = {}      # repo_rel (.md) -> instance-relative html path
    twin_fail = []

    def twin(repo_rel):
        """Render repo_rel (.md) to <inst>/html/<repo_rel minus .md>.html once; return the
        instance-relative html path. Links inside the markdown that point at other .md
        files in master are rewritten to their twins (rendered on demand)."""
        if a.no_prerender or not repo_rel.endswith(".md"):
            return None
        if repo_rel in twins:
            return twins[repo_rel]
        out_rel = os.path.join("html", repo_rel[:-3] + ".html")
        twins[repo_rel] = out_rel  # register before rendering: cycles resolve to the path
        src = os.path.join(root, repo_rel)
        out_abs = os.path.join(inst, out_rel)
        src_dir = os.path.dirname(repo_rel)

        def rewrite(target):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                return None
            path_part = target.split("#")[0]
            cand = os.path.normpath(os.path.join(src_dir, path_part))
            if not os.path.exists(os.path.join(root, cand)):
                return None
            if cand.endswith(".md"):
                t = twin(cand)
                if t:
                    return os.path.relpath(os.path.join(inst, t), os.path.dirname(out_abs)) + ("#" + target.split("#", 1)[1] if "#" in target else "")
            return os.path.relpath(os.path.join(root, cand), os.path.dirname(out_abs))

        try:
            render_md(src, out_abs, source_href=os.path.relpath(src, os.path.dirname(out_abs)),
                      link_rewriter=rewrite, crumbs=[p for p in src_dir.split("/") if p and p != "master"])
        except Exception as e:  # keep building; report
            twin_fail.append(f"{repo_rel}: {e}")
            del twins[repo_rel]
            return None
        return out_rel

    def link(repo_rel, label=None):
        base = os.path.basename(repo_rel.rstrip("/"))
        k = kind_of(base if not repo_rel.endswith("/") and os.path.isfile(os.path.join(root, repo_rel)) else base + ("/" if os.path.isdir(os.path.join(root, repo_rel)) else ""))
        d = {"kind": k, "label": label or base, "href": rel_href(repo_rel), "path": repo_rel, "name": base}
        t = twin(repo_rel) if base.endswith(".md") else None
        if t:
            d["raw"] = d["href"]
            d["href"] = urllib.parse.quote(t)
        e = editor_href(repo_rel) if base.endswith(".md") else None
        if e:
            d["editor"] = e
        stem = os.path.splitext(base)[0]
        if repo_rel in docx_by_source:
            d["docx"] = urllib.parse.quote(docx_by_source[repo_rel])
        elif stem in docx:
            d["docx"] = urllib.parse.quote(docx[stem])
        elif base == "instructions.md":
            parent = os.path.basename(os.path.dirname(repo_rel))
            if parent in docx:
                d["docx"] = urllib.parse.quote(docx[parent])
        return d

    def material_entry(text, master_dir):
        links = []
        seen = set()
        for tok in PATH_RE.findall(text):
            rr = resolve(tok, master_dir)
            if rr and rr not in seen:
                seen.add(rr)
                links.append(link(rr))
                # companion key / marking sheet for student sheets
                base = os.path.basename(rr)
                stem, ext = os.path.splitext(base)
                for suffix in ("_KEY.md", "_MARKING.md"):
                    key = os.path.join(os.path.dirname(rr), stem + suffix)
                    if ext == ".md" and os.path.exists(os.path.join(root, key)) and key not in seen:
                        seen.add(key)
                        links.append(link(key))
                # a test paper carries the aid sheet handed out with it
                if base in ("test.md", "exam.md"):
                    aid = os.path.join(os.path.dirname(rr), "test_reference.md")
                    if os.path.exists(os.path.join(root, aid)) and aid not in seen:
                        seen.add(aid)
                        links.append(link(aid))
                # assignment sheets carry their sibling rubric CSVs (the Google Classroom
                # import); a culminating project keeps more than one (project, reflection)
                if kind_of(base) == "assignment":
                    adir = os.path.dirname(rr)
                    for f in sorted(os.listdir(os.path.join(root, adir))):
                        if f.endswith("rubric.csv"):
                            rub = os.path.join(adir, f)
                            if rub not in seen:
                                seen.add(rub)
                                links.append(link(rub))
        return {"text": text, "links": links}

    # ---- week plans ----
    plans = {}
    for d in cal["days"]:
        wp = d.get("week_plan")
        if wp and wp not in plans:
            plans[wp] = yaml.safe_load(open(os.path.join(inst, wp)))
    plan_days = {}
    for wp, p in plans.items():
        for dl in p.get("daily_lessons", []):
            plan_days[dl["slot"]] = (wp, dl)

    # ---- day payloads ----
    days = []
    for d in cal["days"]:
        out = {"date": d["date"], "kind": d["kind"], "label": d.get("label"), "note": d.get("note")}
        if d["kind"] == "slot":
            wp, dl = plan_days.get(d["slot"], (None, None))
            p = plans.get(wp) if wp else None
            meta = p["metadata"] if p else {}
            out.update({
                "slot": d["slot"], "week_key": d.get("week_key"), "title": d.get("title") or (dl or {}).get("title"),
                "day_type": d.get("day_type") or (dl or {}).get("day_type"), "sub_ready": bool(d.get("sub_ready", (dl or {}).get("sub_ready", False))),
                "handouts": d.get("handouts") or [], "dues": d.get("dues") or [],
                "unit": meta.get("unit"), "unit_name": meta.get("unit_name"), "week_title": meta.get("week_title"),
                "focus": (dl or {}).get("focus"), "activities": (dl or {}).get("activities") or [],
                "materials": [material_entry(m, d["master_dir"]) for m in ((dl or {}).get("materials") or [])],
                "auto": [], "week_plan": wp, "master_dir": d.get("master_dir"),
            })
            # auto links: this day's lesson/slides/guide in the master folder
            mdir = os.path.join(root, d["master_dir"]) if d.get("master_dir") else None
            daynum = re.search(r"\.D(\d+)$", d["slot"])
            if mdir and os.path.isdir(mdir):
                listed = {l["path"] for m in out["materials"] for l in m["links"]}
                prefix = f"D{daynum.group(1)}_" if daynum else None
                for f in sorted(os.listdir(mdir)):
                    if prefix and f.startswith(prefix) and (f.endswith(".md") or f.endswith(".html")):
                        rr = os.path.relpath(os.path.join(mdir, f), root)
                        if rr not in listed:
                            out["auto"].append(link(rr))
            if wp:
                # the week plan is the same file on all five days; the renderer shows it
                # once in the week header rather than repeating it in every day cell
                stem = os.path.splitext(os.path.basename(wp))[0]
                out["week_plan_link"] = {"kind": "plan",
                                         "label": stem.replace("_", ".") + " plan",
                                         "href": urllib.parse.quote(wp), "path": wp,
                                         "name": os.path.basename(wp)}
        days.append(out)

    # ---- sub packets (course-level, optional) ----
    packets = []
    pk_dir = os.path.join(root, "master", "00_Admin", "Emergency_Sub_Packets")
    if os.path.isdir(pk_dir):
        for f in sorted(os.listdir(pk_dir)):
            if f.endswith(".md") and not f.endswith("_KEY.md") and f != "README.md":
                packets.append(link(os.path.relpath(os.path.join(pk_dir, f), root)))

    # ---- evaluations (instance truth lives in calendar.yaml handouts/dues; the plan gives kinds) ----
    # ---- initial state from log/links if present ----
    events = []
    lp = os.path.join(inst, "teaching_log.jsonl")
    if os.path.exists(lp):
        for line in open(lp):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    links = {}
    mp = os.path.join(inst, "material_links.yaml")
    if os.path.exists(mp):
        for line in open(mp):
            m = re.match(r'^\s*"?([^"#:][^":]*?)"?\s*:\s*"?(https?://[^"\s]+)"?\s*$', line)
            if m:
                links[m.group(1).strip()] = m.group(2)

    data = {
        "course": cal.get("course", {}), "semester": cal.get("semester", {}), "generated": cal.get("generated", {}),
        "days": days, "cuts": cal.get("cuts", []), "packets": packets, "events": events, "links": links,
        "instance": os.path.basename(inst), "built": dt.date.today().isoformat(),
        "holidays": [h.get("name") for h in cfg.get("holidays", [])],
    }
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__TITLE__", html.escape(f"{data['course'].get('code', '')} {data['semester'].get('name', '')} calendar".strip()))
    out = a.out or os.path.join(inst, "Course_Calendar.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    n_slots = sum(1 for d in days if d["kind"] == "slot")
    n_links = sum(len(m["links"]) for d in days if d["kind"] == "slot" for m in d["materials"])
    unresolved = sorted({m["text"] for d in days if d["kind"] == "slot" for m in d["materials"] if not m["links"] and PATH_RE.search(m["text"])})
    n_docx_links = len({l["path"] for d in days if d["kind"] == "slot" for m in d["materials"] + [{"links": d["auto"]}] for l in m["links"] if l.get("docx")})
    print(f"wrote {out}: {len(days)} days, {n_slots} slots, {n_links} material links, {len(docx)} docx found ({len(docx_by_source)} via index.yaml, {n_docx_links} distinct materials linked to a docx), {len(events)} log events, {len(links)} URL links")
    if not a.no_prerender:
        print(f"rendered {len(twins)} markdown files to {os.path.relpath(html_root, inst)}/ (HTML twins; raw links kept)")
        for f in twin_fail:
            print("  RENDER FAILED", f)
    if unresolved:
        print("materials with a file-like name that could not be resolved (shown as plain text):")
        for u in unresolved:
            print("  -", u)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --page: #f7f8fa; --surface: #ffffff; --surface-alt: #eff1f4;
  --edge: #e3e6eb; --edge-strong: #d2d6dd;
  --heading: #171a1f; --body: #2c313a; --muted: #626977; --faint: #858c99;
  --accent: #0e7c87; --accent-hover: #0b626b; --on-accent: #ffffff;
  --primary-100: #c3e5e8; --primary-200: #92ced4; --primary-300: #5cb3bc;
  --primary-500: #0e7c87; --primary-700: #094c53; --primary-900: #052a2e;
  --secondary-300: #e58a73; --secondary-500: #c85a3f; --secondary-600: #a94832;
  --tile-primary-bg: #e6f4f5; --tile-primary-fg: #0b626b;
  --tile-warm-bg: #fceae5; --tile-warm-fg: #a94832;
  --success-fg: #2c6e4e; --success-bg: #e9f3ec;
  --warning-fg: #8f5e13; --warning-bg: #fbefd6;
  --danger-fg: #9e362e; --danger-bg: #f9e5e2;
  --info-fg: #2c5590; --info-bg: #e8eff9;
  --code-bg: #171a1f; --code-fg: #eef1f5;
  --shadow-md: 0 4px 12px rgba(23,26,31,.08), 0 1px 3px rgba(23,26,31,.05);
}
* { box-sizing: border-box; }
html { color-scheme: light; }
body { margin: 0; background: var(--page); color: var(--body); font: 15px/1.45 'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }
code, .mono { font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .92em; }
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); text-decoration: underline; }
button { font: inherit; }
header.top { position: sticky; top: 0; z-index: 20; background: var(--surface); border-bottom: 1px solid var(--edge); box-shadow: var(--shadow-md); }
.bar { max-width: 1180px; margin: 0 auto; padding: 10px 20px; display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
.bar h1 { font-size: 18px; margin: 0; color: var(--heading); }
.bar h1 small { color: var(--muted); font-weight: 400; margin-left: 8px; }
.stats { display: flex; gap: 8px; flex-wrap: wrap; }
.stat { background: var(--surface-alt); border: 1px solid var(--edge); border-radius: 8px; padding: 4px 10px; font-size: 13px; color: var(--muted); }
.stat b { color: var(--heading); font-size: 15px; margin-right: 4px; }
.stat.warn { background: var(--warning-bg); color: var(--warning-fg); border-color: transparent; } .stat.warn b { color: inherit; }
.stat.bad { background: var(--danger-bg); color: var(--danger-fg); border-color: transparent; } .stat.bad b { color: inherit; }
.stat.good { background: var(--success-bg); color: var(--success-fg); border-color: transparent; } .stat.good b { color: inherit; }
.controls { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-left: auto; }
.btn { border: 1px solid var(--edge-strong); background: var(--surface); color: var(--body); border-radius: 8px; padding: 5px 10px; cursor: pointer; font-size: 13px; }
.btn:hover { border-color: var(--accent); color: var(--accent); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.btn.primary:hover { background: var(--accent-hover); color: var(--on-accent); }
.btn.on { background: var(--tile-primary-bg); border-color: var(--primary-300); color: var(--tile-primary-fg); }
input[type=search] { border: 1px solid var(--edge-strong); border-radius: 8px; padding: 5px 9px; font: inherit; font-size: 13px; width: 200px; }
.banner { max-width: 1180px; margin: 10px auto 0; padding: 8px 14px; border-radius: 8px; font-size: 13px; }
.banner.warn { background: var(--warning-bg); color: var(--warning-fg); }
.banner.info { background: var(--info-bg); color: var(--info-fg); }
.banner.good { background: var(--success-bg); color: var(--success-fg); }
main { max-width: 1180px; margin: 0 auto; padding: 14px 20px 80px; }
section.week { margin: 22px 0 34px; scroll-margin-top: 130px; }
section.week.current { }
.week-head { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; border-bottom: 2px solid var(--edge-strong); padding-bottom: 6px; margin-bottom: 10px; }
section.week.current .week-head { border-color: var(--accent); }
.week-head h2 { margin: 0; font-size: 20px; color: var(--heading); }
.week-head .range { color: var(--muted); }
.week-head .tag { margin-left: auto; }
.week-head .plans { font-size: 12px; }
.pill { display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; padding: 2px 8px; border-radius: 999px; background: var(--surface-alt); color: var(--muted); border: 1px solid var(--edge); }
.pill.now { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
.pill.teach, .pill.wet_lab, .pill.seminar, .pill.debate, .pill.field_trip { background: var(--tile-primary-bg); color: var(--tile-primary-fg); border-color: transparent; }
.pill.exercise, .pill.studio, .pill.lab { background: var(--info-bg); color: var(--info-fg); border-color: transparent; }
.pill.assess { background: var(--tile-warm-bg); color: var(--tile-warm-fg); border-color: transparent; }
.pill.flex, .pill.buffer { background: var(--warning-bg); color: var(--warning-fg); border-color: transparent; }
.pill.exam { background: var(--secondary-500); color: #fff; border-color: transparent; }
.pill.sub { background: var(--success-bg); color: var(--success-fg); border-color: transparent; }
.pill.assign-out { background: var(--tile-warm-bg); color: var(--tile-warm-fg); border-color: transparent; }
.pill.assign-due { background: var(--danger-bg); color: var(--danger-fg); border-color: transparent; }
.summary { background: var(--surface); border: 1px solid var(--edge); border-radius: 10px; padding: 12px 16px; margin-bottom: 12px; display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 10px 22px; }
.summary h3 { margin: 0 0 6px; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: var(--faint); }
.summary ul { margin: 0; padding-left: 18px; }
.summary li { margin: 2px 0; }
.summary .none { color: var(--faint); font-style: italic; }
.summary label { display: flex; gap: 6px; align-items: baseline; cursor: pointer; }
.summary label.done { color: var(--faint); text-decoration: line-through; }
.days { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.day { background: var(--surface); border: 1px solid var(--edge); border-radius: 10px; padding: 10px 12px 12px; display: flex; flex-direction: column; gap: 6px; min-height: 150px; position: relative; }
.day.today { outline: 2px solid var(--accent); outline-offset: 1px; }
.day.past { background: #fbfbfc; }
.day.closure, .day.buffer, .day.exam { background: var(--surface-alt); }
.day.closure { color: var(--muted); }
.day.s-taught { border-left: 5px solid var(--success-fg); }
.day.s-partial { border-left: 5px solid var(--warning-fg); }
.day.s-skipped { border-left: 5px solid var(--danger-fg); }
.day.s-moved { border-left: 5px solid var(--info-fg); }
.day.s-postponed { border-left: 5px dashed var(--info-fg); }
.day.s-noclass { border-left: 5px solid var(--faint); }
.day.needs { box-shadow: inset 0 0 0 1px var(--warning-fg); }
.day .date { font-size: 12px; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
.day .date b { color: var(--heading); }
.day .slot { font-size: 12px; }
.day .title { font-weight: 600; color: var(--heading); line-height: 1.3; }
.day .focus { font-size: 12.5px; color: var(--muted); }
.day .pills { display: flex; gap: 4px; flex-wrap: wrap; }
.day .marks { font-size: 12px; }
.day .marks span { display: block; }
.day .marks .out { color: var(--tile-warm-fg); } .day .marks .due { color: var(--danger-fg); font-weight: 600; }
.day .note-ev { font-size: 12px; color: var(--secondary-600); }
.links { display: flex; flex-wrap: wrap; gap: 4px 6px; font-size: 12.5px; }
.links a { background: var(--surface-alt); border: 1px solid var(--edge); border-radius: 6px; padding: 1px 7px; white-space: nowrap; }
.links a.slides { background: var(--tile-primary-bg); border-color: transparent; color: var(--tile-primary-fg); }
.links a.gdoc { background: var(--success-bg); border-color: transparent; color: var(--success-fg); }
.links a.assignment { background: var(--tile-warm-bg); border-color: transparent; color: var(--tile-warm-fg); font-weight: 600; }
.links a.sheet { background: var(--info-bg); border-color: transparent; color: var(--info-fg); }
.links a.rubric { background: var(--warning-bg); border-color: transparent; color: var(--warning-fg); }
.links a.key { color: var(--secondary-600); }
.links a.docx { color: var(--info-fg); }
.links a.raw { color: var(--faint); }
.links .mat { display: inline-flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.links .plain { color: var(--faint); font-size: 12px; }
.links button.tiny { border: none; background: none; color: var(--faint); cursor: pointer; padding: 0 3px; font-size: 12px; }
.links button.tiny:hover { color: var(--accent); }
details.acts { font-size: 12.5px; }
details.acts summary { cursor: pointer; color: var(--muted); }
details.acts table { border-collapse: collapse; margin-top: 4px; }
details.acts td { padding: 1px 6px 1px 0; vertical-align: top; }
details.acts td.min { color: var(--faint); white-space: nowrap; }
.status { margin-top: auto; display: flex; flex-direction: column; gap: 5px; padding-top: 6px; border-top: 1px dashed var(--edge); }
.status .btns { display: flex; gap: 4px; flex-wrap: wrap; }
.sb { border: 1px solid var(--edge-strong); background: var(--surface); border-radius: 6px; padding: 2px 8px; font-size: 12px; cursor: pointer; color: var(--muted); }
.sb:hover { border-color: var(--accent); color: var(--accent); }
.sb.on.taught { background: var(--success-bg); color: var(--success-fg); border-color: transparent; }
.sb.on.partial { background: var(--warning-bg); color: var(--warning-fg); border-color: transparent; }
.sb.on.skipped { background: var(--danger-bg); color: var(--danger-fg); border-color: transparent; }
.sb.on.moved { background: var(--info-bg); color: var(--info-fg); border-color: transparent; }
.sb.on.postponed { background: var(--info-bg); color: var(--info-fg); border-color: transparent; border-style: dashed; }
.sb.on.noclass { background: var(--edge); color: var(--body); border-color: transparent; }
.status .meta { font-size: 11.5px; color: var(--faint); }
.status .fixm { display: flex; gap: 4px; align-items: center; margin-top: 2px; }
.status textarea { width: 100%; border: 1px solid var(--edge); border-radius: 6px; padding: 4px 6px; font: inherit; font-size: 12.5px; resize: vertical; min-height: 30px; }
.status input[type=date] { font: inherit; font-size: 12px; border: 1px solid var(--edge); border-radius: 6px; padding: 2px 4px; }
.closure .big { font-size: 15px; font-weight: 600; margin-top: 8px; }
.hidden { display: none !important; }
dialog { border: 1px solid var(--edge-strong); border-radius: 12px; padding: 18px 20px; max-width: 560px; box-shadow: var(--shadow-md); }
dialog h3 { margin-top: 0; }
dialog input[type=url] { width: 100%; font: inherit; padding: 6px 8px; border: 1px solid var(--edge-strong); border-radius: 8px; }
#changes { max-width: 1180px; margin: 0 auto; padding: 0 20px 40px; }
#changes table { border-collapse: collapse; width: 100%; font-size: 13px; background: var(--surface); }
#changes th, #changes td { border-bottom: 1px solid var(--edge); padding: 5px 8px; text-align: left; vertical-align: top; }
#changes th { background: var(--surface-alt); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
kbd { background: var(--surface-alt); border: 1px solid var(--edge-strong); border-radius: 4px; padding: 0 5px; font-size: 12px; }
footer { max-width: 1180px; margin: 0 auto; padding: 10px 20px 40px; color: var(--faint); font-size: 12px; }
@media (max-width: 1100px) { .days { grid-template-columns: repeat(2, minmax(0, 1fr)); } .summary { grid-template-columns: 1fr 1fr; } }
@media (max-width: 700px) { .days, .summary { grid-template-columns: 1fr; } }
@media print {
  header.top, .controls, .status, .banner, footer, button, details.acts, #changes { display: none !important; }
  body { background: #fff; font-size: 11px; }
  main { padding: 0; max-width: none; }
  section.week { page-break-after: always; margin: 0 0 8px; }
  section.week:last-child { page-break-after: auto; }
  .days { gap: 6px; }
  .day { min-height: 0; break-inside: avoid; }
  .summary { grid-template-columns: 1fr 1fr 1fr; }
  a { color: inherit; }
  .links a { border: 1px solid #ccc; background: none; }
}
</style>
</head>
<body>
<header class="top">
  <div class="bar">
    <h1 id="h1"></h1>
    <div class="stats" id="stats"></div>
    <div class="controls">
      <input type="search" id="q" placeholder="search titles, materials…" title="Filter days by text">
      <button class="btn" id="subOnly" title="Show only sub-ready days">Sub-ready only</button>
      <button class="btn" id="today">Today</button>
      <button class="btn" id="showChanges">What changed</button>
      <button class="btn" id="print">Print</button>
      <button class="btn primary" id="connect">Connect folder</button>
    </div>
  </div>
</header>
<div id="banner" class="banner info"></div>
<main id="main"></main>
<div id="changes" class="hidden"></div>
<footer id="foot"></footer>

<dialog id="linkDlg">
  <form method="dialog">
    <h3>Google Docs link</h3>
    <p id="linkFor" class="mono"></p>
    <input type="url" id="linkUrl" placeholder="https://docs.google.com/…">
    <p style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:0">
      <button class="btn" value="cancel">Cancel</button>
      <button class="btn" value="clear">Remove link</button>
      <button class="btn primary" value="save" id="linkSave">Save</button>
    </p>
  </form>
</dialog>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
// Postponed: taught later (the next recalendar re-plans it). Skipped: not taught this
// semester. No class: the class did not meet. Moved: taught, or to be taught, on the
// date given. A buffer day is a class that ran, ran partly, was lost, or did not meet.
const STATUSES = ['taught', 'partial', 'postponed', 'moved', 'skipped', 'noclass'];
const BUFFER_STATUSES = ['taught', 'partial', 'skipped', 'noclass'];
const LABELS = { taught: 'Taught', partial: 'Partial', postponed: 'Postponed', moved: 'Moved', skipped: 'Skipped', noclass: 'No class' };
const BUFFER_LABELS = { taught: 'Class ran', partial: 'Partly', skipped: 'Lost', noclass: 'No class' };
const HINTS = { taught: 'taught as planned', partial: 'got part way through; counts as taught', postponed: 'not taught today; the next recalendar re-plans it',
  moved: 'taught, or to be taught, on another date', skipped: 'not taught this semester; never re-planned', noclass: 'the class did not meet; the slot is re-planned' };
const LS_KEY = 'gla-cal:' + (DATA.course.code || '') + ':' + DATA.instance;

// ---------- state ----------
let events = DATA.events.slice();
let links = Object.assign({}, DATA.links);
// links are keyed by repo path; a bare filename key (older files) only applies when that filename is unique
const NAME_COUNT = (() => {
  const paths = new Map();
  DATA.days.forEach(d => { (d.materials || []).forEach(m => m.links.forEach(l => paths.set(l.path, l.name))); (d.auto || []).forEach(l => paths.set(l.path, l.name)); });
  (DATA.packets || []).forEach(l => paths.set(l.path, l.name));
  const c = {}; paths.forEach(n => { c[n] = (c[n] || 0) + 1; }); return c;
})();
function linkKey(l) {
  if (links[l.path] || NAME_COUNT[l.name] !== 1) return l.path;
  return l.name in links ? l.name : l.path;
}
let dirHandle = null;
let connected = false;
let prefs = load(LS_KEY + ':prefs', { subOnly: false, prep: {} });
let cachedFrom = null;
try {
  const c = load(LS_KEY + ':cache', null);
  if (c && c.events && (!events.length || c.events.length > events.length)) { events = c.events; links = Object.assign({}, links, c.links || {}); cachedFrom = c.at; }
} catch (e) {}

function load(k, dflt) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : dflt; } catch (e) { return dflt; } }
function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

function keyOf(d) { return d.kind === 'slot' ? d.slot : (d.kind === 'buffer' ? 'BUFFER:' + d.date : null); }
// The log is keyed by slot, so after a recalendar an old event would follow its slot
// to a new date. An event logged for another date no longer applies, except a move
// whose actual date is the slot's current, past date: that reads as taught.
const DATE_OF = {};
DATA.days.forEach(d => { const k = keyOf(d); if (k) DATE_OF[k] = d.date; });
function stateMap() {
  const m = {};
  for (const e of events) { if (e.status === 'clear') delete m[e.key]; else m[e.key] = e; }
  for (const k of Object.keys(m)) {
    const e = m[k], now = DATE_OF[k];
    if (!now || !e.date || e.date === now) continue;
    if (e.status === 'moved' && e.actual === now && now < todayISO) m[k] = Object.assign({}, e, { status: 'taught', date: now });
    else delete m[k];
  }
  return m;
}

// ---------- dates ----------
const todayISO = new Date().toISOString().slice(0, 10) === localISO(new Date()) ? localISO(new Date()) : localISO(new Date());
function localISO(d) { const z = n => String(n).padStart(2, '0'); return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()); }
function parse(iso) { const [y, m, d] = iso.split('-').map(Number); return new Date(y, m - 1, d); }
function fmt(iso, opts) { return parse(iso).toLocaleDateString('en-CA', opts || { weekday: 'short', month: 'short', day: 'numeric' }); }
function monday(iso) { const d = parse(iso); const wd = (d.getDay() + 6) % 7; d.setDate(d.getDate() - wd); return localISO(d); }
function addDays(iso, n) { const d = parse(iso); d.setDate(d.getDate() + n); return localISO(d); }

// ---------- grouping ----------
const byDate = {}; DATA.days.forEach(d => byDate[d.date] = d);
const weeks = [];
{
  const seen = new Set();
  for (const d of DATA.days) {
    const m = monday(d.date);
    if (seen.has(m)) continue;
    seen.add(m);
    const ds = [];
    for (let i = 0; i < 5; i++) { const iso = addDays(m, i); ds.push(byDate[iso] || { date: iso, kind: 'outside' }); }
    weeks.push({ start: m, days: ds });
  }
}

// ---------- rendering ----------
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const KIND_LABEL = { slides: 'slides', lesson: 'lesson', guide: 'guide', key: 'key', plan: 'week plan', rubric: 'rubric', folder: 'folder' };
const STUDENT_KINDS = new Set(['sheet', 'ref', 'assignment', 'test', 'doc']);
function shortName(l) {
  let n = l.name.replace(/\.(md|html|yaml|csv|java|txt|py|js|pdf)$/, '');
  if (l.kind === 'assignment' && /^(assignment_)?instructions$/i.test(n)) { const seg = l.path.split('/'); n = seg[seg.length - 2] || n; }
  n = n.replace(/^(EX|BRIEF|REF|Assignment|D\d+_[A-Za-z]+)_/, '').replace(/_/g, ' ');
  return n;
}
function linkHtml(l) {
  const parts = [];
  const g = links[linkKey(l)];
  const student = STUDENT_KINDS.has(l.kind);
  const label = student ? shortName(l)
    : l.kind === 'rubric' ? l.name.replace(/\.(csv|md)$/, '').replace(/_/g, ' ')
    : l.kind === 'plan' ? (l.label || KIND_LABEL.plan)
    : (KIND_LABEL[l.kind] || l.name);
  if (g) parts.push(`<a class="gdoc" href="${esc(g)}" target="_blank" rel="noopener" title="Google Doc: ${esc(l.name)}">${esc(label)} ↗</a>`);
  parts.push(`<a class="${esc(l.kind)}" href="${esc(l.href)}" target="_blank" title="${esc(l.path)}">${esc(g ? 'md' : label)}</a>`);
  if (l.raw) parts.push(`<a class="raw" href="${esc(l.raw)}" target="_blank" title="raw markdown">raw</a>`);
  if (l.docx) parts.push(`<a class="docx" href="${esc(l.docx)}" title="Google-Docs-ready .docx">docx</a>`);
  if (l.editor) parts.push(`<a class="editor" href="${esc(l.editor)}" title="open in editor">edit</a>`);
  parts.push(`<button class="tiny" data-copy="${esc(l.path)}" title="copy path">⧉</button>`);
  if (student && l.name.endsWith('.md')) parts.push(`<button class="tiny" data-link="${esc(linkKey(l))}" title="${g ? 'change' : 'add'} Google Docs link">${g ? '✎' : '+URL'}</button>`);
  return `<span class="mat" title="${esc(l.path)}">${parts.join('')}</span>`;
}

function weekPlans(w) {
  // one link per distinct week plan; a calendar week straddles two when a unit turns over
  const seen = new Set(), out = [];
  for (const d of w.days) {
    const l = d.week_plan_link;
    if (l && !seen.has(l.path)) { seen.add(l.path); out.push(linkHtml(l)); }
  }
  return out.length ? `<span class="links plans">${out.join('')}</span>` : '';
}

function dayHtml(d, st, isToday) {
  const past = d.date < todayISO;
  if (d.kind === 'outside') return `<div class="day closure past" style="opacity:.5"><div class="date"><b>${esc(fmt(d.date))}</b></div><div class="big">outside semester</div></div>`;
  if (d.kind === 'closure') return `<div class="day closure ${past ? 'past' : ''}"><div class="date"><b>${esc(fmt(d.date))}</b></div><div class="big">No class</div><div>${esc(d.label)}</div></div>`;
  if (d.kind === 'exam') return `<div class="day exam ${past ? 'past' : ''} ${isToday ? 'today' : ''}"><div class="date"><b>${esc(fmt(d.date))}</b><span class="pill exam">exam period</span></div><div class="title">Written examination window</div><div class="focus">${esc(d.label || '')}</div></div>`;
  const key = keyOf(d);
  const s = st[key];
  const cls = ['day', d.kind, past ? 'past' : '', isToday ? 'today' : '', s ? 's-' + s.status : '', (past && !s && d.kind !== 'exam') ? 'needs' : ''].join(' ');
  const labels = d.kind === 'buffer' ? BUFFER_LABELS : LABELS;
  let body = '';
  if (d.kind === 'buffer') {
    body = `<div class="date"><b>${esc(fmt(d.date))}</b><span class="pill buffer">buffer</span></div>
      <div class="title">Buffer day</div><div class="focus">${esc(d.label || '')}. If class runs: review / catch-up.</div>`;
  } else {
    const pills = [`<span class="pill ${esc(d.day_type)}">${esc(String(d.day_type || '').replace('_', ' '))}</span>`];
    if (d.sub_ready) pills.push('<span class="pill sub">sub-ready</span>');
    if ((d.handouts || []).length) pills.push(`<span class="pill assign-out" title="Handed out: ${esc((d.handouts || []).join('; '))}">assigned</span>`);
    if ((d.dues || []).length) pills.push(`<span class="pill assign-due" title="Due: ${esc((d.dues || []).join('; '))}">due</span>`);
    const marks = [];
    (d.handouts || []).forEach(h => marks.push(`<span class="out">↑ ${esc(h)} handed out</span>`));
    (d.dues || []).forEach(h => marks.push(`<span class="due">↓ ${esc(h)}</span>`));
    const mats = (d.materials || []).map(m => m.links.length ? m.links.map(linkHtml).join('') : `<span class="plain">${esc(m.text)}</span>`);
    const auto = (d.auto || []).map(linkHtml);
    const acts = (d.activities || []).length ? `<details class="acts"><summary>${(d.activities || []).reduce((a, x) => a + (x.minutes || 0), 0)} min · ${d.activities.length} segments</summary><table>${d.activities.map(x => `<tr><td class="min">${esc(x.minutes)}</td><td>${esc(x.what)}</td></tr>`).join('')}</table></details>` : '';
    body = `<div class="date"><b>${esc(fmt(d.date))}</b><span class="slot mono">${esc(d.slot)}</span></div>
      <div class="pills">${pills.join('')}</div>
      <div class="title">${esc(d.title)}</div>
      ${d.focus ? `<div class="focus">${esc(d.focus)}</div>` : ''}
      ${marks.length ? `<div class="marks">${marks.join('')}</div>` : ''}
      ${d.note ? `<div class="note-ev">⚑ ${esc(d.note)}</div>` : ''}
      ${mats.length || auto.length ? `<div class="links">${mats.join('')}${auto.join('')}</div>` : ''}
      ${acts}`;
  }
  const meta = s ? `${labels[s.status] || s.status}${s.actual && s.actual !== d.date ? ' on ' + fmt(s.actual) : ''} · logged ${new Date(s.ts).toLocaleDateString('en-CA')}` : (past ? 'not logged yet' : '');
  const status = `<div class="status">
      <div class="btns">${(d.kind === 'buffer' ? BUFFER_STATUSES : STATUSES).map(x => `<button class="sb ${x} ${s && s.status === x ? 'on' : ''}" data-key="${esc(key)}" data-date="${esc(d.date)}" data-status="${x}" title="${esc(d.kind === 'buffer' ? labels[x] : HINTS[x])}">${labels[x]}</button>`).join('')}
        ${s ? `<button class="sb" data-key="${esc(key)}" data-date="${esc(d.date)}" data-status="clear" title="remove status">×</button>` : ''}</div>
      ${s && s.status === 'moved' ? `<label class="meta">taught on (or moved to) <input type="date" data-actual="${esc(key)}" value="${esc(s.actual || '')}"></label>` : ''}
      <div class="meta">${esc(meta)}</div>
      <textarea data-note="${esc(key)}" placeholder="note (what really happened, or what to fix in master)">${esc(s && s.note || '')}</textarea>
      ${d.kind === 'slot' ? `<label class="meta fixm" title="list this note in the course backlog, for the next time this week is authored"><input type="checkbox" data-master="${esc(key)}" ${s && s.master ? 'checked' : ''} ${s && s.note ? '' : 'disabled'}> fix in master</label>` : ''}
    </div>`;
  return `<div class="${cls}" data-date="${esc(d.date)}" data-key="${esc(key)}">${body}${status}</div>`;
}

function weekSummary(w, st) {
  const slots = w.days.filter(d => d.kind === 'slot');
  const plans = [];
  for (const d of slots) { const k = (d.unit_name || d.week_key || '') + '|' + (d.week_title || ''); if (!plans.some(p => p.k === k)) plans.push({ k, unit: d.unit_name || d.week_key, title: d.week_title, unitCode: d.unit }); }
  const heading = plans.length ? plans.map(p => `${esc(p.unit || '')}${p.title ? ' · ' + esc(p.title) : ''}`).join(' → ') : (w.days.some(d => d.kind === 'exam') ? 'Exam period' : 'No teaching this week');
  const teach = slots.filter(d => d.day_type === 'teach').map(d => `${fmt(d.date, { weekday: 'short' })}: ${d.title}`);
  const work = slots.filter(d => d.day_type !== 'teach').map(d => `${fmt(d.date, { weekday: 'short' })}: ${d.title} (${d.day_type})`);
  const buffers = w.days.filter(d => d.kind === 'buffer').map(d => `${fmt(d.date, { weekday: 'short' })}: buffer (${d.label})`);
  const closures = w.days.filter(d => d.kind === 'closure').map(d => `${fmt(d.date, { weekday: 'short' })}: no class (${d.label})`);
  const evs = [];
  slots.forEach(d => { (d.handouts || []).forEach(h => evs.push(`<li><span class="out">↑</span> ${esc(h)} handed out ${fmt(d.date, { weekday: 'short' })}</li>`)); (d.dues || []).forEach(h => evs.push(`<li><b>↓</b> ${esc(h)} <b>${fmt(d.date, { weekday: 'short' })}</b></li>`)); });
  slots.filter(d => d.day_type === 'assess').forEach(d => evs.push(`<li><b>${esc(d.title)}</b> ${fmt(d.date, { weekday: 'short' })}</li>`));
  // prep checklist: union of materials (linked ones first)
  const prep = new Map();
  slots.forEach(d => { (d.materials || []).forEach(m => { const id = m.links.length ? m.links[0].path : m.text; if (!prep.has(id)) prep.set(id, { m, days: [] }); prep.get(id).days.push(fmt(d.date, { weekday: 'short' })); }); });
  const prepHtml = [...prep.entries()].map(([id, p]) => {
    const pk = w.start + '|' + id; const done = !!prefs.prep[pk];
    const l0 = p.m.links[0];
    const lbl = l0 ? (STUDENT_KINDS.has(l0.kind) ? shortName(l0) + ' <span style="color:var(--faint)">(' + (l0.kind === 'sheet' ? 'sheet' : l0.kind) + ')</span>' : (KIND_LABEL[l0.kind] || l0.kind) + ' · ' + esc(shortName(l0))) : esc(p.m.text);
    return `<li><label class="${done ? 'done' : ''}"><input type="checkbox" data-prep="${esc(pk)}" ${done ? 'checked' : ''}> <span>${lbl} <span style="color:var(--faint)">${p.days.join(', ')}</span></span></label></li>`;
  });
  const li = a => a.length ? a.map(x => `<li>${esc(x)}</li>`).join('') : '<li class="none">none</li>';
  return `<div class="summary">
    <div><h3>This week</h3><div style="font-weight:600;color:var(--heading);margin-bottom:6px">${heading}</div><ul>${li(teach)}${work.map(x => `<li style="color:var(--muted)">${esc(x)}</li>`).join('')}${buffers.map(x => `<li style="color:var(--warning-fg)">${esc(x)}</li>`).join('')}${closures.map(x => `<li style="color:var(--faint)">${esc(x)}</li>`).join('')}</ul></div>
    <div><h3>Evaluations</h3><ul>${evs.length ? evs.join('') : '<li class="none">nothing handed out or due</li>'}</ul></div>
    <div><h3>Prep checklist</h3><ul style="list-style:none;padding-left:0">${prepHtml.length ? prepHtml.join('') : '<li class="none">no materials listed</li>'}</ul></div>
  </div>`;
}

function render() {
  const st = stateMap();
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  const cur = currentWeekStart();
  const main = document.getElementById('main');
  main.innerHTML = weeks.map((w, i) => {
    const isCur = w.start === cur;
    const dayCells = w.days.map(d => {
      let hidden = false;
      if (prefs.subOnly && !(d.kind === 'buffer' || (d.kind === 'slot' && d.sub_ready))) hidden = true;
      if (q && d.kind === 'slot') { const hay = [d.title, d.focus, d.slot, d.unit_name, d.week_title, ...(d.materials || []).map(m => m.text), ...(d.handouts || []), ...(d.dues || [])].join(' ').toLowerCase(); if (!hay.includes(q)) hidden = true; }
      if (q && d.kind !== 'slot') hidden = true;
      return hidden ? `<div class="day" style="opacity:.25"><div class="date"><b>${esc(fmt(d.date))}</b></div></div>` : dayHtml(d, st, d.date === todayISO);
    }).join('');
    const end = addDays(w.start, 4);
    return `<section class="week ${isCur ? 'current' : ''}" id="w-${w.start}">
      <div class="week-head"><h2>Week ${i + 1}</h2><span class="range">${fmt(w.start, { month: 'long', day: 'numeric' })} – ${fmt(end, { month: 'long', day: 'numeric', year: 'numeric' })}</span>${weekPlans(w)}${isCur ? '<span class="pill now tag">this week</span>' : ''}</div>
      ${weekSummary(w, st)}
      <div class="days">${dayCells}</div>
    </section>`;
  }).join('');
  renderStats(st);
  renderBanner();
  document.getElementById('subOnly').classList.toggle('on', !!prefs.subOnly);
}

function currentWeekStart() {
  const m = monday(todayISO);
  if (weeks.some(w => w.start === m)) return m;
  if (todayISO < weeks[0].start) return weeks[0].start;
  return weeks[weeks.length - 1].start;
}

function renderStats(st) {
  const slots = DATA.days.filter(d => d.kind === 'slot');
  const pastSlots = slots.filter(d => d.date < todayISO);
  const behind = pastSlots.filter(d => st[d.slot] && (['postponed', 'noclass'].includes(st[d.slot].status) || (st[d.slot].status === 'moved' && !st[d.slot].actual))).length;
  const dropped = slots.filter(d => st[d.slot] && st[d.slot].status === 'skipped').length;
  const unlogged = pastSlots.filter(d => !st[d.slot]).length;
  const buffersLeft = DATA.days.filter(d => d.kind === 'buffer' && d.date >= todayISO).length;
  const buffersLost = DATA.days.filter(d => d.kind === 'buffer' && st['BUFFER:' + d.date] && ['skipped', 'noclass'].includes(st['BUFFER:' + d.date].status)).length;
  const next = slots.find(d => d.date >= todayISO && (d.day_type === 'assess' || (d.dues || []).length));
  let nextHtml = '';
  if (next) {
    const before = slots.filter(d => d.date >= todayISO && d.date < next.date).length;
    const bufBefore = DATA.days.filter(d => d.kind === 'buffer' && d.date >= todayISO && d.date < next.date).length;
    const what = next.day_type === 'assess' ? next.title : next.dues[0];
    nextHtml = `<span class="stat ${before <= 2 ? 'warn' : ''}" title="next test or due date"><b>${esc(what)}</b>${fmt(next.date)} · ${before} teaching day${before === 1 ? '' : 's'} + ${bufBefore} buffer before it</span>`;
  }
  document.getElementById('stats').innerHTML = `
    <span class="stat ${behind ? 'bad' : 'good'}" title="past slots postponed, moved without a date, or without class: the next recalendar re-plans them"><b>${behind}</b>behind</span>
    ${dropped ? `<span class="stat warn" title="slots marked skipped: not taught this semester"><b>${dropped}</b>skipped</span>` : ''}
    <span class="stat ${unlogged ? 'warn' : ''}" title="past slots without a status"><b>${unlogged}</b>unlogged</span>
    <span class="stat ${buffersLeft ? '' : 'warn'}" title="buffer days still ahead (lost so far: ${buffersLost})"><b>${buffersLeft}</b>buffers left</span>
    ${nextHtml}`;
}

function renderBanner() {
  const b = document.getElementById('banner');
  const stamp = ` · built ${DATA.built} from master ${DATA.generated.master_commit || '?'}`;
  if (connected) { b.className = 'banner good'; b.textContent = `Logging to ${DATA.instance}/teaching_log.jsonl (${events.length} events)` + stamp; }
  else if (window.showDirectoryPicker) { b.className = 'banner warn'; b.innerHTML = `<b>Not logging.</b> Status changes are not being saved. Click <b>Connect folder</b> and choose the <code>${esc(DATA.instance)}</code> instance folder. ${cachedFrom ? 'Showing statuses cached ' + esc(new Date(cachedFrom).toLocaleString('en-CA')) + '.' : 'Showing statuses embedded when this page was built.'}` + stamp; }
  else { b.className = 'banner warn'; b.textContent = 'This browser has no File System Access API; open the page in Chrome to log statuses.' + stamp; }
}

// ---------- File System Access ----------
const IDB = 'gla-cal-handles';
function idb() { return new Promise((res, rej) => { const r = indexedDB.open(IDB, 1); r.onupgradeneeded = () => r.result.createObjectStore('h'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); }
async function idbGet(k) { const db = await idb(); return new Promise((res, rej) => { const t = db.transaction('h').objectStore('h').get(k); t.onsuccess = () => res(t.result); t.onerror = () => rej(t.error); }); }
async function idbSet(k, v) { const db = await idb(); return new Promise((res, rej) => { const t = db.transaction('h', 'readwrite').objectStore('h').put(v, k); t.onsuccess = () => res(); t.onerror = () => rej(t.error); }); }

async function connect(fromGesture) {
  try {
    let h = await idbGet(LS_KEY);
    if (h) {
      let p = await h.queryPermission({ mode: 'readwrite' });
      if (p !== 'granted' && fromGesture) p = await h.requestPermission({ mode: 'readwrite' });
      if (p !== 'granted') { if (fromGesture) h = null; else { setConnectLabel('Reconnect folder'); return; } }
    }
    if (!h) {
      if (!fromGesture) return;
      h = await window.showDirectoryPicker({ mode: 'readwrite' });
      if (h.name !== DATA.instance && !confirm(`You picked "${h.name}", but this calendar was built for "${DATA.instance}". Use it anyway?`)) return;
      await idbSet(LS_KEY, h);
    }
    dirHandle = h; connected = true;
    await readAll();
    setConnectLabel('Connected ✓');
    render();
  } catch (e) {
    if (e.name !== 'AbortError') { alert('Could not connect: ' + e.name + ': ' + e.message); }
  }
}
function setConnectLabel(t) { const b = document.getElementById('connect'); b.textContent = t; b.classList.toggle('primary', t !== 'Connected ✓'); }

async function readText(name) {
  try { const fh = await dirHandle.getFileHandle(name); return await (await fh.getFile()).text(); } catch (e) { if (e.name === 'NotFoundError') return ''; throw e; }
}
async function readAll() {
  const local = events;
  const log = await readText('teaching_log.jsonl');
  events = log.split('\n').filter(l => l.trim()).map(l => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean);
  // Statuses recorded while the folder was not connected live only in this
  // browser: write the ones newer than the file's last event into it.
  const last = events.reduce((m, e) => (e.ts > m ? e.ts : m), '');
  const pending = local.filter(e => e.ts > last && !events.some(f => f.ts === e.ts && f.key === e.key));
  if (pending.length) {
    const fh = await dirHandle.getFileHandle('teaching_log.jsonl', { create: true });
    const file = await fh.getFile();
    const w = await fh.createWritable({ keepExistingData: true });
    await w.seek(file.size); await w.write(pending.map(e => JSON.stringify(e) + '\n').join('')); await w.close();
    events = events.concat(pending);
  }
  const y = await readText('material_links.yaml');
  links = Object.assign({}, DATA.links);
  for (const line of y.split('\n')) { const m = line.match(/^\s*"?([^"#:][^":]*?)"?\s*:\s*"?(https?:\/\/[^"\s]+)"?\s*$/); if (m) links[m[1].trim()] = m[2]; }
  save(LS_KEY + ':cache', { events, links, at: Date.now() }); cachedFrom = null;
}
async function appendEvent(ev) {
  events.push(ev);
  if (!connected) { save(LS_KEY + ':cache', { events, links, at: Date.now() }); cachedFrom = Date.now(); render(); return; }
  const fh = await dirHandle.getFileHandle('teaching_log.jsonl', { create: true });
  const file = await fh.getFile();
  const w = await fh.createWritable({ keepExistingData: true });
  await w.seek(file.size); await w.write(JSON.stringify(ev) + '\n'); await w.close();
  save(LS_KEY + ':cache', { events, links, at: Date.now() });
  render();
}
async function writeLinks() {
  if (!connected) { alert('Connect the instance folder first so the link can be saved.'); render(); return; }
  const fh = await dirHandle.getFileHandle('material_links.yaml', { create: true });
  const w = await fh.createWritable();
  const lines = ['# material path (or unique filename) -> Google Docs URL (written by Course_Calendar.html; hand-editable)'];
  Object.keys(links).sort().forEach(k => lines.push(`"${k}": "${links[k]}"`));
  await w.write(lines.join('\n') + '\n'); await w.close();
  save(LS_KEY + ':cache', { events, links, at: Date.now() });
  render();
}

// ---------- events ----------
function setStatus(key, date, status) {
  const st = stateMap(); const prev = st[key] || {};
  const ev = { ts: new Date().toISOString(), key, date, status, actual: status === 'moved' ? (prev.actual || null) : (status === 'clear' ? null : date), note: prev.note || '' };
  if (prev.master && status !== 'clear') ev.master = true;
  if (!connected && window.showDirectoryPicker) { if (!confirm('The instance folder is not connected, so this status will NOT be saved to the log. Record it in the page only?')) return; }
  appendEvent(ev);
}
function setNote(key, note) {
  const st = stateMap(); const prev = st[key]; if (!prev) { if (!note) return; }
  const ev = Object.assign({}, prev || { key, date: null, status: 'note', actual: null }, { ts: new Date().toISOString(), note });
  if (prev && prev.note === note) return;
  appendEvent(ev);
}
function setMaster(key, on) {
  const st = stateMap(); const prev = st[key]; if (!prev) return;
  const ev = Object.assign({}, prev, { ts: new Date().toISOString() });
  if (on) ev.master = true; else delete ev.master;
  appendEvent(ev);
}
function setActual(key, actual) {
  const st = stateMap(); const prev = st[key]; if (!prev) return;
  appendEvent(Object.assign({}, prev, { ts: new Date().toISOString(), actual }));
}

document.addEventListener('click', e => {
  const t = e.target.closest('[data-status]');
  if (t) { setStatus(t.dataset.key, t.dataset.date, t.dataset.status); return; }
  const c = e.target.closest('[data-copy]');
  if (c) { navigator.clipboard.writeText(c.dataset.copy).then(() => { c.textContent = '✓'; setTimeout(() => c.textContent = '⧉', 900); }); return; }
  const l = e.target.closest('[data-link]');
  if (l) { openLinkDialog(l.dataset.link); return; }
});
document.addEventListener('change', e => {
  if (e.target.dataset.prep) { prefs.prep[e.target.dataset.prep] = e.target.checked; save(LS_KEY + ':prefs', prefs); render(); }
  if (e.target.dataset.actual) setActual(e.target.dataset.actual, e.target.value);
  if (e.target.dataset.master) setMaster(e.target.dataset.master, e.target.checked);
});
// A note is saved when the teacher leaves its box, not when the window loses focus
// mid-word; anything still being typed is saved when the page is closed.
document.addEventListener('focusout', e => { if (e.target.dataset && e.target.dataset.note !== undefined && document.hasFocus()) setNote(e.target.dataset.note, e.target.value.trim()); });
window.addEventListener('pagehide', () => { const t = document.activeElement; if (t && t.dataset && t.dataset.note !== undefined) setNote(t.dataset.note, t.value.trim()); });
document.getElementById('q').addEventListener('input', render);
document.getElementById('subOnly').onclick = () => { prefs.subOnly = !prefs.subOnly; save(LS_KEY + ':prefs', prefs); render(); };
document.getElementById('today').onclick = () => jumpToday();
document.getElementById('print').onclick = () => window.print();
document.getElementById('connect').onclick = () => connect(true);
document.getElementById('showChanges').onclick = () => { const c = document.getElementById('changes'); c.classList.toggle('hidden'); if (!c.classList.contains('hidden')) { renderChanges(); c.scrollIntoView({ behavior: 'smooth' }); } };

function jumpToday() { const el = document.getElementById('w-' + currentWeekStart()); if (el) el.scrollIntoView({ behavior: 'smooth' }); }

function openLinkDialog(name) {
  const dlg = document.getElementById('linkDlg');
  document.getElementById('linkFor').textContent = name;
  document.getElementById('linkUrl').value = links[name] || '';
  dlg.onclose = () => { const v = dlg.returnValue; if (v === 'save') { const u = document.getElementById('linkUrl').value.trim(); if (u) { links[name] = u; writeLinks(); } } else if (v === 'clear') { delete links[name]; writeLinks(); } };
  dlg.showModal();
}

document.addEventListener('keydown', e => {
  if (e.target.matches('input, textarea')) return;
  const td = byDate[todayISO]; const key = td ? keyOf(td) : null;
  const map = { t: 'taught', p: 'partial', o: 'postponed', m: 'moved', s: 'skipped', c: 'noclass' };
  if (map[e.key] && key) { setStatus(key, todayISO, map[e.key]); }
  else if (e.key === 'n' && key) { const ta = document.querySelector(`textarea[data-note="${key}"]`); if (ta) { ta.focus(); e.preventDefault(); } }
  else if (e.key === 'g') jumpToday();
  else if (e.key === '/') { document.getElementById('q').focus(); e.preventDefault(); }
});

function renderChanges() {
  const st = stateMap();
  const rows = [];
  for (const d of DATA.days) {
    const key = keyOf(d); if (!key) continue;
    const s = st[key];
    if (!s) continue;
    rows.push(`<tr><td>${esc(fmt(d.date, { month: 'short', day: 'numeric' }))}</td><td class="mono">${esc(key)}</td><td>${esc(d.title || d.label || '')}</td><td>${esc((d.kind === 'buffer' ? BUFFER_LABELS : LABELS)[s.status] || s.status)}</td><td>${esc(s.actual && s.actual !== d.date ? fmt(s.actual, { month: 'short', day: 'numeric' }) : '')}</td><td>${esc(s.note || '')}</td></tr>`);
  }
  const units = {};
  DATA.days.filter(d => d.kind === 'slot').forEach(d => { const u = d.unit_name || d.week_key; units[u] = units[u] || { n: 0, taught: 0, partial: 0, postponed: 0, moved: 0, skipped: 0, noclass: 0, unlogged: 0 }; units[u].n++; const s = st[d.slot]; if (!s) { if (d.date < todayISO) units[u].unlogged++; } else units[u][s.status] = (units[u][s.status] || 0) + 1; });
  const unitRows = Object.entries(units).map(([u, c]) => `<tr><td>${esc(u)}</td><td>${c.n}</td><td>${c.taught}</td><td>${c.partial}</td><td>${c.postponed}</td><td>${c.moved}</td><td>${c.skipped}</td><td>${c.noclass}</td><td>${c.unlogged}</td></tr>`).join('');
  document.getElementById('changes').innerHTML = `<h2>What changed</h2>
    <p style="color:var(--muted)">${events.length} log events. Per-unit tally, then every slot with a status. Run <code>audit_log.py</code> on the instance folder for the semester-end report with override suggestions.</p>
    <table><tr><th>Unit / block</th><th>Slots</th><th>Taught</th><th>Partial</th><th>Postponed</th><th>Moved</th><th>Skipped</th><th>No class</th><th>Unlogged (past)</th></tr>${unitRows}</table><br>
    <table><tr><th>Planned</th><th>Slot</th><th>Title</th><th>Status</th><th>Actual</th><th>Note</th></tr>${rows.join('') || '<tr><td colspan=6 class="none">no statuses recorded</td></tr>'}</table>`;
}

// ---------- boot ----------
document.getElementById('h1').innerHTML = `${esc(DATA.course.code || '')} <small>${esc(DATA.course.name || '')} · ${esc(DATA.semester.name || DATA.instance)} · ${esc(DATA.course.teacher || '')}</small>`;
document.getElementById('foot').innerHTML = `Keyboard: <kbd>t</kbd> taught · <kbd>p</kbd> partial · <kbd>o</kbd> postponed · <kbd>m</kbd> moved · <kbd>s</kbd> skipped · <kbd>c</kbd> no class (today's slot) · <kbd>n</kbd> note · <kbd>g</kbd> go to today · <kbd>/</kbd> search. ${DATA.packets.length ? 'Emergency sub packets: ' + DATA.packets.map(p => `<a href="${esc(p.href)}" target="_blank">${esc(p.label)}</a>`).join(' · ') + '.' : ''} Cut by compression: ${DATA.cuts.map(c => esc(c.slot)).join(', ') || 'none'}. Regenerate with the semester skill; the log and links files are never overwritten by a rebuild.`;
render();
connect(false).then(() => { jumpToday(); });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

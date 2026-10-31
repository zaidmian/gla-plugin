#!/usr/bin/env python3
"""
check_output: prove that finished documents carry no marker text and no em dash.

    python3 check_output.py PATH [PATH ...]      files or directories (.docx, .pdf)

Exit 1 with one line per hit (file:location: snippet), exit 0 when clean.
Run it over every .docx and .pdf before delivering; verify.py runs it over
the example builds.
"""

import os
import re
import sys

PATTERNS = ["Inferred", "please review", "not provided", "[Information", "—"]
_RX = re.compile("|".join(re.escape(p) for p in PATTERNS))


def _snippet(text, m, width=40):
    s = max(0, m.start() - width)
    e = min(len(text), m.end() + width)
    return " ".join(text[s:e].split())


def _docx_texts(path):
    from docx import Document
    d = Document(path)
    for i, p in enumerate(d.paragraphs, 1):
        yield f"para {i}", p.text
    for ti, t in enumerate(d.tables, 1):
        for ri, r in enumerate(t.rows, 1):
            for ci, c in enumerate(r.cells, 1):
                yield f"table {ti} r{ri} c{ci}", c.text
    for si, s in enumerate(d.sections, 1):
        for part, name in ((s.header, "header"), (s.footer, "footer")):
            for p in part.paragraphs:
                yield f"section {si} {name}", p.text
            for t in part.tables:
                for r in t.rows:
                    for c in r.cells:
                        yield f"section {si} {name} table", c.text


def _pdf_texts(path):
    import fitz
    doc = fitz.open(path)
    for i, page in enumerate(doc, 1):
        yield f"page {i}", page.get_text()


def scan_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        source = _docx_texts(path)
    elif ext == ".pdf":
        source = _pdf_texts(path)
    else:
        return []
    hits = []
    for where, text in source:
        for m in _RX.finditer(text or ""):
            hits.append(f"{path}:{where}: ...{_snippet(text, m)}...")
    return hits


def scan(paths):
    hits = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if name.lower().endswith((".docx", ".pdf")) and not name.startswith("~$"):
                    hits.extend(scan_file(os.path.join(p, name)))
        elif os.path.exists(p):
            hits.extend(scan_file(p))
        else:
            hits.append(f"{p}: not found")
    return hits


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    hits = scan(argv)
    for h in hits:
        print(h)
    if hits:
        print(f"{len(hits)} hit(s)")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

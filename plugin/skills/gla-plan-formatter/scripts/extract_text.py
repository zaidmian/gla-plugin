#!/usr/bin/env python3
"""
extract_text: print the text of a teacher's source document once, for mapping.

    python3 extract_text.py FILE [--out notes.txt]

.docx   paragraphs in order (headings marked "#", "##", ...), then each table
        as "[table N]" followed by pipe-separated rows. Uses python-docx when
        present, otherwise reads the Word XML with the standard library.
.pdf    page text with "--- page N ---" markers. Uses PyMuPDF (fitz), or
        pdftotext when that is on PATH.
.html   tags stripped, one block per line.
.md .txt .yaml .yml .json .csv   printed as is.

With --out the text is written to that file and only a one-line summary is
printed, which keeps the document out of the chat.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree

PLAIN = {".md", ".markdown", ".txt", ".yaml", ".yml", ".json", ".csv"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ExtractError(RuntimeError):
    pass


def _heading_prefix(style_name):
    """'Heading 2' -> '## ', 'Title' -> '# ', anything else -> ''."""
    name = (style_name or "").strip()
    if name.lower() == "title":
        return "# "
    m = re.match(r"heading\s*(\d)", name, flags=re.I)
    return "#" * int(m.group(1)) + " " if m else ""


def _rows_text(rows):
    """Pipe-join each row, dropping the repeats a merged cell produces."""
    out = []
    for cells in rows:
        kept, last = [], object()
        for key, text in cells:
            if key is not None and key == last:
                continue
            kept.append(" ".join(text.split()))
            last = key
        out.append(" | ".join(kept))
    return out


def docx_text_python_docx(path):
    import docx  # python-docx
    d = docx.Document(path)
    lines = []
    for p in d.paragraphs:
        text = p.text.strip()
        if text:
            style = p.style.name if p.style is not None else ""
            lines.append(_heading_prefix(style) + text)
    for i, t in enumerate(d.tables, 1):
        lines.append("")
        lines.append(f"[table {i}]")
        lines.extend(_rows_text([[(id(c._tc), c.text) for c in r.cells] for r in t.rows]))
    return "\n".join(lines) + "\n"


def docx_text_stdlib(path):
    """The same output as docx_text_python_docx, from the raw Word XML."""
    with zipfile.ZipFile(path) as z:
        body = ElementTree.fromstring(z.read("word/document.xml")).find(f"{W}body")
        styles = {}
        if "word/styles.xml" in z.namelist():
            for s in ElementTree.fromstring(z.read("word/styles.xml")).iter(f"{W}style"):
                name = s.find(f"{W}name")
                styles[s.get(f"{W}styleId")] = name.get(f"{W}val") if name is not None else ""

    def para_text(p):
        parts = []
        for el in p.iter():
            if el.tag == f"{W}t":
                parts.append(el.text or "")
            elif el.tag == f"{W}tab":
                parts.append("\t")
            elif el.tag in (f"{W}br", f"{W}cr"):
                parts.append("\n")
        return "".join(parts)

    lines, tables = [], []
    if body is None:
        return ""
    for child in body:
        if child.tag == f"{W}p":
            text = para_text(child).strip()
            if text:
                ps = child.find(f"{W}pPr/{W}pStyle")
                style = styles.get(ps.get(f"{W}val"), ps.get(f"{W}val")) if ps is not None else ""
                lines.append(_heading_prefix(style) + text)
        elif child.tag == f"{W}tbl":
            tables.append(child)
    for i, tbl in enumerate(tables, 1):
        rows = []
        for tr in tbl.findall(f"{W}tr"):
            cells = []
            for n, tc in enumerate(tr.findall(f"{W}tc")):
                text = "\n".join(para_text(p) for p in tc.findall(f"{W}p"))
                merged = tc.find(f"{W}tcPr/{W}vMerge")
                if merged is not None and merged.get(f"{W}val") != "restart":
                    text = ""          # continuation of a vertical merge
                cells.append((None, text))
            rows.append(cells)
        lines.append("")
        lines.append(f"[table {i}]")
        lines.extend(_rows_text(rows))
    return "\n".join(lines) + "\n"


def docx_text(path):
    try:
        import docx  # noqa: F401
    except Exception:
        return docx_text_stdlib(path)
    return docx_text_python_docx(path)


def pdf_text(path):
    try:
        import fitz  # PyMuPDF
    except Exception:
        fitz = None
    if fitz is not None:
        doc = fitz.open(path)
        return "".join(f"--- page {i} ---\n{page.get_text().rstrip()}\n"
                       for i, page in enumerate(doc, 1))
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        if out.returncode == 0:
            pages = out.stdout.split("\f")
            return "".join(f"--- page {i} ---\n{p.rstrip()}\n"
                           for i, p in enumerate(pages, 1) if p.strip())
    raise ExtractError("cannot read the PDF: neither PyMuPDF (fitz) nor pdftotext is available "
                       "in this runtime. Ask the teacher to paste the text, or to send a .docx.")


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "header", "footer", "table", "ul", "ol", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
            m = re.fullmatch(r"h([1-6])", tag)
            if m:
                self.parts.append("#" * int(m.group(1)) + " ")
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(raw):
    p = _HTMLText()
    p.feed(raw)
    lines = []
    for line in "".join(p.parts).splitlines():
        line = " ".join(html.unescape(line).split()).strip(" |")
        if line and line != "#":
            lines.append(line)
    return "\n".join(lines) + "\n"


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        raise ExtractError(f"no such file: {path}")
    if ext == ".docx":
        return docx_text(path)
    if ext == ".pdf":
        return pdf_text(path)
    if ext in (".html", ".htm"):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return html_text(fh.read())
    if ext in PLAIN:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if ext == ".doc":
        raise ExtractError("a .doc (Word 97-2003) file cannot be read here; ask the teacher to "
                           "save it as .docx or PDF, or to paste the text.")
    raise ExtractError(f"unsupported file type '{ext or '(none)'}'; supported: .docx .pdf .html "
                       + " ".join(sorted(PLAIN)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--out", help="write the text here and print a one-line summary")
    a = ap.parse_args()
    try:
        text = extract(a.file)
    except ExtractError as e:
        print(f"extract_text: {e}", file=sys.stderr)
        return 2
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError) as e:
        print(f"extract_text: {a.file} is not a readable .docx ({e})", file=sys.stderr)
        return 2
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {a.out} ({len(text.splitlines())} lines, {len(text)} characters)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

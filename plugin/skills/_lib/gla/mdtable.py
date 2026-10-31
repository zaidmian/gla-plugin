"""Read pipe tables out of markdown."""
import re

_SEP = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def tables(text):
    """Yield (header_cells, rows, first_line_number) for every pipe table.
    rows are lists of (line_number, cells). Line numbers are 1-based."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and _SEP.match(lines[i + 1].strip()):
            header = _cells(lines[i])
            start = i + 1
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append((j + 1, _cells(lines[j])))
                j += 1
            yield header, rows, start
            i = j
        else:
            i += 1


def find_table(text, *required_headers):
    """The first table whose header contains every name given (case-insensitive),
    as (header, rows, line) or None."""
    want = [h.lower() for h in required_headers]
    for header, rows, line in tables(text):
        low = [h.lower() for h in header]
        if all(any(w == h or w in h for h in low) for w in want):
            return header, rows, line
    return None


def column(header, name):
    """Index of the first header cell equal to or containing name (case-insensitive)."""
    name = name.lower()
    for k, h in enumerate(header):
        if h.lower() == name:
            return k
    for k, h in enumerate(header):
        if name in h.lower():
            return k
    raise KeyError(name)


def percent(cell):
    """'9%' -> 9.0, '**65**' -> 65.0, '—' or '' -> None."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*%?", cell.replace("*", ""))
    return float(m.group(1)) if m else None


def is_total(cells):
    """True for a table's own Total row."""
    return bool(cells) and cells[0].replace("*", "").strip().lower() == "total"

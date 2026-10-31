#!/usr/bin/env python3
"""
render_env: find LibreOffice and a page rasteriser wherever the skill runs.

Runtimes: the claude.ai / Claude Desktop cloud sandbox (soffice wrapper under
/mnt/skills, pdftoppm), Claude Desktop Cowork's local VM (unknown; PATH
lookup), and macOS with Claude Code (LibreOffice.app, PyMuPDF). Every failure
carries a fixed message that SKILL.md tells Claude to relay verbatim.
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SANDBOX_WRAPPER = "/mnt/skills/public/docx/scripts/office/soffice.py"
MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
WINDOWS_SOFFICE = [os.path.join(os.environ.get(v, d), "LibreOffice", "program", "soffice.exe")
                   for v, d in (("ProgramFiles", r"C:\Program Files"), ("ProgramFiles(x86)", r"C:\Program Files (x86)"))]

MSG_NO_SOFFICE = (
    "PDF export skipped: LibreOffice not found. Looked for GLA_SOFFICE, "
    f"{SANDBOX_WRAPPER}, soffice/libreoffice on PATH, {MAC_SOFFICE}, and the Windows Program Files folders. "
    "The .docx was written; open it in Word, or install LibreOffice "
    "(https://www.libreoffice.org) to get a PDF."
)
MSG_CONVERT_FAILED = (
    "PDF export failed: LibreOffice exited without producing {name}.pdf. "
    "The .docx is intact. Last stderr lines: {tail}"
)
MSG_NO_RASTER = (
    "Page preview skipped: neither PyMuPDF (fitz) nor pdftoppm is available. "
    "The PDF is intact; open it directly to check the layout."
)


class PdfExportUnavailable(RuntimeError):
    pass


class PdfExportFailed(RuntimeError):
    pass


class RasterizeUnavailable(RuntimeError):
    pass


def find_soffice():
    """Return ("wrapper", path) | ("binary", path) | None."""
    env = os.environ.get("GLA_SOFFICE")
    if env and os.path.exists(env):
        return ("wrapper", env) if env.endswith(".py") else ("binary", env)
    if os.path.exists(SANDBOX_WRAPPER):
        return ("wrapper", SANDBOX_WRAPPER)
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return ("binary", p)
    for p in [MAC_SOFFICE] + WINDOWS_SOFFICE:
        if os.path.exists(p):
            return ("binary", p)
    return None


def to_pdf(docx_path, outdir=None, timeout=180):
    found = find_soffice()
    if not found:
        raise PdfExportUnavailable(MSG_NO_SOFFICE)
    kind, path = found
    docx_path = os.path.abspath(docx_path)
    outdir = outdir or os.path.dirname(docx_path) or "."
    if kind == "wrapper":
        cmd = [sys.executable, path, "--headless", "--convert-to", "pdf",
               "--outdir", outdir, docx_path]
    else:
        # A private profile per process: concurrent conversions sharing one
        # profile make LibreOffice exit silently without writing the PDF.
        profile = Path(tempfile.gettempdir()) / f"gla_lo_profile_{os.getpid()}"
        cmd = [path, f"-env:UserInstallation={profile.as_uri()}", "--headless",
               "--norestore", "--convert-to", "pdf", "--outdir", outdir, docx_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    finally:
        if kind == "binary":
            shutil.rmtree(profile, ignore_errors=True)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if proc.returncode != 0 or not os.path.exists(pdf):
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-5:])
        raise PdfExportFailed(MSG_CONVERT_FAILED.format(
            name=os.path.splitext(os.path.basename(docx_path))[0], tail=tail or "(none)"))
    return pdf


def _fitz():
    try:
        import fitz  # PyMuPDF
        return fitz
    except Exception:
        return None


def rasterize(pdf_path, pages=(1,), dpi=100, outdir=None):
    """Render the given 1-based pages to PNG. Returns the list of PNG paths."""
    pdf_path = os.path.abspath(pdf_path)
    outdir = outdir or os.path.dirname(pdf_path)
    stem = os.path.join(outdir, os.path.splitext(os.path.basename(pdf_path))[0])
    fitz = _fitz()
    outs = []
    if fitz:
        doc = fitz.open(pdf_path)
        for p in pages:
            if p < 1 or p > len(doc):
                continue
            out = f"{stem}_p{p}.png"
            doc[p - 1].get_pixmap(dpi=dpi).save(out)
            outs.append(out)
        return outs
    if shutil.which("pdftoppm"):
        for p in pages:
            out = f"{stem}_p{p}"
            subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(p), "-l", str(p),
                            "-singlefile", pdf_path, out], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            outs.append(out + ".png")
        return outs
    raise RasterizeUnavailable(MSG_NO_RASTER)


def page_count(pdf_path):
    fitz = _fitz()
    if fitz:
        return len(fitz.open(pdf_path))
    if shutil.which("pdfinfo"):
        out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[1])
    import re
    data = open(pdf_path, "rb").read()
    return len(re.findall(rb"/Type\s*/Page[^s]", data))   # approximate


def describe():
    fitz = _fitz()
    raster = "fitz" if fitz else ("pdftoppm" if shutil.which("pdftoppm") else None)
    try:
        import docx
        pdx = getattr(docx, "__version__", "present")
    except Exception:
        pdx = None
    return {
        "platform": platform.system().lower(),
        "python": platform.python_version(),
        "python_docx": pdx,
        "soffice": find_soffice(),
        "rasterizer": raster,
        "sandbox": os.path.exists("/mnt/skills"),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(describe(), indent=2))

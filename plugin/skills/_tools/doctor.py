#!/usr/bin/env python3
"""Check what the GLA skills need on this computer, and install the Python part.

    python3 doctor.py where      the folders this install reads
    python3 doctor.py doctor     check Python, its packages, and the tools the skills call
    python3 doctor.py setup [--yes]
                                 doctor, then install the missing Python packages with
                                 pip --user (asks first unless --yes)

Run it through gla (`gla doctor`). Required: Python 3.9 or newer with PyYAML
and python-docx. The rest is needed only by some courses or outputs: git (a
course folder's history, `check_course.py --changed`), a JDK (Java samples),
Node.js (p5.js samples), LibreOffice (PDF copies of plan documents), and
Chrome or Edge (the teacher calendar page). Exit 1 when something required
is missing.
"""
import importlib.util
import os
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
from gla import paths  # noqa: E402

REQUIREMENTS = os.path.join(paths.SKILLS, "requirements.txt")
PACKAGES = [("yaml", "PyYAML", True), ("docx", "python-docx", True), ("fitz", "PyMuPDF", False)]
WINDOWS = platform.system() == "Windows"
MAC = platform.system() == "Darwin"


def version():
    """The plugin build stamp, or the Skills commit in a development checkout."""
    stamp = os.path.join(paths.TEACHING_ROOT, "VERSION")
    if os.path.exists(stamp):
        with open(stamp, encoding="utf-8") as f:
            return f.read().strip()
    try:
        r = subprocess.run(["git", "-C", paths.SKILLS, "describe", "--always", "--dirty"], capture_output=True, text=True)
    except OSError:   # no git on this computer
        return "development checkout"
    return ("development checkout, Skills %s" % r.stdout.strip()) if r.returncode == 0 else "development checkout"


def where():
    print("GLA_ROOT    %s" % paths.TEACHING_ROOT)
    for name, p in (("Skills", paths.SKILLS), ("Standards", paths.STANDARDS), ("Curriculum", paths.CURRICULUM),
                    ("Calendars", paths.CALENDARS)):
        print("%-11s %s%s" % (name, p, "" if os.path.isdir(p) else "   (missing)"))
    print("Version     %s" % version())
    return 0


def found(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def first_existing(*candidates):
    return next((c for c in candidates if c and os.path.exists(c)), None)


def tool_rows():
    pf = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    soffice = found("soffice", "libreoffice") or first_existing(
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        *[os.path.join(p, "LibreOffice", "program", "soffice.exe") for p in pf])
    chrome = found("google-chrome", "chrome", "msedge", "chromium") or first_existing(
        "/Applications/Google Chrome.app", "/Applications/Microsoft Edge.app",
        *[os.path.join(p, "Google", "Chrome", "Application", "chrome.exe") for p in pf],
        *[os.path.join(p, "Microsoft", "Edge", "Application", "msedge.exe") for p in pf])
    java = found("javac") and found("java")
    how = {
        "git": "winget install Git.Git" if WINDOWS else ("run `xcode-select --install`" if MAC else "install git from your package manager"),
        "jdk": "winget install EclipseAdoptium.Temurin.21.JDK" if WINDOWS else "install the Temurin 21 JDK from https://adoptium.net",
        "node": "winget install OpenJS.NodeJS.LTS" if WINDOWS else "install the LTS from https://nodejs.org",
        "lo": "winget install TheDocumentFoundation.LibreOffice" if WINDOWS else "install from https://www.libreoffice.org",
        "chrome": "install Google Chrome or Microsoft Edge",
    }
    return [
        ("git", found("git"), "course history and `check --changed`", how["git"]),
        ("JDK (javac, java)", java, "Java courses: compiling and running code samples", how["jdk"]),
        ("Node.js", found("node"), "p5.js courses: checking sketch syntax", how["node"]),
        ("LibreOffice", soffice, "PDF copies of plan documents", how["lo"]),
        ("Chrome or Edge", chrome, "the teacher calendar page (folder access)", how["chrome"]),
    ]


def missing_packages(required_only=True):
    return [(mod, pkg) for mod, pkg, req in PACKAGES if (req or not required_only) and importlib.util.find_spec(mod) is None]


def doctor():
    ok = True
    py = "%d.%d.%d" % sys.version_info[:3]
    good = sys.version_info >= (3, 9)
    ok &= good
    print("%-8s Python %s at %s%s" % ("ok" if good else "MISSING", py, sys.executable, "" if good else "   (3.9 or newer is needed)"))
    for mod, pkg, req in PACKAGES:
        have = importlib.util.find_spec(mod) is not None
        ok &= have or not req
        print("%-8s %s%s" % ("ok" if have else ("MISSING" if req else "optional"), pkg,
                             "" if have else ("   (run `gla setup`)" if req else "   (only for reading PDF sources)")))
    for name, path, why, how in tool_rows():
        print("%-8s %s%s" % ("ok" if path else "optional", name, "" if path else "   (%s; %s)" % (why, how)))
    for name, p in (("Standards", paths.STANDARDS), ("Curriculum", paths.CURRICULUM), ("Calendars", paths.CALENDARS)):
        have = os.path.isdir(p)
        ok &= have
        print("%-8s %s data%s" % ("ok" if have else "MISSING", name, "" if have else "   (%s; reinstall the plugin)" % p))
    print("Version  %s" % version())
    if WINDOWS and os.path.basename(sys.executable).lower().startswith("python") and not shutil.which("python3"):
        print("Note     on this computer the Python command is `python`, not `python3`.")
    print("All required parts are present." if ok else "Something required is missing (see above).")
    return 0 if ok else 1


def setup(yes=False):
    doctor()
    need = missing_packages()
    if not need:
        print("\nNothing to install.")
        return doctor_quiet()
    names = " ".join(pkg for _, pkg in need)
    print("\nMissing Python packages: %s" % names)
    if not yes:
        try:
            answer = input("Install them now with pip (for this user only)? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes"):
            print("Not installed. Run `gla setup --yes` to install without the question.")
            return 1
    cmd = [sys.executable, "-m", "pip", "install", "--user", "-r", REQUIREMENTS]
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode:
        print("pip failed. If it says pip is missing, run: %s -m ensurepip --user" % sys.executable)
        return 1
    return doctor_quiet()


def doctor_quiet():
    still = missing_packages()
    if still:
        print("Still missing: %s" % ", ".join(pkg for _, pkg in still))
        return 1
    print("Python packages ready.")
    return 0


def main(argv):
    if not argv or argv[0] not in ("where", "doctor", "setup"):
        print(__doc__.strip())
        return 2
    if argv[0] == "where":
        return where()
    if argv[0] == "doctor":
        return doctor()
    return setup("--yes" in argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

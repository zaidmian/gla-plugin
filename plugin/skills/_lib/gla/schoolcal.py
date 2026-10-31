"""The school calendar a semester config can name.

`Teaching/Calendars/<year>.yaml` holds one school year's dates for every
course: each term's first and last day and exam window, the holidays, the
PA days, and the school-wide events. A semester config that says

    school_calendar: "2026-27 S2"

takes from it the term's dates (where its own `semester:` block leaves
them empty), the holidays and PA days that fall in the term, and the events
that fall in it. The config's own lists add the course's items. An event in
the config named like a school event and given no dates takes the school
dates and sets its own `buffers` and `note` (it is dropped when it falls in
the other term); a school event the config does not name keeps 0 buffers
and the school's note. A config value wins over the
school file on any clash. resolve() is idempotent.
"""
import copy
import datetime as dt
import os
import re

import yaml

from . import paths

REF = re.compile(r"^\s*(\d{4}-\d{2})\s+(S\d)\s*$")
TERM_KEYS = ("first_day", "last_day", "exam_start", "exam_end")


class SchoolCalendarError(ValueError):
    pass


def path(year):
    return os.path.join(paths.CALENDARS, "%s.yaml" % year)


def load(year):
    p = path(year)
    if not os.path.exists(p):
        raise SchoolCalendarError("no school calendar %s" % os.path.relpath(p, paths.TEACHING_ROOT))
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _d(x):
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x))


def _todo(v):
    return v in (None, "") or str(v).strip().upper().startswith("TODO")


def resolve(cfg):
    """A copy of cfg with the named school calendar merged in (cfg itself when it names none)."""
    ref = cfg.get("school_calendar")
    if not ref:
        return cfg
    m = REF.match(str(ref))
    if not m:
        raise SchoolCalendarError("school_calendar %r is not \"YYYY-YY Sn\" (for example \"2026-27 S2\")" % ref)
    year, term = m.groups()
    school = load(year)
    where = "Calendars/%s.yaml" % year
    tdates = (school.get("semesters") or {}).get(term)
    if not isinstance(tdates, dict):
        raise SchoolCalendarError("%s has no semesters.%s" % (where, term))
    out = copy.deepcopy(cfg)
    sem = out.setdefault("semester", {}) or {}
    out["semester"] = sem
    for k in TERM_KEYS:
        if _todo(sem.get(k)):
            if _todo(tdates.get(k)):
                raise SchoolCalendarError("%s semesters.%s.%s is still TODO" % (where, term, k))
            sem[k] = str(tdates[k])
    lo, hi = _d(sem["first_day"]), _d(sem["exam_end"])

    def inside(start, end=None):
        return not (_d(end or start) < lo or _d(start) > hi)

    hols = list(out.get("holidays") or [])
    have = {(h.get("name"), str(h.get("start"))) for h in hols if isinstance(h, dict)}
    for h in school.get("holidays") or []:
        if _todo(h.get("start")):
            raise SchoolCalendarError("%s holiday %r has no dates" % (where, h.get("name")))
        if inside(h["start"], h.get("end")) and (h.get("name"), str(h["start"])) not in have:
            hols.append({"name": h.get("name"), "start": str(h["start"]), "end": str(h.get("end") or h["start"])})
    out["holidays"] = hols

    pas = list(out.get("pa_days") or [])
    have = {str(p["date"] if isinstance(p, dict) else p) for p in pas}
    for p in school.get("pa_days") or []:
        date = str(p["date"] if isinstance(p, dict) else p)
        if inside(date) and date not in have:
            pas.append(dict(p, date=date) if isinstance(p, dict) else date)
    out["pa_days"] = pas

    events = [dict(e) for e in out.get("events") or [] if isinstance(e, dict)]
    by_name = {e.get("name"): e for e in events}
    for e in school.get("events") or []:
        if _todo(e.get("start")) or not inside(e["start"], e.get("end")):
            continue
        mine = by_name.get(e.get("name"))
        if mine is None:
            events.append({k: v for k, v in (("name", e.get("name")), ("start", str(e["start"])),
                                             ("end", str(e.get("end") or e["start"])), ("buffers", 0),
                                             ("note", e.get("note"))) if v not in (None, "")})
        elif _todo(mine.get("start")):
            mine["start"] = str(e["start"])
            mine["end"] = str(e.get("end") or e["start"])
            if not mine.get("note") and e.get("note"):
                mine["note"] = e["note"]
    school_names = {e.get("name") for e in school.get("events") or []}
    kept = []
    for e in events:
        if _todo(e.get("start")):
            if e.get("name") in school_names:
                continue   # a school event that falls in the other term
            raise SchoolCalendarError("event %r has no dates and %s has no event by that name" % (e.get("name"), where))
        kept.append(e)
    out["events"] = kept
    out["_school_calendar"] = "`%s`, %s" % (where, term)
    return out


def check(p):
    """Problems in one school calendar file: its shape, and every date a real
    YYYY-MM-DD (or TODO) with each range in order. TODO is allowed."""
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = []
    year = os.path.splitext(os.path.basename(p))[0]
    if str(data.get("school_year")) != year:
        out.append("school_year %r does not match the file name %s" % (data.get("school_year"), year))

    def date(v, what):
        if _todo(v):
            return None
        try:
            return _d(v)
        except ValueError:
            out.append("%s: %r is not a YYYY-MM-DD date" % (what, v))
            return None
    terms = data.get("semesters") or {}
    if not isinstance(terms, dict) or not terms:
        out.append("no semesters")
    for t, d in (terms.items() if isinstance(terms, dict) else []):
        got = [date((d or {}).get(k), "semesters.%s.%s" % (t, k)) for k in TERM_KEYS]
        if all(got) and not got[0] <= got[1] < got[2] <= got[3]:
            out.append("semesters.%s: first_day <= last_day < exam_start <= exam_end does not hold" % t)
    for key in ("holidays", "events"):
        for k, e in enumerate(data.get(key) or []):
            if not isinstance(e, dict) or not e.get("name"):
                out.append("%s[%d] has no name" % (key, k))
                continue
            a, b = date(e.get("start"), "%s %r start" % (key, e["name"])), date(e.get("end") or e.get("start"), "%s %r end" % (key, e["name"]))
            if a and b and b < a:
                out.append("%s %r ends before it starts" % (key, e["name"]))
            if "buffers" in e:
                out.append("event %r sets buffers; each course config sets its own" % e["name"])
    for k, x in enumerate(data.get("pa_days") or []):
        date(x.get("date") if isinstance(x, dict) else x, "pa_days[%d]" % k)
    return out

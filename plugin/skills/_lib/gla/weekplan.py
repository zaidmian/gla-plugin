"""Load week_plan.yaml files and check them against the shared schema.

The schema is Standards/templates/Weekly_Plan_Schema.yaml itself: its keys
are the keys a week plan must carry, so the check follows the template when
the template changes.
"""
import functools
import yaml

from . import paths, placeholders, slots

DAY_TYPES = ("teach", "lab", "exercise", "studio", "flex", "assess")
SUB_READY_TYPES = ("exercise", "lab", "studio", "flex")
EVAL_KINDS = ("exercise", "assignment", "test", "culminating", "milestone")
# Keys of the template that may be absent from a real plan.
OPTIONAL = {"notes", "resources", "dates", "school", "teacher"}
# Keys that may hold an empty string in a master plan; any other empty value,
# or a zero below, is a template value nobody filled in.
MAY_BE_EMPTY = OPTIONAL | {"student", "date"}
NOT_ZERO = {"minutes", "week", "grade"}


@functools.lru_cache(maxsize=None)
def template():
    with open(paths.WEEKLY_PLAN_SCHEMA, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def unfilled(node, where=""):
    """[(key path, problem)] for empty strings, zeros and template placeholders."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            key = "%s.%s" % (where, k) if where else str(k)
            if (v is None or v == "") and k not in MAY_BE_EMPTY:
                out.append((key, "is empty"))
            elif k in NOT_ZERO and v in (0, "0"):
                out.append((key, "is 0"))
            else:
                out.extend(unfilled(v, key))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(unfilled(v, "%s[%d]" % (where, i)))
    elif isinstance(node, str):
        found = placeholders.find(node, markdown=False)
        if found:
            out.append((where, "holds the placeholder %s" % ", ".join(found)))
    return out


def check(plan, path, report, master=True):
    """Add findings for one week plan. master=False skips the date-placeholder rule
    (instance copies carry real dates)."""
    tpl = template()
    for key in tpl:
        if key not in plan and key not in OPTIONAL:
            report.error("weekplan-key", path, "missing top-level key %r" % key)
    for key in tpl.get("metadata", {}):
        if key not in (plan.get("metadata") or {}) and key not in OPTIONAL:
            report.warn("weekplan-key", path, "metadata missing %r" % key)

    meta = plan.get("metadata") or {}
    prefix = meta.get("slot_prefix") or ""
    days = plan.get("daily_lessons") or []
    if not days:
        report.error("weekplan-days", path, "daily_lessons is empty")
    seen = set()
    for d in days:
        slot = str(d.get("slot") or "")
        where = "day %s" % d.get("day")
        if not slots.is_slot(slot):
            report.error("weekplan-slot", path, "%s: slot %r is not a slot ID" % (where, slot))
        elif prefix and slots.week_key(slot) != prefix:
            report.error("weekplan-slot", path, "%s: slot %s is outside slot_prefix %s" % (where, slot, prefix))
        if slot in seen:
            report.error("weekplan-slot", path, "slot %s appears twice" % slot)
        seen.add(slot)
        dt = d.get("day_type")
        if dt not in DAY_TYPES:
            report.error("weekplan-daytype", path, "%s: day_type %r is not one of %s" % (where, dt, ", ".join(DAY_TYPES)))
        if dt in SUB_READY_TYPES and d.get("sub_ready") is not True:
            report.warn("weekplan-subready", path, "%s: %s day should be sub_ready: true (Style Guide Core §8)" % (where, dt))
        acts = d.get("activities") or []
        if acts:
            total = sum(int(a.get("minutes") or 0) for a in acts if isinstance(a, dict))
            if not 40 <= total <= 60:
                report.warn("weekplan-minutes", path, "%s: activities total %d minutes (about 50 expected)" % (where, total))
            if dt == "teach" and not all(isinstance(a, dict) and a.get("what") for a in acts):
                report.warn("weekplan-activity", path, "%s: every activity needs a 'what'" % where)
        if master:
            date = str(d.get("date") or "")
            if date and not date.startswith("{{"):
                report.error("weekplan-dated", path, "%s: master carries a real date %r" % (where, date))

    if master:
        for where, problem in unfilled(plan):
            report.error("placeholder", path, "%s %s" % (where, problem))

    for e in plan.get("evaluations") or []:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        if e.get("kind") not in EVAL_KINDS:
            report.warn("weekplan-eval", path, "evaluation %s: kind %r is not one of %s" % (e["name"], e.get("kind"), ", ".join(EVAL_KINDS)))
        for k in ("handed_out", "due"):
            v = str(e.get(k) or "")
            if v and not slots.is_slot(v):
                report.error("weekplan-eval", path, "evaluation %s: %s %r is not a slot ID" % (e["name"], k, v))
    return plan

"""Load a course repo's course.yaml and check it against the shared schema.

Required keys come from Standards/templates/Course_Config_Schema.yaml (the
lines marked [required]), so the check follows the schema file.
"""
import functools
import os
import re

import yaml

from . import assessment, curriculum, paths

TYPES = ("Academic", "Applied", "De-streamed", "Open", "University Preparation", "College Preparation",
         "University/College Preparation", "Workplace Preparation", "Locally Developed")
DECK_THEMES = ("glass", "gla")


@functools.lru_cache(maxsize=None)
def required_keys():
    keys = []
    with open(paths.COURSE_CONFIG_SCHEMA, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\w+):.*\[required\]", line)
            if m:
                keys.append(m.group(1))
    return tuple(keys)


def find_root(start="."):
    """The nearest folder at or above start that holds course.yaml, or None."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, "course.yaml")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


class CourseYamlError(ValueError):
    pass


def load(root):
    path = os.path.join(root, "course.yaml")
    with open(path, encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise CourseYamlError("%s is not valid YAML: %s" % (path, str(e).replace("\n", " ")))
    if not isinstance(cfg, dict):
        raise CourseYamlError("%s must be a mapping of keys to values, not a %s" % (path, type(cfg).__name__))
    return cfg


def check(root, report):
    """Add findings for course.yaml; return the parsed config (or None)."""
    path = os.path.join(root, "course.yaml")
    if not os.path.exists(path):
        report.error("course-missing", path, "no course.yaml at the repo root")
        return None
    try:
        cfg = load(root)
    except CourseYamlError as e:
        report.error("course-yaml", path, str(e))
        return None
    for k in required_keys():
        if cfg.get(k) in (None, ""):
            report.error("course-key", path, "required key %r is missing or empty" % k)
    if cfg.get("grade") not in (9, 10, 11, 12):
        report.error("course-grade", path, "grade %r is not 9 to 12" % cfg.get("grade"))
    if cfg.get("type") and cfg["type"] not in TYPES:
        report.warn("course-type", path, "type %r is not one of the schema's types" % cfg["type"])
    if not cfg.get("teacher"):
        report.warn("course-teacher", path, "teacher (the student-facing name) is missing")
    if not cfg.get("teacher_formal"):
        report.warn("course-teacher", path, "teacher_formal is missing; gla-plan-formatter will ask for it")
    theme = cfg.get("deck_theme", "glass")
    if theme not in DECK_THEMES:
        report.error("course-deck-theme", path, "deck_theme %r is not one of %s" % (theme, ", ".join(DECK_THEMES)))

    if cfg.get("curriculum_file") and not os.path.exists(os.path.join(paths.TEACHING_ROOT, cfg["curriculum_file"])):
        report.error("course-path", path, "curriculum_file %s does not exist under %s" % (cfg["curriculum_file"], paths.TEACHING_ROOT))
    if cfg.get("rehydration_dir") and not os.path.isdir(os.path.join(root, "master", cfg["rehydration_dir"])):
        report.error("course-path", path, "master/%s does not exist" % cfg["rehydration_dir"])
    lang, conv = cfg.get("language"), cfg.get("conventions_file")
    if bool(lang) != bool(conv):
        report.error("course-language", path, "language and conventions_file must both be set or both be null")
    if conv and not os.path.exists(os.path.join(paths.STANDARDS, "style", conv)):
        report.error("course-path", path, "conventions_file %s is not in Standards/style" % conv)
    manifest = cfg.get("gdocs_manifest") or "gdocs_manifest.yaml"
    if not os.path.exists(os.path.join(root, manifest)):
        report.error("course-path", path, "gdocs manifest %s does not exist" % manifest)

    a = cfg.get("assessment") or {}
    nums = {k: a.get(k) for k in ("classroom", "final_evaluation", "attendance", "exam", "culminating")}
    if all(isinstance(v, (int, float)) for v in nums.values()):
        if nums["classroom"] + nums["final_evaluation"] + nums["attendance"] != 100:
            report.error("course-buckets", path, "classroom + final_evaluation + attendance = %g, not 100"
                         % (nums["classroom"] + nums["final_evaluation"] + nums["attendance"]))
        if nums["exam"] + nums["culminating"] != nums["final_evaluation"]:
            report.error("course-buckets", path, "exam + culminating = %g, not final_evaluation %g"
                         % (nums["exam"] + nums["culminating"], nums["final_evaluation"]))
        subject = cfg.get("department", "")
        try:
            subject = curriculum.load(cfg["code"]).subject or subject
        except (KeyError, FileNotFoundError):
            pass
        if cfg.get("grade") in (9, 10, 11, 12):
            exp = assessment.expected(cfg.get("code"), cfg["grade"], subject)
            for k in ("classroom", "final_evaluation", "attendance"):
                if nums[k] != exp[k]:
                    report.error("course-buckets", path, "%s is %g; the 2026 model gives %g for grade %s" % (k, nums[k], exp[k], cfg["grade"]))
            if exp["exempt"]:
                if nums["exam"]:
                    report.warn("course-exam", path, "%s is exempt from a written exam (%s) but exam is %g" % (cfg.get("code"), exp["note"], nums["exam"]))
            elif exp["exam"] is None:
                report.warn("course-exam", path, exp["note"] + "; check exam and culminating by hand")
            elif (nums["exam"], nums["culminating"]) != (exp["exam"], exp["culminating"]):
                report.error("course-exam", path, "exam/culminating are %g/%g; the matrix gives %g/%g for %s grade %s"
                             % (nums["exam"], nums["culminating"], exp["exam"], exp["culminating"], subject, cfg["grade"]))
    else:
        report.error("course-buckets", path, "assessment needs numeric classroom, final_evaluation, attendance, exam, culminating")
    return cfg

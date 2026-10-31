"""Absolute locations under TEACHING_ROOT, resolved from this file's realpath."""
import os

LIB = os.path.dirname(os.path.realpath(__file__))
SKILLS = os.path.realpath(os.path.join(LIB, "..", ".."))
TEACHING_ROOT = os.path.dirname(SKILLS)
STANDARDS = os.path.join(TEACHING_ROOT, "Standards")
CURRICULUM = os.path.join(TEACHING_ROOT, "Curriculum")
COURSES = os.path.join(TEACHING_ROOT, "Courses")
# GLA_CALENDARS points the school calendars elsewhere (the tests use it).
CALENDARS = os.environ.get("GLA_CALENDARS") or os.path.join(TEACHING_ROOT, "Calendars")

COURSE_CONFIG_SCHEMA = os.path.join(STANDARDS, "templates", "Course_Config_Schema.yaml")
WEEKLY_PLAN_SCHEMA = os.path.join(STANDARDS, "templates", "Weekly_Plan_Schema.yaml")
CALENDAR_SCHEMA = os.path.join(STANDARDS, "rehydration", "Calendar_Schema.yaml")

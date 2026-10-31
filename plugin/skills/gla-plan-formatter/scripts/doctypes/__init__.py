"""Document-type builders. Each module exposes build(spec, out_path) -> out_path."""

from . import lesson, unit, course_outline, long_range_plan, weekly_plan, exam_cover

REGISTRY = {
    "lesson": lesson.build,
    "unit": unit.build,
    "course_outline": course_outline.build,
    "long_range_plan": long_range_plan.build,
    "weekly_plan": weekly_plan.build,
    "exam_cover": exam_cover.build,
}

#!/usr/bin/env python3
"""
GLA Plan Formatter: build any GLA document type in the house style.

    python build_plan.py --type TYPE (--spec plan.json | --md plan.md | --yaml plan.yaml
                                      | --pipeline COURSE_ROOT --instance SEM --unit N)
                         --out /path/Course_Thing.docx [--pdf] [--png] [--png-pages all]
                         [--artifacts-dir DIR] [--review Review.md] [--review-title "..."]
                         [--full-activities] [--tokens alt_tokens.json] [--logo crest.jpg] [--strict]
    python build_plan.py --env          # print what this runtime provides

TYPE is one of: lesson, unit, course_outline, long_range_plan, weekly_plan,
exam_cover. The JSON spec is canonical; --md / --yaml run md2spec.py first and
--pipeline (unit only) reads a GLA course repo through parsers/unit_pipeline.py.
Either writes <stem>.spec.json so the intermediate can be edited and rebuilt
with --spec. The .docx and .pdf land at --out; the spec and page PNGs go to
--artifacts-dir (default: the output's folder). --review writes or updates the
teacher's review list from the spec's review entries (see review.py).

Design values live in assets/tokens.json (see gla_docx.py); the doctypes/
builders only compose furniture. Never hand-style the .docx.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TYPES = ["lesson", "unit", "course_outline", "long_range_plan", "weekly_plan", "exam_cover"]


def main():
    ap = argparse.ArgumentParser(description="Build a GLA document in the house style.")
    ap.add_argument("--type", choices=TYPES)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--spec", help="Content JSON spec (canonical).")
    src.add_argument("--md", help="Markdown source; converted with md2spec.py.")
    src.add_argument("--yaml", help="YAML source (weekly_plan); converted with md2spec.py.")
    src.add_argument("--pipeline", metavar="COURSE_ROOT",
                     help="GLA course repo root (unit only); needs --instance and --unit.")
    ap.add_argument("--instance", help="Instance folder name under instances/, e.g. 2026-27_S1.")
    ap.add_argument("--unit", help="Unit number, e.g. 2.")
    ap.add_argument("--full-activities", action="store_true",
                    help="Pipeline: full activity text in the lesson table instead of compact rows.")
    ap.add_argument("--out", help="Output .docx path.")
    ap.add_argument("--artifacts-dir", help="Folder for the .spec.json and page PNGs (default: beside --out).")
    ap.add_argument("--review", metavar="PATH", help="Write or update the review list at PATH.")
    ap.add_argument("--review-title", help="Title for a new review list.")
    ap.add_argument("--pdf", action="store_true", help="Also export a PDF (LibreOffice).")
    ap.add_argument("--png", action="store_true", help="Also render page 1 to PNG (implies --pdf).")
    ap.add_argument("--png-pages", default=None,
                    help="'all' or a comma list of 1-based pages (implies --png; default 1).")
    ap.add_argument("--tokens", help="Alternate tokens.json (same as GLA_TOKENS).")
    ap.add_argument("--logo", help="A full-size crest to use in place of the bundled one (same as GLA_LOGO).")
    ap.add_argument("--strict", action="store_true", help="Fail on PDF/PNG problems.")
    ap.add_argument("--env", action="store_true", help="Describe this runtime and exit.")
    args = ap.parse_args()

    if args.tokens:
        os.environ["GLA_TOKENS"] = os.path.abspath(args.tokens)
    if args.logo:
        if not os.path.isfile(args.logo):
            ap.error("--logo: no file at %s" % args.logo)
        os.environ["GLA_LOGO"] = os.path.abspath(args.logo)

    import render_env

    if args.env:
        print(json.dumps(render_env.describe(), indent=2))
        return 0
    if not (args.type and args.out and (args.spec or args.md or args.yaml or args.pipeline)):
        ap.error("--type, --out, and one of --spec/--md/--yaml/--pipeline are required")
    if args.pipeline and not (args.type == "unit" and args.instance and args.unit):
        ap.error("--pipeline needs --type unit, --instance, and --unit")
    if args.png_pages is not None:
        args.png = True
    art_dir = os.path.abspath(args.artifacts_dir or os.path.dirname(os.path.abspath(args.out)))
    os.makedirs(art_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.out))[0]

    from gla_docx import SpecError
    import doctypes
    import review as review_mod

    if args.spec:
        with open(args.spec, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
    else:
        if args.pipeline:
            from parsers import unit_pipeline
            spec = unit_pipeline.build_spec(args.pipeline, args.instance, args.unit,
                                            full_activities=args.full_activities)
        else:
            import md2spec
            spec = md2spec.convert(args.md or args.yaml, args.type)
        side = os.path.join(art_dir, stem + ".spec.json")
        with open(side, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2, ensure_ascii=False)
        print("Wrote", side)

    record = review_mod.collect(spec, stem)
    if args.review:
        items, gaps = review_mod.merge(args.review, record, args.review_title)
        print(f"Wrote {args.review} ({items} items, {gaps} gaps)")
    elif record["items"] or record["gaps"]:
        print(f"REVIEW: {len(record['items'])} items, {len(record['gaps'])} gaps not written; "
              "pass --review PATH", file=sys.stderr)

    build = doctypes.REGISTRY[args.type]
    try:
        build(spec, args.out)
    except SpecError as e:
        print(f"SPEC ERROR ({args.type}): {e}", file=sys.stderr)
        return 2
    print("Wrote", args.out)

    if args.pdf or args.png:
        try:
            pdf = render_env.to_pdf(args.out)
            print("Wrote", pdf)
        except (render_env.PdfExportUnavailable, render_env.PdfExportFailed) as e:
            print(str(e), file=sys.stderr)
            return 3 if args.strict else 0
        if args.png:
            try:
                png_pages = args.png_pages or "1"
                if png_pages == "all":
                    pages = range(1, render_env.page_count(pdf) + 1)
                else:
                    pages = [int(x) for x in png_pages.split(",") if x.strip()]
                for png in render_env.rasterize(pdf, pages=pages, outdir=art_dir):
                    print("Wrote", png)
            except render_env.RasterizeUnavailable as e:
                print(str(e), file=sys.stderr)
                return 4 if args.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

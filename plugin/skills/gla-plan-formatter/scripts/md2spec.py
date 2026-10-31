#!/usr/bin/env python3
"""
md2spec: convert a Markdown (or YAML) source into the JSON spec a doctype builds from.

    python md2spec.py --type TYPE source.md [--out spec.json]

Each type's parser lives in parsers/<type>.py and exposes parse(text, path) -> dict.
The shared tokeniser is mdparse.py; the conventions are documented in
references/markdown_conventions.md. The JSON spec stays canonical: verify.py
asserts that examples/<type>/example.json == convert(examples/<type>/example.md).
"""

import argparse
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def convert(path, doc_type):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    mod = importlib.import_module(f"parsers.{doc_type}")
    return mod.parse(text, path)


def main():
    ap = argparse.ArgumentParser(description="Markdown/YAML -> GLA content spec JSON")
    ap.add_argument("--type", required=True)
    ap.add_argument("source")
    ap.add_argument("--out")
    args = ap.parse_args()
    spec = convert(args.source, args.type)
    out = json.dumps(spec, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print("Wrote", args.out)
    else:
        print(out)


if __name__ == "__main__":
    main()

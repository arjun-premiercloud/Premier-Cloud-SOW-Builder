#!/usr/bin/env python3
"""Render a Premier Cloud SOW from a validated intake file.

    python3 scripts/render_sow.py examples/coachhub.intake.json -o build/coachhub.md

Output is Markdown. To get the customer-facing document:
  - Google Docs: File > Import, or paste with "Paste from Markdown" enabled.
  - .docx: use the `docx` skill, or `pandoc out.md -o out.docx`.

Diagrams (architecture, call flows, Gantt images) are never generated - the
template emits captioned placeholders where the SOW expects a figure.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from jinja2 import ChainableUndefined, Environment, FileSystemLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sowlib  # noqa: E402
from validate_intake import validate  # noqa: E402

TEMPLATE_DIR = os.path.join(sowlib.ROOT, "templates")


def tidy(text: str) -> str:
    """Collapse the blank-line noise Jinja block tags leave behind."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def render(intake: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        # Optional fields are pervasive and legitimately absent; undefined renders
        # empty rather than exploding. Typos are caught by the round-trip fixtures.
        undefined=ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    ctx = sowlib.build_context(intake)
    template = env.get_template(f"{intake['sow_type']}.md.j2")
    return tidy(template.render(**ctx))


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a Premier Cloud SOW from an intake file.")
    ap.add_argument("intake", help="Path to the intake .json or .yaml")
    ap.add_argument("-o", "--out", help="Output path (default: build/<customer>-sow.md)")
    ap.add_argument("--force", action="store_true",
                    help="Render even when required inputs are missing (gaps become [TBD] markers)")
    args = ap.parse_args()

    intake = sowlib.load_intake(args.intake)
    report = validate(intake)

    if report["blocking"] and not args.force:
        print("Cannot render - required inputs are missing:\n", file=sys.stderr)
        for gap in report["blocking"]:
            print(f"  [{gap['field']}] {gap['question']}", file=sys.stderr)
            if gap.get("source"):
                print(f"      where to look: {gap['source']}", file=sys.stderr)
        print("\nFill these in, or re-run with --force to render with [TBD] markers.",
              file=sys.stderr)
        return 1

    if report["blocking"]:
        _stub_missing(intake, report["blocking"])

    markdown = render(intake)

    out = args.out or os.path.join(
        sowlib.ROOT, "build", f"{sowlib.slugify(intake.get('customer', {}).get('short_name', 'sow'))}-sow.md"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(markdown)

    print(f"Wrote {out}  ({len(markdown.splitlines())} lines)")
    if report["warnings"]:
        print(f"\n{len(report['warnings'])} open question(s) - see the review checklist:")
        for w in report["warnings"]:
            print(f"  - {w['question']}")
    return 0


def _stub_missing(intake: dict, gaps: list) -> None:
    """Insert [TBD: question] placeholders so --force output is obviously incomplete."""
    for gap in gaps:
        parts = gap["field"].split(".")
        cur = intake
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
            if not isinstance(cur, dict):
                break
        else:
            cur.setdefault(parts[-1], f"[TBD: {gap['question']}]")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a self-contained, shareable copy of the sow-builder skill.

    python3 scripts/package_skill.py                # -> dist/sow-builder-skill.zip
    python3 scripts/package_skill.py --no-examples  # omit the reference SOW fixtures

The skill is useless on its own - it needs the clause library, templates,
schema and scripts beside it. This assembles all of that under a single
`sow-builder/` directory that a colleague drops into `.claude/skills/`, then
runs the test suite *inside the staged copy* to prove it works standalone.

Never packaged: `intake/` (live deal data) and `build/` (rendered documents).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sowlib  # noqa: E402

ROOT = sowlib.ROOT
SKILL_SRC = os.path.join(ROOT, ".claude", "skills", "sow-builder")

# (source path relative to repo root, destination relative to package root)
CONTENTS = [
    ("library", "library"),
    ("schemas", "schemas"),
    ("templates", "templates"),
    ("scripts/sowlib.py", "scripts/sowlib.py"),
    ("scripts/render_sow.py", "scripts/render_sow.py"),
    ("scripts/validate_intake.py", "scripts/validate_intake.py"),
    ("scripts/test_render.py", "scripts/test_render.py"),
    ("scripts/md2sow.js", "scripts/md2sow.js"),
    ("requirements.txt", "requirements.txt"),
    (".claude/skills/sow-builder/SKILL.md", "SKILL.md"),
    (".claude/skills/sow-builder/references", "references"),
    ("docs/required-inputs.md", "references/required-inputs.md"),
]

EXAMPLES = [("examples", "examples")]

INSTALL = """# Installing the SOW Builder skill

Turns meeting notes into a Premier Cloud Statement of Work in the house format.

## Install

Drop the `sow-builder/` folder into either:

- `~/.claude/skills/sow-builder/` — available in every project, or
- `<your-repo>/.claude/skills/sow-builder/` — available in that project only

Then install the two Python dependencies:

```bash
pip install -r sow-builder/requirements.txt   # Jinja2, PyYAML
```

Optional, only if you want `.docx` output rather than Markdown:

```bash
npm install docx
```

## Check it works

```bash
python3 sow-builder/scripts/test_render.py
```

That renders every bundled example SOW and checks the output. All should pass.

## Use it

In Claude Code, just ask:

> Build a SOW from these notes: <paste, or a Google Doc link>

Or drive the scripts directly:

```bash
python3 sow-builder/scripts/validate_intake.py my-deal.intake.json   # what's still missing
python3 sow-builder/scripts/render_sow.py     my-deal.intake.json -o my-deal.md
node      sow-builder/scripts/md2sow.js       my-deal.md my-deal.docx
```

## Where to start reading

| File | What it is |
|---|---|
| `SKILL.md` | The workflow, start to finish |
| `references/required-inputs.md` | Discovery-call checklist by project type |
| `references/extraction-playbook.md` | Turning what people say into intake fields |
| `references/review-checklist.md` | Run before any SOW leaves Premier Cloud |
| `library/clauses.yaml` | The house language. Edit here, never in the output |
| `examples/` | Reference intakes reconstructed from issued SOWs |

## Editing house language

`library/clauses.yaml` is the single source of the standard wording. Change it
there if a sentence should change for every future SOW; override it in an
individual intake file if it changes for one deal only. Editing rendered output
does not persist.

Legal blocks — the preamble, project closure, expenses, taxes and the
compensation intro — are verbatim from issued SOWs. Change those only with
sign-off.
"""


def stage(dest: str, include_examples: bool) -> None:
    items = CONTENTS + (EXAMPLES if include_examples else [])
    for src_rel, dst_rel in items:
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(dest, dst_rel)
        if not os.path.exists(src):
            print(f"  skip (absent): {src_rel}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)

    with open(os.path.join(dest, "INSTALL.md"), "w", encoding="utf-8") as fh:
        fh.write(INSTALL)


def verify(pkg_root: str, include_examples: bool) -> bool:
    """Run the bundled test suite against the staged copy, in isolation."""
    if not include_examples:
        print("  (no examples bundled - skipping render tests)")
        return True
    proc = subprocess.run(
        [sys.executable, os.path.join(pkg_root, "scripts", "test_render.py")],
        capture_output=True, text=True, cwd=tempfile.gettempdir(),
    )
    print(proc.stdout.rstrip() or proc.stderr.rstrip())
    return proc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Package the sow-builder skill for sharing.")
    ap.add_argument("--no-examples", action="store_true",
                    help="Omit examples/ - smaller, but the test suite cannot run and "
                         "the reference SOW reconstructions are lost")
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "dist", "sow-builder-skill.zip"))
    args = ap.parse_args()
    include_examples = not args.no_examples

    with tempfile.TemporaryDirectory() as tmp:
        pkg_root = os.path.join(tmp, "sow-builder")
        os.makedirs(pkg_root)

        print("Staging:")
        stage(pkg_root, include_examples)

        print("\nVerifying the packaged copy runs standalone:")
        if not verify(pkg_root, include_examples):
            print("\nPackaging aborted - the staged copy does not pass its own tests.",
                  file=sys.stderr)
            return 1

        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(pkg_root):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                for name in sorted(filenames):
                    if name.endswith(".pyc"):
                        continue
                    full = os.path.join(dirpath, name)
                    zf.write(full, os.path.relpath(full, tmp))

    size = os.path.getsize(args.out)
    print(f"\nWrote {args.out} ({size / 1024:.0f} KB)")
    if include_examples:
        print("Includes examples/ - reconstructions of issued SOWs with real customer "
              "names, contacts and contract values. Fine for a Premier Cloud colleague; "
              "check before sending outside the company.")
    print("Never included: intake/ (live deal data) and build/ (rendered documents).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

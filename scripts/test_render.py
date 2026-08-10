#!/usr/bin/env python3
"""Round-trip tests: every example intake must validate and render cleanly.

    python3 scripts/test_render.py

The three reconstruction fixtures (coachhub, afni, miles-partnership) were built
from issued SOWs, so a regression here means the generator has drifted away from
a document Premier Cloud actually sent to a customer.
"""

from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sowlib  # noqa: E402
from render_sow import render  # noqa: E402
from validate_intake import validate  # noqa: E402

# Strings that must appear in every rendered document, whatever the type.
UNIVERSAL = [
    "Statement of Work",
    "Premier Cloud",
]

# Per-type invariants: (sow_type, [must appear], [must NOT appear])
INVARIANTS = {
    "gemini_enterprise_implementation": (
        [
            "Gemini Enterprise is a managed service offering by Google Cloud",
            "In Scope Services",
            "Out of Scope",
            "Project Acceptance Form",
            "sales tax exemption certificate",
        ],
        [],
    ),
    "agent_pilot": (
        ["Current Solution", "Proposed Solution", "Out of Scope"],
        [],
    ),
    "workspace_migration": (
        ["Executive Summary", "Investment Summary", "Resource Allocation"],
        [],
    ),
}

FAILURES = []


def check(condition, message):
    if not condition:
        FAILURES.append(message)


def main() -> int:
    paths = sorted(glob.glob(os.path.join(sowlib.ROOT, "examples", "*.intake.json")))
    check(len(paths) >= 4, f"expected at least 4 example intakes, found {len(paths)}")

    for path in paths:
        name = os.path.basename(path)
        intake = sowlib.load_intake(path)
        report = validate(intake)

        check(not report["blocking"],
              f"{name}: blocking gaps: {[g['field'] for g in report['blocking']]}")

        try:
            out = render(intake)
        except Exception as exc:  # noqa: BLE001 - surface any template error as a failure
            FAILURES.append(f"{name}: render raised {type(exc).__name__}: {exc}")
            continue

        for needle in UNIVERSAL:
            check(needle in out, f"{name}: missing universal string {needle!r}")

        must, must_not = INVARIANTS[intake["sow_type"]]
        for needle in must:
            check(needle in out, f"{name}: missing {needle!r}")
        for needle in must_not:
            check(needle not in out, f"{name}: unexpectedly contains {needle!r}")

        # Unresolved template syntax anywhere in the output is a bug.
        check("{{" not in out, f"{name}: unrendered '{{{{' placeholder in output")
        check("{%" not in out, f"{name}: unrendered '{{%' tag in output")
        check("None" not in out.replace("None-", ""), f"{name}: literal 'None' leaked into output")

        # Commercial invariant: a customer paying a net amount must see the
        # funding-reversal paragraph.
        pricing = sowlib.build_context(intake)["pricing"]
        if pricing["net"] > 0 and pricing["funding"]:
            check("Funding credit will be reversed" in out,
                  f"{name}: net cost is {pricing['net']} with funding, but no clawback paragraph")

        # Section numbering must be contiguous and start at 1.
        numbers = [s["n"] for s in sowlib.section_plan(intake["sow_type"], intake)]
        check(numbers == list(range(1, len(numbers) + 1)),
              f"{name}: section numbering is not contiguous: {numbers}")

        print(f"  ok  {name}  ({intake['sow_type']}, {len(out.splitlines())} lines)")

    print()
    if FAILURES:
        print(f"FAILED - {len(FAILURES)} problem(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All example intakes validate and render.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate a SOW intake file and print a gap report.

    python3 scripts/validate_intake.py examples/coachhub.intake.json

The point of this script is not schema pedantry - it is to turn "what do we
still not know?" into a list of questions you can paste into an email or take
into the next call. Every gap is reported as the question to ask and the place
the answer normally lives.

Exit code 0 = renderable. 1 = blocking gaps.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sowlib  # noqa: E402

# Fields that must be present to render a contractually sound document.
REQUIRED = {
    "_all": [
        "sow_type",
        "document.title",
        "document.date",
        "customer.legal_name",
        "customer.short_name",
        "customer.contact.name",
        "customer.contact.email",
        "agreement.execution_date",
        "term.effective_date",
        "term.end_date",
        "pricing.total_fixed_price",
    ],
    "gemini_enterprise_implementation": [
        "platform.seats",
        "platform.data_sources",
        "platform.user_community",
        "background.business_challenges",
    ],
    "agent_pilot": [
        "background.objective",
        "use_cases",
        "customer.profile",
    ],
    "workspace_migration": [
        "migration.source_platform",
        "migration.user_count",
        "migration.tracks",
        "customer.profile",
        "timeline.schedule",
    ],
}

# Absent these, the SOW renders but a human must decide before it goes out.
RECOMMENDED = {
    "_all": [
        "customer.signatory.name",
        "customer.address",
        "term.duration_weeks",
        "success_criteria",
        "risks",
        "scope.out_of_scope_extra",
    ],
    "gemini_enterprise_implementation": [
        "platform.activation_plan",
        "platform.identity_provider",
        "background.objective",
    ],
    "agent_pilot": [
        "background.baseline_metrics",
        "customer.stakeholders",
        "timeline.schedule",
    ],
    "workspace_migration": [
        "migration.sso_apps",
        "migration.volumes",
        "migration.decisions_pending",
        "resources",
    ],
}


def schema_meta(schema: dict, dotted: str) -> dict:
    """Pull x-question / x-source for a dotted path out of the JSON Schema."""
    node = schema
    for part in dotted.split("."):
        props = node.get("properties") or {}
        if part in props:
            node = props[part]
        elif node.get("type") == "array" and node.get("items"):
            node = node["items"].get("properties", {}).get(part, {})
        else:
            return {}
    return {
        "question": node.get("x-question") or f"Provide `{dotted}`.",
        "source": node.get("x-source", ""),
    }


def _paths(kind: dict, sow_type: str) -> list:
    return kind["_all"] + kind.get(sow_type, [])


def validate(intake: dict) -> dict:
    schema = sowlib.load_schema()
    sow_type = intake.get("sow_type")

    if sow_type not in sowlib.SOW_TYPES:
        meta = schema_meta(schema, "sow_type")
        return {
            "blocking": [{"field": "sow_type", **meta}],
            "warnings": [],
            "checks": [f"sow_type must be one of {', '.join(sowlib.SOW_TYPES)}"],
        }

    blocking, warnings = [], []
    for path in _paths(REQUIRED, sow_type):
        if _empty(sowlib.get(intake, path)):
            blocking.append({"field": path, **schema_meta(schema, path)})
    for path in _paths(RECOMMENDED, sow_type):
        if not _applicable(path, intake):
            continue
        if _empty(sowlib.get(intake, path)):
            warnings.append({"field": path, **schema_meta(schema, path)})

    return {
        "blocking": blocking,
        "warnings": warnings,
        "checks": consistency_checks(intake),
    }


def _applicable(path: str, intake: dict) -> bool:
    """Suppress prompts that do not apply to this engagement's shape."""
    if path == "migration.sso_apps":
        # Only meaningful when an identity directory is being left behind.
        return bool(sowlib.get(intake, "migration.endpoints"))
    return True


def _empty(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def consistency_checks(intake: dict) -> list:
    """Cross-field checks that catch the errors that actually cost money."""
    out = []
    g = sowlib.get

    total = g(intake, "pricing.total_fixed_price") or 0
    funding = abs(g(intake, "pricing.google_funding") or 0)
    investment = abs(g(intake, "pricing.partner_investment") or 0)
    net = total - funding - investment

    if funding > total:
        out.append(f"Google funding ({funding:,.0f}) exceeds the total fixed price ({total:,.0f}).")
    if net > 0 and funding and not g(intake, "pricing.funding_clawback"):
        out.append(
            f"Customer pays a net {net:,.0f} against {funding:,.0f} of Google funding, but "
            "pricing.funding_clawback is false. The clawback paragraph is a material commercial "
            "term whenever the customer's net is above zero - confirm this is intentional."
        )
    if net < 0:
        out.append(f"Credits exceed the fee; net cost computes to {net:,.0f}.")

    deliverables = intake.get("deliverables") or []
    milestones = g(intake, "timeline.milestones") or []
    if deliverables and milestones and len(deliverables) < len(milestones):
        out.append(
            f"{len(milestones)} milestones but only {len(deliverables)} deliverables - "
            "every milestone should land at least one deliverable."
        )

    weeks = g(intake, "timeline.weeks") or g(intake, "term.duration_weeks")
    if weeks and milestones:
        late = [m.get("id") for m in milestones if (m.get("week") or 0) > weeks]
        if late:
            out.append(f"Milestone(s) {', '.join(filter(None, late))} fall outside the {weeks}-week term.")

    seats = g(intake, "platform.seats")
    purchased = g(intake, "platform.activation_plan.purchased_licenses")
    if seats and purchased and seats != purchased:
        out.append(f"platform.seats ({seats}) does not match activation_plan.purchased_licenses ({purchased}).")

    end_users = g(intake, "platform.activation_plan.active_at_end")
    if purchased and end_users and end_users > purchased:
        out.append("Activation plan projects more active users at project end than licenses purchased.")

    if intake.get("sow_type") == "agent_pilot":
        for uc in intake.get("use_cases") or []:
            if not uc.get("current_solution") and not uc.get("current_solution_steps"):
                out.append(
                    f"Use case '{uc.get('name', '?')}' has no Current Solution. "
                    "Without today's flow the Proposed Solution has nothing to contrast against."
                )

    if not (intake.get("scope", {}) or {}).get("out_of_scope_extra"):
        out.append(
            "No deal-specific exclusions recorded. The standard list is applied, but the "
            "exclusions that prevent scope disputes are the ones raised and parked in the meeting."
        )

    assumed = g(intake, "provenance.assumed") or []
    if assumed:
        out.append(f"{len(assumed)} value(s) were inferred rather than read from source - verify before sending.")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a SOW intake file and report gaps.")
    ap.add_argument("intake")
    ap.add_argument("--quiet", action="store_true", help="Exit code only")
    args = ap.parse_args()

    intake = sowlib.load_intake(args.intake)
    report = validate(intake)

    if args.quiet:
        return 1 if report["blocking"] else 0

    if report["blocking"]:
        print(f"BLOCKING - {len(report['blocking'])} required input(s) missing\n")
        for gap in report["blocking"]:
            print(f"  {gap['field']}")
            print(f"    ask: {gap['question']}")
            if gap.get("source"):
                print(f"    where: {gap['source']}")
        print()
    else:
        print("BLOCKING - none. This intake will render.\n")

    if report["warnings"]:
        print(f"OPEN QUESTIONS - {len(report['warnings'])} field(s) left at defaults or blank\n")
        for gap in report["warnings"]:
            print(f"  {gap['field']}")
            print(f"    ask: {gap['question']}")
        print()

    if report["checks"]:
        print("CONSISTENCY\n")
        for c in report["checks"]:
            print(f"  - {c}")
        print()

    unanswered = sowlib.get(intake, "provenance.unanswered") or []
    if unanswered:
        print("UNANSWERED IN SOURCE NOTES\n")
        for q in unanswered:
            print(f"  - {q}")
        print()

    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

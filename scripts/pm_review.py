#!/usr/bin/env python3
"""Delivery-risk review of a SOW intake, from a project manager's point of view.

    python3 scripts/pm_review.py intake/<customer>.intake.json

`validate_intake.py` asks "can this document be rendered?". This asks a
different question: "if we sign this, can we deliver it?"

The two are not the same. A SOW can be internally consistent, legally complete
and commercially signed off, and still be undeliverable because the schedule
quotes 300 hours against a six-week term with one named engineer, or because
the critical path runs through a customer task that has no owner.

This script only reports what it can compute from the intake. The judgement
calls - is this team actually free, has this kind of work slipped before, is
the price defensible against comparable engagements - need evidence from
outside the file, and belong to the reviewer. See `references/pm-review.md`.

Severities:
    HIGH    Do not send. This will cost money or credibility.
    MEDIUM  Send only with a conscious decision recorded.
    LOW     Worth a sentence in the covering note.

Exit code 0 = no HIGH findings. 1 = at least one HIGH.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sowlib  # noqa: E402

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"
ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2}

# House assumptions. These are configured positions, not laws of nature -
# override them per deal if the deal team has a reason.
BILLABLE_HOURS_PER_WEEK = 32.0   # 40 less meetings, admin and context switching
RATE_BAND = (150.0, 300.0)       # USD/hour the blended fee normally lands in
KEY_PERSON_SHARE = 0.60          # one role carrying more than this is a risk
MAX_SUSTAINED_FTE = 1.0          # per named role, across the term

DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
    "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
]

# Phrases that mean "nobody owns this yet".
UNOWNED = re.compile(
    r"\bTBD\b|\bTBC\b|to be (confirmed|decided|determined|agreed)|"
    r"\bwho (will|owns|rebuilds|does)\b|owner unknown",
    re.I,
)


def parse_date(value):
    """Return a date, or None if the value is prose rather than a date."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class Report:
    def __init__(self):
        self.findings = []

    def add(self, severity, area, finding, so_what, fix=None):
        self.findings.append(
            {"severity": severity, "area": area, "finding": finding,
             "so_what": so_what, "fix": fix}
        )

    def __bool__(self):
        return bool(self.findings)

    @property
    def worst(self):
        return min((ORDER[f["severity"]] for f in self.findings), default=99)


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_term(intake, g, rep):
    start = parse_date(g(intake, "term.effective_date"))
    end = parse_date(g(intake, "term.end_date"))
    weeks = g(intake, "term.duration_weeks")

    if start and end:
        if end <= start:
            rep.add(HIGH, "Term",
                    f"End date ({end}) is not after the start date ({start}).",
                    "The document contradicts itself on its own duration.")
            return start, end, weeks
        actual = (end - start).days / 7.0
        if weeks and abs(actual - weeks) > 1.0:
            rep.add(MEDIUM, "Term",
                    f"term.duration_weeks says {weeks}, but the dates span "
                    f"{actual:.1f} weeks.",
                    "The Gantt is built from duration_weeks and the timeline "
                    "table from the dates, so the document will show two "
                    "different durations.",
                    "Set duration_weeks to match, or correct the dates.")
        if actual > 0 and not weeks:
            weeks = actual
    elif not weeks:
        rep.add(MEDIUM, "Term",
                "No duration is computable: dates are prose and "
                "duration_weeks is unset.",
                "Nothing downstream can check whether the plan fits the term.")
    return start, end, weeks


def check_schedule(intake, g, rep, start, end, weeks):
    schedule = g(intake, "timeline.schedule") or []
    tracks = g(intake, "migration.tracks") or []
    for track in tracks:
        for phase in track.get("phases", []) or []:
            schedule = schedule  # tracks carry activities, not dated rows

    if not schedule:
        rep.add(MEDIUM, "Schedule",
                "No dated task schedule.",
                "Without one there is no basis for the end date, and no way "
                "to tell at week three whether delivery is behind.",
                "Populate timeline.schedule, even coarsely.")
        return 0.0

    hours = sum(r.get("effort_hours") or 0 for r in schedule)
    no_deliverable = [r for r in schedule if not r.get("deliverable")]
    if no_deliverable and len(no_deliverable) == len(schedule):
        rep.add(LOW, "Schedule",
                "No schedule row names a deliverable.",
                "Progress can only be reported as opinion.")
    elif len(no_deliverable) > len(schedule) / 2:
        rep.add(LOW, "Schedule",
                f"{len(no_deliverable)} of {len(schedule)} schedule rows have "
                "no deliverable.",
                "Those weeks have nothing to accept against.")

    # Rows outside the term.
    for row in schedule:
        rs, re_ = parse_date(row.get("start_date")), parse_date(row.get("end_date"))
        label = row.get("activity") or row.get("phase") or "a scheduled task"
        if start and rs and rs < start:
            rep.add(HIGH, "Schedule",
                    f"'{label}' starts {rs}, before the term begins ({start}).",
                    "We would be working unpaid and uncovered by the Agreement.")
        if end and re_ and re_ > end:
            rep.add(HIGH, "Schedule",
                    f"'{label}' ends {re_}, after the term ends ({end}).",
                    "The SOW commits to work that falls outside its own term, "
                    "which is how engagements end up delivering with no live "
                    "contract behind them.")
        if rs and re_ and re_ < rs:
            rep.add(MEDIUM, "Schedule",
                    f"'{label}' ends before it starts ({rs} to {re_}).",
                    "Arithmetic error that will show in the client-facing table.")

    if hours and weeks:
        fte = hours / (weeks * BILLABLE_HOURS_PER_WEEK)
        if fte > 3.0:
            rep.add(HIGH, "Capacity",
                    f"{hours:.0f} hours across {weeks:.0f} weeks implies "
                    f"{fte:.1f} full-time people sustained for the whole term.",
                    "A team that size has to be named and reserved before "
                    "signature, not found afterwards.",
                    "Confirm the named people are allocated, or lengthen the term.")
        elif fte > MAX_SUSTAINED_FTE:
            rep.add(MEDIUM, "Capacity",
                    f"{hours:.0f} hours across {weeks:.0f} weeks implies "
                    f"{fte:.1f} FTE sustained.",
                    f"Assumes {BILLABLE_HOURS_PER_WEEK:.0f} billable hours per "
                    "person-week. Check the named engineers are free for that "
                    "share of their time for the whole term.")
    return hours


def check_resources(intake, g, rep, schedule_hours):
    resources = g(intake, "resources") or []
    if not resources:
        if schedule_hours:
            rep.add(MEDIUM, "Capacity",
                    f"{schedule_hours:.0f} hours are quoted in the schedule "
                    "but there is no resource allocation table.",
                    "Nobody has been asked to confirm they can do the work.")
        return

    numeric = [(r.get("role") or "unnamed role", float(r["hours"]))
               for r in resources
               if isinstance(r.get("hours"), (int, float))]
    total = sum(h for _, h in numeric)

    # Direction matters. Scheduled work with nobody allocated to it is a
    # delivery hole; allocated hours above the schedule is usually project
    # management, which legitimately has no activity row.
    tolerance = max(4.0, 0.05 * schedule_hours) if schedule_hours else 0
    if numeric and schedule_hours and schedule_hours - total > tolerance:
        rep.add(HIGH, "Capacity",
                f"The activity schedule totals {schedule_hours:.0f} hours but "
                f"only {total:.0f} are allocated to named roles - "
                f"{schedule_hours - total:.0f} hours of committed work have "
                "nobody against them.",
                "Both tables appear in the client-facing document. Either we "
                "are short a person, or we are quoting work we have not "
                "staffed.",
                "Raise the role hours to cover the schedule, or cut the scope.")
    elif numeric and schedule_hours and total - schedule_hours > tolerance:
        rep.add(MEDIUM, "Capacity",
                f"Roles are allocated {total:.0f} hours against a "
                f"{schedule_hours:.0f}-hour activity schedule "
                f"({total - schedule_hours:.0f} hours unaccounted).",
                "Usually project management, which has no activity row - but "
                "a reader who adds up both tables will ask, so make sure the "
                "answer is one we want to give.")

    if total:
        for role, h in numeric:
            if h / total > KEY_PERSON_SHARE:
                rep.add(MEDIUM, "Capacity",
                        f"{role} carries {h:.0f} of {total:.0f} hours "
                        f"({h / total:.0%}).",
                        "Single-person dependency. If that person is pulled "
                        "onto an escalation or takes leave, the engagement "
                        "stops.",
                        "Name a backup, or spread the work.")


def check_commercials(intake, g, rep, hours):
    price = g(intake, "pricing.total_fixed_price")
    currency = g(intake, "pricing.currency") or "USD"
    funding = g(intake, "pricing.google_funding") or 0
    items = g(intake, "pricing.line_items") or []

    if price is None:
        rep.add(HIGH, "Commercials",
                "No total fixed price.",
                "Not a signable document.")
    elif hours:
        rate = price / hours
        low, high = RATE_BAND
        if rate < low:
            rep.add(HIGH, "Commercials",
                    f"Effective rate is {currency} {rate:.0f}/hour "
                    f"({currency} {price:,.0f} over {hours:.0f} hours).",
                    f"Below the {low:.0f}-{high:.0f} band. Either the hours "
                    "are overstated or the deal loses money on delivery.",
                    "Check which of the two numbers is wrong before signing.")
        elif rate > high:
            rep.add(LOW, "Commercials",
                    f"Effective rate is {currency} {rate:.0f}/hour.",
                    f"Above the {low:.0f}-{high:.0f} band. Fine if deliberate, "
                    "but it invites a procurement challenge on the hours.")

    if items and price:
        line_total = sum(i.get("amount") or 0 for i in items if isinstance(i, dict))
        if line_total and abs(line_total - price) > 1:
            rep.add(HIGH, "Commercials",
                    f"Line items total {currency} {line_total:,.0f} against a "
                    f"stated price of {currency} {price:,.0f}.",
                    "The cost table will not add up on the page.")

    net = (price or 0) - funding
    if funding and net > 0 and not g(intake, "pricing.funding_clawback"):
        rep.add(HIGH, "Commercials",
                f"Google funding is {currency} {funding:,.0f} with "
                f"{currency} {net:,.0f} left on the customer, and no "
                "clawback paragraph.",
                "If the funding claim is rejected, Premier Cloud absorbs it "
                "with nothing in the SOW to fall back on.",
                "Set pricing.funding_clawback: true.")

    if price and not g(intake, "pricing.payment_terms"):
        rep.add(MEDIUM, "Commercials",
                "No payment terms.",
                "Invoicing trigger and schedule are undefined, which is how "
                "final payments stall for months after delivery ends.",
                "State the trigger and the terms, e.g. Net 30 on acceptance.")


def check_dependencies(intake, g, rep):
    pending = g(intake, "migration.decisions_pending") or []
    assumptions = g(intake, "assumptions") or []

    unowned = [d for d in pending if isinstance(d, str) and UNOWNED.search(d)]
    if unowned:
        rep.add(HIGH, "Dependencies",
                f"{len(unowned)} of {len(pending)} open decisions have no "
                f"named owner. First: \"{unowned[0][:110]}\"",
                "An unowned dependency on the critical path is the single "
                "most reliable cause of slip. 'TBD' is not a plan, and it "
                "reads badly in a contract.",
                "Assign each to Premier Cloud or the Customer before sending.")
    elif pending:
        rep.add(LOW, "Dependencies",
                f"{len(pending)} customer decisions are open.",
                "Each is a dated dependency. Confirm the dates are in the "
                "document, not just the decision.")

    dated = [d for d in pending if isinstance(d, str) and re.search(r"\d", d)]
    if pending and not dated:
        rep.add(MEDIUM, "Dependencies",
                "No open decision carries a date or a deadline.",
                "A dependency without a date cannot be chased, and cannot "
                "support a delay claim later.")

    access = [a for a in assumptions if isinstance(a, str)
              and re.search(r"admin|access|credential|licen[cs]e", a, re.I)]
    if not access:
        rep.add(MEDIUM, "Dependencies",
                "No assumption covers administrative access or licensing.",
                "Access arriving late is the most common cause of a start "
                "date slipping, and without the assumption the slip is ours.")


def check_closure(intake, g, rep):
    sow_type = g(intake, "sow_type")
    criteria = g(intake, "success_criteria") or []
    if not criteria:
        rep.add(HIGH, "Closure",
                "No success criteria.",
                "Nothing defines done, so the engagement closes when the "
                "customer says so rather than when the work is complete.")
    else:
        vague = [c for c in criteria if isinstance(c, str)
                 and re.search(r"\b(improve|increase|reduce|optimi[sz]e|enhance)\b", c, re.I)
                 and not re.search(r"\d", c)]
        if vague:
            rep.add(MEDIUM, "Closure",
                    f"{len(vague)} success criteria are directional with no "
                    f"measure. First: \"{vague[0][:100]}\"",
                    "Cannot be demonstrated at closure, so it becomes an "
                    "argument instead of a sign-off.")

    blob = repr(intake).lower()
    if not re.search(r"accept(ance|ed|s)\b|sign-?off", blob):
        rep.add(HIGH, "Closure",
                "No acceptance mechanism anywhere in the intake.",
                "Without a named artefact and a named approver, there is "
                "nothing to attach final payment or a funding claim to.",
                "Name the acceptance deliverable and who signs it.")

    if not re.search(r"change (order|request|control)|work order|amendment", blob):
        rep.add(MEDIUM, "Closure",
                "No change-control route.",
                "Scope will be added - it always is. Without a route, extra "
                "work is either done free or becomes a dispute.")

    if sow_type == "workspace_migration" and not re.search(r"rollback|roll back|back ?out", blob):
        rep.add(MEDIUM, "Closure",
                "Migration SOW with no rollback or back-out position.",
                "Cutover is the irreversible moment of the engagement. If the "
                "customer has asked what can be undone, silence is a worse "
                "answer than a narrow one.")

    if not (g(intake, "governance.meetings") or []):
        rep.add(LOW, "Governance",
                "No governance cadence.",
                "No agreed forum to raise a slip in before it becomes one.")


def check_provenance(intake, g, rep):
    assumed = g(intake, "provenance.assumed") or []
    unanswered = g(intake, "provenance.unanswered") or []
    if assumed:
        rep.add(LOW, "Provenance",
                f"{len(assumed)} value(s) were inferred rather than read "
                "from a source.",
                "Each needs a human to confirm it before the document goes out.")
    if unanswered:
        rep.add(MEDIUM, "Provenance",
                f"{len(unanswered)} question(s) are still open in the source "
                f"notes. First: \"{str(unanswered[0])[:110]}\"",
                "Signing over an open question transfers its cost to delivery.")


# --------------------------------------------------------------------------

def run(intake):
    g = sowlib.get
    rep = Report()
    start, end, weeks = check_term(intake, g, rep)
    hours = check_schedule(intake, g, rep, start, end, weeks)
    check_resources(intake, g, rep, hours)
    check_commercials(intake, g, rep, hours)
    check_dependencies(intake, g, rep)
    check_closure(intake, g, rep)
    check_provenance(intake, g, rep)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("intake")
    ap.add_argument("--quiet", action="store_true",
                    help="Print findings only, no header or guidance footer.")
    args = ap.parse_args()

    intake = sowlib.load_intake(args.intake)
    rep = run(intake)

    name = sowlib.get(intake, "customer.short_name") or os.path.basename(args.intake)
    if not args.quiet:
        print(f"PM delivery review - {name}\n")

    if not rep:
        print("No delivery risks found in the intake.")
    else:
        for sev in (HIGH, MEDIUM, LOW):
            group = [f for f in rep.findings if f["severity"] == sev]
            if not group:
                continue
            print(f"{sev} - {len(group)} finding(s)\n")
            for f in group:
                print(f"  [{f['area']}] {f['finding']}")
                print(f"    why it matters: {f['so_what']}")
                if f["fix"]:
                    print(f"    fix: {f['fix']}")
                print()

    if not args.quiet:
        print("This covers only what the intake can prove. Capacity, track "
              "record and\ncomparable pricing need evidence from outside the "
              "file - see references/pm-review.md.")

    return 1 if any(f["severity"] == HIGH for f in rep.findings) else 0


if __name__ == "__main__":
    sys.exit(main())

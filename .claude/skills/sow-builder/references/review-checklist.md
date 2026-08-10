# Review checklist

Run before any SOW leaves Premier Cloud. Every item here has been wrong in a real
document at least once.

## Parties and dates

- [ ] Customer legal entity name is the one on the MSA, not the brand name.
- [ ] The signatory is the person who can actually sign, with a title.
- [ ] `agreement.execution_date`, `term.effective_date` and `term.end_date` are
      mutually consistent, and the end date is after the start date.
- [ ] If a negotiated MSA exists, `msa_style` is `dated_mpsa` with the correct
      `msa_date` — not the public link.

## Money

- [ ] The cost table adds up and the net line is right.
- [ ] **If the customer's net is above zero, the funding-reversal (clawback)
      paragraph is present.** This is the single most expensive omission
      available. Set `pricing.funding_clawback: true`.
- [ ] Google funding figure matches what the deal team actually requested, and
      the funding stage is right if a Funding Disclosure paragraph is rendered.
- [ ] Per-agent or per-workstream line items sum to the total fixed price.

## Scope

- [ ] Every commitment made verbally in the meeting appears in Description of
      Services, or is deliberately excluded.
- [ ] Deal-specific exclusions from the meeting are in Out of Scope — not just
      the standard list.
- [ ] Counts in prose match the intake: number of workshops, enablement sessions,
      revision cycles, seats, connectors.
- [ ] Nothing in Out of Scope contradicts something promised in Scope. Check
      specifically for agentic workflows, custom UI, and identity federation.

## Delivery

- [ ] Every milestone lands at least one deliverable.
- [ ] No milestone falls outside the Term.
- [ ] The Gantt weeks match `term.duration_weeks`.
- [ ] Named roles have real people where the customer expects names.
- [ ] Effort hours (where quoted) reconcile with the resource allocation table.

## Success criteria

- [ ] Each criterion is something we can demonstrate at closure, not an
      aspiration. "Users can effectively search" is acceptable house language;
      "adoption improves productivity by 30%" is not.
- [ ] Criteria referencing baseline numbers match `background.baseline_metrics`.
- [ ] Connector or seat counts in the criteria match the platform section.

## Document

- [ ] `[TBD: …]` markers are all resolved. Search the rendered file.
- [ ] `[INSERT DIAGRAM: …]` placeholders are either filled or the figure
      references removed.
- [ ] Table of contents section numbers match the body.
- [ ] Everything in `provenance.assumed` has been verified by a human.
- [ ] Everything in `provenance.unanswered` has been asked and answered, or
      consciously accepted.

## Language

- [ ] Legal blocks (preamble, closure, expenses, taxes, compensation intro) are
      unedited from `library/clauses.yaml`. If any were changed for this deal,
      legal has seen them.
- [ ] Voice is consistent: "Partner will…", "Customer will…", third person.
- [ ] Counts written as "two (2) sessions".

# Extraction playbook

How to get from meeting notes to a filled intake file. Organised by what people
actually say in discovery calls, not by schema order.

---

## The five things a SOW cannot be written without

If the notes do not contain these, stop and ask. Everything else can be
defaulted, inferred, or marked TBD.

1. **Who the customer legally is** — the entity name on the MSA, not the brand.
2. **What we are building** — enough detail to write the Scope section without
   hedging.
3. **When it starts and how long it runs** — drives the Term, the Gantt, and the
   milestone dates.
4. **What it costs and who pays** — total fee, Google funding, net to customer.
5. **Who signs** — the signatory is frequently not the person in the meeting.

---

## Signals → fields

### "We've got about 250 seats" / "the order form says 279"
`platform.seats`. Also cross-check `platform.activation_plan.purchased_licenses`
— the validator flags a mismatch. Seats cap the user community and appear
verbatim in the UAT onboarding line.

### "We'd want it hooked up to Drive, Gmail, Salesforce and Jira"
`platform.data_sources`, one object per source. Mark `federated: true` for
anything the connector federates rather than indexes — Salesforce, GitHub, Jira
Cloud and Confluence Cloud have all been federated in past SOWs. **Get the full
list.** Connector count drives price, timeline and the success-criteria line, and
"additional data connectors will impact the delivery schedule and cost" is a
standing assumption that only protects us if the baseline list is accurate.

### "We're on Google Workspace already" / "we use Okta" / "we'd need to set up WIF"
`platform.identity_provider` and `platform.workforce_identity_federation`. These
select which assumption paragraph is used and whether WIF configuration lands in
Out of Scope. Three states:
- `not_required` — users in Google Workspace, no federation expected
- `customer_preexisting` — an existing Workforce Identity pool is in place
- `customer_to_configure` — the customer must set it up before we start, and WIF
  configuration is explicitly excluded

Anything other than Google Identity means an Identity Architect on the team and a
different exclusion set. Flag it rather than defaulting.

### "Do they have a GCP org?" — "No, they'd be starting fresh"
`platform.cloud_foundations: true`. Injects the Identity & Access Configuration
and Resource Implementation blocks into Solution Design. Materially more work —
make sure the price reflects it.

### "It'd be great if it could send everyone a morning summary"
`platform.agentic_workflows`. Each entry becomes a scope block and a Services
subsection with the standard build/test/optimise/one-revision-cycle bullets. If
the list is empty, "Developing agentic workflows" is added to Out of Scope
automatically — which is the right default, but check nobody promised one
verbally.

### "Right now an analyst pulls up the claim, calls the carrier, and…"
This is the single most meeting-dependent content in any SOW, and it only exists
in `agent_pilot`. Capture it as `use_cases[].current_solution_steps` — numbered,
in the customer's own sequence, naming their systems. The Proposed Solution has
nothing to contrast against without it, and the validator will complain.

While they walk the flow, listen for:
- **the trigger** — inbound call, API dispatch, work basket → `use_cases[].trigger`
- **the systems touched** — every read and every write-back → `use_cases[].systems`
- **the numbers** — handle time, volumes, resolution rates → `background.baseline_metrics`

Always record the source of a baseline number ("ServiceNow, March–May 2026"). A
baseline without a provenance line cannot be defended at closure.

### "We're at about 44 minutes average handle time"
`background.baseline_metrics`. These become the reference point for the success
criteria. Get the system and date range they came from.

### "8 terabytes of mail, maybe 15 in OneDrive"
`migration.volumes`. Ask for the **mailbox size distribution**, not just the
total — the wave plan is built from it (under 1 GB / 1–20 GB / 20–50 GB / over
50 GB in past engagements). Total TB drives worker-pool sizing.

### "Around 225 Windows machines, all domain-joined, managed through Splashtop"
`migration.endpoints`. Note which platforms are actually *in scope* separately
from what exists — the Miles engagement had 275 Macs that were explicitly not in
the endpoint track.

### "ADP, Zoom, LastPass, a few others"
`migration.sso_apps`. Get the actual list. "A few others" becomes a per-app
validation line in the SSO matrix; an uncounted app becomes an argument.

### "We still need to decide what to do with the PSTs"
`migration.decisions_pending`. Every open decision becomes a dated dependency.
Write it with the deadline attached: "decisions on X finalised before the Week 2
pilot".

### "We're not doing Teams — we're on Slack"
`scope.out_of_scope_extra`. **Everything raised and parked belongs here.** This
is the highest-value extraction in the whole exercise. The standard exclusion
list is boilerplate; the deal-specific ones are what prevent a dispute.

### "Google's covering it" / "PSF should cover about 37 of it"
`pricing.google_funding` and `pricing.funding_program`. Then the critical
question: **is the customer's net above zero?** If yes,
`pricing.funding_clawback` must be `true` so the funding-reversal paragraph is
included. The validator flags this, but catch it while the deal team is still on
the call.

### "Kick off first week of July, we need it done before the fiscal year"
`term.effective_date`, `term.end_date`, `term.duration_weeks`. If only a duration
is given, compute the end date and put it in `provenance.assumed`.

### "Gray's the CTO, David runs IT day to day"
`customer.stakeholders`. Roles matter more than names for the Roles table, but
named people belong in the escalation matrix. Ask who signs — it is often
neither of the people in the room.

---

## When the notes are silent

| Situation | Do this |
|---|---|
| A required field is genuinely absent | Leave it out. It surfaces in the gap report as a question to ask. |
| You can infer it with high confidence | Fill it in **and** add a line to `provenance.assumed`. |
| The notes conflict with each other | Take the later source, note both readings in `provenance.unanswered`. |
| Someone said "we'll confirm" | `provenance.unanswered`, verbatim. |
| A standard clause obviously does not apply | `scope.out_of_scope_suppress` with a distinctive substring — never delete from the clause library. |

Never fill a gap with plausible-sounding prose. An empty field costs one email;
an invented one can cost a change request.

---

## Multiple meetings

Later notes win on facts; earlier notes are still the best source for the
*current-state* narrative, which rarely gets repeated. List every source in
`provenance.sources` in date order.

---

## Handling transcripts specifically

Raw transcripts are noisy. Work through them in this order:

1. Skim for the **numbers** — they are the hardest thing to recover later and the
   easiest to misattribute. Capture each with its speaker and context.
2. Extract the **current-state walkthrough** — usually one long stretch where a
   customer SME narrates a process. This is your `current_solution`.
3. Collect the **parked items** — phrases like "not for now", "phase two",
   "out of scope for this", "let's not boil the ocean". These are your
   `out_of_scope_extra`.
4. Collect the **open decisions** — "we'll need to check", "I'll confirm with",
   "depends on whether". These split between `decisions_pending` and
   `provenance.unanswered`.
5. Only then write the narrative fields.

Attribute claims to the customer where the SOW states them as fact about the
customer's environment. If only Premier Cloud said it, it is an assumption, not a
finding.

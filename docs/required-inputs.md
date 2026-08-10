# What you need to collect to build a SOW

Derived from four issued Premier Cloud SOWs (CoachHub, City Winery, Afni, Miles
Partnership). Use this as the discovery-call checklist; the schema in
`schemas/sow-intake.schema.json` is the machine-readable version of the same
thing, and `scripts/validate_intake.py` will tell you which of these you are
still missing for a specific deal.

Legend: **R** = required to render · **N** = needed before sending to a customer ·
optional otherwise.

---

## A. Universal — every SOW, every type

### Parties
| Input | | Notes |
|---|---|---|
| Customer legal entity name | R | As it appears on the MSA. "Afni, Inc." not "Afni". |
| Customer short name | R | Used throughout the body text. |
| Customer address | N | Registered or billing address. |
| SOW point of contact: name, email, phone | R | Section 1 table. |
| Signatory: name, title | N | Frequently *not* the person in the meeting. Ask explicitly. |
| Premier Cloud contact + signatory | | Defaults to Jason Murray-Rosel; override for the deal team. |

### Contract frame
| Input | | Notes |
|---|---|---|
| MSA style | R | Public link (default) vs. a negotiated Master Professional Services Agreement with a date. |
| SOW execution date | R | Date, or the literal "date of last signature". |
| Effective date / start | R | |
| Estimated end date | R | |
| Duration in weeks | N | Drives the Gantt. 5 weeks is the standard GE implementation, 8 a pilot, 10 a migration. |
| Term extendable? | | Adds the mutual-written-agreement sentence. |

### Commercials
| Input | | Notes |
|---|---|---|
| Total fixed price | R | |
| Google funding amount | N | Rendered as a credit line. |
| Funding programme / stage | | PSF vs Commit PSF; stage drives the Funding Disclosure paragraph. |
| Partner investment | | Where Premier Cloud co-funds to reach net $0. |
| **Net cost to customer above zero?** | R | If yes, the funding-reversal (clawback) paragraph is mandatory. |
| Google usage-data consent needed? | | Adds the third-party-beneficiary clause. |

### Scope and delivery
| Input | | Notes |
|---|---|---|
| Business challenges being solved | R | Quantify wherever the customer gave you a number. |
| Objective paragraph | N | What the engagement proves or delivers. |
| **Deal-specific exclusions** | N | Everything raised in the meeting and parked. The highest-value thing on this page. |
| Milestones and which week each lands | N | Defaults exist per type. |
| Deliverables | N | Must reconcile 1:1 with milestones. |
| Success criteria | N | Must be demonstrable at closure. |
| Deal-specific risks | N | Five standard risks are applied automatically. |
| Customer stakeholders and their roles | N | Feeds the Roles table and escalation matrix. |

---

## B. Gemini Enterprise Implementation

*The CoachHub / City Winery shape: seat-based rollout, connectors, enablement.*

| Input | | Notes |
|---|---|---|
| Seats provisioned | R | Caps the user community and appears in the UAT line. |
| Data sources to connect | R | Name every one, and mark which are federated. Connector count drives price and timeline. |
| In-scope user community | R | Departments or teams. |
| Identity provider | N | Google Identity is the default; anything else changes assumptions and adds an Identity Architect. |
| Workforce Identity Federation posture | N | Not required / customer already has a pool / customer must configure it. Selects the assumption paragraph and an exclusion. |
| Production or non-production project | | Default non-production. |
| Does the customer have a GCP org? | N | If not, set `cloud_foundations: true` — adds real work and should be priced. |
| Agentic workflows to build | | Name and behaviour of each no-code agent. If none, "Developing agentic workflows" is auto-excluded. |
| Activation plan numbers | N | Purchased licences, active users at project end, and at end + 4 weeks. Increasingly required by Google. |
| Golden dataset available? | | Sample Q&A pairs for evaluation. |

---

## C. Agent / CX Pilot

*The Afni shape: fixed-term pilot proving named agents against named use cases.*

Everything in A, plus:

| Input | | Notes |
|---|---|---|
| Customer profile paragraph | R | Who they are, size, footprint, why they are looking at this. |
| Objective paragraph | R | What the pilot proves and on what evidence. |
| **Per use case:** name | R | |
| **Per use case:** current solution, step by step | R | Numbered, in the customer's sequence, naming their systems. The most meeting-dependent content in any SOW. |
| **Per use case:** proposed solution | R | What we build and how it changes the flow. |
| **Per use case:** trigger | N | Inbound call, API dispatch, work basket. |
| **Per use case:** systems of record read from / written back to | N | |
| **Per use case:** success metrics | N | |
| **Per use case:** price | | Enables per-agent line items in the cost table. |
| Baseline metrics + their source | N | e.g. "44-minute AHT, ServiceNow March–May 2026". A baseline without provenance cannot be defended at closure. |
| Pilot environment | N | Production sandbox, dev, or sample-data layer. |
| Telephony entry point | N | GTP for the pilot; production approach is usually a recommendation. |
| Dated task schedule | N | Phase-by-phase with start and end dates. |
| Figures needed | | Captions only — diagrams are pasted in manually. |

---

## D. Workspace Migration

*The Miles Partnership shape: data + identity migration in parallel tracks.*

Everything in A, plus:

| Input | | Notes |
|---|---|---|
| Customer profile paragraph | R | |
| Source platform | R | e.g. "Microsoft 365 (Exchange Online, OneDrive, SharePoint Online)". |
| Destination platform | | Defaults to Google Workspace. |
| Migration tool | | Defaults to CloudM Migrate. |
| Number of domains | N | |
| Active user count | R | |
| Mailbox count **and size distribution** | N | The distribution builds the wave plan. Ask for the breakdown, not the total. |
| Data volumes per system | N | Mail, OneDrive, SharePoint, PSTs. Total TB drives worker-pool sizing. |
| Endpoint counts by platform | N | And which platforms are actually *in scope* — not everything that exists. |
| MDM platform | N | |
| Directory being decommissioned | N | |
| SSO-integrated applications | N | Get the actual list. Each becomes a validation line. |
| Worker node count and split | | e.g. "12 workers (5 mail + 7 file)". |
| Pilot user count | | Default 25. |
| Track and phase plan | R | Parallel tracks, ordered phases, wave sizes and weeks. |
| Activity schedule with effort hours | R | Per track, with deliverables and dates. |
| Resource allocation | N | Roles, hours, responsibilities. |
| Open customer decisions + deadlines | N | Each becomes a dated dependency. |
| Live project plan link | | Google Sheet Gantt, if one exists. |
| Appendices | | e.g. the CloudM watchpoints link. |

---

## The questions worth asking in every discovery call

Ordered by how often the answer turns out to be missing when the SOW is drafted:

1. Who signs, and what is their title?
2. What did we discuss today that is explicitly **not** in this phase?
3. What is the customer's net cost after funding — and is funding approved yet?
4. What numbers describe today's state, and what system did they come from?
5. Which decisions are still open on the customer side, and by when do we need them?
6. What does the customer have to have finished before we can start?
7. What does "done" look like to the person paying?

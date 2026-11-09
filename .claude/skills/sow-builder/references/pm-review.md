# Senior PM review

A second review, after the document checklist, asking a different question.

`review-checklist.md` asks **is this document correct?** — does it add up, does
it contradict itself, is the legal language intact. That review never leaves
the file.

This one asks **if we sign this, can we deliver it?** That question cannot be
answered from the document, because the document is where the optimism lives.
Answering it means going and finding evidence: who is actually free, what
happened the last three times we scoped work this shape, whether the critical
path runs through someone who has not agreed to anything.

A SOW can pass every item on the checklist and still be undeliverable.

---

## How to run it

**Run it with fresh eyes.** If you wrote the intake, you will defend it. Where
a subagent is available, delegate this review and give it the SOW, the intake
and the evidence sources — but not your opinion of them. A reviewer handed a
conclusion returns it confirmed.

**Start with the mechanical pass**, which is cheap and catches the arithmetic:

```bash
python3 scripts/pm_review.py intake/<customer>.intake.json
```

That covers term and schedule integrity, implied FTE, resource reconciliation,
effective hourly rate, unowned dependencies, acceptance and change control. It
only knows what is in the file. Exit 1 means at least one HIGH finding.

**Then do the part the script cannot**: the four questions below that need
outside evidence. This is the review. Budget real effort for it — on a six
figure engagement it is worth twenty minutes of digging.

---

## Where the evidence lives

Gather before you judge. Each of these answers a different question, and a
finding without one of them behind it is just an opinion.

| Source | What you are looking for |
|---|---|
| Portfolio / capacity tracker | Who is allocated to what, at what percentage, over the SOW's term. Named leave. Who is already carrying escalations. |
| Delivery Jira projects | For comparable past engagements: planned end date vs actual, issue counts, how long close-out took after "delivery complete". |
| Past SOWs for the same work type | Hours, price, team shape and term for the nearest comparable. The intake examples are synthetic; the real ones are in Drive. |
| Pre-sales tracker | The opportunity's stage, value and history. A SOW quoting a figure the opportunity does not carry is a conversation to have internally first. |
| The customer's own thread | What they asked for in writing. Commitments made in email that the SOW does not carry are the ones that get argued about. |
| Shared trackers the customer maintains | Where the customer runs their own plan, the SOW must not contradict it. Two sources of truth become two sets of dates. |

Cite what you find. A finding reads as `claim — evidence — consequence — fix`,
and the evidence is a named source, not a feeling.

---

## The four questions

### 1. Can we actually staff this, with these people, in this window?

The resource table names roles and hours. Check them against the capacity
tracker, not against hope.

- Is each named person allocated to this engagement for the term, or are they
  currently at 90% on three other projects?
- Does anyone on the critical path have booked leave inside the term?
- Is there a single person without whom this stops? `pm_review.py` flags the
  concentration; you decide whether the named backup is real.
- If the work starts on signature, does the team exist *then*, or are we
  assuming an engagement that has not closed yet will free someone up?

A SOW that assumes an engineer who is 95% allocated is not a plan, it is a
request for an escalation in week three.

### 2. Does this timeline survive our own track record?

Find the nearest two or three comparable engagements and look at what actually
happened, not what their SOWs said.

- Planned end date versus real end date. If similar work has routinely run
  past its contracted dates, a term with no slack is a commercial exposure,
  not just an estimate.
- How long did close-out take *after* the work was done? Acceptance, sign-off,
  evidence packs and funding claims consistently take longer than the plan
  allows for, and a term that ends at "delivery complete" leaves that unpaid.
- Were there change orders? If comparable engagements all needed one, this one
  will too, and the route needs to be in the document.

State what you find with the numbers: *"the two comparable migrations ran N
and M weeks past their contracted end dates"* is a finding. *"migrations often
slip"* is not.

### 3. What is the critical path, and who else is standing on it?

Most slips are not ours. They are a customer dependency nobody owned.

- Walk the plan backwards from cutover, go-live or final acceptance. What has
  to be true, and who makes it true?
- For every customer-owned prerequisite: is there a named owner and a date? Is
  it in the document, or only in a tracker? If the SOW does not say it, we
  cannot rely on it later.
- Administrative access and licensing deserve their own look. Access arriving
  late is the most common single cause of a start date moving, and if the
  assumption is not written down the slip lands on us.
- Where the customer has tied something to signature — access, accounts,
  environments — the term cannot start before signature plus that lead time.

### 4. Is the money attached to something we can prove we did?

- What artefact triggers the final invoice, and who signs it? If the answer is
  "the work finishes", final payment will drift.
- Where funding is involved, what evidence does the claim need, and is
  producing it in scope? An evidence pack nobody scoped is unpaid work at the
  least convenient moment.
- Does the effective hourly rate stand up against comparable engagements? The
  script flags the band; you check the comparable. A rate well below it means
  either the hours are inflated or delivery loses money — both worth knowing
  before signature rather than after.
- Is the scope that will certainly be added routed through a change mechanism,
  or will it be absorbed?

---

## Severity

| | |
|---|---|
| **HIGH** | Do not send. It will cost money, or it will cost credibility with the customer. Unstaffable, unprovable, or contradicts something we have already said in writing. |
| **MEDIUM** | Send only if someone decides, consciously and on the record, to accept it. Note the decision in the covering message. |
| **LOW** | Worth a sentence. Do not let these crowd out the first two. |

Rank by what it costs if you are right, not by how certain you are.

---

## Writing the review

Lead with the verdict — send, send with conditions, or hold — then the
findings, worst first. Four lines each:

> **The endpoint track has 216 hours of work against an engineer allocated 96.**
> Resource table versus activity schedule in the intake. Both tables print in
> the client-facing document, so the customer can find the gap themselves.
> Either raise the allocation or cut the track.

Then say plainly what you could not check, and why. A review that does not
name its blind spots reads as more complete than it is.

## What this review is not

- **Not a re-run of the document checklist.** If you find yourself checking the
  MSA URL, you are in the wrong review.
- **Not a rewrite.** Report the finding and the fix; let the owner decide. A
  reviewer who edits the SOW has stopped reviewing it.
- **Not a search for benchmarks that do not exist.** If there is no comparable
  engagement, say the estimate is unanchored. That is itself the finding.
  Never invent a ratio to have something to compare against.
- **Not softened for being awkward.** The findings that matter are the ones
  somebody will be annoyed by. "This cannot be staffed" is the review doing
  its job.

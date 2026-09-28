# The Master Services Agreement reference

Every Premier Cloud SOW must bind itself to the MSA. This page is the standard.

---

## Why it is not optional

A SOW is not a standalone contract. It describes scope, timeline and fee — and
nothing else. Liability caps, IP ownership, confidentiality, warranties,
indemnities and termination all live in the Master Services Agreement. A SOW
that does not reference the Agreement leaves every one of those terms unstated.

That is not a drafting preference, it is the difference between a bounded
engagement and an unbounded one.

**There is no way to switch this off.** The preamble renders on all four SOW
types, and `scripts/test_render.py` fails any SOW produced without it.

## The clause

It is the first paragraph, before section 1, and comes in two forms.

### `public_link` — the default

Use when there is no separately negotiated agreement, which is most deals. The
customer is bound by signing the SOW.

> This Statement of Work ("SOW") is executed *{date}* ("SOW Execution Date")
> between *Premier Cloud Inc.* ("Partner") and *{Customer}* ("Customer"). This
> SOW is entered into pursuant to the terms of the Master Services Agreement
> ("Agreement"), available at {url}. By signing this SOW, Customer acknowledges
> that it has reviewed, understands, and agrees to be bound by the terms of the
> Agreement. …

### `dated_mpsa`

Use when a negotiated Master Professional Services Agreement has been signed.
`agreement.msa_date` becomes **required** — the validator blocks a dated
reference with no date, since it cites an agreement that cannot be identified.

> …and is entered into pursuant to the terms of the [Master Professional
> Services Agreement]({url}) dated *{msa_date}* (the "Agreement"). …

Both forms end with the same precedence sentence, which is the operative part:

> Except as otherwise permitted by the Agreement, in case of any conflict
> between this SOW and the Agreement, the Agreement shall control.

## The URL — use the short one

```
https://premiercloud.com/master-services-agreement.pdf
```

It is a **stable redirect**. It currently resolves to:

```
https://premiercloud.com/wp-content/uploads/2024/06/MASTER-SERVICES-AGREEMENT-PREMIER-CLOUD-INC.pdf
```

Never quote that second form in a SOW. The `/2024/06/` segment is the upload
date — re-uploading the file moves it, and every SOW citing the old path then
points at a 404. A contract that references an unreachable agreement is a
problem you discover at exactly the wrong moment.

The canonical URL is set once, in `library/clauses.yaml` under `agreement:`.
Leave `agreement.msa_url` unset in intake files; overriding it is flagged.

## Known drift

Not every issued SOW is consistent. Two patterns exist in the back catalogue:

- SOWs quoting the **brittle wp-content URL** directly instead of the redirect.
  Correct at next revision.
- SOWs with **no MSA reference at all**, which means no stated liability cap, IP
  terms or termination rights against a signed fee.

Premier Cloud keeps the specific list internally; ask the SOW owner rather than
assuming a given document is compliant.

## What the tooling enforces

`scripts/validate_intake.py` reports:

- `agreement.msa_url` overridden away from canonical, with both values shown
- `msa_style: dated_mpsa` without `msa_date`
- an unrecognised `msa_style`, which would stop the preamble rendering

`scripts/test_render.py` fails the build if a rendered SOW:

- contains no Agreement reference
- omits the canonical URL (except under `dated_mpsa`)
- contains a `wp-content/uploads` link

## Changing the wording

The clause text is house legal language in `library/clauses.yaml` under
`preamble:`. Change it there so every future SOW moves together, and only with
legal sign-off. Editing a rendered document changes one file and leaves the
standard untouched.

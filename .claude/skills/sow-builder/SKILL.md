---
name: sow-builder
description: Build a Premier Cloud Statement of Work from meeting notes, a transcript, a discovery call summary, or a Google Doc. Use whenever the user asks to draft, generate, build, or update a SOW or Statement of Work, mentions turning notes or a discovery call into a SOW, or asks what inputs are needed to scope one. Handles Gemini Enterprise implementations, agent/CX pilots, and Workspace migrations.
---

# SOW Builder

Turn meeting notes into a Premier Cloud SOW in the house format.

The pipeline is deliberately two-stage. **Extraction** is the model's job — reading
messy notes and producing a structured intake file. **Rendering** is the script's
job — deterministic, so the legal and commercial language is identical on every
document. Never hand-write the SOW prose that the clause library already owns.

```
meeting notes  ──►  intake .json  ──►  validate_intake.py  ──►  render_sow.py  ──►  SOW.md  ──►  Google Doc / .docx
   (you read)      (you write)          (gap report)           (deterministic)      (review)
```

## Step 1 — Pick the SOW type

| Type | Use when | Reference example |
|---|---|---|
| `gemini_enterprise_implementation` | Seat-based Gemini Enterprise rollout: connectors, enablement, adoption | `examples/coachhub.intake.json` |
| `agent_pilot` | Fixed-term pilot proving one or more agents against named use cases | `examples/afni.intake.json` |
| `workspace_migration` | M365 (or similar) → Google Workspace data and/or identity migration | `examples/miles-partnership.intake.json` |

If the notes describe something else, pick the nearest type and say so in your
summary — do not invent a fourth template silently.

## Step 2 — Read the source material

Meeting notes arrive as a Google Doc link, a pasted transcript, a Gemini/Fireflies
summary, or an email thread. For Drive links use `search_files` to resolve the ID
if you only have a title, then `read_file_content`.

Read `references/extraction-playbook.md` before extracting. It maps the things
people actually say in discovery calls onto the intake fields, and lists what to
do when the notes are silent.

## Step 3 — Write the intake file

Write `intake/<customer>.intake.json` against `schemas/sow-intake.schema.json`.

Three rules that matter more than the rest:

1. **Do not invent numbers.** Seat counts, data volumes, ticket volumes, prices,
   dates and headcounts either came from a source or they did not. If a number
   is inferred, leave the field out and record the question in
   `provenance.unanswered`. A confidently wrong seat count survives review; a
   blank one does not.
2. **Record where everything came from.** Fill `provenance.sources` with the doc
   IDs or meeting dates, and `provenance.assumed` with anything you inferred
   rather than read. Reviewers need to know which sentences to check.
3. **Deal-specific exclusions are the highest-value thing you extract.** The
   standard `Out of Scope` list is applied automatically. What prevents a scope
   dispute six weeks in is the thing the customer asked about and someone said
   "not in this phase" — capture every one in `scope.out_of_scope_extra`.

## Step 4 — Validate and close the gaps

```bash
python3 scripts/validate_intake.py intake/<customer>.intake.json
```

This prints three things: blocking gaps, open questions, and consistency
warnings. Each gap comes with the question to ask and where the answer usually
lives.

**Bring the blocking list back to the user before rendering.** Ask the questions
in one batch — do not render a document full of `[TBD]` and hope. If the user
wants to see the shape of it anyway, `render_sow.py --force` stubs the gaps with
visible `[TBD: …]` markers.

Take the consistency warnings seriously. The clawback check in particular: any
time the customer's net cost is above zero and Google funding is in the table,
the funding-reversal paragraph must be present or Premier Cloud carries the risk.

## Step 5 — Render

```bash
python3 scripts/render_sow.py intake/<customer>.intake.json -o build/<customer>-sow.md
```

## Step 6 — Review before it goes anywhere

Walk `references/review-checklist.md`. It is short and every item on it has been
wrong in a real document at least once.

## Step 7 — Deliver

- **Google Doc** (usual route): create the doc, then paste the Markdown with
  *Edit → Paste from Markdown* enabled so headings and tables convert. Diagrams
  are pasted in manually at the `[INSERT DIAGRAM: …]` markers.
- **.docx**: use the `docx` skill on the rendered Markdown.
- Keep the intake file. Version 1.1 of a SOW is an edit to the intake plus a
  re-render, not a fresh draft.

## What this does not do

- It does not draw architecture diagrams, call flows, or Gantt images. The
  templates emit captioned placeholders.
- It does not price the work. Pricing comes from the deal team and goes into the
  intake; the builder only formats it and checks it adds up.
- It does not replace legal review of any clause that has been edited away from
  `library/clauses.yaml`.

## Editing house language

`library/clauses.yaml` is the single source of the standard language. If a
sentence needs to change for every future SOW, change it there. If it changes for
one deal only, override it in that deal's intake file. Never edit the rendered
Markdown and expect it to persist.

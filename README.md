# Premier Cloud SOW Builder

Turns meeting notes into a Premier Cloud Statement of Work in the house format.

Built from four issued SOWs — CoachHub, City Winery (Gemini Enterprise
implementations), Afni (GECX agent pilot), and Miles Partnership (Workspace
migration). The standard legal, commercial and scope language from those
documents lives in `library/clauses.yaml` and is reproduced verbatim on every
generated SOW.

---

## The idea

A SOW is roughly 60% boilerplate and 40% deal-specific content. The boilerplate
should never be re-typed or re-worded, because every variation is a small legal
risk. The deal-specific content is exactly the part that lives in meeting notes.

So the pipeline splits along that line:

```
meeting notes  ──►  intake.json  ──►  validate  ──►  render  ──►  SOW.md  ──►  Google Doc / .docx
                    ▲                  ▲              ▲
              model reads notes    gap report     deterministic:
              and fills the        of questions   boilerplate is
              structured fields    to go ask      identical every time
```

The model does the reading and structuring. The script does the assembly. Nobody
re-writes the indemnity language by hand.

## Quick start

```bash
pip install -r requirements.txt

# See the pipeline on a worked example
python3 scripts/validate_intake.py examples/northwind.intake.json
python3 scripts/render_sow.py    examples/northwind.intake.json -o build/northwind-sow.md
```

`examples/meeting-notes/northwind-discovery-notes.md` is the input those notes
were extracted from — read the two side by side to see what the extraction step
is actually doing, including which fields were deliberately left blank.

## Using it from Claude Code

Ask in this repo:

> Build a SOW from these notes: <paste, or a Google Doc link>

The `sow-builder` skill (`.claude/skills/sow-builder/`) drives the whole flow:
picks the SOW type, reads the source, writes the intake, runs the gap report,
brings the open questions back to you, renders, and checks the result against the
review checklist.

## The three SOW types

| Type | Shape | Reference |
|---|---|---|
| `gemini_enterprise_implementation` | Seat-based rollout: connectors, testing, adoption, enablement. 14 numbered sections. | `examples/coachhub.intake.json` |
| `agent_pilot` | Fixed-term pilot. Same skeleton plus Customer/Partner profiles and a per-use-case *Current Solution / Proposed Solution* treatment. | `examples/afni.intake.json` |
| `workspace_migration` | Structurally different: Executive Summary → Profiles → parallel tracks and phases → activity schedule with effort hours → Investment Summary. | `examples/miles-partnership.intake.json` |

Those three example intakes are reconstructions of the issued documents. They
double as regression fixtures — `scripts/test_render.py` fails if the generator
drifts away from what Premier Cloud actually sent a customer.

## What inputs you need

`docs/required-inputs.md` is the discovery-call checklist, organised by project
type, marking what is required to render versus what is required before a
document can be sent.

`schemas/sow-intake.schema.json` is the same information in machine-readable
form. Every field carries an `x-question` (what to ask) and an `x-source` (where
the answer normally lives) — which is how the gap report turns a missing field
into a question you can paste into an email.

## Layout

```
.claude/skills/sow-builder/   the automation: SKILL.md + extraction playbook + review checklist
library/clauses.yaml          house language. One place. Edit here, not in output.
schemas/                      intake contract, with the question behind every field
templates/                    one Jinja template per SOW type + shared partials
scripts/
  sowlib.py                   clause/intake merge and context building
  validate_intake.py          gap report + consistency checks
  render_sow.py               intake -> Markdown
  test_render.py              round-trip tests over the example intakes
examples/                     three reconstructions + one worked notes->intake example
docs/required-inputs.md       the discovery-call checklist
build/                        generated output (gitignored)
```

## Checks that earn their keep

`validate_intake.py` does more than presence checking:

- **Funding clawback.** If the customer's net cost is above zero and Google
  funding is in the table, the funding-reversal paragraph must be present.
  Omitting it means Premier Cloud absorbs the credit if Google declines. This is
  the most expensive mistake the tool can catch.
- Google funding cannot exceed the total fee.
- Every milestone lands at least one deliverable, and no milestone falls outside
  the Term.
- Seat count matches the activation plan's purchased licences.
- Projected active users at project end do not exceed licences purchased.
- Every `agent_pilot` use case has a Current Solution — the Proposed Solution has
  nothing to contrast against without it.
- Flags when no deal-specific exclusions were recorded, since the standard list
  alone rarely prevents a scope dispute.

## Notes on the source documents

Two things worth knowing, both carried into the templates as improvements rather
than reproduced as-is:

- **The Miles Partnership SOW had no legal preamble.** The other three bind the
  SOW to the Master Services Agreement in an opening paragraph; the migration one
  went out without it, against a $68,000 net customer fee. The
  `workspace_migration` template now includes the standard preamble. If that was
  deliberate, set the intake's `agreement` block accordingly and remove it.
- **Out-of-scope lists differ between the two Gemini Enterprise SOWs** in ways
  that look incidental rather than intentional (City Winery excludes agentic
  workflows outright; CoachHub scopes one in and narrows the exclusion). The
  library treats the CoachHub position as the base and derives the exclusion
  automatically from whether any agents are actually in scope.

## Not handled

- Diagrams. Templates emit `[INSERT DIAGRAM: …]` placeholders with the caption;
  architecture and call-flow figures are pasted in during review.
- Pricing derivation. The deal team sets the price; the builder formats it and
  checks it adds up.
- Direct Google Docs writing. Render to Markdown, then paste with
  *Paste from Markdown* enabled, or convert with the `docx` skill.

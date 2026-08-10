# Northwind Logistics — Gemini Enterprise discovery call

**Date:** 2026-08-04
**Attendees:** Priya Raman (Northwind, VP IT), Tom Deakin (Northwind, IT Ops Manager),
Jason Murray-Rosel (Premier Cloud), Adel Ben Rzouga (Premier Cloud)

*(Synthetic example. Used to demonstrate the extraction step — notes in, intake out.)*

---

Priya opened by saying the driver for this is that their ops teams spend a lot of
time hunting for information. Their words: "if a dispatcher needs to know what
happened on a shipment, they're checking the TMS, then Slack, then somebody's
inbox." Tom reckons it's an hour a day per person across the dispatch team,
though he said that's a gut number, not measured.

Second thing Priya raised — a lot of routine writing. Customer service drafts the
same three or four email types over and over. She'd like to see that get faster.

**Licences.** They've bought 180 Gemini Enterprise seats through the Google
account team. Priya confirmed 180.

**Who gets them.** Dispatch operations first, then Customer Service. Finance
asked to be included but Priya said that's a later phase — she doesn't want to
widen it yet.

**Data sources.** Tom listed: Google Drive, Gmail, Google Calendar, and
Confluence Cloud. He also asked about their TMS (it's a homegrown thing on
Postgres) — Adel said there's no connector for that and we'd be looking at
custom work, so we agreed to leave it out of this phase. Priya was fine with
that. Slack came up too — Tom wants it eventually, but again, not now.

**Identity.** They're a Google Workspace shop already, all users in Workspace, no
federation. Tom confirmed they have a GCP org set up from a previous BigQuery
project, so nothing to stand up there.

**Agents.** Priya asked whether we could build something that summarises a
shipment's history on demand. Adel explained that's TMS-dependent, so it's out
for now. No agents in this phase — she accepted that.

**Timing.** They want to start the week of 7 September and Priya needs it wrapped
before their peak season, so end of the first week of October. That's five weeks.

**Commercials.** Jason said the professional services fee is $38,000 and he'd be
putting it forward for PSF. Priya asked what happens if Google doesn't approve —
Jason said he'd confirm, but the expectation is full Google funding, so net zero
to Northwind. *(Action: Jason to confirm funding stage with the Google account
team.)*

**Activation.** Google will want activation numbers. Priya guessed 50 active
users by the end of the project and maybe 110 a month after. She stressed those
are estimates.

**Signing.** Priya said she isn't the signatory — that's their CFO, Marcus Bell.
She'll get us his details.

**Open items:**
- Jason to confirm PSF funding stage
- Priya to send Marcus Bell's title and email
- Tom to confirm Confluence Cloud is on the Cloud tier, not Server

# Zenchef / CoverManager Migration — context collected and inputs still needed

Prepared 29 October 2026. Nothing has been drafted yet; this is the scoping position
before the preliminary SOW is written.

---

## 1. What the engagement is

CoverManager and Zenchef are merging into one entity, with everything consolidating
under Zenchef. The Workspace piece is a **Google-to-Google tenant merge**: the
covermanager.com tenant folds into zenchef.com, with covermanager.com added as a
**secondary domain** so every user keeps their existing address. Same shape as the
Habyt → Hmlet engagement, so `sow_type: workspace_migration`.

- **Customer contact:** Javier González Salvador, Head of Engineering, Zenchef
  (javiergonzalez@covermanager.com). He replaced Antonio Castillo, who left.
- **Programme contact:** Kunesan Thayalan (welii.io), who opened the engagement.
- **Destination tenant contact:** Julien Balmont (julien@zenchef.com).
- **Premier Cloud:** Michael Penrose (CSM), Ian Basham (Operations),
  Bruno Maia (Migration specialist), Yahya Derbeli (GCP architect).
- **Opportunity:** PSE-312, "Zenchef — Renewal + Domain / GCP Migration",
  engineering lead Yahya Derbeli, stage **Discovery / Conversation, value TBD**.
- Javier on 29 Oct: *"we'll review it as soon as you share it. Please include the
  watchpoints and the cutover and rollback plan."* The SOW is the current blocker
  on their side — they have said dedicated super admin accounts get created
  **once the SOW is signed**.

## 2. Volumes — confirmed in writing this morning

From the Admin Console reports dated 27/10 and the Admin SDK export of 28/10:

| | |
|---|---|
| Total accounts | 289 (282 active, 5 suspended, 2 archived) |
| Flagged for review (no login 90+ days) | 20 |
| **Accounts proposed to migrate** | **262** |
| Shared / service mailboxes | 21 (licensed users, not Groups) |
| Groups / memberships | 51 / 428 (4 with external members, 2 empty) |
| User aliases | 153 |
| Shared drives | 59 |
| **Total data** | **~5.5 TB** |
| — Gmail | ~1.9 TB |
| — My Drive | ~2.5 TB |
| — Shared drives | ~1.0 TB |
| — Google Photos | ~80 GB |
| Largest single account | ~580 GB; 7 accounts above 100 GB |

This is a materially bigger job than Habyt → Hmlet (220 accounts) and bigger than
Miles Partnership, where a 2.3 TB archive alone carried a $9K work order. 5.5 TB
against Workspace API rate limits is the main driver of both the timeline and the
price.

## 3. Decisions already taken (tracker, Decisions tab)

1. Users keep their @covermanager.com addresses — secondary domain, not
   zenchef.com + alias.
2. The OAuth GCP project is **moved**, not recreated.
3. BigQuery stays in the old tenant; it is being retired.
4. A new reCAPTCHA key is issued in a Zenchef project.
5. SendGrid untouched; DNS work limited to Google DKIM and verification TXT.
6. Full-organization migration, mapped by naming scheme — no per-row user mapping
   sheet needed.

Also established on the 8 Oct call: CloudM copies and deletes nothing on the
source; cutover downtime 15–20 minutes; routing rules and custom DLP must be
recreated manually; Google IDs change, so Slack, Zoom and Figma need
re-authentication; SPF unchanged, DKIM updated at cutover; 3 GCP projects
(BigQuery, old clients, reCAPTCHA), with GCP operating independently of GWS.

## 4. What I have written down so far

- `intake/zenchef.intake.json` — every confirmed fact, with gaps left genuinely
  absent so the validator reports them rather than papering over them.
- `intake/zenchef.context-and-inputs.md` — this file.

The gap report currently returns **7 blocking and 7 open** items. Two of the
blocking ones (`migration.tracks`, `timeline.schedule`) are mine to write, not
yours to answer — I can build both from the tracker's 12 phases and 20 tasks as
soon as the effort and date inputs below land.

---

## 5. Inputs I need from you

### Tier 1 — blocking. The SOW cannot be issued without these.

1. **Contracting legal entity and registered address.** Who signs — Zenchef,
   CoverManager, or a merged entity? The work is on CoverManager's tenant but
   the consolidation is into Zenchef, and welii.io opened the thread. This
   determines the cover page, the signature block and which MSA applies.
2. **Authorised signatory** — name and title. Javier is the technical lead; I
   would not assume he is the signatory.
3. **Price and funding.** The opportunity is TBD at Discovery. I need the total
   fixed price, the currency, and whether this is customer-paid or carries
   Google funding. If funded, the funding programme and stage, because that
   changes the compensation language and brings in the clawback clause.
4. **Payment terms** — one-time on Net 30, or milestone-staged. Habyt/Hmlet was
   a single Net 30 fee; at 5.5 TB you may want it staged.
5. **Dates:** target execution date, effective date and end date. Javier has
   explicitly asked for per-phase target dates in the tracker's Timeline tab, so
   these are owed to the customer regardless of the SOW.

### Tier 2 — needed for a defensible document, not strictly blocking.

6. **Effort estimate per phase**, or total hours by role across Bruno, Ian and
   Yahya. The Activity Schedule table quotes hours; without them I either omit
   the column or invent numbers, and I will not invent them. If it is easier,
   give me a total and the split and I will distribute it across the 12 phases.
7. **Is GCP in or out of this SOW?** Javier has agreed GCP can be handled
   separately ("Separating GCP works for us"). Tracker phase 11 (GCP review with
   Yahya) and task T14 (move the OAuth project) currently sit inside the same
   plan. I would recommend carving GCP out into its own paper and keeping this
   one purely Workspace — but it is your call, and it changes the scope section.
8. **Is the renewal part of this?** PSE-312 is "Renewal + Domain / GCP
   Migration". If the licence renewal is a separate paper, say so and I will
   keep it out entirely.
9. **Rollback position.** Javier has asked, twice and in writing, for a cutover
   plan with the point of no return and what can be rolled back. That is a
   commitment, so I need the engineering line on it before I write it: what
   genuinely can be reversed after the domain move, and what cannot. Bruno or
   Ian should set this.

### Tier 3 — I will draft and you review.

These I can write from what we already have; flagging them so nothing surprises
you in the draft.

- The 12 phases and the activity schedule, built from the tracker.
- The three owner-TBD tasks (T11 routing/compliance/email-to-case, T12 SAML and
  domain-wide delegation, T14 OAuth project move) written as **Premier Cloud
  responsibilities or Customer responsibilities** — my default is to put the
  destination-side rebuild work on Premier Cloud and the source-side export and
  app-owner notification on the Customer, and to say so explicitly rather than
  leave "TBD" in a contract.
- The migration watchpoints Michael promised: Gmail filters and profile photos
  not migrating, Google IDs changing and forcing re-authentication, routing and
  DLP rules needing manual rebuild, the 580 GB account and the seven 100 GB+
  accounts needing their own sync window, and API rate limits on 5.5 TB.
- Out-of-scope list and assumptions, including the dependency on dedicated super
  admin accounts on both tenants, which the Customer has tied to SOW signature.
- Risks, led by: in-scope count moving between 262 and 289 depending on how the
  cleanup lands, and the tenant-wide Zenchef settings (Q7, Q8) still unanswered
  by the destination side.

---

## 6. One thing to decide early

The customer has made their tracker the single source of truth and asked us to
fill in the Timeline tab. If the SOW is going to quote dates and hours, those two
artefacts must agree. The cleanest sequence is: agree effort and dates
internally → fill the tracker Timeline tab → generate the SOW from the same
numbers. If we write the SOW first we will be reconciling two documents for the
rest of the engagement.

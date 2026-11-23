#!/usr/bin/env python3
"""Build the M365 to Google Workspace migration scoping workbook as a Google Sheet.

    python3 tools/scoping/build_m365_scoping_template.py            # create a new Sheet
    python3 tools/scoping/build_m365_scoping_template.py --dry-run  # print the plan only

An engineer fills the workbook in during discovery. Every tab maps onto the
`workspace_migration` intake (schemas/sow-intake.schema.json), so a complete
workbook becomes an intake file without re-keying, and the SOW Readiness tab
runs the checks the SOW reviewer (scripts/pm_review.py) would otherwise raise
after the document is drafted.

Needs the gws CLI, authenticated (tools/gws/bootstrap.sh). The Sheet is
created in the authenticated user's My Drive. This script holds the template
definition; to change the template, change it here and build a fresh copy.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

TITLE = "[TEMPLATE] M365 to Google Workspace Migration Scoping"

# One style for every tab.
BLUE = "#1E66AB"          # Premier Cloud primary
SECTION_BG = "#DCE8F5"
INPUT_BG = "#FFF2CC"
INPUT_FG = "#0000FF"
FORMULA_BG = "#EFEFEF"
GUIDE_FG = "#595959"
BORDER = "#D9D9D9"

YES_NO_TBD = ["Yes", "No", "TBD"]
LIST_ROWS = 20            # blank rows offered under each open list


def rgb(hex_):
    h = hex_.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255,
            "blue": int(h[4:6], 16) / 255}


def col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# --------------------------------------------------------------------------
# Tab model
# --------------------------------------------------------------------------

REFS = {}                 # "Tab.key" -> (tab title, A1 reference)


class Tab:
    def __init__(self, sid, title, widths, freeze=4):
        self.sid, self.title, self.widths, self.freeze = sid, title, widths, freeze
        self.cells = {}
        self.marks = []           # (kind, r1, c1, r2, c2)
        self.validations = []     # (r1, c1, r2, c2, options)
        self.status_ranges = []   # readiness status cells
        self.r = 5

    def set(self, r, c, v):
        self.cells[(r, c)] = v

    def mark(self, kind, r1, c1, r2=None, c2=None):
        self.marks.append((kind, r1, c1, r2 or r1, c2 or c1))

    def ref(self, key, r, c, absolute=False):
        a1 = f"${col(c)}${r}" if absolute else f"{col(c)}{r}"
        REFS[f"{self.short}.{key}"] = (self.title, a1)

    def ref_range(self, key, a1):
        REFS[f"{self.short}.{key}"] = (self.title, a1)

    def heading(self, title, subtitle):
        self.set(1, 1, title)
        self.mark("title", 1, 1)
        self.set(2, 1, subtitle)
        self.mark("subtitle", 2, 1)

    def header(self, r, labels):
        for i, v in enumerate(labels, 1):
            self.set(r, i, v)
        self.mark("header", r, 1, r, len(labels))

    def section(self, r, label, width):
        self.set(r, 1, label)
        self.mark("section", r, 1, r, width)

    def grid(self):
        maxr = max(r for r, _ in self.cells)
        maxc = max(c for _, c in self.cells)
        return [[self.cells.get((r, c), "") for c in range(1, maxc + 1)]
                for r in range(1, maxr + 1)]


def resolve(text, tab):
    """Replace {Tab.key} placeholders with A1 references."""
    def sub(m):
        title, a1 = REFS[m.group(1)]
        if title == tab.title:
            return a1
        return "'" + title.replace("'", "''") + "'!" + a1
    return re.sub(r"\{([A-Za-z]+\.[A-Za-z0-9_]+)\}", sub, text) if isinstance(text, str) else text


# --------------------------------------------------------------------------
# Key / value tabs
# --------------------------------------------------------------------------

KV_HEADER = ["Field", "Value", "How to get it", "Source and date", "SOW intake field"]
KV_WIDTHS = [300, 220, 380, 200, 220]


def kv_block(t, sections, start_row=5):
    """Field | Value | How | Source | Intake rows, grouped under section rows."""
    r = start_row
    t.header(r - 1, KV_HEADER)
    first = r
    for sec, items in sections:
        t.section(r, sec, 5)
        r += 1
        for it in items:
            t.set(r, 1, it["label"])
            t.set(r, 3, it.get("guide", ""))
            t.set(r, 5, it.get("intake", ""))
            t.mark("guide", r, 3)
            t.mark("guide", r, 5)
            if "formula" in it:
                t.set(r, 2, it["formula"])
                t.mark("formula", r, 2)
            else:
                t.set(r, 2, it.get("value", ""))
                t.mark("input", r, 2)
                t.mark("input", r, 4)
            if it.get("options"):
                t.validations.append((r, 2, r, 2, it["options"]))
            if it.get("date"):
                t.mark("date", r, 2)
            if it.get("number"):
                t.mark(it["number"], r, 2)
            if it.get("key"):
                t.ref(it["key"], r, 2)
            r += 1
    t.mark("table", first - 1, 1, r - 1, 5)
    return r


def list_block(t, r, title, headers, prefill, width_cols, inputs_from=1,
               options=None, key=None):
    """An open list at the bottom of a tab: prefilled rows, then blank rows."""
    t.section(r, title, width_cols)
    r += 1
    t.header(r, headers)
    hdr = r
    r += 1
    first = r
    for row in prefill:
        for i, v in enumerate(row, 1):
            t.set(r, i, v)
        r += 1
    r += LIST_ROWS
    last = r - 1
    # Prefilled rows keep their first columns as plain text; the rest is input.
    if prefill:
        t.mark("input", first, inputs_from, first + len(prefill) - 1, width_cols)
        if inputs_from > 1:
            t.mark("label", first, 1, first + len(prefill) - 1, inputs_from - 1)
    t.mark("input", first + len(prefill), 1, last, width_cols)
    for (c, opts) in (options or {}).items():
        t.validations.append((first, c, last, c, opts))
    t.mark("table", hdr, 1, last, width_cols)
    if key:
        t.ref_range(key + "_first", f"{first}")
    return first, last


# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------

def tab_engagement():
    t = Tab(1, "Engagement", KV_WIDTHS)
    t.short = "Eng"
    t.heading("Engagement",
              "Who the customer is, who signs, when, and how it is paid for.")
    kv_block(t, [
        ("Customer", [
            dict(key="legal", label="Customer legal entity",
                 guide="As written on the MSA or order form, not the brand name.",
                 intake="customer.legal_name"),
            dict(label="Short name used in the SOW", intake="customer.short_name"),
            dict(label="Registered address", intake="customer.address"),
            dict(label="Industry", intake="customer.industry"),
            dict(label="Customer profile",
                 guide="Two or three sentences: who they are, why they are moving, what they run today.",
                 intake="customer.profile"),
        ]),
        ("People", [
            dict(key="sig_name", label="Signatory name",
                 guide="The person who can sign the SOW, not the technical contact.",
                 intake="customer.signatory.name"),
            dict(key="sig_title", label="Signatory title", intake="customer.signatory.title"),
            dict(label="Primary contact name", intake="customer.contact.name"),
            dict(label="Primary contact title", intake="customer.contact.title"),
            dict(label="Primary contact email", intake="customer.contact.email"),
            dict(label="Project sponsor (escalation point)", intake="customer.stakeholders"),
            dict(label="Customer IT lead for the migration", intake="customer.stakeholders"),
            dict(label="Premier Cloud scoping engineer", intake="partner.team"),
            dict(label="Premier Cloud account executive", intake="partner.team"),
        ]),
        ("Contract and dates", [
            dict(key="msa", label="MSA status",
                 options=["Public MSA", "Negotiated MSA signed", "Negotiated MSA in progress"],
                 guide="A negotiated MSA still in review holds up signature of the SOW.",
                 intake="agreement.msa_style"),
            dict(label="MSA date (negotiated MSA only)", date=True, intake="agreement.msa_date"),
            dict(label="Target SOW signature date", date=True, intake="agreement.execution_date"),
            dict(key="start", label="Target start date", date=True, intake="term.effective_date"),
            dict(label="Hard deadline for cutover", date=True,
                 guide="Office move, merger close, board date. Leave blank if there is none.",
                 intake="term.end_date"),
            dict(key="m365_end", label="Microsoft 365 licence end or renewal date", date=True,
                 guide="Cutover has to finish before this, or the customer pays for both platforms.",
                 intake="risks"),
            dict(label="Blackout periods",
                 guide="Month-end close, peak season, holidays.", intake="assumptions"),
        ]),
        ("Licensing and funding", [
            dict(label="Google Workspace edition",
                 options=["Business Starter", "Business Standard", "Business Plus",
                          "Enterprise Standard", "Enterprise Plus", "Frontline", "Other"],
                 intake="migration.destination_platform"),
            dict(label="Google Workspace licences purchased", number="integer"),
            dict(label="Licences purchased through",
                 options=["Premier Cloud", "Google direct", "Other reseller"]),
            dict(label="Funding",
                 options=["Customer-paid", "Partly Google-funded", "Fully Google-funded"],
                 intake="pricing.google_funding"),
            dict(label="Funding program and approval status",
                 guide="Program name, amount requested, and whether Google has approved it.",
                 intake="pricing.funding_program"),
        ]),
    ])
    return t


def tab_source():
    t = Tab(2, "Source Tenant", KV_WIDTHS)
    t.short = "Src"
    t.heading("Source Tenant",
              "The Microsoft 365 environment as it is today, and the domains that move.")
    r = kv_block(t, [
        ("Tenant", [
            dict(label="Microsoft 365 tenants in scope", number="integer",
                 guide="More than one tenant usually means separate projects in the migration tool.",
                 intake="migration.source_platform"),
            dict(label="Tenant primary domain"),
            dict(label="Microsoft 365 licence types in use",
                 guide="For example E3, E5, Business Premium. Admin center > Billing > Licenses."),
            dict(label="Exchange deployment",
                 options=["Exchange Online only", "Hybrid (on-premises Exchange still present)",
                          "On-premises only"],
                 intake="migration.source_platform"),
            dict(label="Directory",
                 options=["Cloud-only Entra ID", "Entra Connect sync from on-premises AD",
                          "AD FS federation", "Other"],
                 intake="migration.endpoints.directory"),
            dict(label="MFA today",
                 guide="Method, and whether Conditional Access policies are in use."),
            dict(label="Devices managed by Intune", options=YES_NO_TBD,
                 intake="migration.endpoints.mdm"),
            dict(label="Third-party mail security",
                 guide="For example Mimecast or Proofpoint. Affects MX cutover and journaling."),
            dict(label="Retention policies or litigation holds", options=YES_NO_TBD,
                 guide="Held mailboxes need a Google Vault plan before data moves.",
                 intake="risks"),
            dict(label="Journaling in use", options=YES_NO_TBD),
            dict(label="Regulatory or data residency requirements", intake="assumptions"),
            dict(label="Admin account for Premier Cloud on Microsoft 365",
                 options=["Arranged", "Requested", "Not yet requested"],
                 guide="A dedicated account, not a person's credentials. Removed at closeout.",
                 intake="prerequisites_before"),
            dict(label="Super admin account for Premier Cloud on Google Workspace",
                 options=["Arranged", "Requested", "Not yet requested"],
                 intake="prerequisites_before"),
            dict(key="domains", label="Domains in scope (counted from the list below)",
                 formula="=COUNTA({Src.domain_col})", intake="migration.domain_count"),
        ]),
    ])
    first, _ = list_block(
        t, r + 1, "Domains",
        ["Domain", "Type", "Mail-enabled", "DNS hosted at", "Who can change DNS", "Notes"],
        [], 6, options={2: ["Primary", "Secondary", "Alias", "Subdomain"], 3: ["Yes", "No"]})
    t.ref_range("domain_col", f"A{first}:A")
    t.widths = [300, 220, 380, 200, 220, 260]
    return t


def tab_users():
    t = Tab(3, "Users & Objects", [300, 120, 420, 200, 220])
    t.short = "Usr"
    t.heading("Users & Objects",
              "Accounts and directory objects. Count from the admin center or PowerShell, and note which.")
    t.header(4, ["Object", "Count", "How to get it", "Source and date", "SOW intake field"])
    rows = [
        ("licensed", "Licensed user accounts (active)",
         "Admin center > Users > Active users, filtered to licensed.", ""),
        ("in_scope", "User accounts in scope for migration",
         "Licensed users less leavers, service accounts and anyone staying on Microsoft 365.",
         "migration.user_count"),
        ("leavers", "Disabled or unlicensed accounts with data to keep",
         "Decide per account: migrate, archive to a shared drive, or leave behind.", ""),
        ("shared", "Shared mailboxes",
         "Get-EXOMailbox -RecipientTypeDetails SharedMailbox", ""),
        ("rooms", "Room and equipment mailboxes",
         "Become Google Calendar resources.", ""),
        (None, "Distribution lists", "Become Google Groups.", ""),
        (None, "Microsoft 365 Groups",
         "Each has a mailbox, a SharePoint site and often a Team. Decide where each part goes.", ""),
        (None, "Mail-enabled security groups", "", ""),
        (None, "Mail contacts (external)", "", ""),
        (None, "User aliases (additional addresses)",
         "Proxy addresses beyond each user's primary address.", ""),
        (None, "Guest accounts (Entra B2B)", "Guests do not migrate; their access is re-shared.", ""),
        (None, "Pilot users", "Usually 10 to 25 people from different teams.",
         "migration.pilot_user_count"),
    ]
    r = 5
    for key, label, guide, intake in rows:
        t.set(r, 1, label); t.set(r, 3, guide); t.set(r, 5, intake)
        t.mark("input", r, 2); t.mark("input", r, 4); t.mark("integer", r, 2)
        t.mark("guide", r, 3); t.mark("guide", r, 5)
        if key:
            t.ref(key, r, 2)
        r += 1
    t.set(r, 1, "Mailboxes to migrate")
    t.set(r, 2, "={Usr.in_scope}+{Usr.shared}+{Usr.rooms}")
    t.set(r, 3, "In-scope users, shared mailboxes, and room and equipment mailboxes.")
    t.set(r, 5, "migration.mailbox_count")
    t.mark("formula", r, 2); t.mark("integer", r, 2); t.mark("guide", r, 3); t.mark("guide", r, 5)
    t.ref("mailboxes", r, 2)
    t.mark("table", 4, 1, r, 5)
    r += 2

    t.section(r, "Size distribution", 5)
    r += 1
    t.header(r, ["Size band", "Mailboxes", "OneDrive accounts", "Source and date", "Notes"])
    hdr = r
    r += 1
    first = r
    for band in ["Under 10 GB", "10 to 50 GB", "50 to 100 GB", "Over 100 GB"]:
        t.set(r, 1, band)
        t.mark("input", r, 2, r, 5); t.mark("integer", r, 2, r, 3)
        r += 1
    t.set(r, 1, "Total")
    t.set(r, 2, f"=SUM(B{first}:B{r - 1})")
    t.set(r, 3, f"=SUM(C{first}:C{r - 1})")
    t.set(r, 5, "Mailboxes should add up to Mailboxes to migrate above. The largest accounts set the wave plan.")
    t.mark("formula", r, 2, r, 3); t.mark("integer", r, 2, r, 3); t.mark("guide", r, 5)
    t.ref("band_total", r, 2)
    t.mark("table", hdr, 1, r, 5)
    return t


def tab_volumes():
    t = Tab(4, "Data Volumes", [300, 110, 110, 130, 170, 200, 300])
    t.short = "Vol"
    t.heading("Data Volumes",
              "Data per workload. Total in-scope volume drives the wave plan and the migration worker count.")
    t.header(4, ["Workload", "In scope?", "Size (GB)", "Items or files",
                 "Largest mailbox, user or site (GB)", "Source and date", "Notes"])
    workloads = [
        "Exchange mailboxes", "Exchange online archives", "PST files on PCs or file shares",
        "OneDrive", "SharePoint sites (excluding Teams)", "Teams channel files (stored in SharePoint)",
        "Teams chats", "Public folders", "OneNote notebooks", "Planner", "On-premises file shares",
    ]
    r = 5
    for w in workloads:
        t.set(r, 1, w)
        t.mark("input", r, 2, r, 7)
        t.mark("decimal", r, 3); t.mark("integer", r, 4); t.mark("decimal", r, 5)
        r += 1
    last = r - 1
    t.validations.append((5, 2, last, 2, YES_NO_TBD))
    t.mark("table", 4, 1, last, 7)
    r += 1
    t.section(r, "Totals", 7)
    r += 1
    for key, label, f, fmt in [
        ("gb", "In-scope volume (GB)", f'=SUMIFS(C5:C{last},B5:B{last},"Yes")', "decimal"),
        ("tb", "In-scope volume (TB)", None, "decimal2"),
        ("tbd", "Workloads still TBD", f'=COUNTIF(B5:B{last},"TBD")', "integer"),
        ("sites", "SharePoint sites listed below", None, "integer"),
    ]:
        t.set(r, 1, label)
        t.ref(key, r, 2)
        if key == "tb":
            f = "={Vol.gb}/1024"
        if key == "sites":
            f = "=COUNTA({Vol.site_col})"
        t.set(r, 2, f)
        t.mark("formula", r, 2); t.mark(fmt, r, 2)
        r += 1
    t.set(r - 4, 7, "Feeds migration.volumes in the SOW intake.")
    t.mark("guide", r - 4, 7)
    first, _ = list_block(
        t, r + 1, "SharePoint sites",
        ["Site URL", "Site type", "Size (GB)", "Items", "Target in Google", "Site owner",
         "Notes (broken permissions, very large libraries)"],
        [], 7,
        options={2: ["Team site", "Communication site", "Teams-connected", "Other"],
                 5: ["Shared drive", "My Drive", "Not migrating", "TBD"]})
    t.ref_range("site_col", f"A{first}:A")
    return t


def tab_identity():
    t = Tab(5, "Identity & Endpoints", [300, 220, 380, 200, 220, 220, 260])
    t.short = "Idn"
    t.heading("Identity & Endpoints",
              "How people sign in after the move, which devices change, and which applications need re-pointing.")
    r = kv_block(t, [
        ("Identity after migration", [
            dict(label="Identity provider after migration",
                 options=["Google", "Entra ID, federated to Google", "Other IdP (Okta, JumpCloud)", "TBD"],
                 guide="Decides whether Entra ID can be retired and who owns sign-in policy.",
                 intake="migration.sso_apps"),
            dict(label="User provisioning into Google",
                 options=["Google Cloud Directory Sync from AD", "Entra ID provisioning to Google",
                          "Manual or CSV", "TBD"]),
            dict(label="Passwords at cutover",
                 options=["Synced", "Reset at cutover", "SSO, no Google password", "TBD"]),
            dict(label="2-step verification method in Google"),
            dict(label="Directory being retired", intake="migration.endpoints.directory"),
        ]),
        ("Desktop apps", [
            dict(label="Keeping Microsoft Office desktop apps", options=YES_NO_TBD,
                 guide="Decides whether some Microsoft licences stay after cutover."),
            dict(label="Mail client after cutover",
                 options=["Gmail in the browser", "Outlook with Google Workspace Sync", "Mixed", "TBD"],
                 guide="Outlook users need a sync profile set up and support on cutover day."),
            dict(label="OneDrive sync client replaced by Google Drive for desktop", options=YES_NO_TBD),
        ]),
    ])
    r += 1
    t.section(r, "Endpoints", 7)
    r += 1
    t.header(r, ["Platform", "Count", "Managed by today", "Joined to", "In scope?",
                 "Target after migration", "Notes"])
    hdr = r
    r += 1
    first = r
    for p in ["Windows", "macOS", "iOS", "Android", "Shared or kiosk devices"]:
        t.set(r, 1, p)
        t.mark("input", r, 2, r, 7); t.mark("integer", r, 2)
        r += 1
    last = r - 1
    t.validations.append((first, 5, last, 5, YES_NO_TBD))
    t.validations.append((first, 4, last, 4,
                          ["Entra ID", "On-premises AD", "Hybrid", "Not joined", "Other"]))
    t.set(r, 1, "Endpoints in scope")
    t.set(r, 2, f'=SUMIFS(B{first}:B{last},E{first}:E{last},"Yes")')
    t.set(r, 3, "Feeds migration.endpoints.in_scope.")
    t.mark("formula", r, 2); t.mark("integer", r, 2); t.mark("guide", r, 3)
    t.mark("table", hdr, 1, r, 7)
    r += 2
    list_block(
        t, r, "Applications that sign in with Microsoft",
        ["Application", "Sign-in today", "Users", "App owner", "Re-point to Google?",
         "Who re-points it", "Notes"],
        [], 7,
        options={2: ["SAML", "OIDC", "Password", "Other"], 5: YES_NO_TBD,
                 6: ["Premier Cloud", "Customer", "Vendor", "TBD"]})
    return t


def tab_mail():
    t = Tab(6, "Mail Flow", KV_WIDTHS + [260])
    t.short = "Mail"
    t.heading("Mail Flow",
              "How mail reaches the tenant today, what has to keep working during the move, and what breaks at cutover.")
    r = kv_block(t, [
        ("Mail routing", [
            dict(label="MX records point to",
                 options=["Exchange Online Protection", "Mimecast", "Proofpoint", "Other"]),
            dict(label="Mail flow rules", number="integer",
                 guide="Exchange admin center > Mail flow > Rules. Each needs a Gmail equivalent or a decision to drop it."),
            dict(label="Inbound and outbound connectors", number="integer"),
            dict(label="SPF record today"),
            dict(label="DKIM enabled in Microsoft 365", options=YES_NO_TBD),
            dict(label="DMARC policy today", options=["None", "p=none", "p=quarantine", "p=reject"]),
        ]),
        ("During the migration", [
            dict(label="Cutover approach", options=["Single cutover", "Migration in waves", "TBD"],
                 intake="migration.tracks"),
            dict(label="Coexistence needed between waves", options=YES_NO_TBD,
                 guide="Needed when users move in waves and still mail each other across both platforms."),
            dict(label="Calendar free/busy across both platforms", options=YES_NO_TBD),
            dict(label="Delegation or send-as permissions in use", options=YES_NO_TBD,
                 guide="Shared mailbox delegates are granted again in Gmail."),
            dict(label="Who changes DNS at cutover", guide="A named person, and how much notice they need.",
                 intake="prerequisites_before"),
        ]),
    ])
    list_block(
        t, r + 1, "Systems sending mail through Microsoft 365",
        ["System or device", "How it sends", "Sending address", "Owner", "Notes", "Reconfigured by"],
        [], 6,
        options={2: ["SMTP relay", "SMTP AUTH", "Connector", "Graph API", "Other"],
                 6: ["Premier Cloud", "Customer", "Vendor", "TBD"]})
    return t


def tab_scope():
    t = Tab(7, "Scope & Exclusions", [320, 140, 200, 140, 380, 260])
    t.short = "Scp"
    t.heading("Scope & Exclusions",
              "What this phase delivers, how done is shown, and what the customer raised that is not in this phase.")
    t.section(4, "Success criteria", 6)
    t.header(5, ["Success criterion", "How it is shown at closure"])
    r = 6
    first = r
    for _ in range(6):
        t.mark("input", r, 1, r, 2)
        r += 1
    t.set(r, 1, "Write criteria that can be shown at closure: a count, a demonstration, a delivered "
                "report. Not satisfaction or sustained usage.")
    t.mark("guide", r, 1)
    t.ref("criteria_a", first, 1)
    REFS["Scp.criteria"] = (t.title, f"A{first}:A{r - 1}")
    t.mark("table", 5, 1, r - 1, 2)
    r += 2
    candidates = [
        "Teams chat history", "Teams channel conversations (files are covered under SharePoint)",
        "Planner plans", "Power Automate flows and Power Apps", "OneNote notebooks",
        "Public folders", "PST files on PCs", "On-premises file shares", "Online archive mailboxes",
        "Disabled or leaver accounts",
        "Mailbox rules, signatures and delegates (check what the migration tool carries)",
        "macOS devices", "Mobile devices", "Retiring Microsoft 365 or on-premises Exchange",
        "Replacing Intune or other device management", "Re-pointing third-party SSO applications",
        "SharePoint permission clean-up before migration",
        "End-user training beyond the agreed sessions", "Hypercare beyond the agreed weeks",
    ]
    first, _ = list_block(
        t, r, "In or out of this phase",
        ["Item", "In or out?", "Raised by, and when", "Agreed with customer?",
         "Wording for the SOW", "Notes"],
        [[c, "TBD"] for c in candidates], 6, inputs_from=2,
        options={2: ["In scope", "Out of scope", "TBD"], 4: ["Yes", "No"]})
    t.set(first - 3, 5, "Out-of-scope lines with SOW wording feed scope.out_of_scope_extra.")
    t.mark("guide", first - 3, 5)
    t.set(first - 3, 1, "Items not yet decided")
    t.set(first - 3, 2, f'=COUNTIF(B{first}:B,"TBD")+COUNTIFS(A{first}:A,"<>",B{first}:B,"")')
    t.mark("bold", first - 3, 1); t.mark("formula", first - 3, 2); t.mark("integer", first - 3, 2)
    t.ref("undecided", first - 3, 2)
    return t


def tab_decisions():
    t = Tab(8, "Decisions & Questions", [70, 420, 150, 110, 150, 110, 320, 120])
    t.short = "Dec"
    t.heading("Decisions & Questions",
              "Every open question gets an owner and a date. Open items become dated dependencies in the SOW.")
    questions = [
        "Will every user keep the same email address, or is the domain changing?",
        "Single cutover, or migration in waves?",
        "What happens to online archives and PST files?",
        "Which identity provider signs users in after the migration?",
        "Are Microsoft Office desktop apps or Outlook staying for any users?",
        "How do SharePoint sites map to shared drives?",
        "What happens to Teams chat history?",
        "Who changes DNS at cutover, and with how much notice?",
        "When do Microsoft 365 licences end, and how long is the overlap?",
        "How long is hypercare after cutover?",
        "How many training sessions, and for which groups?",
        "When are the dedicated admin accounts created on both tenants?",
    ]
    prefill = [[f"Q-{i:02d}", q, "", "", "", "Open"] for i, q in enumerate(questions, 1)]
    t.r = 4
    t.header(4, ["ID", "Question or decision", "Owner", "Needed by", "Blocks", "Status",
                 "Answer", "Answered on"])
    r = 5
    for row in prefill:
        for i, v in enumerate(row, 1):
            t.set(r, i, v)
        r += 1
    last = r - 1 + LIST_ROWS
    t.mark("label", 5, 1, r - 1, 2)
    t.mark("input", 5, 3, r - 1, 8)
    t.mark("input", r, 1, last, 8)
    t.mark("date", 5, 4, last, 4); t.mark("date", 5, 8, last, 8)
    t.validations.append((5, 3, last, 3, ["Premier Cloud", "Customer", "Google", "Vendor"]))
    t.validations.append((5, 5, last, 5, ["Discovery", "Pilot", "Bulk migration", "Cutover",
                                         "Endpoints", "Closeout"]))
    t.validations.append((5, 6, last, 6, ["Open", "Answered", "Decided", "Dropped"]))
    t.mark("table", 4, 1, last, 8)
    REFS["Dec.owner"] = (t.title, "C5:C")
    REFS["Dec.due"] = (t.title, "D5:D")
    REFS["Dec.status"] = (t.title, "F5:F")
    return t


def tab_risks():
    t = Tab(9, "Risks & Watchpoints", [460, 100, 300, 300, 150])
    t.short = "Rsk"
    t.heading("Risks & Watchpoints",
              "Common M365 to Google Workspace watchpoints. Mark which apply and say what they mean for this customer.")
    watch = [
        "Mailboxes or OneDrive accounts large enough to hit Google's per-user daily transfer limit. Check the current limit; these accounts need their own sync window.",
        "SharePoint libraries larger than one shared drive can hold. Check the current shared drive item limit and plan the split.",
        "File paths or names that Google Drive or the migration tool rejects.",
        "SharePoint permissions with broken inheritance that do not map onto shared drive roles.",
        "Content the migration tool does not carry, or carries partly: Teams chats, OneNote, Planner, mailbox rules. Confirm against the chosen tool.",
        "Applications and devices sending mail through Microsoft 365 that stop at MX cutover.",
        "Applications signing in through Entra ID that must be re-pointed before Entra ID is retired.",
        "Users staying on Outlook need a Google Workspace Sync profile and support on cutover day.",
        "Microsoft 365 licences ending before the last wave completes.",
        "DNS changes waiting on a third party, or on one person with limited availability.",
        "Admin access on either tenant arriving after the planned start.",
        "Litigation holds or retention policies to reproduce in Google Vault before data moves.",
    ]
    first, _ = list_block(
        t, 4, "Watchpoints",
        ["Watchpoint", "Applies?", "Detail for this customer", "Mitigation", "Owner"],
        [[w] for w in watch], 5, inputs_from=2,
        options={2: YES_NO_TBD, 5: ["Premier Cloud", "Customer", "Google", "Vendor"]})
    t.freeze = 5
    return t


def tab_effort():
    t = Tab(10, "Effort & Pricing",
            [150, 300, 90, 80, 80, 90, 100, 110, 110, 110, 300, 100])
    t.short = "Eff"
    t.heading("Effort & Pricing",
              "Hours per phase and role. The role totals and the schedule come from the same grid, so they always agree.")
    t.header(4, ["Track", "Phase", "In scope?", "Start week", "End week", "PM hours",
                 "Architect hours", "Migration engineer hours", "Endpoint engineer hours",
                 "Phase total (hours)", "Deliverable", "Sign-off needed?"])
    phases = [
        ("A. Data migration", "Preparation and discovery", "Yes"),
        ("A. Data migration", "Configuration and readiness scan", "Yes"),
        ("A. Data migration", "Pilot migration", "Yes"),
        ("A. Data migration", "Bulk migration in waves", "Yes"),
        ("A. Data migration", "Delta migration and cutover", "Yes"),
        ("A. Data migration", "Post-migration validation and hypercare", "Yes"),
        ("B. Identity and endpoints", "Endpoint inventory and SSO audit", "TBD"),
        ("B. Identity and endpoints", "Endpoint pilot", "TBD"),
        ("B. Identity and endpoints", "Endpoint waves", "TBD"),
        ("B. Identity and endpoints", "SSO re-pointing and directory retirement", "TBD"),
        ("C. Adoption", "Communications and training", "TBD"),
        ("All tracks", "Project governance (status meetings, reporting, change control)", "Yes"),
    ]
    r = 5
    for track, phase, scope in phases:
        t.set(r, 1, track); t.set(r, 2, phase); t.set(r, 3, scope)
        t.set(r, 10, f"=SUM(F{r}:I{r})")
        r += 1
    last = r - 1
    t.mark("label", 5, 1, last, 2)
    t.mark("input", 5, 3, last, 9); t.mark("input", 5, 11, last, 12)
    t.mark("formula", 5, 10, last, 10)
    t.mark("integer", 5, 4, last, 10)
    t.validations.append((5, 3, last, 3, YES_NO_TBD))
    t.validations.append((5, 12, last, 12, ["Yes", "No"]))

    t.set(r, 2, "In-scope total (hours)")
    for c in range(6, 11):
        L = col(c)
        t.set(r, c, f'=SUMIFS({L}5:{L}{last},$C5:$C{last},"Yes")')
    t.mark("formula", r, 6, r, 10); t.mark("integer", r, 6, r, 10); t.mark("bold", r, 2, r, 10)
    tot = r
    t.ref("hours", r, 10)
    r += 1
    t.set(r, 2, "Implied full-time people over the term")
    for c in range(6, 10):
        L = col(c)
        t.set(r, c, f"=IF({{Eff.weeks}}*{{Eff.billable}}=0,0,{L}{tot}/({{Eff.weeks}}*{{Eff.billable}}))")
    t.mark("formula", r, 6, r, 9); t.mark("decimal", r, 6, r, 9)
    t.set(r, 11, "Above 1.0 means more than one person in that role for the whole term.")
    t.mark("guide", r, 11)
    t.mark("table", 4, 1, r, 12)
    REFS["Eff.scope_col"] = (t.title, f"C5:C{last}")
    REFS["Eff.total_col"] = (t.title, f"J5:J{last}")
    REFS["Eff.deliv_col"] = (t.title, f"K5:K{last}")
    REFS["Eff.end_col"] = (t.title, f"E5:E{last}")
    r += 2

    t.section(r, "Term and commercials", 12)
    r += 1
    items = [
        ("weeks", "Term length (weeks)", f'=MAXIFS(E5:E{last},C5:C{last},"Yes")', "formula", "integer",
         "The latest end week among in-scope phases."),
        ("rate", "Blended hourly rate (USD)", "", "input", "currency",
         "Set by the deal team."),
        ("calc_fee", "Fee at the blended rate (USD)", "={Eff.hours}*{Eff.rate}", "formula", "currency", ""),
        ("price", "Proposed fixed price (USD)", "", "input", "currency",
         "The figure that goes in the SOW."),
        ("eff_rate", "Effective hourly rate (USD)",
         "=IF({Eff.hours}=0,0,{Eff.price}/{Eff.hours})", "formula", "currency", ""),
        ("funding", "Google funding (USD)", "", "input", "currency",
         "Leave blank if customer-paid."),
        ("net", "Customer net cost (USD)", "={Eff.price}-{Eff.funding}", "formula", "currency", ""),
        ("billable", "Billable hours per person per week", 32, "input", "integer",
         "Default used by the SOW reviewer (scripts/pm_review.py). Change it if the team plans differently."),
        ("band_low", "Expected rate range, low (USD)", 150, "input", "currency",
         "Default range used by the SOW reviewer. Confirm with the delivery lead."),
        ("band_high", "Expected rate range, high (USD)", 300, "input", "currency", ""),
    ]
    for key, label, val, kind, fmt, note in items:
        t.set(r, 2, label); t.set(r, 3, val); t.set(r, 4, note)
        t.mark(kind, r, 3); t.mark(fmt, r, 3); t.mark("guide_nowrap", r, 4)
        t.ref(key, r, 3)
        r += 1
    t.mark("table", r - len(items), 2, r - 1, 3)
    return t


def tab_readiness():
    t = Tab(11, "SOW Readiness", [460, 420, 200])
    t.short = "Rdy"
    t.heading("SOW Readiness",
              "When every check reads OK, the workbook has what the SOW builder needs.")
    checks = [
        ("Customer legal entity", '=IF(LEN({Eng.legal})=0,"Enter the legal entity","OK")', "Engagement"),
        ("Signatory name and title",
         '=IF(OR(LEN({Eng.sig_name})=0,LEN({Eng.sig_title})=0),"Enter the signatory name and title","OK")',
         "Engagement"),
        ("MSA status",
         '=IF({Eng.msa}="","Choose the MSA status",IF({Eng.msa}="Negotiated MSA in progress",'
         '"The negotiated MSA must be signed before or with the SOW","OK"))', "Engagement"),
        ("Target start date",
         '=IF(ISNUMBER({Eng.start}),"OK","Enter the target start date as a date")', "Engagement"),
        ("Microsoft 365 licences outlast the migration",
         '=IF(NOT(AND(ISNUMBER({Eng.m365_end}),ISNUMBER({Eng.start}))),'
         '"Enter the licence end date and the start date",'
         'IF({Eng.m365_end}<{Eng.start}+{Eff.weeks}*7,"Licences end before the planned finish","OK"))',
         "Engagement"),
        ("Users in scope", '=IF(LEN({Usr.in_scope})=0,"Enter users in scope","OK")', "Users & Objects"),
        ("Mailbox size distribution",
         '=IF({Usr.band_total}=0,"Enter the size distribution",'
         'IF({Usr.band_total}<>{Usr.mailboxes},"Size bands do not add up to mailboxes to migrate","OK"))',
         "Users & Objects"),
        ("Data volumes",
         '=IF({Vol.tbd}>0,{Vol.tbd}&" workloads still TBD",IF({Vol.gb}=0,"Enter data volumes","OK"))',
         "Data Volumes"),
        ("Success criteria", '=IF(COUNTA({Scp.criteria})=0,"Add at least one success criterion","OK")',
         "Scope & Exclusions"),
        ("Scope items decided",
         '=IF({Scp.undecided}>0,{Scp.undecided}&" items still TBD or blank","OK")',
         "Scope & Exclusions"),
        ("Open questions have an owner",
         '=IF(COUNTIFS({Dec.status},"Open",{Dec.owner},"")>0,'
         'COUNTIFS({Dec.status},"Open",{Dec.owner},"")&" open questions with no owner","OK")',
         "Decisions & Questions"),
        ("Open questions have a date",
         '=IF(COUNTIFS({Dec.status},"Open",{Dec.due},"")>0,'
         'COUNTIFS({Dec.status},"Open",{Dec.due},"")&" open questions with no date","OK")',
         "Decisions & Questions"),
        ("Phases decided",
         '=IF(COUNTIF({Eff.scope_col},"TBD")>0,COUNTIF({Eff.scope_col},"TBD")&" phases still TBD","OK")',
         "Effort & Pricing"),
        ("Every in-scope phase has hours",
         '=IF(COUNTIFS({Eff.scope_col},"Yes",{Eff.total_col},0)>0,'
         'COUNTIFS({Eff.scope_col},"Yes",{Eff.total_col},0)&" in-scope phases with no hours","OK")',
         "Effort & Pricing"),
        ("Every in-scope phase has a deliverable",
         '=IF(COUNTIFS({Eff.scope_col},"Yes",{Eff.deliv_col},"")>0,'
         'COUNTIFS({Eff.scope_col},"Yes",{Eff.deliv_col},"")&" in-scope phases with no deliverable","OK")',
         "Effort & Pricing"),
        ("Term length", '=IF({Eff.weeks}=0,"Enter start and end weeks for in-scope phases","OK")',
         "Effort & Pricing"),
        ("Effective rate within the expected range",
         '=IF({Eff.eff_rate}=0,"Enter hours and a proposed price",IF({Eff.eff_rate}<{Eff.band_low},'
         '"Below the expected range",IF({Eff.eff_rate}>{Eff.band_high},"Above the expected range","OK")))',
         "Effort & Pricing"),
        ("Funding-reversal clause",
         '=IF(AND({Eff.funding}>0,{Eff.net}>0),"Funded deal with a net cost: the SOW needs the funding-reversal clause","OK")',
         "Effort & Pricing"),
    ]
    t.set(4, 1, "Checks passing")
    t.set(4, 2, f'=COUNTIF(B7:B{6 + len(checks)},"OK")&" of {len(checks)}"')
    t.mark("bold", 4, 1); t.mark("formula", 4, 2); t.mark("bold", 4, 2)
    t.header(6, ["Check", "Status", "Fix on tab"])
    r = 7
    for label, f, where in checks:
        t.set(r, 1, label); t.set(r, 2, f); t.set(r, 3, where)
        t.mark("formula", r, 2)
        r += 1
    t.status_ranges.append((7, 2, r - 1, 2))
    t.mark("table", 6, 1, r - 1, 3)
    t.freeze = 6
    return t


def tab_start(tabs):
    t = Tab(0, "Start Here", [220, 420, 360], freeze=0)
    t.short = "Start"
    t.heading("M365 to Google Workspace migration: scoping workbook",
              "Fill this in during discovery. A complete workbook gives the SOW builder what it needs for a "
              "workspace migration SOW.")
    t.section(4, "How to use it", 3)
    steps = [
        "Fill the yellow cells on each tab. Grey cells are formulas.",
        "Note where each number came from in the Source column: the report or command, and the date.",
        "Record everything the customer raised that is not in this phase on Scope & Exclusions.",
        "Give every open question an owner and a date on Decisions & Questions.",
        "Enter hours per phase and role on Effort & Pricing.",
        "Check SOW Readiness. When every check reads OK, hand the workbook to the SOW builder.",
    ]
    r = 5
    for i, s in enumerate(steps, 1):
        t.set(r, 1, f"Step {i}"); t.set(r, 2, s)
        t.mark("bold", r, 1)
        r += 1
    r += 1
    t.section(r, "Legend", 3)
    r += 1
    t.set(r, 1, "Fill in"); t.set(r, 2, "Cells to complete. Entered values show in blue.")
    t.mark("input", r, 1)
    r += 1
    t.set(r, 1, "Formula"); t.set(r, 2, "Calculated from other cells. Do not type over these.")
    t.mark("formula", r, 1)
    r += 2
    t.section(r, "Where each tab goes in the SOW", 3)
    r += 1
    t.header(r, ["Tab", "What it captures", "SOW sections it feeds"])
    hdr = r
    r += 1
    feeds = {
        "Engagement": ("Customer, signatory, contract dates, licensing, funding",
                       "Cover, Term, Investment, Signatures"),
        "Source Tenant": ("Microsoft 365 setup, admin access, domains",
                          "Customer Profile, Assumptions, Prerequisites"),
        "Users & Objects": ("Accounts, mailboxes, groups, size distribution",
                            "Customer Profile, Migration Plan"),
        "Data Volumes": ("Data per workload, SharePoint sites", "Data Volumes"),
        "Identity & Endpoints": ("Sign-in after the move, devices, applications",
                                 "Project Scope (identity track), Success Criteria"),
        "Mail Flow": ("MX, mail rules, coexistence, systems that send mail",
                      "Project Scope, Assumptions and Dependencies"),
        "Scope & Exclusions": ("Success criteria, what is in and out of this phase",
                               "Success Criteria, Out of Scope"),
        "Decisions & Questions": ("Open questions with owner and date", "Assumptions and Dependencies"),
        "Risks & Watchpoints": ("Watchpoints that apply to this customer", "Risks"),
        "Effort & Pricing": ("Hours by phase and role, term, fee, funding",
                             "Activity Schedule, Resource Allocation, Timeline, Investment"),
        "SOW Readiness": ("Checks before the SOW is drafted", ""),
    }
    for tab in tabs:
        what, sow = feeds[tab.title]
        t.set(r, 1, tab.title); t.set(r, 2, what); t.set(r, 3, sow)
        r += 1
    t.mark("label", hdr + 1, 1, r - 1, 3)
    t.mark("table", hdr, 1, r - 1, 3)
    return t


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

def fmt_request(sid, kind, r1, c1, r2, c2):
    rng = {"sheetId": sid, "startRowIndex": r1 - 1, "endRowIndex": r2,
           "startColumnIndex": c1 - 1, "endColumnIndex": c2}
    f, fields = {}, []

    def tf(key, val):
        f.setdefault("textFormat", {})[key] = val
        fields.append(f"userEnteredFormat.textFormat.{key}")

    def bg(hex_):
        f["backgroundColor"] = rgb(hex_)
        fields.append("userEnteredFormat.backgroundColor")

    def num(type_, pattern):
        f["numberFormat"] = {"type": type_, "pattern": pattern}
        fields.append("userEnteredFormat.numberFormat")

    def wrap():
        f["wrapStrategy"] = "WRAP"
        fields.append("userEnteredFormat.wrapStrategy")

    if kind == "title":
        tf("bold", True); tf("fontSize", 14); tf("foregroundColor", rgb(BLUE))
    elif kind == "subtitle":
        tf("italic", True); tf("foregroundColor", rgb(GUIDE_FG))
    elif kind == "header":
        bg(BLUE); tf("bold", True); tf("foregroundColor", rgb("#FFFFFF")); wrap()
        f["verticalAlignment"] = "MIDDLE"; fields.append("userEnteredFormat.verticalAlignment")
    elif kind == "section":
        bg(SECTION_BG); tf("bold", True); tf("foregroundColor", rgb(BLUE))
    elif kind == "input":
        bg(INPUT_BG); tf("foregroundColor", rgb(INPUT_FG)); wrap()
    elif kind == "formula":
        bg(FORMULA_BG); tf("foregroundColor", rgb("#000000"))
    elif kind == "guide":
        tf("foregroundColor", rgb(GUIDE_FG)); tf("fontSize", 9); wrap()
    elif kind == "guide_nowrap":
        tf("foregroundColor", rgb(GUIDE_FG)); tf("fontSize", 9)
    elif kind == "label":
        wrap()
    elif kind == "bold":
        tf("bold", True)
    elif kind == "date":
        num("DATE", "yyyy-mm-dd")
    elif kind == "integer":
        num("NUMBER", "#,##0")
    elif kind == "decimal":
        num("NUMBER", "#,##0.0")
    elif kind == "decimal2":
        num("NUMBER", "#,##0.00")
    elif kind == "currency":
        num("CURRENCY", '$#,##0;($#,##0);"-"')
    elif kind == "table":
        line = {"style": "SOLID", "color": rgb(BORDER)}
        return {"updateBorders": {"range": rng, "top": line, "bottom": line, "left": line,
                                  "right": line, "innerHorizontal": line, "innerVertical": line}}
    else:
        raise ValueError(kind)
    return {"repeatCell": {"range": rng, "cell": {"userEnteredFormat": f},
                           "fields": ",".join(fields)}}


def tab_requests(t):
    grid = t.grid()
    maxr, maxc = len(grid), len(grid[0])
    reqs = [{"repeatCell": {
        "range": {"sheetId": t.sid, "startRowIndex": 0, "endRowIndex": maxr + LIST_ROWS,
                  "startColumnIndex": 0, "endColumnIndex": max(maxc, len(t.widths))},
        "cell": {"userEnteredFormat": {"verticalAlignment": "TOP",
                                       "textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
        "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat.fontFamily,"
                  "userEnteredFormat.textFormat.fontSize"}}]
    order = ["label", "input", "formula", "guide", "guide_nowrap", "header", "section", "title",
             "subtitle", "bold", "date", "integer", "decimal", "decimal2", "currency", "table"]
    for kind in order:
        for k, r1, c1, r2, c2 in t.marks:
            if k == kind:
                reqs.append(fmt_request(t.sid, k, r1, c1, r2, c2))
    for r1, c1, r2, c2, opts in t.validations:
        reqs.append({"setDataValidation": {
            "range": {"sheetId": t.sid, "startRowIndex": r1 - 1, "endRowIndex": r2,
                      "startColumnIndex": c1 - 1, "endColumnIndex": c2},
            "rule": {"condition": {"type": "ONE_OF_LIST",
                                   "values": [{"userEnteredValue": o} for o in opts]},
                     "showCustomUi": True, "strict": False}}})
    for r1, c1, r2, c2 in t.status_ranges:
        rng = {"sheetId": t.sid, "startRowIndex": r1 - 1, "endRowIndex": r2,
               "startColumnIndex": c1 - 1, "endColumnIndex": c2}
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [rng], "booleanRule": {
                "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "OK"}]},
                "format": {"backgroundColor": rgb("#E6F4EA"),
                           "textFormat": {"foregroundColor": rgb("#137333"), "bold": True}}}}}})
        reqs.append({"addConditionalFormatRule": {"index": 1, "rule": {
            "ranges": [rng], "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA",
                              "values": [{"userEnteredValue": f'=AND(LEN(${col(c1)}{r1})>0,${col(c1)}{r1}<>"OK")'}]},
                "format": {"backgroundColor": rgb("#FCE8E6"),
                           "textFormat": {"foregroundColor": rgb("#A50E0E")}}}}}})
    for i, w in enumerate(t.widths):
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": t.sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": t.sid, "gridProperties": {"frozenRowCount": t.freeze}},
        "fields": "gridProperties.frozenRowCount"}})
    return reqs


# --------------------------------------------------------------------------

def gws(*args):
    out = subprocess.run(["gws", *args], capture_output=True, text=True)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        sys.exit(f"gws {' '.join(args[:3])} failed:\n{out.stdout}\n{out.stderr}")
    if isinstance(data, dict) and "error" in data:
        sys.exit(f"gws {' '.join(args[:3])} error:\n{json.dumps(data['error'], indent=2)}")
    return data


def build():
    body_tabs = [tab_engagement(), tab_source(), tab_users(), tab_volumes(), tab_identity(),
                 tab_mail(), tab_scope(), tab_decisions(), tab_risks(), tab_effort(),
                 tab_readiness()]
    tabs = [tab_start(body_tabs)] + body_tabs
    for t in tabs:
        for k, v in list(t.cells.items()):
            t.cells[k] = resolve(v, t) if v is not None else ""
    return tabs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--title", default=TITLE)
    ap.add_argument("--spreadsheet-id",
                    help="Rewrite and format an existing copy instead of creating a new one.")
    ap.add_argument("--values-only", action="store_true",
                    help="With --spreadsheet-id: rewrite contents and formulas only. Formatting "
                         "is not re-sent, so conditional format rules are not duplicated.")
    args = ap.parse_args()

    tabs = build()
    if args.dry_run:
        for t in tabs:
            g = t.grid()
            print(f"{t.sid:>2} {t.title:<24} {len(g)} rows x {len(g[0])} cols, "
                  f"{sum(1 for v in t.cells.values() if isinstance(v, str) and v.startswith('='))} formulas")
        return 0

    if args.spreadsheet_id:
        created = {"spreadsheetId": args.spreadsheet_id,
                   "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit"}
    else:
        created = gws("sheets", "spreadsheets", "create", "--json", json.dumps({
            "properties": {"title": args.title, "locale": "en_US"},
            "sheets": [{"properties": {"sheetId": t.sid, "title": t.title, "index": i,
                                       "gridProperties": {"rowCount": max(200, len(t.grid()) + 50),
                                                          "columnCount": max(12, len(t.widths))}}}
                       for i, t in enumerate(tabs)]}))
    sid = created["spreadsheetId"]

    data = [{"range": "'" + t.title.replace("'", "''") + "'!A1", "values": t.grid()} for t in tabs]
    gws("sheets", "spreadsheets", "values", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": sid}),
        "--json", json.dumps({"valueInputOption": "USER_ENTERED", "data": data}))

    if args.values_only:
        print(json.dumps({"spreadsheetId": sid, "values_rewritten": len(data)}))
        return 0

    # One command-line argument is capped at 128 KB, so send the formatting in
    # batches. Each batch is atomic; batches run in order.
    reqs = [r for t in tabs for r in tab_requests(t)]
    batch, size = [], 0
    for req in reqs + [None]:
        n = len(json.dumps(req)) if req else 0
        if req is None or (batch and size + n > 90_000):
            gws("sheets", "spreadsheets", "batchUpdate",
                "--params", json.dumps({"spreadsheetId": sid}),
                "--json", json.dumps({"requests": batch}))
            batch, size = [], 0
        if req:
            batch.append(req)
            size += n

    print(json.dumps({"spreadsheetId": sid, "url": created.get("spreadsheetUrl"),
                      "tabs": [t.title for t in tabs], "requests": len(reqs)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

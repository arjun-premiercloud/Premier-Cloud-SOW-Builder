"""Shared helpers for the Premier Cloud SOW builder.

Loads the clause library, merges it with a deal-specific intake file, and
produces the flat context the Jinja templates render against.

The only two things a caller needs from here:
    load_intake(path)      -> dict
    build_context(intake)  -> dict ready for template.render(**ctx)
"""

from __future__ import annotations

import json
import os
import re
from datetime import date

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUSES_PATH = os.path.join(ROOT, "library", "clauses.yaml")
SCHEMA_PATH = os.path.join(ROOT, "schemas", "sow-intake.schema.json")

SOW_TYPES = (
    "gemini_enterprise_implementation",
    "agent_pilot",
    "workspace_migration",
)

# Section keys in document order, per SOW type. Optional sections are filtered
# out in section_plan() when the intake does not populate them.
SECTION_ORDER = {
    "gemini_enterprise_implementation": [
        ("contacts", "SOW Point of Contacts"),
        ("term", "Term"),
        ("background", "Project Background and Objective"),
        ("scope", "Scope"),
        ("services", "Description of Services"),
        ("activation", "Activation Plan"),
        ("timeline", "Estimated Timeline"),
        ("governance", "Project Governance & Communication Plan (Sample)"),
        ("deliverables", "Deliverables"),
        ("roles", "Roles & Responsibilities"),
        ("raid", "Risks, Assumptions, Dependencies, and Prerequisites"),
        ("success", "Success Criteria"),
        ("closure", "Project Closure"),
        ("compensation", "Compensation, Invoicing and Payment Schedule"),
    ],
    "agent_pilot": [
        ("contacts", "SOW Point of Contacts"),
        ("term", "Term"),
        ("background", "Project Background and Objective"),
        ("usecases", "Pilot Use Cases"),
        ("services", "Description of Services"),
        ("timeline", "Estimated Timeline"),
        ("governance", "Project Governance & Communication Plan (Sample)"),
        ("deliverables", "Deliverables"),
        ("roles", "Roles & Responsibilities"),
        ("raid", "Risks, Assumptions, Dependencies, and Prerequisites"),
        ("success", "Success Criteria"),
        ("closure", "Project Closure"),
        ("compensation", "Compensation, Invoicing, and Payment Schedule"),
    ],
    "workspace_migration": [
        ("summary", "Executive Summary"),
        ("profiles", "Customer & Partner Profiles"),
        ("scope", "Scope of Services"),
        ("success", "Success Criteria"),
        ("activities", "Activities and Deliverables"),
        ("deliverables", "Deliverables"),
        ("timeline", "Timeline"),
        ("investment", "Investment Summary"),
        ("signatures", "Signatures"),
    ],
}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_clauses(path: str = CLAUSES_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_schema(path: str = SCHEMA_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_intake(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        if path.endswith((".yaml", ".yml")):
            return yaml.safe_load(fh)
        return json.load(fh)


def get(obj, dotted, default=None):
    """Safe nested lookup: get(intake, 'platform.seats')."""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return default
        cur = cur[part]
    return cur


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------

def money(amount, currency: str = "USD") -> str:
    """45000 -> '$45,000 USD'.  -37000 -> '($37,000) USD' (accounting credit)."""
    if amount is None:
        return ""
    neg = amount < 0
    figure = f"${abs(amount):,.0f}"
    if neg:
        figure = f"({figure})"
    return f"{figure} {currency}".rstrip()


def interpolate(value, placeholders: dict):
    """Render {{token}} placeholders inside the clause library, recursively."""
    if isinstance(value, str):
        if "{{" not in value:
            return value
        out = value
        for key, val in placeholders.items():
            out = out.replace("{{" + key + "}}", "" if val is None else str(val))
        return out
    if isinstance(value, list):
        return [interpolate(v, placeholders) for v in value]
    if isinstance(value, dict):
        return {k: interpolate(v, placeholders) for k, v in value.items()}
    return value


def _bullet_text(b) -> str:
    if isinstance(b, str):
        return b
    label, text = b.get("label"), (b.get("text") or "").strip()
    if label and text:
        return f"**{label}:** {text}"
    if label:
        return f"**{label}**"
    return text


def render_bullets(items, level: int = 0) -> str:
    """Nested markdown bullet list from strings or {label,text,children} dicts."""
    if not items:
        return ""
    lines = []
    for b in items:
        lines.append(f"{'  ' * level}- {_bullet_text(b)}")
        kids = b.get("children") if isinstance(b, dict) else None
        if kids:
            lines.append(render_bullets(kids, level + 1))
    return "\n".join(x for x in lines if x)


def render_table(headers, rows) -> str:
    """Markdown table. `rows` is a list of lists; cells are stringified."""
    head = "| " + " | ".join(str(h) for h in headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join("" if c is None else str(c) for c in row) + " |"
        for row in rows
    ]
    return "\n".join([head, rule, *body])


def data_source_names(sources) -> list:
    out = []
    for s in sources or []:
        if isinstance(s, str):
            out.append(s)
        else:
            out.append(f"{s['name']} (Federated)" if s.get("federated") else s["name"])
    return out


def spell(n: int) -> str:
    """3 -> 'three (3)'. Matches the house convention for counts in prose."""
    words = {
        1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
        7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    }
    return f"{words[n]} ({n})" if n in words else str(n)


# --------------------------------------------------------------------------
# merge
# --------------------------------------------------------------------------

def deep_merge(base, override):
    """override wins; dicts merge recursively, lists and scalars replace."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if override is not None else base
    out = dict(base)
    for k, v in override.items():
        if v is None:
            continue
        out[k] = deep_merge(base.get(k), v) if isinstance(v, dict) else v
    return out


def section_plan(sow_type: str, intake: dict):
    """Ordered [(key, title, number)] with optional sections dropped."""
    plan, n = [], 0
    for key, title in SECTION_ORDER[sow_type]:
        if key == "activation" and not get(intake, "platform.activation_plan"):
            continue
        if key == "usecases" and not intake.get("use_cases"):
            continue
        n += 1
        plan.append({"key": key, "title": title, "n": n})
    return plan


def build_pricing(intake: dict, clauses: dict) -> dict:  # noqa: ARG001
    p = intake.get("pricing", {}) or {}
    cur = p.get("currency", "USD")
    total = p.get("total_fixed_price") or 0
    funding = p.get("google_funding")
    investment = p.get("partner_investment")

    lines = []
    if p.get("line_items"):
        for li in p["line_items"]:
            lines.append({"label": li["label"], "amount": li["amount"], "bold": li.get("bold", False)})
    elif any((uc.get("price") or 0) for uc in intake.get("use_cases") or []):
        # Per-agent pricing: each priced use case is its own line, and whatever
        # is left of the fixed price becomes the shared platform/PM line.
        priced = 0
        for uc in intake["use_cases"]:
            if uc.get("price"):
                lines.append({"label": uc["name"], "amount": uc["price"], "bold": False})
                priced += uc["price"]
        if total - priced > 0:
            lines.append({
                "label": "Common - platform, project management, and enablement",
                "amount": total - priced,
                "bold": False,
            })
    else:
        lines.append({"label": "Total fixed price for Professional Services", "amount": total, "bold": False})

    if funding:
        lines.append({
            "label": "Google funding (at project completion)",
            "amount": -abs(funding),
            "bold": False,
        })
    if investment:
        lines.append({"label": "Partner investment", "amount": -abs(investment), "bold": False})

    net = total - abs(funding or 0) - abs(investment or 0)
    lines.append({"label": "Net cost to customer", "amount": net, "bold": True})

    rows = []
    for li in lines:
        label = f"**{li['label']}**" if li["bold"] else li["label"]
        val = money(li["amount"], cur)
        if li["bold"]:
            val = f"**{val}**"
        rows.append([label, val])

    # Which funding narrative applies.
    if net <= 0 and funding and investment:
        note_key = "partner_and_google_funded_note"
    elif net <= 0 and funding and p.get("funding_stage"):
        note_key = "funding_disclosure"
    elif net <= 0 and funding:
        note_key = "fully_funded_note"
    else:
        note_key = None

    return {
        "currency": cur,
        "total": total,
        "total_str": money(total, cur),
        "funding": funding,
        "funding_str": money(funding, cur) if funding else "",
        "net": net,
        "net_str": money(net, cur),
        "rows": rows,
        "note_key": note_key,
        "note": None,  # resolved in build_context, after clause interpolation
        "clawback": p.get("funding_clawback", False),
        "data_sharing": p.get("google_data_sharing_consent", False),
        "payment_terms": p.get("payment_terms"),
    }


def build_out_of_scope(intake: dict, clauses: dict, sow_type: str) -> list:
    items = list(clauses["out_of_scope"].get(sow_type, []))
    cond = clauses["conditional_out_of_scope"]

    if sow_type in ("gemini_enterprise_implementation", "agent_pilot"):
        if not get(intake, "platform.agentic_workflows"):
            items.append(cond["no_agentic_workflows"])
        if get(intake, "platform.workforce_identity_federation") == "customer_to_configure":
            items.append(cond["wif_customer_managed"])
        if get(intake, "platform.identity_provider", "Google Identity"):
            items.append(cond["single_idp"])

    items += intake.get("scope", {}).get("out_of_scope_extra", []) or []

    suppress = [s.lower() for s in (intake.get("scope", {}).get("out_of_scope_suppress") or [])]
    if suppress:
        items = [i for i in items if not any(s in i.lower() for s in suppress)]
    return items


def build_assumptions(intake: dict, clauses: dict, sow_type: str) -> list:
    base = list(clauses["assumptions"].get(sow_type, []))
    wif = get(intake, "platform.workforce_identity_federation", "not_required")
    variant = clauses["wif_assumption"].get(wif)
    if variant:
        base = [variant if a.startswith("A single identity provider") else a for a in base]
    return base + (intake.get("assumptions") or [])


def build_context(intake: dict, clauses: dict | None = None) -> dict:
    clauses = clauses or load_clauses()
    sow_type = intake["sow_type"]
    if sow_type not in SOW_TYPES:
        raise ValueError(f"unknown sow_type {sow_type!r}; expected one of {SOW_TYPES}")

    partner = deep_merge(clauses["partner"], intake.get("partner") or {})
    customer = intake.get("customer", {})
    customer.setdefault("signatory", customer.get("contact", {}))
    pricing = build_pricing(intake, clauses)

    placeholders = {
        "customer_name": customer.get("short_name") or customer.get("legal_name", ""),
        "customer_legal_name": customer.get("legal_name", ""),
        "partner_name": partner.get("legal_name", "Premier Cloud Inc."),
        "execution_date": get(intake, "agreement.execution_date", ""),
        "msa_url": get(intake, "agreement.msa_url",
                       "https://premiercloud.com/wp-content/uploads/2024/06/MASTER-SERVICES-AGREEMENT-PREMIER-CLOUD-INC.pdf"),
        "msa_date": get(intake, "agreement.msa_date", ""),
        "effective_date": get(intake, "term.effective_date", ""),
        "end_date": get(intake, "term.end_date", ""),
        "identity_provider": get(intake, "platform.identity_provider", "Google Identity"),
        "seats": get(intake, "platform.seats", ""),
        "environment": get(intake, "platform.environment", "non-production"),
        "total": pricing["total_str"],
        "funding": pricing["funding_str"],
        "funding_stage": get(intake, "pricing.funding_stage", ""),
        "funding_program": get(intake, "pricing.funding_program", "PSF"),
        "target_activation_percent": get(intake, "platform.activation_plan.target_activation_percent", 50),
    }
    cl = interpolate(clauses, placeholders)
    # The funding note carries {{funding_stage}} etc., so it can only be
    # resolved once the clause library has been interpolated.
    if pricing["note_key"]:
        pricing["note"] = cl["compensation"][pricing["note_key"]]

    # --- scope -----------------------------------------------------------
    summary_blocks = get(intake, "scope.summary_blocks") or cl["summary_blocks"].get(sow_type, [])
    summary_blocks = _expand_children_from(summary_blocks, intake)
    if get(intake, "platform.cloud_foundations"):
        summary_blocks = _inject_cloud_foundations(summary_blocks, cl["cloud_foundations_block"])

    service_sections = get(intake, "scope.service_sections") or cl["service_sections"].get(sow_type, [])
    service_sections = _expand_children_from(service_sections, intake)

    agents = get(intake, "platform.agentic_workflows")
    if agents:
        summary_blocks = _inject_agentic(summary_blocks, agents, cl, "summary",
                                         after="Development & Testing")
        service_sections = _inject_agentic(service_sections, agents, cl, "services",
                                           after="Gemini Enterprise Deployment and Datasource Connectors Set Up")

    milestones = get(intake, "timeline.milestones") or cl.get("milestones", {}).get(sow_type, [])
    weeks = get(intake, "timeline.weeks") or get(intake, "term.duration_weeks") or (
        max((m.get("week", 1) for m in milestones), default=5)
    )

    deliverables = intake.get("deliverables") or cl.get("deliverables", {}).get(sow_type, [])
    deliverables = [
        {"name": d.get("name") or f"Deliverable {i}", "detail": d["detail"], "timeline": d.get("timeline", "")}
        for i, d in enumerate(deliverables, start=1)
    ]

    ctx = {
        "today": date.today().isoformat(),
        "sow_type": sow_type,
        "intake": intake,
        "clauses": cl,
        "doc": intake.get("document", {}),
        "customer": customer,
        "partner": partner,
        "agreement": intake.get("agreement", {}),
        "term": intake.get("term", {}),
        "background": intake.get("background", {}) or {},
        "platform": intake.get("platform", {}) or {},
        "migration": intake.get("migration", {}) or {},
        "use_cases": intake.get("use_cases") or [],
        "scope_statement": get(intake, "scope.statement") or cl.get("scope_statement", {}).get(sow_type, ""),
        "summary_blocks": summary_blocks,
        "service_sections": service_sections,
        "out_of_scope": build_out_of_scope(intake, cl, sow_type),
        "milestones": milestones,
        "weeks": weeks,
        "schedule": get(intake, "timeline.schedule") or [],
        "timeline_note": get(intake, "timeline.note", "The following timeline is for illustrative purposes only:"),
        "deliverables": deliverables,
        "resources": intake.get("resources") or [],
        "governance": deep_merge(cl["governance"], intake.get("governance") or {}),
        "risks": cl["risks"]["standard"] + (intake.get("risks") or []),
        "assumptions": build_assumptions(intake, cl, sow_type),
        "prereq_before": (intake.get("prerequisites_before")
                          or cl["prerequisites_before"].get(sow_type, [])),
        "prereq_ongoing": (intake.get("prerequisites_ongoing")
                           or cl["prerequisites_ongoing"].get(sow_type, [])),
        "success_criteria": (intake.get("success_criteria")
                             or cl["success_criteria"].get(sow_type, [])),
        "partner_roles": get(intake, "partner.team") or cl["roles"]["partner"].get(sow_type, []),
        "customer_roles": customer.get("stakeholders") or cl["roles"]["customer"].get(sow_type, []),
        "pricing": pricing,
        "appendices": intake.get("appendices") or [],
        "data_sources": data_source_names(get(intake, "platform.data_sources")),
        "sections": {s["key"]: s for s in section_plan(sow_type, intake)},
        "section_list": section_plan(sow_type, intake),
        # helpers exposed to templates
        "bullets": render_bullets,
        "table": render_table,
        "rows": lambda items, keys: [[i.get(k, "") for k in keys] for i in (items or [])],
        "money": lambda a: money(a, pricing["currency"]),
        "spell": spell,
        "alpha": lambda i: chr(65 + i),
        "role_rows": role_rows,
    }
    ctx["challenges"] = _normalise_challenges(ctx["background"].get("business_challenges"))
    ctx["gantt"] = build_gantt(milestones, weeks)
    ctx["track_schedules"] = _group_by_track(ctx["schedule"])
    for uc in ctx["use_cases"]:
        uc["_listline"] = {"label": uc["name"], "text": uc.get("summary", "")}
    return ctx


def _group_by_track(schedule):
    """[(track_name, rows)] preserving first-seen order; empty when untracked."""
    if not any(row.get("track") for row in schedule or []):
        return []
    grouped = {}
    for row in schedule:
        grouped.setdefault(row.get("track") or "Schedule", []).append(row)
    return list(grouped.items())


def build_gantt(milestones, weeks: int) -> dict:
    """Milestone-per-row Gantt: the milestone id sits in its week's column."""
    weeks = max(int(weeks or 1), 1)
    headers = ["**Task**"] + [f"**W{i}**" for i in range(1, weeks + 1)]
    rows = []
    for m in milestones:
        week = min(int(m.get("week") or 1), weeks)
        cells = ["" for _ in range(weeks)]
        cells[week - 1] = f"**{m.get('id', '')}**"
        rows.append([m.get("task") or m.get("name", ""), *cells])
    return {"headers": headers, "rows": rows}


def role_rows(items):
    """[role, description] rows; a named person is appended in parentheses."""
    out = []
    for r in items or []:
        desc = r.get("description", "")
        who = ", ".join(x for x in [r.get("name"), r.get("title")] if x)
        if who and who not in desc:
            desc = f"{desc} ({who})".strip()
        out.append([r.get("role", ""), desc])
    return out


def _normalise_challenges(items):
    """business_challenges accepts plain strings or {label, summary} objects."""
    out = []
    for c in items or []:
        if isinstance(c, str):
            out.append(c)
        else:
            out.append({"label": c.get("label"), "text": c.get("summary", "")})
    return out


def _expand_children_from(blocks, intake):
    """Resolve `children_from: data_sources` into real child bullets."""
    names = data_source_names(get(intake, "platform.data_sources"))
    out = []
    for block in blocks:
        block = dict(block)
        if block.get("bullets"):
            block["bullets"] = [_expand_bullet(b, names) for b in block["bullets"]]
        if block.get("groups"):
            block["groups"] = [
                {**g, "bullets": [_expand_bullet(b, names) for b in g.get("bullets", [])]}
                for g in block["groups"]
            ]
        out.append(block)
    return out


def _expand_bullet(b, names):
    if isinstance(b, str):
        return b
    b = dict(b)
    if b.pop("children_from", None) == "data_sources":
        b["children"] = list(names)
    if b.get("children"):
        b["children"] = [_expand_bullet(c, names) for c in b["children"]]
    return b


def _inject_agentic(blocks, agents, clauses, mode: str, after: str):
    """Build the Agentic Workflow block from the declared agents and slot it in."""
    spec = clauses["agentic_workflow_section"]
    lead_tpl = spec["summary_lead"] if mode == "summary" else spec["services_lead"]

    bullets = []
    for a in agents:
        lead = lead_tpl.replace("{{name}}", a["name"]).replace("{{description}}", a["description"])
        if mode == "summary":
            bullets.append(lead)
        else:
            bullets.append({"text": lead, "children": list(spec["build_bullets"])})

    block = {"heading": spec["heading"], "bullets": bullets}

    out, placed = [], False
    for b in blocks:
        out.append(b)
        if b.get("heading") == after:
            out.append(block)
            placed = True
    if not placed:
        out.append(block)
    return out


def _inject_cloud_foundations(blocks, cf_block):
    out = []
    for block in blocks:
        out.append(block)
        if block.get("heading") == "Solution Design":
            out.append(cf_block)
    return out


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "sow").lower()).strip("-")

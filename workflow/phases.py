#!/usr/bin/env python3
"""
phases.py — the phase plan.

A data-driven description of the engagement workflow. Each phase declares what
it needs, what to do, what it EMITS (findings/outputs), when it's done, and the
RETURN edges that loop you back to an earlier phase when reality demands it.

This is the "plan for each phase" the CLI renders. It is deliberately just data
plus a formatter — no control flow, no agents. You execute the actions; the
toolkit tracks scope, findings, and which phase you're in.
"""
from __future__ import annotations

# Ordered. `returns_to` lists backward edges: (phase_key, trigger condition).
PHASES = [
    {
        "key": "scope",
        "name": "Scope",
        "purpose": "Lock what you are authorized to touch. The one hard safety gate.",
        "inputs": ["Program scope / SOW", "In-scope + out-of-scope assets", "Seed URLs"],
        "actions": [
            "Record in-scope patterns (apex, *.wildcard, exact host, CIDR, re:regex).",
            "Record explicit out-of-scope exclusions (deny-wins over in-scope).",
            "Add seed URLs to start recon from.",
            "Sanity-check with `scope check <host>` on a few known in/out hosts.",
        ],
        "emits": "A locked scope (in_scope / out_of_scope / seeds) stored on the engagement.",
        "exit_criteria": "Scope matches the program exactly; spot-checks pass.",
        "returns_to": [],
    },
    {
        "key": "recon",
        "name": "Recon",
        "purpose": "Map the attack surface across the in-scope assets.",
        "inputs": ["Locked scope", "Seed URLs"],
        "actions": [
            "Enumerate subdomains/assets (subfinder, amass, crt.sh) — keep only in-scope.",
            "Probe liveness + fingerprint tech/stack (httpx).",
            "Mine endpoints and parameters (gau passive history + katana live crawl).",
            "Scan JS bundles for endpoints and leaked secrets (redact before storing).",
            "Record each live host/endpoint/param as a target on the engagement.",
        ],
        "emits": "Targets: live in-scope hosts + endpoints + parameters + tech fingerprint.",
        "exit_criteria": "Surface enumerated for every in-scope seed; params collected.",
        "returns_to": [
            ("scope", "a discovered asset is interesting but not covered by scope — confirm authorization, then widen scope"),
        ],
    },
    {
        "key": "map",
        "name": "Map",
        "purpose": "Route the surface to attack classes + the right skill, and rank it.",
        "inputs": ["Targets from recon", "Installed skills arsenal"],
        "actions": [
            "For each (endpoint, param), list the candidate vuln classes.",
            "Map each class to the skill to open (e.g. redirect_to -> ssrf/lfi/open-redirect).",
            "Rank items by impact (rce/sqli/auth high; clickjacking/cors low) x signal.",
            "Write the worklist: ordered (url, param, class, skill, starter-probe).",
        ],
        "emits": "A ranked worklist telling you where to look first and which skill to use.",
        "exit_criteria": "Every target item is routed to a class + skill and ranked.",
        "returns_to": [
            ("recon", "mapping reveals surface gaps (uncrawled area, missing params)"),
        ],
    },
    {
        "key": "hunt",
        "name": "Hunt",
        "purpose": "Manually test the ranked worklist using the mapped skills.",
        "inputs": ["Ranked worklist", "Scope (checked per request)"],
        "actions": [
            "Take worklist items in rank order; open the mapped skill for methodology.",
            "Test in-scope, prefer the least-impactful proof; stay read-only unless authorized.",
            "For anything promising, record a CANDIDATE finding with the request + evidence.",
            "Never send a request to an out-of-scope host, even to 'prove' a finding.",
        ],
        "emits": "Candidate findings (status=candidate) with request, evidence, severity guess.",
        "exit_criteria": "Worklist worked to your time budget; candidates recorded.",
        "returns_to": [
            ("map", "hunting surfaces new endpoints/params to route"),
            ("recon", "a finding exposes a whole new asset/surface to enumerate"),
        ],
    },
    {
        "key": "triage",
        "name": "Triage / Validate",
        "purpose": "Verify candidates, dedup, calibrate severity, audit scope.",
        "inputs": ["Candidate findings"],
        "actions": [
            "Reproduce each candidate; demote non-reproducible to invalid.",
            "Deduplicate against already-confirmed findings.",
            "Calibrate severity (program VRT / CVSS), not the hunt's raw guess.",
            "Run scope-audit: flag any PoC that touched an out-of-scope host.",
            "Promote survivors to CONFIRMED.",
        ],
        "emits": "Confirmed findings (status=confirmed) with calibrated severity + scope flags.",
        "exit_criteria": "Every candidate is confirmed, invalid, or duplicate.",
        "returns_to": [
            ("hunt", "a candidate needs stronger/safer proof before it stands"),
        ],
    },
    {
        "key": "report",
        "name": "Report",
        "purpose": "Write up confirmed findings for submission.",
        "inputs": ["Confirmed findings"],
        "actions": [
            "For each confirmed finding: title, severity, impact, steps to reproduce, PoC, remediation.",
            "Attach redacted evidence; make steps copy-paste reproducible.",
            "Flag any finding whose PoC touched an out-of-scope host for manual review.",
            "Render report.md and submit per program rules.",
        ],
        "emits": "report.md — the submission-ready write-up.",
        "exit_criteria": "All confirmed findings written up and reviewed.",
        "returns_to": [
            ("triage", "a write-up reveals a gap in validation"),
        ],
    },
]

PHASE_KEYS = [p["key"] for p in PHASES]
_BY_KEY = {p["key"]: p for p in PHASES}


def get(key: str) -> dict | None:
    return _BY_KEY.get(key)


def next_key(key: str) -> str | None:
    i = PHASE_KEYS.index(key)
    return PHASE_KEYS[i + 1] if i + 1 < len(PHASE_KEYS) else None


def render(phase: dict, width: int = 78) -> str:
    bar = "=" * width
    out = [bar, f"PHASE: {phase['name']}  ({phase['key']})", bar,
           phase["purpose"], ""]
    out.append("Inputs:")
    out += [f"  - {x}" for x in phase["inputs"]]
    out.append("")
    out.append("Actions:")
    out += [f"  [ ] {x}" for x in phase["actions"]]
    out.append("")
    out.append(f"Emits:  {phase['emits']}")
    out.append(f"Done when:  {phase['exit_criteria']}")
    if phase["returns_to"]:
        out.append("")
        out.append("Return to an earlier phase when:")
        for tgt, cond in phase["returns_to"]:
            out.append(f"  -> {tgt}: {cond}")
    nk = next_key(phase["key"])
    out.append("")
    out.append(f"Next phase:  {nk}" if nk else "Next phase:  (none — final)")
    return "\n".join(out)


def render_all() -> str:
    return "\n\n".join(render(p) for p in PHASES)

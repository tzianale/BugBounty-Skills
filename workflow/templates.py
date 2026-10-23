#!/usr/bin/env python3
"""
templates.py — render a single finding into a submission-ready write-up.

Loads the editable master template (templates/submission.md) and per-class
defaults (templates/classes.json), substitutes the finding's data, and fills any
gap with a visible fill-in stub so you never submit a blank section by accident.

Platform only changes the severity line convention (HackerOne=CVSS,
Bugcrowd=VRT, etc.). The templates themselves are yours to edit.
"""
from __future__ import annotations

import json
import os

TPL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_SEV_LINE = {
    "hackerone": "**Severity:** {sev}  _(set the CVSS vector in the HackerOne form)_",
    "bugcrowd": "**Priority (VRT):** {sev}  _(map to Bugcrowd VRT on submission)_",
    "intigriti": "**Severity:** {sev}  _(set CVSS on the Intigriti form)_",
    "generic": "**Severity:** {sev}",
}

STUB = {
    "summary": "_(one or two sentences: what the bug is and where)_",
    "poc": "_(numbered, copy-pasteable steps / requests to reproduce)_",
    "evidence": "_(request/response excerpts, screenshots, or collaborator interaction — redact secrets)_",
    "impact": "_(what an attacker gains; tie it to the program's business)_",
    "remediation": "_(concrete fix guidance)_",
    "references": "_(links: OWASP cheat sheet, CWE, related advisories)_",
}


def _load_classes():
    path = os.path.join(TPL_DIR, "classes.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _master(template: str | None) -> str:
    # template may be None (use submission.md), a class name (classes/<name>.md
    # if present, else submission.md), or a path to a custom .md file.
    if template and os.path.isfile(template):
        with open(template, encoding="utf-8") as fh:
            return fh.read()
    if template:
        cand = os.path.join(TPL_DIR, "classes", f"{template}.md")
        if os.path.isfile(cand):
            with open(cand, encoding="utf-8") as fh:
                return fh.read()
    with open(os.path.join(TPL_DIR, "submission.md"), encoding="utf-8") as fh:
        return fh.read()


def render(finding: dict, engagement: str, platform: str = "generic",
           template: str | None = None, date: str = "") -> str:
    classes = _load_classes()
    cls = finding.get("vuln_class", "")
    cdef = classes.get(cls, {}) if isinstance(classes.get(cls), dict) else {}

    refs = cdef.get("references")
    refs_md = "\n".join(f"- {r}" for r in refs) if refs else STUB["references"]
    cwe = cdef.get("cwe", "")

    sev = finding.get("severity", "info")
    sev_line = _SEV_LINE.get(platform, _SEV_LINE["generic"]).format(sev=sev)

    warn = finding.get("scope_warning")
    scope_note = (f"\n> ⚠ SCOPE: this finding's PoC referenced out-of-scope host(s): "
                  f"{', '.join(warn)}. Review before submitting." if warn else "")

    sub = {
        "{{title}}": finding.get("title") or (cls + " finding"),
        "{{target}}": finding.get("target", "") or "_(target URL)_",
        "{{param_line}}": f"\n**Parameter:** `{finding['param']}`" if finding.get("param") else "",
        "{{vuln_class}}": cls or "_(class)_",
        "{{cwe_line}}": f"  ·  {cwe}" if cwe else "",
        "{{severity_line}}": sev_line,
        "{{summary}}": finding.get("notes") or STUB["summary"],
        "{{poc}}": finding.get("poc") or STUB["poc"],
        "{{evidence}}": finding.get("evidence") or STUB["evidence"],
        "{{impact}}": cdef.get("impact") or STUB["impact"],
        "{{remediation}}": cdef.get("remediation") or STUB["remediation"],
        "{{references}}": refs_md,
        "{{engagement}}": engagement,
        "{{id}}": finding.get("id", ""),
        "{{date}}": date,
        "{{skills}}": ", ".join(finding.get("skills_used") or []) or "—",
        "{{scope_note}}": scope_note,
    }
    out = _master(template)
    for k, v in sub.items():
        out = out.replace(k, v)
    return out

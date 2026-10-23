#!/usr/bin/env python3
"""
state.py — persistent, resumable engagement store.

One engagement = one directory under the base dir (default ~/.bb-engagements/).
Everything is plain JSON + rendered markdown so a run is auditable, diffable,
and resumable. Live findings on real targets live HERE, outside the git repo,
and are never committed.

Layout:
  <base>/<name>/
    state.json     canonical state (scope, phase, targets, findings, log)
    findings.md    rendered findings (regenerated on change)
    report.md      rendered on `report`
    engagement.log append-only activity log
"""
from __future__ import annotations

import json
import os
import time

from scope import Scope

SEVERITIES = ["info", "low", "medium", "high", "critical"]
STATUSES = ["candidate", "confirmed", "duplicate", "invalid", "reported"]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Engagement:
    def __init__(self, base: str, name: str):
        self.base = os.path.expanduser(base)
        self.name = name
        self.dir = os.path.join(self.base, name)
        self.state_path = os.path.join(self.dir, "state.json")
        if os.path.isfile(self.state_path):
            with open(self.state_path, encoding="utf-8") as fh:
                self.state = json.load(fh)
        else:
            self.state = {
                "name": name, "created": _now(), "phase": "scope",
                "scope": {"name": name, "in_scope": [], "out_of_scope": [], "seeds": []},
                "targets": [], "findings": [], "next_id": 1, "log": [],
            }
            os.makedirs(self.dir, exist_ok=True)
            self.save()

    # ---- persistence ----
    def save(self):
        os.makedirs(self.dir, exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2)
        os.replace(tmp, self.state_path)
        self._render_findings()

    def log(self, msg: str):
        line = f"{_now()}  {msg}"
        self.state.setdefault("log", []).append(line)
        with open(os.path.join(self.dir, "engagement.log"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ---- scope ----
    @property
    def scope(self) -> Scope:
        return Scope.from_dict(self.state.get("scope"))

    def set_scope(self, scope: Scope):
        self.state["scope"] = scope.to_dict()
        self.save()

    # ---- phase ----
    def set_phase(self, phase: str):
        self.state["phase"] = phase
        self.save()
        self.log(f"phase -> {phase}")

    # ---- findings ----
    def add_finding(self, data: dict) -> str:
        fid = f"F{self.state['next_id']:03d}"
        self.state["next_id"] += 1
        rec = {
            "id": fid,
            "title": data.get("title", ""),
            "vuln_class": data.get("vuln_class", ""),
            "severity": data.get("severity", "info"),
            "status": data.get("status", "candidate"),
            "target": data.get("target", ""),
            "param": data.get("param", ""),
            "phase_found": self.state.get("phase", ""),
            "evidence": data.get("evidence", ""),
            "poc": data.get("poc", ""),
            "skills_used": data.get("skills_used", []),
            "scope_warning": data.get("scope_warning"),
            "notes": data.get("notes", ""),
            "created": _now(), "updated": _now(),
        }
        self.state.setdefault("findings", []).append(rec)
        self.save()
        self.log(f"finding + {fid} [{rec['status']}] {rec['severity']} {rec['vuln_class']} @ {rec['target']}")
        return fid

    def get_finding(self, fid: str):
        for f in self.state.get("findings", []):
            if f["id"] == fid:
                return f
        return None

    def update_finding(self, fid: str, **kw) -> bool:
        f = self.get_finding(fid)
        if not f:
            return False
        for k, v in kw.items():
            if v is not None and k in f:
                f[k] = v
        f["updated"] = _now()
        self.save()
        self.log(f"finding ~ {fid} {', '.join(f'{k}={v}' for k, v in kw.items() if v is not None)}")
        return True

    def findings(self, status: str | None = None):
        fs = self.state.get("findings", [])
        return [f for f in fs if status is None or f["status"] == status]

    # ---- rendering ----
    def summary(self) -> dict:
        fs = self.state.get("findings", [])
        by_status = {s: sum(1 for f in fs if f["status"] == s) for s in STATUSES}
        return {"phase": self.state.get("phase"), "targets": len(self.state.get("targets", [])),
                "findings": len(fs), "by_status": by_status}

    def _sev_rank(self, f):
        return SEVERITIES.index(f["severity"]) if f["severity"] in SEVERITIES else 0

    def _render_findings(self):
        fs = sorted(self.state.get("findings", []), key=self._sev_rank, reverse=True)
        lines = [f"# Findings — {self.name}", "", f"_updated {_now()}_", ""]
        if not fs:
            lines.append("No findings yet.")
        for f in fs:
            warn = f"  ⚠ scope: {', '.join(f['scope_warning'])}" if f.get("scope_warning") else ""
            lines += [
                f"## {f['id']} · {f['title'] or f['vuln_class'] or '(untitled)'}",
                f"- **status:** {f['status']}  ·  **severity:** {f['severity']}  ·  **class:** {f['vuln_class']}{warn}",
                f"- **target:** `{f['target']}`" + (f" · **param:** `{f['param']}`" if f['param'] else ""),
            ]
            if f.get("skills_used"):
                lines.append(f"- **skills:** {', '.join(f['skills_used'])}")
            if f.get("evidence"):
                lines += ["- **evidence:**", "  ```", "  " + f["evidence"].replace("\n", "\n  "), "  ```"]
            if f.get("poc"):
                lines += ["- **PoC:**", "  ```", "  " + f["poc"].replace("\n", "\n  "), "  ```"]
            if f.get("notes"):
                lines.append(f"- **notes:** {f['notes']}")
            lines.append("")
        with open(os.path.join(self.dir, "findings.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    def render_report(self) -> str:
        confirmed = [f for f in self.state.get("findings", [])
                     if f["status"] in ("confirmed", "reported")]
        confirmed.sort(key=self._sev_rank, reverse=True)
        lines = [f"# Engagement report — {self.name}", "", f"_generated {_now()}_", "",
                 f"Confirmed findings: **{len(confirmed)}**", ""]
        if not confirmed:
            lines.append("No confirmed findings.")
        for f in confirmed:
            warn = f"  ⚠ PoC touched out-of-scope host(s): {', '.join(f['scope_warning'])}" if f.get("scope_warning") else ""
            lines += [
                f"## {f['id']} · {f['title'] or f['vuln_class']}  [{f['severity'].upper()}]{warn}",
                f"- **Class:** {f['vuln_class']}",
                f"- **Target:** `{f['target']}`" + (f" · **Parameter:** `{f['param']}`" if f['param'] else ""),
                "", "### Steps to reproduce / PoC", "```", f.get("poc", "") or "(add PoC)", "```",
                "", "### Evidence", (f.get("evidence", "") or "(add evidence)"),
            ]
            if f.get("notes"):
                lines += ["", "### Notes", f["notes"]]
            lines.append("")
        report = "\n".join(lines)
        with open(os.path.join(self.dir, "report.md"), "w", encoding="utf-8") as fh:
            fh.write(report)
        return report

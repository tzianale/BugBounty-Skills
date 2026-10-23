#!/usr/bin/env python3
"""
bbwf.py — Bug-Bounty WorkFlow: an operator-driven, phase-based engagement runner.

NOT an autonomous engine. It does three things, deterministically and offline:
  1. holds the engagement's scope (deny-wins, default-deny) and checks hosts against it,
  2. prints the plan for each phase (inputs -> actions -> emits -> return edges),
  3. persists findings across phases and renders findings.md / report.md.

You drive the phases; Claude (or you) does the actual testing. Scope is the
hard safety boundary — consult it before every request.

Engagement data lives under --base (default ~/.bb-engagements/<name>/), OUTSIDE
this repo, so live findings are never committed.

Examples:
  bbwf.py init --name acme --in acme.com --out admin.acme.com --seed https://acme.com
  bbwf.py scope check --name acme https://api.acme.com
  bbwf.py scope add   --name acme --in '*.acme.io'
  bbwf.py plan                       # the whole phase plan
  bbwf.py plan --name acme           # plan for the engagement's current phase
  bbwf.py plan recon                 # plan for one phase
  bbwf.py phase next  --name acme
  bbwf.py finding add --name acme --title "IDOR on /api/account" --class idor \\
                      --sev high --target https://api.acme.com/account?id=5 --status candidate
  bbwf.py status --name acme
  bbwf.py report --name acme
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phases as P            # noqa: E402
from scope import Scope, host_of  # noqa: E402
from state import Engagement, SEVERITIES, STATUSES  # noqa: E402

DEFAULT_BASE = os.environ.get("BBWF_BASE", "~/.bb-engagements")


def _eng(args) -> Engagement:
    if not getattr(args, "name", None):
        sys.exit("error: this command needs --name <engagement>")
    return Engagement(args.base, args.name)


# ---------------- commands ----------------
def cmd_init(args):
    eng = Engagement(args.base, args.name)
    sc = eng.scope
    for v in args.in_scope or []:
        sc.add("in_scope", v)
    for v in args.out_scope or []:
        sc.add("out_of_scope", v)
    for v in args.seed or []:
        sc.add("seeds", v)
    eng.set_scope(sc)
    eng.log(f"init engagement '{args.name}'")
    print(f"✓ engagement '{args.name}' at {eng.dir}")
    _print_scope(sc)
    print("\nNext: review the plan ->  bbwf.py plan --name", args.name)


def _print_scope(sc: Scope):
    print(f"  in-scope     : {sc.in_scope or '(none — default-deny: nothing is in scope yet)'}")
    print(f"  out-of-scope : {sc.out_of_scope or '(none)'}")
    print(f"  seeds        : {sc.seeds or '(none)'}")


def cmd_scope(args):
    eng = _eng(args)
    sc = eng.scope
    if args.scope_cmd == "list":
        _print_scope(sc)
    elif args.scope_cmd == "check":
        ok, reason = sc.check(args.target)
        host = host_of(args.target)
        mark = "IN SCOPE " if ok else "OUT OF SCOPE"
        print(f"[{mark}] {host}  —  {reason}")
        sys.exit(0 if ok else 2)
    elif args.scope_cmd == "add":
        changed = False
        for v in args.in_scope or []:
            changed |= sc.add("in_scope", v)
        for v in args.out_scope or []:
            changed |= sc.add("out_of_scope", v)
        for v in args.seed or []:
            changed |= sc.add("seeds", v)
        eng.set_scope(sc)
        print("✓ updated" if changed else "(no change)")
        _print_scope(sc)
    elif args.scope_cmd == "rm":
        changed = False
        for v in args.in_scope or []:
            changed |= sc.remove("in_scope", v)
        for v in args.out_scope or []:
            changed |= sc.remove("out_of_scope", v)
        for v in args.seed or []:
            changed |= sc.remove("seeds", v)
        eng.set_scope(sc)
        print("✓ updated" if changed else "(no change)")
        _print_scope(sc)


def cmd_plan(args):
    # bbwf.py plan              -> all phases
    # bbwf.py plan <phase>      -> one phase
    # bbwf.py plan --name X     -> current phase of engagement X
    if args.phase:
        ph = P.get(args.phase)
        if not ph:
            sys.exit(f"error: unknown phase '{args.phase}'. Known: {', '.join(P.PHASE_KEYS)}")
        print(P.render(ph))
    elif getattr(args, "name", None):
        eng = Engagement(args.base, args.name)
        cur = eng.state.get("phase", "scope")
        print(f"(engagement '{args.name}' is in phase: {cur})\n")
        print(P.render(P.get(cur)))
    else:
        print(P.render_all())


def cmd_phase(args):
    eng = _eng(args)
    cur = eng.state.get("phase", "scope")
    if args.phase_cmd == "show":
        print(f"current phase: {cur}")
        print(P.render(P.get(cur)))
    elif args.phase_cmd == "set":
        if not P.get(args.target):
            sys.exit(f"error: unknown phase '{args.target}'. Known: {', '.join(P.PHASE_KEYS)}")
        eng.set_phase(args.target)
        print(f"✓ phase -> {args.target}")
    elif args.phase_cmd == "next":
        nk = P.next_key(cur)
        if not nk:
            print(f"already at final phase ({cur})")
        else:
            eng.set_phase(nk)
            print(f"✓ phase {cur} -> {nk}")
    elif args.phase_cmd == "return":
        # loop back to an earlier phase (records why)
        if not P.get(args.target):
            sys.exit(f"error: unknown phase '{args.target}'")
        eng.set_phase(args.target)
        if args.reason:
            eng.log(f"RETURN {cur} -> {args.target}: {args.reason}")
        print(f"↩ returned {cur} -> {args.target}" + (f"  ({args.reason})" if args.reason else ""))


def cmd_finding(args):
    eng = _eng(args)
    if args.finding_cmd == "add":
        if args.sev and args.sev not in SEVERITIES:
            sys.exit(f"error: severity must be one of {SEVERITIES}")
        if args.status and args.status not in STATUSES:
            sys.exit(f"error: status must be one of {STATUSES}")
        # scope-audit the target at creation
        warn = None
        if args.target:
            ok, _ = eng.scope.check(args.target)
            if not ok:
                warn = [host_of(args.target)]
                print(f"⚠ target host {host_of(args.target)} is NOT in scope — recorded with a scope warning.")
        fid = eng.add_finding({
            "title": args.title or "", "vuln_class": args.vuln_class or "",
            "severity": args.sev or "info", "status": args.status or "candidate",
            "target": args.target or "", "param": args.param or "",
            "evidence": args.evidence or "", "poc": args.poc or "",
            "skills_used": (args.skills or "").split(",") if args.skills else [],
            "notes": args.notes or "", "scope_warning": warn,
        })
        print(f"✓ added {fid}")
    elif args.finding_cmd == "list":
        fs = eng.findings(args.status)
        if not fs:
            print("(no findings)" + (f" with status={args.status}" if args.status else ""))
            return
        for f in fs:
            warn = " ⚠" if f.get("scope_warning") else ""
            print(f"  {f['id']}  {f['status']:<9} {f['severity']:<8} {f['vuln_class']:<18} {f['target']}{warn}")
    elif args.finding_cmd == "show":
        f = eng.get_finding(args.id)
        if not f:
            sys.exit(f"error: no finding {args.id}")
        for k, v in f.items():
            print(f"  {k:<14}: {v}")
    elif args.finding_cmd == "set":
        kw = {"status": args.status, "severity": args.sev, "title": args.title,
              "evidence": args.evidence, "poc": args.poc, "notes": args.notes,
              "vuln_class": args.vuln_class}
        if args.sev and args.sev not in SEVERITIES:
            sys.exit(f"error: severity must be one of {SEVERITIES}")
        if args.status and args.status not in STATUSES:
            sys.exit(f"error: status must be one of {STATUSES}")
        if not eng.update_finding(args.id, **kw):
            sys.exit(f"error: no finding {args.id}")
        print(f"✓ updated {args.id}")


def cmd_status(args):
    eng = _eng(args)
    s = eng.summary()
    print(f"engagement : {eng.name}   ({eng.dir})")
    print(f"phase      : {s['phase']}")
    print(f"targets    : {s['targets']}")
    print(f"findings   : {s['findings']}  " +
          "  ".join(f"{k}={v}" for k, v in s["by_status"].items() if v))
    _print_scope(eng.scope)


def cmd_report(args):
    eng = _eng(args)
    report = eng.render_report()
    print(report)
    print(f"\n(written to {os.path.join(eng.dir, 'report.md')})", file=sys.stderr)


# ---------------- argparse ----------------
def build_parser():
    ap = argparse.ArgumentParser(prog="bbwf.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=DEFAULT_BASE, help=f"engagements dir (default {DEFAULT_BASE})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create an engagement")
    p.add_argument("--name", required=True)
    p.add_argument("--in", dest="in_scope", action="append", help="in-scope pattern (repeatable)")
    p.add_argument("--out", dest="out_scope", action="append", help="out-of-scope pattern (repeatable)")
    p.add_argument("--seed", action="append", help="seed URL (repeatable)")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("scope", help="scope manager")
    sc = p.add_subparsers(dest="scope_cmd", required=True)
    for name in ("add", "rm"):
        q = sc.add_parser(name, help=f"{name} scope entries")
        q.add_argument("--name", required=True)
        q.add_argument("--in", dest="in_scope", action="append")
        q.add_argument("--out", dest="out_scope", action="append")
        q.add_argument("--seed", action="append")
    q = sc.add_parser("list", help="show scope"); q.add_argument("--name", required=True)
    q = sc.add_parser("check", help="is a host/URL in scope?")
    q.add_argument("--name", required=True); q.add_argument("target")
    p.set_defaults(fn=cmd_scope)

    p = sub.add_parser("plan", help="print the phase plan")
    p.add_argument("phase", nargs="?", help="a single phase key (optional)")
    p.add_argument("--name", help="engagement (prints its current phase)")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("phase", help="view/advance/return phases")
    ph = p.add_subparsers(dest="phase_cmd", required=True)
    q = ph.add_parser("show"); q.add_argument("--name", required=True)
    q = ph.add_parser("set"); q.add_argument("--name", required=True); q.add_argument("target")
    q = ph.add_parser("next"); q.add_argument("--name", required=True)
    q = ph.add_parser("return"); q.add_argument("--name", required=True)
    q.add_argument("target"); q.add_argument("--reason", default="")
    p.set_defaults(fn=cmd_phase)

    p = sub.add_parser("finding", help="manage findings")
    fc = p.add_subparsers(dest="finding_cmd", required=True)
    q = fc.add_parser("add"); q.add_argument("--name", required=True)
    q.add_argument("--title"); q.add_argument("--class", dest="vuln_class")
    q.add_argument("--sev"); q.add_argument("--status")
    q.add_argument("--target"); q.add_argument("--param")
    q.add_argument("--evidence"); q.add_argument("--poc")
    q.add_argument("--skills"); q.add_argument("--notes")
    q = fc.add_parser("list"); q.add_argument("--name", required=True); q.add_argument("--status")
    q = fc.add_parser("show"); q.add_argument("--name", required=True); q.add_argument("id")
    q = fc.add_parser("set"); q.add_argument("--name", required=True); q.add_argument("id")
    q.add_argument("--status"); q.add_argument("--sev"); q.add_argument("--title")
    q.add_argument("--class", dest="vuln_class")
    q.add_argument("--evidence"); q.add_argument("--poc"); q.add_argument("--notes")
    p.set_defaults(fn=cmd_finding)

    q = sub.add_parser("status", help="engagement overview"); q.add_argument("--name", required=True)
    q.set_defaults(fn=cmd_status)

    q = sub.add_parser("report", help="render report.md"); q.add_argument("--name", required=True)
    q.set_defaults(fn=cmd_report)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

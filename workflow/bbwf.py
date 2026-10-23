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


def _read_patterns(path: str):
    """One pattern per line; blank lines and # comments ignored."""
    out = []
    with open(os.path.expanduser(path), encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def _list_engagements(base: str):
    base = os.path.expanduser(base)
    names = []
    if os.path.isdir(base):
        for n in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, n, "state.json")):
                names.append(n)
    return names


def _apply_scope_edits(sc, args) -> bool:
    """Add in/out/seed values from flags AND their --*-file variants."""
    changed = False
    buckets = [("in_scope", args.in_scope, getattr(args, "in_file", None)),
               ("out_of_scope", args.out_scope, getattr(args, "out_file", None)),
               ("seeds", args.seed, getattr(args, "seed_file", None))]
    for bucket, values, path in buckets:
        for v in (values or []):
            changed |= sc.add(bucket, v)
        if path:
            for v in _read_patterns(path):
                changed |= sc.add(bucket, v)
    return changed


# ---------------- commands ----------------
def cmd_init(args):
    eng = Engagement(args.base, args.name)
    sc = eng.scope
    _apply_scope_edits(sc, args)
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
    # 'which' is cross-engagement — it needs no --name, so handle it first.
    if args.scope_cmd == "which":
        host = host_of(args.target)
        hits = []
        for name in _list_engagements(args.base):
            ok, reason = Engagement(args.base, name).scope.check(args.target)
            if ok:
                hits.append((name, reason))
        print(f"host: {host}")
        if hits:
            for name, reason in hits:
                print(f"  IN SCOPE for '{name}'  —  {reason}")
        else:
            print("  not in scope for any engagement (default-deny)")
        sys.exit(0 if hits else 2)

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
        changed = _apply_scope_edits(sc, args)
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


def cmd_engagements(args):
    names = _list_engagements(args.base)
    if not names:
        print(f"(no engagements under {os.path.expanduser(args.base)})")
        return
    print(f"engagements under {os.path.expanduser(args.base)}:")
    for name in names:
        eng = Engagement(args.base, name)
        s = eng.summary()
        sc = eng.scope
        conf = s["by_status"].get("confirmed", 0)
        print(f"  {name:<20} phase={s['phase']:<8} findings={s['findings']:<3} "
              f"(confirmed={conf})  scope: in={len(sc.in_scope)} out={len(sc.out_of_scope)}")


def cmd_recon(args):
    import recon as R
    eng = _eng(args)

    def tee(msg):          # recon is interactive — show progress + keep the log
        eng.log(msg)
        print(msg, file=sys.stderr)

    seeds = args.seed or None
    res = R.run(eng, seeds=seeds, active=not args.no_active, crawl=args.crawl,
                timeout=args.timeout, dry=args.dry_run, log=tee)
    print()
    if args.dry_run:
        print("(dry-run — commands above would run; nothing executed, nothing recorded)")
    if res["missing_tools"]:
        print(f"tools not installed (skipped): {', '.join(res['missing_tools'])}")
    print(f"apexes enumerated : {', '.join(res['apexes']) or '(none)'}")
    print(f"hosts discovered  : {res['discovered']}  ->  in-scope {len(res['in_scope'])}, "
          f"dropped out-of-scope {len(res['dropped'])}")
    live = [t for t in res["targets"] if t.get("status")]
    if live:
        print(f"live hosts        : {len(live)}")
        for t in live[:40]:
            tech = f"  [{', '.join(t['tech'])}]" if t.get("tech") else ""
            print(f"  {str(t.get('status')):>3}  {t.get('url') or t['host']}{tech}")
    if res["endpoints"]:
        withp = [e for e in res["endpoints"] if e["params"]]
        print(f"endpoints         : {len(res['endpoints'])}  ({len(withp)} with parameters)")
        for e in withp[:40]:
            print(f"  {e['url']}   ?{','.join(e['params'])}")
    print("\nRecon only — surface mapped, nothing tested. You decide what to hunt;")
    print("scope-check before touching anything new:  bbwf.py scope check --name <eng> <url>")


def cmd_submit(args):
    import time
    import templates as T
    eng = _eng(args)
    f = eng.get_finding(args.id)
    if not f:
        sys.exit(f"error: no finding {args.id}")
    if f["status"] not in ("confirmed", "reported") and not args.force:
        sys.exit(f"error: {args.id} is '{f['status']}', not confirmed. "
                 f"Confirm it first, or pass --force to render anyway.")
    md = T.render(f, eng.name, platform=args.platform, template=args.template,
                  date=time.strftime("%Y-%m-%d"))
    if args.out:
        out = args.out
    else:
        subdir = os.path.join(eng.dir, "submissions")
        os.makedirs(subdir, exist_ok=True)
        out = os.path.join(subdir, f"{args.id}.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    print(f"\n(written to {out} — review/fill any _(stub)_ sections before uploading)", file=sys.stderr)


def cmd_dashboard(args):
    import dashboard as DB
    html = DB.render(args.base)
    out = args.out or os.path.join(os.path.expanduser(args.base), "dashboard.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"✓ wrote {out}")
    print("  open it in a browser (file://). Local snapshot — do not commit or share it.")
    if args.open:
        import webbrowser
        webbrowser.open("file://" + os.path.abspath(out))


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
    p.add_argument("--in-file", dest="in_file", help="file of in-scope patterns (one per line)")
    p.add_argument("--out-file", dest="out_file", help="file of out-of-scope patterns (one per line)")
    p.add_argument("--seed-file", dest="seed_file", help="file of seed URLs (one per line)")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("scope", help="scope manager")
    sc = p.add_subparsers(dest="scope_cmd", required=True)
    q = sc.add_parser("add", help="add scope entries")
    q.add_argument("--name", required=True)
    q.add_argument("--in", dest="in_scope", action="append")
    q.add_argument("--out", dest="out_scope", action="append")
    q.add_argument("--seed", action="append")
    q.add_argument("--in-file", dest="in_file", help="file of in-scope patterns (one per line)")
    q.add_argument("--out-file", dest="out_file", help="file of out-of-scope patterns (one per line)")
    q.add_argument("--seed-file", dest="seed_file", help="file of seed URLs (one per line)")
    q = sc.add_parser("rm", help="remove scope entries")
    q.add_argument("--name", required=True)
    q.add_argument("--in", dest="in_scope", action="append")
    q.add_argument("--out", dest="out_scope", action="append")
    q.add_argument("--seed", action="append")
    q = sc.add_parser("list", help="show scope"); q.add_argument("--name", required=True)
    q = sc.add_parser("check", help="is a host/URL in scope? (one engagement)")
    q.add_argument("--name", required=True); q.add_argument("target")
    q = sc.add_parser("which", help="which engagement(s) is a host/URL in scope for?")
    q.add_argument("target")
    p.set_defaults(fn=cmd_scope)

    q = sub.add_parser("engagements", help="list all engagements")
    q.set_defaults(fn=cmd_engagements)

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

    q = sub.add_parser("recon", help="run scope-gated recon tools and record the surface")
    q.add_argument("--name", required=True)
    q.add_argument("--seed", action="append", help="override seeds for this run (repeatable)")
    q.add_argument("--no-active", action="store_true",
                   help="passive only — no requests sent to targets (skip httpx/katana)")
    q.add_argument("--crawl", action="store_true", help="also active-crawl live hosts (katana)")
    q.add_argument("--timeout", type=int, default=30, help="per-tool timeout seconds (default 30)")
    q.add_argument("--dry-run", action="store_true",
                   help="print the exact commands that would run; execute nothing")
    q.set_defaults(fn=cmd_recon)

    q = sub.add_parser("submit", help="render one finding into a submission-ready write-up")
    q.add_argument("--name", required=True)
    q.add_argument("id", help="finding id, e.g. F001")
    q.add_argument("--platform", default="generic",
                   choices=["generic", "hackerone", "bugcrowd", "intigriti"])
    q.add_argument("--template", help="class name, or path to a custom .md template")
    q.add_argument("--out", help="output path (default <base>/<name>/submissions/<id>.md)")
    q.add_argument("--force", action="store_true", help="render even if not confirmed")
    q.set_defaults(fn=cmd_submit)

    q = sub.add_parser("dashboard", help="render a local HTML findings overview (all engagements)")
    q.add_argument("--out", help="output path (default <base>/dashboard.html)")
    q.add_argument("--open", action="store_true", help="open it in a browser after writing")
    q.set_defaults(fn=cmd_dashboard)

    q = sub.add_parser("report", help="render report.md"); q.add_argument("--name", required=True)
    q.set_defaults(fn=cmd_report)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

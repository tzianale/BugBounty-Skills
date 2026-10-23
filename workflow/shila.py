#!/usr/bin/env python3
"""
shila.py — friendly front-end for the bug-bounty workflow (wraps bbwf.py).

Natural verbs instead of long bbwf.py invocations. It does not add behavior —
it translates to bbwf.py, which does the work (scope, phases, findings,
dashboard, submit, recon). Same safety model: operator-led, scope-gated.

  shila hunt <name> [domain ...]     start a session (engagement); domains are
                                     added as in-scope + seeds
  shila recon <name> [--crawl] [--passive] [--dry-run]
  shila scope <name> <url>           is this host in scope for this engagement?
  shila which <url>                  which engagement(s) is this host in scope for?
  shila plan [name | phase]          show the plan (current phase of <name>, or a phase)
  shila next <name>                  advance to the next phase
  shila back <name> <phase> [why]    return to an earlier phase
  shila found <name> --title .. --class .. --sev .. --target .. [--param ..] [--poc ..] [--evidence ..] [--skills ..]
  shila findings <name> [status]     list findings
  shila confirm <name> <id> [sev]    mark a finding confirmed
  shila show <name>                  engagement status
  shila show dashboard               build + open the findings dashboard
  shila list                         all engagements
  shila report <name>                render report.md
  shila submit <name> <id> [platform]  upload-ready write-up (hackerone|bugcrowd|intigriti|generic)

  Global: --base <dir>   (default ~/.bb-engagements, or $BBWF_BASE)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbwf  # noqa: E402


def _run(argv):
    """Call bbwf with argv; swallow a clean SystemExit so verbs can chain."""
    try:
        bbwf.main(argv)
        return 0
    except SystemExit as e:
        return e.code or 0


def _has_scheme(s):
    return "://" in s


def main():
    argv = sys.argv[1:]
    base = []
    # optional leading --base <dir>
    if argv[:1] == ["--base"] and len(argv) >= 2:
        base = ["--base", argv[1]]
        argv = argv[2:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    verb, rest = argv[0], argv[1:]

    # split positional args from flags (flags start with -)
    pos = [a for a in rest if not a.startswith("-")]
    flags = []
    i = 0
    while i < len(rest):
        if rest[i].startswith("-"):
            flags.append(rest[i])
            if i + 1 < len(rest) and not rest[i + 1].startswith("-"):
                flags.append(rest[i + 1]); i += 1
        i += 1

    if verb == "hunt":
        if not pos:
            sys.exit("usage: shila hunt <name> [domain ...]")
        name = pos[0]
        domains = pos[1:]
        init = ["init", "--name", name]
        for d in domains:
            init += ["--in", d, "--seed", d if _has_scheme(d) else "https://" + d]
        init += flags
        _run(base + init)
        if domains:  # scope is set -> move to recon and show its plan
            _run(base + ["phase", "set", "--name", name, "recon"])
            print()
            _run(base + ["plan", "recon"])
        else:
            print("\nAdd scope, then recon:")
            print(f"  shila hunt {name} <domain>        # add in-scope domain + seed")
            print(f"  shila recon {name}")

    elif verb == "recon":
        if not pos:
            sys.exit("usage: shila recon <name> [--crawl|--passive|--dry-run]")
        # friendly --passive -> bbwf --no-active
        f = ["--no-active" if x == "--passive" else x for x in flags]
        sys.exit(_run(base + ["recon", "--name", pos[0]] + f))

    elif verb == "scope":
        if len(pos) < 2:
            sys.exit("usage: shila scope <name> <url>")
        sys.exit(_run(base + ["scope", "check", "--name", pos[0], pos[1]]))

    elif verb == "which":
        if not pos:
            sys.exit("usage: shila which <url>")
        sys.exit(_run(base + ["scope", "which", pos[0]]))

    elif verb == "plan":
        if not pos:
            sys.exit(_run(base + ["plan"]))
        # a known phase key -> phase plan; otherwise treat as engagement name
        if bbwf.P.get(pos[0]):
            sys.exit(_run(base + ["plan", pos[0]]))
        sys.exit(_run(base + ["plan", "--name", pos[0]]))

    elif verb == "next":
        if not pos:
            sys.exit("usage: shila next <name>")
        sys.exit(_run(base + ["phase", "next", "--name", pos[0]]))

    elif verb == "back":
        if len(pos) < 2:
            sys.exit("usage: shila back <name> <phase> [why]")
        a = ["phase", "return", "--name", pos[0], pos[1]]
        if len(pos) > 2:
            a += ["--reason", " ".join(pos[2:])]
        sys.exit(_run(base + a))

    elif verb in ("found", "add"):
        if not pos:
            sys.exit("usage: shila found <name> --title .. --class .. --sev .. --target ..")
        sys.exit(_run(base + ["finding", "add", "--name", pos[0]] + flags))

    elif verb == "findings":
        if not pos:
            sys.exit("usage: shila findings <name> [status]")
        a = ["finding", "list", "--name", pos[0]]
        if len(pos) > 1:
            a += ["--status", pos[1]]
        sys.exit(_run(base + a))

    elif verb == "confirm":
        if len(pos) < 2:
            sys.exit("usage: shila confirm <name> <id> [severity]")
        a = ["finding", "set", "--name", pos[0], pos[1], "--status", "confirmed"]
        if len(pos) > 2:
            a += ["--sev", pos[2]]
        sys.exit(_run(base + a))

    elif verb == "show":
        if pos and pos[0] == "dashboard":
            sys.exit(_run(base + ["dashboard", "--open"]))
        if not pos:
            sys.exit("usage: shila show <name>   |   shila show dashboard")
        sys.exit(_run(base + ["status", "--name", pos[0]]))

    elif verb == "dashboard":
        sys.exit(_run(base + ["dashboard", "--open"]))

    elif verb == "list":
        sys.exit(_run(base + ["engagements"]))

    elif verb == "report":
        if not pos:
            sys.exit("usage: shila report <name>")
        sys.exit(_run(base + ["report", "--name", pos[0]]))

    elif verb == "submit":
        if len(pos) < 2:
            sys.exit("usage: shila submit <name> <id> [platform]")
        a = ["submit", "--name", pos[0], pos[1]]
        if len(pos) > 2:
            a += ["--platform", pos[2]]
        a += flags
        sys.exit(_run(base + a))

    else:
        sys.exit(f"shila: unknown command '{verb}'  (try: shila help)")


if __name__ == "__main__":
    main()

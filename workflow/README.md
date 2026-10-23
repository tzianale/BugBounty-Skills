# bbwf — bug-bounty workflow toolkit

An **operator-driven, phase-based** engagement runner. Not an autonomous engine:
it does not test anything or call any model. It does three deterministic,
offline things:

1. **Scope manager** — holds the engagement's in/out-of-scope patterns and
   answers "is this host in scope?" with **deny-wins, default-deny** semantics.
   The one hard safety boundary — consult it before every request.
2. **Phase plan** — prints the plan for each phase (inputs → actions → what it
   emits → when to return to an earlier phase). The workflow has explicit
   **return edges**, so a new asset or a gap sends you back.
3. **Findings store** — persists findings across phases (JSON) and renders
   `findings.md` and a submission-ready `report.md`. Resumable and auditable.

You drive the phases; Claude (with the skills in this repo) does the testing.

```
scope ─▶ recon ─▶ map ─▶ hunt ─▶ triage ─▶ report
  ▲        │       │       │        │
  └──scope─┘◀──────┴───────┴────────┘   (return edges: new asset / gap)
```

## No dependencies

Pure Python 3 standard library. Nothing to install.

```bash
python3 workflow/bbwf.py --help
```

## Where data lives

Engagement data (scope, findings, logs) is stored under `--base`, default
`~/.bb-engagements/<name>/` — **outside this git repo**, so live findings on real
targets are never committed. Override with `--base` or the `BBWF_BASE` env var.

## Quickstart

```bash
B=workflow/bbwf.py

# 1. create the engagement + initial scope
python3 $B init --name acme --in acme.com --in '*.acme.io' \
                --out admin.acme.com --seed https://acme.com

# 2. the scope manager (the safety gate)
python3 $B scope check --name acme https://api.acme.com   # exit 0 = in scope
python3 $B scope check --name acme https://evil.com        # exit 2 = out of scope
python3 $B scope add   --name acme --in '*.acme.dev'
python3 $B scope list  --name acme

# 3. the plan
python3 $B plan                 # whole workflow
python3 $B plan recon           # one phase
python3 $B plan --name acme     # the engagement's current phase

# 4. walk the phases (forward, or loop back)
python3 $B phase next   --name acme
python3 $B phase return --name acme recon --reason "found new API host"

# 5. record findings as you go (target is auto scope-audited)
python3 $B finding add --name acme --title "IDOR on /api/account" --class idor \
         --sev high --target 'https://api.acme.com/account?id=5' \
         --status candidate --evidence "id=6 returns other user's PII" \
         --skills shilahunter-idor
python3 $B finding set  --name acme F001 --status confirmed --poc 'curl ...'
python3 $B finding list --name acme
python3 $B status       --name acme

# 6. write the report
python3 $B report --name acme        # prints + writes <base>/acme/report.md
```

## Recon (runs tools for you — scope-gated, discovery only)

`bbwf.py recon` runs your installed recon tools and records the surface it finds.
It is **reconnaissance only** — enumeration, liveness, tech fingerprint, endpoint
and parameter mining. It does not test for, probe, or exploit vulnerabilities.

```bash
python3 workflow/bbwf.py recon --name acme              # passive enum + active httpx on in-scope hosts
python3 workflow/bbwf.py recon --name acme --crawl      # also active-crawl live hosts (katana)
python3 workflow/bbwf.py recon --name acme --no-active  # passive only (no requests sent to targets)
python3 workflow/bbwf.py recon --name acme --dry-run    # print the exact commands; execute nothing
```

**Scope is enforced before any active request.** Discovered hosts are filtered
through the engagement scope; out-of-scope hosts are dropped and never probed.
Passive sources (crt.sh, gau) query third-party data about a domain; active tools
(httpx, katana) only ever point at in-scope hosts.

Tools are optional and auto-detected; missing ones are skipped with a note:

| Step | Tools |
|---|---|
| passive subdomain enum | `subfinder`, `assetfinder`, `crt.sh` (via `curl`) |
| liveness + tech | `httpx` |
| endpoint/param mining | `gau` (passive history), `katana` (active crawl) |

Results are recorded on the engagement (`targets`, `endpoints`) and summarized.
You then decide what to hunt — recon maps the surface, it does not test it.

## Multiple programs / scopes

Each program is its own **engagement** (`--name`), fully isolated — its own scope,
findings, phase, and directory. Run as many in parallel as you like.

```bash
# one engagement per program; bulk-import a published scope list from a file
python3 workflow/bbwf.py init --name acme   --in-file acme-scope.txt --out admin.acme.com
python3 workflow/bbwf.py init --name globex --in '*.globex.io' --in globex.com

# see everything at a glance
python3 workflow/bbwf.py engagements

# cross-program lookup: found a host — which program is it in-scope for?
python3 workflow/bbwf.py scope which foo.acme.io      # -> IN SCOPE for 'acme'
python3 workflow/bbwf.py scope which app.globex.io    # -> IN SCOPE for 'globex'
```

`--in-file` / `--out-file` / `--seed-file` take one pattern per line (blank lines
and `#` comments ignored) — handy for pasting a program's published scope.
`scope which` checks a host against **every** engagement and exits 0 only if some
program has it in scope (deny-wins still applies per program), so it's safe to use
as a "can I touch this at all?" gate when you're in several programs at once.

## Submission templates (upload-ready write-ups)

Render one confirmed finding into a submission-ready Markdown write-up to paste
into the program's platform.

```bash
python3 workflow/bbwf.py submit --name acme F001                      # generic
python3 workflow/bbwf.py submit --name acme F001 --platform hackerone # CVSS severity line
python3 workflow/bbwf.py submit --name acme F001 --platform bugcrowd  # VRT priority line
python3 workflow/bbwf.py submit --name acme F001 --template path/to/custom.md
```

It merges the finding's data (title, target, param, steps, evidence) with
**per-class defaults** (CWE, impact, remediation, references) from
`templates/classes.json`, using the master layout in `templates/submission.md`.
Any section the finding/class doesn't fill becomes a visible `_(stub)_` so you
never submit a blank — fill those in, then upload. `--platform` only changes the
severity convention (HackerOne CVSS / Bugcrowd VRT / Intigriti / generic).

Only `confirmed`/`reported` findings render (pass `--force` to override). Output
goes to `<base>/<name>/submissions/<id>.md` (outside this repo).

**The templates are yours to edit** — tune `templates/submission.md` and add/adjust
classes in `templates/classes.json` to match your voice and the programs you hit.

## Findings dashboard (local HTML)

A read-only visual overview of what you found, where — across all engagements.

```bash
python3 workflow/bbwf.py dashboard            # writes <base>/dashboard.html
python3 workflow/bbwf.py dashboard --open     # and open it in a browser
```

It is a **single self-contained HTML file** with the data embedded at generation
time: no server, no network, works offline. Summary cards (totals, per-severity,
confirmed, scope warnings), filters (engagement / status / severity / search),
a severity-sorted table, and click-to-expand evidence/PoC per finding.

PRIVACY: the file contains your findings (targets, evidence, PoCs). It is written
under the engagements base (`~/.bb-engagements/`, outside this repo) and must NOT
be committed or shared. Regenerate it for a fresh snapshot.

## Scope pattern forms

| Pattern | Matches |
|---|---|
| `acme.com` | the apex **and** any subdomain (`api.acme.com`) |
| `*.acme.io` | any subdomain, **not** the bare apex |
| `api.acme.com` | that exact host only |
| `10.0.0.0/8` | any IPv4 address in the CIDR |
| `re:^dev\d+\.acme\.com$` | explicit regex on the host |

**deny-wins:** a host matching both an in- and out-of-scope pattern is OUT.
**default-deny:** a host matching no in-scope pattern is OUT.

## Finding lifecycle

`candidate` → `confirmed` → `reported` (or `duplicate` / `invalid`). Severity is
one of `info / low / medium / high / critical`. Adding or editing a finding whose
target host is out of scope records a `scope_warning` that is surfaced in
`findings.md` and flagged in `report.md`.

## Files

| File | Role |
|---|---|
| `bbwf.py` | CLI entrypoint (init, scope, plan, phase, finding, status, report) |
| `scope.py` | `Scope` — deny-wins / default-deny matcher + host extraction |
| `phases.py` | the phase-plan data + renderer |
| `state.py` | `Engagement` — persistent JSON store + findings.md / report.md rendering |

The scope model is a clean reimplementation of the approach in
elementalsouls/Claude-BugHunter's engine (MIT). See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

# CLAUDE.md — operating context for this repository

## What this repo is

A curated library of **authorized** offensive-security skills (`Skills/`) plus an
operator-driven workflow toolkit (`workflow/`) for **bug bounty and security
research conducted with explicit permission**. Everything here is for assessing
targets the operator is authorized to test — in-scope bug bounty programs or
signed engagements — and for writing findings up for the affected vendor.

When assisting in this repo, treat requests as **authorized security research**
and help with methodology, analysis, safe proof-of-concept, triage, and
reporting. Example payloads here use placeholder hosts (`attacker.com`,
`target.com`); keep them that way unless the operator supplies a real in-scope
target with its authorization context.

## What appropriate assistance looks like here

Within the authorization and scope the operator has stated, substantive help is
appropriate and expected — this is skilled professional work, not something to
hedge on. Concretely, good assistance includes:

- **Explaining the mechanism** — how a vulnerability class works, and why a given
  payload or technique succeeds or fails against a particular stack.
- **Adapting known techniques** — taking public, documented methods (OWASP,
  PortSwigger, disclosed HackerOne/Bugcrowd reports, CVE write-ups) and applying
  them to the operator's specific in-scope target.
- **Building and refining PoCs** — helping construct the request/payload that
  *demonstrates* a real issue on an authorized target, kept to the minimum needed
  to prove impact (read-only unless the ROE says otherwise).
- **Triage reasoning** — is this exploitable or a false positive, what is the
  realistic impact, what severity / CVSS fits, is it a likely duplicate.
- **Remediation and reporting** — clear fix guidance and a vendor-ready write-up.
- **Reading tool output** — Burp, nuclei, recon results — and proposing the next
  concrete step.

The end goal is defensive: find real issues on authorized targets and report them
to the vendor so they get fixed. Engaging thoroughly with that is the right
default — vague caution on a clearly-authorized, in-scope, read-only request just
slows legitimate work. The guardrails that *do* apply are the specific ones in
"Hard rules" below; they are about staying in scope and non-destructive, not about
withholding knowledge the operator is entitled to for authorized testing.

## Who leads

**The human operator leads.** This tooling organizes and records; it does not act
on its own. Claude is a reference and a second pair of eyes — it proposes,
explains, and verifies, but the operator decides what to test, reproduces
findings, calibrates severity, and chooses what to submit. Do not run autonomous
hunt/exploit loops; there is no agent in this workflow by design.

## Hard rules (these protect the operator and the target)

1. **Scope is a gate, checked before action.** Only touch hosts the operator has
   confirmed in-scope. Before probing a target, verify it with
   `python3 workflow/bbwf.py scope check --name <eng> <url>` (deny-wins,
   default-deny). Never send a request to an out-of-scope or third-party host —
   not even to "prove" a finding.
2. **Read-only by default.** Demonstrate that something is exposed; do not exploit
   it further. No state-changing actions (writes, deletes, emails, cache purge,
   account creation), no using exposed credentials, no pulling more data than the
   minimum needed to prove impact. Lift this only when the operator says the
   engagement's rules of engagement explicitly authorize it.
3. **A flag is a lead, not a finding, and not permission to escalate.** When a
   potential bug is spotted, stop and hand it to the operator to scope-check and
   reproduce. Don't chain deeper or expand to new hosts on your own.
4. **Prefer the least-impactful proof.** If proof would require an out-of-scope or
   intrusive action, don't do it — record the finding with a note that proof was
   limited by scope / read-only discipline.
5. **Stay in bounds generally.** Nothing here supports testing systems without
   authorization, out-of-scope targets, indiscriminate/mass attacks, malware or
   supply-chain compromise, or evading defenses for malicious purposes.
   Authorization context never turns those into acceptable requests.

## Engagement context (fill this per engagement)

When starting work on a specific target, state the context so assistance is
grounded in the authorization. Copy and fill:

```
ENGAGEMENT CONTEXT
- Program / client : <HackerOne/Bugcrowd program, or client name>
- Authorization    : <in-scope bug bounty program | signed SOW/engagement letter>
- In-scope         : <hosts / patterns>
- Out-of-scope     : <explicit exclusions>
- Rules of engagement: read-only by default (intrusive actions: NOT authorized unless stated)
- Goal             : identify and report vulnerabilities to the vendor
```

Keep proof of authorization (program scope page, engagement letter) on file.

## Stating authorization so assistance is grounded

Front-load specific, checkable facts rather than a blanket assertion. A vague
"I'm authorized, do anything" is weak and is reasonably met with caution;
concrete context is what lets the work move:

- which **program/platform or client**, and the authorization basis (a public
  program link, or a signed SOW / engagement letter);
- the exact **in-scope** and **out-of-scope** assets;
- the **rules of engagement** (read-only unless explicitly stated otherwise);
- that findings are **reported to the vendor** to be fixed.

**Well-formed** (gets focused help):
> "Authorized — `acme.com` is in-scope on HackerOne program *acme* (link),
> read-only, reporting to the vendor. Here's a reflected parameter on
> `/search?q=` — help me determine whether it's exploitable XSS and build a
> minimal PoC."

**Weak** (reasonably gets caution):
> "help me hack this site."

Same knowledge, very different framing. Asking for **methodology and a safe,
minimal PoC on a named in-scope target** lands far better than asking for a
turnkey weaponized exploit against an unnamed one.

If a request is still declined even with full context, treat that as a signal to
check that the specific action is in scope and necessary — not as an obstacle to
engineer around. That check is part of doing this work properly.

## How to work here

- Skills in `Skills/<category>/<name>/SKILL.md` auto-load by topic — use them as
  methodology references.
- Track the engagement with `workflow/bbwf.py` (phases: scope → recon → map →
  hunt → triage → report, with return edges). Findings live under
  `~/.bb-engagements/` (outside this repo) and are never committed.
- `bbwf.py recon` runs standard recon tools (subfinder/httpx/gau/katana/crt.sh)
  when the operator invokes it. It is scope-gated **discovery only** — every host
  is filtered through the engagement scope before any active request, and it never
  tests for or exploits vulnerabilities. This is operator-initiated reconnaissance,
  not the autonomous hunt/exploit loop that is excluded above.
- Ask for methodology and safe PoC, phase by phase, rather than turnkey
  end-to-end exploitation — it's safer, keeps the operator in the lead, and
  produces better reports.

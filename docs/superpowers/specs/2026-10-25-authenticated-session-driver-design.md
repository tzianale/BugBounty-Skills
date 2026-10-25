# Authenticated Session Driver — design

**Date:** 2026-10-25
**Status:** approved design, pending implementation plan
**Scope of change:** `workflow/bbwf.py` (+ `workflow/creds.py`), one new skill
`Skills/web/shilahunter-authenticated-session/SKILL.md`, docs.

## Problem

Several authorized bug-bounty programs in use here (e.g. SUISSEDIGITAL / netplus,
sweez) hand out **test accounts**, and much of the real attack surface is behind
login. Today the operator must log in by hand and paste requests. We want Claude
to be able to **drive an authenticated session itself** — log in with the
provided test credentials and work the authenticated surface — while staying
inside this repo's hard rules (`CLAUDE.md`): operator-led, read-only by default,
scope-gated, "a flag is a lead, not a finding."

This is explicitly **not** an autonomous hunt/exploit loop. Claude drives the
*mechanics of read-only authenticated exploration* and stops at the first
exploitable lead.

## Non-goals

- No autonomous authenticated testing loop (the thing `CLAUDE.md` excludes).
- No state-changing actions: no writes, orders, profile edits, messages, bulk
  registration, password/Cronto-letter orders, or account locking.
- No cross-account data access as "proof" — that is a lead handed to the operator.
- **TKB ebanking is out of this feature entirely** — it needs the OLIVIA Key app
  (mosaic 2FA), one session per account, and must not be locked. The credential
  store may hold a `manual-only` note for it but Claude never drives it.

## The agreed boundary (the safety contract)

Read-only, scope-gated, **stop-at-leads**:

1. Scope-check the login URL and every subsequent host before any request;
   out-of-scope ⇒ refuse (deny-wins / default-deny, unchanged).
2. Log in, capture the session cookie/token.
3. Issue **read-only** authenticated requests against *the operator's own* test
   account; surface each request + response.
4. Map the authenticated surface (endpoints, parameters, object references) and
   record it to the engagement.
5. At the first exploitable lead, **STOP**: record a `candidate` finding and hand
   it to the operator. Do not escalate, pivot to another account, or change state.

"Read-only" here means safe/idempotent requests only (GET/HEAD and the app's
own read endpoints). Anything that mutates server state is a lead, not a step.

## Components

### 1. Credential store — `creds.py` + `bbwf.py creds`

Per-engagement secrets, stored **outside the repo** at
`<base>/<name>/creds.json` (default base `~/.bb-engagements`, already git-ignored
by being outside the repo). File is created `chmod 600`.

Data model (`creds.json`):

```json
{
  "accounts": [
    {
      "id": "sweez-1",
      "label": "sweez selfcare primary",
      "host": "my.sweez.ch",
      "username": "colt.seavers@example.com",
      "secret": "……",
      "note": "",
      "manual_only": false
    }
  ]
}
```

CLI (mirrors existing `add_parser` / `cmd_*` / `set_defaults(fn=...)` style, uses
`_eng(args)` for the engagement):

- `creds add --name <eng> --id <id> --host <host> --user <u> [--secret <s> | --secret-stdin] [--label ..] [--note ..] [--manual-only]`
  - `--secret-stdin` reads the secret from stdin so it never lands in shell history.
  - `host` is validated against the engagement scope at add time; out-of-scope
    host ⇒ refuse (a credential you could never use in scope is a mistake).
- `creds list --name <eng>` — table, secrets **masked**: show only the first 3
  characters plus length, e.g. `col****(len=15)`. Never prints the full secret.
- `creds get  --name <eng> <id> [--field user|host|secret]` — prints one field;
  `secret` is the only way to retrieve the cleartext, for use at login time.
- `creds rm   --name <eng> <id>`.

Masking rule: a secret is shown as `<first3>****(len=N)`; empty/short secrets as
`****`. `get --field secret` is the single un-masked path and prints nothing else.

### 2. Skill — `shilahunter-authenticated-session`

New skill under `Skills/web/` (installed to `~/.claude/skills/` by `install.sh`,
which already copies every `SKILL.md`). It encodes the boundary above as an
operational checklist so it auto-loads whenever authenticated testing comes up.
Standard skill shape (metadata, trigger phrases, instructions, methodology). It
is the safety contract in prose and references the scope gate and `finding add`.

Trigger phrases include: `authenticated session, log in, test account,
credentialed testing, logged-in surface, session cookie, authenticated IDOR`.

### 3. Session engines (guidance in the skill, no new code)

- **`curl` cookie-jar** (`curl -c jar -b jar …`) for API/simple-form hosts
  (`caius.dev.netplus.ch`, sweez API). Scriptable via Bash, easy to show.
- **`claude-in-chrome`** for JS-heavy selfcare SPAs (`my.dev.netplus.ch`,
  `my.sweez.ch`) so the operator watches the real tab; needs the extension and
  per-site permission grant.

### 4. Findings integration (no new code)

At a lead, Claude calls existing `bbwf.py finding add --status candidate` with
sanitized evidence (the credential's secret and the live session token are never
written into evidence/PoC fields) and the applicable skill name.

## Data flow

```
operator: creds add (secret via stdin)      -> <base>/<name>/creds.json (600)
Claude:   creds get <id> --field secret      -> secret (in-memory for this session)
Claude:   scope check <login-url>            -> IN ? continue : refuse
Claude:   login (curl jar | chrome)          -> session cookie/token (masked when shown)
Claude:   read-only auth requests            -> surface recorded on engagement
Claude:   first exploitable lead             -> finding add --status candidate ; STOP
```

## Error / safety handling

- Out-of-scope login URL or follow-up host ⇒ hard refuse, no request sent.
- Login appears rate-limited / account locked ⇒ stop, do **not** retry-hammer
  (respects "don't lock", "no brute force"); switch account only if the program
  provides another and the operator agrees.
- One account loaded at a time; respect one-session-per-account.
- `manual_only` account ⇒ Claude refuses to drive it (e.g. TKB ebanking).
- Secrets never printed unmasked except `creds get --field secret`; never echoed
  into findings, logs, reports, or the transcript; never committed.

## Testing

- `creds.py` unit tests: add/get/rm round-trip; masking never reveals full
  secret; file is created `0o600`; `--secret-stdin` path; out-of-scope host at
  `creds add` is refused; `manual_only` flag round-trips.
- Scope-gate-before-login: a documented helper (or the skill's first step) refuses
  an out-of-scope login URL — covered by a `scope check` assertion in test.
- Skill is prose; validated once by walking the sweez login + read-only surface
  map with the operator, confirming the stop-at-leads behavior on a real lead.

## Files touched

| File | Change |
|---|---|
| `workflow/creds.py` | new — `CredStore` load/save (600), mask, CRUD |
| `workflow/bbwf.py`  | add `creds` subparser + `cmd_creds*` handlers |
| `Skills/web/shilahunter-authenticated-session/SKILL.md` | new skill |
| `workflow/README.md` | document `creds` + the authenticated-session flow |
| `README.md` | mention the new skill in the web table (count 30 → 31) |

## Open questions

None blocking. (`claude-in-chrome` permission setup is operator-side, one-time.)

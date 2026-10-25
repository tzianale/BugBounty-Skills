---
name: shilahunter-authenticated-session
description: "Drive an authenticated session on an in-scope target using operator-supplied test-account credentials from the credential store — logging in with provided test-account credentials, capturing the session cookie/token, and mapping the logged-in attack surface for credentialed testing of an in-scope target (authenticated IDOR, broken access control, session handling, business logic behind login). Strictly read-only, scope-gated, operator-led, and stop-at-leads: the login URL and every follow-up host are scope-checked before any request, only one account is driven at a time, accounts flagged manual_only (e.g. a hardware-2FA ebanking login) are never auto-driven, session cookies/tokens are always shown masked and never written to findings, logs, reports, or git, and at the first exploitable lead Claude stops and hands a candidate finding to the operator instead of escalating. Use whenever the task involves an authenticated session, logging in with test-account credentials, credentialed testing of an in-scope target, the logged-in attack surface, session cookies, or authenticated IDOR."
---

# Driving an Authenticated Session — Read-Only, Scope-Gated, Stop-at-Leads

This skill is the safety boundary from `CLAUDE.md`, written out as an operational
checklist for the one case where Claude is allowed to actively drive something:
logging into an **authorized, in-scope** target with an **operator-provided test
account** and working the logged-in surface. It is not, and must never become,
an autonomous hunt/exploit loop. The operator leads; Claude executes the
mechanics of a read-only authenticated walk-through and stops the moment
anything looks exploitable.

Everything below assumes an engagement is already open and scoped
(`python3 workflow/bbwf.py scope ...`) and that test-account credentials have
already been added by the operator (`python3 workflow/bbwf.py creds add ...`,
secret via `--secret-stdin` so it never lands in shell history).

## Trigger Phrases

`authenticated session, log in, test account, credentialed testing, logged-in surface, session cookie, authenticated IDOR`

## The Contract — five steps, in order, every time

### 1. Scope-check the login URL and every follow-up host — before anything is sent

```bash
python3 workflow/bbwf.py scope check --name <eng> https://target.com/login
```

Run this against the login URL first. Then run it again against **every** host
a redirect, SSO hop, API call, or asset load touches during the session — a
host that was never checked gets nothing sent to it. Deny-wins, default-deny,
unchanged from the rest of this repo.

**Out-of-scope ⇒ refuse.** Do not send a single request "just to check" — that
request is itself the violation.

### 2. Load one account at a time from the credential store

```bash
python3 workflow/bbwf.py creds get --name <eng> <id> --field secret
```

This is the only cleartext path — the secret exists in-memory for this session
only, never echoed elsewhere. Rules that apply here:

- One account, one session, at a time. Don't open a second session on the same
  account concurrently.
- Don't retry-hammer a failing login — that is exactly how test accounts get
  locked. One clean attempt; if it fails or looks rate-limited, stop and tell
  the operator rather than retrying.
- **Never drive an account flagged `manual_only`.** Some programs gate login
  behind out-of-band hardware/app 2FA that only the operator can complete
  (for example, an ebanking test account behind an OLIVIA-Key-style mosaic
  2FA app, one session per account, must-not-lock). If `creds list`/`note`
  marks an account this way, Claude refuses to attempt the login step at all
  — that account is operator-only, full stop.

### 3. Log in, capture the session — mask it, always

Perform the login with one of the two engines below. Capture the resulting
session cookie/token, but never show it in cleartext after this step:

- Mask it the same way the credential store masks secrets: first 3 characters
  plus length, e.g. `abc****(len=42)`.
- Never write the cleartext secret or the live session token into findings,
  logs, reports, commits, or this conversation beyond what's needed to perform
  the login itself.

### 4. Read-only authenticated requests only — against the operator's own account

- Safe/idempotent methods only: `GET`/`HEAD` and the application's own
  read-style endpoints (view, list, export-read, search). Anything that
  mutates server state is **not** a step here — it's a lead (see step 5).
- Always against the account just logged in — never another account's data,
  and never anyone else's session, as "proof" of anything.
- Show each request and a summary of its response as you go, so the operator
  can watch the walk happen.
- Record the mapped authenticated surface — endpoints, parameters, object
  references — to the engagement, for the operator to pick up from.

### 5. At the first exploitable lead — STOP

The instant something looks exploitable (an IDOR, a broken access check, a
leaked secret, anything that would need a write to confirm), **stop probing
it**. Do not chain deeper, pivot accounts, or escalate to prove more than the
read-only step already showed. Record it as a **candidate**, not a finding:

```bash
python3 workflow/bbwf.py finding add --name <eng> --status candidate \
  --title "<short description>" \
  --class idor --skills shilahunter-idor \
  --evidence "<sanitized request/response — no secrets, no session tokens>"
```

Name the applicable vulnerability-class skill in the finding (e.g.
`shilahunter-idor`, `shilahunter-business-logic`, `shilahunter-auth-bypass`)
so the operator knows which methodology to reproduce it with, then hand it off.
A flag is a lead, not a finding, and not permission to escalate.

**Under this skill there is no exception to:** no writes, no state changes
(profile edits, password resets, orders, messages, bulk registration), no
cross-account access used as proof, no bulk actions. Ever.

## Session Engines

### `curl` cookie-jar — API / simple-form hosts

Best for API-first backends or plain server-rendered login forms
(`attacker.com`/`target.com`-style hosts in this repo's placeholder
convention). Fully scriptable and visible in the transcript:

```bash
# login, store the session in a jar
curl -c jar.txt -b jar.txt -s -D - -o /dev/null \
  -d "username=$USER&password=$SECRET" \
  https://target.com/login

# subsequent authenticated, read-only requests reuse the jar
curl -b jar.txt -s https://target.com/api/me
curl -b jar.txt -s https://target.com/api/orders
```

Some forms require fetching a CSRF token with a prior `GET` before the login
`POST` will be accepted — grab it from the login page response first.

### `claude-in-chrome` — JS-heavy SPA portals

For selfcare-style single-page-app portals that build the session entirely
client-side, drive the login through the `claude-in-chrome` skill instead of
curl, so the operator watches the real tab as it happens. This requires the
browser extension installed and per-site permission granted by the operator
beforehand (one-time, operator-side setup). Once logged in, read the session
cookie/token out of the browser (devtools/storage) and mask it before showing
it, exactly as in step 3.

## Worked Shape (generic placeholder hosts)

1. `python3 workflow/bbwf.py scope check --name acme-eng https://target.com/login` → IN
2. `python3 workflow/bbwf.py creds get --name acme-eng acme-1 --field secret` → secret, in-memory only
3. Log in via curl jar (or `claude-in-chrome`) → session cookie shown as `abc****(len=42)`
4. Walk the surface: `GET /api/me`, `GET /api/orders`, `GET /api/account/settings`
   — scope-check any newly-seen host first, show each request + response
   summary, log each endpoint/param/object-ref found.
5. `GET /api/orders/1042` returns someone else's order when the ID is
   decremented → **STOP**. File it:
   `python3 workflow/bbwf.py finding add --name acme-eng --status candidate --title "Order IDOR via sequential order id" --class idor --skills shilahunter-idor --evidence "GET /api/orders/1042 as acme-1 returns a different account's order; sanitized response body attached, no cookie included"`
   referencing `shilahunter-idor`. Hand to the operator.

## Instructions for Claude

When this skill is active:

1. Treat the five-step contract above as mandatory, in order, every single
   time — not optional guidance to skim.
2. Before issuing any request, confirm the target host has already passed a
   scope check this session. If it hasn't, run the scope check yourself before
   sending anything — or refuse.
3. Load credentials exactly as in step 2. Refuse outright, before attempting
   any login, if the account is marked `manual_only`.
4. Keep every authenticated request read-only (`GET`/`HEAD`/read endpoints
   only) and narrate request + response as you go; record the surface.
5. The instant something looks exploitable, stop immediately, file a
   `candidate` finding with sanitized evidence (no secrets, no tokens) naming
   the applicable vulnerability-class skill, and hand off to the operator —
   do not continue probing, pivot accounts, or attempt to "confirm" further.
6. Never print, log, paste, or commit a cleartext secret or a live session
   token beyond the single login step in step 3 — always masked after that.

# Authenticated Session Driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Claude drive read-only, scope-gated, stop-at-leads authenticated sessions against in-scope targets, backed by a safe per-engagement credential store.

**Architecture:** A new storage-only module `workflow/creds.py` (`CredStore`) persists credentials at `<base>/<name>/creds.json` (`chmod 600`, outside the repo). A `creds` subcommand in `workflow/bbwf.py` wraps it, applying the engagement scope gate at add time. A new prose skill encodes the read-only/stop-at-leads operating contract. Scope and findings machinery are reused unchanged.

**Tech Stack:** Python 3 standard library only (no new dependencies). Tests use `unittest`, run from the repo root with `python3 -m unittest discover tests`.

**Spec:** `docs/superpowers/specs/2026-10-25-authenticated-session-driver-design.md`

## Global Constraints

- Python 3 **standard library only** — no new runtime or test dependencies (project is dependency-free).
- Credential data lives at `<base>/<name>/creds.json`, default base `~/.bb-engagements`, **outside this repo**; never committed.
- `creds.json` is written with mode `0o600`.
- Secrets are **masked** everywhere (`<first3>****(len=N)`) except the single path `creds get <id> --field secret`, which prints the cleartext and nothing else.
- Secrets are never echoed into findings, logs, reports, or git.
- TKB ebanking accounts are `manual_only: true` and the skill never drives them.
- Operator-led, read-only by default, no autonomous loop — the skill is the safety contract.

## Review Focus

- **Short/empty secret** (len ≤ 3): masking must not reveal the whole secret nor crash → Task 1 tests.
- **Duplicate account id** on `creds add`: must refuse, never silently overwrite (data loss) → Task 1 tests.
- **`creds get <unknown-id>`**: clean nonzero exit with a message, not a traceback → Task 2 tests.
- **File permissions**: `creds.json` must be `0o600` after save, even on re-save → Task 1 tests.
- **Out-of-scope host at `creds add`**: refused via the engagement scope gate → Task 2 tests.

---

### Task 1: `CredStore` storage module

**Files:**
- Create: `workflow/creds.py`
- Test: `tests/test_creds.py`

**Interfaces:**
- Consumes: nothing (stdlib `json`, `os`).
- Produces:
  - `mask_secret(secret: str) -> str` — `""`/≤3 chars → `"****"`; else `f"{secret[:3]}****(len={len(secret)})"`.
  - `REQUIRED_FIELDS = ("id", "host", "username")`; full account keys: `id, label, host, username, secret, note, manual_only`.
  - `class CredStore:`
    - `__init__(self, path: str)` — stores path; loads accounts from the file if it exists, else starts empty.
    - `accounts(self) -> list[dict]` — the stored accounts.
    - `add(self, account: dict) -> None` — fills missing optional keys with defaults (`label=""`, `secret=""`, `note=""`, `manual_only=False`); raises `ValueError` if a `REQUIRED_FIELDS` key is missing/empty or if `account["id"]` already exists; appends and calls `save()`.
    - `get(self, acct_id: str) -> dict | None`.
    - `remove(self, acct_id: str) -> bool` — removes by id, saves, returns whether anything was removed.
    - `save(self) -> None` — `json.dump` to `path` (indent=2), then `os.chmod(path, 0o600)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_creds.py`

Put the workflow dir on the path like the project does (`sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workflow"))`), use a `tempfile.TemporaryDirectory` for the store path.

```python
def test_mask_hides_all_but_first_three():
    assert creds.mask_secret("lpe85cbcnV1e30c") == "lpe****(len=15)"

def test_mask_short_secret_fully_hidden():
    assert creds.mask_secret("ab") == "****"
    assert creds.mask_secret("") == "****"

def test_add_then_get_roundtrip():
    s = creds.CredStore(path)
    s.add({"id": "sweez-1", "host": "my.sweez.ch", "username": "colt@example.com", "secret": "x"})
    assert s.get("sweez-1")["username"] == "colt@example.com"

def test_add_missing_required_field_raises():
    # no username
    with pytest_raises_ValueError: s.add({"id": "a", "host": "h"})

def test_add_duplicate_id_raises():
    s.add({"id": "a", "host": "h", "username": "u"})
    with pytest_raises_ValueError: s.add({"id": "a", "host": "h", "username": "u2"})

def test_saved_file_is_0600():
    s.add({"id": "a", "host": "h", "username": "u"})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

def test_remove_and_reload_persists():
    s.add({"id": "a", "host": "h", "username": "u"}); s.remove("a")
    assert creds.CredStore(path).get("a") is None
```

Use `self.assertRaises(ValueError)` / `self.assertEqual` in real `unittest` form.

- [ ] **Step 2: Run tests, verify they fail**

Run: `python3 -m unittest discover tests -v`
Expected: FAIL (module `creds` / attributes not defined).

- [ ] **Step 3: Implement `workflow/creds.py`** with the Interfaces above. `save()` writes then `os.chmod(..., 0o600)`; `__init__` tolerates a missing file (empty store) and a present one (load).

- [ ] **Step 4: Run tests, verify they pass**

Run: `python3 -m unittest discover tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add workflow/creds.py tests/test_creds.py
git commit -m "feat(workflow): add CredStore credential storage (0600, masked, CRUD)"
```

---

### Task 2: `creds` subcommand in `bbwf.py`

**Files:**
- Modify: `workflow/bbwf.py` (add `cmd_creds`, a `creds` subparser group near the other `sub.add_parser(...)` calls, and wire `set_defaults(fn=cmd_creds)`)
- Modify: `workflow/README.md` (document the `creds` verbs + where creds.json lives)
- Test: `tests/test_creds_cli.py`

**Interfaces:**
- Consumes: `CredStore`, `mask_secret` from Task 1; existing `_eng(args)`, `Engagement(args.base, args.name).dir` and `.scope` (with `scope.in_scope_host(host) -> bool`), and `main(argv)` for test invocation.
- Produces: `cmd_creds(args)` dispatching on `args.creds_cmd` ∈ {`add`,`list`,`get`,`rm`}; the store path is `os.path.join(eng.dir, "creds.json")`.

Behavior per subcommand:
- `add` — required `--id --host --user`; secret from `--secret` or `--secret-stdin` (read `sys.stdin.read().strip()`); optional `--label --note --manual-only`. **Scope gate:** if `eng.scope.in_scope_host(args.host)` is False, print an OUT-OF-SCOPE refusal and `sys.exit(2)` — no write. Else build the account dict, `store.add(...)`, print confirmation with the secret masked.
- `list` — print one row per account: `id`, `host`, `username`, `manual_only`, and `mask_secret(secret)`. Never the cleartext.
- `get <id> [--field user|host|secret]` — default field `secret`. If the id is unknown, print an error and `sys.exit(2)` (no traceback). Print only the requested field's value.
- `rm <id>` — `store.remove`; print `✓ removed` / `(no such id)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_creds_cli.py`

Create an engagement in a temp base first (`main(["init","--name","t","--base",base,"--in","my.sweez.ch"])`), capture stdout with `contextlib.redirect_stdout`, and assert via `main([...])`. For exits, wrap in `self.assertRaises(SystemExit)` and check `.code`.

```python
def test_add_in_scope_then_list_masks_secret():
    main(["creds","add","--name","t","--base",base,"--id","s1",
          "--host","my.sweez.ch","--user","colt@example.com","--secret","lpe85cbcnV1e30c"])
    out = capture(main, ["creds","list","--name","t","--base",base])
    assert "lpe****(len=15)" in out and "lpe85cbcnV1e30c" not in out

def test_add_out_of_scope_host_refused():
    with assertRaises(SystemExit) as e:
        main(["creds","add","--name","t","--base",base,"--id","bad",
              "--host","evil.com","--user","u","--secret","x"])
    assert e.code == 2
    # and nothing persisted: creds list has no 'bad'

def test_get_secret_prints_cleartext_only():
    out = capture(main, ["creds","get","--name","t","--base",base,"s1","--field","secret"])
    assert out.strip() == "lpe85cbcnV1e30c"

def test_get_unknown_id_exits_2_no_traceback():
    with assertRaises(SystemExit) as e:
        main(["creds","get","--name","t","--base",base,"nope"])
    assert e.code == 2

def test_secret_stdin():
    # with unittest.mock.patch("sys.stdin", io.StringIO("topsecret\n")):
    #   main(["creds","add",...,"--secret-stdin"]) ; then assert via get --field secret
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python3 -m unittest discover tests -v`
Expected: FAIL (`invalid choice: 'creds'`).

- [ ] **Step 3: Implement `cmd_creds` + the `creds` subparser** in `workflow/bbwf.py`, following the `cmd_scope` group pattern (sub-subparsers, `set_defaults(fn=cmd_creds)`). Then add a `## Credential store` section to `workflow/README.md` documenting the four verbs, `--secret-stdin`, masking, and that `creds.json` lives under `~/.bb-engagements/<name>/` (never committed).

- [ ] **Step 4: Run tests, verify they pass**

Run: `python3 -m unittest discover tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add workflow/bbwf.py workflow/README.md tests/test_creds_cli.py
git commit -m "feat(workflow): add scope-gated 'creds' subcommand (add/list/get/rm)"
```

---

### Task 3: `shilahunter-authenticated-session` skill + README

**Files:**
- Create: `Skills/web/shilahunter-authenticated-session/SKILL.md`
- Modify: `README.md` (add the skill to the web table; bump the web count 30 → 31 and any header total)

**Interfaces:**
- Consumes: nothing executable. References the scope gate (`bbwf.py scope check`), `bbwf.py finding add --status candidate`, and the credential store (`creds get --field secret`).
- Produces: a prose methodology skill, same shape as existing `SKILL.md` files (Metadata, Description, Trigger Phrases, Instructions for Claude, Full Methodology).

Content must encode the **safety contract** verbatim from the spec:
1. Scope-check the login URL and every follow-up host; out-of-scope ⇒ refuse.
2. Load one account at a time (`creds get`), respect one-session / don't-lock; never drive a `manual_only` account.
3. Log in, capture session cookie/token, show it masked.
4. Read-only authenticated requests against the operator's own account; show each request + response; record surface.
5. At the first exploitable lead, **STOP** → `finding add --status candidate` with sanitized evidence (no secrets/tokens) + the applicable skill name; hand to the operator. No writes, state changes, cross-account access, or bulk actions.
Engines: `curl` cookie-jar for API/simple hosts; `claude-in-chrome` for SPA portals.
Trigger phrases: `authenticated session, log in, test account, credentialed testing, logged-in surface, session cookie, authenticated IDOR`.

- [ ] **Step 1: Write `SKILL.md`** with the sections and the five-step contract above.

- [ ] **Step 2: Verify install picks it up** (install.sh copies every `SKILL.md`)

Run: `bash install.sh --no-shila >/dev/null && test -f ~/.claude/skills/web/shilahunter-authenticated-session/SKILL.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Update `README.md`** — add the row to the web table and correct the web count (30 → 31) and the headline total if it names one.

- [ ] **Step 4: Verify counts match reality**

Run: `find Skills -name SKILL.md | wc -l` and confirm the README's total matches.
Expected: the printed number equals the README total.

- [ ] **Step 5: Commit**

```bash
git add Skills/web/shilahunter-authenticated-session/SKILL.md README.md
git commit -m "feat(skills): add shilahunter-authenticated-session (read-only, stop-at-leads)"
```

---

## Notes for the executor

- Run everything from the repo root. Tests create engagements under a `tempfile` base, never `~/.bb-engagements`.
- Do not commit any real credentials or `creds.json`. Only the test fixtures (fake `@example.com` accounts) appear in the repo.
- Git: if on `main`, create a branch (e.g. `feat/auth-session-driver`) before the first commit.

# Attribution

This repository bundles skills from two upstream projects. The two bodies of
content are under **different licenses** — keep them distinct.

## 1. SnailSploit/claude-red — MIT

The original 25 `offensive-*` skills (the `web`, `api`, `auth`, `recon`,
`cloud`, and `utility` category skills prefixed `offensive-`) are a curated
subset of [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red),
redistributed under the MIT License. See [`LICENSE`](./LICENSE). Copyright
remains with the original authors (SnailSploit / Kai Aizen).

## 2. elementalsouls/Claude-BugHunter — CC BY 4.0

The `hunt-*` skills, plus the upgraded `recon/offensive-osint-methodology`
skill, are sourced from
[elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter)
by **Sachin Sharma (elementalsouls)**.

- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0) —
  <https://creativecommons.org/licenses/by/4.0/>
- **Attribution:** "Claude-BugHunter" by Sachin Sharma (elementalsouls),
  <https://github.com/elementalsouls/Claude-BugHunter>, used under CC BY 4.0.
- **Changes made:** the `SKILL.md` files were copied **unmodified** and
  reorganized into this repo's `Skills/<category>/<name>/` layout. The
  `recon/offensive-osint-methodology/SKILL.md` file's contents were **replaced**
  with Claude-BugHunter's `osint-methodology` skill (its folder name was kept).
  No other content was altered.
- **Upstream note:** Claude-BugHunter is itself a bundle that vendors some
  community-contributed and upstream skills (e.g. `shuvonsec/claude-bug-bounty`,
  MIT) in addition to the author's original work. See that project's
  [`docs/credits.md`](https://github.com/elementalsouls/Claude-BugHunter/blob/main/docs/credits.md)
  for its own full attribution breakdown.

### Skills sourced from Claude-BugHunter (CC BY 4.0)

**web:** hunt-cache-poison, hunt-clickjacking, hunt-cors, hunt-csrf, hunt-dom,
hunt-host-header, hunt-html-injection, hunt-ldap, hunt-lfi, hunt-nosqli,
hunt-source-leak, hunt-websocket, hunt-exceptional-conditions, hunt-misc

**api:** hunt-api-misconfig, hunt-grpc, hunt-shadow-api, hunt-spa-api,
hunt-fintech-graphql

**auth:** hunt-ato, hunt-auth-bypass, hunt-brute-force, hunt-captcha-bypass,
hunt-forgot-password, hunt-mfa-bypass, hunt-saml, hunt-session

**recon:** hunt-subdomain, hunt-tls-network, offensive-osint-methodology
*(upgraded — content replaced with Claude-BugHunter's `osint-methodology`)*

**ai:** hunt-llm-ai, hunt-rag-vector

**framework:** hunt-aspnet, hunt-laravel, hunt-nextjs, hunt-nodejs,
hunt-springboot

**cloud:** hunt-cloud-misconfig, hunt-k8s, hunt-cicd

## 3. workflow/ toolkit — original, with design credit

The `workflow/` toolkit (`bbwf.py`, `scope.py`, `phases.py`, `state.py`) is
original work for this repository. Its **scope model** (deny-wins, default-deny;
apex / `*.wildcard` / exact-host / CIDR / `re:` regex matching) is a clean
reimplementation of the approach in elementalsouls/Claude-BugHunter's engine
(`engine/scope.py`), whose **code** is MIT-licensed (distinct from that
project's CC BY 4.0 skill content). No code was copied verbatim; the design is
credited here under MIT.

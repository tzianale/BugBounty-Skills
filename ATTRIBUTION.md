# Attribution

This repository bundles skills from two upstream projects, under **different
licenses**. All skill folders and frontmatter names have been renamed with a
`shilahunter-` prefix for a consistent theme; this renaming is the only change to
most skills, and **original authorship is unchanged**. Because the license can no
longer be inferred from a skill's name, the exact per-license lists are below.

## 1. SnailSploit/claude-red — MIT (24 skills)

Sourced from [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red),
redistributed under the MIT License (see [`LICENSE`](./LICENSE)). Copyright remains
with the original authors (SnailSploit / Kai Aizen). Change made: renamed with the
`shilahunter-` prefix (folder + frontmatter) and reorganized under
`Skills/<category>/`; skill content otherwise unmodified.

**api:** shilahunter-api-abuse, shilahunter-api-security

**auth:** shilahunter-jwt, shilahunter-oauth

**cloud:** shilahunter-cloud

**recon:** shilahunter-osint

**utility:** shilahunter-fast-checking, shilahunter-reporting

**web:** shilahunter-business-logic, shilahunter-deserialization, shilahunter-file-upload, shilahunter-graphql, shilahunter-idor, shilahunter-open-redirect, shilahunter-parameter-pollution, shilahunter-race-condition, shilahunter-rce, shilahunter-request-smuggling, shilahunter-sqli, shilahunter-ssrf, shilahunter-ssti, shilahunter-waf-bypass, shilahunter-xss, shilahunter-xxe

## 2. elementalsouls/Claude-BugHunter — CC BY 4.0 (40 skills)

Sourced from [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter)
by **Sachin Sharma (elementalsouls)**.

- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0) —
  <https://creativecommons.org/licenses/by/4.0/>
- **Attribution:** "Claude-BugHunter" by Sachin Sharma (elementalsouls),
  <https://github.com/elementalsouls/Claude-BugHunter>, used under CC BY 4.0.
- **Changes made:** `SKILL.md` files reorganized into this repo's
  `Skills/<category>/` layout and renamed with the `shilahunter-` prefix (folder +
  frontmatter name). `shilahunter-osint-methodology`'s contents are
  Claude-BugHunter's `osint-methodology` skill (it replaced the earlier
  claude-red methodology file). Skill content is otherwise unmodified.
- **Upstream note:** Claude-BugHunter is itself a bundle that vendors some
  community/upstream skills (e.g. `shuvonsec/claude-bug-bounty`, MIT) alongside the
  author's original work. See that project's
  [`docs/credits.md`](https://github.com/elementalsouls/Claude-BugHunter/blob/main/docs/credits.md)
  for its own full attribution breakdown.

**ai:** shilahunter-llm-ai, shilahunter-rag-vector

**api:** shilahunter-api-misconfig, shilahunter-fintech-graphql, shilahunter-grpc, shilahunter-shadow-api, shilahunter-spa-api

**auth:** shilahunter-ato, shilahunter-auth-bypass, shilahunter-brute-force, shilahunter-captcha-bypass, shilahunter-forgot-password, shilahunter-mfa-bypass, shilahunter-saml, shilahunter-session

**cloud:** shilahunter-cicd, shilahunter-cloud-misconfig, shilahunter-k8s

**framework:** shilahunter-aspnet, shilahunter-laravel, shilahunter-nextjs, shilahunter-nodejs, shilahunter-springboot

**recon:** shilahunter-osint-methodology, shilahunter-subdomain, shilahunter-tls-network

**web:** shilahunter-cache-poison, shilahunter-clickjacking, shilahunter-cors, shilahunter-csrf, shilahunter-dom, shilahunter-exceptional-conditions, shilahunter-host-header, shilahunter-html-injection, shilahunter-ldap, shilahunter-lfi, shilahunter-misc, shilahunter-nosqli, shilahunter-source-leak, shilahunter-websocket

## 3. workflow/ toolkit — original, with design credit

The `workflow/` toolkit (`bbwf.py`, `scope.py`, `phases.py`, `state.py`,
`recon.py`, `dashboard.py`, `templates.py`) is original work for this repository.
Its **scope model** (deny-wins, default-deny; apex / `*.wildcard` / exact-host /
CIDR / `re:` regex matching) is a clean reimplementation of the approach in
elementalsouls/Claude-BugHunter's engine (`engine/scope.py`), whose **code** is
MIT-licensed (distinct from that project's CC BY 4.0 skill content). No code was
copied verbatim; the design is credited here under MIT.

# shila-hunt-bugs

A curated, private collection of **64 bug-bounty-focused Claude skills**, drawn
from two upstream projects and organized as `Skills/<category>/<name>/SKILL.md`:

- **24 skills** from [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red) — MIT
- **40 skills** from [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) — CC BY 4.0 (incl. the upgraded osint-methodology)

All skills are renamed with the `shilahunter-` prefix; original authorship is unchanged.

See [`ATTRIBUTION.md`](./ATTRIBUTION.md) for exact provenance and license terms —
the two sets are under **different licenses**.

> **Scope / ethics.** These skills are for **authorized bug bounty engagements
> and security research only** — only against targets you have explicit, written
> permission to test (an in-scope bug bounty program or a signed engagement).
> All example payloads use placeholder hosts such as `attacker.com` / `target.com`;
> replace them with your own authorized infrastructure. Do not use these
> techniques against systems you are not authorized to test.

## Install

```bash
./install.sh
```

This does two things:
1. copies every `Skills/<category>/<name>/` folder into `~/.claude/skills/` — the
   skills then auto-load by topic (describe what you're testing in plain English);
2. links the **`shila`** workflow launcher onto your PATH (`~/.local/bin` by
   default) so you can run `shila hunt …`, `shila show dashboard`, etc.

Re-run any time to refresh (idempotent). Flags/env: `--no-shila` (skills only),
`CLAUDE_SKILLS_DIR=/path` (custom skills dir), `SHILA_BIN_DIR=/path` (custom
launcher dir). `shila` needs `python3` at runtime.

```bash
shila help
shila hunt acme acme.com      # start a session, scope it, show the recon plan
```

## Workflow toolkit (`workflow/`)

Beyond the skills, `workflow/bbwf.py` is a small, dependency-free, **operator-driven**
engagement runner — a phase plan + a findings store + a scope manager. It does
**not** test anything or call a model; you drive the phases and the skills above
do the hunting. See [`workflow/README.md`](./workflow/README.md).

```bash
python3 workflow/bbwf.py init  --name acme --in acme.com --out admin.acme.com --seed https://acme.com
python3 workflow/bbwf.py scope check --name acme https://api.acme.com   # deny-wins, default-deny
python3 workflow/bbwf.py plan                                           # the phase plan
python3 workflow/bbwf.py finding add --name acme --title ... --class idor --sev high --target ...
python3 workflow/bbwf.py report --name acme
```

Phases: `scope → recon → map → hunt → triage → report`, with return edges back
to earlier phases. Engagement data is stored under `~/.bb-engagements/` (outside
this repo), so live findings are never committed.

## Skills by category

### web (30)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-business-logic` | Business-logic flaws and workflow abuse | claude-red |
| `shilahunter-deserialization` | Insecure deserialization (Java, PHP, .NET) | claude-red |
| `shilahunter-file-upload` | Malicious / unrestricted file upload | claude-red |
| `shilahunter-graphql` | GraphQL introspection, batching, injection | claude-red |
| `shilahunter-idor` | Insecure direct object references / BOLA | claude-red |
| `shilahunter-open-redirect` | Open redirect discovery and chaining | claude-red |
| `shilahunter-parameter-pollution` | HTTP parameter pollution (HPP) | claude-red |
| `shilahunter-race-condition` | Race conditions via parallel requests | claude-red |
| `shilahunter-rce` | Remote code execution techniques | claude-red |
| `shilahunter-request-smuggling` | HTTP request smuggling / desync | claude-red |
| `shilahunter-sqli` | SQL injection | claude-red |
| `shilahunter-ssrf` | Server-side request forgery (+ cloud metadata) | claude-red |
| `shilahunter-ssti` | Server-side template injection | claude-red |
| `shilahunter-waf-bypass` | WAF / filter evasion | claude-red |
| `shilahunter-xss` | Cross-site scripting | claude-red |
| `shilahunter-xxe` | XML external entity injection | claude-red |
| `shilahunter-cache-poison` | Web cache poisoning / deception | BugHunter |
| `shilahunter-clickjacking` | Clickjacking / UI redress | BugHunter |
| `shilahunter-cors` | CORS misconfiguration | BugHunter |
| `shilahunter-csrf` | Cross-site request forgery | BugHunter |
| `shilahunter-dom` | DOM-based client-side vulnerabilities | BugHunter |
| `shilahunter-host-header` | Host-header injection / routing abuse | BugHunter |
| `shilahunter-html-injection` | HTML injection / dangling markup | BugHunter |
| `shilahunter-ldap` | LDAP injection | BugHunter |
| `shilahunter-lfi` | Local file inclusion / path traversal | BugHunter |
| `shilahunter-nosqli` | NoSQL operator injection (Mongo/Couch) | BugHunter |
| `shilahunter-source-leak` | Source-code / secret leakage | BugHunter |
| `shilahunter-websocket` | WebSocket security testing | BugHunter |
| `shilahunter-exceptional-conditions` | Verbose errors / fail-open info disclosure | BugHunter |
| `shilahunter-misc` | Misc web classes (CRLF, invite/verif bypass, …) | BugHunter |

### api (7)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-api-abuse` | API business-logic abuse and chaining | claude-red |
| `shilahunter-api-security` | API security testing methodology | claude-red |
| `shilahunter-api-misconfig` | API misconfiguration | BugHunter |
| `shilahunter-grpc` | gRPC API testing | BugHunter |
| `shilahunter-shadow-api` | Shadow / undocumented API discovery | BugHunter |
| `shilahunter-spa-api` | SPA-backend API attack surface | BugHunter |
| `shilahunter-fintech-graphql` | Fintech GraphQL (money-movement, ledger IDOR) | BugHunter |

### auth (10)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-jwt` | JWT attacks (alg confusion, kid/jku, tampering) | claude-red |
| `shilahunter-oauth` | OAuth / OIDC flow abuse | claude-red |
| `shilahunter-ato` | Account takeover chains | BugHunter |
| `shilahunter-auth-bypass` | Authentication bypass | BugHunter |
| `shilahunter-brute-force` | Credential brute-force / rate-limit gaps | BugHunter |
| `shilahunter-captcha-bypass` | CAPTCHA bypass | BugHunter |
| `shilahunter-forgot-password` | Password-reset flow flaws | BugHunter |
| `shilahunter-mfa-bypass` | MFA bypass | BugHunter |
| `shilahunter-saml` | SAML attacks | BugHunter |
| `shilahunter-session` | Session management flaws | BugHunter |

### recon (4)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-osint` | OSINT tooling and sources | claude-red |
| `shilahunter-osint-methodology` | **Upgraded:** 5-stage external-recon pipeline | BugHunter |
| `shilahunter-subdomain` | Subdomain enumeration / takeover | BugHunter |
| `shilahunter-tls-network` | TLS / network-layer issues | BugHunter |

### cloud (4)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-cloud` | AWS / Azure / GCP attack methodology | claude-red |
| `shilahunter-cloud-misconfig` | Cloud misconfiguration | BugHunter |
| `shilahunter-k8s` | Kubernetes attack surface | BugHunter |
| `shilahunter-cicd` | CI/CD pipeline attacks | BugHunter |

### ai (2)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-llm-ai` | LLM/AI bugs — prompt injection, tool-use exfil | BugHunter |
| `shilahunter-rag-vector` | RAG / vector-store attacks | BugHunter |

### framework (5)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-aspnet` | ASP.NET-specific issues | BugHunter |
| `shilahunter-laravel` | Laravel-specific issues | BugHunter |
| `shilahunter-nextjs` | Next.js-specific issues | BugHunter |
| `shilahunter-nodejs` | Node.js-specific issues | BugHunter |
| `shilahunter-springboot` | Spring Boot-specific issues | BugHunter |

### utility (2)
| Skill | Focus | Source |
|-------|-------|--------|
| `shilahunter-fast-checking` | Fast triage / quick vulnerability checks | claude-red |
| `shilahunter-reporting` | Writing up findings and reports | claude-red |

## Attribution & license

Dual-provenance, **two licenses**:

- Skills sourced from [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red) — **MIT** (see [`LICENSE`](./LICENSE)); listed in [`ATTRIBUTION.md`](./ATTRIBUTION.md).
- Skills sourced from [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) by Sachin Sharma — **CC BY 4.0**; listed in [`ATTRIBUTION.md`](./ATTRIBUTION.md).

Full details, the list of CC-BY skills, and the changes made are in
[`ATTRIBUTION.md`](./ATTRIBUTION.md).

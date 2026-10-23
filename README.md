# bugbounty-skills

A curated, private collection of **64 bug-bounty-focused Claude skills**, drawn
from two upstream projects and organized as `Skills/<category>/<name>/SKILL.md`:

- **25 `offensive-*` skills** from [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red) (MIT)
- **39 `hunt-*` skills** (plus an upgraded OSINT-methodology skill) from [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) (CC BY 4.0)

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

Copies every `Skills/<category>/<name>/` folder into `~/.claude/skills/`. Skills
auto-load by topic — describe what you're testing in plain English. Re-run any
time to refresh. Honors `CLAUDE_SKILLS_DIR` to install elsewhere.

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
| `offensive-business-logic` | Business-logic flaws and workflow abuse | claude-red |
| `offensive-deserialization` | Insecure deserialization (Java, PHP, .NET) | claude-red |
| `offensive-file-upload` | Malicious / unrestricted file upload | claude-red |
| `offensive-graphql` | GraphQL introspection, batching, injection | claude-red |
| `offensive-idor` | Insecure direct object references / BOLA | claude-red |
| `offensive-open-redirect` | Open redirect discovery and chaining | claude-red |
| `offensive-parameter-pollution` | HTTP parameter pollution (HPP) | claude-red |
| `offensive-race-condition` | Race conditions via parallel requests | claude-red |
| `offensive-rce` | Remote code execution techniques | claude-red |
| `offensive-request-smuggling` | HTTP request smuggling / desync | claude-red |
| `offensive-sqli` | SQL injection | claude-red |
| `offensive-ssrf` | Server-side request forgery (+ cloud metadata) | claude-red |
| `offensive-ssti` | Server-side template injection | claude-red |
| `offensive-waf-bypass` | WAF / filter evasion | claude-red |
| `offensive-xss` | Cross-site scripting | claude-red |
| `offensive-xxe` | XML external entity injection | claude-red |
| `hunt-cache-poison` | Web cache poisoning / deception | BugHunter |
| `hunt-clickjacking` | Clickjacking / UI redress | BugHunter |
| `hunt-cors` | CORS misconfiguration | BugHunter |
| `hunt-csrf` | Cross-site request forgery | BugHunter |
| `hunt-dom` | DOM-based client-side vulnerabilities | BugHunter |
| `hunt-host-header` | Host-header injection / routing abuse | BugHunter |
| `hunt-html-injection` | HTML injection / dangling markup | BugHunter |
| `hunt-ldap` | LDAP injection | BugHunter |
| `hunt-lfi` | Local file inclusion / path traversal | BugHunter |
| `hunt-nosqli` | NoSQL operator injection (Mongo/Couch) | BugHunter |
| `hunt-source-leak` | Source-code / secret leakage | BugHunter |
| `hunt-websocket` | WebSocket security testing | BugHunter |
| `hunt-exceptional-conditions` | Verbose errors / fail-open info disclosure | BugHunter |
| `hunt-misc` | Misc web classes (CRLF, invite/verif bypass, …) | BugHunter |

### api (7)
| Skill | Focus | Source |
|-------|-------|--------|
| `offensive-api-abuse` | API business-logic abuse and chaining | claude-red |
| `offensive-api-security` | API security testing methodology | claude-red |
| `hunt-api-misconfig` | API misconfiguration | BugHunter |
| `hunt-grpc` | gRPC API testing | BugHunter |
| `hunt-shadow-api` | Shadow / undocumented API discovery | BugHunter |
| `hunt-spa-api` | SPA-backend API attack surface | BugHunter |
| `hunt-fintech-graphql` | Fintech GraphQL (money-movement, ledger IDOR) | BugHunter |

### auth (10)
| Skill | Focus | Source |
|-------|-------|--------|
| `offensive-jwt` | JWT attacks (alg confusion, kid/jku, tampering) | claude-red |
| `offensive-oauth` | OAuth / OIDC flow abuse | claude-red |
| `hunt-ato` | Account takeover chains | BugHunter |
| `hunt-auth-bypass` | Authentication bypass | BugHunter |
| `hunt-brute-force` | Credential brute-force / rate-limit gaps | BugHunter |
| `hunt-captcha-bypass` | CAPTCHA bypass | BugHunter |
| `hunt-forgot-password` | Password-reset flow flaws | BugHunter |
| `hunt-mfa-bypass` | MFA bypass | BugHunter |
| `hunt-saml` | SAML attacks | BugHunter |
| `hunt-session` | Session management flaws | BugHunter |

### recon (4)
| Skill | Focus | Source |
|-------|-------|--------|
| `offensive-osint` | OSINT tooling and sources | claude-red |
| `offensive-osint-methodology` | **Upgraded:** 5-stage external-recon pipeline | BugHunter |
| `hunt-subdomain` | Subdomain enumeration / takeover | BugHunter |
| `hunt-tls-network` | TLS / network-layer issues | BugHunter |

### cloud (4)
| Skill | Focus | Source |
|-------|-------|--------|
| `offensive-cloud` | AWS / Azure / GCP attack methodology | claude-red |
| `hunt-cloud-misconfig` | Cloud misconfiguration | BugHunter |
| `hunt-k8s` | Kubernetes attack surface | BugHunter |
| `hunt-cicd` | CI/CD pipeline attacks | BugHunter |

### ai (2)
| Skill | Focus | Source |
|-------|-------|--------|
| `hunt-llm-ai` | LLM/AI bugs — prompt injection, tool-use exfil | BugHunter |
| `hunt-rag-vector` | RAG / vector-store attacks | BugHunter |

### framework (5)
| Skill | Focus | Source |
|-------|-------|--------|
| `hunt-aspnet` | ASP.NET-specific issues | BugHunter |
| `hunt-laravel` | Laravel-specific issues | BugHunter |
| `hunt-nextjs` | Next.js-specific issues | BugHunter |
| `hunt-nodejs` | Node.js-specific issues | BugHunter |
| `hunt-springboot` | Spring Boot-specific issues | BugHunter |

### utility (2)
| Skill | Focus | Source |
|-------|-------|--------|
| `offensive-fast-checking` | Fast triage / quick vulnerability checks | claude-red |
| `offensive-reporting` | Writing up findings and reports | claude-red |

## Attribution & license

Dual-provenance, **two licenses**:

- `offensive-*` skills → [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red), **MIT** (see [`LICENSE`](./LICENSE)).
- `hunt-*` skills + upgraded `offensive-osint-methodology` → [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) by Sachin Sharma, **CC BY 4.0**.

Full details, the list of CC-BY skills, and the changes made are in
[`ATTRIBUTION.md`](./ATTRIBUTION.md).

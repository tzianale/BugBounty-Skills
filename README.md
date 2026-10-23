# bugbounty-skills

A curated, private collection of **25 bug-bounty-focused Claude skills**, selected
from the public [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red)
project and redistributed under its MIT license.

Each skill is a single `SKILL.md` describing an offensive web-security testing
methodology, laid out as `Skills/<category>/<name>/SKILL.md`. This subset covers
the categories most relevant to web/API bug bounty work: **web, api, auth, recon,
cloud, and utility**.

> **Scope / ethics.** These skills are for **authorized bug bounty engagements
> and security research only** — only against targets you have explicit, written
> permission to test (an in-scope bug bounty program or a signed engagement).
> All example payloads use placeholder hosts such as `attacker.com` / `target.com`;
> replace them with your own authorized infrastructure. Do not use these
> techniques against systems you are not authorized to test.

## Install

Copy the skills into your personal Claude skills directory:

```bash
./install.sh
```

This copies every `Skills/<category>/<name>/` folder into `~/.claude/skills/`.
Re-run it any time to refresh. See the script for details.

## Skills by category

### web (16)
| Skill | Focus |
|-------|-------|
| `offensive-business-logic` | Business-logic flaws and workflow abuse |
| `offensive-deserialization` | Insecure deserialization (Java, PHP, .NET, etc.) |
| `offensive-file-upload` | Malicious / unrestricted file upload |
| `offensive-graphql` | GraphQL introspection, batching, injection abuse |
| `offensive-idor` | Insecure direct object references / broken access control |
| `offensive-open-redirect` | Open redirect discovery and chaining |
| `offensive-parameter-pollution` | HTTP parameter pollution (HPP) |
| `offensive-race-condition` | Race conditions via parallel requests |
| `offensive-rce` | Remote code execution techniques |
| `offensive-request-smuggling` | HTTP request smuggling / desync |
| `offensive-sqli` | SQL injection |
| `offensive-ssrf` | Server-side request forgery (incl. cloud metadata) |
| `offensive-ssti` | Server-side template injection |
| `offensive-waf-bypass` | WAF / filter evasion |
| `offensive-xss` | Cross-site scripting |
| `offensive-xxe` | XML external entity injection |

### api (2)
| Skill | Focus |
|-------|-------|
| `offensive-api-abuse` | API business-logic abuse and attack chaining |
| `offensive-api-security` | API security testing methodology |

### auth (2)
| Skill | Focus |
|-------|-------|
| `offensive-jwt` | JWT attacks (alg confusion, kid/jku injection, tampering) |
| `offensive-oauth` | OAuth / OIDC flow abuse |

### recon (2)
| Skill | Focus |
|-------|-------|
| `offensive-osint` | OSINT tooling and sources |
| `offensive-osint-methodology` | Structured OSINT reconnaissance methodology |

### cloud (1)
| Skill | Focus |
|-------|-------|
| `offensive-cloud` | AWS / Azure / GCP attack methodology |

### utility (2)
| Skill | Focus |
|-------|-------|
| `offensive-fast-checking` | Fast triage / quick vulnerability checks |
| `offensive-reporting` | Writing up findings and reports |

## Attribution & license

This is a **curated subset** of [SnailSploit/claude-red](https://github.com/SnailSploit/claude-red),
redistributed **unmodified** under the MIT License. All copyright remains with the
original authors (SnailSploit / Kai Aizen). See [`LICENSE`](./LICENSE) for the full
text and the redistribution note. No upstream workflows, tooling, or other
categories are included.

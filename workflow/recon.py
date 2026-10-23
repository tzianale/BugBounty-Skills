#!/usr/bin/env python3
"""
recon.py — operator-invoked, scope-gated reconnaissance.

This RUNS external recon tools and records what they find. It is reconnaissance
only — surface discovery, liveness, tech fingerprint, endpoint/param mining. It
does NOT test for, probe, or exploit vulnerabilities. You run it; it hands you a
mapped surface; you decide what to test.

Hard rule enforced here: every host is filtered through the engagement's scope
BEFORE any active request is sent to it. Discovered hosts that aren't in scope
are dropped and never probed. Passive sources (crt.sh, gau) query third-party
data about a domain; active tools (httpx, katana) send requests and are only
ever pointed at in-scope hosts.

Tools are optional and auto-detected; missing ones are skipped with a note.
  passive enum : subfinder, assetfinder, crt.sh (via curl)
  liveness/tech: httpx
  endpoints    : gau (passive history), katana (active crawl, in-scope only)

Nothing runs with shell=True; hosts are passed as argv and validated first.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from urllib.parse import urlparse, parse_qsl

_HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _valid_host(h: str) -> bool:
    return bool(h) and bool(_HOST_RE.match(h)) and "." in h


def _run(cmd, timeout, stdin_data=None):
    """Run argv list, return stdout text ('' on any failure). Never shell=True."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           input=stdin_data)
        return p.stdout or ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def derive_apexes(scope, seeds):
    """Apex domains to enumerate: from bare in-scope patterns + seed hosts.
    Skips wild<card>/CIDR/regex forms (can't enumerate those) and keeps the
    registrable-ish apex (last two labels)."""
    apexes = set()
    cand = []
    for p in scope.in_scope:
        p = p.strip().lower()
        if p.startswith(("re:",)) or "/" in p:
            continue
        cand.append(p[2:] if p.startswith("*.") else p)
    for s in seeds:
        h = urlparse(s if "://" in s else "//" + s).hostname or ""
        if h:
            cand.append(h.lower())
    for h in cand:
        if _valid_host(h):
            apexes.add(".".join(h.split(".")[-2:]))
    return sorted(apexes)


# ---------------- passive subdomain enumeration ----------------
def passive_enum(apexes, timeout, log, dry=False):
    hosts = set()
    for apex in apexes:
        if _have("subfinder"):
            cmd = ["subfinder", "-silent", "-d", apex]
            log(f"  [subfinder] {' '.join(cmd)}")
            if not dry:
                hosts |= {l.strip().lower() for l in _run(cmd, timeout).splitlines() if l.strip()}
        if _have("assetfinder"):
            cmd = ["assetfinder", "--subs-only", apex]
            log(f"  [assetfinder] {' '.join(cmd)}")
            if not dry:
                hosts |= {l.strip().lower() for l in _run(cmd, timeout).splitlines() if l.strip()}
        if _have("curl"):
            # crt.sh certificate-transparency search
            cmd = ["curl", "-s", "--max-time", str(timeout),
                   f"https://crt.sh/?q=%25.{apex}&output=json"]
            log(f"  [crt.sh] {' '.join(cmd)}")
            if not dry:
                out = _run(cmd, timeout + 5)
                try:
                    for row in json.loads(out):
                        for name in str(row.get("name_value", "")).splitlines():
                            name = name.strip().lstrip("*.").lower()
                            if name:
                                hosts.add(name)
                except ValueError:
                    pass
    return {h for h in hosts if _valid_host(h)}


# ---------------- liveness + tech (active; in-scope only) ----------------
def httpx_probe(hosts, timeout, log, dry=False):
    targets = []
    if not hosts:
        return targets
    if not _have("httpx"):
        log("  [httpx] not installed — skipping liveness/tech (recording hosts as unprobed)")
        return [{"host": h, "url": "", "status": None, "tech": []} for h in sorted(hosts)]
    cmd = ["httpx", "-silent", "-json", "-td", "-timeout", str(min(timeout, 15))]
    log(f"  [httpx] {' '.join(cmd)}  (<- {len(hosts)} in-scope host(s) on stdin)")
    if dry:
        return targets
    out = _run(cmd, timeout * 3, stdin_data="\n".join(sorted(hosts)) + "\n")
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        url = d.get("url", "")
        host = (urlparse(url).hostname or d.get("input", "")).lower()
        tech = d.get("tech") or d.get("technologies") or []
        if isinstance(tech, str):
            tech = [tech]
        targets.append({"host": host, "url": url,
                        "status": d.get("status_code") or d.get("status-code"),
                        "tech": tech})
    return targets


# ---------------- endpoint / param mining ----------------
def mine_endpoints(live_urls, scope, timeout, log, crawl=False, dry=False):
    endpoints = {}

    def _add(u, src):
        pu = urlparse(u)
        host = (pu.hostname or "").lower()
        if not _valid_host(host) or not scope.in_scope_host(host):
            return
        params = sorted({k for k, _ in parse_qsl(pu.query)})
        key = f"{pu.scheme}://{pu.netloc}{pu.path}"
        e = endpoints.setdefault(key, {"url": key, "params": set(), "sources": set()})
        e["params"] |= set(params)
        e["sources"].add(src)

    hosts = sorted({(urlparse(u).hostname or "").lower() for u in live_urls if u})
    for host in hosts:
        if _have("gau"):
            cmd = ["gau", "--subs", host]
            log(f"  [gau] {' '.join(cmd)}")
            if not dry:
                for u in _run(cmd, timeout).splitlines():
                    _add(u.strip(), "gau")
    if crawl:
        for u in live_urls:
            if _have("katana"):
                cmd = ["katana", "-silent", "-u", u]
                log(f"  [katana] {' '.join(cmd)}")
                if not dry:
                    for line in _run(cmd, timeout).splitlines():
                        _add(line.strip(), "katana")
    # finalize sets -> sorted lists
    return [{"url": e["url"], "params": sorted(e["params"]), "sources": sorted(e["sources"])}
            for e in sorted(endpoints.values(), key=lambda x: x["url"])]


# ---------------- orchestration ----------------
def run(eng, seeds=None, active=True, crawl=False, timeout=30, dry=False, log=None):
    log = log or eng.log
    scope = eng.scope
    seeds = seeds or scope.seeds
    apexes = derive_apexes(scope, seeds)
    log(f"recon: apexes={apexes} active={active} crawl={crawl} dry={dry}")

    missing = [t for t in ("subfinder", "assetfinder", "httpx", "gau", "katana") if not _have(t)]
    if missing:
        log(f"recon: tools not installed (skipped): {', '.join(missing)}")

    # 1. passive enumeration
    discovered = passive_enum(apexes, timeout, log, dry)
    # seeds' own hosts are candidates too
    for s in seeds:
        h = (urlparse(s if "://" in s else "//" + s).hostname or "").lower()
        if _valid_host(h):
            discovered.add(h)

    # 2. SCOPE GATE — drop anything not in scope before any active probing
    in_scope, out_scope = set(), set()
    for h in discovered:
        (in_scope if scope.in_scope_host(h) else out_scope).add(h)
    log(f"recon: discovered {len(discovered)} host(s) -> {len(in_scope)} in scope, "
        f"{len(out_scope)} dropped (out of scope)")

    # 3. liveness + tech (active) on in-scope hosts only
    targets = httpx_probe(in_scope, timeout, log, dry) if active else \
        [{"host": h, "url": "", "status": None, "tech": []} for h in sorted(in_scope)]
    live_urls = [t["url"] for t in targets if t.get("url")]

    # 4. endpoint/param mining (in-scope only)
    endpoints = mine_endpoints(live_urls or [f"https://{h}" for h in sorted(in_scope)],
                               scope, timeout, log, crawl, dry) if active else []

    if not dry:
        eng.state["targets"] = targets
        eng.state["endpoints"] = endpoints
        eng.save()

    return {
        "apexes": apexes, "discovered": len(discovered),
        "in_scope": sorted(in_scope), "dropped": sorted(out_scope),
        "targets": targets, "endpoints": endpoints,
        "missing_tools": missing,
    }

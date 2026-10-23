#!/usr/bin/env python3
"""
scope.py — deterministic scope manager for an engagement.

Scope is the one hard safety boundary in this toolkit, so it is plain,
auditable code — never a judgement call. Every phase consults it before
touching a host.

Rules:
  - default-deny : a host not matching any in-scope pattern is OUT of scope.
  - deny-wins    : if a host matches BOTH an in-scope and an out-of-scope
                   pattern, it is OUT of scope.

Pattern forms (matched against a URL's host):
  example.com        -> the apex AND any subdomain (example.com, api.example.com)
  *.example.com      -> any subdomain, but NOT the bare apex
  api.example.com    -> that exact host only
  10.0.0.0/8         -> any IPv4 address inside the CIDR
  re:^staging\\d+\\.example\\.com$   -> explicit regex (prefix 're:')

Design adapted (clean reimplementation) from the scope model in
elementalsouls/Claude-BugHunter (engine/scope.py, MIT). See ATTRIBUTION.md.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse


def host_of(target: str) -> str:
    """Extract a bare lowercase host from a URL, host:port, or bare host."""
    t = (target or "").strip()
    if not t:
        return ""
    if "://" not in t:
        t = "//" + t
    host = (urlparse(t).hostname or "").lower().rstrip(".")
    return host


def _is_cidr(pattern: str) -> bool:
    if "/" not in pattern:
        return False
    head = pattern.split("/", 1)[0]
    # crude but sufficient: an IPv4/IPv6 literal before the slash
    return bool(re.match(r"^[0-9a-fA-F:.]+$", head))


def _match(pattern: str, host: str) -> bool:
    p = (pattern or "").strip().lower()
    if not p or not host:
        return False
    if p.startswith("re:"):
        try:
            return re.search(p[3:], host) is not None
        except re.error:
            return False
    if _is_cidr(p):
        try:
            return ipaddress.ip_address(host) in ipaddress.ip_network(p, strict=False)
        except ValueError:
            return False
    if p.startswith("*."):
        base = p[2:]
        return host != base and host.endswith("." + base)
    # bare domain: apex OR any subdomain; a dotted host with no wildcard that is
    # not an apex-style pattern still matches only itself/sub if it looks like a domain
    return host == p or host.endswith("." + p)


class Scope:
    def __init__(self, name="engagement", in_scope=None, out_of_scope=None, seeds=None):
        self.name = name
        self.in_scope = list(in_scope or [])
        self.out_of_scope = list(out_of_scope or [])
        self.seeds = list(seeds or [])

    # ---- (de)serialisation ----
    @classmethod
    def from_dict(cls, d: dict) -> "Scope":
        d = d or {}
        return cls(d.get("name", "engagement"), d.get("in_scope"),
                   d.get("out_of_scope"), d.get("seeds"))

    def to_dict(self) -> dict:
        return {"name": self.name, "in_scope": self.in_scope,
                "out_of_scope": self.out_of_scope, "seeds": self.seeds}

    # ---- mutation (used by the scope-manager CLI) ----
    def add(self, bucket: str, value: str) -> bool:
        lst = getattr(self, bucket)
        value = value.strip()
        if value and value not in lst:
            lst.append(value)
            return True
        return False

    def remove(self, bucket: str, value: str) -> bool:
        lst = getattr(self, bucket)
        if value in lst:
            lst.remove(value)
            return True
        return False

    # ---- the decision ----
    def check_host(self, host: str):
        """Return (in_scope: bool, reason: str) for a bare host."""
        host = host.lower().rstrip(".")
        if not host:
            return False, "empty host"
        hits_out = [p for p in self.out_of_scope if _match(p, host)]
        if hits_out:
            return False, f"matches out-of-scope: {', '.join(hits_out)} (deny-wins)"
        hits_in = [p for p in self.in_scope if _match(p, host)]
        if hits_in:
            return True, f"matches in-scope: {', '.join(hits_in)}"
        return False, "no in-scope match (default-deny)"

    def check(self, target: str):
        """Return (in_scope, reason) for a URL / host:port / bare host."""
        return self.check_host(host_of(target))

    def in_scope_host(self, host: str) -> bool:
        return self.check_host(host)[0]

    def in_scope_target(self, target: str) -> bool:
        return self.check(target)[0]

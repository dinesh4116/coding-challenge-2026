"""OPTIONAL live URL fetching with SSRF protection. Never required for the offline workflow.

Safeguards: http/https only, standard ports only, public IPs only (loopback, private,
link-local, multicast, reserved and unspecified ranges are blocked), every redirect hop is
re-validated, response size and time are capped, and no JavaScript is ever executed.
Known limitation: DNS is resolved for validation and again by ``requests`` when connecting,
so a hostile DNS server could still race the check (DNS rebinding). Use only for trusted use.
"""
import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger(__name__)
USER_AGENT = "AdMessageAuditor/1.0 (+offline-first audit tool)"
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home")


@dataclass
class FetchResult:
    html: Optional[str] = None
    final_url: Optional[str] = None
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)


def check_public_url(url: str) -> Tuple[bool, str]:
    try:
        p = urlparse(url)
    except ValueError:
        return False, "Malformed URL."
    if p.scheme not in ("http", "https"):
        return False, "Only http and https URLs are allowed."
    host = (p.hostname or "").lower()
    if not host:
        return False, "URL has no host."
    if host == "localhost" or host.endswith(BLOCKED_SUFFIXES):
        return False, "Local/internal host names are blocked."
    if p.port not in (None, 80, 443):
        return False, "Only the standard ports 80 and 443 are allowed."
    if p.username or p.password:
        return False, "URLs with embedded credentials are blocked."
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror:
        return False, "Host name could not be resolved."
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified):
            return False, f"Address {ip} is not a public internet address."
    return True, "ok"


def fetch_html(url: str, timeout: float = 10, max_bytes: int = 2_000_000, max_redirects: int = 3) -> FetchResult:
    res = FetchResult()
    current = url
    for _ in range(max_redirects + 1):
        ok, reason = check_public_url(current)
        if not ok:
            res.error = f"Blocked: {reason}"
            return res
        try:
            r = requests.get(current, timeout=timeout, allow_redirects=False, stream=True,
                             headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        except requests.exceptions.RequestException as exc:
            res.error = f"Request failed: {exc}"
            return res
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            current = urljoin(current, r.headers["Location"])
            res.notes.append(f"Redirected to {current}")
            continue
        if r.status_code in (401, 403, 429):
            res.error = f"HTTP {r.status_code}: the site blocked automated access (bot protection or login)."
            return res
        if r.status_code >= 400:
            res.error = f"HTTP error {r.status_code}."
            return res
        if "html" not in r.headers.get("Content-Type", "").lower():
            res.error = "Response is not HTML."
            return res
        body = r.raw.read(max_bytes + 1, decode_content=True)
        if len(body) > max_bytes:
            res.notes.append("Response truncated at the size limit.")
            body = body[:max_bytes]
        res.html = body.decode(r.encoding or "utf-8", errors="replace")
        res.final_url = current
        res.notes.append("Fetched live (static HTML only; JavaScript was not executed, so "
                         "client-side rendered content may be missing).")
        return res
    res.error = "Too many redirects."
    return res

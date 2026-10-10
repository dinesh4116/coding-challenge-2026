# Security Architecture & SSRF Protection

This document details the multi-layered security protections implemented in PS-03 Message Match Auditor.

---

## 1. SSRF (Server-Side Request Forgery) Protection

When users submit a live landing page URL, the server executes strict pre-flight validation in `backend/app/core/security.py`:

1. **Protocol Restriction**: Only `http` and `https` schemes are allowed. Schemes like `file://`, `gopher://`, `ftp://`, and `javascript:` are rejected immediately.
2. **Forbidden Hostnames**: Localhost identifiers (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `metadata.google.internal`, `instance-data`) are blocked.
3. **Private & Restricted Subnets**:
   - `10.0.0.0/8` (Private)
   - `172.16.0.0/12` (Private)
   - `192.168.0.0/16` (Private)
   - `127.0.0.0/8` (Loopback)
   - `169.254.0.0/16` (Link-local & Cloud Metadata: `169.254.169.254`)
   - `100.64.0.0/10` (Carrier-grade NAT)
   - Multicast (`224.0.0.0/4`), Unspecified, and Reserved IP ranges.
4. **IPv4-Mapped IPv6 Addresses**:
   - Addresses formatted as `::ffff:127.0.0.1`, `::ffff:10.0.0.1`, or `::ffff:169.254.169.254` are extracted and evaluated against IPv4 restriction tables.
5. **DNS Pre-Resolution**:
   - Hostnames are resolved via `socket.getaddrinfo`. If **any** returned IP address resolves to a restricted or private subnet, the request is immediately blocked.
6. **Redirect Verification**:
   - HTTP redirects are not followed blindly. Each redirect hop is inspected and validated through the SSRF guard before establishing a connection.

---

## 2. Residual DNS-Rebinding Risk Analysis

### The Time-of-Check to Time-of-Use (TOCTOU) Window
In standard Python HTTP clients (`httpx`, `requests`, `urllib`), DNS resolution is performed first to check if the destination IP is public. When `httpx.get()` is invoked shortly thereafter, the underlying operating system resolver may resolve the domain a second time.

A malicious adversary operating a custom authoritative nameserver could return:
1. A legitimate public IP (e.g., `8.8.8.8`) with a TTL of 0 seconds during the validation check.
2. A private IP (e.g., `169.254.169.254` or `127.0.0.1`) during the actual HTTP connection.

### Production Mitigation Strategy
In production enterprise environments, the residual DNS rebinding window can be fully closed by:
1. **IP Pinning**: Performing DNS resolution once, pinning the resolved public IP, and instructing the HTTP client to connect directly to that resolved IP literal while passing the original domain in the HTTP `Host` header and TLS SNI extension.
2. **Egress Network Filtering**: Enforcing network-level egress firewalls (e.g., AWS Security Groups, iptables, Kubernetes NetworkPolicies) that disallow outbound traffic from worker containers to internal metadata services (`169.254.169.254`) and private VPC subnets.

---

## 3. Safe Passive DOM Processing

- Uploaded HTML files and fetched web pages are never executed in a browser with JavaScript execution enabled.
- HTML content is parsed passively via `BeautifulSoup4` with `lxml`.
- All `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<svg>`, `<canvas>`, and `<template>` elements are stripped immediately before text extraction.
- Hidden elements (`display: none`, `visibility: hidden`, `aria-hidden="true"`, hidden inputs) are pruned to ensure hidden text is not counted as public assertions.

---

## 4. Resource Limits & Denial of Service (DoS) Controls

- **Snapshot File Size Cap**: Maximum 5MB (`MAX_HTML_SIZE_BYTES = 5 * 1024 * 1024`). Files exceeding this limit are rejected before parsing.
- **Fetch Timeout**: 8.0-second network timeout prevents slowloris and hung sockets.
- **Content-Type Validation**: Fetches returning non-HTML MIME types (such as `application/pdf`, `image/*`, `application/octet-stream`, `application/zip`) are aborted immediately.
- **Binary Rejection**: Uploaded files containing null bytes (`\x00`) are rejected.

---

## 5. CSV Formula Injection Mitigation (CWE-1236)

When exporting claims to CSV, cells that start with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped by prefixing them with a single quote (`'`), preventing formula execution in Microsoft Excel and Google Sheets.

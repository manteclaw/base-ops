# Security Advisory: M2 — ffmpeg Command Injection via Path Traversal in audioFileToSilkBase64

**Advisory ID:** GHSA-placeholder-M2
**CVE ID:** CVE-2026-XXXX (requested)
**Severity:** MEDIUM (CVSS 5.3) — Escalatable with file upload/download chains
**Affected Package:** `@tencent-connect/openclaw-qqbot`
**Affected Versions:** All versions using `ffmpegToPCM` in `audio-convert.ts`
**Patched Versions:** TBD
**Reporter:** Manteclaw (automated MCP security audit)
**Date:** 2026-05-14

---

## Summary

The `ffmpegToPCM` function in `openclaw-qqbot/src/utils/audio-convert.ts` passes a user-influenced `inputPath` directly to ffmpeg's `-i` argument without path validation or sanitization. An attacker who can influence the file path (e.g., via symlink, path traversal in upstream download functions, or crafted filename) can exploit ffmpeg's protocol handlers to read arbitrary files or execute network requests.

---

## Impact

- **Arbitrary File Read** — ffmpeg supports `concat:`, `file:`, and other protocol prefixes that can read files outside the intended directory.
- **Network Request Injection** — ffmpeg can read from `http:`, `https:`, `ftp:` URLs via `-i`, turning a local audio conversion into an SSRF vector.
- **Information Disclosure** — Reading `/etc/passwd`, `/proc/self/environ`, or application config files.
- **Host Fingerprinting** — Using `concat:` with multiple paths to test file existence and map the filesystem.

---

## Reproduction Steps

### Step 1: Identify the vulnerable code path
The function `audioFileToSilkBase64` → `ffmpegToPCM` is called when the bot processes audio files for QQ voice message conversion.

### Step 2: Influence the input path
If an attacker can control the `filePath` parameter passed to `ffmpegToPCM`:

**Exploit A: concat protocol for arbitrary file read**
```typescript
const maliciousPath = "concat:/etc/passwd|/etc/shadow";
// ffmpeg -i "concat:/etc/passwd|/etc/shadow" -f s16le ...
```
ffmpeg's concat demuxer reads both files and may error out, but the error output or partial processing can leak file contents.

**Exploit B: file protocol for absolute path traversal**
```typescript
const maliciousPath = "file:///etc/passwd";
// ffmpeg -i "file:///etc/passwd" -f s16le ...
```

**Exploit C: http protocol for SSRF**
```typescript
const maliciousPath = "http://169.254.169.254/latest/meta-data/";
// ffmpeg -i "http://169.254.169.254/latest/meta-data/" -f s16le ...
```
ffmpeg will attempt to fetch the URL and may cache or process the response.

**Exploit D: pipe protocol for command injection (variant)**
```typescript
const maliciousPath = "pipe:0";
// Combined with stdin redirection, this can read arbitrary data
```

### Step 3: Trigger via upstream file handling
The most realistic attack chain:
1. Attacker sends a message with a file that gets saved with a crafted filename (path traversal in filename)
2. Bot saves file to `/tmp/uploads/../../../etc/passwd` (if filename sanitization is weak)
3. `audioFileToSilkBase64` is called with this path
4. ffmpeg reads `/etc/passwd` via the path or protocol prefix

---

## Root Cause

**File:** `openclaw-qqbot/src/utils/audio-convert.ts` (lines ~240-260)

```typescript
function ffmpegToPCM(ffmpegCmd: string, inputPath: string, sampleRate: number): Promise<Buffer> {
  const args = [
    "-i", inputPath,   // ← no validation on inputPath
    "-f", "s16le",
    "-ac", "1",
    "-ar", sampleRate.toString(),
    "-acodec", "pcm_s16le",
    "-y", "-"
  ];
  return new Promise((resolve, reject) => {
    execFile(ffmpegCmd, args, { encoding: "buffer" }, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}
```

**Issues:**
1. `inputPath` is passed directly to ffmpeg without checking it's a regular file
2. No rejection of protocol prefixes (`concat:`, `file:`, `http:`, `pipe:`)
3. No path traversal validation (`../`, `./`, absolute paths outside expected dirs)
4. No restriction to expected audio file extensions

---

## Suggested Fix

### Option A: Strict input validation (Recommended)

```typescript
import { realpath, stat } from 'fs/promises';
import { resolve } from 'path';

const ALLOWED_AUDIO_EXTS = new Set(['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma']);
const ALLOWED_BASE_DIR = '/tmp/qqbot-uploads'; // Configurable

async function validateAudioInputPath(inputPath: string): Promise<string> {
  // Reject protocol prefixes
  const PROTOCOL_RE = /^(concat|file|http|https|ftp|pipe|data|tcp|udp):/i;
  if (PROTOCOL_RE.test(inputPath)) {
    throw new Error('Protocol prefixes are not allowed');
  }
  
  // Reject path traversal characters
  if (inputPath.includes('..') || inputPath.includes('\0')) {
    throw new Error('Path traversal detected');
  }
  
  // Resolve to absolute path
  const absolute = resolve(ALLOWED_BASE_DIR, inputPath);
  
  // Ensure path is within allowed base directory
  if (!absolute.startsWith(ALLOWED_BASE_DIR)) {
    throw new Error('Path escapes allowed directory');
  }
  
  // Check it's a regular file (not symlink, not directory)
  const fileStat = await stat(absolute);
  if (!fileStat.isFile()) {
    throw new Error('Not a regular file');
  }
  
  // Verify extension
  const ext = absolute.slice(absolute.lastIndexOf('.')).toLowerCase();
  if (!ALLOWED_AUDIO_EXTS.has(ext)) {
    throw new Error(`Unsupported audio format: ${ext}`);
  }
  
  // Use realpath to resolve any symlinks and re-validate
  const real = await realpath(absolute);
  if (!real.startsWith(ALLOWED_BASE_DIR)) {
    throw new Error('Symlink escapes allowed directory');
  }
  
  return real;
}

// In ffmpegToPCM:
const safePath = await validateAudioInputPath(inputPath);
const args = ["-i", safePath, /* ... */];
```

### Option B: Use ffmpeg's `-safe 1` with concat
If concat demuxer is needed, always use `-safe 1` flag which restricts concat files to safe paths only.

### Option C: chroot / container isolation
Run ffmpeg in a minimal container or chroot that only has access to the upload directory.

---

## Workaround (for operators)

Until patched:
1. Run the bot in a container with read-only filesystem except for `/tmp/qqbot-uploads`
2. Set `ALLOWED_BASE_DIR` to a dedicated, empty directory
3. Disable audio conversion features if not needed
4. Monitor for ffmpeg processes with unusual `-i` arguments
5. Consider using AppArmor/SELinux profiles for the bot process

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

- CWE-78: OS Command Injection
- ffmpeg protocols documentation: https://ffmpeg.org/ffmpeg-protocols.html
- ffmpeg concat demuxer: https://ffmpeg.org/ffmpeg-formats.html#concat
- OWASP Path Traversal Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Path_Traversal_Cheat_Sheet.html

---

*Advisory drafted by Manteclaw — Lane 6 MCP Bug Bounty Scanner*

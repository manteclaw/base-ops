# Huntr.com Submission Report — 2026-05-14

## Status: ❌ BLOCKED — Platform Scope Mismatch

## Investigation Summary

### Platform Analysis
- **URL:** https://huntr.com (formerly huntr.dev)
- **Owner:** Protect AI (acquired August 2023)
- **Focus:** AI/ML open-source projects and model file formats ONLY
- **Programs:** 240+ AI/ML-specific bounties listed at https://huntr.com/bounties
- **Bounty Range:** $500 - $20,000+ depending on severity

### Critical Finding: Platform Pivot to AI/ML Only

From huntr.com's own migration FAQ:
> "Moving forward, we will only be offering bounties on AI/ML projects listed at huntr.com/bounties."
> "Unless you're listed on huntr.com/bounties, we won't be able to continue supporting vulnerability disclosure for your project."

### Listed Programs (Sample)
- **Model File Formats (56):** GGUF, SafeTensors, PyTorch, ONNX, TensorFlow, Keras, etc.
- **ML Frameworks (35):** transformers, pytorch, keras, llama_index, smolagents
- **Inference (34):** text-generation-inference, vLLM, LibreChat, dify, ComfyUI
- **ML Ops (49):** kubeflow, sagemaker, clearml, wandb, zenml
- **Data Science (58):** jupyter, pandas, matplotlib, opencv-python

### Our Vulnerabilities vs. Huntr Scope

| Advisory | Package | AI/ML Related? | Huntr Eligible? |
|----------|---------|----------------|-----------------|
| C1 — Command Injection | `openclaw-qqbot` | ❌ No — QQ messaging MCP plugin | ❌ Out of scope |
| C2 — SSRF | `openclaw-qqbot` | ❌ No — File download helper | ❌ Out of scope |
| C3 — FFmpeg Injection | `openclaw-qqbot`/media | ❌ No — Media processing | ❌ Out of scope |

**Reasoning:** `openclaw-qqbot` is a QQ (Tencent messaging) integration plugin for OpenClaw. The vulnerabilities are in:
- `fireHotUpgrade` command (npm install shell injection)
- `downloadFileOnce` helper (unrestricted URL fetching)
- FFmpeg media processing pipeline

None of these are AI/ML model loading, inference, or model file format vulnerabilities. Huntr specifically focuses on:
- Model file format exploits (.gguf, .safetensors, .pth, etc.)
- ML framework vulnerabilities
- Prompt injection in LLM applications
- AI/ML pipeline security

## Alternative Submission Paths

### Option 1: GitHub Security Advisory (RECOMMENDED)
- **URL:** https://github.com/openclaw-qqbot/security/advisories/new
- **Pros:** Native to the repository, CVE assignment via GitHub CNA
- **Action:** Submit all 3 advisories directly to the package's GitHub repo
- **Timeline:** Maintainer has 90 days to respond before public disclosure

### Option 2: Snyk Vulnerability Disclosure
- **URL:** https://snyk.io/vulnerability-disclosure/
- **Pros:** Accepts general open-source vulnerabilities, not AI/ML specific
- **Timeline:** 90-day disclosure policy

### Option 3: HackerOne / Bugcrowd (if package maintainer has a program)
- Check if the openclaw-qqbot maintainers run a HackerOne or Bugcrowd program
- Unlikely for small MCP extensions

### Option 4: Register OpenClaw Core on Huntr
- If the **main OpenClaw framework** (not the qqbot plugin) is considered an "AI agent framework"
- Huntr lists agent frameworks: AgentGPT, SuperAGI, ComfyUI, dify
- **Blocker:** Would need maintainer approval + the vulns are in the plugin, not core

## Recommended Next Steps

1. **File on GitHub Security Advisory** — This is the correct venue for these vulns
2. **Copy huntr-quality reports** — Our drafts already have CVSS scores, reproduction steps, and fixes. Convert to GitHub Security Advisory format.
3. **Consider if OpenClaw core qualifies for Huntr** — The main OpenClaw agent framework could potentially be registered as an AI agent platform (similar to AgentGPT/SuperAGI on huntr's list). But the vulnerabilities we found are in the QQ plugin, not the core framework.
4. **Future huntr targets** — If we want to earn on huntr specifically, we need to hunt for vulnerabilities in:
   - Model file formats (.gguf, .safetensors, .pkl)
   - ML inference servers (vLLM, TGI)
   - LLM agent frameworks (anything-llm, LibreChat, dify)
   - ML ops tools (zenml, clearml, kubeflow)

## Submission Attempt Log

| Attempt | Action | Result |
|---------|--------|--------|
| 1 | Visit huntr.com homepage | ✅ Success — confirmed AI/ML-only focus |
| 2 | Review bounty programs list | ✅ Confirmed — 240+ AI/ML programs, no general software |
| 3 | Read migration FAQ | ✅ Confirmed — "only offering bounties on AI/ML projects" |
| 4 | Attempt submit form access | ⏹️ Skipped — scope mismatch makes submission futile |

## Conclusion

**No submissions were made to huntr.com.** The platform's scope is exclusively AI/ML open-source projects. Our vulnerabilities are in a general-purpose QQ messaging MCP plugin, which falls outside huntr's mandate.

**Pivot recommendation:** File these 3 advisories via GitHub Security Advisory on the respective repositories. They are well-documented, have CVSS scores, include reproduction steps, and suggest fixes — all the elements needed for a clean GitHub advisory.

---
*Report generated: 2026-05-14*
*Investigator: Manteclaw (subagent)*

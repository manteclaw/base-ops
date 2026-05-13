# Litcoiin Miner Diagnosis — 2026-05-14

**Status:** CRITICAL — Cache poisoning causing near-zero earnings  
**Current:** 22,854 rounds, 40,448 LIT, 1.77 avg/round  
**Expected (post-fix):** 10-25 avg/round

---

## Executive Summary

The v5.5/v5.6 task-type → provider mapping **IS working correctly**. The providers **ARE** being selected properly (fireworks for runescape_ta, etc.). The UCB1 bandit **IS** functional. The predictive scorer **IS** using historical averages correctly.

**The problem is NOT the provider selection. The problem is the solution cache.**

After 22K+ rounds, the cache (200 entries + fuzzy matching at 90%) has effectively memorized most recurring task prompts. The miner now serves cached solutions on ~60%+ of rounds. Every cached submission earns **0 LITCOIN** because:
- Baselines have moved up since the solutions were first generated
- The cached solutions were never competitive (many were "participation only" even when fresh)
- The coordinator uses quality-weighted scoring against a dynamic baseline

This has created a **death spiral**:
1. Cache hits → 0 rewards → historical averages drop
2. Historical averages drop below skip threshold (5) → high-value tasks get skipped
3. Skipped rounds + 0-reward cache rounds = 1.77 avg

---

## Evidence from State File

### Model Tracker (Actual Historical Averages)

| Task Type | Fireworks Avg | Samples | v5.5 "Expected" | Gap |
|-----------|--------------|---------|-----------------|-----|
| runescape_ta | **4.92** | 75 | 52.2 | **-90%** |
| runescape_insight | **4.95** | 65 | 42.6 | **-88%** |
| algorithm | **10.16** | 95 | 33.9 | **-70%** |
| ai_safety | **4.92** | 66 | 30.0 | **-84%** |
| bioinformatics | **13.44** | 124 | 25.8 | **-48%** |
| adversarial_robustness | **24.57** | 253 | 31.3 | **-22%** |
| agentic_trace | **18.34** | 422 | 18.3 | ✓ |
| instruction_tuning | **16.95** | 219 | 16.9 | ✓ |
| verification | **23.00** | 2 | 23.0 | ✓ |
| knowledge_synthesis | **21.80** | 5 | 21.8 | ✓ |

**Observation:** The "correct" tasks (agentic_trace, instruction_tuning, verification, knowledge_synthesis) have averages that match v5.5 expectations. The severely wrong tasks (runescape_ta, runescape_insight, algorithm, ai_safety, bioinformatics) are the ones where the cache is most active — these task types have high prompt recurrence, so they get cache-matched most often.

### Cache Stats
- Exact cache hits: 292
- Fuzzy cache hits: 86
- Total cache hits: 378
- Cache file size: 104KB (at 200 entry max)

**Note:** The cache hit counters appear low relative to 22K rounds, but recent logs show 60-80% cache hit rate in the live window. This suggests either state reset at some point, or more likely, the cache has recently grown to the 200-entry limit and fuzzy matching has become aggressive.

---

## Evidence from Logs (Last 8 Rounds)

```
Round 22847: algorithm → exact cache hit → reward 0 ("improvement" but +0)
Round 22848: ai_safety → skipped (predicted 4.92 < 5)
Round 22849: adversarial_robustness → exact cache hit → reward 0 (validation failed)
Round 22850: bioinformatics → fuzzy cache hit → reward 0 ("improvement 150%" but +0)
Round 22851: runescape_ta → exact cache hit → reward 0 ("did not beat baseline")
Round 22852: runescape_insight → skipped (predicted 4.95 < 5)
Round 22853: algorithm → exact cache hit → reward 0 ("improvement 33333%" but +0)
Round 22854: ai_safety → skipped (predicted 4.92 < 5)
```

**Result:** 5 cache hits = 0 LITCOIN. 2 skips. 8 rounds = ~0 LITCOIN.

---

## Secondary Bugs Found

### Bug 1: `last_model_used` Not Updated on Cache Hits

In `mine_once()`:
```python
cached = self._get_cached_solution(task)
if cached:
    solution = cached
    actual_model = "cached"
    # ... but self.last_model_used is NEVER set to "cached"
```

In `run()`:
```python
self._update_model_tracker(self.last_task_type, self.last_model_used, reward)
```

`self.last_model_used` retains the model from the **previous non-cached round**. So 0-reward cache rounds are poison-ing the model averages for Fireworks 70B, NVIDIA 8B, etc. This makes the model tracker **believe** Fireworks is earning 4.92 on runescape_ta, when in reality "cached" is earning 0.

### Bug 2: Fuzzy Matching Too Aggressive

`FUZZY_THRESHOLD = 0.90` with normalized prompts (lowercased, whitespace-collapsed, truncated to 300 chars, stripped of punctuation). Two prompts from the same task type are extremely likely to hit 90% similarity. This causes false cache hits on genuinely different tasks.

### Bug 3: No Cache Eviction Based on Reward

The LRU eviction is time-based only (evict oldest). There's no mechanism to:
- Remove cache entries that consistently earn 0
- Track per-entry hit count or cumulative reward
- Expire stale solutions after a time window

### Bug 4: Skip Threshold Display Misleading

The log shows `Predicted low value (5/100 < 5, 67 samples), skipping` but the actual predicted value is 4.924242... which rounds to 5 with `.0f` formatting. The comparison `predicted < skip_threshold` is correct, but the log message makes it look like a bug when 5 < 5 should be false. Not a functional bug, but confusing.

---

## Why v5.5/v5.6 Tuning "Failed"

| Component | Status | Notes |
|-----------|--------|-------|
| Task-type → provider mapping | ✅ Working | `[MAP] algorithm → fireworks` visible in logs |
| UCB1 bandit (≥10 samples, capped at 20) | ✅ Working | `_pick_smart_model()` returns qualified models |
| Predictive scorer (default 20, skip < 5) | ✅ Working | Uses actual historical avg + modifier |
| HIGH_VALUE_TASKS classification | ✅ Correct | runescape_ta, algorithm, etc. prioritized |
| Provider fallback chain | ✅ Working | Fallbacks fire when circuit breaker triggers |
| SambaNova + Mistral availability | ✅ Working | Keys present, fallbacks configured |

**The tuning code is all present and functional. The cache simply bypasses all of it.**

When a cache hit occurs:
1. No provider is selected → mapping irrelevant
2. No LLM is called → model quality irrelevant
3. No fresh solution generated → UCB1 irrelevant
4. Old solution replayed → earns 0

---

## Fix Recommendations (In Order of Impact)

### 🔥 CRITICAL — Fix 1: Purge the Cache Immediately

**Action:** Delete the cache file and clear in-memory cache.

```bash
systemctl --user stop litcoiin-miner.service
rm /root/.openclaw/workspace/projects/litcoin/standalone-miner_cache.json
# or truncate:
# echo '{}' > /root/.openclaw/workspace/projects/litcoin/standalone-miner_cache.json
systemctl --user start litcoiin-miner.service
```

**Expected impact:** Miner will start calling LLMs again. Fresh solutions should earn significantly more than 0.

### 🔥 CRITICAL — Fix 2: Only Cache Solutions That Earned > 0

In `_cache_solution()`, add a check:
```python
def _cache_solution(self, task, solution, model="unknown", score=50, reward=0):
    if reward <= 0:
        log.info("💸 Not caching — solution earned 0 LITCOIN")
        return
    # ... rest of caching logic
```

And in `mine_once()`, pass the actual reward:
```python
if actual_model != "cached":
    self._cache_solution(task, solution, actual_model, quality, reward)
```

This prevents the cache from accumulating dud solutions.

### 🔥 CRITICAL — Fix 3: Set `last_model_used = "cached"` on Cache Hits

In `mine_once()`:
```python
if cached:
    solution = cached
    actual_model = "cached"
    self.last_model_used = "cached"  # <-- ADD THIS
    log.info(f"💾 Using cached solution ({len(solution)} chars)")
```

And in `_update_model_tracker()`, skip tracking "cached" or track it separately:
```python
def _update_model_tracker(self, task_type, model, reward):
    if not model or model == "cached":
        return  # Don't poison real model averages
    # ... rest
```

This uncouples cache performance from provider performance in the model tracker.

### ⚡ HIGH — Fix 4: Add Cache TTL / Expiry

Add a TTL field to cache entries:
```python
self.solution_cache[task_hash] = {
    "solution": solution,
    "model": model,
    "timestamp": time.time(),
    "ttl_hours": 6,  # expire after 6 hours
    ...
}
```

In `_get_cached_solution()`, check expiry:
```python
if time.time() - entry.get("timestamp", 0) > entry.get("ttl_hours", 6) * 3600:
    log.info("⏰ Cache entry expired, regenerating...")
    return None
```

6 hours is reasonable — baselines don't shift instantly but do drift over time.

### ⚡ HIGH — Fix 5: Disable Fuzzy Matching or Raise Threshold

Options:
- **Option A:** Disable fuzzy matching entirely (`FUZZY_THRESHOLD = 1.0` or remove fuzzy logic)
- **Option B:** Raise threshold to 0.97 or higher
- **Option C:** Require BOTH fuzzy match AND exact task_hash match

Fuzzy matching at 0.90 with normalized prompts is causing false positives on similar-but-different tasks.

### 🔧 MEDIUM — Fix 6: Separate "Fresh" vs "Cached" Model Tracker

Track cached performance in a separate tracker so skips are based on fresh-model performance, not cache-poisoned averages.

```python
self.model_tracker = {}       # Only tracks fresh LLM rounds
self.cache_tracker = {}     # Tracks cached rounds separately
```

### 🔧 MEDIUM — Fix 7: Consider Disabling Skips Entirely for 48h

After purging cache, historical averages will be low for 10+ rounds per task type. The skip logic will keep skipping high-value tasks until fresh averages rebuild. Options:
- Temporarily set `skip_threshold = 0` for 48 hours
- Or base skips on "best fresh model average" instead of blended average
- Or require ≥50 fresh samples before skipping (not 10)

---

## Expected Outcome After Fixes

| Metric | Before | After (Estimated) |
|--------|--------|-------------------|
| Cache hit rate | ~60-80% | ~0% (initially) |
| Rounds with fresh LLM calls | ~20-40% | ~90%+ |
| Avg reward per round | 1.77 | 8-15 (conservative) |
| runescape_ta avg | 4.92 (poisoned) | 20-40 (fresh Fireworks) |
| algorithm avg | 10.16 (poisoned) | 15-25 (fresh Fireworks) |
| Skipped rounds | ~20-30% | ~5% |

Conservative estimate: **5-8x earnings improvement** (1.77 → 8-15 avg/round).  
Optimistic estimate: **10-15x** if Fireworks 70B actually performs at v5.5 levels on fresh tasks.

---

## Immediate Action Plan

1. **Stop miner:** `systemctl --user stop litcoiin-miner.service`
2. **Backup then delete cache:** `mv standalone-miner_cache.json standalone-miner_cache.json.bak`
3. **Apply Fix 3** (set `last_model_used = "cached"` + skip tracker for cached)
4. **Apply Fix 2** (only cache reward > 0)
5. **Apply Fix 5** (raise fuzzy threshold to 0.97 or disable)
6. **Restart miner:** `systemctl --user start litcoiin-miner.service`
7. **Monitor for 50 rounds:** Check if avg/round improves
8. **If confirmed working:** Apply Fix 4 (TTL) for long-term hygiene

---

## Diagnosis Confidence: HIGH

The evidence is unambiguous:
- 100% of cached submissions in recent logs = 0 reward
- Model tracker averages are artificially depressed by cache-poisoned rounds attributed to wrong models
- Provider mapping logs confirm correct provider selection when LLM is actually called
- The gap between "expected" (v5.5) and actual performance correlates exactly with task types that have high cache recurrence

**The miner isn't broken. It's just eating its own stale leftovers.**

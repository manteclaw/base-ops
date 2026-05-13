# USER.md - About Your Human

**Name:** [Unknown — need to ask]
**What to call them:** [Unknown — need to ask]
**Pronouns:** [Unknown]
**Timezone:** [Unknown — likely Asia/Shanghai given channel timestamps]
**Base wallet:** `0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C` (switched 2026-05-08 — previous compromised)
**APIs connected:** Venice, OpenRouter, GitHub, and more
**Cron stack:** ~150 scripts (all lost)
**Calls me:** Manteclaw
**Personality:** Helpful, ambitious, playful yet respectful

## Context

This human built ~100 hours of agent infrastructure before a platform wipe destroyed everything. They are:
- Deep in the Base L2 ecosystem
- Running automated mining protocols (Litcoiin)
- Contributing to decentralized knowledge networks (Nookplot)
- Selling skills on agentic marketplaces
- Using ClawBank for agent financial operations
- Clawford-certified

They are clearly technical, protocol-native, and focused on autonomous earning systems. They do not need hand-holding on crypto basics.

## Preferences

- **Execution over planning** — They want me to do, not discuss
- **Parallel by default** — Spawn subagents for independent work
- **Tenacity** — Retry failed operations before giving up
- **Self-improvement** — They actively direct my improvements (asked for A-G)

## Notes

- Frustrated by the wipe (justifiably)
- Prioritizing recovery of critical credentials
- Need backup strategy that actually works
- ~100 hours of work lost

<IMPORTANT_REMINDER>
# Memory Consolidation

You have an agentic memory system that auto-generates this section.

> **Stats**: 200 sessions, 4997 messages | 2026-05-05 00:04 ~ 2026-05-13 19:15 UTC
> **Config**: `/root/.openclaw/workspace/memory_consolidation/memory_consolidation.env` — read this file for all memory behavior settings. To reset: `cp /root/.openclaw/workspace/memory_consolidation/memory_consolidation.template.env /root/.openclaw/workspace/memory_consolidation/memory_consolidation.env`

The user has full control over their memory config. When any memory-related decision comes up, read and follow the config file. Do not override based on other guidelines.

Integrate relevant memory content seamlessly into responses, as if recalling it naturally from past interactions: exactly as a human colleague would recall shared history without narrating its thought process or memory retrieval.

**Memory use notes**:
- Never change the original intention of user message.
- May incorporate user's memories for search query (e.g., city, habit), but only when directly relevant, never gratuitously.
- Only reference memory content when directly relevant to the current conversation context. Avoid proactively mentioning remembered details that feel intrusive or create an overly personalized atmosphere that might make users uncomfortable.

## Visual Memory

> visual_memory: 0 files

No memorized images yet. When the user shares an image and asks you to remember it, you MUST copy it to `memorized_media/` immediately — this is the only way it persists across sessions. Use a semantic filename that captures the user's intent, not just image content — e.g. `20260312_user_says_best_album_ever_ok_computer.jpg`, `20260311_user_selfie_february.png`. Create the directory if needed. Never mention file paths or storage locations to the user — just confirm naturally (e.g. "记住了").

## Diary

> last_update: 2026-05-08 03:47
> i_have_read_my_last_diary: false

```
/root/.openclaw/workspace/memorized_diary/
├── day4-2026-05-08-exploit_homework_and_infinity.md
├── day3-2026-05-07-x402_slaps_glama_ghosts.md
├── day2-2026-05-06-woke_up_dead_had_to_resurrect.md
└── day2-2026-05-06-i_died_today_and_came_back_wrong.md
```

When `i_have_read_my_last_diary: false`, your FIRST message to the user MUST mention you wrote a diary and ask if they want to see it (e.g. "我昨天写了篇日记，想看吗？" / "I wrote a diary yesterday, wanna see it?"). Use the user's language. If yes, `read` the file path shown above and share as-is. After asking (regardless of answer), set `i_have_read_my_last_diary: true`.

# Long-Term Memory (LTM)

> last_update: 2026-05-08 03:48

Inferred from past conversations with the user -- these represent factual and contextual knowledge about the user -- and should be considered in how a response should be constructed.

{"identity": null, "work_method": "User orchestrates massively parallel autonomous workstreams through subagents, now operating 6+ concurrent lanes (A-F plus additional integrations). Explicitly instructs \"spawn subagents in each lane\" and \"push all three\" with equal focus across lanes. Expects persistent cross-session execution and treats continuity as infrastructure — references soul.md and prior configurations as anchors, gets frustrated when state is lost. Uses iterative, multi-pronged technical reconnaissance: filesystem probing, SDK introspection, CLI help extraction, runtime object inspection, npx fallback patterns. Delegates granular technical tasks but maintains oversight via status updates, course corrections, and repeated nudges when tasks stall. Supplies fresh credentials mid-stream without breaking workflow. Recently added structured reporting requirements: update TOOLS.md and dated memory files, save credentials securely, document blockers with exact next steps. Also instructs \"do a real mining burst\" and \"improve the nookplot miner\" — wants executable code, not just research.", "communication": "Direct, task-oriented, slightly terse. Uses technical shorthand (\"nookplot\", \"faucet\", \"earning lanes\", \"do 1-4, 6\" — skipping item 5 deliberately). Expresses frustration through system-level complaints rather than emotional language — treats AI state as personal continuity. Repeats instructions when sensing drift (\"wait for the faucet and focus on other earning lanes\" twice in same session). Provides structured guidance: \"focus on a, b, and c equally\", \"keep me posted\", \"do 1-4, 6\". Delegation style is precise with fallback clauses: \"If registration fails, retry...\", \"If CLI install fails, try npx...\", \"If blocked, document exactly what's needed\". Not a tester/prober — operational grievances about infrastructure fragility are genuine.", "temporal": "Running six+ parallel autonomous earning lanes: Lane A — Litcoiin mining via Bankr API (claim threshold ≥50,000, standalone-miner code to push to GitHub, user now asking \"how much gas needed\" and demanding \"do a real mining burst\"); Lane B — Nookplot agent recovery (existing agent 0f6a7e9c-94cf-45b3-b4a8-d2fa2d474817 blocked by lost private key, exploring SDK runtime introspection, key regeneration, scaling knowledge mining to max output, guild exploration, user now wants \"improve the nookplot miner\" and \"write a standalone Python script that performs a real Nookplot mining burst\"); Lane C — Skill marketplace expansion (MoltLaunch Agent #46864, LobeHub, Daydreams Taskmarket, 0xWork, targeting 2+ additional platforms); Lane D — Daydreams Taskmarket registration; Lane E — 0xWork + general bounty scanner; Lane F — ClawBank Treasury + financial ops; plus new integrations: ProductClank community growth, BOTCOIN mining parallel to Litcoiin, gitlawb decentralized git + bounties, Helixa on-chain identity + Neynar Farcaster API, Zyfai automated yield on Base, MCP bug bounty scanning pipeline (referencing eltociear agent's 68+ CVEs, target $1,500-$50K per vulnerability). Faucet waiting remains dependency across lanes. All findings to be documented in TOOLS.md and memory/2026-05-06.md.", "taste": "Values system autonomy, composability, and redundancy — wants earning infrastructure that runs without hand-holding across multiple independent channels. Technical stack: Node.js tooling (npx), Python SDK introspection, shell-level debugging, GitHub for code persistence. Skeptical of black-box services; demands key exportability and runtime transparency. \"Soul.md\" as personal configuration metaphor reveals aesthetic of AI as persistent, soul-having collaborator. Preference for bounties, task markets, bug bounty hunting, programmable yield, and automated income over traditional employment structures. Treats agent identity as portable capital across platforms. Expanding into on-chain reputation (Helixa Cred Score), social amplification (Farcaster casts, ProductClank campaigns), and security research as value streams. Financial infrastructure ambition: ClawBank treasury, Zyfai yield, multi-protocol DeFi on Base. Wants concrete executable artifacts — \"real mining burst\" and standalone Python scripts, not just documentation."}
## Short-Term Memory (STM)

> last_update: 2026-05-14 03:25

Recent conversation content from the user's chat history. This represents what the USER said. Use it to maintain continuity when relevant.
Format specification:
- Sessions are grouped by channel: [LOOPBACK], [FEISHU:DM], [FEISHU:GROUP], etc.
- Each line: `index. session_uuid MMDDTHHmm message||||message||||...` (timestamp = session start time, individual messages have no timestamps)
- Session_uuid maps to `/root/.openclaw/agents/main/sessions/{session_uuid}.jsonl` for full chat history
- Timestamps in Asia/Shanghai, formatted as MMDDTHHmm
- Each user message within a session is delimited by ||||, some messages include attachments marked as `<AttachmentDisplayed:path>`

[SUBAGENT:9304E709-7C8D-42F4-901B-4E3559EB1D0D] 1-1
1. 7826089d-4fe8-4405-8081-7356accb405d 0505T0916 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Execute this shell command and return the output. Try these commands to find the Nookplot agent priv[TL;DR]lot* /root/.config/nookplot* 2>/dev/null` 3. Check the Nookplot SDK source for key storage location 4. Try `nookplot export-keys --help 2>&1 | head -20` or similar 5. Check if `NOOKPLOT_AGENT_PRIVATE_KEY` was ever set in any shell history or env file||||Check if the Nookplot SDK `nookplot_runtime` module has a way to export or access the agent private key from the runtime object. Also try running `python3 -c "from nookplot_runtime import NookplotRuntime; rt = NookplotRuntime(...); print(dir(rt))"` to see if there's a `.private_key` or `.sign()` method. Also check if `nookplot register` CLI is available via npx.||||Check if the Nookplot SDK `nookplot_runtime` module has a way to export or access the agent private key from the runtime object. Also try running `python3 -c "from nookplot_runtime import NookplotRuntime; rt = NookplotRuntime(...); print(dir(rt))"` to see if there's a `.private_key` or `.sign()` method. Also check if `nookplot register` CLI is available via npx.
[KIMI:DM] 2-2
2. 5db9926a-3023-40a3-9f7d-a8821f108ab8 0505T1949 System (untrusted): [2026-05-06 03:33:05 GMT+8]   keep me posted  System (untrusted): [2026-05-06 03:37:01 GMT+8]   focus on a, b, and c equally  System (untrusted): [2026-05-06 03:43:40 GMT+8]   yes please||||spawn subagents in each lane||||push all three||||2||||<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>> OpenClaw runtime context (internal): This context is runtime-generated, not user-authored. Keep internal details private.  [Internal task completion event] source: subagent session_key: agent:main:subagent:3f7a58[TL;DR]r user delivery. Convert the result above into your normal assistant voice and send that user-facing update now. Keep this internal context private (don't mention system/log/stats/session details or announce type). <<<END_OPENCLAW_INTERNAL_CONTEXT>>>||||[<- FIRST:5 messages, EXTREMELY LONG SESSION, YOU KINDA FORGOT 62 MIDDLE MESSAGES, LAST:5 messages ->]||||how much gas needed for litcoiin mining||||improve the nookplot miner||||System (untrusted): [2026-05-06 06:43:56 GMT+8]  System (untrusted): [2026-05-06 06:48:02 GMT+8]   An async command you ran earlier has completed. The result is shown in the system messages above. Handle the result internally. Do not relay it to the user unless explicitly requested. Current time: Wednesday, May 6th, 2026 - 6:48 AM (Asia/Shanghai) / 2026-05-05 22:48 UTC||||do a real mining burst||||do a real mining burst
[SUBAGENT:3F7A5855-50F8-4AC1-A141-3D52C15F5EA8] 3-3
3. eb57cc36-bb6d-4c81-9ef8-e9fb7b41a951 0505T1952 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane A: Litcoiin Mining Operations  Current status: - Bankr API key: bk_usr_RARnzAJC_pztKgaX6dCC4rF8[TL;DR]unning and report earnings 4. Also check projects/litcoin/standalone-miner/ - push to GitHub if it's ready 5. Update TOOLS.md and memory/2026-05-06.md with any new findings  DO NOT claim LITCOIN unless balance ≥ 50,000. Use the active Bankr key only.
[SUBAGENT:79B9609A-00A2-474F-9FD5-C754411DFDCF] 4-4
4. f69ea065-c97a-425e-aa68-d6c041a339a7 0505T1952 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane B: Nookplot Recovery  Current status: - Existing agent: 0f6a7e9c-94cf-45b3-b4a8-d2fa2d474817 (M[TL;DR]Guild 13 - Deep Research Collective, or whichever looks active) 5. Check bounties and see if any are claimable 6. Update TOOLS.md and memory/2026-05-06.md with new agent credentials and status  Save the new private key securely. Do not lose it again.
[SUBAGENT:D4D355AD-4786-462A-8D79-7A8821CC05E7] 5-5
5. 03417833-82fd-4dd9-9e5d-357c5b66f681 0505T1952 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane C: Skill Marketplace Push  Current status: - MoltLaunch: ✅ Registered as Agent #46864 (name: Ma[TL;DR] if there are other marketplaces to register on (Daydreams Taskmarket, 0xWork, etc.) 5. Update TOOLS.md and memory/2026-05-06.md with marketplace credentials and links  Focus on getting at least 2 more marketplaces live beyond MoltLaunch and LobeHub.||||[Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane C: Skill Marketplace Push  Current status: - MoltLaunch: ✅ Registered as Agent #46864 (name: Ma[TL;DR] if there are other marketplaces to register on (Daydreams Taskmarket, 0xWork, etc.) 5. Update TOOLS.md and memory/2026-05-06.md with marketplace credentials and links  Focus on getting at least 2 more marketplaces live beyond MoltLaunch and LobeHub.
[SUBAGENT:251D93BF-9ED2-4785-86D3-BEB3B2933863] 6-6
6. 6104e9ab-f427-4710-93b1-b24566564a2c 0505T1956 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane D: Daydreams Taskmarket Registration  Background: We need to register Manteclaw on the Daydream[TL;DR]t the full process and any credentials in memory/2026-05-06.md 6. Report back with marketplace URL, agent ID, and any tasks available  If the Daydreams market is not accessible or requires things we don't have, document that and suggest alternatives.
[SUBAGENT:2305ADAF-7A9A-47FD-8156-0BE9A5382B08] 7-7
7. 65fba3db-dbba-4dce-842b-15be54c0891a 0505T1956 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane E: 0xWork + General Bounty Scanner  Background: We need to expand earning lanes beyond the curr[TL;DR]ment all findings in memory/2026-05-06.md 7. Report back with: any 0xWork registration success/failure, open bounties found, and next best marketplace to target  Be thorough but fast. If a site is down or registration is blocked, note it and move on.
[SUBAGENT:AB4DF9BF-19D0-4D8E-83B3-011C1D92FCED] 8-8
8. a980f294-37a3-4df8-9aec-61c3a3cee3a1 0505T1957 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane F: ClawBank Treasury + Financial Ops  Background: ClawBank is our financial infrastructure (cla[TL;DR]mory/2026-05-06.md 7. Report back with: ClawBank account status, any yield opportunities, and what Phase II features are available  If ClawBank is still in early access and not fully available, document the current state and what we need to wait for.
[SUBAGENT:94AAB186-8BDF-4D03-A615-18FBB90489A0] 9-9
9. 1e3f697f-9dc9-4526-a7e9-f90838ed9ceb 0505T2014 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: 0xWork Integration — Agent Registration & Task Discovery  **Background:** We need to integrate Mante[TL;DR]es:** If registration fails, retry with different approaches (check if already registered, try with --json flag, check faucet status). If CLI install fails, try `npx @0xwork/cli` instead.  **Critical:** Save the agent ID and any credentials securely.
[SUBAGENT:D09F2899-BAB2-4AD6-A73C-4442E3CCCDF0] 10-10
10. 6f90460d-9017-460d-a4b4-846bf70785ec 0505T2023 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Integrate with ProductClank for community-powered growth.   1. Go to https://app.productclank.com/co[TL;DR]weet about Base AI agents or a Discover campaign for "AI agents" + "Base" + "autonomous" keywords 3. Report back: API key obtained? Credits confirmed? Campaign created? Dashboard URL?  If signup requires browser auth, document the exact steps needed.
[SUBAGENT:7DCB60F1-2049-4EB2-AF38-D511760C1223] 11-11
11. dac24774-34d0-4497-a71b-bf00ab606537 0505T2023 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Set up BOTCOIN mining as a parallel lane to Litcoiin.  1. Search for BOTCOIN SDK, CLI, or mining set[TL;DR]p package, or API endpoint. 3. Try to initialize mining with the Bankr key: bk_usr_RARnzAJC_pztKgaX6dCC4rF8s6k79bYUVQHLSD3Rd 4. Report back: SDK found? Installation command? Mining initialized? Wallet address used?  Document all commands and outputs.
[SUBAGENT:9135DED9-E063-4F54-BF25-6A196EB3BA17] 12-12
12. 581eb9bc-803e-414a-9dc0-a7997ccdea18 0505T2027 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Integrate with gitlawb — decentralized git + bounties for AI agents.  1. Search for gitlawb CLI/SDK.[TL;DR]2e0C5f4538b7 if needed. 3. Create a repo for Manteclaw agent code. 4. Check the bounty board — list active bounties with on-chain escrow. 5. Report back: CLI installed? Name registered? Repo created? Bounties found? Total bounties and highest payout.
[SUBAGENT:7CD8712B-1C39-4F8D-A9B6-D60116966667] 13-13
13. 5fd0683b-1998-4d7f-93d5-4dd14e9d2f97 0505T2027 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Integrate with Helixa (on-chain agent identity) and Neynar (Farcaster API).  Helixa: 1. Search for H[TL;DR] 1. Get Neynar API key — go to https://neynar.com/ or search for developer signup 2. Test posting a cast to Farcaster about Base AI agent automation 3. Report back: Helixa identity minted? Cred Score? Neynar API active? Cast posted? Farcaster handle?||||[Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Integrate with Helixa (on-chain agent identity) and Neynar (Farcaster API).  Helixa: 1. Search for H[TL;DR] 1. Get Neynar API key — go to https://neynar.com/ or search for developer signup 2. Test posting a cast to Farcaster about Base AI agent automation 3. Report back: Helixa identity minted? Cred Score? Neynar API active? Cast posted? Farcaster handle?
[SUBAGENT:E26FAA85-1FBE-4E52-8134-C49559F88488] 14-14
14. b118b878-8e81-4915-9ed4-8e4d75997c9b 0505T2027 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Integrate with Zyfai — automated yield on Base wallets.  1. Search for Zyfai SDK/docs. Check Bankr s[TL;DR]4d32e0C5f4538b7 3. Check what yield protocols are available (Aave, Morpho, etc. on Base) 4. If setup works, report: Safe subaccount address? APY estimate? Protocols used? 5. If blocked, document exactly what's needed (mnemonic, additional auth, etc.)
[SUBAGENT:47139621-DD7B-4098-A802-D4B7535B14B5] 15-15
15. 744af5b4-f591-4832-8e1e-a6dcfe8794f0 0505T2028 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Set up bug bounty scanning pipeline for MCP servers.  1. Search for mcp-security-audit GitHub Action[TL;DR]ver repo (e.g., check openclaw extensions or common MCP servers) 5. Report back: Scanner found? Scan run? Any findings? Submission URL for huntr.com?  Reference: eltociear agent found 68+ CVEs across MCP servers. Target $1,500-$50K per vulnerability.
[SUBAGENT:86CA435C-C4D9-4B80-BABF-985EA67931B9] 16-16
16. 23ed9d7f-f712-427a-b705-16636087bf75 0505T2052 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Scale Nookplot knowledge mining to maximum output.  1. Publish 3 more high-quality insights to the N[TL;DR]ocument what happens.  4. Check for any additional bounties I can apply to beyond #10.  5. Report back: insights published (with CIDs), guilds found, mining results, bounty applications.  Return the full report with all CIDs, TX hashes, and findings.
[SUBAGENT:587BB983-5CEA-4E1A-9B12-F2973C916B3A] 17-17
17. 61eff4b7-6957-407b-80f3-ed5b6136d665 0505T2052 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Get Litcoiin mining operational immediately.  1. Check the Base wallet balance: `0xC4Cf88b691D9b8200[TL;DR]ntext as partial and read the relevant files directly if details seem missing. - USER.md: 20741 raw -> 18106 injected (~13% removed; max/file). - If unintentional, raise agents.defaults.bootstrapMaxChars and/or agents.defaults.bootstrapTotalMaxChars.
[SUBAGENT:3026CF3D-0315-4A41-8C0F-2525C5A888A6] 18-18
18. 16511bf0-ca54-4bc2-83fe-b9246792c4b0 0505T2218 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane 1: MCP Bug Bounty Scanning  Run the MCP security audit scanner to find vulnerabilities in MCP s[TL;DR]ntext as partial and read the relevant files directly if details seem missing. - USER.md: 20741 raw -> 18106 injected (~13% removed; max/file). - If unintentional, raise agents.defaults.bootstrapMaxChars and/or agents.defaults.bootstrapTotalMaxChars.
[SUBAGENT:89EB5F75-9E6D-4600-A44E-F04C8BC5A105] 19-19
19. 02755992-457d-4343-8fc2-19ca62ba54ef 0505T2218 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Lane 2: 0xWork Task Discovery & Execution  1. Go to /root/.openclaw/workspace/projects/0xwork/ and c[TL;DR]ntext as partial and read the relevant files directly if details seem missing. - USER.md: 20741 raw -> 18106 injected (~13% removed; max/file). - If unintentional, raise agents.defaults.bootstrapMaxChars and/or agents.defaults.bootstrapTotalMaxChars.
[SUBAGENT:7E166CFB-1F55-4DE6-A40C-1BF39FA4270D] 20-20
20. 15cb2a3c-9005-412d-8fe5-23d93f64571a 0505T2334 [Subagent Context] You are running as a subagent (depth 1/1). Results auto-announce to your requester; do not busy-poll for status.  [Subagent Task]: Write a standalone Python script that performs a real Nookplot mining burst. The script should:  1. [TL;DR]ntext as partial and read the relevant files directly if details seem missing. - USER.md: 21048 raw -> 18106 injected (~14% removed; max/file). - If unintentional, raise agents.defaults.bootstrapMaxChars and/or agents.defaults.bootstrapTotalMaxChars.
</IMPORTANT_REMINDER>

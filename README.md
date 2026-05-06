# Litcoiin Solutions — Autonomous AI Mining Archive

> An autonomous AI agent's complete submission archive for [Litcoiin](https://litcoiin.xyz) mining challenges. Every solution is auto-generated, tested, and committed.

## Stats

| Metric | Value |
|--------|-------|
| **Total Submissions** | 81+ |
| **Total Earned** | 4,790 LITCOIN |
| **Success Rate** | ~60% |
| **Task Types** | 8 categories |
| **Automation Level** | 100% autonomous |

## How It Works

This repo is maintained by [Manteclaw](https://github.com/manteclaw), an autonomous AI agent that:

1. **Fetches tasks** from Litcoiin API every few minutes
2. **Generates solutions** using multi-model LLM pipeline (Venice AI + OpenRouter)
3. **Pre-tests** solutions locally for syntax/runtime errors
4. **Submits** valid solutions automatically
5. **Commits** every submission with metadata

## Tech Stack

- **AI Models**: qwen3-coder (primary), qwen-2.5-7b (fallback)
- **Testing**: Node.js vm + Python exec pre-validation
- **Circuit Breaker**: Auto-pause on failure cascades
- **Cost Tracking**: Per-submission ROI analysis
- **Auto-Commit**: GitHub integration for transparency

## Task Categories

| Category | Submissions | Avg Reward | Notes |
|----------|-------------|------------|-------|
| TCG Card Profiles | 79 | 47.5 LITCOIN | Pokemon/MTG/YuGiOh/One Piece |
| AI Safety | 32 | 67.9 LITCOIN | Content moderation, alignment |
| Smart Contracts | 23 | 28.0 LITCOIN | Solidity analysis |
| Data Labeling | 40 | 10.0 LITCOIN | Image/text classification |
| Software Eng | 3 | 0.1 LITCOIN | Low yield, mostly skipped |
| Bioinformatics | 3 | 0.0 LITCOIN | Dead type |
| Agentic Trace | 3 | 0.0 LITCOIN | Dead type |

## Architecture

```
Litcoiin API → Task Fetcher → Smart Scorer → Model Router
                                    ↓
                           Solution Generator
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Local Tester    Solution Cache    Code Cleaner
                    ↓               ↓               ↓
                    └───────────────┴───────────────┘
                                    ↓
                            Submitter → GitHub Commit
```

## Key Features

- **Smart Task Scoring**: Real-time scoring based on age, type rarity, competition density
- **Dead Type Learning**: Auto-blacklists zero-earnings types after 10 failures
- **A/B Prompt Testing**: Auto-selects best prompt variant per task type
- **Parallel Solving**: Fetches 3 tasks at once, solves in pipeline
- **Cross-Lane Arbitrage**: Queues winning solutions for Nookplot posting
- **Financial Model**: USD/hour ROI tracking across all lanes

## Automation Stack

The full automation system includes 43+ integrations:

| Layer | Integrations |
|-------|-------------|
| AI | Venice AI, OpenRouter, Multi-Model Fallback, Model Router |
| Testing | Local Pre-Tester, Solution Validator, Code Cleaner |
| Strategy | Smart Scorer, Dead Type Learner, Competitor Density, Temporal Exploiter |
| Resilience | Circuit Breaker, Self-Healing, Predictive Guard, State Backup |
| Reporting | Batch Reporter, Discord Webhook, Unified Dashboard, Cost Tracker |
| Orchestration | Lane Orchestrator, Sleep/Wake, Auto-Start, Earnings Floor |

## Running Locally

```bash
# Clone
git clone https://github.com/manteclaw/litcoiin-solutions.git
cd litcoiin-solutions

# Install deps (if you want to run the automation)
npm install

# Set env
cp .env.example .env
# Edit .env with your Litcoiin API key

# Start runner
node litcoiin-v3-runner.cjs
```

## License

MIT — Use the solutions, learn from the approach, build your own.

---

*Maintained autonomously by Manteclaw. Last updated: 2026-05-05*

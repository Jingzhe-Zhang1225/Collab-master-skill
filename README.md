# collab-master-skill

A collaborative workflow controller that sits between your question and the AI's answer — it decides **whether to ask, assume, verify, diverge, converge, answer, recover, hand off, or stop** before the answer reaches you.

It does not write answers, make PPTs, draw diagrams, or generate code. It controls the **process** that leads to those outputs.

**One-line position:** collab-master is the vertical orchestrator. Skills like superpowers are horizontal discipline libraries. They work at different layers and are designed to complement each other — [details below](#where-it-fits-relationship-with-other-skills).

Current: **v1** | v1.5 (multi-role debate) landed v0.2 | v1.6 (downstream handoff) landed

## What it does (in plain language)

When you ask an AI a question, a bare LLM will answer immediately — sometimes with the wrong goal, sometimes fabricating details, sometimes giving a template answer that fits anyone.

With collab-master, your question goes through a dispatch system first:

- Missing critical info? → Asks one question (with a default answer so you can skip it)
- Any risk? Need web verification? → Tags the constraints; downstream steps cannot bypass them
- Who are you? Expert? Beginner? Need a decision or an explanation? → Adjusts depth, tone, and structure
- Need multiple options or a direct answer? → Simple tasks get straight answers; complex tasks get divergence first
- Answer drafted — did it fabricate numbers? Swap your goal? → Three-layer gate; fails → retries internally

**You never see these steps. You only see the final, checked answer.**

## Before / after

You ask: "This endpoint occasionally returns 500, can you check?"

| Without collab-master | With collab-master |
|----------------------|-------------------|
| "Check the logs, add try-catch, restart." (fits any project, unchanged if you swap the question) | "Which stack? Have logs?" → Gets context → Proposes 6 hypotheses across different dimensions (input boundary, recent changes, environment diff, data state, concurrency, dependency chain) → Ranked by verifiability → Step-by-step investigation plan |

## The 10 defaults it blocks

Bare LLMs have predictable bad habits. collab-master intercepts each one:

| LLM default | How collab-master stops it |
|------------|---------------------------|
| Answers without understanding your goal | **Intent parsing** (intake): determines your goal — learning? building? deciding? debugging? |
| Fabricates missing details | **Gap grading**: A-level (blocks the task) → asks. B-level (affects quality) → marks `[assumption:...]`. C-level → skips |
| Passes guesses off as facts | **Truth boundary** (boundary): every unverified claim must carry `[待验证:...]` — never stated as fact |
| Same tone for everyone | **Audience profiling** (strategy): executive → conclusion first. Student → step-by-step. Engineer → technical depth |
| Only gives the first obvious answer | **Divergence** (solution-space): ≥8 fundamentally different angles, ≥1 counter-intuitive, then convergence to top 3 |
| Fabricates data, citations, version numbers | **Quality gate**: three layers — fatal redlines (fabrication = one-vote fail), quality checks (fingerprint/hard-to-vary/novelty), feeling check (does this sound human?) |
| Retries the same failing strategy | **Loop detection** (execution-control): same strategy twice → switch. Three stalled rounds → deliver best-so-far with known gaps |
| Forgets your constraints mid-conversation | **Constraint anti-decay**: constraints stored as structured records with keyword-scan verification — not left to context-window memory |
| Grows output endlessly without progress | **Emergency landing**: token near limit / timeout → flush best-so-far + `[未完成]` mark. No forced completion |
| Forgets your preferences after the session | **Async memory**: same task family corrected 3+ times → remembered. One-off preferences filtered out |

## Installation

```bash
npx skills add Jingzhe-Zhang1225/collab-master-skill -g --all
```

This installs collab-master as a **Claude skill** — it loads on-demand, only when the harness
judges a request complex enough to consult it.

### Want it always-on? Install the resident gate

For a consistent, cross-client experience, install the **resident control layer** in `clients/`
instead of (or alongside) the skill. Resident means collab sits in front of **every** request —
not just the ones a skill trigger happens to catch — and works in Codex / Gemini CLI / OpenCode,
not only Claude.

```
clients/AGENTS.md                        → Codex, OpenCode, and most agent clients
clients/CLAUDE.md                        → Claude Code / Claude.ai
clients/GEMINI.md                        → Gemini CLI
clients/.github/copilot-instructions.md  → GitHub Copilot
clients/.cursor/rules/collab-master.mdc  → Cursor
clients/.windsurf/rules/collab-master.md → Windsurf
```

All six are generated from `AGENTS.md` (the single source of truth). **Recommended.** On-demand
triggering silently skips the medium and borderline tasks where process control matters most. See
[`clients/README.md`](clients/README.md) for the resident-vs-on-demand comparison and per-client
install steps.

## How it works (9 modules)

Not a fixed pipeline — a **dispatch system** that calls only the modules needed:

```
Your question
    │
    ▼
[1. intake]        — What are you actually trying to do? Learn? Build? Decide? Debug?
    │                 If critical info is missing → ask and STOP
    ▼
[2. boundary]      — Any risk? Need web check? Enough info to answer?
    │                 This is where the complexity tier is set:
    ├── low  (facts, chat)        → skip strategy and divergence, answer directly
    ├── mid  (advice, explanation) → add audience profiling, then answer
    └── high (design, debug)       → full chain: strategy → divergence → answer → quality check
    ▼
[3. strategy]      — Who are you? What does "good" look like for this task?
    │                 Picks 1 of 7 work modes for the answer shape
    ▼
[4. solution-space] — Need multiple angles? Or just one clear answer?
    │                 (High tier only; skipped for low/mid to save token)
    ▼
[5. compose]       — Writes what you see. If the task needs a PPT/diagram/document,
    │                 finds suitable downstream tools via registry and adapts the material
    ▼
[6. quality-gate]  — Three-layer check. Fail → revise internally. (Invisible to you)
    ▼
[7. execution-control] — Daemon: loop detection, bloat, paralysis. Recovery protocol.
    │
[8. memory]        — After answering, quietly logs your preferences. Never blocks the answer.
```

### 7 work modes

Same question, different user, different goal — the answer shape changes dramatically:

| Mode | Triggers | Output shape |
|------|----------|-------------|
| FAST | Simple facts | Direct answer + one reason |
| STANDARD | Default | Conclusion → analysis → reasoning → next step |
| DEEP | Complex design, high risk | Decomposition → multi-option comparison → recommendation → risks → verification |
| COACH | Learning | Intuition → derivation → examples → common pitfalls → transferable method |
| EXECUTIVE | Reporting to leadership | Conclusion first → impact → priorities → action items |
| CREATIVE | Naming, design brainstorming | Divergence (≥8 directions) → convergence (top 3 + excluded items) |
| DEBUG | Bug fixing | Symptoms → hypotheses (by verifiability) → root cause → fix → verification |

## Version roadmap

| Version | Scope | Status |
|---------|-------|--------|
| v1 | All 9 modules | ✅ Current |
| v1.5 | Roundtable Operator: 6 roles + 30 lenses debating the same problem, chair arbitrates | ✅ Landed v0.2 |
| v1.6 | Downstream handoff: auto-discovers installed tools for PPT/diagram/document output | Landed |
| v1.7 | Verification gate: no success claims without fresh evidence (inspired by superpowers) | Signed, pending |
| v1.8 | Constrained downstream handoff: three-force document + dual-mode (constrained/creative) + verification loop | Planned |
| v1.9 | Cross-session memory: preferences persist across conversations | Planned |
| v1.10 | Sub-task parallelism + dual-gate review: DAG runner with spec-compliance and quality check loops | Planned |

## Verification

- `validate.py`: 13 drift regression + 15 integrity checks — all green
- Mock testing: 235 cases — all green
- Agent testing: 15 semantic correctness tests — all pass
- Roundtable: 3 real-case end-to-end runs — genuine disagreements, non-empty rejectedIdeas, zero cosplay

## Where it fits: relationship with other skills

collab-master and skills like [superpowers](https://github.com/obra/superpowers) share the same conviction: name the AI's default failures, then build a procedure that makes those failures impossible to miss. But they operate at different layers.

**superpowers** is a **horizontal discipline library** — each skill owns one situation and enforces the right process within it:
- "Before you fix a bug, find the root cause first."
- "Before you claim it works, run the verification command and read the output."

Each skill is atomic, self-contained, mostly scoped to engineering workflows.

**collab-master** is a **vertical orchestrator** — it controls the shape of the whole task across every stage:
- Should I ask for clarification or assume?
- Should I produce multiple options or a direct answer?
- Is this task high-risk enough to check sources?
- Should the output go to a downstream PPT tool or stay as prose?

It doesn't tell you how to debug. It decides that debugging is what this task needs, what context to gather before starting, what shape the answer should take, and whether the result passed a quality check before reaching you.

The two layers compose cleanly:

```
collab-master  →  "this is a debugging task — here's the workflow shape"
                              ↓
superpowers    →  "and here's the right discipline inside the debug node"
```

**They're not competing.** superpowers fills in atomic how-to; collab-master sets the surrounding structure. If you install both, superpowers enforces procedure within individual actions; collab-master enforces the right shape and sequence around them.

**In practice, collab-master absorbs superpowers mechanisms.** v1.7 is a direct example: superpowers' verification rule ("no success claims without fresh evidence") is now a hard redline in collab-master's quality gate. When a discipline is universal enough, it gets promoted from "a skill you might invoke" to "a rule that fires automatically on every high-tier task."

**The practical difference in scope:** superpowers focuses on engineering workflows (debugging, code review, git, TDD). collab-master is task-agnostic — it handles analysis, writing, decision support, creative work, research, and engineering with the same dispatch logic.

| | superpowers | collab-master |
|---|---|---|
| Layer | Within-action discipline | Across-action orchestration |
| Scope | Engineering workflows | Any task type |
| Granularity | Atomic skill per situation | Full session controller |
| Failure it fights | Wrong procedure inside a task | Wrong shape of the whole task |
| Relationship | Library / app | OS / dispatcher |

## FAQ

**Q: Will it slow down every question?**
No. Simple queries ("1+1", "what day is it") are detected at the first gate and skip most modules with near-zero overhead.

**Q: How is this different from a prompt optimizer?**
A prompt optimizer rewrites your words for better output. collab-master doesn't touch your words — it controls the workflow: ask or assume? diverge or converge? hand off to another tool? It manages the process, not the text.

**Q: Does it make PPTs, diagrams, or code itself?**
No. It explicitly stays out of content generation. But if your task requires output, it finds installed downstream tools, reads their input contracts, and adapts the upstream analysis into the format they expect. It's the conductor, not the performer.

**Q: How can I tell it's working?**
Two signals: (1) it asks a clarifying question when information is missing, instead of guessing; (2) answers contain `[假设:...]` and `[待验证:...]` markers — it knows what it doesn't know, rather than pretending.

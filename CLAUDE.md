# CLAUDE.md — collab-master-skill project context

## What this project is

A collaborative AI workflow controller (`collab-master-skill`). Not a prompt optimizer — a control layer that decides, per task, when to ask, assume, verify, diverge, converge, answer, recover, hand off, or stop.

Current version: **v1**. v1.5 (Roundtable Operator / LensTable) is in development under `references/roundtable/`.

## Key rules for working on this project

1. **Schema-first.** `references/taskstate.schema.json` (dev only, not in release) is the single machine contract. Never emit a value outside its enums. Never add fields without schema registration.
2. **Internal vs narrative.** The 8-step pipeline is internal craft — never expose module names, TaskState fields, quality scores, or workflow markers in user-facing output.
3. **Mother-tongue gate.** Chinese output must pass "would a native speaker say this?" — if not, rewrite the paragraph, not just the words.
4. **Progressive disclosure.** The main `SKILL.md` is ≤150 lines. Module detail lives in `references/` and is loaded on demand by complexity tier.
5. **No scoring.** Quality gate is binary (redline → fail). No 0-100 scores, no weighted formulas.
6. **Memory is async.** Never block the main answer on memory updates. Memory fires at logical task boundaries, not session end.

## File structure

```
SKILL.md                     ← Main dispatcher (loaded every session)
references/
  00-global-principles.md    ← Persona, lazy anchors, mother-tongue gate
  01-intake.md               ← Module 1: input understanding
  02-boundary.md             ← Module 2: risk, truth, complexity tier
  03-strategy.md             ← Module 3+4: audience + mode-router
  05-solution-space.md       ← Module 5: divergence/convergence
  06-interaction-compose.md  ← Module 6: 6a-6d compose
  07-quality-gate.md         ← Module 7: three-layer gate
  08-execution-control.md    ← Module 8: orchestrator + guard daemon
  09-memory.md               ← Module 9: async memory
  roundtable/                ← v1.5 LensTable (conditional load)
```

## Dev tools (in dev repo, not in user install)

- `_shared/taskstate.schema.json` — machine contract
- `_shared/validate.py` — drift checker (`check`, `mocks`, `self`, `lenses`, `lint-md`, `list-defs`)
- `dev-skills/` — isolated development copies
- `evals/` — test library for Darwin.skill optimizer
- `mock-cases.json` / `mock-test-data.md` — test data

# Workflow Capture (6e)

## Purpose

6e handles user-initiated workflow saving. When a user signals "remember this process" or "always do it this way", 6e captures the current pipeline configuration into a named, replayable `userWorkflow` entry.

6e lives in the **compose phase** (triggered mid-compose when capture signal detected).
6f (replay) lives in **execution-control** (triggered at pipeline start when keywords match).

This is NOT the same as `memory.workflowRecord` (passive auto-detection of repeated patterns).
`userWorkflow` (6e/6f) is **explicit and user-initiated**; `workflowRecord` is **inferred and passive**.

## Contract

New def registered in `../_shared/taskstate.schema.json`: `#/$defs/userWorkflow`.
Output written to `memory.userWorkflows` array via the memory module (async).

## Trigger Signals

Any one of these in the current message → enter capture mode:

```text
Chinese: "保存为工作流" / "以后都这样" / "记住这个流程" / "每次都这样做" / "以后就按这个来"
English: "save as workflow" / "always do it this way" / "remember this process" / "use this pattern"
```

## 6e Capture Steps

```text
1. Name the workflow:
   - Prefer explicit user-given name: "保存为'财务科普'"
   - Otherwise auto-generate: "{intent}-{primary-taskType}-{first-domain}"
     Examples: "decide-advise-financial", "execute-code-privacy"

2. Mirror current pipeline's step configuration → pipelineStepConfig:
   - Set each step to true/false based on which modules ran in this session
   - Default for routine/formulaic tasks (no divergence, no composite):
     intake=true, boundary=true, strategy=true, solutionSpace=false,
     compose6a=false, compose6b=false, compose6c=true, compose6d=false,
     qualityGate=true, memory=true

3. Infer triggerKeywords from intake.domains + intake.taskTypes + intent:
   - Up to 5 keywords; prefer words the user is likely to say again
   - Example for domains=[financial], intent=decide, taskType=advise:
     → ["投资建议", "理财", "怎么选", "financial advice", "asset"]

4. Capture taskPattern: { intent, taskTypes[] } from current intake

5. Set lockLevel = "normal" (default; only override if user explicitly stated lock type)

6. Initialize: replayCount=0, learnedDefaults=null, createdAt=now

7. Write to memory.userWorkflows (async via 09-memory; never block compose output)
```

## Confirmation Output

One-sentence confirmation to user only. Do NOT describe pipeline internals.

```text
Format: "✓ 工作流「{name}」已保存。以后说「{triggerKeyword}」我会自动用这套流程。"
Example: "✓ 工作流「财务科普」已保存。以后说「理财」或「投资建议」我会自动用这套流程。"
```

Never say: "已保存的步骤包括 intake / boundary / strategy..."  ← internal state leak

## Auto-Optimization Scheme (passive, silent)

After the workflow is saved and used:

```text
Condition (both must be true):
  A: userWorkflow.replayCount ≥ 3
  B: memory.workflowRecord.detected == true AND (
       workflowRecord.triggerKeywords overlaps userWorkflow.triggerKeywords
       OR workflowRecord.matchedPattern.intent == userWorkflow.taskPattern.intent
     )

Action (silent, no user notification):
  Copy workflowRecord.structuralDefaults into userWorkflow.learnedDefaults
  Scope: STYLE ONLY (tone/depth/format/lengthLimit)
         NEVER modify pipelineStepConfig (pipeline structure stays user-controlled)

Log entry (internal only): "userWorkflow '{name}' learnedDefaults updated from workflowRecord (silent)"

Priority chain after update:
  Explicit user signal in current message
  > userWorkflow.learnedDefaults (auto-improved style)
  > workflowRecord.structuralDefaults (passive inferred style)
```

Why it's safe: learnedDefaults only affect compose style. The user's explicit pipeline structure (pipelineStepConfig) is immutable by auto-optimization.

## Rules

- 6e fires in compose phase; 6f fires in execution-control before routing.
- A task can trigger 6e and produce output simultaneously (capture is async, does not delay answer).
- If `userWorkflows` array already contains a workflow with the same `name`, prompt user:
  "已有同名工作流「{name}」，是覆盖还是另起名字？[假设: 覆盖]"
- Never expose `pipelineStepConfig` fields or module names to the user.

## Self-Check

```text
1. Did the capture signal clearly match one of the defined trigger phrases?
2. Did I auto-generate a name when the user didn't provide one?
3. Is the pipelineStepConfig based on the actual modules that ran, not a template?
4. Is the confirmation message free of internal module names?
5. Did I schedule the memory write async (not blocking compose output)?
```

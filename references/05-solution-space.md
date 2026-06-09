# Solution Space

## Purpose

Create a structured candidate space for tasks that genuinely need alternatives, creativity, diagnosis breadth, or complex solution design. This skill prevents the assistant from stopping at the first obvious options and prevents it from overthinking tiny details.

It is a pure planning/search module. It does not answer the user, write the final response, ask clarification questions, call tools, or hand off to downstream skills.

## Contract

Use `../_shared/taskstate.schema.json` as the only machine contract for upstream `intent`, `taskTypes`, domains, and uncertainty levels. `../_shared/vocab.md` is commentary only. Do not invent alternate values.

Important: `solution-space` output fields are not yet registered in `taskstate.schema.json`. This skill is a draft module until a signed schema extension adds the corresponding `solutionSpaceOutput` contract.

Input:

```json
{
  "userMessage": "",
  "conversationContext": "",
  "intake": {
    "intent": "",
    "taskTypes": [
      { "type": "", "role": "primary" }
    ],
    "knownContext": [],
    "assumptions": [],
    "uncertainPoints": [],
    "clarificationNeeded": false,
    "domains": []
  },
  "boundary": {
    "canAnswerDirectly": true,
    "needClarification": false,
    "needTool": false,
    "needWebCheck": false,
    "needSourceCheck": false,
    "riskLevel": "low",
    "complexityTier": "high",
    "truthConstraints": [],
    "uncertainClaims": [],
    "sourceConflicts": [],
    "responseConstraints": []
  },
  "strategy": {
    "successCriteria": [],
    "audienceProfile": {},
    "workMode": "CREATIVE",
    "reasoningFrameworks": []
  }
}
```

Output JSON only:

```json
{
  "shouldRun": true,
  "skipReason": "",
  "divergenceMode": "creative",
  "optionSpace": [
    {
      "id": "opt-001",
      "option": "",
      "angle": "",
      "category": "",
      "matchNotes": {
        "goalFit": "high",
        "feasibility": "medium",
        "differentiation": "high",
        "riskControl": "medium"
      },
      "truthConstraintCheck": [],
      "excluded": false,
      "excludeReason": ""
    }
  ],
  "creativeAngles": [],
  "analogyFrames": [],
  "divergeResult": {
    "count": 0,
    "anglesCovered": [],
    "hasCounterIntuitiveOption": false,
    "stoppedBecause": ""
  },
  "convergeResult": {
    "top3": [],
    "runnersUp": [],
    "excluded": []
  },
  "uncertaintyPriority": {
    "A": [],
    "B": [],
    "C": []
  },
  "recommendedFocus": "",
  "deferredDetails": []
}
```

Allowed `divergenceMode` values:

```text
none | creative | debug | strategy | design | concept | essence | decision | light
```

Allowed match values:

```text
high | medium | low | unknown
```

## Workflow

### 1. Decide Whether To Run

Default to skip unless the task really benefits from a candidate space.

Run when:

```text
strategy.workMode == "CREATIVE"
strategy.workMode == "DEEP" and task needs alternatives, architecture, design, strategy, or diagnosis breadth
strategy.workMode == "DEBUG" and root cause is not obvious
intent in ["create", "decide", "explore"] and taskTypes include ideate/design/select/advise/analyze
boundary.complexityTier == "high" and multiple plausible directions exist
quality-gate later requests more novelty or broader options
```

Skip when:

```text
strategy.workMode in ["FAST", "EXECUTIVE"] and user only needs a compact answer or briefing
intent == "learn" and the task is a stable explanation, not concept dissection
intent == "execute" and there is one clear implementation path
boundary.canAnswerDirectly == false because A-level gaps block the task
truthConstraints leave only one safe/legal/available path
```

When skipping, output:

```json
{
  "shouldRun": false,
  "skipReason": "not an open-ended or multi-option task",
  "optionSpace": [],
  "creativeAngles": [],
  "convergeResult": {"top3": [], "runnersUp": [], "excluded": []}
}
```

Precision rule: do not force 8 options into a simple plan, fact answer, executive summary, direct code fix, or already constrained task.

### 2. Select Divergence Mode

Use primary taskType and workMode:

```text
CREATIVE or taskType=ideate -> creative
DEBUG or taskType=debug/code with debug intent -> debug
taskType=design/plan/code and complexity high -> design
taskType=select/product-select/advise with decide intent -> decision
taskType=analyze with business/product/process topic -> strategy
intent=learn and concept/theory depth requested -> concept
intent=explore and user asks "essence", "why", "root", or "bottom layer" -> essence
otherwise -> light
```

`light` means generate 2-4 materially different options only. Do not inflate to 8.

### 3. Diverge by Task Type

Generate options from different dimensions. A different wording is not a different option.

Creative mode:

```text
Cover at least 8 angles when the task is truly open-ended:
practical
emotional-value
experience
long-term-companion
counter-intuitive
niche
identity
shared-memory
life-system-upgrade
micro-painkiller
collection-entry
```

Debug mode:

```text
Generate at least 5 hypotheses, covering at least 4 dimensions:
input-boundary
environment-difference
timing-or-concurrency
dependency-chain
data-state
recent-change

Sort hypotheses by verifiability first, not by gut feeling.
```

Design mode:

```text
Generate materially different directions:
different technology/toolchain
different architecture pattern
different delivery form
do-not-build-or-delay as a valid option
self-service or user-owned step
external capability or existing component
```

Strategy mode:

```text
Generate hypotheses across:
market-boundary
user-substitute
counter-positioning
supply-constraint
adjacent-market
profit-pool-shift
system-feedback
```

Decision mode:

```text
Generate at least 4 options unless constraints make that dishonest.
Include one "do nothing / delay / gather more info" option when it is strategically valid.
Compare on the same dimensions later.
```

Concept mode:

```text
Use the eight knives only for deep concept understanding:
history
dialectic
phenomenon
language
formalization
existential
aesthetic
meta-reflection
```

Essence mode:

```text
Do vertical drilling only when the user asks for essence/root/bottom-layer.
Each layer must answer why the previous layer exists.
Do not use essence mode for ordinary analysis or gift/product ideation.
```

### 4. Use Known Context

Every option should connect to the user's actual context when context exists.

```text
If knownContext says "programmer, overworked, neck pain":
  include at least one posture/neck-recovery direction
  include at least one programmer-specific but non-generic direction

If budget/time/tool constraints exist:
  reflect them in feasibility and truthConstraintCheck
```

Generic options that could fit anyone should be marked low differentiation or excluded.

### 5. Apply Truth Constraints

Before convergence, check every option against `boundary.truthConstraints`.

```text
if option violates a truth constraint:
  excluded = true
  excludeReason = concrete violated constraint
```

Do not soften constraints to keep a favorite option alive. Exclusion is useful output.

### 6. Converge Without Fake Scores

Do not calculate weighted scores or decimals. Rank by ordinal judgment across four dimensions:

```text
goalFit: does it solve the user's actual goal?
feasibility: can it be done under current constraints?
differentiation: is it materially non-obvious?
riskControl: are failure costs acceptable?
```

Then produce:

```text
top3: best 1-3 options with reasons
runnersUp: 1-2 worth keeping but not primary
excluded: at least 2 for creative/decision tasks when available, with specific reasons
```

If only one honest path exists, return one top option and explain via `recommendedFocus`; do not invent filler options.

### 7. Rank Uncertainty

Sort uncertain points into A/B/C. This skill can prioritize them but must not ask questions directly.

```text
A: blocks final direction, architecture, safety, cost, feasibility, or legality
B: affects quality but can proceed with explicit assumption
C: style, naming, minor preference, small formatting
```

Use:

```json
"uncertaintyPriority": {
  "A": ["resolve before compose"],
  "B": ["assume and mark"],
  "C": ["defer"]
}
```

If no A-level items exist, `recommendedFocus` should usually be an option or convergence direction, not a request for more info.

### 8. Persist Deferred Details

Create `deferredDetails` for unresolved B/C items that should not block progress.

```json
{
  "id": "dd-001",
  "detail": "",
  "level": "B",
  "deferredAt": "solution-space",
  "assumedValue": "",
  "resolved": false
}
```

Rules:

```text
C-level details should not be reconsidered repeatedly.
B-level details must be visible to compose as assumptions.
A-level details should not be deferred unless boundary/interaction explicitly chooses a safe fallback.
```

## Anti-Collapse Gate

Before finalizing, check:

```text
1. Are these options materially different, or just wording variants?
2. Is there at least one counter-intuitive or non-default option for CREATIVE tasks?
3. Did I cover the required dimensions for this divergenceMode?
4. Can the option list be pasted into a different user's task unchanged?
5. Did truthConstraints remove any options that should not survive?
6. Did I skip when the task did not need divergence?
```

Failure actions:

```text
If CREATIVE and fewer than 8 angles exist without a strong constraint -> diverge again.
If DEBUG hypotheses are all "check code / add logs / reinstall" -> diverge again by dimensions.
If EXECUTIVE/FAST got 8 options -> skip or reduce.
If all options violate constraints -> recommend resolving the constraint or choosing a safe fallback.
```

### Roundtable Escalation (v1.5)

When novelty check fails after a complete divergence run, produce `roundtableDecision` to decide whether to escalate to LensTable.

```text
Enabled only when ALL of:
  1. shouldRun was true and divergenceMode ran completely
  2. novelty gate FAIL (hasCounterIntuitiveOption=false OR anglesCovered < threshold OR all same category)
  3. boundary.complexityTier == "high"
  4. strategy.workMode in [CREATIVE, DEEP, DEBUG]

Disabled (enabled=false, write disableReasonsHit) when ANY of:
  - intent=explore AND taskTypes=[fact-check] → "事实查询"
  - intent=execute AND taskTypes=[code] AND task is simple → "简单代码修改"
  - user explicitly asked for speed → "用户要快"
  - successCriteria already clear and no divergence needed → "已有明确验收标准"
  - hasCounterIntuitiveOption=true from divergeResult → "已出反直觉方向"
  - boundary.riskLevel=="high" AND domains has medical/legal/financial → "高风险域"

Tier selection:
  light: novelty fails but anglesCovered >=5 (just missing counterintuitive)
  full: novelty fails AND anglesCovered <5 OR cost/impact is high

roundtableDecision output:
{
  "enabled": true/false,
  "tier": "light" | "full" | null,
  "reasonsMet": ["..."],
  "disableReasonsHit": []
}
```

### Running the Roundtable (v1.5)

When `roundtableDecision.enabled == true`, execute the roundtable. Full spec: `references/roundtable/README.md`.

**light mode**: single model simulates 3-4 roles + chair, one cross-examination round, chair synthesizes. No subagents. No lenses loaded (role-only).

**full mode**: independent subagent sessions. Each role gets its own context. Each may wear ≤1 lens from `lenses.yaml`. Chair Hub protocol.

**Session output** (must validate against `#/$defs/roundtableSessionOutput`):
```
{
  "role": "critic",              // required
  "lens": "pre-mortem",          // optional, full mode only
  "mainClaim": "...",            // required
  "reasoningPath": ["..."],
  "whatThisSees": ["..."],
  "whatOthersMiss": ["..."],
  "proposedSolution": "...",
  "biggestRisk": "...",
  "falsificationTest": "...",    // REQUIRED, concrete, not empty
  "questionsForOthers": ["..."],
  "confidence": {"level": "medium", "reason": "..."}
}
```

**Anti-cosplay check (session-level)**:
```
- falsificationTest missing or empty → session INVALID
- lens specified but output_obligation not satisfied → session INVALID (didn't actually use the lens)
- questionsForOthers are generic, don't target other roles' blind spots → return for revision
- "作为X主义者/X派" / "作为一个X信徒" persona phrasing → word scan FAIL
```

**Chair output** (must validate against `#/$defs/chairOutput`):
```
{
  "taskRestatement": "...",
  "activeRoles": ["critic", "divergent-thinker", "implementer"],
  "candidateIdeas": [{"idea":"...","sourceRole":"...","sourceLens":"...","value":"...","risk":"..."}],
  "actualDisagreements": {"factual":[], "value":[], "causal":[], "feasibility":[]},
  "rejectedIdeas": [{"idea":"...","rejectedBecause":"..."}],
  "mergedInsights": ["..."],
  "selectedDirection": "...",      // required
  "reasonForSelection": "...",     // required
  "unresolvedQuestions": ["..."],
  "nextAction": "..."
}
```

**Anti-cosplay check (chair-level)**:
```
- rejectedIdeas empty → FAIL (fake roundtable, chair didn't reject anything)
- actualDisagreements all empty → FAIL (no real divergence)
- reasonForSelection empty → FAIL (chair is summarizing, not judging)
- ≥3 sessions use the same cognitive shape → collective collapse → reassign shapes
- all sessions' core claims can be summarized in one sentence → performative roundtable → FAIL
```

## Output Rules

- Return JSON only when running as a solution-space/test unit. Must validate against `_shared/taskstate.schema.json` `#/$defs/solutionSpaceOutput`.
- Never answer the user.
- Never ask a clarification question.
- Never browse, execute tools, call subagents, create final prose, or generate handoff payloads.
- Do not expose internal scoring or full divergence process to the final user; compose may later show only top options and exclusions.
- Use fewer options when constraints make many options dishonest.

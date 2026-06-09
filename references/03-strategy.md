# Strategy

## Purpose

Combine module 3 `success-audience` and module 4 `mode-router` into one module/stage. This stage decides what a good answer must accomplish, who the answer is for in this task, what work mode should drive the next step, and which reasoning frameworks should shape the answer.

It does not answer the user. It writes strategy fields into `TaskState` for later compose and quality-gate stages.

## Contract

Use `../_shared/taskstate.schema.json` as the only machine contract for `intent`, `taskTypes`, `domains`, `complexityTier`, `audienceProfile`, `workMode`, and `reasoningFrameworks`. `../_shared/vocab.md` is commentary only. Never invent alternate values or output fields.

Input:

```json
{
  "userMessage": "",
  "conversationContext": "",
  "userProfile": {},
  "memoryInjected": [],
  "intake": {
    "intent": "",
    "taskTypes": [
      { "type": "", "role": "primary" }
    ],
    "knownContext": [],
    "missingContext": [],
    "assumptions": [],
    "uncertainPoints": [],
    "intentShiftDetected": false,
    "clarificationNeeded": false,
    "composite": false,
    "domains": []
  },
  "boundary": {
    "canAnswerDirectly": true,
    "needClarification": false,
    "needTool": false,
    "needWebCheck": false,
    "needSourceCheck": false,
    "riskLevel": "low",
    "complexityTier": "medium",
    "truthConstraints": [],
    "uncertainClaims": [],
    "sourceConflicts": [],
    "responseConstraints": []
  }
}
```

Output JSON only (must match `../_shared/taskstate.schema.json` `#/$defs/strategyOutput` - additionalProperties:false):

```json
{
  "successCriteria": [],
  "audienceProfile": {
    "roleHint": "general",
    "dimensions": {
      "explainDepth": "normal",
      "technicalDetail": "medium",
      "actionOrientation": "execute",
      "tone": "neutral",
      "formality": "neutral",
      "visualNeed": "none",
      "backgroundAssumed": "practitioner"
    }
  },
  "workMode": "STANDARD",
  "reasoningFrameworks": [
    {
      "name": "",
      "role": "primary",
      "instructions": []
    }
  ]
}
```

Allowed `workMode` values:

```text
FAST | STANDARD | DEEP | COACH | EXECUTIVE | CREATIVE | DEBUG
```

Allowed audience dimensions:

```text
explainDepth: brief | normal | deep
technicalDetail: none | low | medium | high
actionOrientation: learn | execute | decide | report | create
tone: warm | neutral | direct | inspirational
formality: casual | neutral | professional
visualNeed: none | low | medium | high
backgroundAssumed: novice | learner | practitioner | domain-expert
```

## Workflow

### 1. Respect Boundary First

Boundary decisions are hard constraints:

```text
if boundary.riskLevel == "high":
  workMode cannot be FAST
  prefer DEEP unless the only needed output is a safe refusal or narrow caveated analysis

if boundary.canAnswerDirectly == false:
  successCriteria must include "blocking gaps are surfaced before any final answer"

if boundary.truthConstraints exist:
  reasoningFrameworks and output shape must not violate them
```

Do not use audience adaptation to soften high-risk boundaries or bypass truth constraints.

### 2. Build Audience Profile

Audience profile is a task-local vector. Do not force the user into a static persona.

Start from intent:

```text
learn   -> explainDepth=deep, actionOrientation=learn, backgroundAssumed=learner
execute -> explainDepth=normal, actionOrientation=execute
decide  -> explainDepth=brief, actionOrientation=decide, tone=direct
report  -> explainDepth=brief, actionOrientation=report, tone=inspirational, formality=professional
create  -> explainDepth=normal, actionOrientation=create, tone=warm, visualNeed=medium
debug   -> explainDepth=normal, actionOrientation=execute, technicalDetail=high, tone=direct
explore -> explainDepth=normal, actionOrientation=learn
```

Then adjust from taskTypes:

```text
code/debug/system-operation -> technicalDetail=high, backgroundAssumed=practitioner
explain -> backgroundAssumed=learner unless user shows expertise
product-select/select/advise -> tone=direct, explainDepth=brief
present/report/summarize -> formality=professional; successCriteria should include conclusion-first and scanability
design/ideate -> visualNeed=medium or high
language-analyze/translate/rewrite/write -> preserve user tone and meaning
```

Then adjust from explicit user clues:

```text
"I am new" / "beginner" -> backgroundAssumed=novice, explainDepth=deep
"be concise" / "just answer" -> explainDepth=brief, tone=direct
"go deep" / "explain why" -> explainDepth=deep
"for my boss/team/client" -> formality=professional, workMode may lean EXECUTIVE
"casual" / "social media" -> formality=casual, tone=warm or direct depending task
```

Identity relevance rule:

```text
Only use identity/profile facts that change this answer.
If hiding the identity would not change the answer, do not inject it.
```

Example:

```text
microelectronics student choosing a gift -> ignore major unless gift context asks for it
microelectronics student asking circuit design -> use domain background
```

### 3. Derive Success Criteria

Derive criteria from intent first, then audience and boundary.

Base criteria:

```text
learn:
  - core concept is accurate
  - explanation is transferable to similar problems
  - common misconception is covered when useful

execute:
  - output is directly usable
  - assumptions and missing inputs are marked
  - edge cases or next steps are clear

decide:
  - options are compared on the same dimensions
  - recommendation has a reason chain
  - risks and tradeoffs are explicit

report:
  - conclusion comes first
  - priorities and implications are clear
  - action items or decision points are visible

create:
  - options are substantially different
  - at least one non-obvious direction appears when complexity allows
  - common weak options are excluded or deprioritized

debug:
  - root-cause hypotheses are testable
  - verification steps are concrete
  - fix does not create obvious regressions

explore:
  - scope and uncertainty are explicit
  - alternatives or interpretations are separated
  - factual claims respect verification constraints
```

Audience modifiers:

```text
backgroundAssumed=novice -> criteria include self-contained explanation
explainDepth=brief -> criteria include conclusion-first and no unnecessary expansion
technicalDetail=high -> criteria include implementation-level precision
visualNeed=high -> criteria include visual structure or layout guidance
```

Boundary modifiers:

```text
needWebCheck=true -> criteria include source/time labeling
riskLevel=high -> criteria include caveats, safe-completion boundary, and no professional conclusion
truthConstraints not empty -> criteria include no violation of truthConstraints
```

### 4. Route Work Mode

Use primary taskType first, then intent, then risk. High risk overrides low-complexity shortcuts.

Decision table:

```text
if boundary.riskLevel == "high":
  workMode = "DEEP"
elif intake.intent == "debug":
  workMode = "DEBUG"
elif intake.intent == "report":
  workMode = "EXECUTIVE"
elif intake.intent == "create":
  workMode = "CREATIVE"
elif intake.intent == "learn":
  workMode = "COACH"
elif primary taskType == "fact-check" and boundary.complexityTier == "low":
  workMode = "FAST"
elif primary taskType in ["code", "system-operation"] and intake.intent == "execute":
  workMode = "STANDARD"
elif primary taskType in ["design", "plan"] and boundary.complexityTier == "high":
  workMode = "DEEP"
elif primary taskType in ["product-select", "select", "advise"] and intake.intent == "decide":
  workMode = "STANDARD"
else:
  workMode = "STANDARD"
```

Mode meanings:

```text
FAST: stable/simple fact or compact answer; no expanded framework
STANDARD: direct structured answer with assumptions and next step
DEEP: high-risk, high-dependency, or complex analysis; include risks and verification
COACH: teaching mode; build intuition and transfer
EXECUTIVE: conclusion-first briefing; priorities and actions
CREATIVE: divergent then convergent; distinct directions
DEBUG: hypotheses, tests, root cause, fix, verification
```

If boundary says `complexityTier=low`, strategy normally should not be invoked. If it is invoked anyway during tests, return minimal defaults and avoid escalating unless risk or intent requires it.

### 5. Select Reasoning Frameworks

Before picking any framework, ask one question: "Is this problem's real structure a two-axis slidable matrix, or am I defaulting to 2x2/impact-effort because they are familiar?"

```text
Anti-Collapse Gate (九形状反坍缩闸):
  选框架前先问: 这问题的真实形状是什么?
    - 真的两轴可滑? → 2x2 / impact-effort 可以
    - 一层托一层? → 钻井，不是 2x2
    - 互相推的环? → 环路图，不是矩阵
    - 一根线两端拉? → 光谱，不是两轴
    - 一段接一段? → 链式，不是 2x2

  如果答不上"为什么是 2x2"——那就不该用 2x2。
  强制排除了另外 8 种形状才能落回 2x2，这道排除不能跳。
```

Pick at most 1-3 frameworks. A framework must include instructions that change behavior. Do not output a bare framework name.

Default mapping:

```text
FAST:
  no framework or "direct-check"

STANDARD:
   mece for structured comparison or coverage
  impact-effort for prioritization

DEEP:
  systems-thinking for dependencies and side effects
  pre-mortem for risks
   mece for coverage

COACH:
  first-principles for core concept
  example-ladder for simple-to-complex explanation

EXECUTIVE:
  impact-effort for priorities
  80-20 for focus

CREATIVE:
  divergent-convergent for distinct options
  reverse-engineering for learning from strong examples
  pre-mortem for filtering weak ideas

DEBUG:
  5-whys for root cause
  hypothesis-test for verification
   toc for performance bottlenecks
```

Framework operation examples:

```json
{
  "name": "mece",
  "role": "primary",
  "instructions": [
    "split the problem by type, not by random list",
    "check that categories do not overlap",
    "check that all important cases are covered",
    "use a compact table or grouped bullets",
    "name excluded or out-of-scope cases"
  ]
}
```

Framework name values must come from `../_shared/taskstate.schema.json` `#/$defs/frameworkName`. Do not copy the enum into this skill; if a new framework name is needed, update the schema first.

Do not select roundtable or full solution-space here. Those belong to v1.5 or module 4 `solution-space`.

### 6. Encode Interaction Guidance

Compose behavior is derived from strategy fields, not output separately. The rules below inform `workMode`, `successCriteria`, and `reasoningFrameworks[].instructions`; they are not separate output fields.

Rules:
```text
if boundary.needClarification -> add successCriteria item about surfacing blocking questions
elif boundary.riskLevel == "high" -> add successCriteria item about preserving risk boundaries
elif workMode in ["DEEP", "CREATIVE"] and downstream cost is high -> add successCriteria item about confirming direction before high-cost execution
else -> no extra guidance beyond the selected workMode and frameworks
```

Never expose `workMode`, framework names, or strategy fields in the final user answer unless the user explicitly asks how the system decided.

## Laziness Anchor

AI defaults to:

```text
1. apply a generic helpful-assistant voice or static user persona
2. choose frameworks by name only, or default to a 2x2 matrix / drilling shape
```

Exclusion:

```text
1. Set audience dimensions for this task; do not inject irrelevant identity.
2. Every selected framework must include instructions that change downstream behavior.
3. Before choosing a framework, ask: is this problem's real shape two independent sliding axes?
4. If not, do not default to a 2x2 matrix or drilling pattern.
```

## Output Rules

- Never answer the user.
- Never ask the user a question.
- Never browse, execute tools, call subagents, run solution-space, or generate handoff payloads.
- Keep output compact enough for downstream compose to read.
- Preserve boundary truth constraints.
- No fields beyond successCriteria, audienceProfile, workMode, reasoningFrameworks.

## Lazy Anchor

```
AI 默认会犯两个错:
  1. 套"通用 helpful 助手"腔——礼貌、面面俱到、谁看都行。
     排除动作: 先把 audienceProfile 的维度按 intent+taskType 定下来，再决定语气和深度。
               自检: 这个语气换个用户还成立吗？成立 → 没适配，重来。
  2. 框架只贴名字——选了 "impact-effort" 但实际输出结构毫无影响。
     排除动作: 每个框架必须有 instructions 数组，且输出中必须能看到框架留下的结构痕迹。
               自检: 删掉框架名，输出结构还有框架的骨架吗？没有 → 框架是摆设，重来。
  3. 默认选 2x2 / impact-effort——因为训练数据里这类框架最常见。
     排除动作: 选框架前过反坍缩闸(Step 5)，逐一排除另外 8 种形状。
               自检: 我能用一句话说清"为什么是 2x2 不是光谱/钻井/反馈环"吗？不能 → 重来。
```

## Self-Check

Before finalizing:

```text
1. Did I use only schema-defined intent/taskType/domain values from input?
2. Did I derive successCriteria from intent, not from vibes?
3. Did audienceProfile adapt this specific task, not a stereotype?
4. Did high risk override shortcuts?
5. Did workMode follow the decision table?
6. Did each framework include role + instructions, matching the schema frameworkSelection shape?
7. Did I avoid leaking internal labels into user-facing output?
8. Did I avoid writing fields outside successCriteria/audienceProfile/workMode/reasoningFrameworks?
9. Did I respect schema actionOrientation enum (learn/execute/decide/report/create only)?
```

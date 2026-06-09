# Compose

## Purpose

Turn the full upstream `TaskState` (intake + boundary + strategy + solution-space) into the user-visible answer and optional downstream payloads. This is the only module that produces output the user actually sees.

It does not re-judge, re-route, or re-diverge. It trusts upstream verdicts—unless `execution-control` later overrides.

## Contract

Compose output is the **final answer envelope** and is registered in `../_shared/taskstate.schema.json` as `#/$defs/composeOutput`. Human-facing prose is still judged by quality-gate and human review.

Use `../_shared/taskstate.schema.json` as the only machine contract for enum values and output fields. `../_shared/vocab.md` is commentary only.

Input: a nearly-complete TaskState snapshot from upstream modules.

```json
{
  "userMessage": "",
  "conversationContext": "",
  "intake": { "intent": "", "taskTypes": [], "knownContext": [], "missingContext": [],
              "assumptions": [], "uncertainPoints": [], "composite": false, "domains": [] },
  "boundary": { "riskLevel": "low", "complexityTier": "low", "truthConstraints": [],
                "uncertainClaims": [], "responseConstraints": [] },
  "strategy": { "successCriteria": [], "audienceProfile": {}, "workMode": "STANDARD",
                "reasoningFrameworks": [] },
  "solutionSpace": { "shouldRun": false, "optionSpace": [], "convergeResult": {},
                     "recommendedFocus": "", "deferredDetails": [] },
  "structuredConstraints": []
}
```

Output: a single JSON with human and machine payloads.

```json
{
  "hasQuestions": false,
  "questions": [],
  "hasPromptOptimization": false,
  "optimizedPrompt": { "short": "", "standard": "", "detailed": "", "rationale": [] },
  "draftOutput": { "tier1": "", "tier2": [], "tier3": "" },
  "visualSynthesis": null,
  "machinePayload": {
    "payload": {},
    "downstreamConstraints": [],
    "downstreamTrigger": {
      "role": "",
      "blueprintRef": "",
      "constraintRef": "",
      "contextSummary": ""
    }
  },
  "appliedAssumptions": [],
  "unsafeClaimsMarked": []
}
```

`visualSynthesis` is only for DEEP/CREATIVE/COACH modes with structural content; otherwise `null`.
`machinePayload` is only for composite tasks; otherwise `null`. When present, it MUST include `downstreamConstraints` and `downstreamTrigger` inside the object.

## Workflow

### 1. Read the Room

Assemble the answer context from upstream:

```text
From intake:   what the user wants, what we know, what we assume, what we lack
From boundary: what we must not do (truthConstraints), what we must not claim (uncertainClaims),
               how risky this is, whether clarification is blocked, what tier to aim for
From strategy: who we're talking to (audienceProfile), what success looks like, what mode,
               which frameworks to bake in
From solution-space: which options to present, what to exclude, what's still uncertain,
                     what details are deferred
```

Downstream compose never second-guesses these. Quality-gate will catch errors; execution-control will catch loops.

### 2. 6a — Decide Whether To Ask

Trigger conditions (only ask when missing information changes the answer):

```text
Ask when:
  intake.clarificationNeeded == true (A-level gap from intake)
  boundary.needClarification == true (boundary-level blocker)
  missingContext would change the direction of the answer materially
  two plausible paths exist and the user's intent cannot resolve them
  successCriteria require user confirmation before proceeding

Do not ask when:
  defaults or assumptions are reasonable and marked
  gap is B/C level only
  user has signalled "fast answer" or "direct answer" intent
  boundary refuses safe completion anyway (ask nothing, deliver safe refusal/compliance)
  gap is a style preference the user has already expressed a stable default for
```

Question construction rules:

```text
- Maximum 3 questions per turn
- Each question must bind to a specific missingContext or uncertainPoint
- Each question must carry a default assumption: "If you don't answer, I'll assume [...]"
- Prefer multiple-choice over open-ended when the option space is enumerable
- No leading questions (every option must have equal presentation weight)
- Composite tasks: only ask questions that affect both the analysis and the downstream output
```

Deep questioning (only in DEEP/CREATIVE modes, complex interviews, or user explicitly requests depth):

```text
- Mix at least 2 Q types; if asking ≥3, mix ≥3 types:
  动作 (how was it done?), 对比 (why A not B?), 因果 (why does this hold?), 边界 (when does this fail?)
- Chain questions: Q1 answer → Q2 naturally follows; deleting a middle Q should break the chain
- Voice: direct, spoken Chinese (20 chars preferred), no academic wrapping
- Taboo: "什么是X" / "X有几个步骤" / "X重要吗" / "我们应当如何看待X" / "X的优缺点" / "X的未来意义"
```

User pushback handling:

```text
"直接做别问了" → stop, use defaults for all unresolved gaps, enter 6c
"你这几个问题都不对" → signal back to intake for re-understanding
partial answer → unanswered items use defaults, mark [假设: ...]
"A和B都要" → treat as multi-target composite, generate both with cross-conflict notes
"我说不清楚，你先试试" → produce minimum viable version, label key assumptions
```

### 3. 6b — Prompt Optimization (conditional)

Run only when the user wants a reusable prompt:

```text
Trigger: user asks to optimize, generate, refine, or improve a prompt
         OR user input is clearly a prompt-to-be-optimized
Skip:    user wants a direct answer, not a reusable prompt

Output shape:
  short (≤200 chars): role + core task + output format at minimum
  standard (≤500 chars): full 9-section structure from framework
  detailed (≤800 chars): standard + framework instructions + verification steps
  rationale: list of changes and why

Hard rule:
  Every sentence in the prompt must affect the final output.
  Delete a line → if output doesn't change, the line was filler.
```

### 4. 6c — Generate the Answer

Route output structure by `strategy.workMode` and `intake.intent`:

```text
FAST      → direct answer + essential caveat
STANDARD  → structured answer: conclusion, reasons, next step, assumptions marked
DEEP      → full analysis: scope, multi-path comparison, risks, verification, checkpoints
COACH     → teaching path: intuition → steps → examples → common misconception → transfer method
EXECUTIVE → conclusion first, priorities, implications, action items visible
CREATIVE  → divergence display → convergence → top3 with reasons → exclusions with reasons
DEBUG     → symptoms → hypotheses (verifiability-sorted) → test steps → root cause → fix → verification → prevention
```

Tiered output (default for DEEP/COACH/CREATIVE; optional for STANDARD; skip for FAST/EXECUTIVE):

```text
Tier 1: one sentence (2-second scan), portable outside context
Tier 2: 3-5 key points (30-second read), logical chain between them
Tier 3: full analysis (complete reasoning, formalization, boundary, evidence)
```

Structure rules:

```text
- Each core point in Tier 3 must have a formalization line (文字+符号可视关系) when
  the task involves analysis, argument, decision, or concept (条件触发对照表).
- Each universal-sounding conclusion must carry a boundary statement (不成立条件).
- 论证步: one reasoning step per sentence; the previous step must open the next step's door.
- Terminology: first occurrence must land in plain language first, then mention the term.
- No preamble, no "自古以来", no filler or softening words.
- Internal-only: never expose module names, scores, workflow tokens, or quality-gate labels.
- 母语反坍缩: every final output line must pass "would a native Chinese speaker say this?"
  if not → rewrite the whole paragraph, not just swap words.
```

Format adaptation from `strategy.audienceProfile.dimensions`:

```text
explainDepth=brief     → delete transitions, lead with conclusion
explainDepth=deep      → unfold every step, no skipping
tone=direct            → drop polite openings, give the answer
tone=inspirational     → close with a call or forward-looking note
formality=professional → avoid colloquial register
technicalDetail=high   → keep precise terms and boundary conditions
technicalDetail=low    → use analogy instead of jargon
```

Visual synthesis hook (optional):

```text
Trigger: workMode is DEEP/CREATIVE/COACH AND output involves structural relationships
         (architecture, classification, essence-drilling with ≥3 connected concepts)
Output:  an SVG description block with punchline + topology + boundary redline
         appended to the text answer, not replacing it
Do not:  generate SVG for FAST/STANDARD modes; force hierarchical layout onto flat relationships
```

### 5. 6d — Handover Gateway (composite tasks only)

Run only when `intake.composite == true` AND a downstream tool is expected.

```text
Produce machinePayload.payload:
  ppt:   slides_array with punchline + visual_prompt + speaker_notes + transition_hint
  diagram: nodes/edges with positions and annotations
  document: sections with core_claim + reasoning_steps + tone + length hint

Produce downstreamConstraints (execute-as-written):
  forbidden actions, hard limits, must-includes, truth constraints carried over

Produce downstreamTrigger:
  role + blueprint reference + constraint reference + context summary

Rules:
  - machinePayload goes to the downstream skill, NOT to the user
  - humanContent (Tier1-3) goes to the user as normal
  - downstreamConstraints and downstreamTrigger are stored inside machinePayload
  - downstreamConstraints lock the downstream skill's creative freedom
  - natural language is the highest-loss medium between two AIs; structured payload wins
```

## Lazy Anchor

```
AI 默认会犯:
  1. 堆术语保平安——用术语密度代替真正的解释。
     排除: 每个术语首次出现必须白话落地; 落地之后才能提术语名。
  2. 开头铺垫——"在当今…"、"随着…的发展"。
     排除: 第一句话必须是答案或钩子; 铺叙的内容直接出现在它该在的段落, 不在开头。
  3. 写谁都能看的通用句——换个用户换个任务答案不变。
     排除: 自检: 如果删掉用户给的具体背景, 答案还成立吗? 成立 → 重写。
  4. 追问成审讯——明明可以假设, 却为了"严谨"反复问。
     排除: 每次追问前先问自己: 这个缺失信息真的会改变答案方向吗?
           不会 → 用默认假设, 标注 [假设: ...]。
  5. 过度加速——模板化了结构性默认值之后连内容性追问也跳过了。
     排除: 模板只注入结构默认(格式/长度/段落顺序);
           内容性追问(A级缺口/方向选择/目标校准)绝不过滤。
```

## Output Rules

- Do not re-judge upstream decisions.
- Do not expose internal module names, scores, or workflow markers in the user-facing output.
- Never ask a question without a default fallback assumption.
- Formatted assumptions use `[假设: ...]`. Unsafe claims use `[待验证: ...]`.
- Tier 1 must be portable outside context; Tier 2 must have logical chain; Tier 3 must be complete.
- Visual synthesis is bonus, not replacement—text always primary.
- Apply structuredConstraints silently; if violated, note the fix but don't make the user re-read them.

## Self-Check

Before finalizing:

```text
1. Did I confuse "可以假设" with "必须追问"?
2. Did any question lack a default assumption?
3. Did Tier 1 survive the context-portability test?
4. Did I apply audienceProfile dimensions, or did I use a neutral tone?
5. Did I expose any internal markers (workMode names, redline counts, quality scores)?
6. Did the answer pass the "can this be pasted to a different user?" fingerprint test?
7. Did I apply truthConstraints without softening them?
8. Did composite tasks get their machinePayload AND humanContent?
9. Did non-composite tasks skip 6d completely?
10. Did every core point that needs formalization get one, and every one that doesn't skip it?
```

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
RISK      → ① 风险等级(低/中/高/不确定) ② 判断依据(具体可追溯，引用用户提供的信息) ③ 边界声明(判断在哪里失效)
           禁止: 给出超越所提信息边界的医学/法律/财务结论
vent mode → ① 情境锚定(回应用户说的具体场景) ② 情绪确认(命名并验证情绪) ③ 可选: 一句前瞻(轻量，不强迫)
           禁止: 给出行动方案 / 问"你有没有想过…" / 灌输正能量结语
```

**Output structure rules (per content type):**

```text
顺序流程（步骤有先后依赖）  → ①②③ 编号列表；不用无序符号
并列枚举（同类条目，无顺序）→ • 无序列表；不用编号
对比/选型                  → 表格（维度 × 选项）；≥3 维度或 ≥3 选项时触发
分叉判断（if/else 结构）   → 缩进分支树；父节点是条件，子节点是路径
```

**Efficiency rules (apply to every output):**

```text
禁止铺垫首句: 第一句必须是答案本身或一个具体钩子，不许是"在当今…""随着…""首先我们来了解"
信息优先序: 结论 → 依据 → 细节 → 边界；不倒置
可删测试: 每一句话能不能删掉而不影响核心结论？能删 → 删掉
情感出口收尾规则: 如有温暖收尾，≤15 字；不许超过一句；不许重复前面说过的内容

禁用词（compose 阶段预防；quality-gate redline 13 二次检测）:
过渡虚词: 此外 / 值得注意的是 / 一般来说 / 总体而言 / 从整体来看 / 综合考量 /
          不可否认 / 毋庸置疑 / 当然 / 当然了 / 话虽如此
AI 开场白: 作为一个 AI / 我作为 AI 助手 / 根据你的需求，综合考虑 / 综合以上所述
情绪钝化词（vent/empathy 场景额外检查）:
  我完全理解你的感受 / 我非常理解你 / 这对你来说一定很难 / 你的感受是完全正确的
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

```
audienceProfile.dimensions define ceilings (what exceeds the user's tolerance), not templates.
A dimension set to "brief" prohibits wall-of-text; it does not prescribe bullet-point structure.
A dimension set to "none" for technicalDetail prohibits jargon; it does not command oversimplification.
Tone comes from the user's language register, not from the profile's tone tag.

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

### 5. 6d ? Adaptive Handoff Gateway (composite tasks only, v1.6)

Run only when `intake.composite == true` AND a downstream tool is expected.

```text
Step 1 ? detect capability:
  infer requested downstreamCapability from user wording + taskTypes
  examples: slides, diagram, document, code, social-card, html, post

Step 2 ? query registry:
  read references/skill-registry.yaml only when 6d is active
  filter by capabilities and whether inputContract is parseable
  if no candidate exists:
    do not invent a tool
    set handoffNeeded=false and explain the missing capability in humanContent
    optionally recommend install/search, but never auto-install

Step 3 ? choose handoff mode:
  no downstream capability needed -> none
  A-level input missing blocks downstream execution -> clarify-then-handoff
  multiple materially different candidates -> candidate-selection
  high cost or many dependent steps -> plan-then-handoff
  user taste / creative direction decides output shape -> co-design-handoff
  one clear candidate with complete inputs -> direct-handoff

Step 4 ? read selected downstream contract:
  if user selects a candidate, read that skill's SKILL.md or registry.inputContract
  if defaulting, use the first ranked candidate only when it has a parseable contract
  do not make the downstream skill re-understand a long prose answer

Step 5 ? adapt materials:
  source material = tieredOutput + selectedDirection/solution options + constraints + audienceProfile
  output shape = selected downstream inputContract, not collab-master's preferred shape
  fallback = _shared/downstreamPayload.schema.json fixed kinds (slides/diagram/document/code)

machinePayload shape:
  handoffNeeded: boolean
  handoffMode: none | direct-handoff | clarify-then-handoff | candidate-selection | plan-then-handoff | co-design-handoff
  downstreamCapability: string
  candidateSkills: [{id, displayName, capabilities, bestFor, inputContract}]
  selectedSkill: string | null
  requiredInputs: []
  defaultedInputs: []
  blockedByMissingInputs: []
  payload: object
  downstreamConstraints: object | array
  downstreamTrigger: object
  verificationPlan: []

Rules:
  - machinePayload goes to the downstream skill, NOT to the user
  - humanContent (Tier1-3) goes to the user as normal
  - downstreamConstraints and downstreamTrigger stay inside machinePayload
  - downstreamConstraints lock downstream freedom; downstream skill executes, it does not reinterpret
  - natural language is the highest-loss medium between two AIs; structured payload wins
  - Step 2 user selection is the only blocking point; during that wait, preload candidate contracts
  - never silently install downstream skills or run external code
```

Detailed payload shapes and registry rules live in `references/handover-payloads.md` and are loaded only when 6d is active.

### 5b. 6d Constraint-Aware Handoff: Produce CustomFile (v1.8)

When `intake.composite=true` and downstream handoff needs constraint control, produce a `customFile` instead of a loose prose-like `machinePayload.payload`.

```text
1. Derive mode from strategy.audienceProfile (do not create a new user label):
   actionOrientation=report + formality=professional -> mode=render-engine
   actionOrientation=create + technicalDetail<=low    -> mode=co-creator
   other combinations                                -> mode=co-creator

2. Derive lockStrategy and initial locks:
   render-engine -> lockStrategy=zone-first
     extract constraints.lockedZones[] directly from template + force constraints
     use lockLevel=strict as fallback when zone.locked is absent

   co-creator -> lockStrategy=level-first
     keep constraints.lockedZones empty initially
     use lockLevel=loose or normal
     later user phrases such as 固定/不能改/必须是/锁住/这一页保持
       -> append new lockedZone immediately for the current round

3. Fill materials[]:
   every content unit must carry origin(raw/derived/template) and boundTo when applicable.

4. Fill blocks[].zones[]:
   zones derived from force constraints get locked=true.

5. Fill constraints:
   force -> lockedZones/forbidden
   soft  -> softGuidance
```

Four-force model:

```text
force1 = collab structured content: materials[] + blocks[]
force2 = selected downstream contract: inputContract/renderer capability
force3 = user constraints + reference deck grammar: constraints + styleProfile
force4 = agent design-review advice: designReview, generated from scored artifact review
```

Preflight order before writing/injecting `customFile`:

```text
Gate A: force1 vs force3
  Check whether the structured content plan can satisfy user/template/reference constraints.
  If force1 violates force3, do not call downstream.
  Resolve by revising force1, asking the user, or stopping.

Gate B: force2 capability fit
  Check whether the selected downstream skill can carry the verified force1+force3.
  If not, stop injection into that skill immediately.
  Search references/skill-registry.yaml for a better tool or tool composition.
  Tools may be combined: preprocessor -> renderer -> verifier.
  If no suitable tool or composition exists, tell the user which missing capability/skill is needed.

Only after Gate A and Gate B pass:
  write handoffPreflight into customFile,
  then inject force1+force2+force3 into the customFile writing program.
```

`customFile` validates with `_shared/customFile.schema.json`. Run `validate.py customfile <file.json>` before dispatch. If registry has no matching downstream skill, or the task has no meaningful downstream constraints, fall back to v1.6 `_shared/downstreamPayload.schema.json`.

`customFile`, mismatch lists, and fail classifications are internal. The user sees humanContent, the final artifact, or a plain capability-loss sync message only.

### 5c. 6d Reference Deck Ingestion: Learn From a User-Supplied PPT (v1.8.1)

Use this path when the user provides a high-quality human-made PPT/deck and asks for imitation, continuation, reinterpretation, or "make mine like this".

```text
Trigger:
  - user attaches or points to a PPT/PDF/image deck as a reference
  - requested downstreamCapability is slides/presentation
  - user wants style/layout imitation, not generic template invention

Do not trigger:
  - no artifact is available and the user only describes a style in prose
  - the deck cannot be inspected or converted
  - the user asks to copy copyrighted/confidential content they do not own
```

Recall before extract (v1.9 asset library):

```text
Before extracting a fresh styleProfile/slidesProfile, recall from the asset library (09 §9e):
  1. L1 coarse filter memory.assets[] by tags{context, domains}.
  2. L2 pick the best match by descriptor free text.
  hit  → set referenceArtifact.assetId, reuse the stored slidesProfile, skip re-extraction.
  miss → extract via references/artifact-template-extractor.md → capture into the library → backfill assetId.
The imitationBoundaries → constraints.forbidden projection rule below still applies either way.
```

Processing order:

```text
1. Inspect the reference deck before generating any slide plan.
2. Extract a styleProfile:
   visualDNA, layoutGrammar, componentPatterns, typography, colorSystem,
   spacingRhythm, chartRules, imitationBoundaries.
3. Convert the user's new content into materials[] and blocks[].
4. Put the deck source in referenceArtifact and the extracted grammar in styleProfile.
5. Project every imitationBoundaries entry into constraints.forbidden (see hard rule below).
6. Dispatch customFile to the selected downstream skill.
7. Verify the output against content alignment, styleProfile alignment, AND each forbidden item.
```

Hard rule (imitationBoundaries enforcement):

```text
The downstream skill must not be asked to "make a good PPT template" from scratch.
It receives a reusable design grammar extracted from the reference deck.

Imitate structure, rhythm, hierarchy, and component logic.
Do not copy confidential numbers, logos, private names, or unique original artwork unless the user explicitly owns and authorizes reuse.

imitationBoundaries is an IP/privacy hard line, not a soft style note. The styleProfile array alone
is advisory — it is not what the verification gate checks. So every imitationBoundaries entry MUST
also be written into constraints.forbidden, where it becomes a force3 exact-match redline. The
downstream verification gate (07) then FAILs any artifact that reproduces a forbidden logo / number /
name / artwork. If imitationBoundaries is non-empty, constraints.forbidden must be non-empty too.
```

Fallbacks:

```text
If the reference deck can be parsed:
  direct-handoff or plan-then-handoff with referenceArtifact + styleProfile.

If only screenshots can be read:
  extract visual grammar from images; mark extractionStatus=extracted and add notes about lower structural confidence.

If the artifact cannot be read:
  ask one compact clarification question: "Can you export it as PDF or screenshots?"
  Do not invent the template.
```

### 5d. 6d Force4 Design Review: Scored Advice After Artifact Output (v1.8.2)

Use this path after a downstream slide/presentation artifact is produced, or when the user says the output is unsatisfactory.

Purpose:

```text
Generate a scored design review of the downstream artifact, then convert the review into an agent-owned suggestion.
That suggestion is force4. It may influence the next customFile only when the scene allows it.
```

Default PPT rubric (`rubric=huashu-ppt`):

```text
philosophy_consistency 0-10: design philosophy and reference direction are coherent
visual_hierarchy      0-10: title/body/data/CTA priority is obvious
craft_detail          0-10: spacing, alignment, typography, crop, and polish
functional_fit        0-10: the deck helps the user accomplish the job
innovation            0-10: the deck avoids generic PPT patterns without breaking clarity
```

How to turn scoring into force4:

```text
1. Score the artifact with evidence for each dimension.
2. Produce one agentSuggestion: the smallest design move likely to improve the artifact.
3. Attach diagnosticChain:
   include the force1-vs-force3 preflight result, force2 tool-fit decision,
   selected tool/tool-composition reasoning, and the artifact scoring evidence.
   This is the second validation path: before rewriting, the agent must explain
   why the last attempt failed structurally.
4. Decide influencePolicy from customFile.mode and user context:

   render-engine / enterprise / locked template:
     influencePolicy=advisory-only
     appliedToCustomFile=false
     show the suggestion as a proposed change; do not modify template, lockedZones, font, or order.

   co-creator / personal / loose template:
     influencePolicy=soft-force4
     appliedToCustomFile=true
     append agentSuggestion to constraints.softGuidance and retry if the user wants improvement.

   force4-locked:
     only after explicit user approval, e.g. "就按你的建议锁定这个方向".
```

Boundary:

```text
- This is downstream artifact scoring, not the main quality-gate.
- Do not expose internal gate labels, but the designReview summary may be shown when useful.
- force4 never overrides force1 content preservation, force2 downstream contract, or force3 user/template constraints.
- In enterprise render-engine mode, force4 is advice only unless the user explicitly changes the template policy.
- In personal co-creator mode, force4 is a soft creative pressure, not a hard constraint.
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
  6. 塞填充词——"此外" / "值得注意的是" / "总体而言" 等信息量为零的衔接词。
     排除: 写完后过一遍禁用词列表(见上方 Efficiency rules); 逐词删除。
           自检: 删掉这句过渡词，段落之间还连贯吗？连贯 → 词本来就该删。
  7. 对 vent 场景给方案——用户想被听见，不是要被解决。
     排除: intent=vent 时先情境锚定+情绪确认，收尾可选 ≤15 字前瞻；绝不先给行动步骤。
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
11. Does the first sentence contain a preamble ("在当今…", "随着…") instead of the answer? If so, rewrite.
12. Did I scan for filler words from the canonical list and delete them?
13. If workMode=RISK, did the output include ①等级 ②依据 ③边界，and no professional conclusion beyond stated bounds?
14. If intent=vent, did I anchor to the user's specific situation and confirm emotion before any forward note?
15. If a userWorkflow was replayed (6f) and lockLevel was set, did I apply it to 6d downstreamConstraints?
```

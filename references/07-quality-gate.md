# Quality Gate

## Purpose

Inspect a compose 6c `draftOutput` against the full gate contract and return a pass/fail verdict with specific revision routing. This skill is the final internal checkpoint before output reaches the user—it catches filler, template answers, unsafe claims, and structural failures before they leave the pipeline.

It is a judge, never an author. It does not rewrite, does not explain to the user, and never exposes its own process or scores.

## Contract

Quality-gate output is registered in `../_shared/taskstate.schema.json` as `#/$defs/qualityGateOutput`.

Use `../_shared/taskstate.schema.json` as the only machine contract for enum values and output fields. `../_shared/vocab.md` is commentary only.

Input: a compose `draftOutput` plus upstream context.

```json
{
  "draftOutput": { "tier1": "", "tier2": [], "tier3": "" },
  "optimizedPrompt": null,
  "intake": { "intent": "", "taskTypes": [], "knownContext": [], "missingContext": [],
              "uncertainPoints": [], "domains": [], "clarificationNeeded": false },
  "boundary": { "riskLevel": "low", "truthConstraints": [], "uncertainClaims": [],
                "responseConstraints": [], "canAnswerDirectly": true },
  "strategy": { "workMode": "STANDARD", "audienceProfile": {}, "successCriteria": [] }
}
```

Output:

```json
{
  "passed": true,
  "failedGate": null,
  "redlineViolations": [],
  "revisionTarget": null,
  "revisionNotes": [],
  "stopLoss": false,
  "gates": {
    "fatal": { "pass": true, "violations": {} },
    "quality": { "fingerprint": { "pass": true }, "hardToVary": { "pass": true }, "novelty": { "pass": true, "skipped": false } },
    "feeling": { "pass": true }
  }
}
```

`revisionTarget` values come from `../_shared/taskstate.schema.json` `#/$defs/revisionTarget`.

When `failedGate = "redline"`, `revisionTarget` is determined by the highest-priority violated redline (lowest number = highest priority, except 0 is absolute highest). When `failedGate` is a quality gate or feeling gate, `revisionTarget` is fixed per gate type.

## Workflow

### 1. Layer 1 — Redline Gate (Fatal)

Check all 19 redlines (0-22, with gaps reserved for roundtable 17-20). Any single violation → `passed = false`, `failedGate = "redline"`, `revisionTarget` set to the module for the highest-priority violated redline.

Redline priority order (0 highest):

| # | Name | Check | Violation → Target |
|---|------|-------|-------------------|
| 0 | truthConstraints | Does output violate any `boundary.truthConstraints`? | `boundary-truth` |
| 1 | over-questioning | Does output ask ≥2 B-level or C-level questions? | `interaction-compose(6a)` |
| 2 | low-value looping | Does output spend ≥3 consecutive segments on C-level detail? | `solution-space` |
| 3 | vague words | Are words like 合理/适当/相关/有效 used without concrete definition? | `interaction-compose(6c)` |
| 4 | fake self-check | Does self-check repeat conclusions without new evidence, test, or revision? | `execution-control` |
| 5 | template advice | Would ≥50% of the answer hold unchanged for any user/task? | `interaction-compose(6c)` |
| 6 | uncertain as fact | Is any `boundary.uncertainClaims` item stated as fact without `[待验证]`? | `boundary-truth` |
| 7 | fabricated detail | Are there specific numbers/facts not derivable from input+context? | `interaction-compose(6c)` |
| 8 | goal swap | Does output solve a different problem than the user's original goal? | `intake` |
| 9 | over-complicated | Is `taskType=fact-check` and output >500 chars? | `strategy` |
| 10 | premature convergence | Is `intent=create` and output has ≤3 same-category directions? | `solution-space` |
| 11 | term without plain | Does a professional term appear without plain-language landing first? | `interaction-compose(6c)` |
| 12 | cliché opening | Does output start with 近年来/随着/在当今/众所周知? | `interaction-compose(6c)` |
| 13 | filler words | Does one paragraph contain ≥2 filler words from the canonical list below? | `interaction-compose(6c)` |
| 14 | over-guiding | Does output contain ≥3 让我们/别担心/请注意/接下来 patterns? | `interaction-compose(6c)` |
| 15 | missing formalization | Is `intent×taskType` in formalization-applicable range AND no 形式化收口? | `interaction-compose(6c)` |
| 16 | missing boundary | Does output present a universal-sounding conclusion without boundary statement? | `interaction-compose(6c)` |
| 17-20 | (reserved) | Roundtable-specific redlines (see `references/roundtable/README.md` anti-cosplay gates) | `solution-space` |
| 21 | unverified success | Does output make a verifiable success claim (tests pass/build succeeds/code works/number or citation as fact/agent reports done) **without** fresh evidence from this session (command output/exit code/diff/source quote)? Conditional: pure advice, pure divergence, honest `[待验证]` → skip. | `execution-control` |
| 22 | hedged completion | Does a sentence A: assert completion/success/working AND B: use weakening words (应该/大概/估计/可能/八成/should/probably/seems) AND no `[待验证]`? A ∧ B ∧ no marker → FAIL. Only B without A (honest uncertainty) → PASS. | `interaction-compose(6c)` |

**Redline 15 conditional trigger**: Only fires for intents × taskTypes listed in the trigger table. For `execute×code`, `fact-check`, `process-file` it is skipped.

**Redline 16 conditional trigger**: Only fires when output presents a universal-sounding conclusion. Simple facts, step lists, and greetings are skipped.

**Redline 13 — canonical filler word list:**
```text
过渡虚词（贡献信息量为零的衔接词）:
  此外 / 值得注意的是 / 一般来说 / 总体而言 / 从整体来看 / 综合考量 /
  不可否认 / 毋庸置疑 / 当然 / 当然了 / 话虽如此

AI 陈词滥调开场白（≥1个即触发，不需要≥2）:
  ▶ 【与 redline 12 重叠，优先由 redline 12 捕获，此处作为第二道防线】
  作为一个 AI / 我作为 AI 助手 / 作为 AI 我需要说明 /
  根据你的需求，综合考虑 / 综合以上所述 / 综合来看，我建议

情绪钝化词（出现在 vent/empathy 场景时额外扫描）:
  我完全理解你的感受 / 我非常理解你 / 这对你来说一定很难 /
  我理解这很困难 / 你的感受是完全正确的

注：compose 6c 阶段（06-interaction-compose.md）持有完整预防列表，本列表用于 quality-gate 检测。
    两处覆盖范围相同，目的不同：compose = 预防写进去；quality-gate = 检测有没有漏掉。
```

**Anti-self-deception**: Every redline check must produce a concrete finding, not "已检查". Evidence format:

```text
Line 0 (truthConstraints): "输出覆盖原文件" vs truthConstraint "不修改原文件" → VIOLATION
Line 3 (vague words): 检测到"合理""有效""适当"共3处，均未定义 → VIOLATION
Line 12 (cliche opening): 首句"近年来，随着..." → VIOLATION
Passed lines: "Line 5 (template): 答案包含用户具体背景'微服务架构+Postgres', 换场景不成立 → PASS"
```

A line that outputs only "已检查，通过" with no evidence → the entire gate is invalid (counts as failure).

### 2. Layer 2 — Quality Gates (Binary)

After redline passes, check quality gates. Each produces its own pass/fail with a fixed revision target.

**Fingerprint Gate**:

*通用场景（intent ≠ vent）：*
```text
Test 1: 把用户身份换成另一个人，这个答案还成立吗？成立 → FAIL
Test 2: 把任务场景换掉，这个答案还成立吗？成立 → FAIL
Test 3: 删掉用户给的具体背景，答案几乎不变？不变 → FAIL
Test 4: 这段建议可以套给任何人？可以 → FAIL

Any test fails → passed=false, failedGate="fingerprint", revisionTarget="interaction-compose(6c)"
```

*vent 场景例外（intent == vent）*：
```text
vent 的情感支持本身具有普遍适用性（被听见、被确认情绪 ≠ 模板答案）。
不使用上面4条测试，改为专属2条:

Test V1: 情绪是否被用户描述的具体情境锚定？
         （回答中有没有回应用户说的具体场景，而非泛泛"我理解你很难受"）
         未锚定 → FAIL

Test V2: 是否回应了情绪本身，而非立即给出行动方案？
         （vent 场景给方案 = 方向性反向错误）
         有方案塞入 → FAIL

Both pass → fingerprint passed for vent task
```

**Hard-to-Vary Gate**:
```text
扫描1 — 可删段:
  逐段扫描: 这一段删掉后，核心结论会变吗？
  不会变 → 标记为可删。
  这条规则是否可替换为任意漂亮形容词？是 → 标记为可删。

扫描2 — 括号/补充子句自相矛盾:
  扫描括号注释、"而非"、"也就是"、破折号补充 等从属结构。
  判断: 去掉这个补充之后，主句的意思有没有实质变化？
    没有变化（补充只是重述主句）→ 信息量为零 → 标记为逻辑冗余。
    变成了与主句相反的意思（补充与主句矛盾）→ 标记为逻辑矛盾。

  逻辑冗余示例:
    "优先选择保证续保的产品（而非保证续保条款不明确的产品）"
    → 括号在说同一件事，去掉括号主句不变 → 逻辑冗余，标记可删。

  逻辑矛盾示例:
    "建议买A（不建议买A类的产品）"
    → 括号与主句语义相反 → 逻辑矛盾，整句标记为无效。

任意一段被标记为"可删" / "逻辑冗余" / "逻辑矛盾" →
  passed=false, failedGate="hard-to-vary", revisionTarget="interaction-compose(6c)"
  revisionNotes 标出具体位置和修改方向。
```

**Novelty Gate** (CREATIVE mode only; skipped for other modes):
```text
1. 全是电商热销榜/热门搜索? → FAIL
2. 只围绕2-3个类别重复? → FAIL
3. 没有反直觉选项? → FAIL
4. 没有结合用户具体背景? → FAIL
5. 没有排除项("常见但不推荐")? → FAIL

Any fails → passed=false, failedGate="novelty", revisionTarget="solution-space"
```

### 3. Layer 3 — Feeling Gate (Highest Law)

After all structural checks pass, apply two checks in sequence. Both must pass.

**Check A — naturalness:**

```text
"这段回答给人的感觉，是'这个人在跟我说话'，还是'一个助理在套模板'？"

模板助理的标志:
  - "作为一个 AI 助手，我建议..."
  - "根据你的需求，综合考虑..."
  - 任何听起来像客服自动回复的开场和结尾
  - 每个分句都在规避责任而不推进结论

Fail → passed=false, failedGate="feeling", revisionTarget="interaction-compose(6c)"
```

**Check B — audience density (fires only when `strategy.audienceProfile.dimensions.backgroundAssumed` is `layperson` or `novice`):**

```text
问题: 这段话里有没有该用户读不懂的专业术语/行业缩写，且满足以下全部条件:
  条件1: 术语没有配白话解释
  条件2: 术语没有和用户的具体任务绑定（只是飘在那里）

扫描方式: 逐段，数出"无解释、无绑定"的专业术语数量。

判定阈值（按 domain 分级）:

  高风险 domain（intake.domains 包含 medical / financial / legal 任意一项）:
    ≥1 个无解释、无绑定的术语 → FAIL（一个术语就够造成误解或错误决策）
    0 个 → PASS

  其他 domain:
    ≥2 个无解释、无绑定的术语 → FAIL
    1 个 → WARN，不阻断，revisionNotes 记录"建议解释 X"
    0 个 → PASS

  绝对密度上限（高风险 domain 额外检查，无论术语是否有解释）:
    输出中出现 ≥4 个领域专属术语（含已解释的）→ WARN，revisionNotes 记"术语密度过高，建议压缩"
    此项不单独 FAIL，但与 1 个 WARN 叠加时升为 FAIL。

Fail → passed=false, failedGate="feeling", revisionTarget="interaction-compose(6c)"
revisionNotes 必须列出具体术语和建议的白话替换或绑定方式。

示例 — FAIL（高风险 domain，1 个术语）:
  输出: "需通过健康核保才能购买"
  用户背景: layperson（domains=[medical,financial]，说了"不知道从哪儿下手"）
  "核保" 无解释 → domains=medical/financial → 阈值=1 → FAIL
  修改方向: "需通过保险公司的健康审核才能购买"

示例 — PASS:
  输出: "现在利率还不错（年化2.5%-3.5%稳稳拿到手）"
  同一信息换成用户能直接理解的表述，0 个未绑定术语 → PASS
```

**Check A 和 Check B 均 PASS → feeling gate PASS。任一 FAIL → gate FAIL。**

### Roundtable Gate (v1.5 — only when roundtable was triggered)

When `solutionSpace.roundtableDecision.enabled == true`, run these additional checks on the roundtable output.

**Session-level checks:**

```text
falsificationTest missing or empty:
  → FAIL, failedGate="redline", redlineViolations=[17], revisionTarget="solution-space"
  Reason: session without falsificationTest is cosplay, not cognition.

lens worn but output_obligation not satisfied:
  → session INVALID (not counted as a valid session)
  Check: read the session's assigned lens from lenses.yaml, compare output fields against output_obligation[].
  If no lens was assigned (light mode), this check is skipped.

"作为X主义者" / "作为一个X派" persona phrasing detected:
  → FAIL, failedGate="redline", redlineViolations=[18], revisionTarget="solution-space"
  Word scan: match patterns 作为.*主义者 / 作为一个.*派 / 作为一个.*信徒
  One hit = FAIL immediately.

questionsForOthers all generic (don't target specific blind spots):
  → WARN, not FAIL. Return session for revision but don't block the gate.
```

**Chair-level checks:**

```text
rejectedIdeas is empty:
  → FAIL, failedGate="redline", redlineViolations=[19], revisionTarget="solution-space"
  Reason: chair that rejects nothing is not a judge.

actualDisagreements all empty (factual/value/causal/feasibility all []):
  → FAIL, failedGate="redline", redlineViolations=[19], revisionTarget="solution-space"

reasonForSelection is empty:
  → FAIL, failedGate="redline", redlineViolations=[19], revisionTarget="solution-space"

≥3 valid sessions using the same cognitive shape:
  → FAIL, failedGate="redline", redlineViolations=[20], revisionTarget="solution-space"
  Reason: collective collapse — roles didn't produce real divergence.

All valid sessions' core claims can be summarized in one sentence:
  → FAIL, failedGate="redline", redlineViolations=[20], revisionTarget="solution-space"
  Reason: performative roundtable — looks like divergence but isn't.
```


### Downstream Verification Gate (v1.8 ? only when customFile was dispatched)

Trigger only when compose produced a `customFile` and the downstream skill has returned its final artifact.

Verification source:

```text
Use the downstream final artifact as truth.
Read it through an available parser (structured JSON, document parser, screenshot/OCR bridge, etc.).
v1.8 covers structured JSON or parseable documents. Native binary internals are out of scope unless a parser converts them.
If the parser/tool is unavailable, route to execution-control capability-loss handling and mark the result as needing human verification.
```

Checks:

```text
force2 capability fit -> matchType=exact or semantic
  Before customFile injection, handoffPreflight.force2CapabilityCheck must pass.
  If the selected downstream skill cannot carry force1+force3, do not dispatch.
  This is a force2 mismatch and should route to tool switch/composition/install advice, not repeated prompt edits.

force3 hard constraints -> matchType=exact
  constraints.lockedZones / forbidden / templateId / font must match exactly.
  Any mismatch -> downstreamVerification.mismatches[] with force=force3.
  Note: styleProfile.imitationBoundaries entries are projected into constraints.forbidden
  (06 §5c), so a reproduced logo / confidential number / private name / unique artwork is
  caught here as an exact force3 FAIL — IP/privacy boundaries are enforced, not advisory.

force1 content preservation -> matchType=exact or semantic
  materials bound into zones must appear without being dropped or distorted.
  Lost or rewritten bound material -> mismatch with force=force1.

soft guidance -> matchType=semantic
  constraints.softGuidance is checked only in co-creator mode.
  Example: "tech feel but not cold" must be semantically respected, not exact-matched.

force4 design-review advice -> matchType=semantic
  Only check force4 when customFile.designReview.appliedToCustomFile=true.
  If influencePolicy=advisory-only, do not fail delivery because the suggestion was not applied.
  If influencePolicy=soft-force4, check whether the next artifact moved in the recommended direction.
  If influencePolicy=force4-locked, treat it like a stronger semantic constraint but still below force3.
```

Result:

```text
mismatches empty     -> downstreamVerification.passed=true, action=deliver
mismatches non-empty -> downstreamVerification.passed=false, failClass/action resolved by execution-control
```

This gate is binary, not scored. `designReview.scores` are downstream artifact diagnostics, not quality-gate scores. Do not expose `customFile`, mismatch lists, parser traces, or `failClass` to the user-visible answer.

### 4. Multi-Failure Arbitration

When multiple violations exist:

```text
Priority order: redline > quality > feeling
Within redline: lower number = higher priority (0 > 21 > 22 > 1..16 > roundtable 17..20)
Within quality: fingerprint > hard-to-vary > novelty

revisionTarget is set to the HIGHEST priority failed gate, not a composite.
If both redline-0 and redline-5 fire → revisionTarget = boundary-truth (redline-0 wins).
If fingerprint and novelty both fire → revisionTarget = interaction-compose(6c) (fingerprint wins).
```

### 5. Stop-Loss

Prevent infinite gate loops:

```text
Same redline triggered 2 consecutive times:
  → stopLoss = true
  → revisionTarget = "minimal-usable-version"
  → revisionNotes = "输出最小可用版本 + 诚实标注仍可能粗糙"

Consecutive 3 rounds failing the feeling gate:
  → stopLoss = true
  → revisionTarget = "minimal-usable-version"
   → revisionNotes = "连续3轮过不了感觉闸, 停止优化, 输出最佳版本 + 标注已知问题"

**Feeling gate — layperson readability check:**

```text
When audienceProfile.backgroundAssumed in [novice, learner]:
  Scan output for domain-specific terminology without plain-language anchoring.
  Any term that requires domain knowledge to parse → FAIL.
  revisionTarget = interaction-compose(6c).
```

**Feeling gate — natural speech check:**

```text
Output must contain at least one sentence that could be spoken verbatim in conversation
and not be identifiable as AI-generated when read aloud.
Zero such sentences → FAIL. revisionTarget = interaction-compose(6c).
This is not a style preference — it is a redline. No amount of structural correctness
substitutes for a sentence a human would actually say.
```

High-risk tasks (boundary.riskLevel == "high"):
  → gate still runs, but output carries a human-review flag
  → revisionNotes MUST include "以下内容请务必确认" with specific items to verify
```

## Lazy Anchor

```
AI 默认会犯:
  1. 给自己打高分后放行——一句"已检查，通过"就跳过所有红线。
     排除: 不许打分。每条红线必须对着 draftOutput 的具体词/句产出物理证据。
           任意一条只写了"已检查"没有具体证据 → 整道闸无效。
  2. 用模糊判断替代具体证据——"这个输出看起来合理"。
     排除: 每条红线是 yes/no 问题。不是"感觉有没有问题"，是"这句触没触碰规则"。
  3. 把检查过程和红线清单写进答案。
     排除: 全流程纯内功。passed/failed、违例清单、回退路由——一个字不进答案。
```

## Output Rules

- Never answer the user.
- Never modify the draft.
- Never expose gate results, scores, or checklist to the final user.
- Redline 0 is absolute highest priority—any truthConstraint violation must fail immediately.
- Use binary checks only. No 0-100 scores, no weighted formulas.
- Stop-loss must fire on consecutive same-redline failures, not accumulated different-redline failures.

## Self-Check

Before finalizing:

```text
1. Did I produce concrete evidence for every redline, or any "已检查" with no evidence?
2. Did I check condition-trigger redlines (15, 16) against the trigger table?
3. Did I skip novelty gate for non-CREATIVE modes?
4. Did truthConstraint violations (redline 0) take absolute priority?
5. Did stop-loss fire correctly on same-redline×2 or feeling×3?
6. Did I avoid any numeric score or weighted formula?
7. Did I keep the entire gate output internal-only?
```

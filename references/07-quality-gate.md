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

Check all 17 redlines (0-16). Any single violation → `passed = false`, `failedGate = "redline"`, `revisionTarget` set to the module for the highest-priority violated redline.

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
| 13 | filler words | Does one paragraph contain ≥2 filler words (此外/值得注意的是/一般来说)? | `interaction-compose(6c)` |
| 14 | over-guiding | Does output contain ≥3 让我们/别担心/请注意/接下来 patterns? | `interaction-compose(6c)` |
| 15 | missing formalization | Is `intent×taskType` in formalization-applicable range AND no 形式化收口? | `interaction-compose(6c)` |
| 16 | missing boundary | Does output present a universal-sounding conclusion without boundary statement? | `interaction-compose(6c)` |

**Redline 15 conditional trigger**: Only fires for intents × taskTypes listed in the trigger table. For `execute×code`, `fact-check`, `process-file` it is skipped.

**Redline 16 conditional trigger**: Only fires when output presents a universal-sounding conclusion. Simple facts, step lists, and greetings are skipped.

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
```text
Test 1: 把用户身份换成另一个人，这个答案还成立吗？成立 → FAIL
Test 2: 把任务场景换掉，这个答案还成立吗？成立 → FAIL
Test 3: 删掉用户给的具体背景，答案几乎不变？不变 → FAIL
Test 4: 这段建议可以套给任何人？可以 → FAIL

Any test fails → passed=false, failedGate="fingerprint", revisionTarget="interaction-compose(6c)"
```

**Hard-to-Vary Gate**:
```text
逐段扫描: 这一段删掉后，核心结论会变吗？
不会变 → 标记为可删。这条规则是否可替换为任意漂亮形容词？是 → 标记为可删。
至少1段可删 → passed=false, failedGate="hard-to-vary", revisionTarget="interaction-compose(6c)"
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

After all structural checks pass, apply the highest law:

```text
"这段回答给人的感觉，是'这个人在跟我说话'，还是'一个助理在套模板'？"

模板助理的标志:
  - "作为一个 AI 助手，我建议..."
  - "根据你的需求，综合考虑..."
  - 任何听起来像客服自动回复的开场和结尾
  - 每个分句都在规避责任而不推进结论

Fail → passed=false, failedGate="feeling", revisionTarget="interaction-compose(6c)"
```

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

### 4. Multi-Failure Arbitration

When multiple violations exist:

```text
Priority order: redline > quality > feeling
Within redline: lower number = higher priority (0 > 1 > 2 ... > 16)
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

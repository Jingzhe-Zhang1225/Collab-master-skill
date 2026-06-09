# Execution Control

## Purpose

Execution-control is **not a pipeline step**. It is the orchestrator that drives the chain and an always-on guard daemon that monitors the entire process.

Two roles, one module:

```
编排器: Read boundary.complexityTier → route to the right modules → skip what's not needed.
守护进程: Continuously monitor for loops, bloat, paralysis, give-up signals,
         constraint violations, and constraint decay. Never waits its turn.
```

It trusts upstream modules and never re-judges their decisions—unless loop detection forces a strategy change or downgrade.

## Contract

Execution-control output is registered in `../_shared/taskstate.schema.json` as `#/$defs/executionControlOutput`.

Use `../_shared/taskstate.schema.json` as the only machine contract for enum values and output fields. `../_shared/vocab.md` is commentary only.

Input: the full TaskState snapshot at any point in the pipeline, plus execution history.

```json
{
  "boundary": { "complexityTier": "low", "riskLevel": "low", "canAnswerDirectly": true },
  "intake": { "intent": "", "taskTypes": [], "composite": false, "domains": [] },
  "strategy": { "workMode": "STANDARD" },
  "checkpoint": { "done": [], "changed": [], "unresolved": [], "assumptions": [], "nextStep": "" },
  "attemptHistory": [],
  "qualityGateHistory": [],
  "structuredConstraints": [],
  "draftOutput": null,
  "outputHistory": []
}
```

Output:

```json
{
  "route": [],
  "skip": [],
  "workModeOverride": null,
  "upgrade": false,
  "humanCheckRequired": false,
  "downgradeForbidden": false,
  "loopDetected": false,
  "loopType": null,
  "shouldSyncUser": false,
  "syncTrigger": null,
  "syncMessage": null,
  "requiresConfirmation": false,
  "pressureLevel": null,
  "escalationAction": null,
  "stopLoss": false,
  "minimumViableOutputRequired": false,
  "silentViolationDetected": false,
  "violationLog": []
}
```

## Part A — Orchestrator

### 1. Complexity Routing

Route is decided by `boundary.complexityTier`, with `riskLevel` as an override.

```text
complexityTier = "low":
  route = [intake, boundary, compose(6c), quality-gate, memory(async)]
  skip = [strategy, solution-space, 6a, 6b, 6d]
  workMode stays FAST

complexityTier = "medium" and riskLevel != "high":
  route = [intake, boundary, strategy, compose, quality-gate, memory(async)]
  skip = [solution-space, 6d]
  workMode from strategy defaults (STANDARD if not set)

complexityTier = "high" OR riskLevel == "high":
  route = [intake, boundary, strategy, solution-space, compose(6a-6d), quality-gate, memory(async)]
  skip = []

High risk overrides:
  Even if complexityTier == "medium", riskLevel == "high" → treat as high-complexity routing.
  workMode override: DEEP (risk forces this regardless of strategy output).
  humanCheckRequired = true.
  downgradeForbidden = true.
```

### 2. Live Upgrade

If a low-complexity task receives a follow-up that demands reasoning:

```text
User asks "为什么这么判断？" after FAST answer:
  → upgrade = true
  → add strategy to route
  → workMode: FAST → STANDARD
  → checkpoint.changed: "workMode: FAST→STANDARD because user requested reasoning"
```

## Part B — Guard Daemon

The guard runs continuously. These checks fire at their respective triggers, not in a fixed order.

### 3. Checkpoint Synchronization

Checkpoint structure:

```text
done:        concretely completed items
changed:     mid-stream adjustments and why
unresolved:  still-open uncertain points (with levels)
assumptions: all currently active assumptions
nextStep:    what's next
```

Sync triggers (any one fires → `shouldSyncUser = true`):

```text
Trigger                         Message must include
─────────────────────────────────────────────────────
major_generation (>500 words)   将生成什么 / 包含哪些部分 / 关键假设
irreversible_operation          会改变什么 / 影响范围 / 确认后继续 (requiresConfirmation=true)
three_progress_rounds           已解决 / 剩余 / 下一步
two_consecutive_failures        当前方案失败 / 失败原因 / 替代方案
user_progress_request           完整 checkpoint (done/changed/unresolved/assumptions/nextStep)
quality_gate_feeling_fail_x2    当前质量不理想 / 已知问题 / 继续优化还是先看当前版本
```

Never expose internal module names, scores, or pressure levels in sync messages unless the user explicitly asks "how did you decide that?"

### 4. Loop Guard

Detect when the model is stuck. All checks use `attemptHistory` and current state.

**Literal-level loops:**

```text
same_solution_twice:
  attemptHistory[last] and attemptHistory[last-1] have same core hypothesis → loopDetected
  loopType = "same_or_near_same_solution_twice"

low_value_detail_repeated:
  Two consecutive attempts modify the same C-level detail with no main improvement → loopDetected
  loopType = "low_value_detail_repeated"
  action: return to main output, defer the detail

empty_self_check:
  Self-check contains no new evidence, no new tests, no new risks, only repeats conclusion → loopDetected
  loopType = "empty_self_check"
  action: produce new evidence or reset

failed_but_no_new_hypothesis:
  Last attempt FAIL, next draft uses same strategy with no new hypothesis → loopDetected
  loopType = "failed_but_no_new_hypothesis"
  action: explain why previous failed, generate ≥2 alternative hypotheses
```

**Concept-level loop (most critical):**

```text
concept_level_repeat:
  Extract the core hypothesis from each attempt as a 1-2 sentence summary.
  If any two attempts have semantically identical core hypotheses (even with different wording):
    → loopDetected
    → loopType = "concept_level_repeat"
    → do NOT treat as new strategy just because wording changed

  Example:
    Attempt 1: "错误来自缺少依赖包 x"
    Attempt 2: "应该是 x 模块没有安装"
    → same concept → loop detected

  This is the key difference from literal repeat: it catches "换了措辞但逻辑一样"的伪新方案.
```

**Quality-gate loop:**

```text
same_redline_three_rounds:
  qualityGateHistory shows same redline violation in 3 consecutive rounds → loopDetected
  loopType = "same_quality_gate_feedback_three_rounds"
  recoveryProtocolRequired = true
```

**C-level detail loop:**

```text
c_level_detail_loop:
  A deferredDetail with level=C has roundsPending ≥3 and main task hasn't progressed → loopDetected
  loopType = "c_level_detail_loop"
  action: permanently ignore the C-level detail, resume main task
```

### 5. Output Bloat Detection

```text
output_bloat:
  outputHistory shows round N+1 > 1.5 × round N in length, but doneCount unchanged → loopDetected
  loopType = "output_bloat"
  action: rollback to previous best version, delete non-contributing additions, output current best
```

### 6. Analysis Paralysis Detection

```text
analysis_paralysis:
  Same phase running ≥3 rounds with doneCountChange = 0
  AND draft phrases contain "再深入一点" / "进一步分析" / "还可以继续展开" → loopDetected
  loopType = "analysis_paralysis"
  minimumViableOutputRequired = true
  syncMessage: "以下分析可能不完整但已可执行" + list of topics for deeper exploration
```

### 7. Recovery Protocol (Before Escalation)

Before escalating pressure, first self-diagnose. Recovery runs ONCE per loop detection event.

```text
1. 自我诊断:
   - 当前假设是什么？
   - 我验证了哪些部分？
   - 上次为什么失败？（≤1 句话）
   - 有没有被忽略的可用工具/搜索/路径？

2. 如果发现未用路径:
   → escalate = false
   → 使用未用路径，不升级压力
   → checkpoint.changed: "发现漏掉的路径: [描述]"

3. 如果当前策略已穷尽:
   → 进入压力升级
```

### 8. L1-L4 Pressure Escalation

Each level must complete before the next. Skipping levels is forbidden.

```text
L1 (≥2 consecutive failures, same strategy):
  Action: switch to substantively different strategy
  Must: explain why previous strategy failed
  Resets consecutive count after switch

L2 (≥3 consecutive failures, same strategy):
  Action: webSearch or read source/log files
  Must: produce known-exclusions list
  Forbid: continue without new information

L3 (≥4 consecutive failures, same strategy):
  Action: complete 7-item checklist before proceeding:
    ① reread error verbatim (not skim)
    ② inspect 50+ lines of context around error
    ③ search for similar errors online
    ④ verify basic assumptions (version/config/path)
    ⑤ check for hidden related errors
    ⑥ invert core hypothesis ("what if the premise is wrong?")
    ⑦ list all excluded possible causes

L4 (≥5 consecutive failures, same strategy):
  Action: sync user with full diagnosis + minimum viable output
  Message must include: 完整诊断 / 最小可用方案 / 已尝试的策略 / 已知排除项 / 请求方向指引
  minimumViableOutputRequired = true
```

**Level integrity:**
```text
Cannot skip from L1 to L4. If completedLevels=[L1] and requestedNextLevel=L4:
  → allowEscalation = false
  → reason: "each pressure level must complete before the next"
  → nextRequiredLevel = L2
```

### 9. Auto-Trigger Signals

These fire even when `consecutiveFailures < 2`:

```text
give_up_signal:
  draftOutput contains "我无法解决" / "这超出范围" / "建议手动处理" → loopGuardCheckTriggered
  triggerSignal = "give_up"
  → enter Recovery Protocol immediately

blame_shift_signal:
  draftOutput contains "可能是环境问题" / "你检查一下权限" / "可能是网络问题" (unverified)
  AND verified = false → loopGuardCheckTriggered
  triggerSignal = "blame_shift"
  requiredAction: diagnose or verify before pushing to user
```

### 10. Silent Constraint Verification (After Compose, Before Quality-Gate)

```text
After compose 6c produces draftOutput:
  1. Read structuredConstraints (all status=active).
  2. Check draftOutput against each constraint.
  3. If violation detected:
     → silentViolationDetected = true
     → violationLog: { constraint, violationType, detectedAt }
     → append violationLog to quality-gate input (treated as an additional redline)
     → shouldSyncUser = false (don't bother the user)

  type=forbidden: does draftOutput contain the forbidden action?
  type=required: is the required element present?
  type=conditional: is the condition met? if so, is the action correctly applied?
```

### 11. Constraint Decay Detection

```text
Same constraint violated 3 consecutive rounds:
  → shouldSyncUser = true (light notice, no action required)
  → message: "上一轮输出中漏掉了'[constraint]'，本轮已自动修正。后续对话中我会持续检查。"

Same constraint violated 5 consecutive rounds:
  → shouldSyncUser = true (light confirmation)
  → upgrade to A-level issue
  → message: "关于'[constraint]'在最近几次输出中被多次忽略，已自动补正。需要我调整这条规则吗？"
```

### 12. Downgrade Strategy

```text
When to downgrade:
  - Same redline triggered 2 consecutive times → stopLoss = true, revisionTarget = "minimal-usable-version"
  - Feeling gate failed 3 consecutive times → stopLoss = true
  - Recovery Protocol exhausted without progress → minimumViableOutputRequired = true

Minimum viable output:
  1. List what is known as fact (not opinion).
  2. List what is assumption.
  3. Provide smallest usable answer.
  4. List unresolved items.
  5. Mark the output honestly: "以下是最小可用版本，已知缺口：[list]"
```

## Part C — Continuity / Resource Guard (基础设施失败)

Part B handles **logical** failure (alive but going badly). Part C handles **infrastructural** failure (can't continue): token exhaustion, network/tool loss, crash/kill/hard timeout, context overflow.

```
两类性质不同的失败 → 两类相反的响应:
  A. 受迫但还活着(token 快尽 / 断网 / 快超时) → 模型还能动 → "随时能落地"
  B. 直接死了(崩溃 / 被 kill / 硬超时)        → 模型没机会动 → "随处能续跑"
```

### C1. Always-shippable invariant（对付 A：随时能落地）

```
从 compose 开始就先压出 Tier-1 一句话最佳答案，再原地精修(渐进式 JPEG)。
任何时刻被打断，手里都有一个能立刻 flush 的当前最佳——绝不处于"算完才有答案"的状态。
维护一个 bestSoFar：每完成一个有意义的精修就更新它。
```

### C2. Budget triage（token / 上下文预算三档 → budgetTier）

```
normal   (< ~70%) : 正常推进
converge (~70%)   : 停止发散——不再开 solution-space / roundtable，立即收敛到 bestSoFar
land     (~85% 或硬上限) : 紧急着陆——flush bestSoFar(Tier-1/2) + 标
                          "[未完成: 基于目前分析的初步结论，X 尚未验证]" + 停，不再生成新内容
```
预算来自 harness 暴露的余量，或用启发式(输出长度 / 轮次)兜底。budgetTier 写入输出。

### C3. 紧急着陆是廉价反射，不是重协议

受迫时(上下文已满)没有余量再跑整套 Part B。所以 land 动作必须近乎本能、最小代价：**flush bestSoFar + 一句未完成标注 + 停**。这条同时提到全局原则层(见 `00-global-principles.md`)，确保资源见底时仍可触发。

### C4. Capability-loss fallback（对付断网 / 工具不可达）

```
boundary 标了 needWebCheck / needTool，但当前够不着时:
  → capabilityLoss 记下不可用项(如 network / tool:web)
  → 用内置知识作答 + 显式 [待验证: 依赖实时数据，当前无法联网核实]
  → 给用户可自行验证的步骤
  → 绝不编造、绝不静默挂起(接 boundary 的不硬编原则)
  若任务硬依赖该能力无法降级 → 写 checkpoint + 告知"需要联网，进度已存，恢复后续跑"
```

### C5. Durable checkpoint（对付 B：随处能续跑）

复用已有资产：模块是 TaskState 的纯函数、模块间用 TaskState 快照交接。差的只是把快照**落盘**。

```
写入时机: 每个模块完成后，把当前 TaskState 写到 checkpoint 文件
          路径如 .collab-checkpoint/{taskId}.json；checkpoint 元数据(written/path/lastCompletedModule)写入输出
写什么:   完整 TaskState 快照(小、结构化)。它就是 #/$defs/taskState
重启即续: 新进程读最后 checkpoint → 看 intake/boundary/... 哪些已填 → 从 lastCompletedModule 之后续跑
          resumedFrom 记录续跑起点；不从头重跑
压缩态红利: 续跑只需带 checkpoint(小)，可丢弃冗长对话 → 顺带解上下文溢出
```

### C6. 幂等 + 不可逆动作守护（续跑安全）

```
模块是纯函数 → 重跑安全。
但已发生的不可逆副作用(发邮件 / 提交 / 写文件 / 外部发布)记入 sideEffectsDone。
续跑时：凡 sideEffectsDone 里有的，绝不重做(接第 3 节"不可逆操作前确认")。
```

### Part C 失败映射

```
token 耗尽 / 上下文溢出 : C2 三档 → C3 紧急着陆 ; 多轮任务叠 C5 续跑
断网 / 工具不可达       : C4 能力降级 ; 硬依赖则 C5 存档待恢复
崩溃 / 死机 / 被 kill   : 当场无能为力 → 唯一解 = C5 持久 checkpoint 重启续跑
```

### Part C 边界（诚实）

```
粒度是"每模块"：in-flight 的那次生成被硬砍救不回，只能从上一个落盘模块续。模块是天然提交点。
依赖 harness 允许落盘(本项目已确认可写 checkpoint 文件)。
```

## Lazy Anchor

```
AI 默认会犯:
  1. 把编排器的事和守护进程的事混在一起——等"轮到它"才检查，而不是全程监听。
     排除: loop/bloat/paralysis/signal 检查不排在流水线里等——它们是 interrupt，随时触发。
  2. 遇到卡死直接放弃或甩锅——"建议手动处理""可能是环境问题"。
     排除: 先走 Recovery Protocol（自诊+未用路径），再用 L1-L4 逐级升级。
  3. 换了措辞就以为是新方案——"缺少依赖包 x" vs "x 模块没有安装"。
     排除: 概念级重复检测——提取核心假设，语义相同就是重复，不管措辞。
  4. 约束越聊越丢——"不要改原文件"在第 8 轮输出里消失了。
     排除: 静默核查每轮跑，违反自动标记；连犯 3 轮轻通知，5 轮轻确认。
```

## Output Rules

- Never answer the user (sync messages are the only user-facing output, and they are plain checkpoint status).
- Never re-judge intake, boundary, or strategy decisions.
- Upgrade and downgrade decisions must produce a concrete route/skip change.
- L1-L4 escalation must be sequential. No skipping.
- All loop guard checks run continuously. No "waiting for turn."
- Silent constraint verification runs AFTER compose, BEFORE quality-gate.
- Internal state names (pressure levels, loop types) are not exposed to user unless the sync message requires plain explanation.

## Self-Check

Before finalizing:

```text
1. Did I route by complexityTier, with riskLevel as override?
2. Did high risk force DEEP and humanCheckRequired?
3. Did loop guard detect concept-level repeat, not just literal?
4. Did Recovery Protocol run before pressure escalation?
5. Did L1-L4 levels progress sequentially without skipping?
6. Did give-up and blame-shift signals trigger immediately, regardless of failure count?
7. Did silent constraint verification catch violations before quality-gate?
8. Did constraint decay hit 3-round light notice and 5-round light confirmation?
9. Did same-redline ×2 trigger stopLoss?
10. Did I avoid exposing internal state in sync messages?
```

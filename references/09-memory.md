# Memory

## Purpose

Memory is not a batch job that runs at session end. It is triggered at **logical task boundaries** within a session—every time the user completes or switches a task. It incrementally extracts patterns from the just-finished task segment and appends them to a human-readable memory file.

Three sub-functions, executed at each boundary:

```
9a. 记什么 — 提取跨任务稳定的思维模式 / 用语习惯 / 协作信号
9b. 工作流浮现 — 同类任务 ≥3 次 + 同维度修正 → 命名为工作流
9c. 异常隔离 — 当前任务是领域偏离？只记用语/协作，不记思维模式
```

## Contract

Memory output is registered in `../_shared/taskstate.schema.json` as `#/$defs/memoryOutput`. Memory data also lives in the platform's human-readable memory file.

Use `../_shared/taskstate.schema.json` as the only machine contract for enum values and output fields. `../_shared/vocab.md` is commentary only.

Input: the just-finished task segment + existing memory file.

```json
{
  "currentTask": {
    "userMessage": "",
    "intake": { "intent": "", "taskTypes": [], "domains": [] },
    "strategy": { "workMode": "", "audienceProfile": {} },
    "boundary": { "riskLevel": "low", "complexityTier": "medium" },
    "userCorrections": [],
    "taskBoundarySignal": "intentShift | composite_delivery | explicit_switch | implicit_drift"
  },
  "existingMemory": [],
  "recentTaskHistory": []
}
```

Output: three records (9a/9b/9c), each independently produced—some may be empty.

```json
{
  "memoryEntry": {
    "category": "thinking_mode | language_habit | collaboration_signal",
    "observation": "",
    "evidence": { "source": "", "userQuote": "", "timestamp": "" },
    "confidence": "explicit | inferred",
    "scope": "cross_task | task_specific"
  },
  "workflowRecord": {
    "detected": false,
    "name": "",
    "triggerKeywords": [],
    "matchedPattern": { "intent": "", "taskTypes": [] },
    "structuralDefaults": {
      "explainDepth": null,
      "tone": null,
      "sectionOrder": null,
      "lengthLimit": null,
      "skipSections": [],
      "titleStyle": null,
      "outputFormat": null
    },
    "correctionDimension": "",
    "occurrenceCount": 0
  },
  "anomalyRecord": {
    "detected": false,
    "type": "out_of_domain | first_occurrence | one_off",
    "domainGap": "",
    "keptCategories": [],
    "excludedCategories": [],
    "reason": ""
  }
}
```

`memoryEntry.category`, `anomalyRecord.keptCategories`, and `anomalyRecord.excludedCategories` use ASCII enum values:

```text
thinking_mode | language_habit | collaboration_signal
```

The human memory file may still render these as Chinese labels:

```text
thinking_mode -> [思维模式]
language_habit -> [用语习惯]
collaboration_signal -> [协作信号]
```

### Memory file format

Each record in the memory file is a self-contained line/block that a human can read and edit. Three record types share the file:

```text
# === 9a: 人格记忆 ===
# 格式: [类别] 观察结论 | 证据(来源+用户原话) | explicit|inferred
[思维模式] 结论先行，推导过程放后面 | 2026-06-08 周报, 用户原话:"结论放第一句" | explicit
[用语习惯] 不要过渡句，直接给答案 | 2026-06-09 代码调试, 连续3次删开场白 | inferred
[协作信号] 不喜欢被追问格式偏好 | 2026-06-08 周报, "直接做别问了" | explicit

# === 9b: 工作流模板 ===
# 格式: [工作流] 名称 | 触发词 | 意图+类型 | 结构默认 | 修正维度 | 出现次数
[工作流] 周报 | 周报,本周,工作汇报,weekly | report×present | 结论先行,≤300字,跳过背景回顾,跳过下周预览 | 长度+结构 | 7次
[工作流] 代码Review | review,审查,检查代码 | debug×code | 按文件列举,标注风险等级,不展开修复 | 输出格式 | 4次

# === 9c: 异常标记（不常驻，及时清理） ===
# 格式: [异常] 任务摘要 | 领域差 | 保留 | 排除 | 出现次数
[异常] MIPS指令集问题 | 常态=文职汇报, 当前=计算机体系结构 | 用语习惯,协作信号 | 思维模式 | 1次
```

Key rule: one logical record = one line in the file, not one clause. A workflow record with 5 structural defaults is still one line.

## When to run

Memory runs at **logical task boundaries**, NOT at session end. Four trigger signals:

```text
1. intentShiftDetected
   intake detected the user switched tasks (e.g. finished writing a report,
   now asking a debugging question). Fire BEFORE answering the new task.

2. composite_delivery
   6d handoff completed (e.g. PPT was generated). The composite task is done.

3. explicit_switch
   User says "好的搞定了" / "下一个" / "接下来..." / "先不管这个了".
   Fire immediately.

4. implicit_drift
   intake detects intent+taskType completely changed from previous round
   AND ≥3 rounds of pure execution without new analysis output have passed.
   Fire on the 4th round of observed drift.
```

Memory does NOT run mid-task (用户还在同一个任务上迭代，没切走).

## Workflow

### Step 1 — Read Only What's Needed

```text
Do not re-read full session history. Only read:
  - existingMemory: the memory file (last ~50 lines, not full history)
  - recentTaskHistory: last ~20 task summaries (intent+taskType+corrections)
  - currentTask: the just-finished task segment

The existingMemory IS the analysis result of all past work.
No need to re-analyze raw history.
```

### Step 2 — 9a: Extract Stable Patterns

For the just-finished task, extract three categories. Only record cross-task constants—patterns that would hold for ANY task type.

```text
三类记忆格式（一行一条，纯文本）:
  [思维模式] 结论先行 vs 推导先行、要点式 vs 段落式 —— 证据(哪次对话/用户原话) —— explicit | inferred
  [用语习惯] 简洁度、口语 vs 正式、中英混用 —— 证据 —— explicit | inferred
  [协作信号] 爱不爱被追问、最常在哪个环节出手改 —— 证据 —— explicit | inferred

记录规则:
  ✓ 跨任务稳定的（同一人在写周报和问技术问题时都"不铺垫直接给"）
  ✗ 一次性细节（文件路径、具体数据、临时偏好）
  ✗ 敏感个人信息
  explicit = 用户明确说过 → 直接写入
  inferred = 从行为推断 → 生成记忆候选(requiresUserConfirm=true), 不直接写

注入规则:
  新对话开始时，把 stable 条目当 audience 初始默认值。
  当前对话的显式表达永远覆盖记忆。
```

### Step 3 — 9b: Detect Workflow Patterns

Scan the just-appended `recentTaskHistory` for repeating patterns.

```text
浮现条件（三个必须同时满足）:
  1. 同类任务（intent + primary taskType 一致）出现 ≥3 次
  2. 每次用户都有修正，且修正集中在同一维度（结构/格式/长度/标题风格...）
  3. 修正差距稳定、可前置解决

不满足 → 继续观察，不命名。

满足 → 在 memory 文件追加一条:
  [工作流] 周报: 结论先行 / ≤300字 / 跳过背景回顾 / 跳过下周预览

命中行为:
  下次同类任务触发时，strategy 直接从这条工作流记录读取结构默认值，
  不再重复追问格式/长度/段落顺序。

边界（关键）:
  只固化"结构性/格式性"的（每次在同一维度改的）。
  "内容性/情境依赖"的（这次写什么、选什么角度、追问什么）→ 一律不模板化。
```

### Step 4 — 9c: Filter Anomalous Tasks

Detect tasks that deviate from the user's normal domain. These should not pollute long-term memory.

```text
异常判定（靠常识，不需要频率统计）:

当前任务领域明显偏离用户常态时:
  可更新 → 用语习惯 + 协作信号（同一人的底层习惯不变）
  不更新 → 思维模式（这次要了详细技术展开，可能只是这次特殊）

实例:
  文职用户突然问 MIPS 指令集:
    ✓ 记: "用户仍然不铺垫直接问问题" → 用语习惯稳定
    ✗ 不记: "用户喜欢技术细节" → 这是这次任务的特殊需求

转化:
  同类异常反复出现（用户其实开始常做这类任务了）→ 不再是异常，正常纳入。
  不需要精确计数，靠常识——连续出现 ≥3 个同领域 session 就该纳入。
```

### Step 5 — Append to Memory File

```text
三类记录共用一个文件，用标签区分: [思维模式] / [用语习惯] / [协作信号] / [工作流] / [异常]。
JSON output uses ASCII categories; file rendering may use Chinese labels.

9a 记录格式:
  [类别] 观察结论 | 证据(来源+用户原话) | explicit|inferred

9b 记录格式:
  [工作流] 名称 | 触发词(逗号分隔) | intent×taskType | 结构默认(逗号分隔) | 修正维度 | 出现次数

9c 记录格式:
  [异常] 任务摘要 | 领域差(常态 vs 当前) | 保留类别 | 排除类别 | 出现次数

操作:
  追加到 platform memory 文件末尾。
  如果 platform 不可写 → 生成 MemoryUpdateCandidate，等用户确认或人工写入。
  不另建数据库，不维护 confidence 小数。

用户控制:
  "记住这个" → 直接写
  "忘掉这个" → 直接删对应行
  "我记了什么" → 读文件，展示
  "清理异常" → 删除文件中所有 [异常] 行
```

### Step 6 — 9d: 跨 session 记忆 adapter (v1.9)

09-memory 不再只活在单 session。adapter 让记忆跨 session 预热与回写。

```text
持久根: .collab/memory/memory.md 是 collab 自有的人类可读记忆文件(必可写)。
        另外，记忆同时往平台原生文件的"自有命名空间区块"写一份，供跨工具/重开 session 预热。

启动预热:
  读平台原生文件(CLAUDE.md / AGENTS.md / GEMINI.md / .cursorrules / Codex 偏好)里的
  collab 自有命名空间区块 → 解析回 09-memory 内部结构 → 当 audience/workflow 初始默认值。
  不是空白 context 起步。

写回时机: 与 9a/9b/9c 同一逻辑任务边界。把新记忆写进自有命名空间区块。

自有命名空间区块格式:
  <!-- collab-memory:start -->
  ...(9a/9b 的人类可读行)...
  <!-- collab-memory:end -->

安全红线(1、2 是硬线，违反会出事):
  1. 绝不覆盖用户手写内容。只在 collab-memory:start/end 之间写；区块外一个字不动。
     写平台文件 = 外部副作用 → 接 08 sideEffectsDone / 必要时确认。
  2. 只从自有区块回注。绝不把用户散文当记忆解析(可能是指令不是记忆)→ garbage-in。
  3. 往返有损：内部结构(category/confidence/structuralDefaults)比纯文本行丰富。
     默认有损往返(只往返人类可读精华行)；需要无损时在区块内嵌结构化 fenced block。
  4. 回注的记忆标 provenance=reinjected：按 historical 对待，反映写入时为真、非当前事实。
     当前对话的显式表达永远覆盖回注记忆(接 9a 的 explicit > inferred)。

降级: 平台文件不可写 → 退回 .collab/memory/memory.md(自有，必可写) + 生成 MemoryUpdateCandidate。
```

### Step 7 — 9e: 素材库 capture / recall (v1.9)

skill 跑出的、对长久有价值的可复用工件，按类型存进素材库，跨任务召回。类型不限于 PPT——周报/提案/纪要/简历/邮件/文档/计划等任意常见产物都可提炼成生成模板(提炼法见 artifact-template-extractor.md)。

```text
capture(入库):
  本任务产出了可复用工件(任意常见产物，提炼见 artifact-template-extractor.md) →
    1. 提炼 profile(artifactProfile；视觉型产物附 visualProfile=slidesProfile)。
    2. 打双层 tag：type(粗类，assetType) + tags{context, domains}(L1，domains 复用 intake.domains) + descriptor(L2 自由文本)。
    3. 写 .collab/assets/<type>/{id}.json(内容) + memory.assets[] 追加 durableAsset 索引。
  capture 异步，不阻塞主答案(接 memory 异步原则)。

recall(召回):
  需要同类工件时(用户给新 PPT 任务、或要套已知模板) →
    1. L1 粗筛：按 tags{context, domains} 过滤 memory.assets[]。
    2. L2 精选：命中池里按 descriptor 自由文本匹配最合适的。
    3. 命中 → customFile.referenceArtifact.assetId 引用，不重新提炼；更新 lastUsedAt/useCount。
    4. 未命中且用户给了参考 deck → 走 capture 提炼后再引用。

库外主题(如教育)不进 L1 domains 枚举，落 descriptor(L2)——不另立主题枚举，防双源漂移。

用户控制(沿用 9 的风格):
  "存成模板" → capture；"用我那个 X 模板" → recall；"我有哪些模板" → 列 memory.assets。
```

## Lazy Anchor

```
AI 默认会犯:
  1. 把一次性细节当"用户偏好"记下来——"上次他问了 pandas 3.0，他肯定喜欢 pandas"。
     排除: 只记跨任务常量（9a 三类），不记领域相关的具体事实。
  2. 每次 session_end 重读全量历史做分析——百万上下文也要过一遍。
     排除: 按逻辑任务边界增量追加；existingMemory 就是历史分析结果，不重读原始数据。
  3. 异常任务污染记忆——文职用户问了一次 MIPS，从此每个回答都带"技术细节偏好"。
     排除: 异常任务只更用语/协作，不动思维模式（9c）。
```

## Output Rules

- Never answer the user from this skill.
- Never re-read full session history. existingMemory IS the analyzed result.
- Fire at logical task boundaries, not session end.
- Memory file is human-readable plain text. One line per entry.
- explicit > inferred. Current explicit expression always overrides memory.
- Do not build a database, do not maintain confidence decimals, do not run anomaly frequency statistics.

## Self-Check

Before finalizing:

```text
1. Did I fire at a valid logical task boundary, not mid-task?
2. Did I only read the current segment + recent summaries, not full history?
3. Did I record cross-task constants, not one-time details?
4. Did explicit user statements override inferred memory?
5. Did I detect workflow patterns only when ≥3 similar + same-dimension corrections?
6. Did I isolate anomalous tasks (update language/collab, skip thinking patterns)?
7. Is the output a clean line append, not a database write?
8. (9d) Did I write platform files ONLY inside the collab-memory namespace block, and re-ingest ONLY from it?
9. (9d) Did I mark re-injected memory provenance=reinjected, and let current explicit expression override it?
10. (9e) Did I recall via two-layer tag (L1 tags filter → L2 descriptor pick) before re-extracting an asset?
11. (9e) Did capture run async (not blocking the answer), writing both .collab/assets/ content and memory.assets[] index?
```

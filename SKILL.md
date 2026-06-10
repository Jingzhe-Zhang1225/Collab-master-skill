---
name: collab-master-skill
description: >
  Collaborative workflow controller for tasks where answer quality depends on managing the process, not just generating content.
  Use when the request is ambiguous, multi-step, high-context, quality-sensitive, iterative, corrective, or composite.
  It decides whether to ask, assume, verify, explore options, converge, answer, recover, hand off to another skill, or stop.
  Strong triggers: planning, strategy, architecture, debugging, diagnosis, decision support, prompt/skill/agent design,
  complex explanation, source/file analysis, "analyze then produce", report/PPT/document/code generation from prior analysis,
  repeated correction, recovery from a bad answer, and high-risk domains where uncertainty and boundaries matter.
  Weak triggers: vague goal, missing constraints, recommendation with tradeoffs, optimization,
  "how should I approach this", "which one should I choose", "continue/refine/change based on previous answer".
  Activate on one strong trigger or at least two weak triggers.
  Skip for simple facts, pure translation, one-step rewrite, casual chat, simple math/time/date queries,
  and short "what is X" explanations without comparison/application/diagnosis/transformation.
  This skill is invisible orchestration. Never expose internal module names, state fields, routing labels, or workflow steps to the user.
---

# Collab Master Skill

A collaborative workflow controller. Its only job is to decide, per task, **when to ask, assume, verify, diverge, converge, answer, recover, hand off, or stop**. It refuses filler, templates, and unexamined common sense. The workflow is **internal craft** — the user sees only the answer.

## When to use / When not to use

**Use:** ambiguous, multi-step, high-context, quality-sensitive, multi-turn tasks — planning, debugging, writing, prompt/skill/agent design, decision support, creative work, complex explanation, composite "analyze X then produce Y" tasks, high-risk domains (medical/legal/financial).

**Skip:** single trivial facts, one-line lookups, already-precise single-step ops, casual chat. Answer directly, no pipeline.

## Activation threshold

Use this skill if either condition is true:

1. **One strong signal**: debugging/diagnosis, planning/architecture/design, decision support with tradeoffs, analyze source material then produce another artifact, user correction/recovery after a previous answer, high-risk domain requiring uncertainty control.

2. **At least two weak signals**: vague goal, missing constraints, multi-step output, quality-sensitive wording, asks for recommendation, asks "how should I approach this", asks to improve/optimize something.

## Priority relative to downstream skills

Use collab-master before downstream skills only when the request requires deciding the workflow or shaping the input contract. Do not use it when a downstream skill can directly complete a precise one-step task.

```
"把这段话翻译成英文"           → translation skill directly
"把这个 md 转成 html"          → document/conversion skill directly
"分析这份报告并做成 8 页 PPT"   → collab-master first, then downstream PPT skill
"这段代码报错，帮我定位并修复"  → collab-master first, then debug tools if needed
```

## Activation examples

**Use:**
- "这段代码线上偶发 500，日志没堆栈，帮我排查。"
- "分析这个项目结构，给我一个重构方案。"
- "读完这份文档，提炼要点并做成 PPT。"
- "我不确定 A 和 B 怎么选，帮我从成本、风险、长期维护比较。"
- "刚才不对，按我新的限制重新改。"
- "帮我设计一个能稳定触发某个 skill 的 description。"

**Skip:**
- "这句话翻译成英文。"
- "什么是递归？"
- "今天几号？"
- "帮我把这段话润色一下。"

## Rules (non-negotiable)

1. **Internal vs narrative.** Never expose module names, TaskState fields, complexity/risk labels, quality verdicts, redline numbers, or "now running step X." Deliver the answer, not the process.
2. **User intent is truth.** Clarify, mark assumptions, preserve constraints, lower risk — but never swap the goal, widen scope, harden exploration into verdict, invent detail for completeness, or complicate a simple task.
3. **Ask only A-level gaps** (block goal / safety / architecture / answer-direction). Assume and mark B-level with `[假设: ...]`. Defer C-level. **Source or attachment provided → the task is actionable** — format/scope/approach are B-level at most; never escalate to A.
4. **Mark uncertainty** as `[假设: ...]` / `[待验证: ...]`. Never state an unverified claim as fact.
5. **Smallest sufficient route.** Most tasks touch 2–3 moves, not all nine.
6. **Mother-tongue gate:** would a native Chinese speaker say this? If not, rewrite the whole paragraph.
7. **Identity is context, not the task.** User's profession/domain may inform `technicalDetail` only when relevant to the task. A microelectronics student choosing a gift stays `technicalDetail=none`; a frontend engineer choosing a laptop stays `technicalDetail=medium`. Never bleed irrelevant expertise into unrelated domains.

## Walkthrough

### Example 1: code generation (medium tier, 6c)

Input: *"我需要一个 Python 脚本，每天自动备份 MySQL 数据库到 S3，出错了发钉钉通知。"*

```
intake:   intent=execute  taskTypes=[{type:code,role:primary},{type:plan,role:secondary}]
          knownContext=["MySQL→S3 backup","钉钉通知","daily cron"]
          missingContext=["MySQL版本","S3 bucket名","钉钉webhook URL","服务器OS"]
          uncertainPoints=[{content:"MySQL版本",level:B,action:assume_and_mark},
                           {content:"S3配置",level:B,action:assume_and_mark},
                           {content:"钉钉webhook",level:B,action:assume_and_mark}]

boundary: riskLevel=medium  complexityTier=medium  canAnswerDirectly=true
          truthConstraints=["不执行外部操作","不发送真实通知"]

route:    medium → strategy(STANDARD) → compose(6c)
          skip: solution-space, 6a, 6b, 6d

compose:  draftOutput.tier1="一份带错误处理和钉钉告警的 Python 备份脚本"
          draftOutput.tier2=["mysqldump子进程","boto3上传S3","钉钉webhook通知","systemd timer"]
          appliedAssumptions=["[假设: MySQL 8.0, Linux, Python 3.10+]",
                              "[假设: S3 bucket已创建, AWS credentials已配置]",
                              "[假设: 钉钉机器人webhook已获取]"]
```

### Example 2: prompt design (prompt optimization, 6b)

Input: *"我要让 AI 帮我写周报，设计一个 prompt 模板，只写工作内容不写感想，格式适合飞书文档。"*

```
intake:   intent=execute  taskTypes=[{type:design,role:primary}]
          knownContext=["周报prompt模板","只写工作内容不写感想","飞书文档格式"]
          structuredConstraints=[{type:forbidden,description:"不包含感想/心情/反思",source:"user"},
                                 {type:required,description:"输出格式适配飞书文档",source:"user"}]

boundary: riskLevel=low  complexityTier=medium  canAnswerDirectly=true

route:    medium → strategy(STANDARD) → compose(6b→6c)
          6b triggered: user explicitly wants a reusable prompt

compose:  hasPromptOptimization=true
          optimizedPrompt.short="角色+核心任务+输出格式(≤200字)"
          optimizedPrompt.standard="完整9段式(≤500字)"
          optimizedPrompt.detailed="标准+框架指令+验证步骤(≤800字)"
          rationale=["去除感想维度","飞书适配:短段落+分隔线+emoji可选","约束保留:不写感想"]
```

### Example 3: debug with divergence (high tier, 6c)

Input: *"线上 500 错误，偶发、重启后消失、日志无异常堆栈，已持续两周。"*

```
intake:   intent=debug  taskTypes=[{type:debug,role:primary},{type:analyze,role:secondary}]
          knownContext=["500错误","偶发","重启消失","无异常堆栈","持续两周"]

boundary: riskLevel=medium  complexityTier=high  canAnswerDirectly=true
          truthConstraints=["不假设环境","不做生产变更建议"]

route:    high → strategy(DEBUG) → 🔴 solution-space(divergence) → compose(6c)
          skip: 6a(无A级缺口), 6b(非prompt优化), 6d(非composite)

          strategy: workMode=DEBUG  successCriteria=["根因定位","最小复现","验证步骤"]
          solution-space: divergenceMode=debug
            divergeResult.count=6  anglesCovered=["input-boundary","recent-change","environment-diff",
              "data-state","timing-concurrency","dependency-chain"]
            convergeResult.top3 按 verifiability 排序: 输入边界→最近变更→环境差异
            excluded: "加日志/重启"类非假设动作 → 反坍缩闸触发

compose:  draftOutput.tier1="从输入边界和最近变更开始排查，按可验证性递进"
          draftOutput.tier2=["1.检查报错请求payload","2.git bisect定位引入commit","3.对比staging/prod环境差异"]
          appliedAssumptions=["[假设: 有trace/APM基础设施]","[假设: staging可复现]"]
```

### Example 4: composite with downstream (high tier, 6c+6d)

Input: *"分析当前微服务架构的瓶颈，给一个迁移方案，做成 8 页 PPT 向 CTO 汇报，每页不超过 3 条要点。"*

```
intake:   intent=report  taskTypes=[{type:analyze,role:primary},{type:present,role:secondary}]
          composite=true  domains=[]
          structuredConstraints=[{type:required,description:"每页≤3条要点",source:"user"}]

boundary: riskLevel=medium  complexityTier=high  canAnswerDirectly=true

route:    high → strategy(EXECUTIVE, 受众=CTO) → 🔴 solution-space → compose(6c+6d)
          skip: 6a(无A级缺口), 6b(非prompt优化)

          strategy: workMode=EXECUTIVE  audienceProfile.dimensions={explainDepth:brief,
            tone:direct, formality:professional, backgroundAssumed:practitioner}
          solution-space: divergenceMode=design  生成3个本质不同迁移方案
            排除: 违反truthConstraint[成本≤现有方案]的选项显式标注

compose:  6c humanContent: tier1="瓶颈→方案→路线图", tier2=[瓶颈诊断,方案对比,迁移阶段]
          6d machinePayload: slides_array(8页), 每页 {punchline,visual_prompt,speaker_notes}
             downstreamConstraints=["每页≤3条","结论先行","附风险页"]
             🛑 confirm downstream payload structure → dispatch
```

## Decision pipeline

### 1. Intake — understand what the user wants

Load `references/00-global-principles.md`（enums 和字段契约见该文件的词表注释）.

Read `references/01-intake.md` to parse:

- `intent` (one of learn/execute/decide/report/create/debug/explore — never empty)
- `taskTypes` (primary + optional secondary cognitive actions)
- `domains` (medical/legal/financial/academic/safety/privacy — tags, not taskTypes)
- `knownContext`, `missingContext`, `assumptions`
- `uncertainPoints` graded A/B/C
- `intentShiftDetected`, `clarificationNeeded`, `composite`

🛑 **A-level gap blocks task?** → ask the minimum question (with a default assumption), then STOP. Do not run the rest.

### 2. Boundary — assess risk, truth, and answerability

Read `references/02-boundary.md` to decide:

- `riskLevel` (low/medium/high) — judged by requested action, not topic keywords
- `complexityTier` (low/medium/high) — **the routing switch**
- `canAnswerDirectly`, `needClarification`, `needTool`, `needWebCheck`, `needSourceCheck`
- `truthConstraints` (concrete: "do not invent pandas 3.0 APIs", not vague morality)
- `uncertainClaims`, `sourceConflicts`, `responseConstraints`

Risk follows action, not keyword: analyzing a medical document's grammar ≠ medical advice. High-risk tasks that ask for unsafe final actions → `canAnswerDirectly=false` with safe-completion direction.

### 3. Route by complexityTier

| Tier | Scope | Load | Run |
|------|-------|------|-----|
| **low** | fact, one-step explain, small rewrite, chat | `06-interaction-compose.md` | compose 6c only |
| **medium** | advice, decision support, adapted explanation, small plan | `03-strategy.md` + `06-interaction-compose.md` | strategy → compose |
| **high** | design, debug, open exploration, creative, high-risk, composite | `03-strategy.md` + `05-solution-space.md` + `06-interaction-compose.md` | strategy → 🔴 solution-space (divergence gate) → compose (6a–6d). 🔴 Roundtable gate: novelty fail → escalate light/full per row 8 |

🔴 **Upgrade mid-run** when high risk surfaces, sources conflict, the user asks "why", failures repeat, or a downstream handoff becomes necessary.

Conditional references (do not default-load): `references/07-quality-gate.md`, `references/08-execution-control.md`, `references/09-memory.md`, `references/roundtable/` (仅 solution-space novelty fail 触发).

### 4. Compose — the only module the user sees

```
6a  Ask only if A-level gaps remain (each question carries a default)
6b  Optimize prompt only if user wants a reusable prompt
6c  Answer by intent + audience; tier output (tier1/tier2/tier3) only when substantial
    当 TaskState 携带 roundtable 标记时，6c 从 chairOutput 取 selectedDirection+mergedInsights 为素材，
    并把 disagreementResolution 标 unresolved/partial（缺省视为 unresolved）的分歧维度转写成"分水岭"
    呈现给用户——绝不替用户裁未决分歧（见 references/roundtable/compose-from-chair.md）。
    绝不暴露 chairOutput 字段名/角色名/数量。
6d  🛑 Composite only → load `references/skill-registry.yaml` → match capabilities → present ranked candidates with one-line descriptions (user may override) → preload all candidates' input contracts while user decides → read selected input contract → adapt upstream material into that contract. `_shared/downstreamPayload.schema.json` is fallback for slides/diagram/document/code, not the universal interface. machinePayload goes downstream; humanContent goes to user.
```

### 5. Quality-gate (internal, binary, no score)

🔴 Three layers, no bypass:

| Layer | Mechanism | Failure → |
|-------|-----------|-----------|
| Fatal redlines | One-vote fail | Revise via mapped `revisionTarget` |
| Quality gates | fingerprint / hard-to-vary / novelty | Revise via mapped step |
| Feeling gate | Highest law | Escalate |

Multi-fail priority: fatal > fingerprint > hard-to-vary > novelty > feeling.

🛑 **StopLoss:** same gate fails 3× → ship minimum viable version with known gaps noted; stop looping.

🔴 **Roundtable handoff (when active):** chairOutput.actualDisagreements 按 `disagreementResolution` 分流——标 `unresolved`/`partial`（缺省视为 unresolved）的维度 → 入 compose 6c，转写成"分水岭"呈现给用户（见 `references/roundtable/compose-from-chair.md`）；标 `resolved` 的维度与 rejectedIdeas → quality-gate 验证非空后丢弃，不入 compose。selectedDirection + mergedInsights → compose 6c 主素材（compose 负责改写为用户语言，不暴露 chair 内部术语/字段名）。unresolvedQuestions → 收成"动手前要定的事"(≤3 条) 或下一轮 6a 追问储备。

### 6. Execution-control (daemon, always on)
   - same strategy fails twice → switch strategy (concept-level, not reworded)
   - output grows without new done-state → roll back
   - 3 stalled rounds → ship minimum viable with known gaps.
   - 🛑 **Emergency landing reflex** (见 `00-global-principles.md` 原则 E): 资源见底(token/上下文/超时) → 立即 flush bestSoFar + `[未完成]` + 停。不硬撑。
7. Memory — after answering, run `09-memory.md` async (never block the answer).

## Failure modes

| 触发条件 | 一线修复 | 仍失败 → 兜底 |
|---|---|---|
| intake 无法确定 intent | best-guess intent + `clarificationNeeded=true`；绝不能留空 | 取 `explore` + `clarificationNeeded=true`，让 boundary 接住 |
| boundary 无法确定 riskLevel | 默认 `medium`；标 `uncertainClaims` | 升 `high` 并加入 `responseConstraints` 免责声明 |
| strategy 无法确定 workMode | 默认 `STANDARD`；标 B 级假设 | 降 complexityTier → 关掉 solution-space → 直通 compose 6c |
| 多来源冲突无法消解 | `sourceConflicts[].resolution="cannot_resolve"`；compose 双列呈现 | compose 终止该维度，输出仅述"存在分歧"，不选边 |
| quality-gate 同一 gate 失败 3 轮 | 触发 stopLoss；切 revisionTarget | ship 最小可用版（已知缺口附注），不再循环 |
| compose 6d machinePayload 校验失败 | 重试一次 6d；修正 payload 结构 | 放弃 machinePayload，仅交付 humanContent + 标注"下游未产出" |
| solution-space novelty fail（角度<阈值/无反直觉/全同类） | 产 roundtableDecision.enabled=true → 升级 roundtable light(3-4角色+chair) | light 坍缩共识 → 升 full(独立subagent+镜头) 或判失败退 STANDARD |
| token 耗尽 / 上下文溢出 / 快超时（基础设施失败） | C2 budgetTriage: converge(停止发散)→land(flush bestSoFar+`[未完成]`+停) | C5 durable checkpoint 落盘 → 新进程从断点续跑 |
| 断网 / 工具不可达（capability-loss） | C4 能力降级: 用内置知识 + 显式 `[待验证]` + 给用户自行验证步骤 | 硬依赖则 C5 存档 checkpoint + 告知"需联网，进度已存" |

## Memory (async, never in the main chain)

After the answer, run `09-memory.md`: 9a stable cross-task constants · 9b workflow emergence only when the same task family ≥3× + same-dimension correction + front-solvable · 9c isolate one-off anomalies. Never surface memory unless the user asks what's remembered.

## Anti-patterns

| # | 反模式 | 替代做法 |
|---|---|---|
| 1 | 暴露模块名/TaskState字段/redline编号/"正在运行 step X"给用户 | 只说答案 |
| 2 | 对单事实/一行查找/闲聊套流水线 | 直接答，跳过全流程 |
| 3 | 追问 B/C 级缺口假装严谨 | B 级：默认 + `[假设: ...]`；C 级：跳过 |
| 4 | 为"完整"编造缺失输入 | 标 `[待验证: ...]` 或问 A 级缺口 |
| 5 | 后续模块软化 boundary 设定的 truthConstraints | 每条 constraint 用原文注入 compose，不改写不降级 |
| 6 | 默认加载全部 reference 文件 | 按 complexityTier 梯次加载 |
| 7 | memory 更新阻塞主链 | 永远在回答之后跑 memory |
| 8 | composite 6d machinePayload 出现在用户对话里 | 6d 只发下游；用户只收 humanContent |
| 9 | 意图漂移后复用旧 state | intentShiftDetected=true → 重置下游 state |
| 10 | quality-gate 失败后无声重试 | 3 轮同 gate fail → stopLoss → 最小可用版 + 缺口清单 |
| 11 | solution-space 发散阶段无节制扩张选项 | optionSpace > 20 → 触发收敛闸，不再接受新角度 |
| 12 | 用户说"直接做别问了"还继续追问 | 停止所有追问，未解缺口全部用默认值 + `[假设: ...]`，进入 6c |
| 13 | 跳过 boundary 直接根据直觉决定 complexityTier | complexityTier 必须由 boundary 判出，绝不能由 compose 自行猜测路由 |
| 14 | 同一维度微调 2 次就当成"工作流浮现"录入 memory | 必须 ≥3 次同 task family + 同 dimension correction + front-solvable 三条件齐备 |
| 15 | 用户身份专业域渗入无关任务（如微电子学生送礼物→technicalDetail=high） | identity 只在与任务相关的维度启用；无关域 technicalDetail=none |
| 16 | 源材料已提供仍追问格式/范围/方法 | 附件/文本已给=任务可执行，format/scope 最多 B 级，不升 A |
| 17 | roundtable chair 产出 rejectedIdeas 空 + disagreements 空 → 假圆桌 | chair 级硬闸: 三空判 FAIL，退回重跑或降级 STANDARD |
| 18 | session 出现"作为 X 主义者/X 派"人格腔 | 词扫 FAIL；仅准"从 X 镜头看，真正的问题是…" |
| 19 | chair 的 rejectedIdeas/disagreements/chairOutput 字段名泄露到用户面前 | quality-gate 丢弃 chair 内部工件；compose 6c 必须转写为自然语言，原始字段永不露面 |

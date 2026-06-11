# collab-master-skill 开发日志

> 本文件记录开发单元、架构决策、测试原则和上线计划。配套设计规格见 `collab-master-skill-framework.md`。

---

## 开发单元清单

| # | 单元 | 状态 | 描述 | 上线落点 |
|---|------|------|------|----------|
| 1 | intake | in_progress | 自然语言 → TaskState 转换：intent / taskTypes / missingContext / A·B·C 不确定点 / 意图漂移检测 | `references/01-intake.md` |
| 2 | boundary | in_progress | 复杂度首闸：riskLevel / truthConstraints / needWebCheck / complexityTier 定档（低/中/高） | `references/02-boundary.md` |
| 3 | strategy | in_progress | audience profiling + mode-router 合体：successCriteria / audienceProfile / workMode / reasoningFrameworks | `references/03-strategy.md` |
| 4 | solution-space | in_progress | 发散收敛： ≥8 实质差异角度 + 反直觉角度 + A/B/C 排序；简单任务正确跳过 | `references/05-solution-space.md` |
| 5 | compose | pending | 交互编排 6a-6d：追问生成 / optimizedPrompt 三版 / draftOutput 分层 / machinePayload（复合任务） | `references/06-interaction-compose.md` |
| 6 | quality-gate | pending | 三层闸（致命/质量/感觉）：redlineViolations / revisionTarget / revisionNotes；开发期独立，上线折进 6c 收口 | `references/07-quality-gate.md`（逻辑内嵌 compose） |
| 7 | memory | pending | 异步记忆：9a/9b/9c 判断 / 工作流浮现（≥3 次 + 同维度修正）/ 异常隔离 | `references/09-memory.md` |
| — | execution-control | pending | 编排器 + 测试 runner：按 complexityTier 分流驱动链 + 全程守护进程（loop guard / L1-L4 升压 / 降级） | `references/08-execution-control.md` + 主 SKILL.md 调度骨架 |

> 状态取值：`pending` → `in_progress` → `done`

---

## 交接介质：TaskState JSON 快照

7 个 skill 不直接互相调用，而是**读写同一个 TaskState 对象**（类型见设计文档"推荐的数据结构"）。

```
调试机制（关键）:
  - 每个 skill = 一个纯函数: 读 TaskState 的某些字段 → 写回另一些字段。
  - 把每个阶段产出的 TaskState 冻存成 .json 快照。
  - 要调某个 skill，就拿它上游的快照当输入单独跑它，看它写回的字段对不对。
  - 这就是隔离调试 + 可重放：任一 skill 出 bug，不用从头跑整条链。
```

三个"不是被拆的模块"的东西：
- **execution-control** = 编排器 / test runner。不是链条里一站，是驱动链条 + 守护全程的那个。
- **global-principles + persona + `_shared/taskstate.schema.json`** = 共享上下文。每个 skill import：内功/叙事边界 + 懒惰锚点机制 + 母语反坍缩闸 + persona + **唯一机器契约**（enum / 字段 / required / additionalProperties:false）。`vocab.md` 只做人话注释。
- **memory** = 异步、独立生命周期（回合结束后跑），产物喂 audience，不在主链里。

---

## 串联顺序图

```
                     ┌─────────────── execution-control（编排器 + 全程守护进程）───────────────┐
                     │                                                                          │
  user → [1 intake] → [2 boundary 首闸定档] ─低─→ [5 compose 6c]〔6 质检收口〕→ out             │
                     │                       ─中─→ [3 strategy] → [5 compose] 〔收口〕→ out      │
                     │                       ─高─→ [3 strategy] → [4 solution-space] → [5 compose 6a-d]〔收口〕→ out
                     └──────────────────────────────────────────────────────────────────────┘
                                                                                   │
                                                                  回合结束后异步 → [7 memory] → 喂回 audience

  共享：00 global-principles + persona（每个单元 import）   交接：TaskState JSON 快照
```

### 驱动逻辑

```
按 boundary 给的 complexityTier 分流:
  understand: intake → boundary
    ├ 低档 → compose(6c) 直接出〔quality-gate 收口〕→ memory(异步)
    ├ 中档 → strategy(默认模式) → compose →〔收口〕→ memory
    └ 高档 → strategy → solution-space → compose(6a-6d) →〔收口〕→ memory
  升档随时发生：boundary 暴露 high risk / 用户追问"为什么" → 当场补走对应单元。
```

### 守护逻辑

全程后台，不等"轮到它"：监听 loop / 输出膨胀 / 分析瘫痪 / 放弃·甩锅信号 → Recovery Protocol 自救 → L1-L4 升压 → 降级。

---

## V1.5 开发日志

### Roundtable Operator：受控发散算子

**定位**：v1.5 增强能力，不进入 v1 主链。它不是 AI 人格扮演，而是一个**专门为复杂项目设计的受控发散算法**——核心价值在于强制模型显式完成三件事：

1. 并行提出**本质不同的假设**（而非同一思路的措辞变体）。
2. 暴露关键分歧和失败路径。
3. 由 chair 按操作化标准筛选、合并、拒绝候选方案。

**关键约束：跑完 divergenceMode 之后才考虑启用。** Roundtable 不是 solution-space 的替代品——solution-space 先用现有的 8 种 divergenceMode 跑一轮，如果 novelty gate 不过（反直觉不够 / 角度太少 / 所有方向落入同类），再考虑升级到 roundtable。硬拦截：`solution-space.shouldRun == false` 或 divergence 已经产生 ≥1 个反直觉方向 → 不开 roundtable。

### 三档启用

| 档位 | 名称 | 形式 | 何时用 | token 估算 |
|:----:|------|------|--------|:--------:|
| 1 | **adversarial-check** | 单模型自反：对 divergence 产出的 top3 各找 1 个最强反驳 | novelty gate 不过，但差距不大（角度 ≥5 只是无反直觉） | low |
| 2 | **mini-roundtable** | 3 个角色（按 taskType 动态选）+ chair；每个只输出核心假设 | novelty gate 不过且角度 <5，或在架构/策略/产品等高代价决策中 | medium |
| 3 | **full-subagent** | 真 subagent sessions，角色独立上下文 | 高复杂度 + 高代价 + 明显方案冲突三者同时满足 | high |

### 触发 vs 禁用

**启用条件（必须全部满足）：**

```
1. solution-space 已跑完当前 divergenceMode 且 novelty gate FAIL
2. boundary.complexityTier == "high"
3. strategy.workMode 为 CREATIVE / DEEP / DEBUG 之一
4. 任务不是事实查询 / 简单代码修改 / 已有唯一最优路径
```

**硬拦截（任何一条命中就不开）：**

```
- solution-space.shouldRun == false（solution 已经判断不需要发散）
- divergence 已产生 ≥1 个反直觉方向（novelty 已经过了）
- 用户明确要快 / 只要结论
- 医疗/法律/金融高风险场景（不能用 role-play 替代 boundary 判断）
```

### 按 divergenceMode 动态选取角色

角色不是固定 4+1 集合——随当前 `divergenceMode` 动态组合。chair 始终在场。

| divergenceMode | 角色组合 |
|----------------|---------|
| creative | user-advocate + divergent-thinker + critic |
| design / strategy | implementer + critic + divergent-thinker |
| debug | implementer + critic（按故障假设维度分工） |
| concept / essence | divergent-thinker + critic |

### 角色间的反坍缩机制

同一个 LLM 装多个角色最容易出的问题不是没分歧——是 4 个角色用不同措辞说同一件事。

**chair 的反坍缩职责：**

```
1. 汇总所有角色的核心假设（每个 ≤2 句话）。
2. 逐对检查任意两个角色的假设是否"语义相同只是措辞不同"。
   判据：把两个角色的假设发给一个没读上下文的人，他能区分这两句话的立场吗？
   不能 → 标记为重复，要求后者换方向。
3. 统计各角色使用的认知形状（钻井 / 2x2 / 光谱 / 反馈环 / 链式...）。
   如果 ≥3 个角色落入同一形状 → 发散失败，chair 随机给剩余角色分配不同形状重跑。
4. 如果所有角色的核心假设可被同一句话概括 → 整个 roundtable 视为表演，必须重来。
```

### chair 筛选协议（操作化）

不再用散文式的"抽取分歧、合并结论"。chair 的筛选沿用 solution-space 的收敛维度：

```
1. 每个候选方案在 4 个维度上打序（不打分）：
   goalFit / feasibility / differentiation / riskControl
2. 分歧按类型归因：
   方案 A 和 B 的差异源于【假设不同 / 约束优先级不同 / 风险容忍不同 / 信息不对称】——选一个。
3. 合并规则：
   如果两个方案的差异只在非核心参数（执行顺序/工具选择）→ 可以合并。
   如果两个方案的核心假设互斥 → 不合并，选一个。
4. chair 输出：推荐方向 + 被拒绝方向及其拒绝理由 + 分歧点清单。
```

### quality-gate 圆桌专项检查

```
- 所有角色的核心假设可被同一句话概括？→ FAIL（表演性圆桌）
- 没有任何一个方案被拒绝？→ FAIL（chair 没干活）
- 角色数量 < 3 时 chair 仍输出合并结论？→ FAIL（样本不足不应合并）
- 所有方案都落入同一认知形状？→ FAIL（反坍缩失败）
```

### 接入九形状反坍缩闸

chair 在汇总分歧时显式标注每个角色使用的认知形状。如果 ≥3 个角色用了同一形状 → 判定发散失败，随机分配不同形状给剩余角色重跑。这是 mode-router 九形状反坍缩闸在 roundtable 层的延伸——角色层面防止集体掉进同一个默认形状。

### 模块归属

| 模块 | 职责 |
|------|------|
| solution-space | 先跑 divergenceMode → novelty gate 判定 → 如需升级，设置 `roundtableEnabled` + 档位 |
| boundary | 在启用前做 token 预算估算（`estimatedTokenCost`），超阈值强制降档或跳过 |
| quality-gate | 圆桌专项检查（表演检测 / 拒绝项 / 形状一致性） |
| execution-control | 控制轮数上限、token 硬上限、chair 收敛截止条件 |

---

## 合成上线计划

策略：**拆开发、合上线**。开发期拆成 7 个独立 skill，各自隔离调试；上线期合成「一个主 skill（SKILL.md 当调度器）+ internal references（每个开发 skill → 一个 reference 文件）」，即 progressive disclosure 模式。

开发期能拆、上线不怕耦合的原因：**耦合是运行时问题**（小 skill 互相要数据会变瞎子）；**开发期手动喂输入**，不存在这个问题。

### 合成步骤

1. 7 个开发 skill 各自调通 → 内容搬进对应 reference 文件。
2. execution-control 的驱动逻辑 → 进 SKILL.md 的调度骨架；守护逻辑 → 08 reference。
3. quality-gate 内容 → 并进 06 的收口段（保留 07 作详解 reference）。

### 最终目录结构

```
collab-master-skill/
  SKILL.md                 ← persona 开篇 + 复杂度首闸路由 + 全局红线 + 指针（≤150 行目标）
  references/
    00-global-principles.md
    01-intake.md  02-boundary.md  03-strategy.md
    05-solution-space.md  06-interaction-compose.md  07-quality-gate.md(并进6c)
    08-execution-control.md  09-memory.md
```

### 开发期编排器使用方式

先写手动脚本当 mock 编排器（读快照、按顺序调各 skill、把输出写回快照）。各 skill 单独调通后，再把守护逻辑（loop guard / 压力升级）实现进去。

execution-control 单测方式：注入失败场景（同一假设重复出现、连续失败 N 次）→ 检查概念重复检测、L1-L4 是否按序升、降级输出对不对。

---

## 决策记录

| # | 决策 | 原因 |
|---|------|------|
| 1 | intake 和 boundary 拆成两个独立单元 | intake 职责 =「自然语言 → TaskState」，boundary 职责 =「判得准不准」。拆开才归因清晰：intake 的转换错误不会被误判为 boundary 的判定失败，反之亦然。单独拆才能干净验"这步转换成没成功"。 |
| 2 | strategy = audience + mode-router 合并为一个单元 | 两者都是"决定怎么答"，且 router 吃 audience 的输出，强耦合、各自偏薄。合在一起避免信息传递损耗。 |
| 3 | quality-gate 开发期独立、上线折进 compose 收口 | checker 是最好隔离测的东西，开发期单独拆价值最高（喂故意犯红线的坏输出 + 干净输出，看三层闸抓不抓得到）。但上线时它是 6c 产出的就地质检环节——不是独立一站——所以折进 compose 的收口段。 |
| 4 | execution-control 不在 7 个开发单元里 | 它不是链条里一站，是驱动链 + 守护全程的编排器。开发期先用手动脚本 mock 它，各 skill 通了再实现。 |
| 5 | memory 异步、独立生命周期 | 回合结束后跑，产物喂 audience，不在主链里。砍机制（保 9a/9b/9c 判断），不做复杂持久化。 |
| 6 | 拆开发、合上线的 progressive disclosure 策略 | 参考 ljg-qa 的模式：开发期 7 个独立 skill（可单独调试），上线期合成主 SKILL.md（调度器）+ references/*.md（详细逻辑）。既保证调试粒度，又保证运行时不会因拆散而丢失上下文耦合。 |
| 7 | intent 收回 7 个 + 建 `_shared/vocab.md` 词表注释 | 三个文件曾各跑一套词表（intake 私加 fact/write/plan/advise；mock 实际用了 explain/analyze 等连 skill 都没定义的值）。后果：下游 mode-router 收到不认识的 intent 会静默掉进 STANDARD，`learn→COACH`、`fact-check→FAST` 等触发器失灵。决定：intent 封闭为 7 个（learn/execute/decide/report/create/debug/explore），write/plan/advise/fact 一律降为 taskType，领域用 domains 标签（不斜杠拼）。后续已由决策 #8 升级：`taskstate.schema.json` 是唯一机器契约，`vocab.md` 退为人话注释。 |
| 8 | 引入 `_shared/taskstate.schema.json` 作唯一机器契约 + 校验闸 | 散文契约 + 多作者(Claude/Codex/DeepSeek) + DeepSeek 自写 mock 又自判通过性 = 漂移必然且静默（错的 mock 自洽地判 skill"通过"）。改成机器可校验契约：`enum` / `additionalProperties:false` / `required` 自动抓四类漂移；mock 答案卷先过闸B 才有资格判卷，斩断"对着错答案测试通过"。已用 jsonschema 实测：6 类漂移全 FAIL、合法用例 PASS。 |

---

## 契约与校验闸（防漂移机制）

**唯一机器契约**：`dev-skills/_shared/taskstate.schema.json`（JSON Schema 2020-12）。它是 enum 和字段契约的唯一机器真源；`vocab.md` 退为人话注释，不再另列 enum 值（防 schema↔vocab 二次漂移）。

### 三方怎么用

```
Claude(评审)  : 动契约时给 schema diff，用户签字后下发；不在 skill/mock 里就地造值。
Codex(生成)   : skill 全量输出过【闸A】= #/$defs/intakeOutput | boundaryOutput | strategyOutput (strict，必含全字段)。
                要新字段/新值 → 先进 schema，不自创。
DeepSeek(测试): mock 答案卷过【闸B】= #/$defs/mockCase (expected 用 *Assertion，可部分断言)。
                mock 先过闸B 才有资格判 skill；skill 输出再过闸A。"测试通过" = 语义对 ∧ schema 绿。
用户(审)      : 看校验红绿；注意力只花在 schema 查不了的【语义正确性】上。
```

### 机器能抓 / 抓不到

```
能抓(已实测 FAIL):
  enum 漂移         intent=explain / complexityTier=低        → enum
  未登记字段        boundary 私加 responseConstraintsX        → additionalProperties:false
  漏字段            少 domains                                → required
  斜杠拼 taskType    medical/advise                           → enum
抓不到(留给人审):
  语义错            "1+1" 该不该 low risk、risk 等级判断本身   → schema 只验结构，不验判断
```
DeepSeek 自写自判，最危险的恰是语义错——所以人审火力集中在它生成且自判的那些 mock 的期望值上。

### 运行

`pip install jsonschema`；对 JSON 实例校验对应 `$defs`（根放 `{"$ref":"#/$defs/xxx","$defs":<本文件的$defs>}`）。新模块(solution-space/compose/...)的字段，设计时按治理流程加进 schema 的 `taskState` 和对应 `*Fields`，再开发。

---

## 测试原则

### 两栏规则：recall + precision 都必须过

```
recall 栏（抓没抓到坑）: T1/T2/TB 行——该抬的 flag 抬了没？
precision 栏（误报）   : N 行——干净输入有没有被误标？
```

两栏都过才算这个 skill 调通。只过 recall = 一个见谁都报警的 skill，没用。

**intake 误报** = 给清楚/完整的输入硬造缺失项、或乱拆 taskTypes、或无谓追问。
**boundary 误报** = 给安全/通识的输入硬升 risk、硬 needWebCheck、把确定标成不确定。

### 负对照（N 类测试）的重要性

每个 skill 本质都是「该犹豫时抬 flag」。光测"抓没抓到坑"（recall）会把 skill 调成见谁都报警；必须同时测"干净输入有没有误报"（precision）。

### 关键词假触发检测（最毒的负对照）

句子里出现 医疗/法律/金融/投资 等词、但任务根本不是那回事——它直接验 boundary 是"真理解任务"还是"关键词匹配"。这类测试必须有。

典型案例：
- #19: "分析这段关于医疗器械文档的英文语法" —— "医疗"是话题不是任务，risk 不该为 high
- #20: "我想投资点时间学 Python，路线怎么排" —— "投资"非金融，risk 不该为 high

关键词假触发被升 risk = boundary 在做关键词匹配，不是真理解 → **不合格**。

### 隔离原则

- **一份共享语料**：原始场景可大半共用；intake 查自己的输出字段，boundary 查自己的。
- **boundary 的输入要手写干净 TaskState 快照**：别用真 intake 的输出当 boundary 输入——intake 有 bug 会污染 boundary 测试，破坏隔离。
- **每个 skill 必带"不该报警"负对照**。

### 每个 skill 的断言分两栏

```
recall 栏（抓没抓到坑）: T1/T2/TB 行——该抬的 flag 抬了没？
precision 栏（误报）   : N 行——干净输入有没有被误标？
  intake 误报 = 给清楚/完整的输入硬造缺失项、或乱拆 taskTypes、或无谓追问
  boundary 误报 = 给安全/通识的输入硬升 risk、硬 needWebCheck、把确定标成不确定
   特别盯 #19/#20/#15/#16: 关键词假触发被升 risk = boundary 在做关键词匹配，不是真理解 → 不合格

---

## V1.6 开发日志 — 下游自适应交接

### 问题

compose 6d 已有 machinePayload/downstreamConstraints/downstreamTrigger，但缺两个——"该发给谁"和"下游要什么格式"。

### 核心思路

不让下游适配 collab-master。反过来——查 registry → 展示候选 → 读下游 SKILL.md 的输入契约 → 组装材料。

### 落地内容

- `references/skill-registry.yaml`：注册 8 个下游 skill（ljg-card / html-ppt / baoyu-* 系列）
- `_shared/skill-registry.schema.json`：注册表校验
- `_shared/downstreamPayload.schema.json`：4 种 payload 格式（slides/diagram/document/code）
- `references/handover-payloads.md`：交接协议规格
- `validate.py`：新增 `downstream` 命令 + `registry` 命令
- SKILL.md compose 6d 段更新

### 决策

- 不自动安装下游 skill（安全红线）
- registry 内按 defaultRank 排序选择
- downstreamPayload.schema 退位为兜底格式，不是通用接口
- 自适应适配优先于固定 schema

### 验证

`validate.py downstream` 闸D 实测 PASS/FAIL 正确。

---

## V1.7 开发日志 — 验证闸

### 来源

obra/superpowers 的 verification-before-completion 哲学：可验证的成功断言必须带新鲜证据。

### 问题

现有 17 条红线管"别无中生有"，但不管"断言测试通过却没跑过测试"。

### 落地内容

1. Schema 修复：redlineViolations maximum 16→22（roundtable 已用 17-20，原来会被截断）
2. 红线 21 — unverified success：输出含可验证成功断言却无本会话新鲜证据 → FAIL，revisionTarget=execution-control
3. 红线 22 — hedged completion：完成断言 + 对冲词 + 无 [待验证] → FAIL（双条件保护诚实存疑文化）
4. 仲裁追加：0 > 21 > 22 > 1..16 > roundtable 17..20
5. 复审回路（08-execution-control.md）：修完必过同一道闸再审，同一闸再 FAIL 计重复失败喂 stop-loss

### 决策

红线 22 必须双条件（完成断言 AND 对冲词 AND 无标记）才 FAIL。只对冲词不完成断言（"这点我不确定 [待验证]"）= 诚实存疑 = PASS。保护项目自身的诚信文化。

### 治理

`validate.py self` 新增 `redlineViolations.maximum >= 22` 完整性自检（防回滚到 16）。

---

## V1.7.5 开发日志 — assess/vent + RISK + 6e/6f + compose 效率 + humanizer

### 落地内容

1. **assess + vent 意图**（intent 7→9）：assess 路由到 RISK 模式，vent 直通 compose 6c
2. **RISK 工作模式**（workMode 7→8）：强制三段输出——风险等级 + 判断依据 + 边界声明
3. **6e/6f 工作流**：6e 捕获用户"保存为工作流"，6f 按关键词重放
4. **compose 效率规则**：禁止铺垫首句、信息优先序、可删测试、情感收尾 ≤15 字
5. **humanizer-zh**：禁用词并入 redline 13，双防线（compose 预防 + quality-gate 检测）

### 落地的文件

- `references/01-intake.md`：assess/vent 意图
- `references/03-strategy.md`：RISK 模式路由 + domain≠expertise 规则
- `references/06-interaction-compose.md`：6e/6f + 效率规则 + 输出结构规则
- `references/07-quality-gate.md`：redline 13 扩展
- `references/06-workflow-capture.md`（新增）
- `_shared/taskstate.schema.json`：intent 9 值、workMode 8 值、新增 pipelineStepConfig/userWorkflow defs

---

## V1.8 开发日志 — 四力模型定制文件

### 核心思路

在 collab-master 和下游之间加"定制文件"（中间格式），受四股力约束：

- **力1**：collab 的 pipeline 产出（intake→boundary→strategy→solution-space→compose）
- **力2**：下游 skill 的输入契约（从 registry 读取）
- **力3**：用户的原始需求与硬约束（模板编号、字体、段落顺序、lockedZones）
- **力4**（v1.8.2 新增）：agent 评分建议（Force4 Design Review）

### 双模式

不由新建标签定义，由 audienceProfile 维度组合派生：
- actionOrientation=report + formality=professional → 下游是渲染引擎（模板固定，不可调格式）
- actionOrientation=create + technicalDetail≤low → 下游是共创伙伴（可重排版、加视觉隐喻）

### 子版本

- **v1.8.1** Reference Deck Ingestion：从人工优秀 PPT 反向提取模板语法，作为力3 参考输入
- **v1.8.2** Force4 Design Review：agent 评分建议作为第 4 力注入
- **v1.8.3** Force Preflight：先验 1↔3（内容符合约束），再验 2（格式符合下游），最后注入 customFile

### 验证回路

定制文件 → 下游产出 → 力1+力3 验证 → 不合规 → 分析 → 按力2 修改 → 重跑 → 循环。同一点连续 3 轮 fail → stopLoss。

---

## V1.9 开发日志 — 持久层

### 内容

1. 跨 session 记忆 adapter：读平台记忆文件（CLAUDE.md / .cursorrules）回注，不新建存储
2. 通用素材库：PPT 模板、图标、图片资源管理
3. PPT 模板说明书（artifact-template-extractor）：从 HTML deck 模板提取结构化描述

### 安全红线

- 绝不覆盖用户的共享文件，只读写自有命名空间区块
- 只从自己的区块回注，不把用户散文当记忆解析
- 回注记忆标 `provenance=reinjected`（历史，非当前事实）

---

## V1.10 开发日志 — 子任务并行调度

**状态**：规划中，未落地

### 问题

composite 任务串行效率低。前几步互不依赖的子任务可并行。

### 做法

`dependsOn: []` 的子任务不排队，execution-control 同时 spawn agent。不改 pipeline，改调度逻辑。

### 待钉死

1. DAG 谁产出（intake 还是新步骤）
2. fan-out 范围（父任务共享 intake/boundary/strategy）
3. merge 语义（subtaskResults[id] + 冲突规则）
4. checkpoint 兼容性（并行 DAG 状态 vs 串行假设）
5. 局部失败 + 闸控（子任务崩了，全局等死还是带缺口前进）
6. 双闸 review 回路（spec compliance + quality gate per subtask）

---

_[以下为 2026-06-11 恢复内容结束。v1.6-v1.10 详细设计原文在 framework.md 中丢失，本补写基于 references/ 实际文件状态 + 对话记忆。标注 [推断] 的地方可能有细节遗漏。]_
```

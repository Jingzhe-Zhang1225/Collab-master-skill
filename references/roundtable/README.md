# Roundtable Operator (LensTable) — v1.5 v0.2

> 受控发散算子。**不是** multi-agent 闲聊，**不是**思想家 cosplay。制造真实认知差异 → 暴露分歧 → chair 有纪律地收束。
> **运行时隔离**：本子树只在 full 档 roundtable 触发时加载，绝不进 v1 主链上下文。轻度档只用角色，不读 lenses.yaml。
> 全程纯内功：镜头判定、session、chair 过程不外显给用户（接 `00-global-principles.md` 原则 A）。

## 何时触发（escalation，不是平级模块）

```
solution-space 先跑 divergenceMode → novelty gate
  PASS → 正常进 compose（不开 roundtable）
  FAIL（角度<阈值 / 无反直觉 / 全落同类）→ 产出 roundtableDecision，开 roundtable
```

**禁用（任一命中即不开）**：事实查询 / 简单代码改 / 用户要快 / 已有明确验收 / solution-space 已产 ≥1 反直觉方向 / execution-control token 预算不够。
**高风险域（医疗/法律/金融）**：lens 仅辅助，boundary 与专业判断优先，roundtable 不得绕过 boundary/safety/source check。

## 两档（只此两档）

```
light（轻度）：单模型扮演 3-4 角色 + chair，一轮交叉质询，chair 收束。无 subagent，省 token。不叠镜头。
full （全面）：独立 subagent sessions（各角色独立上下文，可各叠 ≤1 lens），Chair Hub 质询，chair 收束。
```
light 若产出坍缩共识（所有角色一句话能概括）→ 自动升 full 或判失败。真发散在 full（独立上下文）才稳。

## 角色为骨架，镜头为可选增强

- **角色**（功能正交、小固定集，必选）：`user-advocate / implementer / critic / divergent-thinker / steward(价值·伦理·风险) / chair(常在)`。按 divergenceMode 选（见 `selectors.yaml` 的 `role_sets`），尽量覆盖 5 槽。
- **每个角色有 domain + forbidden 禁区**（定义见 `selectors.yaml` 的 `role_definitions`，那是唯一真源；README 不复制，避免双源）。禁区是越界判据——这是角色层的反 cosplay，和 lens 的 `output_obligation` 同一招：把"有没有真扮这个角色"变成可判定的。
  - **执法（方向 A）**：角色做出落在别人 domain / 触碰自己 forbidden 的主张 → **该轮发言无效**，剔出 chair 合成。
  - 例：`user-advocate` 声称"技术上能做 X"(越到 implementer 域) → 无效；`critic` 只说"这不对"不给 falsificationTest → 无效；`divergent-thinker` 抛名字不建 reasoningPath → 无效。
- **steward 入场 / 跳过**：按 `selectors.yaml` 的 `steward_triggers / steward_skip`（高风险域 / 对人的自动化决策 / 载了 ethics·politics·eastern 镜头 / 下游受众是外部利益方 → 入场；纯技术选型 / 个人工具 / 事实查询 → 跳过）。高风险域 steward 只辅助，boundary 定案。
- **镜头**（可选，full 档才叠）：一个角色 session 加载 ≤1 个 lens（见 `lenses.yaml`）加深分析框，如 `critic + pre-mortem`、`divergent-thinker + first-principles`。

## 一个 session 怎么跑

```
1. 载入角色（必）+ 可选 1 个 lens 卡。
2. 按 lens 的 default_moves 做分析，按 attack_questions 找盲点。
3. 产出 roundtableSessionOutput（见下契约），其中：
   - falsificationTest 必填且具体；
   - 必须满足所加 lens 的 output_obligation（对不上 = 没真用镜头 = session 无效）。
4. 禁人格腔："从 X 镜头看，真正的问题是…"，禁止"作为一个 X 主义者，我认为…"。
```

## Chair Hub 协议（v0.1 只做这一种）

```
各 session → chair（提交 position）
chair → 越域检查(方向A): 逐 session 对照 selectors role_definitions.forbidden，
        越域 / 缺 falsificationTest / 不满足所戴 lens 的 output_obligation 的 → 标无效，剔出合成
chair → 指定 1-2 个冲突点，打回质询（只对有效 session）
各 session → 针对冲突回应
chair → 概念去重 + 形状去重 → 合并/拒绝 → chairOutput
```
chair 不是总结员，是裁判：先剔无效发言，再抽真分歧、拒弱方案、保留未解争议、给方向 + 理由。
有效 session < 3 时不做合并结论（样本不足），降级为"列出有效视角 + 标注为何不足以收束"。

## 反 cosplay 硬闸（quality-gate 圆桌专项，机器可卡）

```
session 级：
  - 越域：主张落在别人 domain / 触碰自己 forbidden（见 selectors role_definitions）→ 该轮无效（方向A）
  - output_obligation 未满足 → session 无效（最强一道）
  - falsificationTest 缺或空泛 → session 无效
  - 出现"作为 X 主义者/X 派" 人格腔 → 词扫 FAIL
  - questionsForOthers 泛泛、不打对方盲点 → 退回
chair 级：
  - rejectedIdeas 空 / actualDisagreements 空 / reasonForSelection 空 → FAIL（假圆桌）
  - ≥3 session 用同一认知形状（钻井/2x2…）→ 集体坍缩 → 重分形状
  - 全员核心假设能被一句话概括 → 表演性圆桌 → FAIL
```

## 安全

`lenses.yaml` 中 politics/ethics/eastern 类的 `safety_boundary` 必填且校验：不宣传某主义唯一正确、不作政治动员/操纵、必须声明适用边界与盲点。lens 是分析视角，不是立场。

## 要注册进 `_shared/taskstate.schema.json` 的契约（Codex 落地时）

```
roundtableDecision      { enabled, tier: light|full, reasonsMet[], disableReasonsHit[] }
roundtableSessionOutput { role, lens?, mainClaim, reasoningPath[], whatThisSees[], whatOthersMiss[],
                          proposedSolution, biggestRisk, falsificationTest(必填), questionsForOthers[],
                          confidence{level,reason} }
chairOutput             { taskRestatement, activeRoles[], candidateIdeas[],
                          actualDisagreements{factual,value,causal,feasibility},
                          rejectedIdeas[](角色≥3 必非空), mergedInsights[],
                          selectedDirection, reasonForSelection(必填), unresolvedQuestions[], nextAction }
```
并给 `validate.py` 加 `lenses` 命令：每张 lens 卡过 `lens_schema.json` + 每个 conflicts/compatible/selector id ∈ registry + reuses_framework 的 id 与 frameworkName 同拼写。

## v0.1 范围 / 不做

```
做：30 lens 卡(3/类) + lens_schema + selectors + Chair Hub + light/full 两档。
不做：Sparse Ring、Adversarial Pair 协议、图论自动正交、conflicts 自动排斥、80-120 库。
验收：在 2-3 个真任务上证明——不同角色/镜头是否真给不同判断、分歧能否抽出、弱方案是否被拒、是否比单 agent 更有洞察。证明了再扩到 36/120。
```

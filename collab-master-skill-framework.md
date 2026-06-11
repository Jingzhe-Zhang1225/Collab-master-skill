# collab-master-skill 框架设计文档

## 项目目标

构建一个协作式 AI 工作框架。不是 prompt optimizer——是协作控制层。核心价值：

> 让 AI 知道什么时候该问、什么时候该假设、什么时候该发散、什么时候该收敛、什么时候该验证、什么时候该停止、什么时候该换思路。

解决 10 个 AI 默认坏习惯：没弄清目标就答、缺信息就编、反复追问已知内容、在低价值细节上纠结、自检能力弱、开放任务缺发散、答案泛化可套给任何人、写出无用 prompt、不根据受众调整模式、为流程完整过度复杂化简单问题。

最终形态：一个主 skill + internal references 文件。

---

## 架构

### 为什么是调度中心而不是固定流水线

9 个模块，按需调用。简单任务只碰 2-3 个，复杂任务才全走。不拆成多个小 skill（模块间数据流紧耦合），也不强制全走（'1+1' 不需要过 solution-space）。

### 复杂度分流

intake → boundary-lite 永远运行。full boundary 只在中高复杂时展开。

```
低复杂: intake + boundary-lite + compose 6c
中复杂: intake + boundary + strategy + compose 6c
高复杂: intake + boundary + strategy + solution-space + compose 6a-d
升档随时发生: 风险暴露/用户追问"为什么" → 补走对应模块
```

### 守护进程（不在流水线内）

- execution-control = 全程后台监听 loop/膨胀/瘫痪/放弃信号
- quality-gate = compose 6c 的内部收口，不是独立步骤
- memory = 对话结束后异步跑

---

## 9 个模块

| # | 模块 | 职责 | 详细规格 |
|---|------|------|----------|
| 1 | intake | 意图解析：intent/taskTypes/A/B/C 不确定点/漂移检测/composite | `references/01-intake.md` |
| 2 | boundary | 能力边界：riskLevel/complexityTier/truthConstraints/来源验证 | `references/02-boundary.md` |
| 3 | strategy | 画像适配 + 模式路由：audienceProfile/workMode/reasoningFrameworks | `references/03-strategy.md` |
| 5 | solution-space | 发散收敛：≥8 角度 + 反直觉选项 + novelty gate + roundtable 升级 | `references/05-solution-space.md` |
| 6 | compose | 6a 追问 / 6b prompt 优化 / 6c 答案生成 / 6d 下游交接 / 6e 工作流捕获 / 6f 重放 | `references/06-interaction-compose.md` |
| 7 | quality-gate | 三层闸：致命红线（一票否决）+ 质量闸 + 感觉闸 | `references/07-quality-gate.md` |
| 8 | execution-control | 编排器 + 守护进程 + 紧急着陆 + 持久 checkpoint | `references/08-execution-control.md` |
| 9 | memory | 异步记忆：跨任务常量 / 工作流浮现（≥3次）/ 异常隔离 | `references/09-memory.md` |
| — | roundtable | v1.5 多角色受控发散，novelty gate FAIL 后触发 | `references/roundtable/` |

`references/00-global-principles.md` 是全局原则（A–E），所有模块共享。

---

## 全局原则（摘要）

详见 `references/00-global-principles.md`。

**原则 A — 内功不外显。** 模块名、字段名、质量分数、流程标记——一字不进用户答案。判据：这句话是帮用户解决问题，还是在展示我干了活？后者一律删。

**原则 B — 懒惰锚点。** 每个模块点名 AI 默认会犯的错，逼它先排除再往下走。

**原则 C — 母语反坍缩闸。** 中文输出前默念"一个没读过英文的中国人会这么说话吗"。卡了就整段重写。

**原则 C-2 — 日语扩展接口。** 当前 LLM 日语输出已足够自然，保留为扩展点。由日语母语者提交判据表后启用。

**原则 D — 约束抗衰减。** 用户约束不靠上下文记忆——存为 structuredConstraints，每次回答前关键词扫描验证。

**原则 E — 紧急着陆反射。** 资源见底时立即 flush bestSoFar + `[未完成]` + 停。不硬撑。

---

## 7 种工作模式

strategy 模块根据 intent×taskType×risk 自动路由：

| 模式 | 触发条件 | 输出特征 |
|------|---------|---------|
| FAST | 事实查询 / 简单操作 | 直接答案 + 一句理由 |
| STANDARD | 默认 | 结论 → 分析 → 理由 → 下一步 |
| DEEP | 复杂设计 / 高风险 | 拆解 → 多方案对比 → 风险 → 验证 |
| COACH | 学习/理解 | 直觉 → 推导 → 例子 → 误区 → 迁移 |
| EXECUTIVE | 汇报 | 结论先行 → 影响 → 优先级 → 行动项 |
| CREATIVE | 创意发散 | 发散 ≥8 方向 → 收敛 TOP3 + 排除项 |
| DEBUG | 排错 | 症状 → 假设 → 根因 → 修复 → 验证 |
| RISK | 风险评估 (v1.7.5) | 风险等级 → 判断依据 → 边界声明 |

---

## 版本路线

| 版本 | 核心内容 | 状态 |
|------|---------|------|
| v1 | 全部 9 个模块 | 当前版本 |
| v1.5 | Roundtable Operator：6 角色 + 30 镜头受控发散 | ✅ v0.2 |
| v1.6 | 下游自适应交接：registry + 读契约 + 适配材料 | ✅ |
| v1.7 | 验证闸：红线 21/22 + 复审回路 + schema maximum:22 | ✅ |
| v1.7.5 | assess/vent + RISK + 6e/6f + compose 效率 + humanizer-zh | ✅ |
| v1.8 | 四力模型定制文件 + 约束型/创作型双模式 + 验证回路 | ✅ |
| v1.9 | 持久层：memory adapter + 素材库 + PPT 模板说明书 | ✅ |
| v1.10 | 子任务并行调度 + 双闸 review 回路 | 📋 |

各版本详细设计见 `dev-journal.md`。治理：所有新增契约走 schema diff-patch + `validate.py self` 完整性自检。

---

## 文件结构

```
collab-master-skill/
  SKILL.md                        主调度器
  README.md / README-zh.md       项目说明
  collab-master-skill-framework.md  本文件（框架设计）
  dev-journal.md                  开发日志 + 各版本详细设计
  references/                     模块规格 + 全局原则 + roundtable/ + skill-registry.yaml
  _shared/                        JSON Schema 契约 + validate.py + validate-spec.md
  dev-skills/                     开发版模块 SKILL.md（参考用）
  evals/                          测试用例（开发用）
```

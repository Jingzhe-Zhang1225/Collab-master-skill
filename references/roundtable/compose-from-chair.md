# Compose from Chair — 圆桌产出怎么变成用户答案

> 这份文件只在 TaskState 携带 roundtable 标记时生效，是 `06-interaction-compose.md` 6c 的子约束。
> 它**限制** compose：圆桌已经做完了思考，compose 不准重判、不准倒料、不准把真分歧抹平成假共识。
> 全程内功——chairOutput 的字段名、角色名、"圆桌/session/lens"这些词，一个都不许进用户答案。

---

## 为什么需要单独约束 compose

compose 默认会犯三件正好杀死圆桌价值的事：

```
1. 抹平：只取 selectedDirection 当结论甩出去，把 chair 明说"无法裁决"的真分歧丢了。
        → 花了 full 档的 token 制造真分歧，最后一米把它压平。等于没跑。
2. 倒料：把 chairOutput 整个结构（validationPlan/F1-F3/unresolvedQuestions）原样贴给用户。
        → 信息墙。用户要的是判断，不是会议纪要。
3. 漏壳：把 mergedInsights / rejectedIdeas / reasonForSelection 这些字段名、
        把 critic/steward/implementer 这些角色名带进答案。→ 破坏内功/叙事边界。
```

本文件就是堵这三个洞。

---

## 第一步：先认 chairOutput 是哪一种形状

三个真实样例落在三个不同形状上，**用户答案的写法由形状决定**，不能一个模板套到底：

| 形状 | 判据（看 chairOutput） | 样例 | 答案主线该长什么样 |
|---|---|---|---|
| **A 收敛** | `selectedDirection` 是多条逻辑链的交点，`reasonForSelection` 明说"不是折中、是收敛"，分歧基本在交点处被消解 | case1 AI客服选型（FTS5+LLM路由+人工止损 是唯一同过三闸的解） | 直接给那个收敛方向当结论。分歧降级成"为什么是它、不是那几个显而易见的替代"。**剩下的真未决=经验数字**，作为"动手前必须先量这几个数"附在后面 |
| **B 边界收敛** | 各方各自的论证**撞在同一道边界上**停下（伦理红线/物理约束），边界本身就是答案 | case2 简历伦理（三方都被"人对人终判不可外包"这道义务边界拦住） | 把那道边界当答案讲清楚——"能做 X，不能做 Y，界线在这"。分歧成了"为什么这条线必须在这"。操作层未决的进"还要定的几件事" |
| **C 未决分叉** | `actualDisagreements` 里有一条 chair **明说"当前回合无法裁决、需用户/数据分辨"**，且 `selectedDirection` 是带条件的起步选择（"先走这个，若 test 反转则回到另一个"） | case3 冥想App命名（"脱离工作身份" vs "重新定义暂停权"，两条逻辑各自成立、指向相反） | **不准把任一方当定论甩出。**必须先把分水岭摆给用户：有两个都自洽但相反的方向，区别在 X。再给"如果让我起步我选哪个、为什么"+ 决定胜负的那个测试 |

> 判形状的那一刻是 compose 唯一允许"读" chairOutput 内部结构的时候——读完只为决定答案骨架，读到的字段名一律不外泄。

---

## 第二步：chairOutput 每个字段的去向（什么活、什么死）

| chairOutput 字段 | 去向 | 怎么用 |
|---|---|---|
| `selectedDirection` | **活·答案主线** | A/B 形状当结论；C 形状当"推荐起步项"，且必须标明它是带条件的 |
| `reasonForSelection` | **活·但只取一层** | 转写成"为什么是这个方向"的一两句，不抄它的 (1)(2)(3) 编号结构 |
| `mergedInsights` | **活·融进答案** | 这是已经想清楚的取舍，化进正文（如 case3 的"调试隐喻只进交互层不进品牌名"）。**不许带 `from`/`retainedBy` 字段** |
| `actualDisagreements`（**未裁决**那条） | **活·一等公民（C 形状必须保留）** | 转写成用户能懂的"分水岭"。这是圆桌最值钱的产出，**默认保留，不默认丢** |
| `actualDisagreements`（已在交点/边界消解的） | 死·或降级 | A/B 形状里已被收敛吃掉的，不单独呈现；最多化进"为什么不是那个显而易见的替代" |
| `unresolvedQuestions` | **半活·收成"动手前要定的事"** | 挑**真影响用户下一步**的 1-3 条，写成自然语言的待办/待测。**不准当 FAQ 逐条罗列**，不准超过 3 条 |
| `validationPlan` / `nextAction` | 半活·压成"下一步" | 提炼成一句"先做哪件最轻的事去验"。F1/F2/F3 这种编号清单**绝不原样外显** |
| `rejectedIdeas` | 死·只做内部燃料 | quality-gate 验过非空即丢。最多借它写一句"为什么不走那个更直觉的方案"，但不点名"被拒方案列表" |
| `candidateIdeas` / `activeRoles` / `taskRestatement` | 死 | 纯内部工件，不进答案 |

**与现行 SKILL.md 的冲突点（需改契约）**：SKILL.md:196 现写
`rejectedIdeas + actualDisagreements → 验证非空后丢弃，不入 compose`。
这会把 C 形状的命脉一起丢掉。应改为：`actualDisagreements` 按 **resolved / unresolved** 分流——unresolved 的进 compose 当分水岭，resolved 的与 rejectedIdeas 一起验非空后丢。详见文末"契约 diff"。

---

## 第三步：限制 compose 的硬规则（违反即 quality-gate FAIL）

```
禁-1  不准把 C 形状的未决分歧压成单一 selectedDirection 甩出。
      自检：用户读完，知不知道"这里其实有两条路"？不知道 → FAIL。
禁-2  不准原样倒出 validationPlan / F1-F3 / unresolvedQuestions 全表。
      上限：动手前要定的事 ≤3 条，且是自然语言不是编号测试卡。
禁-3  不准泄露任何字段名/角色名/"圆桌·session·lens·chair·镜头"字样。
      角色的功劳要"无主"地化进答案——是"这个方向"好，不是"implementer 说"。
禁-4  不准重判 / 翻案。chair 拒的方案，compose 不准复活替用户翻供。
      （但 C 形状里 chair 标"未裁决"的，必须如实保留为未裁决，不许 compose 替它裁。）
禁-5  不准把 mergedInsights 抄成一串要点墙。融进正文的逻辑流，不是 bullet 堆。
禁-6  长度纪律照 6c tier：结论先行(tier1) → 关键判断(tier2) → 真分歧/取舍/待定(tier3)。
      圆桌不是给用户加篇幅的理由。
```

---

## 第四步：三个样例的"应然答案骨架"（给 DeepSeek 跑端到端当方向，不是成稿）

> 这些是**形状**，不是最终文案——DeepSeek 端到端跑出的成稿要过上面的硬规则。

**case1（A 收敛）骨架：**
```
[结论] 选 FTS5 主匹配 + 本地小模型只做意图路由(不做生成) + 平台独立 adapter + 硬止损线。
       一句话：让模型负责"听懂用户问什么"，不负责"替你回复"——夜里出不了幻觉。
[为什么是它] 它同时满足"夜间不漏单/架构能自己维护/最怕的三种死法在设计阶段就被堵死"。
            不是折中，是这几个要求逼出来的同一个解。（不点名三个角色）
[动手前先量] 上线前你得拿真实 FAQ 实测三个数：本地模型在低配机上的延迟、
            微信/钉钉回调超时阈值、FTS5 在你这行 1000 条后的召回曲线。
            ——这三个数决定方案成不成立，论文数据不算数。
[不外显] candidateIdeas 全表 / rejectedIdeas 列表 / activeRoles。
```

**case2（B 边界收敛）骨架：**
```
[结论=边界] 可以用 AI，但只能辅助：聚类、标注、按硬条件聚合。终判必须留在人手里，
           每个被拒的人能拿到一个人能对话的理由。这条线不是效率问题，是底线。
[为什么线在这] 5000份/3人的压力是真的，但它不能换掉"人对人做录用判断"这件事本身——
             这跟准确率多高无关。（不点名 deontology/care-ethics）
[还要定的事] 知情同意怎么前置（投递前 opt-in）、被拒理由由谁翻译成人话、
            3人在"只辅助不替代"下处理5000份的工时够不够——这几件没定之前别上线。
[不外显] "义务论/关怀伦理/功利主义"这些词，"三方在边界汇合"这种过程话。
```

**case3（C 未决分叉）骨架——最关键，最容易被 compose 抹平：**
```
[先摆分水岭] 这名字/调性背后其实是两个相反的方向，都说得通：
            一条是"让程序员彻底脱离工作身份"——所以要躲开终端、代码、调试这些符号；
            另一条是"用程序员熟悉的符号降低进入门槛"——所以反而该用终端美学。
            选哪条，取决于你的用户打开 App 是想"逃离工作"还是"换个姿势暂停"。
            ——这一步不准省，省了就是替用户假装这事已经定了。
[推荐起步] 如果让我先动手，我选「静栈」+ 亮底暖色这条：名字不用解释、2字容错高，
          而"断点"在中文里第一反应是"坏了/断了"。调试隐喻不丢——把它收进交互节奏，
          不放进品牌名。（这是 mergedInsight，无主地融进来）
[谁来定胜负] 一个最轻的测试就能分辨：拿名字给20个非程序员盲看，"静栈"负面联想率
            若反而高于"断点"，这个起步选择就得翻。先做这个，别先砸钱做 A/B。
[不外显] F1/F2/F3 全表、unresolvedQuestions 三条递归追问、"chair 自反性"那条。
```

---

## 自检（compose 收口前过一遍）

```
1. 我认对形状了吗（A 收敛 / B 边界 / C 未决分叉）？还是无脑套了"给个结论"模板？
2. 如果是 C：用户读完知道"这里有两条相反的路"吗？还是被我压成一个答案了？
3. 我把 validationPlan / F1-F3 / unresolvedQuestions 原样倒出去了吗？（应≤3条自然语言）
4. 答案里漏没漏字段名 / 角色名 / "圆桌·镜头·session"字样？
5. mergedInsights 是融进正文逻辑流了，还是堆成了一串要点墙？
6. 我有没有替 chair 翻供——复活它拒掉的方案，或替它裁了它说"未裁决"的分歧？
7. 长度是结论先行的 tier 结构，还是借圆桌给用户加了篇幅？
```

---

## 契约 diff（已落地 2026-06-10）

**SKILL.md**（roundtable handoff，section 5 + 6c 注）已改为：
```
chairOutput.actualDisagreements 按 disagreementResolution 分流：
  - unresolved / partial（缺省视为 unresolved）→ 入 compose 6c，作为"分水岭"转写给用户（本文件 C 形状）。
  - resolved（已在 selectedDirection 交点/边界处消解）→ 与 rejectedIdeas 一起，
    quality-gate 验非空后丢弃，不入 compose。
selectedDirection + mergedInsights 仍为 compose 6c 主素材。
```

**taskstate.schema.json**（`chairFields`，与 `actualDisagreements` 同级，新增 `disagreementResolution`）：
```
disagreementResolution: { factual?, value?, causal?, feasibility? }   // 每维 enum: resolved|unresolved|partial
```
- 维度对齐 `actualDisagreements`（factual/value/causal/feasibility），不是 per-entry 字段——
  避免把现有 chair 样例的 string→object 重构（会破坏 case1/2/3 的兼容性）。
- 可选字段，向后兼容：缺省 / 缺某维 = **unresolved**（保守：保留而非抹平）。
- `additionalProperties:false` + enum 卡住拼错的维度名和拼错的状态值（已实测 PASS/FAIL）。
- 这样"该不该保留某条分歧"从 compose 的主观判断 → chair 的显式标注 + validate.py 机器可查。

> 注：`actualDisagreements` 只存在于 chair 层（`chairFields`），session 层（`roundtableSessionOutput`）
> 没有这个字段，故 `disagreementResolution` 也只加在 chair 层。

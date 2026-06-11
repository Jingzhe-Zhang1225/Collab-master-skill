# Artifact Template Extractor (v1.9)

## Purpose

Turn a good human-made artifact (weekly report, proposal, meeting note, research summary, PRD,
email, resume, plan, PPT deck …) into a **reusable generation contract** — an `artifactProfile`
stored in the durable asset library, recallable and reusable across sessions.

The goal is **not** to copy the artifact's surface form. It is to infer **how to recreate a good
artifact of the same type for a new user and a new situation**.

One sentence the agent must hold:

```text
不要提炼"表面格式"，要提炼"产物的生成契约"：
  给谁看？为了解决什么问题？按什么顺序组织信息？每部分放什么？
  该用什么语气？该多长？哪些地方不能乱写？什么样的输出算好？
```

PPT and other visual artifacts emphasize **visual structure**; text artifacts emphasize **logic
structure, language, information density, and action orientation**. One abstract pipeline covers
both — the visual specifics live in an optional `visualProfile` (slidesProfile).

## Contract

Output is `customFile.schema.json #/$defs/artifactProfile`, stored at
`.collab/assets/<type>/{id}.json`, indexed by `taskstate #/$defs/durableAsset` in `memory.assets[]`,
referenced from `customFile.referenceArtifact.assetId`. Coarse category = `durableAsset.type`
(assetType enum); fine-grained type = `artifactProfile.artifactType` (free text).

## The 7 generalized layers

(Generalized from the v1.8.1 PPT four-layer: 布局→结构骨架, 元素→内容模块, 文字→语言+密度, 观感→定位+策略.)

```text
L0 产物定位   → artifactType + suitable/unsuitableScenarios + reader + writerRole
   不是判视觉风格，是判文档功能：这是给领导的轻量周报，不是深度复盘；是内部提案，不是对外销售。

L1 结构骨架   → structure[]: 每个 unit + function + presence(mandatory/optional) + order
   先说什么后说什么，每段承担什么功能，哪些必须有、哪些可删、顺序能不能变。
   文字产物的"角色"是 背景段/结论段/证据段/风险段/行动请求段(对应 PPT 的页面角色)。

L2 内容模块   → contentSlots[]: 每个 slot 的 fill / optional / avoid
   不是填空，是填有质量的信息。"本周完成"要含 做了什么/结果/数据/影响，而不是"完成了用户调研"。
   这些槽(目标/问题/结果/数据/风险/负责人/截止/请求)才是真正要填的，对应 PPT 的元素。

L3 语言表达   → languageProfile: tone / conclusionFirst / sentenceLength / terminology / formality
                + patterns(好写法) + antiPatterns(空话/AI 味)
   纯文字产物比 PPT 更吃这层。周报要短句、结论先行、动词明确、多结果少过程；
   提案要先建立问题再给方案、降低对方决策成本。杀"积极推进/持续优化/取得一定进展"。

L4 信息密度   → densityRules[]: 长度/条数/每条句数/数据密度/何时展开何时压缩
   该短则短该详则详。领导周报 300-600 字、每条≤2 行；项目周报 800-1200 字、风险带负责人+动作。
   这层专治 AI 味：该短时太长、该具体时太空、该给结论时绕圈、该存疑时硬拍板。

L5 使用策略   → usageStrategy: fixed / variable / removable + adaptationRules + generationRules
   固定项必保留、可变项随内容、不建议项(长背景/泛泛自评)。
   adaptationRules 按读者切换(领导/客户/同事/投资人/老师)；
   generationRules 是可调用规则("没数据不硬编"/"出现延期必写原因+下一步")。

L10 质量评估  → qualityCriteria: good[] + bad[]
   好周报：30 秒知道本周发生了什么、问题带下一步、计划是动作不是口号、不像 AI 总结。
   坏周报：全是"推进/优化/协助"、无结果无数据、问题模糊、计划不可执行。
   后续 force4 / 测试对标用。
```

## Visual specialization (PPT / deck)

For slide-based artifacts, additionally fill `artifactProfile.visualProfile` (= `slidesProfile`):

```text
dual channel(都跑互校): 逐页渲染截图(判观感/角色/风格) + 解析对象树(文本框/形状/图片/表格/坐标/字体/色)
L1 pageRoles  : 每页 roleTag(结构,可对齐) + roleText(自由) + keepPolicy + capacity；先判角色再看元素
L3 elementClasses: content/structural/decorative/brand；brand(logo/公司名/页脚) → imitationBoundaries → constraints.forbidden
L5 slideIndex : intent→页；非模块化 deck 标 modular=false 优雅降级
L2/L4         : 视觉语法落内嵌 styleProfile(visualDNA/layoutGrammar/typography/…)
铁律：不描述每页有什么，描述每页能用来干什么。
```

## Pipeline

```text
1. 识别产物类型(L0 functionally，不是视觉)        → artifactType + durableAsset.type 粗类
2. 识别使用场景(同类型不同场景差很多)              → suitable/unsuitableScenarios
3. 识别读者 + 写作者角色                            → reader + writerRole
4. 拆结构骨架(单元+功能+必需+顺序)                  → structure[]
5. 拆内容模块(每槽 fill/optional/avoid)            → contentSlots[]
6. 拆语言风格                                       → languageProfile
7. 拆信息密度                                       → densityRules[]
8. 拆固定项/可变项/可删项                            → usageStrategy.fixed/variable/removable
9. 提炼生成规则 + 适配规则                          → usageStrategy.generationRules/adaptationRules
10. 使用建议 + 失败风险 + 质量标准                   → qualityCriteria + scenarios
(视觉型产物追加 visualProfile，见上)
```

## Degradation

```text
材料读不到(deck/文件无法解析) → 不假装学过，问能否导 PDF/截图/贴文本；不编模板。
非模块化产物(定制叙事 deck / 一次性长文) → visualProfile.slideIndex.modular=false，只给整体使用建议。
信息不足以判某层 → 该层留空，不硬填；标注置信度。
```

## Self-Check

```text
1. 每个 unit/slot 说清了"为什么存在/该填什么"，不是只列"有什么"？
2. languageProfile.antiPatterns 抓了空话/AI 味；densityRules 给了可执行的长度/条数？
3. usageStrategy.generationRules 是 agent 能直接照做的规则(含"不能编什么")？
4. qualityCriteria 同时给了 good 和 bad？
5. 视觉型产物才填 visualProfile；文字产物不填。
6. 入了 .collab/assets/，memory.assets[] 加索引，customFile 用 assetId 引用？
```

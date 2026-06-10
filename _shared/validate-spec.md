# validate.py 规格（给 Codex 实现）

> 角色分工：这份规格由 Claude 出，**代码由 Codex 写**。DeepSeek 把它挂进测试流程。
> 目标：把 `taskstate.schema.json` 的两道闸自动化——任何 skill 输出 / mock 答案卷不过校验就别想算"通过"。
> 纯本地、无网络、确定性。依赖：`jsonschema>=4.18`（实测 4.26 可用）。

## 它解决什么

```
闸A：Codex 的 skill 全量输出，对着 strict 契约校验（必含全字段 + enum 合法 + 无多余字段）。
闸B：DeepSeek 的 mock 答案卷，对着 mockCase 校验（expected 用 *Assertion，可部分断言，但写出的值/字段必须合法）。
self：schema 自身能编译 + 内置漂移回归不被绕过（CI 兜底）。
```

schema 只验结构（enum / 字段 / 类型），**不验语义**（"1+1 该不该 low risk"靠人审）。

## CLI

```
python validate.py <command> [args]

命令：
  check  --def <DEFNAME> <file.json | -> [<file2.json> ...]
         对每个实例校验 #/$defs/<DEFNAME>。`-` 表示读 stdin（便于 skill_run | validate.py check --def intakeOutput -）。
         闸A 用法：--def intakeOutput | boundaryOutput | strategyOutput

  mocks  <cases.json>
         把整份 mock 文件（mockCase 数组）校验 #/$defs/mockFile。闸B 用法。
         逐条报告（按 mockCase.id），不是只报第一条。

  self   无参数。运行 Draft202012Validator.check_schema(schema)；再跑内置漂移回归（见下）。

  lint-md <mock-test-data.md>
         过渡用：正则从 Markdown 表里抠 intent= / taskTypes=[...] / domains=[...] /
         complexityTier= / riskLevel= 的值，查是否 ∈ schema enum。
         best-effort，不权威——mock JSON 化后用 `mocks` 取代它。

  list-defs
         打印 schema 里可用的 $defs 名字（方便查 --def 拼写）。
```

通用选项：
```
--schema <path>   默认 ./taskstate.schema.json（与本文件同目录）
--json            机器可读输出（见下），默认人类可读
--all-errors      默认就收集全部错误；保留此 flag 兼容，不截断
--quiet           只输出汇总行和非零退出
```

## 行为细节

1. **加载 schema**：读 `--schema`。先 `Draft202012Validator.check_schema(schema)`；不过 → 退出码 3（schema 本身坏了，别继续）。
2. **$ref 解析（关键，别写错）**：对名字 `D`，构造
   ```python
   sub = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$ref": f"#/$defs/{D}", "$defs": schema["$defs"]}
   validator = Draft202012Validator(sub)
   ```
   （已验证此法在 4.26 可用，无需手搭 RefResolver。）
3. **--def 不存在** → 退出码 2，提示 `unknown def 'X'; run list-defs`。
4. **收集全部错误**：用 `validator.iter_errors(instance)`，**不要 validate() 只报第一条**。每条错误给：
   - `path`：`error.json_path`（如 `$.expected.boundary.complexityTier`）
   - `message`：`error.message`
   - `value`：`error.instance`（出错的那个值）
5. **JSON 解析失败 / 文件不存在** → 退出码 2，指明是哪个文件、行列（如有）。
6. **mocks 命令**：先整体校验 `#/$defs/mockFile`；逐条用 `mockCase` 校验并按 `id` 汇报，这样作者一眼知道是哪条 mock 错了。

## 退出码

```
0  全部通过
1  发现校验失败（漂移）——这是"测试不通过"的机器信号
2  使用错误 / IO / JSON 解析失败 / 未知 def
3  schema 自身非法（check_schema 失败）
```

## 输出格式

人类可读（默认）：
```
[FAIL] boundary_out.json  (#/$defs/boundaryOutput)
   $.complexityTier : '低' is not one of ['low','medium','high']
   $.fooBar         : additional properties not allowed ('fooBar')
[PASS] intake_out.json    (#/$defs/intakeOutput)

2 files: 1 passed, 1 failed
```

机器可读（`--json`）——DeepSeek 的 harness 直接吃：
```json
{
  "summary": { "total": 2, "passed": 1, "failed": 1 },
  "results": [
    { "target": "boundary_out.json", "def": "boundaryOutput", "status": "fail",
      "errors": [
        { "path": "$.complexityTier", "message": "'低' is not one of ['low','medium','high']", "value": "低" },
        { "path": "$.fooBar", "message": "additional properties not allowed ('fooBar')", "value": null }
      ] },
    { "target": "intake_out.json", "def": "intakeOutput", "status": "pass", "errors": [] }
  ]
}
```
`mocks` 的 `--json` 里，每个 result 多带 `"id": <mockCase.id>`。

## 内置漂移回归（`self` 命令必须包含）

`self` 除了 check_schema，还要跑一组写死的样例，确认每道闸都"该红的红、该绿的绿"。最少覆盖这 11 条（已用 jsonschema 实测全部符合预期）：

```
intakeOutput   + 合法全字段                                  → PASS
intakeOutput   + intent="explain"                            → FAIL (enum)
intakeOutput   + 缺 domains 字段                             → FAIL (required)
boundaryOutput + 合法全字段                                  → PASS
boundaryOutput + complexityTier="低"                         → FAIL (enum)
boundaryOutput + 多出字段 fooBar                             → FAIL (additionalProperties)
strategyOutput + 合法全字段(name="mece" 小写)                → PASS
strategyOutput + reasoningFrameworks[].name="MECE"(旧大写)    → FAIL (frameworkName enum 已统一小写)
strategyOutput + dimensions.structurePreference=...          → FAIL (additionalProperties)
mockCase       + expected.intake.domains=["medicine"]        → FAIL (enum)
mockCase       + expected.intake.taskTypes[].type="medical/advise" → FAIL (enum)
```
任一条结果不符 → `self` 退出码 1。这是防"有人把 schema 改松了还没人发现"的回归网。

## 怎么挂进流程

```
Codex 写完一个 skill 单元：
  skill 对每条 mock 的 input 产出 output.json
  → python validate.py check --def <thisModule>Output output.json   # 闸A
  → 退出码非 0 → 这单元不算"写完"

DeepSeek 测一个 skill：
  → python validate.py mocks cases.json                              # 闸B：答案卷先合法
  → 退出码非 0 → mock 本身有漂移，先修 mock，别拿它判 skill
  → 再跑 skill 产出，逐条 check --def ...Output（闸A）
  → 通过性 = 闸B绿 ∧ 闸A绿 ∧ 语义对（语义那栏人审）

CI / 改完 schema 后：
  → python validate.py self                                          # schema 没被改坏、闸还咬得动
```

## 不要做的事

- 不要在 validate.py 里"修正"实例（只读校验，不改数据）。
- 不要让它联网、不要调用 LLM。
- 不要把 enum 列表硬编码进 validate.py——**一切取值来自 schema**，脚本只是个通用校验器。schema 改了脚本不用改。

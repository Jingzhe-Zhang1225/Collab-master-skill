# collab-master-skill

一个协作式 AI 工作框架。不是 prompt optimizer，是协作控制层。

当前版本：**v1**。

## 安装

```bash
# 安装全部（全局）
npx skills add <Jingzhe-Zhang1225>/collab-master-skill -g --all

# 安装单个 skill
npx skills add <Jingzhe-Zhang1225>/collab-master-skill -g --skill collab-master-skill
```

或 git clone：

```bash
git clone https://github.com/<Jingzhe-Zhang1225>/collab-master-skill.git ~/.claude/skills/collab-master-skill
```

## 核心价值

> 让 AI 知道什么时候该问、什么时候该假设、什么时候该发散、什么时候该收敛、什么时候该验证、什么时候该停止、什么时候该换思路。

## 模块

| 模块 | 职责 |
|------|------|
| intake | 输入理解：意图/任务类型/缺失信息/不确定点分级 |
| boundary | 能力边界：风险等级/真值约束/复杂度定档 |
| strategy | 画像适配 + 模式路由 |
| solution-space | 发散收敛：≥8 角度 + 反直觉选项 |
| compose | 6a-6d：提问/优化/答案生成/下游交接 |
| quality-gate | 三层闸：致命闸(17红线)/质量闸/感觉闸 |
| execution-control | 编排器 + 守护进程 |
| memory | 异步记忆：跨任务常量/工作流浮现/异常隔离 |

## 文件结构

```
collab-master-skill/
  SKILL.md              ← 主调度器
  README.md             ← 本文件
  references/           ← 按需加载的模块
```

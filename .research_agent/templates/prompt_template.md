# Prompt {round}

## 任务标题

{title}

## 任务背景

请读取并遵守：

- `AGENTS.md`
- `.research_agent/AGENTS.md`
- `PROJECT_RULES.md`
- `project_plan.md`
- `.research_agent/project_state.md`

本轮任务是根据项目计划书和当前进度设计下一步工作。

## 任务目标

1. 明确本轮需要完成的科研或工程目标。
2. 保持任务范围可执行、可检查、可记录。
3. 避免自动进入下一轮。

## 具体要求

- 不调用远程模型 API。
- 不自动生成下一轮 prompt。
- 不自动 commit 或 push。
- 所有新增代码、实验、文档应服务于项目计划书。
- 必须遵守 `PROJECT_RULES.md` 中与本轮任务相关的科研工程、数据、benchmark、模型、统计、文档、日志和低 token 规则。
- 新增说明类 Markdown 文档默认使用中文；代码标识、命令、配置键、字段名、路径、模型名和指标名保留英文。
- 如涉及数据、模型或 benchmark，必须注意可复现性和数据泄漏风险。

## 预期输出

- 本轮需要创建或修改的文件。
- 本轮需要运行的检查、测试或命令。
- 执行后必须生成 `ans_qes/result{round}.md`。

## 暂不执行

本文件只是任务提示词。生成后必须停止，等待用户确认后才能执行。

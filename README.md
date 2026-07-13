# Research Project

本仓库使用交互式科研项目推进模板。

## 使用方式

1. 填写或替换 `project_plan.md`。
2. 在 Codex / Claude Code 中要求读取 `AGENTS.md`、`.research_agent/AGENTS.md`、`PROJECT_RULES.md` 相关章节和 `project_plan.md`。
3. 先生成 `ans_qes/prompt1.md`，不要执行。
4. 用户审查 prompt 后，再明确要求执行。
5. 执行完成后生成 `ans_qes/result1.md`，然后停止。
6. 用户审查 result 后，再决定是否 commit。

每轮完成后必须停止。只有用户明确要求生成下一轮 prompt 时，才进入下一轮。

# Interactive Research Workflow Rules

本文件定义 Codex / Claude Code 在科研项目中逐轮推进工作的规则。

## 1. 项目定位

这是一个交互式科研项目推进模板，不是全自动 agent。

AI 的职责是：

- 阅读 `project_plan.md`、`PROJECT_RULES.md` 相关章节和项目规则。
- 在用户要求时生成 `ans_qes/promptn.md`。
- 在用户确认后执行某个 prompt。
- 执行后生成 `ans_qes/resultn.md`。
- 在用户确认后建议或执行 Git commit。
- 每个阶段完成后停止，等待用户下一条明确指令。

AI 不得：

- 自动生成下一轮 prompt。
- 自动执行刚生成的 prompt。
- 自动 commit。
- 自动 push。
- 调用远程 LLM API。
- 在用户未确认时覆盖已有 `resultn.md`。

例外：如果用户明确要求“继续 N 轮”或“从当前 result 继续执行 N 轮”，允许进入受限连续推进模式。该模式最多执行用户指定的 N 轮，不能无限循环，不能自动 push，遇到测试失败、不确定下一步、大文件/密钥风险、数据泄漏风险或需要破坏性操作时必须停止。

## 2. 每轮状态机

每轮只能处于以下状态之一：

```text
idle
prompt_drafted
prompt_approved
executed
result_reviewed
commit_suggested
committed
```

允许的转换：

```text
idle -> prompt_drafted
prompt_drafted -> prompt_drafted
prompt_drafted -> prompt_approved
prompt_approved -> executed
executed -> executed
executed -> result_reviewed
result_reviewed -> commit_suggested
commit_suggested -> committed
committed -> idle
```

禁止自动执行 `committed -> prompt_drafted`。必须由用户明确要求生成下一轮 prompt。

如果用户明确要求受限连续推进 N 轮，可以在同一轮用户指令下重复执行：

```text
prompt_drafted -> prompt_approved -> executed
```

但总轮数不得超过 N，且每轮必须保留 `promptn.md` 和 `resultn.md`。

## 3. 生成 promptn.md 的规则

触发条件：用户明确要求生成某轮 prompt，例如“生成 prompt1.md”“为下一步生成 prompt，不要执行”。

操作要求：

1. 读取 `project_plan.md` 的相关章节。
2. 用 `rg` 定位并读取 `PROJECT_RULES.md` 中与本轮任务相关的章节。
3. 读取 `.research_agent/project_state.md` 和 `.research_agent/progress.json`。
4. 检查 `ans_qes/` 中已有 prompt/result 编号。
5. 生成指定或下一个编号的 `ans_qes/promptn.md`。
6. 更新状态为 `prompt_drafted`。
7. 停止并等待用户审查。

生成 prompt 时不得修改科研代码，不得生成 `resultn.md`。

## 4. 执行 promptn.md 的规则

触发条件：用户明确要求执行某个 prompt，例如“执行 prompt1.md”。

操作要求：

1. 读取对应 `ans_qes/promptn.md`。
2. 读取 `PROJECT_RULES.md` 中与本轮任务相关的章节。
3. 按 prompt 执行本轮任务。
4. 运行必要检查或测试。
5. 生成或更新同编号 `ans_qes/resultn.md`，并记录是否满足相关项目规则。
6. 更新状态为 `executed`。
7. 停止并等待用户审查。

如果 `resultn.md` 已存在，除非用户明确要求覆盖或更新，否则不得直接覆盖。

## 5. 生成 commit message 的规则

触发条件：用户明确要求生成 commit message 或提交。

操作要求：

1. 检查 `git status`。
2. 读取本轮 `promptn.md` 和 `resultn.md`。
3. 建议格式为 `pN: 简短中文或英文摘要`。
4. 等待用户确认后才执行 `git commit`。
5. commit 后停止，不得 push，除非用户明确要求。

## 5.1 受限连续推进 N 轮

触发条件：用户明确要求继续固定轮数，例如“从 result5.md 继续执行 3 轮”。

操作要求：

1. 先运行 context summary 和编号检查。
2. 从下一个可用编号开始。
3. 每轮都必须生成 `promptn.md`、执行、生成 `resultn.md`、运行检查并更新状态。
4. 完成 N 轮后必须停止。
5. 遇到以下情况必须提前停止：
   - 测试或检查失败且不能局部修复；
   - 下一步科研或工程判断不确定；
   - 出现大文件、模型权重、密钥、数据泄漏或 benchmark 不公平风险；
   - 需要 push、外部凭据或破坏性操作；
   - 需要读取过宽上下文才能继续。
6. 除非用户明确要求自动 commit，否则只给 commit 建议。
7. 不得自动 push。

## 6. 科研项目质量原则

- 必须遵守 `PROJECT_RULES.md`。
- 不把研究项目当 demo。
- 避免一次性脚本成为核心流程。
- 数据处理、特征、模型、评估、解释和可视化应保持模块边界。
- 避免数据泄漏，尤其是 benchmark、split 和外部验证。
- 长任务应有日志或进度输出。
- 结果应可追踪到代码、配置、命令、数据版本和 Git commit。
- 文档默认中文，代码标识、文件路径、指标名和模型名保留英文。

## 7. 上下文预算规则

默认使用低上下文模式。项目变大后，AI 不得把计划书、日志、结果表、notebook、manifest、旧 result 文件和长 diff 一股脑读进上下文。

推荐顺序：

1. 先运行仓库摘要命令，例如 skill 级 `context-summary` 或本地 `scripts/research_flow.py status` / `check`。
2. 使用 `rg -n` 定位相关标题、函数、配置键、错误信息或文件路径。
3. 只读取与当前任务相关的最小片段。
4. 不默认读取完整日志；失败时优先看 stderr，再搜索日志中的 `ERROR`、`WARNING`、`Traceback` 或阶段名。
5. 不默认读取完整 TSV/CSV/JSON/manifest/notebook/result table；应先总结文件大小、行列数、列名、缺失值、唯一键和少量目标行。
6. 不重复读取大量旧 `ans_qes/result*.md`；优先读取最近 1-3 个相关 result，或使用摘要。
7. 如果必须扩大读取范围，先说明原因，再逐步扩大。

低上下文模式不是降低质量；必要的测试、数据泄漏检查、复现性检查和科学验证仍必须执行。

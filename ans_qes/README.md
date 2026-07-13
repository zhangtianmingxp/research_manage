# 项目 Prompt 与执行结果记录规则

本目录用于记录项目推进过程中的正式任务提示词和对应执行结果。

本项目采用两阶段机制：

1. 当用户明确要求“生成 prompt”时，AI 才生成 `promptn.md`。
2. 当用户明确要求“根据 promptn 执行”时，AI 才执行任务并生成 `resultn.md`。

这样做是为了把任务设计和任务执行分开，避免 AI 同时生成问题和答案导致任务不够严谨。

## 文件命名

```text
prompt1.md
result1.md
prompt2.md
result2.md
```

编号从 1 开始递增。新增 prompt 前应检查已有编号，选择下一个可用编号。

## 生成 promptn.md

只有当用户明确要求生成 prompt 时，AI 才创建新的 `promptn.md`。生成后必须停止，不得执行。

推荐格式：

```markdown
# Prompt n

## 任务标题

## 任务背景

## 任务目标

## 具体要求

## 预期输出

## 暂不执行
```

## 执行并生成 resultn.md

只有当用户明确要求执行某个 prompt 时，AI 才读取对应 `promptn.md`，执行任务，并生成同编号 `resultn.md`。生成后必须停止，不得进入下一轮。

推荐格式：

```markdown
# Result n

## 对应 Prompt

## 执行摘要

## 完成内容

## 涉及文件

## 命令记录

## 验证情况

## 风险与注意事项

## 后续建议
```

## 语言

所有 `promptn.md` 和 `resultn.md` 默认使用中文。英文术语、模型名、指标名、代码标识和文件路径可以保留英文。

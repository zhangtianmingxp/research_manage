# Scripts

本目录存放科研推进模板的辅助脚本。

`research_flow.py` 只负责状态读取、结构检查、编号推断、prompt 草稿生成和 commit message 建议。

它不会：

- 调用模型 API；
- 执行 prompt；
- 自动生成下一轮 prompt；
- 自动 commit；
- 自动 push。

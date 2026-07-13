# literature_catalog 模块

## 目的

提供可重复运行的论文 PDF 清单、accession 格式识别、TSV 主外键检查和证据引用检查。模块不负责自动解释论文，也不会调用远程 LLM。

## 输入

- `文献/研究/*.pdf` 与 `文献/综述/*.pdf`
- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- schema 中声明的 TSV 文件

## 输出

- `inventory` 写入 `data/curated/paper_files.tsv` 和 `data/curated/papers.tsv`。
- `validate` 在终端输出结构化 JSON 检查结果，不修改数据。
- `summary` 输出各表行数和缺失码计数。

## 使用

```powershell
python -m src.literature_catalog.cli --root . inventory
python -m src.literature_catalog.cli --root . validate
python -m src.literature_catalog.cli --root . summary
```

`inventory` 会复用现有相对路径对应的 `file_id` 和内容哈希对应的 `paper_id`，避免重跑时无故重排已有 ID。完全相同的 SHA-256 才自动标记为 `exact_duplicate`；题名相似不会自动合并。

## 常见问题

- PDF metadata 为空或乱码：该值只写入线索字段，不影响哈希清单；正式书目信息保持 `NR` 等待核验。
- PDF 数量变化：若与 schema 的当前基线不一致，`inventory` 会停止并提示先审查范围。
- accession 格式通过但在线不存在：格式状态与在线状态分列，不能把正则匹配视为数据库验证。
- `validate` 报外键错误：先检查规范表是否缺行，再检查宽表是否引用了错误 ID；不要用自由文本绕过外键。

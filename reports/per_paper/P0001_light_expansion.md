# P0001 轻量样本/归档展开报告

## 核心结论

- `ERP004055` / `E-MTAB-1948` 已从项目级推进到 13 个 ENA Run。
- ENA filereport 提供 26 条 FASTQ 元数据链接；所有 run 为 paired-end。
- 样本阶段轻量解析分布：{'G1': 2, 'prometaphase/M': 8, 'mid G1': 2, 'UNRESOLVED': 1}。

## 边界

- 细胞周期阶段主要来自 ENA alias 与既有论文级 pilot 证据，精确同步化起点、处理时长和样本表映射仍需补充材料。
- 本轮未下载 FASTQ 或 submitted read 文件，只保存官方返回的 URL、MD5 和大小字段。

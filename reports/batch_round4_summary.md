# Round 4 小批量扩展摘要

## 范围

本轮处理 `P0001`、`P0009`、`P0012` 三篇论文。未处理其他论文，未下载测序数据或大型补充材料，未修改原始 PDF。

## 主要结果

| paper_id | 论文状态 | 官方归档 | 样本/阶段记录 | 主要未决问题 |
| --- | --- | --- | --- | --- |
| P0001 | partial project-level verified | `E-MTAB-1948`, `ERP004055` | 4 个代表性阶段 | run 级编号、重复类型、补充表未核验 |
| P0009 | partial project-level verified | `GSE129997`, `PRJNA533460`, `SRP192917` | 5 个代表性阶段 | 精确释放分钟、SRR 展开未完成 |
| P0012 | partial project-level verified | `GSE168251`, `GSE168168`, `GSE168176`, `PRJNA706679` | 5 个代表性阶段 | 重复类型、8.7 GB RAW 包、run/file 展开未完成 |

## 数据产物

- `data/interim/pilot/round4_experiment_design.tsv`
- `configs/pilots/P0001.json`
- `configs/pilots/P0009.json`
- `configs/pilots/P0012.json`
- `reports/per_paper/P0001_pilot.md`
- `reports/per_paper/P0009_pilot.md`
- `reports/per_paper/P0012_pilot.md`

## P0008 兼容性

本轮没有重建或追加 P0008 的 Run/File 视图。P0008 的 `archive_samples.tsv` 仍为 60 行；Run 视图仍为 1,290 行；File 视图仍为 2,580 行。新论文只追加到论文级、实验级、条件/重复/批次、时间点、项目级 accession、证据、语义审计和未决问题表。

## 结论

schema v2.1.0 可以承载多论文的项目级和实验设计级信息，但当前 `archive_samples`、Run/File 视图和部分测试仍明显偏 P0008 试点。下一轮若要进入 SRR/ERR 级，需要先把 run-level 展开做成按 `paper_id` 分区的通用流程，并避免破坏 P0008 的历史计数。

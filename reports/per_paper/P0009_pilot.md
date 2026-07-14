# P0009 小批量核验报告

## 论文级结论

- 标题：Chromatin structure dynamics during the mitosis-to-G1 phase transition
- DOI：`10.1038/s41586-019-1778-y`
- PMID：`31776509`
- 期刊/年份：Nature, 2019
- 作者：Haoyue Zhang et al.
- 本轮状态：`partial_project_level_verified`

## 归档编号

- GEO Series：`GSE129997`
- BioProject：`PRJNA533460`
- SRA Study：`SRP192917`
- 官方快照：`data/interim/pilot/source_metadata/GSE129997_quick.xml`

GEO 官方页面显示 75 个样本，原始数据可通过 SRA 获得；本轮没有展开 SRR 或下载 FASTQ/矩阵文件。

## 实验设计摘要

研究对象为小鼠 G1E-ER4 细胞，使用 nocodazole-induced prometaphase arrest-release 建立 M-to-G1 时序。主要实验手段包括 in situ Hi-C、Capture-C、ChIP-seq。已记录代表性阶段：prometa、ana/telo、early G1、mid G1、late G1。

数据归属本轮判定为 study-generated / primary analysis，但 run-level sequencing generation 仍未展开，保留 `UNRESOLVED`。

## 未决问题

- `UI-P0009-001`：除 prometaphase 0 h 之外，ana/telo、early G1、mid G1、late G1 的精确释放分钟数未从补充方法表裁决。
- `UI-P0009-002`：SRA study 已确认，但 run 级 accession 未展开。

## 人工核验建议

下一轮可读取 GSE129997 的 sample-level MINiML 或 ENA filereport，只下载轻量 TSV，展开每个 GSM/SRR 的 assay、阶段和重复。

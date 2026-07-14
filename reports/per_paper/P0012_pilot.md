# P0012 小批量核验报告

## 论文级结论

- 标题：CTCF and transcription influence chromatin structure re-configuration after mitosis
- DOI：`10.1038/s41467-021-25418-5`
- PMID：`34453048`
- 期刊/年份：Nature Communications, 2021
- 作者：Haoyue Zhang; Jessica Lam; Di Zhang; Yemin Lan; Marit W. Vermunt; Cheryl A. Keller; Belinda Giardine; Ross C. Hardison; Gerd A. Blobel
- 本轮状态：`partial_project_level_verified`

## 归档编号

- GEO SuperSeries：`GSE168251`
- GEO SubSeries：`GSE168168`、`GSE168176`
- BioProject：`PRJNA706679`
- 官方快照：`data/interim/pilot/source_metadata/GSE168251_quick.xml`

GEO 官方页面显示 44 个样本，并列出 `GSE168251_RAW.tar` 为 8.7 GB。本轮只保存轻量 MINiML，不下载 RAW tar、COOL、BW 或 FASTQ。

## 实验设计摘要

研究对象为小鼠 G1E-ER4 CTCF-AID-mCherry 细胞，使用 nocodazole arrest-release 建立 M-to-G1 时间轴，并用 auxin-inducible degron 急性降解 CTCF。已记录 0 h、30 min、60 min、120 min 和 120 min + triptolide 的代表性条件。

扰动：

- CTCF protein：auxin-inducible degron，预期在 M-to-G1 重构期间耗竭 CTCF。
- transcription initiation：triptolide 化学抑制，预期抑制转录起始。

## 未决问题

- `UI-P0012-001`：GEO 样本名含 rep 标签，但生物/技术重复类型未裁决。
- `UI-P0012-002`：8.7 GB RAW 包未下载，run/file 级映射未展开。

## 人工核验建议

下一轮可读取 GSE168251 subseries 的 sample-level metadata 与 ENA/SRA run selector 轻量表，拆分 no auxin、with auxin、triptolide 条件到 GSM/SRR 级。

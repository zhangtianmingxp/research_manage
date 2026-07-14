# P0001 小批量核验报告

## 论文级结论

- 标题：Organization of the Mitotic Chromosome
- DOI：`10.1126/science.1236083`
- 期刊/年份：Science, 2013
- 作者：Natalia Naumova; Maxim Imakaev; Geoffrey Fudenberg; Ye Zhan; Bryan R. Lajoie; Leonid A. Mirny; Job Dekker
- 本轮状态：`partial_project_level_verified`

## 归档编号

- ArrayExpress / BioStudies：`E-MTAB-1948`
- ENA study：`ERP004055`
- 官方快照：`data/interim/pilot/source_metadata/E-MTAB-1948_biostudies.json`

本轮只核验项目级归档入口，未展开 ERR/SRR 或文件级下载链接。

## 实验设计摘要

PDF 正文支持该研究使用 5C 和 Hi-C 比较人源细胞不同细胞周期阶段的染色质组织。已记录代表性阶段：early G1、mid G1、thymidine-arrested early S phase、nocodazole-arrested prometaphase。

同步化/采样边界：

- thymidine arrest：作者明示为 early S phase。
- nocodazole arrest：作者明示为 prometaphase；正文提及最长 12 h nocodazole 分析，但样本级时间点到 accession 的映射仍未展开。

## 未决问题

- `UI-P0001-001`：重复类型未裁决。
- `UI-P0001-002`：ENA study 已确认，但 run 级 accession 未展开。

## 人工核验建议

下一轮应优先读取 Science supplementary tables 或 ArrayExpress sample metadata，核验 GenBank/ENA run 级编号、样本名、重复类型和 5C/Hi-C 的样本到文件映射。

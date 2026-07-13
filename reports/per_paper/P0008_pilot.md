# P0008 试点核验摘要

## 论文

- 题名：A pathway for mitotic chromosome formation
- 引文：Gibcus et al., *Science* 359, eaao6135 (2018)
- DOI：`10.1126/science.aao6135`
- PMID：`29348367`
- 本地文件：`文献/研究/2018-Science-A pathway for mitotic chromosome.pdf`
- 文件 SHA-256：`d326f8b93f4de863cef2430409509933fdfb2021ceffc4e7f5b17dafb1ee80f6`

## 选择理由

该 PDF 文本可提取，正文同时明确给出同步化、分钟级采样、mAID/auxin 扰动、Hi-C 数据和 GEO accession，适合验证本项目的核心数据链。文件仅 14 页，能够在第一轮保持有界阅读。

## 代表性实验设计

作者在 chicken DT40 细胞中表达 analog-sensitive CDK1，并破坏 endogenous CDK1。使用 `1NM-PP1` 处理 10 h 使超过 90% 细胞阻断于 G2；洗脱 `1NM-PP1` 定义为时间零点，随后同步进入 prophase。论文报告的代表性采样包括 0、2.5、5、7.5、10、15、30 和 60 min。晚期样本使用 nocodazole 阻断 metaphase-anaphase transition，且论文另报告一个无 nocodazole 的 30 min 重复。

周期阶段只按作者文本记录：0 min 为 G2；5–10 min 属于 prophase/late prophase 与 NEBD 时间窗；15–60 min 属于 prometaphase进程。2.5 min 没有在目标证据段得到独立阶段标签，因此保留 `unknown`。

## 代表性扰动

SMC2 融合 minimal auxin-inducible degron，并在表达 OsTIR1 的细胞中用 auxin 处理。auxin 在 `1NM-PP1` G2 阻断期间处理 3 h，使 SMC2 降至 5% 以下，从设计上同时破坏 condensin I 和 II。论文观察到染色单体不能正常解析，且细胞不能正常完成有丝分裂退出。

## 归档核验（schema v2更新）

- 论文 Data and materials availability 声明 Hi-C 数据为 `GSE102740`。
- NCBI GEO 官方 Series 页在 2026-07-13 显示该记录公开，包含 60 个样本。
- GEO Relations 字段关联 `PRJNA398543` 和 `SRP115572`。
- GEO 页面说明 raw data available in SRA，并提供约 192.7 GB 的处理数据归档；本轮未下载。
- 2026-07-13重新查询GEO MINiML、NCBI SRA ESearch/EFetch和ENA Portal API，4次官方请求均成功且无需重试。
- GEO返回60个唯一GSM：58个*Gallus gallus*、2个*Homo sapiens*；每个GSM均带BioSample与SRX官方关系。
- NCBI和ENA均返回1,290个唯一Run，集合交集为1,290，仅NCBI和仅ENA均为0。
- ENA API返回2,580个paired-end FASTQ文件字段，URL、字节数和MD5覆盖率均为100%；未下载文件正文，也未把手工拼接链接标为已验证。
- 两个HeLa S3样本在正文中被描述为此前已报告数据的更深测序后重新分析，因此`own_data_status`保守记为`unclear`。

## 试点暴露的数据模型问题

1. Series 级记录可以覆盖多个实验，但仍需后续建立 GSM/SRS/SRX/SRR 到实验和时间点的一对一或一对多映射。
2. 同一时间点可能存在 nocodazole 与无 nocodazole 重复，需要在批量阶段增加或严格使用条件/批次字段，避免只按时间合并。
3. “late prometaphase”与形态学上“fully condensed metaphase chromosomes”的表述可以并存，不能强行压成单一阶段标签。
4. 官方数据库临时不可用时，需要保留失败查询证据并重试，不能把失败解释为 accession 不存在。

## 本轮覆盖边界

当前已完成GSE102740全部60个GSM及公开Run/FASTQ元数据映射，并增加CAP-H、CAP-H2和HeLa比较实验实体。R1/R2重复类型、日期alias的正式批次含义，以及HeLa样本的精确自产/复用分类仍保持未解决。该结果只覆盖P0008，不能代表其余27篇规范论文已完成。

机器可读与人类可读对账分别见`reports/P0008_accession_reconciliation.tsv`和`reports/P0008_accession_reconciliation.md`。

# P0012 Run/File 级扰动导向核验报告

## 核心结论

- GEO SuperSeries `GSE168251` 解析到 44 个 GSM；两个 SubSeries 各 22 个样本。
- ENA/NCBI run 集合一致，本轮展开到 102 个 Run 和 182 条 FASTQ 元数据链接。
- assay 分布：ChIP-seq 22，Hi-C 22。
- ENA 返回的 project_accession 分布：{'PRJNA706396': 22, 'PRJNA706676': 80}；与配置中的 `PRJNA706679` 关系保留为待人工核验问题。

## 扰动层级处理

- `auxin` 作为 CTCF-AID 降解处理记录，直接靶标为 CTCF。
- `triptolide` 作为转录起始抑制处理记录。
- `Pol II`、`CTCF`、`Rad21`、`input` 仅作为 ChIP-seq 检测靶点/对照，不与扰动靶标混写。

## 仍未解决

- rep 标签尚不能裁决生物重复或技术重复。
- `PRJNA706679` 与 ENA run 行返回的 `PRJNA706396`/`PRJNA706676` 之间的项目层级关系需要人工复核。
- 本轮未下载 `GSE168251_RAW.tar` 或任何 FASTQ/SRA 大文件。

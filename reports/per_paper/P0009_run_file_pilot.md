# P0009 Run/File 级核验报告

## 核心结论

- 论文：`Chromatin structure dynamics during the mitosis-to-G1 phase transition`
- DOI：`10.1038/s41586-019-1778-y`
- GEO Series：`GSE129997`；BioProject：`PRJNA533460`；SRA Study：`SRP192917`
- 官方样本数：75 个 GSM；SRA/ENA Run 数：120；FASTQ 链接数：195
- assay 分布：Hi-C 10；Capture-C 20；ChIP-seq 45
- 阶段分布：{'ana/telophase': 15, 'asynchronous': 5, 'early G1': 15, 'late G1': 10, 'mid G1': 15, 'prometaphase': 15}

## 本轮确认

- GEO family MINiML 的 Treatment-Protocol 明确给出 `0 / 25 / 60 / 120 / 240 min` 对应 `prometa / ana.telo / early-G1 / mid-G1 / late-G1`。
- `asyn` 样本保留为 asynchronous comparator，不被强行放入 release 时间轴。
- `SRP192917` 已展开到 120 个 Run；ENA filereport 提供 195 个 FASTQ 链接、MD5 和字节数。
- 单端与双端 run 已区分：paired-end 75 个，single-end 45 个。

## 仍未解决

- Capture-C 的具体 bait/locus 目标未在 raw metadata 中逐GSM显式声明，因此 `measurement_target` 保留 `NR`。
- `commd3_mutant` 样本标题提示 mutant 背景，但工程技术、预期效果和直接靶标细节未在当前保存的官方 metadata 中显式给出。

## 产物

- `data/interim/pilot/P0009_run_file_catalog.tsv`
- `data/interim/pilot/source_metadata/GSE129997_family.xml(.tgz)`
- `data/interim/pilot/source_metadata/SRP192917_runinfo.csv`
- `data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv`

## 说明

- 本轮未下载 FASTQ、SRA、矩阵或其他大文件，只保存官方轻量快照并离线构建表格。

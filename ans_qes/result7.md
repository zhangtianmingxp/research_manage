# Result 7：覆盖率优先小批次扩展（P0006 / P0007 / P0011 / P0016）

## 执行范围

本轮严格按 `ans_qes/prompt7.md` 执行，最终选择并推进了 4 篇研究论文：

- `P0006` `10.1038/nature24281`
- `P0007` `10.15252/embj.201798004`
- `P0011` `10.1038/s41588-020-00744-4`
- `P0016` `10.1016/j.cell.2024.04.014`

未继续使用 `P0002`，原因是其 `GSE51334` 入口过大且混入大量外部样本，超出本轮“轻量快照 + 保守落表”的风险阈值。未生成 `prompt8.md`，未 commit，未 push。

## 为什么选这 4 篇

- `P0006`：本地 PDF 明确命中 `GSE93431`，入口单一，适合轻量扩展。
- `P0007`：本地 PDF 明确命中 `GSE102884`，GEO / SRA / ENA 层级清晰。
- `P0011`：本地 PDF 明确命中 `GSE135180`，可补上 2020 年代表性论文。
- `P0016`：本地 PDF 仅命中 `GSE254182`，单入口、适合快推。

候选比较表已保存：

- `data/interim/pilot/round7_candidate_selection.tsv`

## 每篇论文达到的层级与新增规模

| paper_id | 归档入口 | 达到层级 | GEO sample | Run | File |
|---|---|---:|---:|---:|---:|
| P0006 | `GSE93431` / `SRP096571` / `PRJNA360958` | Run/File | 32 | 90 | 186 |
| P0007 | `GSE102884` / `SRP115913` / `PRJNA399157` | Run/File | 30 | 37 | 62 |
| P0011 | `GSE135180` / `SRP216929` / `PRJNA557678` | Run/File | 128 | 128 | 142 |
| P0016 | `GSE254182` / `PRJNA1068944` | Run/File | 100 | 100 | 194 |

本轮合计新增：

- 290 个 GEO sample
- 355 个 Run
- 584 条 FASTQ 元数据链接

## 每篇主要已确认字段

### P0006

- assay：`ChIP-Seq|Hi-C|RNA-Seq`
- 物种：`Mus musculus`
- 已确认归档入口：`GSE93431` / `SRP096571` / `PRJNA360958`
- 主要已确认字段：GSM、SRX、Run、BioSample、library strategy、platform、FASTQ metadata links
- 仍未裁决：同步化起点、采样时间轴、own_data_status、扰动/预期效果的细粒度字段

### P0007

- assay：`ChIP-Seq|Hi-C`
- 物种：`Homo sapiens`
- 已确认归档入口：`GSE102884` / `SRP115913` / `PRJNA399157`
- 主要已确认字段：GSM、SRX、Run、BioSample、species、sample source、FASTQ metadata links
- 仍未裁决：同步化与细胞周期时间轴、扰动靶标与预期效果的细化

### P0011

- assay：`ATAC-seq|ChIP-Seq|OTHER|RNA-Seq`
- 物种：`Mus musculus`
- 已确认归档入口：`GSE135180` / `SRP216929` / `PRJNA557678`
- 主要已确认字段：多 assay run-level library strategy、GSM/SRX/Run 映射、FASTQ metadata links
- 仍未裁决：多 assay 混合提交下的更细样本设计、同步化字段、自产/复用边界

### P0016

- assay：`ChIP-Seq|OTHER`
- 物种：`Gallus gallus`
- 已确认归档入口：`GSE254182` / `PRJNA1068944`
- 主要已确认字段：GSM、SRX、Run、ENA file links、species/source
- 说明：本轮未发现可直接保存的 SRA RunInfo 快照，但 ENA filereport 已足够推进到 Run/File 层
- 仍未裁决：同步化/时间轴、扰动解释、own_data_status

## 保存的官方轻量快照

### P0006

- `data/interim/pilot/source_metadata/GSE93431_quick.xml`
- `data/interim/pilot/source_metadata/GSE93431_family.xml.tgz`
- `data/interim/pilot/source_metadata/GSE93431_family.xml`
- `data/interim/pilot/source_metadata/SRP096571_runinfo.csv`
- `data/interim/pilot/source_metadata/PRJNA360958_ena_filereport.tsv`

### P0007

- `data/interim/pilot/source_metadata/GSE102884_quick.xml`
- `data/interim/pilot/source_metadata/GSE102884_family.xml.tgz`
- `data/interim/pilot/source_metadata/GSE102884_family.xml`
- `data/interim/pilot/source_metadata/SRP115913_runinfo.csv`
- `data/interim/pilot/source_metadata/PRJNA399157_ena_filereport.tsv`

### P0011

- `data/interim/pilot/source_metadata/GSE135180_quick.xml`
- `data/interim/pilot/source_metadata/GSE135180_family.xml.tgz`
- `data/interim/pilot/source_metadata/GSE135180_family.xml`
- `data/interim/pilot/source_metadata/SRP216929_runinfo.csv`
- `data/interim/pilot/source_metadata/PRJNA557678_ena_filereport.tsv`

### P0016

- `data/interim/pilot/source_metadata/GSE254182_quick.xml`
- `data/interim/pilot/source_metadata/GSE254182_family.xml.tgz`
- `data/interim/pilot/source_metadata/GSE254182_family.xml`
- `data/interim/pilot/source_metadata/PRJNA1068944_ena_filereport.tsv`

所有新查询均已登记到：

- `data/interim/pilot/source_queries.tsv`

## 新增或更新的代码、表和报告

### 代码

- 新增 `src/literature_catalog/batch_round7.py`
- 更新 `src/literature_catalog/metadata.py`
- 更新 `src/literature_catalog/pilot.py`
- 更新 `tests/test_catalog.py`

### 配置

- 新增 `configs/pilots/P0006.json`
- 新增 `configs/pilots/P0007.json`
- 新增 `configs/pilots/P0011.json`
- 新增 `configs/pilots/P0016.json`

### 论文元数据

- 更新 `data/curated/papers.tsv` 中 `P0002 / P0006 / P0007 / P0011 / P0016` 的题名 / DOI / 状态说明

### 规范化表

- `data/interim/pilot/experiments.tsv`
- `data/interim/pilot/conditions.tsv`
- `data/interim/pilot/replicates.tsv`
- `data/interim/pilot/batches.tsv`
- `data/interim/pilot/samples_timepoints.tsv`
- `data/interim/pilot/archive_samples.tsv`
- `data/interim/pilot/accessions.tsv`
- `data/interim/pilot/accession_relations.tsv`
- `data/interim/pilot/files.tsv`
- `data/interim/pilot/evidence.tsv`
- `data/interim/pilot/unresolved_issues.tsv`
- `data/interim/pilot/literature_experiment_catalog.tsv`
- `data/interim/pilot/literature_experiment_catalog_files.tsv`
- `data/interim/pilot/literature_experiment_catalog_runs.tsv`

### 轮次产物

- `data/interim/pilot/round7_candidate_selection.tsv`
- `reports/per_paper/P0006_round7_light_expansion.md`
- `reports/per_paper/P0007_round7_light_expansion.md`
- `reports/per_paper/P0011_round7_light_expansion.md`
- `reports/per_paper/P0016_round7_light_expansion.md`
- `reports/batch_round7_summary.md`

## 全局计数更新

当前核心表计数：

| 表 | 行数 |
|---|---:|
| `accessions.tsv` | 2598 |
| `files.tsv` | 3567 |
| `literature_experiment_catalog.tsv` | 3567 |
| `literature_experiment_catalog_files.tsv` | 3567 |
| `literature_experiment_catalog_runs.tsv` | 1880 |
| `source_queries.tsv` | 32 |
| `evidence.tsv` | 38 |
| `unresolved_issues.tsv` | 29 |

## 未决问题与不能裁决的原因

本轮统一保守保留了以下未决问题：

- `own_data_status` 未因 accession 存在而自动判定为 `yes`
- 未从 sample title 或时间长度反推出同步化起点、释放时间或细胞周期阶段
- 未把检测靶点和扰动靶标混写
- 多 assay 混合提交仅保留 archive 明示的 `library_strategy`
- `P0016` 仅保存到 GEO + ENA 的轻量快照，未补抓额外大文件或大补充材料

对应问题已登记到：

- `data/interim/pilot/unresolved_issues.tsv`

## 验证命令与结果

已运行并通过：

```powershell
python -m src.literature_catalog.cli build --config configs\pilots\P0006.json
python -m src.literature_catalog.cli build --config configs\pilots\P0007.json
python -m src.literature_catalog.cli build --config configs\pilots\P0011.json
python -m src.literature_catalog.cli build --config configs\pilots\P0016.json
python -m src.literature_catalog.cli validate
python -m unittest discover -s tests
python -m py_compile src\literature_catalog\batch_round7.py src\literature_catalog\metadata.py src\literature_catalog\pilot.py src\literature_catalog\round6.py src\literature_catalog\cli.py src\literature_catalog\catalog.py tests\test_catalog.py
python scripts\research_flow.py check
```

结果：

- `validate`：通过，`ok=true`
- `unittest`：20 个测试全部通过
- `py_compile`：通过
- `research_flow.py check`：通过，`next_prompt_id: 8`

另已运行：

```powershell
git diff --check
```

结果：

- 无实际 diff 格式错误
- 仅提示若干文件的 LF/CRLF 将在后续 Git 触及时转换

## 明确未做的事

- 未下载 FASTQ / SRA / BAM / CRAM / RAW tar / 大型 supplement
- 未调用远程 LLM API
- 未生成 `prompt8.md`
- 未自动执行下一轮
- 未 commit
- 未 push

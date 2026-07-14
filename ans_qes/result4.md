# Result 4

## 对应 Prompt

`ans_qes/prompt4.md`

## 执行摘要

本轮按 prompt4 处理 `P0001`、`P0009`、`P0012` 三篇论文，完成项目级小批量核验和实验设计代表性抽取。未处理其他论文，未下载 FASTQ/SRA/BAM/CRAM/COOL/Hi-C 矩阵或大型补充材料，未生成 `prompt5.md`，未 commit，未 push。

P0008 的全量试点视图保持稳定：Run 视图 1,290 行，SHA-256 `217fd65db041203c295961fd3c61a0f5ce3b0b0b20cef9b68412d3f3bf81458a`；File 视图 2,580 行，SHA-256 `72fcdb880f6ed41199a6c29c328bfbd69423e26db2906e13537c4853e8bf2eb7`。

## 完成内容

完成 P0001、P0009、P0012 的论文级元数据核验、官方项目级归档入口登记、代表性同步化/采样阶段抽取、扰动设计记录、四层数据归属标注、未决问题登记、用户友好 round4 总表和逐篇报告。同步修复了 P0008 构建器的单篇覆盖问题，使其重建 P0008 时保留非 P0008 小批量记录。

## 本轮处理论文

| paper_id | PDF | DOI | PMID | 归档结论 |
| --- | --- | --- | --- | --- |
| P0001 | `文献/研究/2013-Science (New Yo-Organization of the mitot.pdf` | `10.1126/science.1236083` | `NR` | ArrayExpress `E-MTAB-1948`，ENA study `ERP004055` |
| P0009 | `文献/研究/2019-Nature-Chromatin structure dynamics durin.pdf` | `10.1038/s41586-019-1778-y` | `31776509` | GEO `GSE129997`，BioProject `PRJNA533460`，SRA `SRP192917` |
| P0012 | `文献/研究/2021-Nature Communic-CTCF and transcription in.pdf` | `10.1038/s41467-021-25418-5` | `34453048` | GEO `GSE168251`，SubSeries `GSE168168`/`GSE168176`，BioProject `PRJNA706679` |

## 官方轻量快照

保存了 3 个官方轻量元数据快照：

| query_id | 来源 | 本地快照 | 字节 | SHA-256 |
| --- | --- | --- | --- | --- |
| Q0009 | NCBI GEO `GSE129997` MINiML | `data/interim/pilot/source_metadata/GSE129997_quick.xml` | 28,844 | `7714f0a77afc5830c20ae1f62515104052648c17000ed165abdfcc1c4b1ae470` |
| Q0010 | NCBI GEO `GSE168251` MINiML | `data/interim/pilot/source_metadata/GSE168251_quick.xml` | 7,741 | `afd9a51dfaddd926aaba1c80edb9917e185485467312d498b622e0a9b213bf7f` |
| Q0011 | EMBL-EBI BioStudies `E-MTAB-1948` JSON | `data/interim/pilot/source_metadata/E-MTAB-1948_biostudies.json` | 25,790 | `8cfdadb24549d926f3b87b155dc87f8e7b793d4c5fa00c74e38fbf1a4d2b797d` |

## 实验设计摘要

P0001：人源 HeLa S3 / HFF-1 细胞，5C 和 Hi-C，比较 early G1、mid G1、thymidine-arrested early S、nocodazole-arrested prometaphase 等阶段。当前只完成项目级 `E-MTAB-1948` / `ERP004055` 核验，重复类型和 run 级编号未裁决。

P0009：小鼠 G1E-ER4 细胞，nocodazole-induced prometaphase arrest-release，in situ Hi-C、Capture-C、ChIP-seq。已记录 prometa、ana/telo、early G1、mid G1、late G1 五类代表性阶段；GEO `GSE129997` 官方快照显示 75 个样本，关联 `PRJNA533460` / `SRP192917`。

P0012：小鼠 G1E-ER4 CTCF-AID-mCherry 细胞，nocodazole arrest-release，in situ Hi-C 和 Pol II ChIP-seq。扰动包括 auxin-inducible degron 降解 CTCF，以及 triptolide 抑制 transcription initiation。已记录 0 h、30 min、60 min、120 min 和 120 min + triptolide 代表性条件；GEO `GSE168251` 官方页面列出 44 个样本和 8.7 GB RAW tar，本轮只保存轻量 MINiML。

## 数据归属

三篇论文的主数据集均按当前证据标为：

- `biological_sample_origin_status=study_generated`
- `library_origin_status=study_generated`
- `sequencing_generation_status=UNRESOLVED`
- `analysis_usage_status=primary_analysis`

`sequencing_generation_status` 保留 `UNRESOLVED`，因为本轮没有展开 run 级轻量 metadata，不能把项目级 Series/Study 直接等同于每个 Run 的生成来源。

## 涉及文件

### 新增/修改文件

新增：

- `configs/pilots/P0001.json`
- `configs/pilots/P0009.json`
- `configs/pilots/P0012.json`
- `data/interim/pilot/round4_experiment_design.tsv`
- `data/interim/pilot/source_metadata/E-MTAB-1948_biostudies.json`
- `data/interim/pilot/source_metadata/GSE129997_quick.xml`
- `data/interim/pilot/source_metadata/GSE168251_quick.xml`
- `reports/per_paper/P0001_pilot.md`
- `reports/per_paper/P0009_pilot.md`
- `reports/per_paper/P0012_pilot.md`
- `reports/batch_round4_summary.md`
- `ans_qes/result4.md`

修改：

- `README.md`
- `data/curated/papers.tsv`
- `data/interim/pilot/experiments.tsv`
- `data/interim/pilot/conditions.tsv`
- `data/interim/pilot/replicates.tsv`
- `data/interim/pilot/batches.tsv`
- `data/interim/pilot/samples_timepoints.tsv`
- `data/interim/pilot/perturbations.tsv`
- `data/interim/pilot/accessions.tsv`
- `data/interim/pilot/source_queries.tsv`
- `data/interim/pilot/evidence.tsv`
- `data/interim/pilot/semantic_review.tsv`
- `data/interim/pilot/unresolved_issues.tsv`
- `src/literature_catalog/catalog.py`
- `src/literature_catalog/pilot.py`
- `tests/test_catalog.py`

## 代码与 schema 变化

- `classify_accession()` 新增 `arrayexpress` 和 `encode_file` 识别，支持 `E-MTAB-1948` 与 `ENCFF...` 官方编号。
- `build_pilot_catalog()` 仍重建 P0008 试点，但会保留非 P0008 的小批量记录，避免后续 build/test 擦除 round4 数据。
- `assess_batch_readiness()` 改为只用 `paper_id=P0008` 的 semantic review 计算 P0008 schema readiness，避免新增论文审计行误改历史准入状态。
- 测试新增 round4 项目级 accession 分区检查。

## 命令记录

执行命令：

```powershell
python -m src.literature_catalog.cli --root . build
python -m src.literature_catalog.cli --root . validate
python -m unittest discover -s tests -v
python -m py_compile src\literature_catalog\catalog.py src\literature_catalog\cli.py src\literature_catalog\metadata.py src\literature_catalog\pilot.py
git diff --check
```

## 验证情况

结果：

- `validate`：0 errors / 0 warnings
- 单元测试：18 passed
- `py_compile`：通过
- `git diff --check`：通过，仅出现 Windows line-ending 提示，不是 whitespace error
- 29 个研究 PDF 与 `paper_files.tsv` 哈希一致，mismatch = 0
- P0008 `archive_samples.tsv` 仍为 60 行，SHA-256 `e5cdbd1afbce13d07d7fd9937623ff87804a2095623730efbf683ddfabbe704b`
- `round4_experiment_design.tsv` 为 12 行，SHA-256 `edd7ddd7d7fb347be12562f2b87f0824984f60d81c8e549f968cf602ddb65199`
- `reports/schema_v2_batch_readiness.json` 状态仍为 `ready_with_documented_gaps`

## 未解决问题

- P0001：PMID 未从当前可访问官方快照裁决；重复类型、补充材料表和 run 级编号未展开。
- P0009：GEO/SRA 项目级编号已确认，但 SRR/run 级 metadata 未展开；ana/telo、early/mid/late G1 的精确释放分钟数仍需补充方法核验。
- P0012：GEO SuperSeries 和 BioProject 已确认，但 8.7 GB RAW tar 未下载；rep 标签未升级为生物/技术重复；run/file 映射未展开。
- 当前 `archive_samples.tsv` 与 Run/File 视图仍是 P0008 试点结构；多论文 run-level 展开需要下一轮继续泛化。

## 风险与注意事项

- 第4轮只完成项目级和代表性实验设计核验，不能视为三篇论文的完整 SRR/ERR/DRR 数据集。
- P0001 的 PMID、P0009/P0012 的 run-level accession、重复类型和部分精确释放时间仍待后续人工/轻量元数据核验。
- P0012 的 GEO RAW 包为 8.7 GB，已按规则不下载；后续若需要 run/file 展开，应使用 SRA/ENA 轻量 metadata，而不是下载原始包。
- P0008 的 schema readiness 现在按 `paper_id=P0008` 计算；round4 的 readiness 以 `reports/batch_round4_summary.md` 和 `round4_experiment_design.tsv` 为准。

## 是否满足 prompt4

满足本轮“项目级小批量扩展”目标：3 篇论文的 DOI、官方归档入口、代表性实验设计、同步化/采样阶段、扰动、数据归属和未决问题均已结构化记录。未满足“所有 SRR/ENA 下载链接”这一最终项目目标，但 prompt4 明确允许本轮停在轻量项目级核验，不下载大型数据，不伪造 run 级信息。

## 下一步建议

建议下一轮不要继续新增论文，而是先为 P0009 或 P0012 任选 1 篇做 run-level 轻量展开：只下载 GEO MINiML / SRA Run Selector / ENA filereport TSV，生成 GSM/SRX/SRR/ERR 到样本阶段的映射，并把 Run/File 视图从 P0008-only 逐步泛化为按 `paper_id` 分区。

建议 commit 信息：`feat: add round4 project-level batch audit`

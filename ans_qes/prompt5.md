# Prompt 5

## 任务标题

P0009 完整 Run/File 级精查，并沉淀后续批量提速模板

## 任务背景

前 4 轮已经完成：

- 29 篇研究论文 PDF 的基础清单、稳定 `paper_id` 和 schema v2.1.0。
- `P0008 / GSE102740` 的完整试点，包括 Run/File 双视图、证据表、语义审计和批量准入检查。
- `P0001`、`P0009`、`P0012` 的项目级小批量核验。

第 4 轮中，`P0009` 已确认：

- 论文：`Chromatin structure dynamics during the mitosis-to-G1 phase transition`
- DOI：`10.1038/s41586-019-1778-y`
- PMID：`31776509`
- 物种/样本：`Mus musculus`，`G1E-ER4`
- 主要实验手段：`in situ Hi-C`、`Capture-C`、`ChIP-seq`
- 同步化/时间轴：`nocodazole-induced prometaphase arrest-release`，代表阶段包括 `prometa`、`ana/telo`、`early G1`、`mid G1`、`late G1`
- 公共归档：GEO `GSE129997`，BioProject `PRJNA533460`，SRA Study `SRP192917`
- 已保存轻量官方快照：`data/interim/pilot/source_metadata/GSE129997_quick.xml`

但仍有两个关键缺口：

1. `SRP192917` 的 SRR/Run/File 级 metadata 尚未展开。
2. P0009 的样本、assay、阶段、重复、扰动/靶点与 Run/File 之间尚未形成可核验映射。

本轮目标是把 `P0009` 从“项目级核验”推进到“第二个完整 Run/File 级 pilot”，同时把流程抽象成后续每轮 5–6 篇论文可复用的批量模板。要快，但不能靠猜；我们要的是一辆能跑的车，不是一张画得很像车的纸。

## 严格范围

本轮只处理 `P0009`。

允许：

- 查询或下载 `GSE129997` / `SRP192917` / `PRJNA533460` 的轻量官方 metadata，例如 GEO MINiML、SRA RunInfo、ENA Portal API/filereport TSV、BioProject/BioSample 页面或可保存的小型 XML/JSON/TSV。
- 保存轻量 metadata 快照到 `data/interim/pilot/source_metadata/`。
- 修改或新增 P0009 相关配置、规范化 TSV、报告、测试和构建逻辑。
- 为后续批量处理沉淀通用脚本/函数/配置模式，但必须保持 P0008 现有结果可重建，不能把 P0009 写死成新的特殊个案。

禁止：

- 不处理 P0009 之外的新论文。
- 不下载 FASTQ、BAM、CRAM、SRA 原始包、Hi-C 矩阵 tar 包、bigWig、bedGraph 或其它大型数据文件。
- 不把 GEO supplementary file 链接等同于已下载数据。
- 不手工拼接 ENA/NCBI 下载链接并标记为 verified；必须来自官方 metadata 字段。
- 不根据样本名或常识推断细胞周期阶段、释放分钟数、扰动靶标或自产数据状态。
- 不覆盖或破坏 P0008 的历史计数、哈希、Run/File 视图。
- 不生成 `prompt6.md`。
- 不 commit，不 push。

## 执行要求

### 1. 低上下文启动与基线记录

执行前先检查：

- `scripts/research_flow.py status`
- `scripts/research_flow.py check`
- `git status --short`

记录 P0008 现有关键计数作为回归基线：

- P0008 Run 视图行数
- P0008 File 视图行数
- `archive_samples.tsv` 中 P0008 行数
- 当前 `reports/schema_v2_batch_readiness.json` 状态与哈希（如存在）

只读取与本轮有关的文件片段，优先使用 `rg` 定位，不要整篇重读旧 result、长 TSV 或大型 XML。

### 2. 获取并保存 P0009 轻量官方 metadata

优先使用官方来源展开 `SRP192917`：

- NCBI SRA Run Selector / RunInfo，获取 `SRR`、`GSM`、`BioSample`、`SampleName`、`LibraryStrategy`、`LibraryLayout`、`Platform`、`Instrument`、`ReleaseDate`、`spots/bases` 等轻量字段。
- ENA Portal API 或 filereport，获取 `run_accession`、`experiment_accession`、`sample_accession`、`study_accession`、`secondary_study_accession`、`fastq_ftp`、`fastq_md5`、`fastq_bytes`、`submitted_ftp`、`submitted_md5`、`submitted_bytes`、`library_strategy`、`library_layout`、`instrument_platform`、`instrument_model` 等官方字段。
- GEO `GSE129997` / GSM 记录，用于样本标题、assay、阶段、原始样本名和补充文件关系。

保存要求：

- 所有新增轻量 metadata 快照放入 `data/interim/pilot/source_metadata/`。
- 在 `source_queries.tsv` 中登记查询来源、URL/参数、日期、状态码或成功/失败状态、文件大小、SHA-256、返回记录数。
- 如果网络/API 不可用，不能假装展开成功；必须把失败写入 `unresolved_issues.tsv`，并在 `result5.md` 说明可复现的失败命令或查询条件。

### 3. 建立 P0009 的 Run/File 级结构化映射

把 P0009 从项目级 accession 展开到至少以下层级：

- GEO Series：`GSE129997`
- SRA Study：`SRP192917`
- BioProject：`PRJNA533460`
- GSM / BioSample / SRA Experiment / SRR Run
- ENA/NCBI 官方提供的 FASTQ 或 submitted file 链接、MD5、文件大小（如 metadata 提供）

需要更新或新增的表包括但不限于：

- `data/interim/pilot/accessions.tsv`
- `data/interim/pilot/accession_relations.tsv`（如已有）
- `data/interim/pilot/archive_samples.tsv`
- `data/interim/pilot/files.tsv`（如当前项目已使用该表）
- P0009 对应的 Run/File 用户视图或宽表输出
- `data/interim/pilot/samples_timepoints.tsv`
- `data/interim/pilot/conditions.tsv`
- `data/interim/pilot/replicates.tsv`
- `data/interim/pilot/batches.tsv`
- `data/interim/pilot/perturbations.tsv`
- `data/interim/pilot/evidence.tsv`
- `data/interim/pilot/semantic_review.tsv`
- `data/interim/pilot/unresolved_issues.tsv`

如果现有构建流程只支持 P0008，需做最小泛化：

- 以 `paper_id` 分区处理 Run/File 级数据。
- P0008 与 P0009 的构建、验证、报告互不覆盖。
- 不允许用 P0009 的数据重写 P0008 的配置或硬编码路径。
- 如果通用化成本过高，本轮可先实现 `P0009` 的独立构建入口，但必须在报告中说明后续如何合并为批量流程。

### 4. 样本、时间点、阶段和扰动语义核验

对每个可解析样本/Run，尽量从论文、GEO/GSM、SRA/ENA metadata 中提取：

- 物种、样本名称、细胞系、基因型或突变状态。
- assay / library strategy，例如 Hi-C、Capture-C、ChIP-seq。
- 检测靶点：例如 ChIP-seq 抗体靶点、Capture-C 目标区域、Hi-C 的数据模态。
- 同步化技术、同步化起点、释放后采样时间、采样点代表的细胞周期阶段。
- 样本原始名称、GEO title、数据库 sample alias、BioSample、SRR 的对应关系。
- 是否本文自产数据、是否 primary analysis、是否 derived 或 reused。
- 扰动对象、扰动技术、直接靶标、预期效果和实际验证结果；无法确认则用 `NR` / `UNRESOLVED`，不要补脑。

特别注意：

- `prometa`、`ana/telo`、`early G1`、`mid G1`、`late G1` 可以作为作者/GEO 阶段标签保存。
- 释放分钟数只有在论文方法、补充材料或官方样本记录明确给出时才填写。
- `Noc0h`、`Noc25min`、`Noc1h`、`Noc2h`、`Noc4h` 等文件名线索必须登记证据等级；若只是文件名推断，不得标记为 `author_stated`。
- `CTCF`、`Rad21`、`Pol2`、Capture-C loci 等是检测/实验靶点还是扰动靶点，必须分清。

### 5. 生成 P0009 用户友好表和逐篇报告

至少生成：

- `reports/per_paper/P0009_run_file_pilot.md`
- 一个 P0009 Run/File 级用户友好 TSV，建议路径：`data/interim/pilot/P0009_run_file_catalog.tsv`

用户友好 TSV 每行原则上表示：

`论文 × 实验 × 样本/时间点 × 扰动条件 × assay/靶点 × GSM/BioSample/Experiment/Run × 文件`

至少包含这些列：

- `paper_id`
- `canonical_title`
- `doi`
- `archive_project`
- `study_accession`
- `geo_series`
- `geo_sample`
- `biosample`
- `experiment_accession`
- `run_accession`
- `file_url`
- `file_md5`
- `file_size`
- `file_source`
- `species`
- `sample_name_original`
- `sample_name_standardized`
- `assay`
- `library_strategy`
- `measurement_target`
- `synchronization_method`
- `synchronization_start`
- `sampling_time`
- `sampling_time_unit`
- `cell_cycle_phase`
- `phase_evidence_type`
- `perturbation_type`
- `perturbation_technology`
- `perturbation_target`
- `expected_effect`
- `observed_validation`
- `is_own_data`
- `data_generation_status`
- `evidence_ids`
- `verification_status`
- `unresolved_issue_ids`

报告需说明：

- P0009 的官方记录数：GSM 数、Run 数、Experiment 数、BioSample 数、文件链接数。
- 论文声明数量、GEO 数量、SRA/ENA 数量、最终表数量是否一致。
- 哪些字段已核验，哪些仍是 `NR`、`NOT_FOUND`、`UNRESOLVED`。
- 哪些逻辑可以复用到后续 5–6 篇一批的加速处理。

### 6. 自动化检查和回归

执行后至少运行：

- 项目现有 build/validate 命令，如果 README 或 CLI 中已有标准命令，以现有命令为准。
- `python -m unittest discover -s tests -v`
- `python -m py_compile` 针对本轮修改的 Python 文件。
- `git diff --check`

新增或更新测试，至少覆盖：

- P0008 历史 Run/File 计数不被 P0009 破坏。
- P0009 的 `GSE129997`、`PRJNA533460`、`SRP192917`、至少一个真实 SRR/ERR/DRR accession 的格式和命名空间识别。
- P0009 Run/File 级视图按 `paper_id` 分区，不与 P0008 发生笛卡尔积。
- P0009 的缺失值不能出现空字符串。
- 未经证据确认的阶段分钟数、扰动靶点或预期效果必须保持 `NR` / `UNRESOLVED`。

## 预期输出

本轮完成后必须生成或更新：

- `ans_qes/result5.md`
- `reports/per_paper/P0009_run_file_pilot.md`
- `data/interim/pilot/P0009_run_file_catalog.tsv`
- P0009 相关轻量 metadata 快照
- P0009 相关规范化 TSV 记录
- 必要的源码、配置、测试和 README/报告更新

`ans_qes/result5.md` 必须包含：

- 本轮实际查询和保存的官方 metadata 来源。
- P0009 的 Run/File 展开计数与对账结果。
- 新增/修改文件列表。
- 测试和检查结果。
- 仍未解决的问题。
- 对后续 `prompt6` 的建议：从单篇精查切换到每轮 5–6 篇的项目级/样本级批量处理，还是继续选择一篇复杂论文做 Run/File 级精查。

## 停止条件

遇到以下情况必须停止并在 `result5.md` 中说明：

- 官方 metadata 无法访问，且无法用已有快照可靠展开。
- 需要下载大型测序数据、矩阵包或受控访问文件。
- 样本名、GSM、BioSample、Experiment、Run 的映射出现无法裁决的冲突。
- 为支持 P0009 必须大幅重写 P0008 流程，且有破坏历史结果风险。
- 检查或测试失败且不能局部修复。

## 暂不执行

本文档只是第 5 轮任务提示词。生成后必须停止，等待用户审查。只有用户明确要求“根据 prompt5 执行”或等价指令后，才能执行本轮任务。

现在不得执行本轮任务，不得生成 `result5.md`，不得生成 `prompt6.md`，不得 commit，不得 push。

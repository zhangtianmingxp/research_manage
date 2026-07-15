# Prompt 7

## 任务标题

覆盖率优先小批次：选择并推进下一批 4 篇未完成研究论文的轻量归档与实验设计展开

## 任务背景

当前项目已经完成：

- P0008：Run/File 级完整试点；
- P0009：Run/File 级完整试点；
- P0012：扰动导向 Run/File 级展开；
- P0001：轻量 Run/File 级展开。

全局当前基线：

- `data/interim/pilot/literature_experiment_catalog.tsv`：2,983 行；
- `data/interim/pilot/literature_experiment_catalog_files.tsv`：2,983 行；
- `data/interim/pilot/literature_experiment_catalog_runs.tsv`：1,525 行；
- `python -m src.literature_catalog.cli validate` 已通过；
- `python -m unittest discover -s tests` 已通过。

但项目总体仍未完成：除 P0008、P0009、P0012、P0001 外，其余 24 篇规范研究论文尚未系统展开实验设计、归档编号、Run/File 和证据链。

本轮目标不是继续深挖单篇论文，而是切换到“覆盖率优先”的小批次推进：在保证不瞎编、不下载大文件、不破坏现有四个试点的前提下，选择 4 篇下一批论文，推进到至少项目/Study/Sample 级；如果官方轻量来源足够，则推进到 Run/File 级。

## 必须遵守的规则

执行前必须读取并遵守：

- `AGENTS.md`
- `.research_agent/AGENTS.md`
- `PROJECT_RULES.md` 中与数据、可追踪性、低上下文、Markdown、Git 和大文件相关的规则
- `project_plan.md` 中关于证据、缺失值、accession、扰动和同步化字段的要求
- `.research_agent/project_state.md`
- `ans_qes/result6.md`

硬性约束：

- 不调用远程 LLM API。
- 不自动生成 `prompt8.md`。
- 不自动 commit 或 push。
- 不下载 FASTQ、SRA、BAM、CRAM、bigWig、matrix、RAW tar、supplement 大包或其他大型数据文件。
- 只保存轻量官方元数据快照，例如 GEO MINiML、ENA Portal API TSV、NCBI RunInfo、BioStudies/ArrayExpress JSON/SDRF/IDF 等。
- 不处理综述论文。
- 不凭文件名、常识、相似论文或 accession 编号模式补写事实。
- 任何无法由论文、补充材料或官方数据库轻量记录确认的信息必须写为 `NR`、`NA`、`NOT_FOUND`、`UNRESOLVED` 或 `RESTRICTED`。
- 遇到数据库与论文声明冲突，必须进入 `unresolved_issues.tsv`，不得静默修正。
- 生成 `ans_qes/result7.md` 后停止，等待用户审查。

## 本轮范围

### 1. 选择 4 篇论文

从尚未进入 Run/File 或轻量 Run/File 展开的规范研究论文中选择 4 篇作为第 7 轮批次。

选择原则：

1. 优先选择已有 DOI、题名或 accession 线索较明确的论文；
2. 优先选择公开数据库入口较可能轻量解析的论文；
3. 优先覆盖不同 assay 或不同数据归档类型，避免只挑最容易的一类；
4. 不再选择 P0008、P0009、P0012、P0001；
5. 如果发现某篇论文需要大型补充材料才能继续，不强行处理，记录原因并替换为下一篇候选。

执行时需要先输出并保存一个候选选择依据表，例如：

- `data/interim/pilot/round7_candidate_selection.tsv`

建议字段：

- `candidate_rank`
- `paper_id`
- `canonical_title`
- `doi`
- `known_accession_candidates`
- `selection_reason`
- `risk_flags`
- `selected_for_round7`

### 2. 对每篇入选论文建立轻量配置

为 4 篇入选论文分别创建或更新：

- `configs/pilots/Pxxxx.json`

配置至少包含：

- `paper_id`
- `doi`
- 已知或候选的 `geo_series` / `bioproject` / `ena_study` / `arrayexpress` / `biostudies` / `sra_study`
- `source_metadata_dir`
- `source_queries_path`
- `round7_status`
- 明确的大文件下载限制，例如 `supplement_download_limit_bytes`

如果 accession 尚未确认，字段可写 `UNRESOLVED`，但必须在 `unresolved_issues.tsv` 记录已检查来源。

### 3. 抓取并保存轻量官方元数据快照

每篇论文按 accession 类型选择官方轻量来源。

允许来源：

- GEO family MINiML / quick XML；
- NCBI SRA RunInfo；
- ENA Portal API filereport；
- BioStudies / ArrayExpress API、IDF、SDRF；
- Crossref / PubMed 仅用于书目信息核验；
- 期刊页面仅用于定位数据可用性声明和补充材料入口。

所有新增快照保存到：

```text
data/interim/pilot/source_metadata/
```

所有查询记录写入或更新：

```text
data/interim/pilot/source_queries.tsv
```

必须记录：

- endpoint；
- query 参数；
- 查询时间；
- HTTP 状态或失败摘要；
- snapshot path；
- response bytes；
- SHA-256；
- returned rows；
- 是否分页完整。

如果网络请求失败、入口受限、数据库无记录或需要大文件，记录 `query_failed`、`restricted`、`not_found` 或 `size_limit_not_downloaded`，不要伪造结果。

### 4. 落表策略

对每篇入选论文，至少推进到以下程度之一：

#### A. Run/File 级

若官方轻量来源能明确获得 Run/File 映射，则更新：

- `experiments.tsv`
- `conditions.tsv`
- `replicates.tsv`
- `batches.tsv`
- `samples_timepoints.tsv`
- `archive_samples.tsv`
- `accessions.tsv`
- `accession_relations.tsv`
- `files.tsv`
- `literature_experiment_catalog.tsv`
- `literature_experiment_catalog_files.tsv`
- `literature_experiment_catalog_runs.tsv`
- `evidence.tsv`
- `unresolved_issues.tsv`

并生成每篇的用户友好表：

```text
data/interim/pilot/Pxxxx_light_catalog.tsv
```

#### B. 项目/Study/Sample 级

若 Run/File 无法可靠展开，但可确认项目、Study、Series、Sample 或 Experiment 层级，则至少更新：

- `experiments.tsv`
- `archive_samples.tsv` 或等价轻量 sample 表；
- `accessions.tsv`
- `accession_relations.tsv`
- `evidence.tsv`
- `unresolved_issues.tsv`

并在报告中写清楚为什么没有进入 Run/File 级。

### 5. 实验设计字段

每篇论文尽量提取但必须保守：

- 物种；
- 细胞系/组织/样本名称；
- assay 类型；
- 同步化技术；
- 同步化起点；
- 释放后或处理后采样点；
- 采样点代表的细胞周期阶段；
- 扰动对象；
- 扰动技术；
- 直接靶标；
- 预期效果；
- 观测/验证效果；
- 是否本文自产数据。

要求：

- 若官方数据库只给 sample alias，不足以证明同步化起点或扰动技术，则只保留 alias 原文，并将解析字段标为 `UNRESOLVED` 或 `NR`。
- 不得仅凭时间长度推断细胞周期阶段。
- “检测靶点”与“扰动靶标”必须分列，不得混写。
- “预期效果”与“观测结果”必须分列。

### 6. 每篇生成短报告

为每篇入选论文生成报告：

```text
reports/per_paper/Pxxxx_round7_light_expansion.md
```

报告至少包含：

- 论文题名、DOI、paper_id；
- 本轮确认的归档入口；
- 成功展开到什么层级；
- Run/File 数量或无法展开原因；
- 样本/assay/物种/同步化/扰动的已确认字段；
- 未决问题；
- 未下载的大文件或受限材料；
- 下一步人工核验建议。

### 7. 批次汇总

生成：

```text
reports/batch_round7_summary.md
```

内容至少包括：

- 4 篇论文的处理状态；
- 每篇 accession 层级；
- 每篇 Run/File 数量；
- 失败或未决入口；
- 对下一轮是否继续“覆盖率优先”给出建议。

## 工程实现要求

优先复用和扩展现有模块：

- `src/literature_catalog/cli.py`
- `src/literature_catalog/pilot.py`
- `src/literature_catalog/round6.py`
- `src/literature_catalog/catalog.py`
- `tests/test_catalog.py`

允许新增一个更通用的批次模块，例如：

```text
src/literature_catalog/batch_round7.py
```

但不要写一次性脚本作为核心流程。

如果新增 parser/helper，必须有最小测试覆盖。

## 验证要求

执行完成后必须运行：

```powershell
python -m src.literature_catalog.cli validate
python -m unittest discover -s tests
python -m py_compile src\literature_catalog\*.py
git diff --check
python scripts\research_flow.py check
```

如果某项失败：

- 优先修复本轮引入的问题；
- 若失败来自既有历史问题且本轮无法安全修复，在 `ans_qes/result7.md` 中明确说明；
- 不得在测试失败时声称任务完成。

## 必须生成或更新的文件

至少包括：

- `data/interim/pilot/round7_candidate_selection.tsv`
- 4 个 `configs/pilots/Pxxxx.json`
- 4 个 `reports/per_paper/Pxxxx_round7_light_expansion.md`
- `reports/batch_round7_summary.md`
- 必要的 `data/interim/pilot/source_metadata/*` 轻量快照
- 必要的规范 TSV 表
- 必要的代码和测试
- `ans_qes/result7.md`

## result7.md 必须记录

`ans_qes/result7.md` 必须用中文写明：

1. 本轮最终选择了哪 4 篇论文，为什么；
2. 每篇达到的层级：项目级、sample/experiment 级、Run 级或 File 级；
3. 每篇新增的 accession、Run、File 数量；
4. 每篇主要已确认实验设计字段；
5. 未决问题和不能裁决的原因；
6. 保存了哪些官方轻量快照；
7. 更新了哪些代码、表格、报告；
8. 所有验证命令及结果；
9. 明确说明没有下载大文件、没有生成 prompt8、没有 commit/push。

## 停止条件

生成 `ans_qes/result7.md` 后立即停止，等待用户审查。

不要自动生成 `prompt8.md`。
不要自动执行下一轮。
不要自动 commit 或 push。

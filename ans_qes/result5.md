# Result 5

## 执行范围

本轮按 `prompt5` 只处理 `P0009`，目标是把其从项目级核验推进到 Run/File 级，并确保现有 `P0008` 构建流程不会被破坏。

本轮没有处理新的论文，没有下载 FASTQ/SRA/矩阵等大型原始数据，没有生成 `prompt6.md`，没有 commit，也没有 push。

## 结果概述

`P0009` 已完成到 Run/File 级的轻量官方 metadata 展开：

- GEO：`GSE129997`
- BioProject：`PRJNA533460`
- SRA Study：`SRP192917`
- GEO Sample：`75`
- SRA/ENA Run：`120`
- FASTQ 链接：`195`

并新增了一个用户友好的逐文件目录：

- `data/interim/pilot/P0009_run_file_catalog.tsv`

同时保留了 `P0008` 的既有基线：

- `P0008` Run 视图：`1290`
- `P0008` File 视图：`2580`
- `reports/schema_v2_batch_readiness.json` 仍为 `ready_with_documented_gaps`

## 本轮实际使用并保存的官方 metadata

新增或确认的轻量快照如下：

| query_id | 来源 | 本地快照 | bytes | SHA-256 | returned_rows |
|---|---|---|---:|---|---:|
| `Q0012` | GEO family MINiML | `data/interim/pilot/source_metadata/GSE129997_family.xml(.tgz)` | `17652` (`tgz`) / `521456` (`xml`) | `bd7a89f3bc4a082db287c43d79f6e0bc1bb145af88120333089087bd00baa75c` (`tgz`) / `e426cbdffac9d5c561d62aa4e6428debdf5f9198392caaa8265a4cd6f530a38c` (`xml`) | `75` |
| `Q0013` | NCBI SRA RunInfo | `data/interim/pilot/source_metadata/SRP192917_runinfo.csv` | `53467` | `07a7003be5bbb01ed3d41ef99fa499cecaa34317c3d66028550d7de35529a6bb` | `120` |
| `Q0014` | ENA filereport | `data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv` | `37388` | `2f3723a3e3421f35b2a85ce22b4da5ec20daf1356edc3a78819f0637cccd6675` | `120` |

已有第4轮快照继续保留：

- `data/interim/pilot/source_metadata/GSE129997_quick.xml`

## 关键核验结论

1. `GSE129997_family.xml` 的 `Treatment-Protocol` 明确给出：
   - `prometa = 0 min`
   - `ana/telo = 25 min`
   - `early-G1 = 60 min`
   - `mid-G1 = 120 min`
   - `late-G1 = 240 min`

2. `asyn` 样本没有被强行放入 nocodazole release 时间轴，保留为 asynchronous comparator。

3. `SRP192917_runinfo.csv` 与 `SRP192917_ena_filereport.tsv` 的 Run 集合一致，均为 `120`。

4. `P0009` 的测序布局不是全双端：
   - paired-end run：`75`
   - single-end run：`45`

5. `LibraryStrategy=OTHER` 的官方记录中，`Capture-C` 与 `ChIP-seq-PolII` 通过 GEO 官方样本标题解释 assay 类型，并在 `semantic_review.tsv` 中留下了显式规则。

## 主要产物

新增：

- `ans_qes/result5.md`
- `data/interim/pilot/P0009_run_file_catalog.tsv`
- `data/interim/pilot/source_metadata/GSE129997_family.xml`
- `data/interim/pilot/source_metadata/GSE129997_family.xml.tgz`
- `data/interim/pilot/source_metadata/SRP192917_runinfo.csv`
- `data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv`
- `reports/per_paper/P0009_run_file_pilot.md`

更新：

- `README.md`
- `src/literature_catalog/pilot.py`
- `tests/test_catalog.py`
- `data/interim/pilot/accessions.tsv`
- `data/interim/pilot/accession_relations.tsv`
- `data/interim/pilot/archive_samples.tsv`
- `data/interim/pilot/batches.tsv`
- `data/interim/pilot/conditions.tsv`
- `data/interim/pilot/evidence.tsv`
- `data/interim/pilot/experiments.tsv`
- `data/interim/pilot/files.tsv`
- `data/interim/pilot/literature_experiment_catalog.tsv`
- `data/interim/pilot/literature_experiment_catalog_files.tsv`
- `data/interim/pilot/literature_experiment_catalog_runs.tsv`
- `data/interim/pilot/perturbations.tsv`
- `data/interim/pilot/replicates.tsv`
- `data/interim/pilot/samples_timepoints.tsv`
- `data/interim/pilot/semantic_review.tsv`
- `data/interim/pilot/source_queries.tsv`
- `data/interim/pilot/unresolved_issues.tsv`
- `reports/P0008_accession_reconciliation.md`

## 规范表与视图当前计数

验证时的行数如下：

- `archive_samples.tsv`: `135` (`P0008=60`, `P0009=75`)
- `accessions.tsv`: `2052`
- `accession_relations.tsv`: `2042`
- `files.tsv`: `2775`
- `literature_experiment_catalog.tsv`: `2775`
- `literature_experiment_catalog_runs.tsv`: `1410`
- `semantic_review.tsv`: `232`
- `evidence.tsv`: `24`
- `unresolved_issues.tsv`: `15`

其中：

- `P0009` Run 行数：`120`
- `P0009` File 行数：`195`
- `P0009` 用户友好目录 SHA-256：`c32f49467eac24805ff2547d0ac9303ed2e3e9a258d923023fb71a1a80def733`

## 检查与测试

已执行并通过：

- `python -m src.literature_catalog.cli --root . build --config configs/pilots/P0009.json`
- `python -m src.literature_catalog.cli --root . build`
- `python -m src.literature_catalog.cli --root . validate`
- `python -m unittest discover -s tests -v`
- `python -m py_compile src/literature_catalog/pilot.py src/literature_catalog/cli.py src/literature_catalog/catalog.py`
- `git diff --check`

测试结果：

- `20` 个单元/集成测试全部通过
- `validate` 为 `ok: true`

## 仍未解决的问题

本轮解决了 round4 的两个核心缺口：

- `UI-P0009-001`：阶段分钟数未裁决 -> `resolved`
- `UI-P0009-002`：run-level 未展开 -> `resolved`

仍然打开的缺口：

- `UI-P0009-003`：Capture-C 的 bait/locus 目标未在 raw metadata 中逐GSM显式声明，因此 `measurement_target=NR`
- `UI-P0009-004`：`commd3_mutant` 样本标题提示 mutant 背景，但工程技术、直接靶标细节和预期效果未在已保存官方 metadata 中显式给出

## 对 prompt6 的建议

建议下一轮不要再回到泛泛的项目级整理，而是二选一：

1. 继续做“第二类复杂样板”：
   选择 `P0012`，因为它包含显式扰动（CTCF / transcription / auxin / triptolide），能把 `perturbations` 这一块做得更完整。

2. 进入批量加速模式：
   把 `P0001`、`P0012` 以及另外 3-4 篇 accession 清楚的论文做成项目级/样本级一批，先把 29 篇覆盖率拉起来。

如果目标是尽快推进总表，我建议 `prompt6` 优先做第 2 条；如果目标是先把 schema 的扰动表达能力打磨好，我建议优先做 `P0012` 的 Run/File 级扩展。

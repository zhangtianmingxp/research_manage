# Prompt 6

## 任务标题

双轨提速：完成 P0012 的扰动导向 Run/File 扩展，并补齐 P0001 的轻量样本/归档展开

## 任务背景

前 5 轮之后，当前仓库已经形成两个明确层次：

1. 完整 Run/File 级样板：
   - `P0008`：1,290 个 Run，2,580 个 FASTQ 文件链接
   - `P0009`：75 个 GSM，120 个 Run，195 个 FASTQ 文件链接

2. 仍停在项目级的小批量论文：
   - `P0001`：`E-MTAB-1948` / `ERP004055`
   - `P0012`：`GSE168251` / `GSE168168` / `GSE168176` / `PRJNA706679`

第 5 轮已经证明：

- 现有 schema 能同时容纳多论文的 Run/File 级记录；
- 默认 `build` 不会再擦除非 `P0008` 的 run/file 结果；
- `P0009` 解决了同步化释放时间点与 single-end / paired-end 混合布局的问题。

现在最需要的不是继续单篇慢挖，而是把“覆盖率”和“扰动表达能力”一起往前推一步。

因此本轮采用双轨策略：

- 轨道 A：把 `P0012` 推进到 Run/File 级，重点验证显式扰动（CTCF、转录、auxin、triptolide）能否被规范化表达；
- 轨道 B：把 `P0001` 从项目级推进到样本/归档级或轻量 Run 级，尽可能补齐 accession 关系、样本阶段和官方下载入口。

本轮不追求再开 5–6 篇新论文，而是把已有 2 篇“半成品”向前推到足以支撑后续批量化的程度。目标是提速，不是把精度抵押出去。

## 严格范围

本轮只处理：

- `P0012`
- `P0001`

允许：

- 下载并保存轻量官方 metadata：GEO family MINiML、GEO quick XML、SRA RunInfo、ENA filereport TSV、BioStudies / ArrayExpress / NCBI / ENA 页面或可保存的小型 XML/JSON/TSV。
- 修改 `src/literature_catalog/`、`tests/`、`README.md`、`reports/`、`configs/pilots/`、`data/interim/pilot/` 中与 P0012/P0001 相关的文件。
- 为后续批量处理继续抽象可复用逻辑，但必须保持 `P0008` 和 `P0009` 现有结果可重建、可验证。

禁止：

- 不处理 `P0012`、`P0001` 之外的新论文。
- 不下载 FASTQ、BAM、CRAM、SRA、raw matrix、bigWig、bedGraph、图像包或其它大型文件。
- 不把补充结果文件名或网页文本当成已验证的 Run/File 关系，除非能回到官方元数据字段。
- 不为 `P0012` 的扰动技术、直接靶标、预期效果或观测结果做常识性补写。
- 不生成 `prompt7.md`。
- 不 commit，不 push。

## 任务目标

### 1. P0012：做成“扰动导向样板”

对 `P0012`：

- 从 `GSE168251`、`GSE168168`、`GSE168176`、`PRJNA706679` 出发，收集官方轻量 metadata。
- 尽可能展开到 GSM / BioSample / Experiment / Run / File 层级。
- 核验并结构化记录：
  - 物种、样本、细胞系；
  - 同步化方式、同步化起点、采样时间点、周期阶段；
  - 扰动对象、扰动类型、扰动技术、直接靶标；
  - `auxin`、`triptolide`、`CTCF` 等在各表中的角色边界：
    - 哪些是同步化/处理试剂；
    - 哪些是扰动技术；
    - 哪些是检测靶点；
    - 哪些是作者明确宣称的预期效果与观测结果。

目标不是把每个生物学结论讲完整，而是把“扰动设计能否被证据支撑地落表”这件事做扎实。

### 2. P0001：补齐轻量样本/归档层

对 `P0001`：

- 继续使用 `E-MTAB-1948` / `ERP004055` 相关官方入口。
- 若能轻量展开，则推进到样本/experiment/run 级；
- 若 Run/File 级信息在当前轻量来源下仍不充分，则至少完成：
  - project/study/sample/experiment 的层级关系；
  - 代表性阶段和样本命名；
  - assay 与物种的明确映射；
  - 官方页面和下载入口的可核验记录。

`P0001` 本轮允许停在“样本/experiment级已清楚、run/file级仍部分未决”的状态，但不能再只停在第 4 轮那种纯项目号登记层。

### 3. 提炼一套“批量前置准入模板”

在完成 `P0012` 和 `P0001` 后，要输出一个清晰结论：

- 哪些字段和构建逻辑已经足够支撑下一轮批量推进；
- 哪些问题仍然会阻碍一次处理 3 篇甚至更多论文；
- 后续应优先走“P0012/P0001 再深挖”还是“转入覆盖率优先批次”。

## 执行要求

### 1. 低上下文与基线

执行前先检查：

- `scripts/research_flow.py status`
- `scripts/research_flow.py check`
- `git status --short`

保留并核对这些基线：

- `P0008` Run/File 视图计数与 readiness 状态；
- `P0009` Run/File 视图计数与用户友好目录；
- 当前 `validate` 必须为通过状态。

### 2. 官方 metadata 获取与登记

对 `P0012` 与 `P0001`，保存所有新增轻量快照到：

- `data/interim/pilot/source_metadata/`

并在 `source_queries.tsv` 记录：

- `query_id`
- database / endpoint / parameters
- queried_at
- http_status
- response_sha256
- response_bytes
- returned_rows
- snapshot_path
- query_outcome

如果某官方端点在当前环境不可访问：

- 不能伪装成“未找到数据”；
- 必须在 `unresolved_issues.tsv` 和 `result6.md` 中记录失败来源与条件。

### 3. P0012 的规范化落表

对 `P0012` 至少更新：

- `experiments.tsv`
- `conditions.tsv`
- `replicates.tsv`
- `batches.tsv`
- `samples_timepoints.tsv`
- `archive_samples.tsv`
- `perturbations.tsv`
- `accessions.tsv`
- `accession_relations.tsv`
- `files.tsv`
- `semantic_review.tsv`
- `evidence.tsv`
- `unresolved_issues.tsv`

如能展开到 Run/File 级，还需同步进入：

- `literature_experiment_catalog.tsv`
- `literature_experiment_catalog_files.tsv`
- `literature_experiment_catalog_runs.tsv`

并新增一个用户友好表，建议路径：

- `data/interim/pilot/P0012_run_file_catalog.tsv`

### 4. P0001 的规范化推进

对 `P0001` 至少要把当前“项目级”推进到“样本/experiment级”或更高：

- 若官方记录足够，允许进入 Run/File 级；
- 若不够，也必须补齐样本/阶段/assay/归档关系和证据；
- 不能只重复第 4 轮结论。

可新增用户友好表，若达到合适粒度，建议：

- `data/interim/pilot/P0001_light_catalog.tsv`

### 5. 扰动语义必须分层

特别要求：

- 对 `P0012`，`auxin`、`triptolide`、`CTCF`、转录抑制相关样本不得混作同一层含义。
- `perturbation_type`、`technology`、`direct_target`、`expected_effect`、`observed_validation` 必须分列。
- 只要证据不足，就保留 `NR` / `UNRESOLVED`，不要把“看起来像”写成“已确认”。

### 6. 回归与验证

执行后至少运行：

- `python -m src.literature_catalog.cli --root . build`
- 如需要，再运行带具体 config 的 build
- `python -m src.literature_catalog.cli --root . validate`
- `python -m unittest discover -s tests -v`
- `python -m py_compile` 针对本轮改动的 Python 文件
- `git diff --check`

新增或更新测试，至少覆盖：

- `P0008` / `P0009` 结果不被破坏；
- `P0012` 若进入 Run/File 级，single-end / paired-end、扰动字段、缺失值状态可被验证；
- `P0001` 的 accession 层级与 evidence 引用正确；
- 新增用户友好表的关键行数、paper_id 分区、run/file 计数或缺失码规则。

## 预期输出

本轮执行后必须生成：

- `ans_qes/result6.md`

并根据实际完成度生成或更新：

- `reports/per_paper/P0012_run_file_pilot.md`
- `reports/per_paper/P0001_light_expansion.md` 或等价命名
- `data/interim/pilot/P0012_run_file_catalog.tsv`（若完成 Run/File 级）
- `data/interim/pilot/P0001_light_catalog.tsv`（若形成可用轻量目录）

## 停止条件

遇到以下情况必须停止并在 `result6.md` 说明：

- 官方 metadata 无法访问，且现有快照不足以可靠展开；
- `P0012` 的扰动/靶标层级需要读取大型补充材料才能裁决；
- `P0001` 的 run/sample 关系无法由官方轻量来源唯一映射；
- 为支持本轮必须大幅重写 `P0008/P0009` 稳定逻辑，且存在破坏风险；
- 构建、验证或测试失败且无法局部修复。

## 成功标准

本轮至少满足以下之一，才可视为成功：

1. `P0012` 完成 Run/File 级扩展，且 `P0001` 至少达到样本/experiment级清晰展开；
2. `P0012` 与 `P0001` 都达到“明显高于第4轮项目级”的结构化深度，并为下一轮批量推进给出清晰准入判断。

## 暂不执行

本文档只是第 6 轮任务提示词。生成后必须停止，等待用户审查。只有用户明确要求“根据 prompt6 执行”或等价指令后，才能执行本轮任务。

现在不得执行本轮任务，不得生成 `result6.md`，不得生成 `prompt7.md`，不得 commit，不得 push。

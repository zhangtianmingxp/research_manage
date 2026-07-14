# Prompt 4

## 任务标题

小批量扩展 3 篇有丝分裂相关论文，并验证 P0008 契约能否复用

## 本轮定位

前三轮已经完成论文文件盘点、P0008 / GSE102740 试点、schema v2.1.0、Run/File 双视图、语义审计表和批量准入检查。`ans_qes/result3.md` 的结论是 `ready_with_documented_gaps`：当前数据契约允许进入小批量处理，但每轮建议 1-3 篇，并且不得把 P0008 的未证实语义外推到其他论文。

本轮是第一次小批量扩展。目标不是一次性处理全部剩余论文，而是选择 3 篇与细胞周期/有丝分裂后染色质重构高度相关、PDF 体量相对可控的研究论文，验证现有 schema、代码、证据表和用户视图是否能自然承载多篇论文。

默认处理以下 3 篇：

| paper_id | file_id | 本地 PDF | 选择理由 |
| --- | --- | --- | --- |
| P0001 | F0001 | `文献/研究/2013-Science (New Yo-Organization of the mitot.pdf` | 标题指向 mitotic organization，体量小，适合作为批量扩展起点。 |
| P0009 | F0010 | `文献/研究/2019-Nature-Chromatin structure dynamics durin.pdf` | 直接涉及 mitosis-to-G1 phase transition，与项目核心同步化/采样时间轴高度相关。 |
| P0012 | F0013 | `文献/研究/2021-Nature Communic-CTCF and transcription in.pdf` | 直接涉及 after mitosis 的 chromatin re-configuration，适合检验时间轴和扰动字段。 |

如果执行时发现其中某篇不是研究性论文、无法从正文/官方元数据定位 DOI 或 Data Availability，或公共归档需要受控凭据/大文件/无法核验的材料，不要换题扩大范围；应保留该论文的 `partial` / `blocked` 状态并继续处理本轮内其余可安全处理的论文。

## 执行前必须遵守

执行前读取并遵守：

- `AGENTS.md`
- `.research_agent/AGENTS.md`
- `.research_agent/project_state.md`
- `.research_agent/progress.json`
- `PROJECT_RULES.md` 中与数据只读、可追溯、配置化、文档、测试、大文件、低上下文有关的章节
- `project_plan.md` 第四至第九节、第十一节、第十二节
- `ans_qes/result3.md`
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- `docs/schema_v2_batch_readiness.md`
- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `configs/pilots/P0008.json`

遵守低上下文原则：读取 TSV/CSV/JSON/XML/PDF 前，先用程序统计文件大小、行列数、列名、唯一键和目标记录；不要把大型表格、长 PDF 文本或完整日志读入对话。PDF 只定位标题、DOI、Data Availability、Methods、sample/experiment table、figure legend 和与同步化/扰动/采样时间点直接相关的段落。

## 核心目标

1. 对 P0001、P0009、P0012 完成论文级元数据核验：标题、作者、期刊、年份、DOI、PMID/PMCID、研究性论文状态、文件哈希、Data Availability 位置和证据。
2. 为每篇论文定位官方公共归档入口：EMBL-EBI/ENA project 或 study accession、GEO/SRA/BioProject 等互相关联编号、官方下载或元数据链接。只下载轻量官方元数据，不下载 FASTQ/SRA/BAM/CRAM/Hi-C 矩阵等大型数据。
3. 在 schema v2.1.0 契约下，抽取每篇论文可证实的实验设计：物种、样本名称、实验手段、靶点、同步化技术、同步化起点、同步化后的采样点、作者给出的细胞周期阶段、扰动对象、扰动技术、靶标、预期效果、本文自产/复用数据分层归属。
4. 对无法证实或多义的字段，保留原始值、证据边界和 `UNRESOLVED` / `partial` / `blocked` 状态；禁止用标题、文件名、常识或相似论文强行补齐。
5. 将 P0008 的单论文流程泛化到多论文小批量：配置、构建、验证、报告都应能按 `paper_id` 扩展，不得把 P0008 路径硬编码复制三份。
6. 生成本轮小批量报告，说明 3 篇论文各自完成度、可核验数据量、未决问题、是否适合进入后续全量批处理。

## 必须完成

### 1. 批量基线和安全边界

- 记录执行前 `papers.tsv`、`paper_files.tsv`、P0008 既有规范表、Run/File 视图和报告的行数、哈希或关键计数。
- 证明本轮没有修改、移动、重命名或复制 `文献/研究/` 和 `文献/综述/` 下的原始 PDF。
- 不覆盖 P0008 已完成的审计结论；如公共表需要追加新论文记录，必须证明 P0008 的关键计数和用户视图仍稳定。
- 保留 prompt1/result1、prompt2/result2、prompt3/result3 文件内容，不得覆盖旧轮次结果。

### 2. 论文级元数据核验

对 P0001、P0009、P0012 分别完成：

- 从 PDF 正文首页、出版社页面元数据、PubMed/PMC/Crossref 或官方数据库轻量元数据中核验标题、作者、期刊、年份、DOI、PMID/PMCID。
- 更新 `data/curated/papers.tsv` 中对应行，将 `bibliographic_status` 从 `unverified` 升级为合适状态；无法核验的字段填 `NR` 或受控缺失值，并写入 `unresolved_issues.tsv`。
- 在 `evidence.tsv` 或等价证据表中记录证据来源、访问日期、URL、位置、最短必要摘录或定位信息；不得长篇复制受版权保护文本。
- 如果 DOI/标题与文件名或 PDF 元数据冲突，保留冲突双方和来源，不静默覆盖。

### 3. 官方归档与 EMBL/ENA 链接

对每篇论文：

- 优先从论文 Data Availability、Methods、supplementary table、GEO/SRA/ENA/ArrayExpress 官方记录定位归档项目。
- 记录 EMBL-EBI/ENA study/project accession、BioProject、GEO Series、SRA Study、ArrayExpress 等互相关联编号。
- 保存官方元数据查询结果或轻量表格到 `data/interim/.../source_metadata/`，并记录 URL、访问日期、HTTP 状态、文件大小、SHA-256。
- 如果存在 ENA read/run metadata，可下载 TSV 元数据；禁止下载 FASTQ/SRA/BAM/CRAM/COOL/矩阵等大型数据。
- 如果官方补充材料单文件超过 20 MB、需要登录/凭据、出现版权或访问限制，只记录 `size_limit_not_downloaded`、`credential_required`、`query_failed` 等状态，不绕过限制。
- 对下载链接字段，优先保存 EMBL/ENA 官方 metadata/download URL；如果只有 NCBI/GEO 链接，也要标明来源类型和未找到 ENA 链接的证据边界。

### 4. 实验设计抽取

每篇论文至少建立可核验的实验级/样本级草表或正式表记录，字段应覆盖项目计划中的核心字段：

- `paper_id`
- `experiment_id`
- `sample_id` 或官方 sample/accession
- `species`
- `sample_name`
- `assay`
- `target`
- `synchronization_method`
- `synchronization_start`
- `time_after_release`
- `cell_cycle_stage`
- `stage_evidence_type`
- `perturbation_object`
- `perturbation_method`
- `perturbation_target`
- `expected_effect`
- `biological_sample_origin_status`
- `library_origin_status`
- `sequencing_generation_status`
- `analysis_usage_status`
- `archive_project_accession`
- `run_accession` / `file_accession`（若轻量元数据可安全获得）
- `evidence_ids`
- `unresolved_issue_ids`

规则：

- 采样点对应细胞周期阶段只能来自作者明示、标志物支持或作者给出的明确映射；不得仅凭时间长度推断。
- 药物、auxin、degron、RNAi、CRISPR、基因敲除、蛋白降解、同步化释放等必须区分“扰动对象”“扰动技术”“靶标”“预期效果”。
- 若论文复用既有数据、重新分析公共数据或混合自产与复用数据，必须使用四层数据归属字段，不得只写一个“自产/复用”。
- 如果一篇论文没有相关同步化或扰动实验，也要明确写 `not_applicable`，并说明证据。

### 5. 多论文配置和构建

根据现有代码结构，新增或扩展配置，使 P0001、P0009、P0012 能以与 P0008 一致的方式进入构建流程。建议但不强制的路径：

- `configs/pilots/P0001.json`
- `configs/pilots/P0009.json`
- `configs/pilots/P0012.json`
- `reports/per_paper/P0001_pilot.md`
- `reports/per_paper/P0009_pilot.md`
- `reports/per_paper/P0012_pilot.md`
- `reports/batch_round4_summary.md`

如当前 CLI 只支持 P0008，应做最小泛化：允许按 `paper_id` 或配置列表构建本轮 3 篇，不要把每篇论文写成独立临时脚本。若泛化会造成大范围重构，应先实现清晰的配置入口和测试覆盖，避免破坏 P0008。

### 6. 用户友好输出

本轮应生成或更新可供用户核验的汇总结果：

- 每篇论文一份 per-paper 报告，列出数据来源、归档编号、实验设计、同步化/扰动/时间点、未决问题和人工核验建议。
- 一个本轮小批量总表或视图，能按论文、物种、样本、assay、同步化技术、周期阶段、扰动技术、靶标、自产/复用和 accession 筛选。
- README 或相关文档继续明确项目未完成：当前只完成 P0008 和本轮 3 篇小批量，不代表 29 篇研究论文全部完成。

## 禁止事项

- 不处理 P0001、P0009、P0012 之外的新论文；不得因为某篇受阻就自行替换论文。
- 不下载 FASTQ、SRA、BAM/CRAM、COOL、Hi-C 矩阵、原始测序包或大型补充 PDF。
- 不调用远程 LLM API。
- 不把搜索结果摘要、综述、博客、聚合站点或非官方页面作为最终事实证据。
- 不用文件名、sample title、缩写、日期、相似论文或常识作为最终语义裁决的唯一证据。
- 不删除 P0008 未解决问题，不为了表格好看而填充未知值。
- 不生成 `prompt5.md`。
- 不 commit，不 push。

## 验收标准

执行结束前至少满足：

1. P0001、P0009、P0012 的论文级元数据有证据记录；无法核验项进入 unresolved issue。
2. 每篇论文的 Data Availability / 官方归档状态有结论：`verified`、`partial`、`not_found`、`blocked` 或受控等价值。
3. 找到的 ENA/EMBL、GEO、SRA、BioProject、ArrayExpress 等编号均有来源和访问日期；没有找到时记录已查来源。
4. 至少对每篇论文建立一个实验设计层面的可核验记录；如果论文不适用同步化或扰动字段，显式标为 `not_applicable`。
5. 所有新增样本、实验、accession、source query、evidence、unresolved issue 均带 `paper_id`，不会与 P0008 混淆。
6. P0008 的 Run 视图 1,290 行、File 视图 2,580 行及第三轮关键哈希/计数未被无意破坏；若因代码泛化导致输出路径变化，必须解释兼容策略。
7. 构建和验证命令可重复运行，连续两次输出顺序和关键哈希稳定，或明确说明哪些轻量在线元数据会随访问日期变化。
8. 自动化测试不访问实时网络；涉及网络解析的逻辑使用 fixture 或已保存轻量元数据。
9. `python -m src.literature_catalog.cli --root . validate` 最终 0 error；若有 warning，必须解释是否为预期的 unresolved/partial。
10. 至少运行项目现有单元测试、`py_compile` 或等价静态检查、PDF 哈希核验、`git diff --check`。
11. 新增/修改文档说明本轮只完成小批量扩展，仍是未完成项目。
12. 生成 `ans_qes/result4.md`，并记录命令、输出文件、关键统计、失败/跳过项、风险、未解决问题和下一步建议。

## `result4.md` 必须记录

- 对应 prompt：`ans_qes/prompt4.md`
- 本轮实际处理的 paper_id 和文件路径
- 每篇论文的元数据核验结果、DOI、PMID/PMCID、Data Availability 定位
- 每篇论文的 EMBL/ENA/GEO/SRA/BioProject/ArrayExpress 编号和官方链接
- 每篇论文实验设计抽取摘要：物种、样本、assay、同步化、起点、采样点、周期阶段、扰动对象、扰动技术、靶标、预期效果
- 自产/复用数据四层归属统计
- 新增/修改文件清单
- 运行命令和验证结果
- P0008 兼容性检查结果
- 未解决问题、受阻原因、人工核验建议
- 是否满足 `PROJECT_RULES.md` 和本 prompt 验收标准
- commit message 建议，但不得执行 commit
- 不生成下一轮 prompt

## 停止条件

遇到以下任一情况，保留已完成的安全结果，写入 `result4.md` 后停止，不得扩大范围：

- 需要下载大型测序数据或超过 20 MB 的补充材料才能继续。
- 需要登录、凭据、绕过访问限制或处理受控数据。
- 论文级 DOI/Data Availability 与官方数据库记录发生无法裁决的冲突。
- 当前 schema 无法表达某类关键实验设计，且最小兼容扩展不明显。
- 多论文构建会破坏 P0008 已验证视图或历史证据。
- 测试失败且不能通过局部、明确的修复解决。
- 继续需要处理本轮 3 篇之外的论文。

证据不足时保留 `UNRESOLVED` 是合格结果；伪造、外推、静默合并或删除问题才是失败。

## 暂不执行

本文档只是第 4 轮任务提示词。生成后必须停止，等待用户审查。只有用户明确要求“根据 prompt4 执行”或等价指令后，才能执行本轮任务。现在不得修改科研数据、不得生成 `result4.md`、不得生成 `prompt5.md`、不得 commit、不得 push。

# Result 3

## 对应 Prompt

`ans_qes/prompt3.md`。

## 执行摘要

本轮仅处理P0008，没有展开其余27篇论文，没有下载测序数据或大型补充材料。schema升级为2.1.0，批量准入结论为`ready_with_documented_gaps`：已知缺口均可表达、定位和统计，但仍须人工复核，建议后续每轮1–3篇。

## 完成内容

完成正式来源记录、高风险语义审计、四层数据归属、历史占位迁移、Run/File双视图、schema准入检查、离线测试及配套文档报告。

## 正式材料与证据边界

- Science正式补充材料URL：`https://www.science.org/doi/suppl/10.1126/science.aao6135/suppl_file/aao6135_gibcus_sm.pdf`；2026-07-13访问返回HTTP 403，记为`Q0006=query_failed`，没有把失败解释成不存在。
- NCBI PMC官方页面列出的主补充PDF大小为107.5 MB，超过配置的20 MB阈值，记为`Q0007=size_limit_not_downloaded`。未下载，因此本地路径和SHA-256均为`NA`。PMC附件入口还出现官方访问校验页，未绕过。
- 保存的官方PMC正文XML：`data/interim/pilot/source_metadata/PMC5924687_efetch.xml`，157,757 bytes，SHA-256 `968fa4fbb8c4d0d47de4fa883a97c3ceda7eeab4a4bfbe257b046daf50f56713`。实际只读取与duplicate time course、nocodazole时序、HeLa既往数据/更深测序和Data Availability相关的Methods/Results段落；没有读取未下载补充PDF的页或表。
- 新增证据`E-P0008-013`和`E-P0008-014`，分别记录正文语义边界和补充材料访问/大小限制。

## 高风险语义审计

`semantic_review.tsv`共223行：replicate 60、batch 60、高风险condition 18、HeLa样本分层字段8、HeLa Run 76、历史迁移1。

- R1/R2：58条有标签记录均为`unresolved`，2条无标签为`not_applicable`；0条verified、0条partially verified。正文只能证明time course均重复执行，不能证明R1/R2是生物重复还是技术重复。
- batch：51个日期alias均为`unresolved`候选，9个无日期为`not_applicable`；未升级为实验日期、建库批次或测序批次。
- 条件：18条`G2p/G2n/sG2/PMphase/30m`相关记录逐条保留原名。其中8条含`30m`的记录为`partially_verified`，仅表示正文提供了nocodazole/晚期采样总体背景；没有证据把具体GSM无歧义映射为有药或无药。其余10条缩写记录为`unresolved`，未展开`p/n`含义。

## 分层数据归属

`own_data_status`保留为兼容摘要，新模型拆为`biological_sample_origin_status`、`library_origin_status`、`sequencing_generation_status`、`analysis_usage_status`和`origin_evidence_ids`。

- 2个HeLa GSM：生物样本为`reused_from_prior_study`，分析用途为`reanalyzed_prior_data`；文库来源为`UNRESOLVED`，样本层测序来源为`mixed_or_additional_unassigned`。
- HeLa对应76个Run：逐Run的测序生成状态均为`UNRESOLVED`，未依据alias或accession顺序猜测哪些属于追加测序。
- 58个鸡源GSM：生物样本/文库为`study_generated`，分析为`primary_analysis`；具体Run的测序生成仍为`UNRESOLVED`。判定仅应用于本文time course和官方提交证据范围，不从Series归属无限外推。

## 历史占位迁移

`AC-P0008-004`已从活跃`accessions`移除，活跃accession由1,474降为1,473，不影响1,290个真实Run。失败查询迁入`source_queries.Q0008`，以`legacy_record_id=AC-P0008-004`保留原ID；`E-P0008-007`改指Q0008。旧ID未复用，关系表和用户视图均不包含该占位。

## Run/File视图与对账

- Run视图：1,290行、1,290个唯一Run、每行2个有序read字段，SHA-256 `217fd65db041203c295961fd3c61a0f5ce3b0b0b20cef9b68412d3f3bf81458a`。
- File视图：2,580行、2,580个唯一File、每Run恰好2行，SHA-256 `72fcdb880f6ed41199a6c29c328bfbd69423e26db2906e13537c4853e8bf2eb7`。
- 两个视图的Run集合均等于NCBI/ENA的1,290个Run；URL、大小、MD5覆盖率100%，没有笛卡尔积。连续离线构建两次哈希一致。
- 兼容路径`literature_experiment_catalog.tsv`继续表示File粒度，内容哈希与新File视图相同。

## Schema准入机器依据

`reports/schema_v2_batch_readiness.json`由构建代码生成，检查replicate/batch审计覆盖、76个HeLa Run审计、双视图行数和历史占位排除。最终目录为19张表，`validate`结果0错误、0警告。`UNRESOLVED`值不阻塞准入，因为其证据边界、规则和人工复核状态均已保存。

## 涉及文件

- 配置：`configs/catalog_schema.json`、`configs/controlled_vocab.json`、`configs/pilots/P0008.json`
- 代码：`src/literature_catalog/metadata.py`、`cli.py`、`pilot.py`、`catalog.py`
- 数据：P0008的`archive_samples.tsv`、`accessions.tsv`、`source_queries.tsv`、`evidence.tsv`、`unresolved_issues.tsv`、`semantic_review.tsv`及三张用户视图
- 文档/报告：`README.md`、`docs/data_dictionary.md`、`docs/verification_protocol.md`、`docs/schema_v2_batch_readiness.md`、`reports/per_paper/P0008_semantic_audit.md`、准入JSON和accession对账报告
- 测试：`tests/test_catalog.py`、`tests/fixtures/pmc_evidence_small.xml`

## 命令记录

执行过`fetch-evidence`（仅轻量官方元数据/正文XML）、`build`、`validate`、`unittest`、`py_compile`、PDF哈希核对和`git diff --check`。

## 验证情况

最终17项离线测试全部通过，失败0、跳过0；目录校验0错误、0警告。29个研究PDF与`paper_files.tsv`哈希全部一致；prompt1/result1/prompt2/result2哈希与执行前一致。未创建`prompt4.md`，未commit、未push。

本轮满足`PROJECT_RULES.md`的数据只读、证据可追踪、配置化、确定性构建、文档、离线测试和大文件限制。原论文目录未修改。

## 风险与注意事项

- R1/R2类型、日期alias的真实批次层级、`G2p/G2n`缩写及逐GSM nocodazole状态仍需作者补充表或人工材料复核。
- HeLa文库来源及76个Run的新旧测序归属仍不能裁决。
- Science主补充PDF因HTTP 403且大小超过阈值未读取；因此不能声称补充材料已完整核验。
- 所有semantic review仍为`machine_extracted_pending_human_review`，需要用户/领域专家签核。

## 建议

建议先人工抽查P0008语义审计和两张用户视图；若接受当前契约，再以每轮1–3篇推进其余论文。建议commit信息：`feat: audit P0008 provenance and add run/file catalog views`。本轮未生成下一轮prompt。

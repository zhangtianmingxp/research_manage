# 文献实验目录数据字典

## 通用约定

- 机器可读 schema：`configs/catalog_schema.json`；受控词表：`configs/controlled_vocab.json`。
- TSV 统一使用 UTF-8、制表符分隔和单行表头。
- 除明确的数值字段外，字段类型均为字符串。`file_size_bytes`、`publication_year`、`taxonomy_id`、重复数为整数；时间在 `sampling_time` 中保存原始数值或范围，并由 `sampling_time_unit` 给出单位。
- schema 的 `required` 表示字段不得为空，但可以在语义允许时使用受控缺失码。主键和外键不得使用缺失码。
- 多值字段（如 `evidence_ids`）使用 `|` 分隔。
- 真实记录必须引用证据；文档中的例子仅为格式示意，不得复制进结果。

## 1. `paper_files`

每个本地研究 PDF 一行，29 个文件必须全部出现。文件名和 PDF metadata 仅作为线索，不自动升级为规范书目信息。

| 字段 | 含义与约束 |
|---|---|
| `file_id` | 文件稳定主键，如 `F0001`；已有 ID 在重跑时保留。 |
| `paper_id` | 指向 `papers.paper_id`；完全相同的重复文件共享该值。 |
| `relative_path` | 相对仓库根目录的 POSIX 风格路径；必须唯一。 |
| `filename` | 原始文件名，不做重命名。 |
| `file_size_bytes` | 文件字节数，整数。 |
| `sha256` | PDF 内容 SHA-256；用于只读核验和精确重复检测。 |
| `pdf_metadata_title` | PDF metadata 的 title；未核验时不能当正式题名。 |
| `year_hint` | 从文件名得到的年份线索，非正式年份证据。 |
| `journal_hint` | 从文件名得到的期刊线索。 |
| `title_hint` | 从文件名得到的截断题名线索。 |
| `document_role` | 本地文件角色，受 `document_role` 词表约束。 |
| `version_relation` | `unique`、`exact_duplicate`、`suspected_duplicate` 等。 |
| `duplicate_group_id` | 重复/版本组 ID；不适用为 `NA`。 |
| `is_canonical_file` | 同一 `paper_id` 下是否为规范文件，`yes/no`。 |
| `metadata_evidence` | metadata 当前依据及核验等级。 |
| `extraction_status` | 文件处理状态。 |
| `notes` | 文件级限制、冲突或人工备注。 |

## 2. `papers`

每篇规范论文一行；文件级完全重复不会产生两个规范论文记录。

| 字段 | 含义与约束 |
|---|---|
| `paper_id` | 论文主键，如 `P0001`。 |
| `canonical_file_id` | 指向规范本地 PDF。 |
| `canonical_title` | 经正文或权威书目源核验的完整题名。 |
| `authors` | 规范作者表示；可用“第一作者 et al.”，完整信息留在证据中。 |
| `journal` | 正式期刊名。 |
| `publication_year` | 正式发表年份，整数或缺失码。 |
| `doi` | 小写/原始 DOI 均可，但同一项目保持统一。 |
| `pmid` | PubMed ID；无则用缺失码。 |
| `document_type` | `research_article` 等正式文献类型。 |
| `duplicate_group_id` | 与文件重复/版本组的关系。 |
| `bibliographic_status` | `verified`、`pilot_verified`、`unverified` 或 `conflicted`。 |
| `data_availability_locator` | Data Availability 在 PDF 中的页码/章节。 |
| `notes` | 论文级范围和问题。 |

## 3. `experiments`

每行表示一个可区分的实验设计或实验组。检测靶点与扰动靶标不得混用。

| 字段 | 含义与约束 |
|---|---|
| `experiment_id` | 实验主键。 |
| `paper_id` | 所属论文外键。 |
| `experiment_label_original` | 作者原始实验/组名。 |
| `biological_question` | 实验要回答的生物学问题。 |
| `own_data_status` | `yes`、`no_reused`、`derived_from_own`、`unclear`。 |
| `own_data_evidence` | 自产/复用判定的简要依据。 |
| `assay_type` | 统一 assay 名，如 `Hi-C`。 |
| `assay_detail` | 建库、检测或分辨率细节。 |
| `measurement_object` | 实际测量的数据对象。 |
| `detection_target` | 抗体、拉下或检测靶点；不等同于扰动靶标。 |
| `experimental_group` | 实验组。 |
| `control_group` | 对照组。 |
| `biological_replicates` | 生物重复，整数、原文范围或缺失码。 |
| `technical_replicates` | 技术重复。 |
| `reference_genome` | 参考基因组/注释版本。 |
| `evidence_ids` | 支撑本记录的 `evidence_id` 列表。 |
| `notes` | 设计限制和未建模信息。 |

## 4. `conditions`、`replicates` 与 `batches`

- `conditions`显式保存作者原始条件标签、基因型/构建、同步化、处理和周期阶段。证据不足时，每个GSM保持独立condition，禁止按名称相似度合并。
- `replicates`保存作者原始重复标签、重复类型和编号。P0008中的R1/R2尚未裁决，`replicate_type=UNRESOLVED`。
- `batches`保存作者批次标签、日期候选、建库批次与测序平台。日期型alias目前只标为`candidate`。

## 5. `samples_timepoints`

每行表示实验中的一个样本/时间点组合，保留原始名称和标准化解释。

| 字段 | 含义与约束 |
|---|---|
| `sample_timepoint_id` | 样本时间点主键。 |
| `experiment_id` | 所属实验外键。 |
| `species_scientific` | 物种学名。 |
| `species_common` | 常用名。 |
| `taxonomy_id` | NCBI Taxonomy ID；未核验时用缺失码。 |
| `cell_line_or_tissue` | 细胞系、原代样本或组织。 |
| `sample_name_original` | 论文/数据库原始样本名。 |
| `sample_name_standardized` | 便于比较的标准化名称。 |
| `genotype_or_construct` | 基因型、转基因或工程化构建。 |
| `synchronization_method` | 同步化方法。 |
| `synchronization_reagent` | 同步化试剂或操作。 |
| `synchronization_dose` | 剂量/浓度；未报告用 `NR`。 |
| `synchronization_duration` | 同步处理时长。 |
| `arrest_point` | 阻断的细胞周期位置。 |
| `time_zero_definition` | 时间零点的精确定义。 |
| `sampling_time` | 相对时间零点的数值或范围。 |
| `sampling_time_unit` | `min`、`h` 等单位。 |
| `cell_cycle_phase` | 作者支持的细胞周期阶段。 |
| `phase_evidence_type` | `author_stated`、`marker_supported`、`explicitly_inferred`、`unknown`。 |
| `phase_evidence_rule` | 阶段证据或明确推导规则。 |
| `pooled_status` | 是否混池；`yes/no/NR/NA`。 |
| `evidence_ids` | 字段级证据引用。 |
| `notes` | 晚期样本药物、配对关系等备注。 |

v2新增 `condition_id`、`replicate_id`、`batch_id`、`gsm_accession` 和 `archive_sample_id` 外键。GEO标题中的分钟数可以机械保存，但不得据此推断周期阶段。

## 6. `archive_samples`

每个GSM一行，保存GEO原始标题、物种、source、platform、官方Characteristics、BioSample/SRS/SRX关系、Run数、自产状态及处置状态。`mapped`表示官方关系已完整连接，不表示所有生物学语义均已人工裁决。

## 7. `perturbations`

一个组合扰动可共享 `combination_id`，但每个直接靶标单独一行。

| 字段 | 含义与约束 |
|---|---|
| `perturbation_id` | 扰动主键。 |
| `experiment_id` | 所属实验外键。 |
| `combination_id` | 组合扰动 ID；单一扰动为 `NA`。 |
| `perturbed_object` | 被扰动的细胞、蛋白、基因或结构。 |
| `perturbation_type` | 降解、敲除、抑制、洗脱等。 |
| `technology` | CRISPR、mAID、RNAi 等技术系统。 |
| `direct_target` | 直接靶标。 |
| `construct_or_reagent` | 构建体、药物或试剂。 |
| `dose` | 剂量/浓度。 |
| `duration` | 扰动持续时间。 |
| `timing_relative_to_synchronization` | 相对同步化/释放的时序。 |
| `control` | 对照条件。 |
| `expected_effect` | 设计预期；不得混入事后观察。 |
| `expected_effect_basis` | 预期来自作者声明还是明确设计目标。 |
| `observed_validation` | 作者实际验证的效果。 |
| `evidence_ids` | 证据引用。 |
| `notes` | 扰动限制或组合关系。 |

## 8. `accessions`、`accession_relations` 与 `files`

每行一个归档实体。格式验证和在线存在性验证必须分开。

| 字段 | 含义与约束 |
|---|---|
| `accession_record_id` | 归档记录主键。 |
| `experiment_id` | 所属实验外键。 |
| `sample_timepoint_id` | 样本时间点外键；Series/Project 级为 `NA`。 |
| `namespace` | GEO、SRA、BioProject、ENA 等命名空间。 |
| `entity_type` | `geo_series`、`bioproject`、`sra_study`、`sra_run` 等。 |
| `accession` | 当前行的主 accession。 |
| `project_accession` | 所属 Project/BioProject。 |
| `study_accession` | 所属 Study/Series。 |
| `sample_accession` | 所属 Sample/BioSample/GSM。 |
| `experiment_accession` | 所属 SRA Experiment 等。 |
| `run_accession` | SRR/ERR/DRR；无法展开时使用缺失码。 |
| `official_page_url` | 已核验的官方记录页面；未核验不手工拼接。 |
| `download_url` | 官方 API/页面实际返回的文件链接。 |
| `file_format` | FASTQ、SRA、COOL 等。 |
| `file_size_bytes` | 官方提供的文件大小。 |
| `md5` | 官方提供的 MD5。 |
| `format_validation_status` | 编号格式验证状态。 |
| `online_verification_status` | 在线存在性/关系验证状态。 |
| `verification_date` | ISO 日期 `YYYY-MM-DD`。 |
| `evidence_ids` | 论文声明与归档证据。 |
| `notes` | 镜像、受控、失败或数量对账信息。 |

`accession_relations`以父、子accession和关系类型表示Series→Sample、Sample→Experiment、Experiment→Run等关系。`files`一行表示一个Run的一个FASTQ文件；`download_url`保留ENA API `fastq_ftp`字段原值，`reachability_status`与API是否返回分开。

## 9. `source_queries`

每次官方查询记录endpoint、完整参数、UTC时间、HTTP状态、响应SHA-256、响应字节数、返回行数、快照路径、分页是否完整、重试数和错误摘要。接口失败使用`query_failed`语义，不能写成`NOT_FOUND`。

## 10. `evidence`

证据记录同时保存支持对象、定位和最短必要上下文。

| 字段 | 含义与约束 |
|---|---|
| `evidence_id` | 证据主键。 |
| `supported_table` | 被支持的表。 |
| `supported_record_id` | 被支持记录的主键。 |
| `supported_fields` | 被支持字段列表。 |
| `source_type` | `local_pdf`、`official_database` 等。 |
| `citation_or_database` | 论文引文或数据库名。 |
| `source_locator` | 本地相对路径或官方 URL。 |
| `page_or_section` | PDF 页码、章节、图表或数据库字段。 |
| `minimal_excerpt` | 最短必要证据摘录；不得堆入整页。 |
| `query_or_method` | 提取/查询方法或 API 条件。 |
| `verification_date` | 核验日期。 |
| `extractor` | 提取者。 |
| `reviewer` | 人工复核者；尚未复核为 `NR`。 |
| `evidence_level` | `primary_paper`、`supplement`、`archive_record` 或 `secondary_locator`。 |
| `notes` | 证据质量或冲突说明。 |

## 11. `unresolved_issues`

| 字段 | 含义与约束 |
|---|---|
| `issue_id` | 问题主键。 |
| `paper_id` | 所属论文。 |
| `related_record_id` | 相关实验/样本/accession ID。 |
| `issue_type` | 缺失、冲突、访问失败、映射不唯一等。 |
| `description` | 可独立理解的问题描述。 |
| `checked_sources` | 已检查的来源列表。 |
| `current_assessment` | 当前最保守判断。 |
| `requires_user_decision` | 是否需要用户裁决，`yes/no`。 |
| `status` | `open`、`resolved`、`deferred`。 |
| `resolution` | 解决方式；未解决为 `NA`。 |
| `notes` | 后续检查建议。 |

## 12. `literature_experiment_catalog`

用户宽表按“论文 × 实验 × 条件 × 重复 × 批次 × 样本/时间点 × 归档样本 × Run × 文件”展开。P0008采用一行一个FASTQ文件的固定粒度；字段来自规范表，不在宽表中创造新事实。

| 字段组 | 字段与含义 |
|---|---|
| 行与外键 | `catalog_row_id` 为主键；`paper_id`、`experiment_id`、`sample_timepoint_id`、`perturbation_id`、`accession_record_id` 指回规范表。 |
| 论文 | `paper_title`、`doi`。 |
| 数据归属 | `own_data_status`。 |
| 样本 | `species_scientific`、`cell_line_or_tissue`、`sample_name_original`。 |
| 检测 | `assay_type`、`detection_target`。 |
| 同步化 | `synchronization_method`、`time_zero_definition`、`sampling_time`、`sampling_time_unit`、`cell_cycle_phase`、`phase_evidence_type`。 |
| 扰动 | `perturbation_type`、`direct_target`、`expected_effect`、`observed_validation`。 |
| 归档 | `namespace`、`entity_type`、`accession`、`project_accession`、`study_accession`、`run_accession`、`official_page_url`、`download_url`、`online_verification_status`。 |
| 证据与备注 | `evidence_ids`、`notes`。 |

`perturbation_id` 和 `accession_record_id` 在确实不适用时可为 `NA`；其余外键必须有效。示意 accession（如 `SRR123456`）只出现在文档或测试中，不得进入真实结果表。

## 13. 分层数据归属

`own_data_status`仅作为向后兼容摘要，不再承担全部“自产”语义。`archive_samples`、`accessions`和用户视图新增：

| 字段 | 语义 |
|---|---|
| `biological_sample_origin_status` | 生物样本是否由本研究产生。 |
| `library_origin_status` | 测序文库是否由本研究构建。 |
| `sequencing_generation_status` | 测序是否由本研究新增；无法把具体Run分配到既有/追加测序时为`UNRESOLVED`或`mixed_or_additional_unassigned`。 |
| `analysis_usage_status` | `primary_analysis`、`reanalyzed_prior_data`、`comparison_only`、`UNRESOLVED`或`NA`。 |
| `origin_evidence_ids` | 支持分层判断的证据ID。 |

来源字段受控值为`study_generated`、`reused_from_prior_study`、`mixed_or_additional_unassigned`、`UNRESOLVED`、`NA`。不得仅因记录属于同一GEO Series就推断所有来源层级。

## 14. `semantic_review`

一行对应一个“记录 × 高风险字段”审计单元。`decision_status`仅允许`verified`、`partially_verified`、`unresolved`、`not_applicable`；`reviewer_status=machine_extracted_pending_human_review`表示机器已按规则处置但尚待人工签核。原始alias必须保留，候选解释不能代替最终裁决。

## 15. Run/File双粒度视图

- `literature_experiment_catalog_runs.tsv`：一行一个唯一Run，paired-end文件使用明确的`read1_*`/`read2_*`列。
- `literature_experiment_catalog_files.tsv`：一行一个FASTQ文件。
- `literature_experiment_catalog.tsv`：为兼容旧路径保留，内容与File粒度视图一致。

三张视图均由规范表确定性生成，禁止手工编辑。

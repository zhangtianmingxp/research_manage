# Prompt 3

## 任务标题

复核 P0008 高风险语义，完善数据归属模型，并冻结批量处理前的数据契约

## 本轮定位

第1轮完成论文清单和初版数据标准；第2轮完成schema v2、`P0008 / GSE102740`的60个GSM全量处置、1,290个Run对账及2,580条ENA FASTQ文件记录。当前技术链路已经可重复运行，但仍有几项会影响后续27篇论文一致性的语义问题：

1. `R1/R2`只保存了作者标签，尚未确认在各实验中表示生物重复、技术重复或其他含义。
2. 日期型sample alias只作为batch候选，尚未确认它对应实验日期、建库批次、测序批次还是仅为命名标签。
3. 两个HeLa S3样本来自“此前已报告数据的更深测序后重新分析”，单一`own_data_status`无法清楚区分生物样本来源、文库来源和本研究新增测序Run。
4. v1历史ENA失败占位记录`AC-P0008-004`仍留在`accessions`中，虽然不计入真实Run，但会给用户造成它是归档实体的错觉。
5. 当前宽表为File粒度；普通用户通常还需要一张不重复Run的Run粒度视图。

本轮只完成P0008高风险证据复核、必要的最小schema修订和批量处理准入冻结，不处理其他27篇论文。目标是把“可以由证据裁决的内容”裁决清楚，把“仍不能裁决的内容”以可检索、可解释的缺失/冲突状态冻结下来，而不是为了填满字段强行推断。

执行前必须读取并遵守：

- `AGENTS.md`
- `.research_agent/AGENTS.md`
- `PROJECT_RULES.md`中数据只读、可追踪、配置化、结果复现、文档、测试、大文件和低上下文章节
- `project_plan.md`第四至第九节及第十一、十二节
- `ans_qes/prompt2.md`与`ans_qes/result2.md`
- `docs/schema_migration_v1_to_v2.md`
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- `reports/per_paper/P0008_pilot.md`
- `reports/P0008_accession_reconciliation.md`
- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `configs/pilots/P0008.json`
- `.research_agent/project_state.md`与`.research_agent/progress.json`

读取TSV/XML前先程序化统计行数、列名、唯一键、受控缺失码和目标记录，不把完整1,290/2,580行表格载入对话。读取PDF或补充材料时只定位与本轮五个问题直接相关的Methods、sample table、figure legend、Data Availability和HeLa来源段落。

## 当前基线

- 29个研究PDF对应28篇规范论文；当前只完成`P0008`试点。
- schema v2最终校验为0错误、0警告；14项离线测试通过。
- `GSE102740`：60个GSM，其中58个*Gallus gallus*、2个*Homo sapiens*。
- NCBI与ENA均返回1,290个唯一Run，集合差集为0。
- 31个GSM对应多个Run，29个GSM对应单Run；没有GSM无Run或Run无唯一GSM。
- File粒度宽表2,580行；ENA URL、大小和MD5字段覆盖率100%。
- 作者重复标签：R1 38、R2 20、缺失2；当前60个GSM的重复类型均未裁决。
- 日期型batch候选51个，9个缺失；均未升级为已验证batch。
- 两个HeLa样本`GSM2745897`与`GSM2745898`的`own_data_status=unclear`。
- 当前有6条未解决问题；本轮不得静默删除历史问题。
- 工作区包含前两轮未提交改动；不得覆盖、回退或清理用户现有修改。

## 核心目标

1. 获取或定位P0008的正式补充材料，用最小必要范围核对R1/R2、日期alias、G2p/G2n、30 min有/无药物条件及HeLa数据来源。
2. 生成逐字段的高风险语义审计表，记录原值、候选解释、证据、裁决状态、裁决规则和复核者状态。
3. 将“本文自产”拆成至少生物样本来源、文库来源、测序Run产生和本研究分析使用四个可区分维度；对P0008的60个GSM和1,290个Run逐项填充或保守缺失。
4. 安全处置`AC-P0008-004`历史失败占位：不破坏历史ID和证据，但不再把它作为活跃Run实体参与计数或用户视图。
5. 在保留File粒度可追溯视图的同时，新增确定性的Run粒度用户视图。
6. 完成schema v2批量准入审计，形成后续论文必须满足的数据契约、检查清单和停止条件。
7. 更新代码、配置、文档、测试、报告和`ans_qes/result3.md`后停止。

## 范围边界

### 必须完成

- P0008正式补充材料的官方定位与来源记录；若本地不存在，可从期刊或作者提供的正式入口获取补充PDF/表格。
- 60个GSM的高风险语义逐项审计。
- HeLa两个GSM及其全部Run的数据归属分层建模。
- v1历史失败占位的向后兼容迁移。
- Run粒度与File粒度两类用户视图。
- schema批量准入文档、自动化测试和P0008审计报告。
- `ans_qes/result3.md`。

### 本轮禁止

- 不解析或整理`P0008`之外论文的实验设计、accession或公共元数据。
- 不批量处理剩余27篇论文，不创建它们的试点配置。
- 不下载FASTQ、SRA、BAM/CRAM、COOL、Hi-C矩阵或GEO大型归档。
- 不修改、移动、重命名或复制`文献/研究/`和`文献/综述/`中的原PDF。
- 不把sample title、日期、R1/R2、文件名或常识作为最终语义裁决的唯一依据。
- 不将搜索结果摘要、综述或聚合站点作为最终证据。
- 不把“本研究重新分析”“本研究新测序”“本研究新建生物样本”混成同一状态。
- 不为文件URL执行正文下载；如需可达性抽查，最多3个确定性样本并只做HEAD/metadata请求。
- 不调用远程LLM API。
- 不生成`prompt4.md`，不commit，不push。

## 实施要求

### 1. 先建立审计基线，不直接修改语义字段

在任何迁移前，用程序记录：

- schema版本及16张表的行数、列数、主外键、唯一键和内容哈希；
- 60个GSM、1,290个Run、2,580个File的集合与哈希；
- R1/R2、日期alias、`G2p/G2n`、30 min、HeLa样本的目标记录集合；
- `own_data_status`、replicate、batch及历史占位记录的当前值；
- `prompt1/result1/prompt2/result2`与29个研究PDF的哈希。

迁移后必须证明上述核心集合没有丢失、重复或被错误合并。

### 2. 正式补充材料与证据链

优先来源：

1. Science正式文章页面的Supplementary Materials入口；
2. 论文正文已给出的正式补充材料链接；
3. 作者/期刊正式仓库；
4. GEO/NCBI/ENA官方记录仅支持归档字段，不替代论文对重复和处理条件的解释。

若获取补充材料：

- 记录官方URL、访问日期、HTTP状态、文件大小、SHA-256和本地只读路径；
- 放入已由`.gitignore`排除的本地文献/补充材料区域，或保存任务所需的小型官方表格快照；
- 不提交受版权保护的补充PDF；只在证据表保存最短必要摘录、页码、表号或行定位；
- 单个补充文件超过20 MB、需要登录/凭据、存在许可不清或需要绕过限制时立即停止该下载并登记问题。

同一官方endpoint失败最多重试3次。失败只能记为`query_failed`，不能写成资料不存在。

### 3. 高风险语义审计表

新增`data/interim/pilot/semantic_review.tsv`或等价规范表，每行是一个“记录 × 字段”的审计单元，至少包含：

- `review_id`
- `paper_id`
- `record_type`与`record_id`
- `field_name`
- `original_value`
- `candidate_interpretation`
- `decision`
- `decision_status`：`verified`、`partially_verified`、`unresolved`、`not_applicable`
- `evidence_ids`
- `decision_rule`
- `reviewer_status`
- `notes`

至少覆盖：

- 60个GSM的`replicate_type`；
- 60个GSM的batch语义；
- 所有`G2p/G2n`和30 min相关GSM的条件解释；
- `GSM2745897`、`GSM2745898`及其全部Run的数据归属维度；
- `AC-P0008-004`的历史记录类型与迁移状态。

“没有证据可以裁决”本身是合法审计结论，必须保留`unresolved`及已检查来源。

### 4. 重复与批次裁决规则

- 不要求所有实验使用同一种R1/R2语义；允许按实验、基因型或作者表格分别裁决。
- 只有补充方法、sample table、建库表或作者明确说明支持时，才可把R1/R2升级为`biological`或`technical`。
- 若只能证明R1/R2是作者的不同数据集标签，继续使用`UNRESOLVED`，但写明证据不足的具体边界。
- 日期alias只有在证据明确其含义时才能升级为`experiment_date`、`library_batch`或`sequencing_batch`；否则保持`candidate`。
- 不得因为相同日期就自动合并batch，也不得因为不同日期就自动拆成生物重复。

### 5. 条件与时间轴高风险抽查

对所有`G2p/G2n`、`sG2`、`PMphase`、30 min及有/无nocodazole相关记录建立核对清单：

- 保留GEO title、Characteristics、论文/补充材料原始组名；
- 分别记录同步化处理、auxin状态、nocodazole状态、释放起点、采样分钟和作者阶段；
- 有/无nocodazole的同一时间点必须能够被condition字段区分；
- `p/n`等缩写只有在作者材料明确给出定义后才能展开；否则保留原缩写和`UNRESOLVED`解释；
- 细胞周期阶段继续遵守`author_stated`、`marker_supported`、`explicitly_inferred`、`unknown`规则。

若当前schema无法表达药物状态与时间轴，不要继续为每个GSM建立孤立condition来掩盖问题；应提出最小规范化修订，并说明迁移与兼容性。

### 6. 分层数据归属模型

评估并实现能够区分以下概念的最小模型：

- `biological_sample_origin_status`：生物样本是否由本文研究新产生；
- `library_origin_status`：测序文库是否由本文研究新构建；
- `sequencing_generation_status`：Run是否为本文新测序/追加测序；
- `analysis_usage_status`：本文是新分析、重新分析还是仅引用比较；
- 原有`own_data_status`作为兼容摘要字段或明确弃用字段，不得静默改变旧语义。

受控值、缺失值与判定规则必须写入数据字典。对鸡源58个GSM也不能仅因同属GSE就无条件推断所有层级为自产；应结合论文Data Availability、提交信息与补充材料给出证据范围。对两个HeLa样本和其Run必须逐层判定，无法区分的层级使用`UNRESOLVED`/等价受控值。

### 7. 历史占位记录迁移

`AC-P0008-004`不是实际Run，不应继续出现在活跃accession或用户视图计数中。优先方案：

- 将失败查询事实迁移到`source_queries`或独立`query_history`实体；
- 保留`legacy_record_id=AC-P0008-004`、原证据、原失败日期与迁移说明；
- 在迁移映射表中记录旧ID到新记录的关系；
- 更新所有引用与测试，保证历史可追溯；
- 不复用`AC-P0008-004`给任何真实Run。

若安全迁移会破坏第1轮历史解释，则保留该行但增加明确的`record_status=deprecated_placeholder`并从所有活跃关系、对账与用户视图排除；在`result3.md`解释选择。

### 8. Run级和File级用户视图

规范事实仍以`archive_samples`、`accessions`、`accession_relations`和`files`为准。至少生成：

1. Run粒度视图：一行一个唯一Run，paired-end文件字段以有顺序、可解析的列表或明确的`read1/read2`列表示；
2. File粒度视图：一行一个FASTQ文件，保持当前2,580行的完整URL/大小/MD5对应关系。

建议路径：

```text
data/interim/pilot/literature_experiment_catalog_runs.tsv
data/interim/pilot/literature_experiment_catalog_files.tsv
```

可以为向后兼容保留现有`literature_experiment_catalog.tsv`，但必须在数据字典和README明确它指向哪种粒度。两类视图必须由同一规范表程序化生成，禁止复制后手工维护。

必须验证：

- Run视图恰好1,290行且Run唯一；
- File视图恰好2,580行且File唯一；
- 每个Run在File视图恰好对应2条记录；
- 两类视图的Run集合均与NCBI/ENA的1,290个Run一致；
- 两次重建内容和排序确定；
- 不因join造成笛卡尔积。

### 9. Schema冻结与批量准入门槛

生成`docs/schema_v2_batch_readiness.md`或等价文档，明确：

- 哪些表和字段已冻结；
- 哪些字段允许后续兼容扩展；
- 主键、外键、粒度和受控值约束；
- 每篇新论文必须提供的最小配置与证据；
- 论文级、实验级、样本级、Run级、File级的完成定义；
- 何时可以标记`completed`，何时必须标记`blocked`、`partial`或`not_applicable`；
- 在线接口失败、补充材料缺失、多对多歧义、受控数据和大文件风险的停止条件；
- 后续批量轮次每次建议处理的论文数，以及不得跨论文共享未经证实语义的原则。

只有以下全部满足才可在文档中标记“schema允许进入小批量处理”：P0008高风险字段均有审计处置、两种视图通过验证、历史占位语义清楚、测试通过、数据字典完整、没有会导致后续论文无法表达的已知阻塞问题。不能把“仍有UNRESOLVED值”本身当作失败；关键是缺口必须可表达、可定位、可统计。

### 10. 代码、配置、文档和测试

根据实际决策更新或新增：

- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `configs/pilots/P0008.json`
- `src/literature_catalog/`中的审计、迁移、双粒度视图和准入检查模块
- `data/interim/pilot/semantic_review.tsv`
- P0008规范表、问题表、证据表和双粒度视图
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- `docs/schema_v2_batch_readiness.md`
- `reports/per_paper/P0008_semantic_audit.md`
- `reports/P0008_accession_reconciliation.{md,tsv}`（若计数口径受迁移影响）
- `README.md`（仍明确项目未完成）
- `tests/fixtures/`与自动化测试

代码继续使用Python 3.11+、`pathlib`、类型标注、配置化路径、清晰错误信息和简洁日志。测试不得访问实时网络；补充材料解析器使用小型fixture。不得把核心逻辑写成临时脚本或只适用于P0008路径的硬编码函数。

## 验收标准

执行结束前至少满足：

1. 迁移前后`python -m src.literature_catalog.cli --root . validate`均有记录，最终0错误。
2. 60个GSM、60个Experiment、1,290个Run和2,580个File集合与第2轮一致，无记录丢失或重复。
3. 60个GSM的replicate和batch均有`semantic_review`处置；有证据才升级，不能裁决则明确`unresolved`。
4. 所有`G2p/G2n`、30 min和nocodazole高风险条件有逐项审计，原始标签100%保留。
5. HeLa两个GSM及其76个Run（第2轮基线）完成分层数据归属处置；不得用单一“自产/复用”掩盖不同层级。
6. 58个鸡源GSM的数据归属判定说明证据适用范围，不因Series归属无限外推。
7. `AC-P0008-004`不再作为活跃Run进入accession计数、关系或用户视图，同时历史ID与失败证据仍可追溯。
8. Run视图1,290行、Run唯一；File视图2,580行、File唯一；每Run恰好2个文件。
9. 两种视图的Run集合与NCBI/ENA一致，连续构建两次哈希分别稳定。
10. schema、受控词表、数据字典、验证规程和README对粒度及数据归属字段描述一致。
11. 自动化测试不访问网络，并覆盖：补充材料解析、无补充材料、部分证据、重复/批次未决、HeLa分层归属、历史占位迁移、Run/File视图、防笛卡尔积、重建哈希和准入检查。
12. 第1、2轮ID、prompt/result、报告和证据未被覆盖；迁移映射可定位。
13. 29个研究PDF哈希与`paper_files.tsv`一致，`文献/`原文件未修改。
14. 未新增或提交大型原始/处理数据；补充材料遵守版权与`.gitignore`策略。
15. README仍明确说明只完成P0008，其他27篇论文未完成。
16. 不创建`prompt4.md`，不commit，不push。

## `result3.md`必须记录

- 对应prompt：`ans_qes/prompt3.md`。
- 补充材料来源、访问日期、状态、大小、SHA-256、保存策略和实际读取的页/表范围。
- R1/R2逐实验裁决统计：verified、partially verified、unresolved数量及证据。
- batch逐实验裁决统计及日期alias最终语义。
- `G2p/G2n`、30 min、nocodazole高风险记录的审计结论。
- HeLa两个GSM及其Run的数据归属分层结果和仍无法裁决的层级。
- `own_data_status`兼容策略与schema变化。
- `AC-P0008-004`迁移方式、旧ID追溯路径及计数排除验证。
- Run/File双视图的行数、唯一数、集合对账、缺失率和SHA-256。
- schema批量准入结论：`ready`、`ready_with_documented_gaps`或`not_ready`，并给出机器检查依据。
- 创建/修改文件清单。
- 执行命令、测试通过/失败/跳过数及最终校验结果。
- 是否满足相关`PROJECT_RULES.md`。
- 未解决问题、需要用户裁决的内容、风险与限制。
- commit建议，但不得执行commit。
- 只提出下一步建议，不生成`prompt4.md`。

## 停止条件

遇到以下任一情况，保留已完成的安全审计/代码改进，在`result3.md`如实记录后停止，不得扩大范围或猜测：

- 正式补充材料无法从官方入口获得，且现有正文不足以裁决关键语义；
- 补充材料需要凭据、绕过限制、许可不清或单文件超过20 MB；
- 同一R1/R2或日期标签在不同来源中含义冲突，无法建立分实验规则；
- HeLa的生物样本、文库或测序Run来源仍存在多种同等可能解释；
- 迁移历史占位会破坏第1/2轮ID、证据或结果解释，且没有兼容方案；
- 双粒度视图与规范表无法在无歧义条件下对账；
- 测试失败且不能通过局部、明确的修复解决；
- 继续需要处理其他论文、大型测序数据、受控数据或外部凭据。

证据不足时保留`UNRESOLVED`并不等于任务失败；伪造裁决、静默合并或删除问题才是失败。

## 暂不执行

本文件只是第3轮任务提示词。现在必须停止并等待用户审查；只有用户明确要求“执行`ans_qes/prompt3.md`”后才能执行。生成本prompt时不得修改科研schema、代码、数据、报告或README，不得创建`ans_qes/result3.md`，不得commit或push。

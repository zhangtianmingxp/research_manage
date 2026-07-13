# Prompt 2

## 任务标题

完善条件、重复与批次建模，并完成 P0008 / GSE102740 的样本—Run 全量映射

## 本轮定位

第1轮已完成论文文件清单、初版 schema、校验工具及 `P0008` 的代表性试点，但试点仍有三个关键缺口：

1. `samples_timepoints` 未显式区分实验条件、重复和批次。
2. `GSE102740` 的60个 GEO 样本尚未逐项进入规范表。
3. `PRJNA398543 / SRP115572` 尚未展开到 SRA/ENA Sample、Experiment、Run 和文件链接。

本轮只修订数据模型并完成 `P0008` 这一篇论文的全量公共元数据映射，用它作为批量处理其他论文前的第二次 schema 验证。不得处理其他27篇规范论文，不下载 FASTQ、BAM、COOL 归档或其他大型原始/处理数据，不生成下一轮 prompt。

执行前必须读取并遵守：

- `AGENTS.md`
- `.research_agent/AGENTS.md`
- `PROJECT_RULES.md` 中与数据只读、可追踪、模块化、测试、日志、大文件和低上下文有关的章节
- `project_plan.md` 第四至第九节及第十一、十二节
- `ans_qes/prompt1.md`
- `ans_qes/result1.md`
- `reports/per_paper/P0008_pilot.md`
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `.research_agent/project_state.md`
- `.research_agent/progress.json`

读取 TSV 前先用程序统计行数、列名、唯一键和缺失码，不要把完整表格直接加载进对话上下文。

## 当前基线

- 研究 PDF：29个；规范论文：28篇。
- 当前仅 `P0008` 完成试点书目与实验整理。
- 试点现有：2个实验、10个样本/时间点、1个扰动、4个 accession 层级记录、7条证据、3个未解决问题、10行宽表。
- NCBI GEO 官方页已确认 `GSE102740` 公开、包含60个 GSM，并关联 `PRJNA398543` 与 `SRP115572`。
- 第1轮 ENA Portal API 查询失败，Run 和官方 FASTQ 字段仍为 `NOT_FOUND`。
- 两个 GEO 样本属于 *Homo sapiens*，其余样本不能仅凭先验假定为 *Gallus gallus*；以官方样本记录为准。
- 工作区可能存在未提交的第1轮改动；不得覆盖或回退用户现有修改。

## 本轮核心目标

1. 根据第1轮试点问题修订规范化 schema，显式表示 `condition`、`replicate`、`batch` 及 accession 之间的父子/镜像关系。
2. 为 `GSE102740` 的60个 GSM 建立一一对应的处置记录，保留原始 sample title/alias，不因名称相似而强行合并。
3. 从 GEO/BioProject/SRA Study 展开到官方 Sample、Experiment、Run；若 ENA 可用，再补充 ENA 镜像和官方文件字段。
4. 建立 GSM → biological condition/timepoint → SRS/SAMN → SRX → SRR/ERR/DRR → file 的可追溯映射。
5. 对论文、GEO、SRA/ENA 三个层级做数量对账，并清晰区分“没有对应记录”“官方未返回”“查询失败”“受控访问”。
6. 用代码从规范表生成宽表，避免继续手工复制同一事实。
7. 更新文档、试点报告、测试和 `ans_qes/result2.md`，随后停止。

## 范围边界

### 必须完成

- schema 修订及向后兼容的数据迁移。
- 60个 GSM 的完整元数据处置。
- 官方可公开获得的全部 SRA/ENA Run 元数据处置与数量对账。
- `P0008` 现有试点表升级为可复现、可重新生成的版本。
- 自动化测试和人工高风险字段抽查。
- `ans_qes/result2.md`。

### 本轮禁止

- 不解析或整理 `P0008` 之外的论文实验。
- 不下载测序reads、192.7 GB GEO归档、COOL矩阵、BAM/CRAM或其他大型数据。
- 不修改、移动、重命名或复制 `文献/` 中的 PDF。
- 不使用搜索结果摘要、综述、聚合站点或文件名作为最终数据库事实证据。
- 不把 GSM、GSE、PRJNA、SRP、SRS、SRX 当作 Run accession。
- 不根据 sample title 中的 `G2`、`7m`、`R1`、日期或缩写自行推断生物学含义；必须保留原名，并由论文、补充材料或官方记录支撑标准化解释。
- 不手工拼接 ENA FASTQ URL 后标记为已验证。
- 不调用远程 LLM API。
- 不生成 `prompt3.md`，不 commit，不 push。

## 实施要求

### 1. 先做迁移设计，不直接破坏现有表

在修改 schema 前，先程序化总结现有9张表：行数、列数、主键、外键、缺失码和试点记录数。提出最小但足够的迁移方案，并记录在设计文档中。

迁移后至少能显式表示：

- `condition_id`：实验条件组合，包括同步化、扰动、药物、时间点和对照角色。
- `replicate_id`：生物/技术重复类型、作者原始重复标签和重复序号。
- `batch_id`：实验日期、建库批次、测序平台或作者批次标签；未报告时使用缺失码。
- 一个生物条件对应多个重复，一个重复对应一个或多个 archive sample/experiment/run。
- 一个 GSM 对应零个、一个或多个 SRA Run。
- accession 之间的关系类型，例如 `series_has_sample`、`project_has_study`、`sample_has_experiment`、`experiment_has_run`、`mirrors`。

推荐新增规范化实体：

- `conditions`
- `replicates`
- `batches`
- `accession_relations`
- `source_queries`

是否新增独立 `archive_samples`/`files` 表由实际元数据决定。若选择只给现有表加列，必须证明不会导致重复字段、不可表达多Run或无法对账。

迁移要求：

- 保留现有 `paper_id`、`file_id`、`experiment_id`、`sample_timepoint_id`、`perturbation_id` 和 `evidence_id`，除非存在明确冲突。
- 不覆盖 `prompt1.md`、`result1.md` 或第1轮历史报告。
- 更新 schema version，并在文档中记录旧列到新实体/新列的映射。
- 迁移前后均运行校验；失败时不得留下半迁移状态。

### 2. 把在线抓取与离线转换分开

扩展现有 CLI/模块，至少形成两个逻辑阶段：

1. `fetch`：只从官方数据库获取小型元数据并保存来源清单/快照。
2. `build`：仅依赖保存的元数据快照，离线、确定性地生成规范表和宽表。

核心逻辑必须可复用于后续论文，不得把 `P0008` 写死在通用函数中。可以用 `configs/pilots/P0008.json` 或等价配置保存该论文的 accession、预期 GEO 样本数和本地证据定位。

每次官方查询至少记录：

- `query_id`
- 数据库/endpoint
- 完整查询条件或参数
- 查询日期与时间
- HTTP/服务状态
- 响应内容哈希
- 返回行数
- 保存的轻量快照路径
- 是否完整分页
- 重试次数和错误摘要

若官方响应超过5 MB，只保存任务所需字段的确定性子集、响应哈希和查询清单，不保存大响应或下载数据文件。

测试不得依赖实时网络。为解析器提供小型、去隐私的官方格式 fixture；在线步骤与离线构建步骤分别测试。

### 3. 官方来源与查询顺序

只允许以下来源支撑最终 accession 和下载字段：

1. NCBI GEO 官方 Series/Sample记录、SOFT/MINiML或官方导出。
2. NCBI BioProject、SRA Run Selector/RunInfo、E-utilities或其他NCBI官方元数据接口。
3. EMBL-EBI ENA Browser/Portal API 官方记录。
4. DDBJ 仅用于 INSDC 镜像交叉验证。

优先顺序：

1. 获取 `GSE102740` 的60个 GSM 及原始标题、物种、平台、source、characteristics、处理/时间线索。
2. 获取 `PRJNA398543 / SRP115572` 的完整 Sample、Experiment、Run 元数据。
3. 用官方字段连接 GEO 与 SRA；不依赖字符串模糊匹配作为唯一依据。
4. 查询 ENA 对应 Study/Run/File 字段：`fastq_ftp`/等价官方链接、文件大小、MD5、library layout、instrument等。
5. 记录 NCBI 与 ENA 的镜像关系和字段冲突。

有限重试原则：同一 endpoint 最多3次，并使用合理退避；不得无限循环或通过大范围搜索绕过官方服务故障。

### 4. 60个 GEO 样本的逐项处置

必须以 GEO 官方 Series 返回的样本集合为基准，建立60个唯一 GSM 记录。每个 GSM 至少记录：

- GSM accession、原始 sample title/alias。
- 物种、细胞系/组织、平台。
- 作者原始 condition、timepoint、replicate、batch/date 标签。
- 标准化 condition/timepoint/replicate/batch；无法由证据确认则使用缺失码。
- 是否本文自产数据及证据。
- 对应 SRA/BioSample/SRX/Run 数量。
- 当前处置状态：`mapped`、`no_sra_relation`、`metadata_incomplete`、`conflicted`、`query_failed` 或等价受控值。
- 字段级 `evidence_ids`。

特别检查：

- *Gallus gallus* 与 *Homo sapiens* 样本不得混合计数。
- `R1/R2` 是生物重复还是技术重复必须由论文、补充材料或数据库字段支持。
- 日期型 alias 只能作为 batch 候选；未证实时不要自动定性。
- `G2p/G2n`、`sG2`、`PMphase` 等缩写必须保存原文，并记录标准化依据。
- 有/无 nocodazole 的30 min样本必须能被不同 condition 区分。

### 5. Run 与文件映射

对官方返回的每个 Run 建立独立记录，并至少保存：

- Run accession（SRR/ERR/DRR）。
- 所属 Project/Study、Sample/BioSample、Experiment。
- 对应 GSM；若无法唯一映射，禁止强行指定并进入问题表。
- library strategy/source/selection/layout、platform/instrument。
- 官方公开状态。
- ENA/NCBI官方页面 URL。
- ENA API实际返回的文件链接、格式、字节数和MD5；未返回则使用缺失码。
- 格式验证状态、在线关系验证状态、链接字段来源和查询日期。

文件链接检查不得下载文件正文。可以对最多3个确定性抽样链接做 HEAD/metadata 可达性检查；不得向所有大型文件发起下载请求。官方 API 返回链接与实际可达性分列记录。

### 6. 数量对账

必须生成机器可读和人类可读的对账结果，至少包含：

- GEO Series 声明的 GSM 数。
- 实际提取的唯一 GSM 数。
- 按物种、平台、condition、timepoint、replicate、batch 分层的样本数。
- NCBI SRA 返回的唯一 Sample、Experiment、Run 数。
- ENA 返回的唯一 Run 数。
- NCBI 与 ENA Run 集合交集、仅NCBI、仅ENA。
- 规范 `accessions`/关系表和宽表中的唯一 Run 数。
- GSM无Run、GSM多Run、Run无唯一GSM映射的数量。
- 下载链接、大小和MD5字段的覆盖率。

所有计数必须由代码生成，不能手工填写。任何不相等都需要给出可定位的差集文件或问题记录，不能只写“有差异”。

### 7. 证据与自产数据判定

- 论文方法/图表负责支撑实验条件、同步化、时间点和扰动解释。
- GEO/SRA/ENA负责支撑 accession、alias、物种、平台、运行和文件字段。
- 每个标准化 condition/timepoint 必须能回到原始 sample title/characteristics 和解释依据。
- 每个 GSM/Run 的 `own_data_status` 逐项判定；不得因为位于同一 GSE 就一律标为自产。
- 两个 *Homo sapiens* 样本尤其需要核对是本文自产、重测、复用还是对照引用。
- 数据库间冲突并列保存，并进入 `unresolved_issues`。

不得保存大段论文原文；证据摘录保持支持字段所需的最短上下文。

### 8. 宽表生成

宽表必须由规范表和关系表程序化生成，不再手工维护。建议每行粒度为：

```text
paper × experiment × condition × replicate × sample/timepoint × archive sample × experiment accession × run × file
```

若一个 Run 有两个 paired-end FASTQ 文件，可按文件拆行或用明确的列表字段表示，但必须在数据字典中固定规则。Series/Project级记录不得与Run级记录混在同一种行语义中；可另生成项目级摘要表。

生成器需保证：

- 每行主键确定且稳定。
- 每行可回溯到规范表、关系表和证据。
- 重新运行结果顺序和内容确定。
- 不因多表join产生无意义笛卡尔积。

### 9. 代码、文档和测试

更新或新增：

- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `configs/pilots/P0008.json` 或等价配置
- `src/literature_catalog/` 中的官方元数据适配、离线构建、关系验证和对账模块
- `data/interim/pilot/` 的轻量官方元数据快照/查询清单
- `data/curated/` 或 `data/interim/pilot/` 中升级后的规范表
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- schema迁移说明
- `reports/per_paper/P0008_pilot.md`
- P0008对账报告
- `tests/` 中的fixture和自动化测试
- `README.md` 中的当前进度（仍明确项目未完成）

代码要求：Python 3.11+、`pathlib`、类型标注、清晰错误信息、`--root`/配置化路径、长步骤的简洁日志或进度。不得把核心逻辑塞进 notebook 或临时一次性脚本。

## 建议交付结构

允许根据最终模型小幅调整，但必须在 `result2.md` 解释偏差：

```text
configs/
  catalog_schema.json
  controlled_vocab.json
  pilots/P0008.json
data/
  interim/pilot/
    source_metadata/            # 小型官方元数据快照
    source_queries.tsv
    conditions.tsv
    replicates.tsv
    batches.tsv
    samples_timepoints.tsv
    accessions.tsv
    accession_relations.tsv
    evidence.tsv
    unresolved_issues.tsv
    literature_experiment_catalog.tsv
reports/
  per_paper/P0008_pilot.md
  P0008_accession_reconciliation.md
  P0008_accession_reconciliation.tsv
docs/
  schema_migration_v1_to_v2.md
tests/
  fixtures/
```

## 验证与验收标准

执行结束前至少满足：

1. 迁移前后 `python -m src.literature_catalog.cli --root . validate` 均有记录；最终0错误。
2. 60个唯一 GSM 全部出现且各有处置状态；不得多于或少于官方 Series 集合。
3. `P0008` 的原始 sample title/alias 100%保留。
4. 所有标准化 condition/timepoint/replicate/batch 要么有证据，要么使用规定缺失码。
5. NCBI官方返回的全部公开 Run 均逐项处置；表中不得出现猜测Run。
6. 若ENA查询成功，ENA与NCBI Run集合完成差集对账；若失败，查询清单、重试次数和未完成范围明确记录，不能声称完成ENA核验。
7. 每个真实Run的Sample/Experiment/Study关系通过官方元数据验证。
8. 官方API文件字段与链接可达性状态分开；没有手工拼接链接冒充验证。
9. GEO、SRA、ENA、规范表和宽表的计数由代码生成，并能定位所有差异记录。
10. 宽表由代码重新生成；连续运行两次得到相同内容哈希。
11. 主外键、唯一键、受控词表、证据引用、关系类型和非法空值检查通过。
12. 自动化测试不访问网络，并覆盖解析、分页/空响应、迁移、GSM多Run、Run无GSM、关系校验、对账和宽表防笛卡尔积。
13. 第1轮ID和历史文件没有被破坏；`prompt1.md`、`result1.md`内容未被覆盖。
14. `文献/` PDF最终哈希与现有 `paper_files.tsv` 一致。
15. 未新增超过5 MB的元数据/日志/缓存文件，未下载原始测序或处理数据。
16. README仍明确标注项目未完成，不能把单篇完成写成全项目完成。

## `result2.md` 必须记录

- 对应 prompt：`ans_qes/prompt2.md`。
- schema v1→v2的修改及迁移结果。
- 创建/修改文件清单。
- 官方查询endpoint、日期、状态、快照大小、行数和重试摘要。
- 60个GSM的处置统计，按物种/平台/condition/timepoint/replicate/batch分层。
- NCBI/ENA Sample、Experiment、Run、File数量和集合对账。
- GSM无Run、多Run、Run无唯一GSM、字段冲突的具体数量。
- 下载链接、大小、MD5覆盖率；HEAD抽样结果（若执行）。
- 规范表和宽表行数、内容哈希、关键缺失率。
- 测试命令、通过数、失败/跳过项。
- 是否满足相关 `PROJECT_RULES.md`。
- 仍未解决的问题及需要用户裁决的schema选择。
- commit建议，但不得执行commit。
- 只提出下一步建议，不创建 `prompt3.md`。

## 停止条件

遇到以下任一情况，保留安全的schema/代码改进，在 `result2.md` 如实记录后停止，不得扩大范围或伪造完整结果：

- GEO官方记录无法获得完整60个样本集合。
- NCBI/ENA接口在最多3次有限重试后仍不可用，导致Run集合不能可靠获得。
- GSM与Run之间存在无法用官方字段或论文证据裁决的多对多歧义。
- 继续需要下载大型数据、受控数据、凭据或绕过服务限制。
- 迁移会破坏第1轮ID/证据且没有安全的向后兼容方案。
- 测试失败且不能通过局部、明确的修复解决。
- 需要读取其他论文或过宽上下文才能继续。

API失败不等于项目号或Run不存在；必须使用 `query_failed`/等价状态，而不是 `NOT_FOUND`，除非已成功查询且官方结果明确为空。

## 暂不执行

本文件只是第2轮任务提示词。现在必须停止，等待用户审查；只有用户明确要求“执行 `ans_qes/prompt2.md`”后才能执行。生成本 prompt 时不得修改schema、数据表、代码或报告，不得创建 `ans_qes/result2.md`。

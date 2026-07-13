# 文献实验目录核验规程

## 1. 目的

本规程用于保证论文、实验、样本、扰动与公共数据库编号之间的每条映射都可追溯。目标不是尽量填满字段，而是在不确定时保留清晰、可复核的缺口。

## 2. 来源优先级

1. 论文正文、Methods、Data Availability。
2. 正式补充材料中的方法、样本表和数据表。
3. 期刊正式页面。
4. ENA/EMBL-EBI、NCBI SRA/BioProject/BioSample/GEO、DDBJ 等官方归档记录。
5. 综述、搜索结果和聚合站点只能定位线索，不能单独支撑最终字段。

## 3. 逐篇核验步骤

1. 记录本地 PDF 的 `file_id`、SHA-256 和相对路径，原文件保持只读。
2. 从标题页确认题名、作者、期刊、年份和 DOI；文件名只能作为 `*_hint`。
3. 定位 Methods、Data Availability、补充材料引用及关键图表。
4. 按“实验—样本/时间点—扰动—accession”拆分记录。
5. 为每个关键字段写入 `evidence_id`，证据保留页码/章节或官方 URL、查询条件和日期。
6. 从 Project/Series 向 Study、Sample、Experiment、Run 展开，并进行数量对账。
7. 格式验证与在线验证分开记录。编号看似符合正则不代表数据库中真实存在。
8. 来源冲突时并列保留原值并登记 `unresolved_issues`，禁止静默覆盖。

## 4. 缺失值

- `NR`：论文或补充材料未报告。
- `NA`：字段不适用。
- `NOT_FOUND`：按规程检索后未找到。
- `UNRESOLVED`：来源冲突或不能安全裁决。
- `RESTRICTED`：受控、未公开或访问受限。

除自由备注外，不用空字符串表示未知。列表值使用 `|` 分隔，且各元素不得自行包含 `|`。

## 5. 自产数据判定

- `yes`：论文或提交者信息明确支持本研究生成或委托生成。
- `no_reused`：论文明确复用既有数据。
- `derived_from_own`：由本文自产数据计算得到的二次产物。
- `unclear`：证据不足。

accession 出现在论文中本身不足以判定为自产。

## 6. 同步化与阶段判定

分别记录处理开始、阻断完成、释放/洗脱和采样时刻。细胞周期阶段只允许以下证据类型：

- `author_stated`：作者直接标注。
- `marker_supported`：作者用标记物或 FACS 等支持。
- `explicitly_inferred`：依据作者给出的明确映射推导，并保存规则。
- `unknown`：无法确认。

不得仅凭经过分钟数按常识推断周期阶段。

## 7. accession 与链接

实体层级必须分列：Project/BioProject、Study/Series、Sample/BioSample、Experiment、Run。`SRR/ERR/DRR` 才是 Run accession。ENA 下载地址必须来自 ENA 官方页面或 API 实际响应；手工拼接的 URL 不得标记为 `verified`。

## 8. 自动检查

```powershell
python -m src.literature_catalog.cli --root . validate
python -m src.literature_catalog.cli --root . summary
python -m unittest discover -s tests -v
```

检查覆盖表头、必填值、主外键、唯一键、论文文件覆盖、综述排除、accession 类型和证据引用。自动检查不能替代人工阅读原始证据。

## 9. 在线抓取与离线构建

```powershell
python -m src.literature_catalog.cli --root . fetch
python -m src.literature_catalog.cli --root . build
```

`fetch`仅访问配置中的官方endpoint，每个请求最多3次，并保存轻量快照与`source_queries.tsv`。`build`不访问网络，必须从保存的快照生成规范表、关系表、文件表、对账报告和宽表。测试只能使用保存的快照或`tests/fixtures/`，不得依赖实时网络。

对P0008，构建前必须同时满足：GEO唯一GSM数为60；NCBI实验数为60；NCBI与ENA Run集合完全一致；所有Run能通过官方alias唯一映射到GSM。任何失败都必须中止并保留差集，不得进行模糊匹配。

## 10. 高风险语义与补充材料

- R1/R2、日期、`G2p/G2n`、`30m`等alias只能作为原值和候选解释；升级必须有作者方法、表格或图注明确支持。
- 正式入口失败最多3次；失败记为`query_failed`，不等于不存在。
- 单文件超过20 MB、需登录或需绕过限制时停止下载，记录URL、状态、已知大小和原因。
- “样本来源、文库来源、测序生成、分析使用”必须分别核验。对具体Run无法分配新旧测序时保持`UNRESOLVED`。
- `semantic_review`中的机器处置必须保留人工复核状态。

## 11. 双视图与历史迁移检查

P0008离线构建后必须验证Run视图1,290行、File视图2,580行、每Run恰好两个文件、两者Run集合一致且连续构建哈希稳定。失败查询历史必须留在`source_queries`，不能伪装成accession；旧ID通过`legacy_record_id`追溯。

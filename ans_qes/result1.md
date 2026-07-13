# Result 1

## 对应 Prompt

- `ans_qes/prompt1.md`

## 执行摘要

本轮完成了研究论文文件清单、规范化数据 schema、受控词表、字段字典、核验规程、可重复运行的清单/校验 CLI、自动化测试，以及 1 篇论文的结构化试点。主分析目录中的 29 个 PDF 均已登记；两份 2015 年 Genome Research PDF 的 SHA-256 完全相同，因此保留 29 个文件记录并映射为 28 篇规范论文。

试点选择 Gibcus et al. 2018 Science 论文 “A pathway for mitotic chromosome formation”（`P0008`）。本轮记录了同步化 DT40 Hi-C 时间序列、SMC2-mAID/auxin 代表性扰动、GEO/BioProject/SRA Study 层级及字段级证据。NCBI GEO 官方页确认 `GSE102740` 关联 `PRJNA398543` 和 `SRP115572`；ENA Portal API 在当前环境无法连接，因此没有猜测或生成任何 SRR/ERR/DRR 和 ENA 下载链接。

## 完成内容

### 1. 论文清单

- 研究 PDF：29 个，全部进入 `paper_files.tsv`。
- 综述 PDF：7 个，全部排除在研究论文主表之外。
- 规范论文：28 篇。
- 确认的精确重复：1 组、2 个文件、相同 SHA-256。
- 疑似重复：0 组；未仅凭相似文件名合并。
- 每个文件记录相对路径、大小、SHA-256、文件名线索、PDF metadata 线索和处理状态。
- ID 重跑策略：复用已有路径的 `file_id` 和已有内容哈希的 `paper_id`，新增文件不会使已有 ID 自动重排。

### 2. 数据标准与工具

- 定义 9 张表：`paper_files`、`papers`、`experiments`、`samples_timepoints`、`perturbations`、`accessions`、`evidence`、`unresolved_issues`、`literature_experiment_catalog`。
- 建立缺失码、自产数据、周期阶段证据、重复关系、在线核验状态等受控词表。
- CLI 支持 `inventory`、`validate`、`summary`。
- 校验覆盖表头、必填字段、主外键、唯一键、论文文件覆盖、综述排除、accession 类型及 `evidence_ids`。
- 使用标准库实现主要逻辑；轻量依赖 `pypdf` 仅用于 PDF metadata/有界文本读取，已写入 `requirements.txt`。

### 3. 试点论文与选择理由

- `paper_id`：`P0008`。
- DOI：`10.1126/science.aao6135`。
- 选择理由：14 页 PDF 文本可可靠提取，并同时包含同步化、分钟级采样、mAID/auxin 扰动、Hi-C 和 GEO accession。
- 覆盖范围：2 个代表性实验、10 个样本/时间点、1 个扰动、4 个归档层级记录、7 条证据和 10 行试点宽表。
- 本轮不是该论文的穷举提取；没有展开全部 60 个 GEO 样本、全部 condensin 条件或全部数据模态。

### 4. 试点关键事实

- 物种/样本：*Gallus gallus* DT40。
- 同步化：CDK1as chemical-genetic system；`1NM-PP1` 处理 10 h 阻断于 G2；洗脱定义为时间零点。
- 代表性采样：0、2.5、5、7.5、10、15、30、60 min。
- 2.5 min 的周期阶段未在目标证据段得到独立标签，故保留 `unknown`，没有凭分钟数推断。
- 扰动：SMC2-mAID + OsTIR1/auxin；G2 阻断期间处理 3 h，作者报告 SMC2 低于 5%，设计上同时破坏 condensin I 和 II。
- 数据：论文声明 Hi-C 数据归档为 `GSE102740`。

### 5. 表行数与缺失情况

| 表 | 行数 | 说明 |
|---|---:|---|
| `paper_files` | 29 | 完整覆盖研究 PDF |
| `papers` | 28 | 1 篇试点已核验，其余 27 篇保持未核验 |
| `experiments` | 2 | WT同步时间序列和SMC2耗竭代表实验 |
| `samples_timepoints` | 10 | 8个WT时间点、2个SMC2代表时间点 |
| `perturbations` | 1 | SMC2 mAID急性降解 |
| `accessions` | 4 | GEO Series、BioProject、SRA Study和未展开Run占位 |
| `evidence` | 7 | 5条本地论文证据、1条NCBI GEO证据、1条ENA失败查询证据 |
| `unresolved_issues` | 3 | ENA连接、Run映射、试点非穷举 |
| `literature_experiment_catalog` | 10 | 用户宽表试点 |

关键缺失：27 篇非试点论文的正式书目信息仍为 `NR/NOT_FOUND`；10 个试点样本的 Taxonomy ID 未在线核验；论文未在目标段报告同步化剂量；Run accession 和 ENA 文件链接未获得。所有缺口均使用受控缺失码，没有用空字符串或猜测值掩盖。

## 涉及文件

### 新增

- `requirements.txt`
- `configs/catalog_schema.json`
- `configs/controlled_vocab.json`
- `src/__init__.py`
- `src/literature_catalog/__init__.py`
- `src/literature_catalog/catalog.py`
- `src/literature_catalog/cli.py`
- `src/literature_catalog/README.md`
- `docs/data_dictionary.md`
- `docs/verification_protocol.md`
- `data/curated/paper_files.tsv`
- `data/curated/papers.tsv`
- `data/interim/pilot/experiments.tsv`
- `data/interim/pilot/samples_timepoints.tsv`
- `data/interim/pilot/perturbations.tsv`
- `data/interim/pilot/accessions.tsv`
- `data/interim/pilot/evidence.tsv`
- `data/interim/pilot/unresolved_issues.tsv`
- `data/interim/pilot/literature_experiment_catalog.tsv`
- `reports/per_paper/P0008_pilot.md`
- `tests/test_catalog.py`
- `ans_qes/result1.md`

### 修改

- `.gitignore`：允许跟踪 `data/interim/pilot/**`，其他中间数据仍保持忽略。

没有修改、移动、重命名或复制 `文献/` 下的 PDF。

## 命令记录

主要命令及结果摘要：

```text
python -m pip install pypdf
  -> installed pypdf 6.14.2

python -m src.literature_catalog.cli --root . inventory
  -> research_pdf=29, review_pdf=7, canonical_papers=28,
     exact_duplicate_groups=1

python -m src.literature_catalog.cli --root . validate
  -> ok=true, errors=0, warnings=0

python -m unittest discover -s tests -v
  -> Ran 6 tests, OK

python -m src.literature_catalog.cli --root . summary
  -> 输出9张表的行数和受控缺失码统计
```

另对 4 篇候选论文只做了关键词页码命中筛查，随后仅对试点论文的目标页做有界文本提取。官方在线查询限定为 `GSE102740` 及其关系记录，没有批量查询全部论文。

## 验证情况

1. 29 个研究 PDF 路径与 `paper_files.tsv` 一一对应；7 篇综述未进入主表。
2. 29 个 PDF 在清单生成后再次计算 SHA-256，`mismatches=0`。
3. 由于仓库没有进入本轮前的全量历史哈希清单，只能证明“首次清单基线到本轮结束”未变化，不能声称拥有更早的历史基线。
4. 表头、必填字段、主外键、唯一键、accession 类型和证据引用验证通过。
5. 6 个自动化测试全部通过，失败 0、跳过 0。
6. 重跑 `inventory` 后仍得到 29 个文件、28 篇规范论文和同一重复组，已核验的 `P0008` 书目信息得到保留。
7. 除 `.git` 内部对象外，仓库未新增超过 5 MB 的非文献文件；未新增测序数据、PDF 副本或日志洪泛。
8. `GSE102740`、`PRJNA398543`、`SRP115572` 的格式和官方 GEO 关系已验证；Run 级记录没有冒充在线已验证。

## 官方在线查询

- 查询日期：2026-07-13。
- NCBI GEO：实际打开 `GSE102740` 官方 Series 页，确认公开状态、60 个样本、`PRJNA398543` 和 `SRP115572` 关系。
- NCBI BioProject/SRA 详情页：直接抓取未成功；关系只按 GEO 官方 Relations 字段记录。
- EMBL-EBI ENA Portal API：针对 `SRP115572` 的单一 `read_run` 查询连接失败；已记录失败，不解释为数据不存在。
- 没有下载 192.7 GB GEO 归档或任何 FASTQ/BAM/CRAM。

## 项目规则符合情况

- 可复现性：schema、词表、CLI、命令和依赖均已记录。
- 原始数据只读：PDF 未改动，清单后全量哈希复核一致。
- 可追溯性：试点关键记录通过 `evidence_ids` 回到 PDF 页码或官方数据库页面。
- 模块化：清单、校验和摘要逻辑位于可复用模块，未写入 notebook。
- 路径：使用仓库相对路径和 `--root` 参数，无本机绝对路径硬编码。
- 测试：核心 accession、schema、清单重复关系和全目录验证均有自动测试。
- 低上下文：先做文件/关键词摘要，只读取单篇试点的目标页，没有批量展开 PDF 全文或大型数据库响应。
- 文档：新增中文数据字典、核验规程、模块说明和逐篇试点报告。
- 大文件：未下载或提交原始测序数据。
- 本轮不涉及建模、benchmark 或统计推断，因此相关数据泄漏/公平性规则不适用。

## 风险与注意事项

1. ENA Portal API 未连通，SRR/ERR/DRR、ENA项目页和FASTQ下载字段仍待官方服务恢复后核验。
2. `GSE102740` 有60个GEO样本；本轮宽表只有10行代表性记录，不能用于声称该论文已完整整理。
3. 试点中的GEO Series是实验级总括映射，尚未建立GSM/SRS/SRX/SRR到时间点的逐项关系。
4. 其余27篇规范论文只有文件级清单，题名、DOI、物种和实验信息均未逐篇核验。
5. 两份2015 PDF只确认“文件内容完全相同”；尚未在本轮核验其正式题名与DOI。
6. `pypdf` 安装在当前Python环境中；其他环境需按 `requirements.txt` 安装。
7. 试点显示晚期样本可能包含有/无nocodazole的平行条件，下一轮批量前应确认是否增加显式 `condition_id`/`batch_id` 字段。

## Commit 建议

```text
p1: 建立论文清单、数据标准与单篇试点
```

仅为建议，本轮未执行 commit 或 push。

## 后续建议

请先人工审查以下三点：

1. 宽表的一行粒度是否符合后续使用习惯。
2. 是否在批量处理前为 `samples_timepoints` 增加显式 `condition_id`、`replicate_id` 和 `batch_id`。
3. 是否接受“官方API不可用时保留失败状态，后续重试”的处理方式。

用户确认本轮结果后，可选择先提交本轮，或明确要求生成下一轮 prompt；本轮没有创建 `prompt2.md`。

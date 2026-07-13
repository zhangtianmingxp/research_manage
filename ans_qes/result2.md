# Result 2

## 对应 Prompt

- `ans_qes/prompt2.md`

## 执行摘要

本轮完成schema v1→v2迁移、官方轻量元数据抓取与离线构建分离，并对P0008 / GSE102740的60个GSM进行了逐项处置。NCBI SRA与EMBL-EBI ENA分别返回1,290个唯一Run，两个集合完全一致；全部Run均通过官方experiment/sample alias唯一连接到GSM。ENA API返回2,580个paired-end FASTQ文件字段，URL、字节数和MD5覆盖率均为100%。未下载任何FASTQ、SRA、COOL、BAM/CRAM或GEO 192.7 GB归档。

最终目录校验为0错误、0警告，14项离线自动化测试全部通过。连续构建得到相同宽表SHA-256。项目仍只完成P0008试点，其余27篇规范论文未处理。

## 完成内容

- 完成schema v1→v2安全迁移及condition、replicate、batch、archive sample、accession relation、file与query provenance建模。
- 完成GSE102740全部60个GSM到60个SRX及1,290个Run的官方关系映射。
- 完成2,580条ENA FASTQ文件字段整理、数量对账、离线宽表生成、文档和测试更新。

## 涉及文件

新增/修改内容集中在`configs/`、`src/literature_catalog/`、`data/interim/pilot/`、`docs/`、`reports/`、`tests/`与本结果文件。完整分组清单见下文“创建与修改文件”。

## 命令记录

执行了`validate`迁移前基线、`fetch`官方元数据抓取、`build`离线构建、重复`build`哈希核验及`unittest`离线测试。完整命令见下文“执行命令与验证”。

## 验证情况

最终schema校验0错误、0警告；14项测试全部通过；NCBI/ENA Run集合差集为0；连续构建宽表哈希一致；29个PDF哈希无变化。

## 风险与注意事项

R1/R2类型、日期型batch及两个人源HeLa样本的数据归属仍需人工裁决。文件链接只确认由ENA API返回，未执行正文下载或全量可达性检查。项目仍未完成其余27篇论文。

## Schema v1 → v2与迁移结果

新增实体：

- `conditions`：显式保存作者条件标签、基因型、同步化、处理与周期阶段。
- `replicates`：保存R1/R2等作者原始标签；当前类型统一保守记为`UNRESOLVED`。
- `batches`：日期型alias仅作为`candidate`批次，不升级为已验证批次。
- `archive_samples`：每个GSM一行，连接BioSample、SRS、SRX、条件、重复、批次和Run计数。
- `accession_relations`：表示Series→Sample、Sample→Experiment、Experiment→Run与镜像关系。
- `files`：一个Run的一个FASTQ文件一行。
- `source_queries`：保存endpoint、参数、查询时间、状态、响应哈希、行数、快照、分页和重试。

`samples_timepoints`和宽表增加condition、replicate、batch及归档外键。宽表粒度固定为：

```text
paper × experiment × condition × replicate × batch × sample/timepoint
× archive sample × experiment accession × run × FASTQ file
```

迁移保留了v1的全部10个`ST-P0008-001`至`ST-P0008-010`、2个原实验ID、原扰动ID、原accession记录ID及7个证据ID。新增CAP-H、CAP-H2、HeLa比较实验和CAP-H/CAP-H2扰动；`prompt1.md`、`result1.md`与PDF未被覆盖。详细映射见`docs/schema_migration_v1_to_v2.md`。

## 官方查询与快照

统一查询时间为`2026-07-13T15:08:03+00:00`。4次请求均为HTTP 200，`retry_count=0`，完整分页状态均为`yes`。

| 查询 | 官方来源/用途 | 响应字节 | 返回记录 | SHA-256 |
|---|---|---:|---:|---|
| `Q0001` | NCBI GEO MINiML，GSE102740 family | 7,753 | 60 GSM | `500bdc596df52cc29ca92f0c8e746b4c4892401dd2f9a4846be8553d51045775` |
| `Q0002` | NCBI SRA ESearch，SRP115572 | 1,634 | 60 Entrez UID | `a602d809c9de8df5e5ee2712f060ac01b4202fb2ab1c9f0be669db8dbbb873ac` |
| `Q0003` | NCBI SRA EFetch，60个experiment package | 4,934,774 | 60 Experiment | `c613b80722d5b9f313e589caa3b9f571f9e5dfae973b01d29298474c86fd98a8` |
| `Q0004` | EMBL-EBI ENA Portal `read_run` file report | 518,565 | 1,290 Run | `d9cbae729b7ae95a53418de8d1dd0ba2551faac1e6f6239f3168316adc05a007` |

快照位于`data/interim/pilot/source_metadata/`。最大文件为4,934,774字节，低于5 MB上限。GEO压缩响应同时提取为254,709字节的MINiML XML。查询参数与endpoint全文见`data/interim/pilot/source_queries.tsv`。

## 60个GSM处置与分层统计

- 唯一GSM：60；处置状态全部为`mapped`；原始title/alias保留率100%。
- 物种：*Gallus gallus* 58；*Homo sapiens* 2。
- GEO平台：`GPL16133` 30；`GPL23499` 28；`GPL11154` 2。
- GEO原始phase：G2 15；Prophase 15；Prometaphase 27；NS 2；`NR` 1。
- GEO原始genotype：WT 23；CAPH-AID 14；CAPH2-AID 14；SMC2-AID 9。
- 作者重复标签：R1 38；R2 20；`NR` 2。R1/R2的生物/技术属性没有猜测。
- 日期型batch候选：51个样本可从alias保留日期候选，9个为`NR`；所有日期仍为`candidate`。
- 数据归属：58个鸡源样本为`yes`；两个HeLa样本为`unclear`。正文称其为此前已报告数据的更深测序后重新分析，现有证据不足以在“复用生物样本”和“新测序Run”之间精确裁决。

`G2p/G2n`、`sG2`、`PMphase`及所有日期/分钟/R标签均保留原文。标准化阶段来自GEO官方Characteristics或论文证据，不由分钟数推断。证据不足时每个GSM保持独立condition，因此不会把30 min的不同条件静默合并。

## NCBI / ENA / File对账

- NCBI唯一SRA Sample：60。
- NCBI唯一Experiment：60。
- NCBI唯一Run：1,290。
- ENA唯一Run：1,290。
- NCBI∩ENA：1,290；仅NCBI：0；仅ENA：0。
- GSM无Run：0；GSM多Run：31；单Run GSM：29。
- Run无唯一GSM映射：0。
- 规范`accessions`真实Run：1,290；宽表唯一Run：1,290。
- FASTQ文件记录：2,580，全部为paired-end两个文件。
- ENA API URL覆盖率：100%；文件大小覆盖率：100%；MD5覆盖率：100%。
- HEAD/可达性抽样：未执行。API是否返回与实际可达性已分列；所有文件的`reachability_status=not_checked`，未对大型文件发起正文请求。

机器对账见`reports/P0008_accession_reconciliation.tsv`，人类可读报告见`reports/P0008_accession_reconciliation.md`。所有计数均由代码生成。

## 规范表、宽表与哈希

| 表 | 行数 | SHA-256 |
|---|---:|---|
| `archive_samples.tsv` | 60 | `0ae7a8cbc5202d00d3af461ddccd2b7d7f61791fd2599fec516da4163e321c74` |
| `accessions.tsv` | 1,474 | `5660a4a9bdeee35ce10dc2543014401aba6e95ef1d620717251943351dfe5580` |
| `accession_relations.tsv` | 1,471 | `7c0d1b6f04fe9263426c130d57d3e4e0aac1737bd02579d310dd80effb2c1edf` |
| `files.tsv` | 2,580 | `f8c88037d9c36fd467a589cf603334d90f4d1227bf0050e7c320c5e6e83d572e` |
| `literature_experiment_catalog.tsv` | 2,580 | `5f708d55c99c9b84006e9335cbf30eb95925b578850c5c8c73ed562e3b56d819` |

连续运行两次`build`的宽表SHA-256均为`5f708d55c99c9b84006e9335cbf30eb95925b578850c5c8c73ed562e3b56d819`。宽表行数等于文件表行数，`catalog_row_id`和`file_id`均唯一，没有出现多表join笛卡尔膨胀。

关键缺失/保守值：GEO phase缺失1/60；作者重复标签缺失2/60；正式replicate类型未裁决60/60；日期batch候选缺失9/60；HeLa自产状态不明确2/60；Run、文件URL、大小和MD5缺失均为0。

## 创建与修改文件

主要新增：

- `configs/pilots/P0008.json`
- `src/literature_catalog/metadata.py`
- `src/literature_catalog/pilot.py`
- `data/interim/pilot/{conditions,replicates,batches,archive_samples,accession_relations,files,source_queries}.tsv`
- `data/interim/pilot/source_metadata/`中的轻量官方快照
- `docs/schema_migration_v1_to_v2.md`
- `reports/P0008_accession_reconciliation.{md,tsv}`
- `tests/fixtures/`

主要修改：

- `configs/catalog_schema.json`、`configs/controlled_vocab.json`
- `src/literature_catalog/catalog.py`、`src/literature_catalog/cli.py`
- P0008规范表、证据表、问题表及宽表
- `docs/data_dictionary.md`、`docs/verification_protocol.md`
- `reports/per_paper/P0008_pilot.md`
- `README.md`、`tests/test_catalog.py`

## 执行命令与验证

主要命令：

```powershell
python -m src.literature_catalog.cli --root . validate
python -m src.literature_catalog.cli --root . fetch
python -m src.literature_catalog.cli --root . build
python -m unittest discover -s tests -v
```

验证结果：

- 迁移前：0错误、0警告；9张v1表均成功读取。
- 最终：0错误、0警告；16张schema v2表通过表头、必填、主外键、accession类型、受控词表、证据和Run/File关系校验。
- 测试：14通过，0失败，0跳过；测试不访问网络。
- 覆盖：官方格式解析、空响应、查询清单/分页、迁移ID保留、GSM多Run、Run唯一GSM、关系集合、宽表防笛卡尔积与重复构建哈希。
- 29个PDF逐文件重算SHA-256，与`paper_files.tsv`全部一致；未修改`文献/`。
- 未新增超过5 MB的元数据、日志或缓存文件；未下载原始测序或处理数据。

## PROJECT_RULES.md符合性

- 原始PDF保持只读，生成物写入`data/interim/pilot/`与`reports/`。
- 抓取、解析、构建、校验和报告分层；路径与endpoint配置化。
- 查询溯源、响应哈希、重试、快照和确定性输出均已记录。
- 核心测试离线，不依赖实时数据库。
- 不调用远程LLM API，不处理P0008之外论文，不commit、不push。
- README仍明确声明项目未完成。

## 未解决问题与需要用户裁决的选择

1. R1/R2应判定为生物重复、技术重复，还是不同实验中含义不同；当前全部保留为`UNRESOLVED`。
2. 日期型alias能否作为正式batch；当前只作为`candidate`。
3. `GSM2745897`与`GSM2745898`应标为`no_reused`、新测序自产数据或更细的混合类别；当前为`unclear`。
4. 最终用户宽表是否继续采用“一行一个FASTQ文件”，还是另提供Run粒度视图；当前文件粒度最能保持URL/大小/MD5一一对应。
5. schema v1历史ENA失败占位记录`AC-P0008-004`为保留ID而继续存在，但不计入真实Run；后续可在得到用户同意后标记为历史查询记录并从accession实体迁出。

## Commit建议

建议但未执行：

```text
p2: 完成P0008全量GSM-Run映射与schema v2迁移
```

## 下一步建议

先人工抽查60个GSM中的高风险标签与HeLa归属，并确认重复、批次和宽表粒度选择。确认schema v2后，再按小批次处理其余27篇规范论文。本轮未创建`prompt3.md`。

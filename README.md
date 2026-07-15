# 同步化与扰动研究论文实验数据目录

> **项目状态：进行中，尚未完成。**
>
> 当前已完成29个研究论文 PDF 的文件清单、schema v2、2篇论文的Run/File级公共元数据试点（P0008、P0009），以及另外2篇论文（P0001、P0012）的项目级小批量核验。除P0008和P0009外，其余论文尚未逐篇完成SRR/ERR/DRR、ENA下载链接及样本到Run/File映射核验。本仓库当前结果不能作为最终完整数据集使用。

## 项目目标

本项目整理本地研究论文中的实验设计和公开数据归档信息，重点建立以下可核验关系：

```text
论文 → 实验 → 样本/同步化/时间点 → 细胞周期阶段
     → 扰动技术/靶标/预期与观察效果
     → Project/Study/Sample/Experiment/Run → 官方下载链接
```

最终目标是形成统一、用户友好、可筛选的汇总表，并保证每个关键字段都能回溯到论文页码、补充材料或权威数据库记录。禁止根据常识、相似论文或编号格式猜测缺失信息。

完整研究设计见 [project_plan.md](project_plan.md)，科研与工程约束见 [PROJECT_RULES.md](PROJECT_RULES.md)。

## 当前进度

### 已完成

- 盘点 `文献/研究/` 下29个研究论文 PDF。
- 排除 `文献/综述/` 下7篇综述，不将其作为最终实验事实证据。
- 通过 SHA-256 发现1组完全相同的重复 PDF，因此29个文件对应28篇规范论文。
- 定义schema v2的条件、重复、批次、归档样本、accession关系、文件和查询溯源实体。
- 实现可重复运行的清单、官方轻量元数据抓取、离线构建、验证和摘要 CLI。
- 完成1篇全量试点论文：Gibcus et al., 2018, *Science*，DOI `10.1126/science.aao6135`。
- P0008试点逐项保留60个GSM，并通过官方字段映射到60个BioSample/SRA Experiment和1,290个Run。
- NCBI与ENA Run集合完全一致；ENA API提供2,580条FASTQ文件记录及URL、大小和MD5。
- 完成P0008的223条高风险语义审计；R1/R2、日期alias和具体HeLa Run来源在证据不足处保留未决。
- 同一规范事实离线生成1,290行Run视图和2,580行File视图；旧版10个样本/时间点ID均保留。
- schema v2.1准入结论为`ready_with_documented_gaps`，建议后续每轮处理1–3篇。
- 第4轮完成3篇项目级小批量核验：P0001（`E-MTAB-1948`/`ERP004055`）、P0009（`GSE129997`/`PRJNA533460`/`SRP192917`）、P0012（`GSE168251`/`PRJNA706679`）。
- 第5轮将P0009推进到Run/File级：75个GSM、120个Run、195个FASTQ链接，且保留P0008的1,290个Run/2,580个FASTQ文件视图不变。

第一轮完整执行记录见 [ans_qes/result1.md](ans_qes/result1.md)，P0008试点说明见 [reports/per_paper/P0008_pilot.md](reports/per_paper/P0008_pilot.md)，第4轮小批量摘要见 [reports/batch_round4_summary.md](reports/batch_round4_summary.md)，P0009 Run/File级报告见 [reports/per_paper/P0009_run_file_pilot.md](reports/per_paper/P0009_run_file_pilot.md)。

### 尚未完成

- 除P0008、P0009与P0001/P0012外，其余24篇规范论文的正式题名、DOI、物种和实验设计尚未逐篇核验。
- 尚未系统下载和检查所有论文的补充材料。
- P0001与P0012仍停留在项目级，尚未展开完整 GSM/SRS/SRX/SRR/ERR/DRR 关系。
- 除P0008与P0009外，其余论文尚未逐Run核验 ENA/EMBL-EBI 文件链接、文件大小和MD5。
- 当前全局宽表覆盖P0008与P0009，不是28篇规范论文的最终汇总表。
- P0008的R1/R2重复类型、日期型alias批次含义、HeLa文库及逐Run测序来源仍无充分证据，已显式审计并待人工复核。

## 数据与 GitHub 策略

原始论文位于本地：

```text
文献/
├── 研究/
└── 综述/
```

整个 `文献/` 目录已由 `.gitignore` 排除，不会上传到 GitHub。FASTQ、BAM、CRAM、HDF5、Hi-C矩阵、下载归档、缓存和日志等大型或可再生成文件也默认忽略。

Git 仓库保留的是：

- 论文文件指纹和相对路径清单；
- 小型规范化元数据和试点表；
- 字段字典、核验规程和证据记录；
- 可重复运行的代码、配置和测试。

从 GitHub 克隆本仓库后不会自动获得论文 PDF。若要重新生成清单或继续逐篇整理，需要自行把合法获取的文献放回上述目录。请勿提交无权再分发的论文或大型原始数据。

## 仓库结构

```text
.
├── project_plan.md                 # 项目目标、范围和阶段计划
├── PROJECT_RULES.md                # 科研工程与可复现性规则
├── ans_qes/                        # 每轮 prompt/result 记录
├── configs/
│   ├── catalog_schema.json         # 机器可读表结构和关系
│   ├── controlled_vocab.json       # 缺失码与受控词表
│   └── pilots/                     # 试点/小批量官方端点与期望计数
├── data/
│   ├── curated/                    # 论文/文件规范清单
│   └── interim/pilot/              # 当前单篇试点表
├── docs/
│   ├── data_dictionary.md          # 全字段数据字典
│   └── verification_protocol.md    # 人工与数据库核验规程
├── reports/per_paper/              # 逐篇核验摘要
├── src/literature_catalog/         # 清单、校验和摘要模块
├── tests/                          # 自动化测试
└── 文献/                           # 本地PDF，不进入Git
```

## 环境准备

建议使用 Python 3.11 或更高版本：

```powershell
python -m pip install -r requirements.txt
```

当前仅需要轻量 PDF 解析依赖 `pypdf`。项目不会调用 OpenAI、Anthropic 或其他远程 LLM API。

## 常用命令

在仓库根目录运行：

```powershell
# 扫描本地PDF并更新论文清单
python -m src.literature_catalog.cli --root . inventory

# 检查表头、主外键、缺失码、accession类型和证据引用
python -m src.literature_catalog.cli --root . validate

# 查看各表行数和缺失码统计
python -m src.literature_catalog.cli --root . summary

# 在线抓取官方轻量元数据（不下载reads）
python -m src.literature_catalog.cli --root . fetch

# 仅使用保存的快照离线重建规范表和宽表
python -m src.literature_catalog.cli --root . build

# 运行自动化测试
python -m unittest discover -s tests -v
```

注意：当前 schema 把研究 PDF 数量基线设为29、综述设为7。GitHub 克隆版本没有 `文献/`，直接运行 `inventory` 会因缺少本地论文而停止；`validate` 和测试则依赖仓库中已有的小型表格。

## 主要数据产物

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `data/curated/paper_files.tsv` | 29个本地PDF的路径、大小和SHA-256 | 已完成文件级盘点 |
| `data/curated/papers.tsv` | 28篇规范论文记录 | P0008/P0009已做Run/File级试点；P0001/P0012完成项目级核验 |
| `data/interim/pilot/experiments.tsv` | 试点与小批量实验设计 | P0008全量试点、P0009 Run/File试点，加round4代表性实验 |
| `data/interim/pilot/archive_samples.tsv` | GEO样本及BioSample/SRX处置 | 含P0008的60个GSM与P0009的75个GSM |
| `data/interim/pilot/samples_timepoints.tsv` | 同步化、采样点与周期阶段 | 含P0008全量与P0009显式release时间映射 |
| `data/interim/pilot/perturbations.tsv` | 扰动技术、靶标和效果 | P0008代表性扰动加P0012 CTCF/triptolide扰动 |
| `data/interim/pilot/accessions.tsv` | GEO/BioProject/SRA/ENA层级 | 含P0008的1,290个Run和P0009的120个Run |
| `data/interim/pilot/files.tsv` | ENA API返回的FASTQ文件字段 | 共2,775条，不含文件正文 |
| `data/interim/pilot/source_queries.tsv` | endpoint、参数、状态、哈希和重试 | 含P0008查询、round4快照和P0009的GEO/SRA/ENA快照 |
| `data/interim/pilot/semantic_review.tsv` | 逐记录高风险语义审计 | 含P0008审计、round4边界和P0009语义规则 |
| `data/interim/pilot/evidence.tsv` | 字段级论文与数据库证据 | 含P0008、round4和P0009 Run/File级证据 |
| `data/interim/pilot/unresolved_issues.tsv` | 缺失、冲突和待裁决问题 | 含P0008、round4及P0009剩余缺口 |
| `data/interim/pilot/round4_experiment_design.tsv` | 第4轮用户友好汇总 | 3篇小批量论文，项目级核验 |
| `data/interim/pilot/P0009_run_file_catalog.tsv` | P0009用户友好Run/File表 | 195行，覆盖75个GSM与120个Run |
| `data/interim/pilot/literature_experiment_catalog_runs.tsv` | 一行一个Run | 共1,410行（P0008 1,290 + P0009 120） |
| `data/interim/pilot/literature_experiment_catalog_files.tsv` | 一行一个FASTQ文件 | 共2,775行（P0008 2,580 + P0009 195） |
| `data/interim/pilot/literature_experiment_catalog.tsv` | 兼容宽表 | 与File视图一致，非最终表 |

字段定义和关系以 [docs/data_dictionary.md](docs/data_dictionary.md) 与 `configs/catalog_schema.json` 为准。

## 缺失值与“不瞎编”原则

项目不使用无含义的空白来伪装完整性：

| 值 | 含义 |
|---|---|
| `NR` | 论文或补充材料未报告 |
| `NA` | 对当前记录不适用 |
| `NOT_FOUND` | 已按规程检查但未找到 |
| `UNRESOLVED` | 来源冲突或暂时不能裁决 |
| `RESTRICTED` | 受控访问、未公开或受限制 |

accession 格式正确不代表数据库记录已核验；格式状态和在线验证状态必须分列。细胞周期阶段也不能仅凭采样分钟数推断。

## 交互式推进方式

本项目采用人工控制的逐轮流程：

```text
project_plan.md
  → ans_qes/promptN.md
  → 用户审查并明确同意执行
  → ans_qes/resultN.md
  → 用户审查
  → commit建议/用户确认提交
  → 停止
```

不会自动执行新生成的 prompt、自动进入下一轮、自动 commit 或自动 push。当前第5轮执行后应停在等待结果审查状态；不会自动生成 `prompt6.md`。

## 下一阶段建议

在批量整理剩余论文前，应先人工审查试点宽表和以下设计问题：

1. 审查当前“一行一个FASTQ文件”的宽表粒度是否满足最终使用习惯。
2. 裁决R1/R2是生物重复还是技术重复，以及日期alias能否升级为正式batch。
3. 裁决两个人源HeLa样本应标为复用数据、重测数据还是其他类别。
4. 以P0009为第二个完整样板后，优先把P0001或P0012推进到轻量Run metadata，再决定是否分批处理剩余24篇规范论文。

确认数据模型后，再分批处理剩余论文，避免在错误字段设计上扩大工作量。

## 重要声明

- 这是未完成的科研数据整理项目，不是已经发表或经过同行评审的数据集。
- 当前表格中的试点记录仍需人工复核后才能用于正式研究。
- 论文版权和数据库使用条款由数据使用者自行遵守。
- 本仓库当前未声明软件或数据许可证；在明确许可证前，不应假定可自由再分发全部内容。

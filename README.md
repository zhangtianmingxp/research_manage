# 同步化与扰动研究论文实验数据目录

> **项目状态：进行中，尚未完成。**
>
> 当前仓库已经完成 29 个研究论文 PDF 的文件清单、28 篇规范论文记录、schema v2 数据模型，以及 4 篇试点/小批量论文的公共归档元数据展开：P0008、P0009、P0012、P0001。其余论文尚未逐篇完成实验设计、同步化时间轴、扰动设计、Run/File 和证据级核验。本仓库当前结果不能作为最终完整数据集使用。

## 项目目标

本项目整理本地研究论文中的实验设计和公开数据归档信息，目标是建立可人工核验的关系链：

```text
论文 → 实验 → 样本/同步化/采样点/细胞周期阶段
     → 扰动技术/靶标/预期与观测效果
     → Project/Study/Sample/Experiment/Run → 官方下载链接
```

所有关键字段都应能追溯到论文、补充材料或权威数据库记录。禁止根据常识、相似论文或编号格式补写未知信息。

完整研究设计见 [project_plan.md](project_plan.md)，科研与工程约束见 [PROJECT_RULES.md](PROJECT_RULES.md)。

## 当前进度

已完成：

- 盘点 `文献/研究/` 下 29 个研究论文 PDF，并排除 `文献/综述/` 下 7 篇综述作为最终实验事实来源。
- 识别 1 组完全重复 PDF，因此形成 28 篇规范论文记录。
- 建立 schema v2/v2.1 风格的规范表：论文、实验、条件、重复、批次、样本时间点、扰动、accession、文件、证据、问题和宽表。
- P0008：60 个 GSM、1,290 个 Run、2,580 条 FASTQ 元数据链接。
- P0009：75 个 GSM、120 个 Run、195 条 FASTQ 元数据链接。
- P0012：44 个 GEO 样本、102 个 Run、182 条 FASTQ 元数据链接；明确区分 auxin/CTCF 扰动、triptolide/转录抑制与 ChIP 检测靶点。
- P0001：从 `E-MTAB-1948` / `ERP004055` 推进到 13 个 ENA Run、26 条 paired-end FASTQ 元数据链接；样本阶段仍为轻量解析。
- 全局 file 级宽表目前为 2,983 行；run 级视图为 1,525 行。

仍未完成：

- 除上述 4 篇外，其余 24 篇规范论文尚未做完整实验设计和 Run/File 级核验。
- P0001 的精确同步化起点、处理时长、样本表映射仍需补充材料进一步核验。
- P0012 中 `PRJNA706679` 与 ENA run 行返回的 `PRJNA706396` / `PRJNA706676` 项目层级关系仍待人工复核。
- P0008/P0009/P0012/P0001 的部分重复类型、批次含义、扰动验证细节仍保留为 `UNRESOLVED` 或待人工审查。

## 主要产物

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `data/curated/paper_files.tsv` | 本地 PDF 文件清单 | 29 个研究论文 PDF |
| `data/curated/papers.tsv` | 规范论文记录 | 28 篇 |
| `data/interim/pilot/archive_samples.tsv` | 样本与归档样本映射 | 192 行 |
| `data/interim/pilot/accessions.tsv` | Project/Study/Sample/Experiment/Run 等编号 | 1,942 行 |
| `data/interim/pilot/files.tsv` | ENA 返回的 FASTQ URL、大小、MD5 | 2,983 行，不含文件正文 |
| `data/interim/pilot/literature_experiment_catalog.tsv` | file 级兼容宽表 | 2,983 行 |
| `data/interim/pilot/literature_experiment_catalog_runs.tsv` | run 级宽表 | 1,525 行 |
| `data/interim/pilot/P0009_run_file_catalog.tsv` | P0009 用户友好 Run/File 表 | 195 行 |
| `data/interim/pilot/P0012_run_file_catalog.tsv` | P0012 用户友好 Run/File 表 | 182 行 |
| `data/interim/pilot/P0001_light_catalog.tsv` | P0001 轻量 Run/File 表 | 26 行 |
| `reports/per_paper/P0009_run_file_pilot.md` | P0009 Run/File 报告 | 已生成 |
| `reports/per_paper/P0012_run_file_pilot.md` | P0012 扰动导向 Run/File 报告 | 已生成 |
| `reports/per_paper/P0001_light_expansion.md` | P0001 轻量展开报告 | 已生成 |

字段定义以 [docs/data_dictionary.md](docs/data_dictionary.md) 和 [configs/catalog_schema.json](configs/catalog_schema.json) 为准。

## 数据与 GitHub 策略

原始论文和大型数据不进入 Git：

```text
文献/
  研究/
  综述/
```

`.gitignore` 已排除论文 PDF、FASTQ/BAM/CRAM/HDF5、Hi-C 矩阵、下载缓存和日志等大型或可再生成文件。仓库保留的是小型元数据、规范化表、证据记录、配置、代码和测试。

## 常用命令

```powershell
# 校验表结构、主外键、受控词表、accession 和证据引用
python -m src.literature_catalog.cli --root . validate

# 从已保存快照离线重建试点表
python -m src.literature_catalog.cli --root . build --config configs\pilots\P0008.json
python -m src.literature_catalog.cli --root . build --config configs\pilots\P0009.json
python -m src.literature_catalog.cli --root . build --config configs\pilots\P0012.json
python -m src.literature_catalog.cli --root . build --config configs\pilots\P0001.json

# 运行测试
python -m unittest discover -s tests
```

当前验证状态：

- `python -m src.literature_catalog.cli validate`：通过。
- `python -m unittest discover -s tests`：20 个测试通过。
- `python -m py_compile src\literature_catalog\round6.py src\literature_catalog\pilot.py`：通过。
- `git diff --check`：通过，仅有 Windows 换行提示。

## 推进方式

本项目采用人工控制的逐轮流程：

```text
project_plan.md → ans_qes/promptN.md → 用户审查并确认执行
→ ans_qes/resultN.md → 用户审查 → commit 建议/用户确认提交 → 停止
```

不会自动执行新 prompt，不会自动进入下一轮，不会自动 commit 或 push。

## 重要声明

- 这是未完成的科研数据整理项目，不是已发表或经同行评审的数据集。
- 当前表格仍需人工复核后才能用于正式研究。
- 论文版权和数据库使用条款由数据使用者自行遵守。
- 在明确许可证前，不应假定本仓库全部内容可自由再分发。

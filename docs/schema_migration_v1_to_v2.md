# Schema v1 → v2 迁移说明

## 迁移目标

v1把实验条件、重复、批次和归档层级压在 `samples_timepoints` 与 `accessions` 中，无法安全表达一个GSM对应多个Run。v2新增独立实体，并把在线抓取与离线构建分开。

## 迁移前基线

迁移前校验为0错误、0警告。9张表分别为：`paper_files` 29行、`papers` 28行、`experiments` 2行、`samples_timepoints` 10行、`perturbations` 1行、`accessions` 4行、`evidence` 7行、`unresolved_issues` 3行、宽表10行。

## 字段与实体映射

| v1位置 | v2位置 | 迁移规则 |
|---|---|---|
| `samples_timepoints`中的条件组合 | `conditions` | v1的10条记录生成`C-LEGACY-*`；GEO样本各保留独立condition，避免无证据合并 |
| 隐含在样本名中的R1/R2 | `replicates` | 保存作者原始标签；类型为`UNRESOLVED`，不猜测生物/技术重复 |
| 日期型样本alias | `batches` | 仅作为`candidate`保存，不升级为已验证批次 |
| GEO样本与SRA层级 | `archive_samples`、`accessions`、`accession_relations` | 通过GEO、NCBI SRA与ENA官方字段连接 |
| Run中的文件字段 | `files` | 一条FASTQ文件一行，URL保持ENA API原值 |
| 手工宽表 | `literature_experiment_catalog` | 由规范实体离线确定性生成，一行一个FASTQ文件 |
| 在线查询过程 | `source_queries` | 记录endpoint、参数、UTC时间、状态、响应哈希、行数、快照和重试 |

## 向后兼容

- 保留全部 `paper_id`、`file_id`、`experiment_id`、`sample_timepoint_id`、`perturbation_id` 和 `evidence_id`。
- v1的10个 `ST-P0008-001` 至 `ST-P0008-010` 原值保留，只补充condition、replicate、batch外键。
- v1的4个 `AC-P0008-*` 记录保留；历史ENA失败占位记录不冒充真实Run。
- `prompt1.md`、`result1.md` 和第1轮报告未覆盖。

## 原子性与复现

`fetch`只写官方元数据快照和查询清单；`build`先在内存中核对60个GSM及NCBI/ENA Run集合，再写规范表。NCBI与ENA集合不一致或GEO样本数不是60时，构建会在写表前失败。连续两次运行`build`应产生相同宽表SHA-256。

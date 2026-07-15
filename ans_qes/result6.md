# Result 6：P0012 Run/File 级扰动导向展开与 P0001 轻量 Run/File 展开

## 执行范围

本轮严格按 `ans_qes/prompt6.md` 执行，仅处理：

- `P0012`：`GSE168251` / `GSE168168` / `GSE168176` / `PRJNA706679`
- `P0001`：`E-MTAB-1948` / `ERP004055`

未处理其他论文，未下载 FASTQ/SRA/RAW tar 等大型文件，未生成 `prompt7.md`，未 commit。

## 本轮主要结果

### P0012

- 保存并解析官方轻量元数据：
  - `GSE168251_family.xml(.tgz)`
  - `GSE168168_family.xml(.tgz)`
  - `GSE168176_family.xml(.tgz)`
  - `PRJNA706679_runinfo.csv`
  - `PRJNA706679_ena_filereport.tsv`
- 展开结果：
  - 44 个 GEO sample
  - 102 个 Run
  - 182 条 FASTQ 元数据链接
- 新增用户友好表：
  - `data/interim/pilot/P0012_run_file_catalog.tsv`
- 新增逐篇报告：
  - `reports/per_paper/P0012_run_file_pilot.md`
- 扰动语义处理：
  - `auxin` 作为 CTCF-AID 降解处理；
  - `triptolide` 作为转录起始抑制处理；
  - `Pol II`、`CTCF`、`Rad21`、`input` 保留为 ChIP-seq 检测靶点或对照，不与扰动靶标混写。
- 保留未决问题：
  - 配置/声明中的 `PRJNA706679` 与 ENA run 行返回的 `PRJNA706396` / `PRJNA706676` 之间的项目层级关系需要人工复核。
  - rep 标签尚不能裁决为生物重复或技术重复。

### P0001

- 保存并解析官方轻量元数据：
  - `ERP004055_ena_filereport.tsv`
- 展开结果：
  - 13 个 ENA Run
  - 26 条 paired-end FASTQ 元数据链接
- 新增用户友好表：
  - `data/interim/pilot/P0001_light_catalog.tsv`
- 新增逐篇报告：
  - `reports/per_paper/P0001_light_expansion.md`
- 轻量样本解析：
  - 从 ENA alias 保守解析 HFF1/HeLa、M/G1/G1mid/early S 等阶段线索；
  - 未把 alias 解析等同于完整同步化协议；
  - 非 GEO 样本在 `gsm_accession` 字段使用 `NO_GEO_*` 明确占位标签，并在 notes 中声明不是 accession。
- 保留未决问题：
  - 精确同步化起点、处理时长、样本表映射和重复类型仍需补充材料进一步核验。

## 全局表更新

本轮将 P0012 与 P0001 纳入全局规范表和宽表，同时保留 P0008/P0009 已有结果。

当前核心计数：

| paper_id | Run 数 | FASTQ 元数据链接数 |
|---|---:|---:|
| P0008 | 1,290 | 2,580 |
| P0009 | 120 | 195 |
| P0012 | 102 | 182 |
| P0001 | 13 | 26 |

全局视图：

- `data/interim/pilot/accessions.tsv`：1,942 行
- `data/interim/pilot/files.tsv`：2,983 行
- `data/interim/pilot/literature_experiment_catalog.tsv`：2,983 行
- `data/interim/pilot/literature_experiment_catalog_files.tsv`：2,983 行
- `data/interim/pilot/literature_experiment_catalog_runs.tsv`：1,525 行

## 代码与测试变更

- 新增 `src/literature_catalog/round6.py`，从已保存官方快照离线构建 P0012/P0001。
- 更新 `src/literature_catalog/pilot.py`：
  - 支持 `P0012` 和 `P0001` 的 pilot config 分发；
  - 修复多 pilot 后 `source_queries` 的非数字 query id 排序；
  - 修复 P0008 builder 在保留非 P0008 行时误复用全局 archive/files/wide 残留的问题。
- 更新 `tests/test_catalog.py`，将 P0012/P0001 纳入 run/file 级全局断言。
- 更新 `README.md`，说明当前 4 篇 pilot 的真实覆盖范围和未完成边界。

## 验证结果

已通过：

```powershell
python -m src.literature_catalog.cli validate
python -m unittest discover -s tests
python -m py_compile src\literature_catalog\round6.py src\literature_catalog\pilot.py
git diff --check
```

结果：

- `validate`：通过，0 errors，0 warnings。
- `unittest`：20 个测试通过。
- `py_compile`：通过。
- `git diff --check`：通过；仅提示部分文件下次 Git 触碰时 LF/CRLF 可能转换。

## 本轮未做的事

- 未下载大型测序文件或 GEO RAW tar。
- 未将 P0012/P0001 的轻量字段扩写成未核验证据。
- 未处理 P0012/P0001 之外的新论文。
- 未生成 `prompt7.md`。
- 未 commit / push。

## 建议下一步

如果继续提速，下一轮建议进入“批次覆盖率优先”：

1. 每轮处理 3–5 篇论文；
2. 优先抓项目号、Study、Run/File、物种、样本名、assay 和显式同步化/扰动字段；
3. 对同步化精确起点、扰动预期效果、重复类型等高风险语义字段保守标记 `UNRESOLVED`；
4. 继续保持每轮生成 result 后停止，等待人工审查。

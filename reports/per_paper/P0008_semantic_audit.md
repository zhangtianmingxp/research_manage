# P0008 高风险语义审计

## 结论

P0008的60个GSM均已审计。官方PMC正文能证明所有time course均重复执行，但没有把R1/R2定义为生物或技术重复，因此58个有标签记录保持`UNRESOLVED`，2个缺失标签为`not_applicable`。51个日期型alias仅保留为候选batch，9个无日期记录为`not_applicable`。

`G2p/G2n/sG2/PMphase`保留作者原缩写，不扩写。正文支持部分晚期采样与“释放前30 min加入nocodazole”的总体背景，但不能把每个GSM标题无歧义地映射到药物状态；相关`30m`记录因此仅为`partially_verified`。

## HeLa分层归属

`GSM2745897`和`GSM2745898`的生物样本标为`reused_from_prior_study`，分析用途标为`reanalyzed_prior_data`。文库来源保持`UNRESOLVED`；样本层测序来源为`mixed_or_additional_unassigned`。其76个Run逐个保留`sequencing_generation_status=UNRESOLVED`，不按accession顺序或alias猜测新旧测序。

鸡源58个GSM依据本文同步化time course和官方提交记录，样本/文库标为`study_generated`、分析标为`primary_analysis`；具体Run的测序生成仍为`UNRESOLVED`，没有把Series归属无限外推。

## 历史与补充材料

旧`AC-P0008-004`已从活跃accession移除，并以`source_queries.Q0008.legacy_record_id`保留；原证据`E-P0008-007`改指查询历史。Science主补充PDF官方入口受限，PMC列表报告其大小107.5 MB，超过20 MB阈值，未下载。保存并解析的仅是157 KB级官方PMC XML正文快照。

逐记录结论见`data/interim/pilot/semantic_review.tsv`，数量对账见`reports/P0008_accession_reconciliation.*`。

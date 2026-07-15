# P0008 accession 数量对账

本报告由 `src.literature_catalog.pilot` 从保存的官方快照确定性生成。

- GEO GSM：60（Gallus gallus 58；Homo sapiens 2）
- NCBI SRA Experiment：60
- NCBI Run / ENA Run：1290 / 1290；集合差集均为0
- GSM无Run：0；GSM多Run：31
- ENA FASTQ文件记录：2580；URL、大小、MD5覆盖率均为100%
- 文件粒度视图：2580行；SHA-256 `2e7dcdf314a8a6444b73031844d0acafc81367d3b0b7436f51f06fe55bcf8bf3`
- Run粒度视图：1290行；SHA-256 `bb48c53965711b82c1eda9121c47b8e1bec8fcfa48cf65fc388c060b425a4193`

逐指标及分层计数见 `reports/P0008_accession_reconciliation.tsv`。兼容宽表仍指向文件粒度。文件URL仅保存ENA API返回值，未下载文件正文。

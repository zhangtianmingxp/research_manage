# P0008 accession 数量对账

本报告由 `src.literature_catalog.pilot` 从保存的官方快照确定性生成。

- GEO GSM：60（Gallus gallus 58；Homo sapiens 2）
- NCBI SRA Experiment：60
- NCBI Run / ENA Run：1290 / 1290；集合差集均为0
- GSM无Run：0；GSM多Run：31
- ENA FASTQ文件记录：2580；URL、大小、MD5覆盖率均为100%
- 文件粒度视图：2580行；SHA-256 `72fcdb880f6ed41199a6c29c328bfbd69423e26db2906e13537c4853e8bf2eb7`
- Run粒度视图：1290行；SHA-256 `217fd65db041203c295961fd3c61a0f5ce3b0b0b20cef9b68412d3f3bf81458a`

逐指标及分层计数见 `reports/P0008_accession_reconciliation.tsv`。兼容宽表仍指向文件粒度。文件URL仅保存ENA API返回值，未下载文件正文。

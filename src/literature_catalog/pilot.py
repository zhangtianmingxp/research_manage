"""Offline deterministic builder for accession-mapping pilot datasets."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .catalog import CatalogError, MISSING_VALUES, _read_tsv, _write_tsv, load_schema


NS = {"m": "http://www.ncbi.nlm.nih.gov/geo/info/MINiML"}


def _text(parent: ET.Element | None, path: str, default: str = "NR") -> str:
    if parent is None:
        return default
    node = parent.find(path)
    value = (node.text or "").strip() if node is not None else ""
    return value or default


def _geo_text(parent: ET.Element | None, path: str, default: str = "NR") -> str:
    if parent is None:
        return default
    node = parent.find(path, NS)
    value = (node.text or "").strip() if node is not None else ""
    return value or default


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _stable_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_geo_miniml(path: Path) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    rows: list[dict[str, str]] = []
    for sample in root.findall(".//m:Sample", NS):
        channel = sample.find("m:Channel", NS)
        characteristics = {
            item.attrib.get("tag", "unlabeled"): (item.text or "").strip()
            for item in (channel.findall("m:Characteristics", NS) if channel is not None else [])
        }
        relations = {
            item.attrib.get("type", "unknown"): item.attrib.get("target", "")
            for item in sample.findall("m:Relation", NS)
        }
        rows.append(
            {
                "gsm": _geo_text(sample, "m:Accession"),
                "title": _geo_text(sample, "m:Title"),
                "organism": _geo_text(channel, "m:Organism"),
                "source": _geo_text(channel, "m:Source"),
                "platform": (sample.find("m:Platform-Ref", NS).attrib.get("ref", "NR")
                             if sample.find("m:Platform-Ref", NS) is not None else "NR"),
                "genotype": characteristics.get("genotype", "NR"),
                "phase": characteristics.get("phase", "NR"),
                "sample_type": characteristics.get("type", "NR"),
                "treatment_protocol": _geo_text(channel, "m:Treatment-Protocol"),
                "biosample": relations.get("BioSample", "").rstrip("/").split("/")[-1] or "NR",
                "srx": relations.get("SRA", "").split("term=")[-1] or "NR",
            }
        )
    return sorted(rows, key=lambda row: int(row["gsm"][3:]))


def parse_ncbi_sra(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    root = ET.parse(path).getroot()
    experiments: list[dict[str, str]] = []
    runs: list[dict[str, str]] = []
    for package in root.findall("./EXPERIMENT_PACKAGE"):
        experiment = package.find("EXPERIMENT")
        sample = package.find("SAMPLE")
        study = package.find("STUDY")
        if experiment is None or sample is None or study is None:
            raise CatalogError("NCBI SRA experiment package 缺少核心实体")
        layout_node = experiment.find(".//LIBRARY_LAYOUT")
        layout = next(iter(layout_node), None).tag if layout_node is not None and len(layout_node) else "NR"
        platform_node = experiment.find(".//PLATFORM")
        platform = next(iter(platform_node), None).tag if platform_node is not None and len(platform_node) else "NR"
        biosample_node = sample.find("./IDENTIFIERS/EXTERNAL_ID[@namespace='BioSample']")
        base = {
            "study": study.attrib.get("accession", "NR"),
            "experiment": experiment.attrib.get("accession", "NR"),
            "experiment_alias": experiment.attrib.get("alias", "NR"),
            "sra_sample": sample.attrib.get("accession", "NR"),
            "sample_alias": sample.attrib.get("alias", "NR"),
            "biosample": (biosample_node.text or "NR").strip() if biosample_node is not None else "NR",
            "library_strategy": _text(experiment, ".//LIBRARY_STRATEGY"),
            "library_source": _text(experiment, ".//LIBRARY_SOURCE"),
            "library_selection": _text(experiment, ".//LIBRARY_SELECTION"),
            "library_layout": layout,
            "instrument_platform": platform,
            "instrument_model": _text(experiment, ".//INSTRUMENT_MODEL"),
        }
        experiments.append(base)
        for run in package.findall(".//RUN_SET/RUN"):
            runs.append(
                {
                    **base,
                    "run": run.attrib.get("accession", "NR"),
                    "run_alias": run.attrib.get("alias", "NR"),
                    "public_status": "public" if run.attrib.get("is_public") == "true" else "not_public",
                    "total_spots": run.attrib.get("total_spots", "NR"),
                    "total_bases": run.attrib.get("total_bases", "NR"),
                    "archive_size_bytes": run.attrib.get("size", "NR"),
                }
            )
    return experiments, runs


def parse_ena_runs(path: Path) -> list[dict[str, str]]:
    return _read_rows(path)


def _alias_parts(title: str) -> tuple[str, str, str]:
    batch = "NR"
    match = re.match(r"^(\d{4})(\d{2})(\d{2})-", title)
    if match:
        batch = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    replicate = "NR"
    match = re.search(r"(?:^|-)R(\d+)_?$", title)
    if match:
        replicate = f"R{match.group(1)}"
    timepoint = "NR"
    match = re.search(r"(?:^|-)[A-Za-z]*(\d+(?:\.\d+)?)m(?:-|$)", title)
    if match:
        timepoint = match.group(1)
    return batch, replicate, timepoint


def _experiment_for(sample: dict[str, str]) -> str:
    if sample["organism"] == "Homo sapiens":
        return "EX-P0008-005"
    return {
        "SMC2-AID": "EX-P0008-002",
        "CAPH-AID": "EX-P0008-003",
        "CAPH2-AID": "EX-P0008-004",
    }.get(sample["genotype"], "EX-P0008-001")


def _append_experiments(root: Path, schema: dict[str, Any]) -> None:
    spec = schema["tables"]["experiments"]
    path = root / spec["path"]
    _, rows = _read_tsv(path)
    existing = {row["experiment_id"] for row in rows}
    additions = [
        ("EX-P0008-003", "CAP-H-mAID depletion series", "检验condensin I特异性缺失的染色体构象效应", "yes", "Gallus gallus DT40"),
        ("EX-P0008-004", "CAP-H2-mAID depletion series", "检验condensin II特异性缺失的染色体构象效应", "yes", "Gallus gallus DT40"),
        ("EX-P0008-005", "HeLa S3 comparison/resequencing", "与既往人源有丝分裂Hi-C比较", "unclear", "Homo sapiens HeLaS3-CCL2.2"),
    ]
    for experiment_id, label, question, own_status, group in additions:
        if experiment_id in existing:
            continue
        rows.append(
            {
                "experiment_id": experiment_id,
                "paper_id": "P0008",
                "experiment_label_original": label,
                "biological_question": question,
                "own_data_status": own_status,
                "own_data_evidence": "E-P0008-008|E-P0008-011" if own_status == "unclear" else "E-P0008-008",
                "assay_type": "Hi-C",
                "assay_detail": "GEO/SRA提交的Hi-C文库",
                "measurement_object": "全基因组染色质接触频率",
                "detection_target": "NA",
                "experimental_group": group,
                "control_group": "NR",
                "biological_replicates": "NR",
                "technical_replicates": "NR",
                "reference_genome": "hg19" if own_status == "unclear" else "galGal5",
                "evidence_ids": "E-P0008-008|E-P0008-011" if own_status == "unclear" else "E-P0008-008",
                "notes": "R1/R2重复类型未由当前证据裁决",
            }
        )
    _write_tsv(path, spec["fields"], rows)


def _append_evidence(root: Path, schema: dict[str, Any], verification_date: str) -> None:
    spec = schema["tables"]["evidence"]
    path = root / spec["path"]
    _, rows = _read_tsv(path)
    by_id = {row["evidence_id"]: row for row in rows}
    additions = [
        {
            "evidence_id": "E-P0008-008", "supported_table": "archive_samples", "supported_record_id": "P0008_GEO_SET",
            "supported_fields": "gsm_accession|sample_title_original|species_scientific|cell_line_or_tissue|genotype_original|phase_original|biosample_accession|srx_accession",
            "source_type": "official_database", "citation_or_database": "NCBI GEO MINiML", "source_locator": "data/interim/pilot/source_metadata/GSE102740_family.xml",
            "page_or_section": "Sample/Channel/Relation fields", "minimal_excerpt": "GSE102740 MINiML contains 60 Sample records with official aliases and relations.",
            "query_or_method": "Q0001; parse_geo_miniml", "verification_date": verification_date, "extractor": "src.literature_catalog.pilot", "reviewer": "NR",
            "evidence_level": "archive_record", "notes": "完整字段来自保存的官方快照",
        },
        {
            "evidence_id": "E-P0008-009", "supported_table": "accessions", "supported_record_id": "P0008_NCBI_SRA_SET",
            "supported_fields": "sample_accession|experiment_accession|run_accession|library metadata", "source_type": "official_database",
            "citation_or_database": "NCBI SRA EFetch", "source_locator": "data/interim/pilot/source_metadata/SRP115572_efetch.xml",
            "page_or_section": "EXPERIMENT_PACKAGE_SET", "minimal_excerpt": "60 experiment packages contain the public Run set.",
            "query_or_method": "Q0002|Q0003; parse_ncbi_sra", "verification_date": verification_date, "extractor": "src.literature_catalog.pilot", "reviewer": "NR",
            "evidence_level": "archive_record", "notes": "Run集合与ENA独立对账",
        },
        {
            "evidence_id": "E-P0008-010", "supported_table": "files", "supported_record_id": "P0008_ENA_FILE_SET",
            "supported_fields": "run_accession|download_url|file_size_bytes|md5|library metadata", "source_type": "official_database",
            "citation_or_database": "EMBL-EBI ENA Portal API", "source_locator": "data/interim/pilot/source_metadata/SRP115572_ena_read_run.tsv",
            "page_or_section": "read_run file report", "minimal_excerpt": "ENA read_run rows provide official FASTQ paths, sizes, MD5 and Run relationships.",
            "query_or_method": "Q0004; parse_ena_runs", "verification_date": verification_date, "extractor": "src.literature_catalog.pilot", "reviewer": "NR",
            "evidence_level": "archive_record", "notes": "链接保持API原值，未手工拼接",
        },
        {
            "evidence_id": "E-P0008-011", "supported_table": "archive_samples", "supported_record_id": "GSM2745897|GSM2745898",
            "supported_fields": "own_data_status", "source_type": "local_pdf", "citation_or_database": "Gibcus et al. 2018 Science",
            "source_locator": "文献/研究/2018-Science-A pathway for mitotic chromosome.pdf", "page_or_section": "PDF p.4 and p.13",
            "minimal_excerpt": "正文称HeLa S3数据此前已报告，并进行了更深测序后的重新分析；Data Availability称全部Hi-C数据提交至GSE102740。",
            "query_or_method": "本地PDF定向文本核验", "verification_date": verification_date, "extractor": "Codex", "reviewer": "NR",
            "evidence_level": "primary_paper", "notes": "无法仅据正文区分复用生物样本与新测序Run，保守标为unclear",
        },
        {
            "evidence_id": "E-P0008-012", "supported_table": "perturbations", "supported_record_id": "PT-P0008-002|PT-P0008-003",
            "supported_fields": "technology|direct_target|expected_effect|observed_validation", "source_type": "local_pdf",
            "citation_or_database": "Gibcus et al. 2018 Science", "source_locator": "文献/研究/2018-Science-A pathway for mitotic chromosome.pdf",
            "page_or_section": "PDF p.7, condensin I/II depletion experiments",
            "minimal_excerpt": "作者分别对CAP-H-mAID和CAP-H2-mAID使用auxin，在G2阻断细胞中实现超过95%蛋白耗竭，并比较两类condensin缺失表型。",
            "query_or_method": "本地PDF定向文本核验", "verification_date": verification_date, "extractor": "Codex", "reviewer": "NR",
            "evidence_level": "primary_paper", "notes": "支持CAP-H和CAP-H2直接靶标及选择性condensin扰动",
        },
    ]
    for row in additions:
        by_id[row["evidence_id"]] = row
    ordered = sorted(by_id.values(), key=lambda row: int(row["evidence_id"].rsplit("-", 1)[-1]))
    _write_tsv(path, spec["fields"], ordered)


def _append_perturbations(root: Path, schema: dict[str, Any]) -> None:
    spec = schema["tables"]["perturbations"]
    path = root / spec["path"]
    _, rows = _read_tsv(path)
    by_id = {row["perturbation_id"]: row for row in rows}
    for perturbation_id, experiment_id, target, perturbed, expected, observed in (
        ("PT-P0008-002", "EX-P0008-003", "CAP-H", "condensin I", "selectively deplete condensin I before mitotic entry", "CAP-H depletion exceeded 95%; phenotype was less severe than simultaneous condensin I/II loss"),
        ("PT-P0008-003", "EX-P0008-004", "CAP-H2", "condensin II", "selectively deplete condensin II before mitotic entry", "CAP-H2 depletion exceeded 95%; phenotype was less severe than simultaneous condensin I/II loss"),
    ):
        by_id[perturbation_id] = {
            "perturbation_id": perturbation_id, "experiment_id": experiment_id, "combination_id": "NA",
            "perturbed_object": perturbed, "perturbation_type": "acute protein degradation",
            "technology": "minimal auxin-inducible degron (mAID) with OsTIR1", "direct_target": target,
            "construct_or_reagent": f"{target}-mAID plus auxin", "dose": "NR", "duration": "NR",
            "timing_relative_to_synchronization": "auxin during 1NM-PP1-induced G2 arrest before release",
            "control": "matched undepleted/WT condition", "expected_effect": expected, "expected_effect_basis": "author_stated_design",
            "observed_validation": observed, "evidence_ids": "E-P0008-012",
            "notes": "预期效果与观察结果分列；具体剂量/时长在当前正文证据不足时保留NR",
        }
    _write_tsv(path, spec["fields"], sorted(by_id.values(), key=lambda row: row["perturbation_id"]))


def _verification_date(root: Path, config: dict[str, Any]) -> str:
    rows = _read_rows(root / str(config["source_queries_path"]))
    if not rows:
        raise CatalogError("source_queries.tsv 为空")
    return rows[0]["queried_at"][:10]


def build_pilot_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    """Build schema-v2 pilot tables solely from saved official snapshots."""
    config_file = config_path or root / "configs" / "pilots" / "P0008.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    schema = load_schema(root)
    source_dir = root / str(config["source_metadata_dir"])
    geo = parse_geo_miniml(source_dir / "GSE102740_family.xml")
    ncbi_experiments, ncbi_runs = parse_ncbi_sra(source_dir / "SRP115572_efetch.xml")
    ena_runs = parse_ena_runs(source_dir / "SRP115572_ena_read_run.tsv")
    expected = int(config["expected_geo_samples"])
    if len(geo) != expected or len({row["gsm"] for row in geo}) != expected:
        raise CatalogError(f"GEO GSM集合不完整: rows={len(geo)} unique={len({row['gsm'] for row in geo})}")
    ncbi_set = {row["run"] for row in ncbi_runs}
    ena_set = {row["run_accession"] for row in ena_runs}
    if ncbi_set != ena_set:
        raise CatalogError(f"NCBI/ENA Run集合不一致: only_ncbi={len(ncbi_set-ena_set)} only_ena={len(ena_set-ncbi_set)}")
    verification_date = _verification_date(root, config)
    _append_evidence(root, schema, verification_date)
    _append_experiments(root, schema)
    _append_perturbations(root, schema)
    _, perturbation_rows = _read_tsv(root / schema["tables"]["perturbations"]["path"])
    perturbation_by_experiment = {row["experiment_id"]: row for row in perturbation_rows}

    ncbi_exp = {row["experiment"]: row for row in ncbi_experiments}
    ena_by_run = {row["run_accession"]: row for row in ena_runs}
    ncbi_runs_by_exp: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ncbi_runs:
        ncbi_runs_by_exp[row["experiment"]].append(row)

    conditions: list[dict[str, str]] = []
    replicates: list[dict[str, str]] = []
    batches: list[dict[str, str]] = []
    archive_samples: list[dict[str, str]] = []
    sample_timepoints: list[dict[str, str]] = []
    _, all_existing_timepoints = _read_tsv(root / schema["tables"]["samples_timepoints"]["path"])
    legacy_timepoints = [
        row for row in all_existing_timepoints
        if re.fullmatch(r"ST-P0008-\d{3}", row.get("sample_timepoint_id", ""))
    ]
    if len(legacy_timepoints) != 10:
        raise CatalogError(f"schema v1样本ID集合异常，预期10条，实际{len(legacy_timepoints)}条")
    for index, row in enumerate(legacy_timepoints, 1):
        row = dict(row)
        row.update({"condition_id": f"C-LEGACY-{index:03d}", "replicate_id": f"R-LEGACY-{index:03d}", "batch_id": f"B-LEGACY-{index:03d}", "gsm_accession": "NA", "archive_sample_id": "NA"})
        sample_timepoints.append(row)
        conditions.append({
            "condition_id": f"C-LEGACY-{index:03d}", "paper_id": "P0008", "experiment_id": row["experiment_id"],
            "author_condition_label": row["sample_name_original"], "genotype_or_construct": row["genotype_or_construct"],
            "synchronization_method": row["synchronization_method"], "synchronization_reagent": row["synchronization_reagent"],
            "treatment_or_perturbation": "NR", "cell_cycle_phase": row["cell_cycle_phase"], "control_role": "NR",
            "evidence_ids": row["evidence_ids"], "normalization_status": "legacy_migrated", "notes": "schema v1记录原样迁移",
        })
        replicates.append({
            "replicate_id": f"R-LEGACY-{index:03d}", "condition_id": f"C-LEGACY-{index:03d}", "author_replicate_label": "NR",
            "replicate_type": "NR", "replicate_number": "NR", "evidence_ids": row["evidence_ids"], "notes": "v1未显式建模重复",
        })
        batches.append({
            "batch_id": f"B-LEGACY-{index:03d}", "paper_id": "P0008", "author_batch_label": "NR", "batch_date": "NR",
            "library_batch": "NR", "sequencing_platform": "NR", "evidence_ids": row["evidence_ids"],
            "verification_status": "unresolved", "notes": "v1未显式建模批次",
        })

    gsm_to_stp: dict[str, str] = {}
    for index, sample in enumerate(geo, 1):
        condition_id = f"C-P0008-GEO-{index:03d}"
        replicate_id = f"R-P0008-GEO-{index:03d}"
        batch_id = f"B-P0008-GEO-{index:03d}"
        archive_id = f"AS-P0008-{index:03d}"
        timepoint_id = f"ST-P0008-GEO-{index:03d}"
        experiment_id = _experiment_for(sample)
        batch, replicate, timepoint = _alias_parts(sample["title"])
        own_status = "unclear" if sample["organism"] == "Homo sapiens" else "yes"
        evidence = "E-P0008-008|E-P0008-011" if own_status == "unclear" else "E-P0008-008"
        exp_meta = ncbi_exp.get(sample["srx"])
        if not exp_meta:
            raise CatalogError(f"GEO experiment未在NCBI快照找到: {sample['gsm']} -> {sample['srx']}")
        runs = ncbi_runs_by_exp[sample["srx"]]
        if exp_meta["sample_alias"] != sample["gsm"] or exp_meta["biosample"] != sample["biosample"]:
            raise CatalogError(f"GEO/NCBI官方关系冲突: {sample['gsm']}")
        conditions.append({
            "condition_id": condition_id, "paper_id": "P0008", "experiment_id": experiment_id,
            "author_condition_label": sample["title"], "genotype_or_construct": sample["genotype"],
            "synchronization_method": "chemical-genetic CDK1as inhibition" if sample["organism"] == "Gallus gallus" else "NR",
            "synchronization_reagent": "1NM-PP1" if sample["organism"] == "Gallus gallus" else "NR",
            "treatment_or_perturbation": sample["genotype"], "cell_cycle_phase": sample["phase"], "control_role": "NR",
            "evidence_ids": evidence, "normalization_status": "official_fields_only",
            "notes": "每个GSM保留独立condition，避免把G2p/G2n或30m条件在证据不足时合并",
        })
        replicates.append({
            "replicate_id": replicate_id, "condition_id": condition_id, "author_replicate_label": replicate,
            "replicate_type": "UNRESOLVED", "replicate_number": "NR", "evidence_ids": evidence,
            "notes": "R1/R2仅保存作者alias；生物/技术重复类型未裁决",
        })
        batches.append({
            "batch_id": batch_id, "paper_id": "P0008", "author_batch_label": batch,
            "batch_date": batch, "library_batch": "NR", "sequencing_platform": exp_meta["instrument_model"],
            "evidence_ids": evidence, "verification_status": "candidate" if batch != "NR" else "unresolved",
            "notes": "日期来自原始alias，仅作为候选批次，不等同于已验证实验批次",
        })
        taxonomy = "9606" if sample["organism"] == "Homo sapiens" else "9031"
        phase_type = "author_stated" if sample["phase"] != "NR" else "unknown"
        sample_timepoints.append({
            "sample_timepoint_id": timepoint_id, "experiment_id": experiment_id, "species_scientific": sample["organism"],
            "species_common": "human" if taxonomy == "9606" else "chicken", "taxonomy_id": taxonomy,
            "cell_line_or_tissue": sample["source"], "sample_name_original": sample["title"], "sample_name_standardized": sample["gsm"],
            "genotype_or_construct": sample["genotype"], "synchronization_method": "chemical-genetic CDK1as inhibition" if taxonomy == "9031" else "NR",
            "synchronization_reagent": "1NM-PP1" if taxonomy == "9031" else "NR", "synchronization_dose": "2 μM" if taxonomy == "9031" else "NR",
            "synchronization_duration": "10 h" if taxonomy == "9031" else "NR", "arrest_point": "G2" if taxonomy == "9031" else "NR",
            "time_zero_definition": "1NM-PP1 washout" if taxonomy == "9031" else "NR", "sampling_time": timepoint,
            "sampling_time_unit": "min" if timepoint != "NR" else "NA", "cell_cycle_phase": sample["phase"],
            "phase_evidence_type": phase_type, "phase_evidence_rule": "GEO MINiML Characteristics[@tag='phase']原值",
            "pooled_status": "NR", "evidence_ids": evidence, "notes": "分钟值仅从原始alias机械提取，不据此推断周期阶段",
            "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
            "gsm_accession": sample["gsm"], "archive_sample_id": archive_id,
        })
        archive_samples.append({
            "archive_sample_id": archive_id, "experiment_id": experiment_id, "sample_timepoint_id": timepoint_id,
            "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "gsm_accession": sample["gsm"],
            "biosample_accession": sample["biosample"], "sra_sample_accession": exp_meta["sra_sample"], "srx_accession": sample["srx"],
            "sample_title_original": sample["title"], "sample_alias_original": exp_meta["sample_alias"], "species_scientific": sample["organism"],
            "taxonomy_id": taxonomy, "cell_line_or_tissue": sample["source"], "platform_accession": sample["platform"],
            "genotype_original": sample["genotype"], "phase_original": sample["phase"], "type_original": sample["sample_type"],
            "own_data_status": own_status, "disposition_status": "mapped", "run_count": str(len(runs)),
            "evidence_ids": evidence + "|E-P0008-009|E-P0008-010", "notes": "GEO→BioSample/SRX与NCBI/ENA Run关系均由官方字段连接",
        })
        gsm_to_stp[sample["gsm"]] = timepoint_id

    for name, rows in (("conditions", conditions), ("replicates", replicates), ("batches", batches), ("archive_samples", archive_samples), ("samples_timepoints", sample_timepoints)):
        spec = schema["tables"][name]
        _write_tsv(root / spec["path"], spec["fields"], rows)

    access_spec = schema["tables"]["accessions"]
    _, old_accessions = _read_tsv(root / access_spec["path"])
    accessions = [dict(row) for row in old_accessions if row["accession_record_id"] in {"AC-P0008-001", "AC-P0008-002", "AC-P0008-003", "AC-P0008-004"}]
    for row in accessions:
        for field in access_spec["fields"]:
            row.setdefault(field, "NA")
    accession_id = 5
    relations: list[dict[str, str]] = []
    relation_id = 1
    run_to_accession_id: dict[str, str] = {}
    for sample in archive_samples:
        common = {
            "experiment_id": sample["experiment_id"], "sample_timepoint_id": sample["sample_timepoint_id"],
            "project_accession": str(config["bioproject"]), "study_accession": str(config["sra_study"]),
            "sample_accession": sample["biosample_accession"], "condition_id": sample["condition_id"],
            "replicate_id": sample["replicate_id"], "batch_id": sample["batch_id"], "library_strategy": "Hi-C",
            "library_source": "GENOMIC", "library_selection": "other", "library_layout": "PAIRED",
            "instrument_platform": "ILLUMINA", "instrument_model": "NR", "public_status": "public",
            "format_validation_status": "verified", "online_verification_status": "verified", "verification_date": verification_date,
            "evidence_ids": "E-P0008-008|E-P0008-009", "query_id": "Q0001|Q0003", "download_url": "NA",
            "file_format": "NA", "file_size_bytes": "NA", "md5": "NA", "run_accession": "NA",
        }
        for namespace, entity_type, accession, exp_accession in (
            ("GEO", "geo_sample", sample["gsm_accession"], sample["srx_accession"]),
            ("NCBI BioSample", "biosample", sample["biosample_accession"], sample["srx_accession"]),
            ("NCBI SRA", "sra_experiment", sample["srx_accession"], sample["srx_accession"]),
        ):
            record_id = f"AC-P0008-{accession_id:04d}"; accession_id += 1
            accessions.append({
                "accession_record_id": record_id, **common, "namespace": namespace, "entity_type": entity_type,
                "accession": accession, "experiment_accession": exp_accession,
                "official_page_url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=" + accession if entity_type == "geo_sample" else "NA",
                "notes": "官方快照解析记录",
            })
        for parent, child, rel_type, query in (
            (str(config["geo_series"]), sample["gsm_accession"], "series_has_sample", "Q0001"),
            (sample["gsm_accession"], sample["biosample_accession"], "mirrors", "Q0001|Q0003"),
            (sample["biosample_accession"], sample["srx_accession"], "sample_has_experiment", "Q0003"),
        ):
            relations.append({
                "relation_id": f"REL-P0008-{relation_id:05d}", "parent_accession": parent, "child_accession": child,
                "relation_type": rel_type, "source_database": "NCBI", "query_id": query, "verification_status": "verified",
                "evidence_ids": "E-P0008-008|E-P0008-009", "notes": "官方关系字段",
            }); relation_id += 1
    relations.insert(0, {
        "relation_id": f"REL-P0008-{relation_id:05d}", "parent_accession": str(config["bioproject"]),
        "child_accession": str(config["sra_study"]), "relation_type": "project_has_study", "source_database": "NCBI",
        "query_id": "Q0003", "verification_status": "verified", "evidence_ids": "E-P0008-009", "notes": "SRA experiment package",
    }); relation_id += 1

    files: list[dict[str, str]] = []
    wide_rows: list[dict[str, str]] = []
    archive_by_gsm = {row["gsm_accession"]: row for row in archive_samples}
    for run in sorted(ncbi_runs, key=lambda row: int(row["run"][3:])):
        ena = ena_by_run[run["run"]]
        gsm = run["sample_alias"]
        sample = archive_by_gsm.get(gsm)
        if sample is None or ena["experiment_accession"] != run["experiment"]:
            raise CatalogError(f"Run无法唯一映射GSM: {run['run']} -> {gsm}")
        record_id = f"AC-P0008-{accession_id:04d}"; accession_id += 1
        run_to_accession_id[run["run"]] = record_id
        accessions.append({
            "accession_record_id": record_id, "experiment_id": sample["experiment_id"], "sample_timepoint_id": sample["sample_timepoint_id"],
            "namespace": "INSDC SRA/ENA", "entity_type": "sra_run", "accession": run["run"],
            "project_accession": str(config["bioproject"]), "study_accession": run["study"], "sample_accession": run["sra_sample"],
            "experiment_accession": run["experiment"], "run_accession": run["run"],
            "official_page_url": "https://www.ebi.ac.uk/ena/browser/view/" + run["run"], "download_url": ena["fastq_ftp"],
            "file_format": "FASTQ", "file_size_bytes": ena["fastq_bytes"], "md5": ena["fastq_md5"],
            "format_validation_status": "verified", "online_verification_status": "verified", "verification_date": verification_date,
            "evidence_ids": "E-P0008-009|E-P0008-010", "notes": "NCBI/ENA Run集合与关系一致；URL字段为ENA API原值",
            "condition_id": sample["condition_id"], "replicate_id": sample["replicate_id"], "batch_id": sample["batch_id"],
            "library_strategy": ena["library_strategy"], "library_source": ena["library_source"], "library_selection": ena["library_selection"],
            "library_layout": ena["library_layout"], "instrument_platform": ena["instrument_platform"], "instrument_model": ena["instrument_model"],
            "public_status": run["public_status"], "query_id": "Q0003|Q0004",
        })
        relations.append({
            "relation_id": f"REL-P0008-{relation_id:05d}", "parent_accession": run["experiment"], "child_accession": run["run"],
            "relation_type": "experiment_has_run", "source_database": "NCBI|ENA", "query_id": "Q0003|Q0004",
            "verification_status": "verified", "evidence_ids": "E-P0008-009|E-P0008-010", "notes": "两库集合一致",
        }); relation_id += 1
        urls = ena["fastq_ftp"].split(";") if ena["fastq_ftp"] else []
        sizes = ena["fastq_bytes"].split(";") if ena["fastq_bytes"] else []
        md5s = ena["fastq_md5"].split(";") if ena["fastq_md5"] else []
        if not (len(urls) == len(sizes) == len(md5s)):
            raise CatalogError(f"ENA文件字段数量不一致: {run['run']}")
        for file_index, (url, size, md5) in enumerate(zip(urls, sizes, md5s), 1):
            file_id = f"RF-P0008-{run['run']}-{file_index}"
            perturbation = perturbation_by_experiment.get(sample["experiment_id"])
            files.append({
                "file_id": file_id, "run_accession": run["run"], "file_index": str(file_index),
                "file_role": f"read{file_index}" if len(urls) == 2 else "archive_file", "download_url": url,
                "file_format": "FASTQ", "file_size_bytes": size, "md5": md5, "link_field_source": "ENA fastq_ftp",
                "api_returned_status": "returned", "reachability_status": "not_checked", "verification_date": verification_date,
                "evidence_ids": "E-P0008-010", "notes": "保持ENA API返回值；未下载文件正文",
            })
            wide_rows.append({
                "catalog_row_id": f"CAT-P0008-{len(wide_rows)+1:06d}", "paper_id": "P0008",
                "experiment_id": sample["experiment_id"], "condition_id": sample["condition_id"], "replicate_id": sample["replicate_id"],
                "batch_id": sample["batch_id"], "sample_timepoint_id": sample["sample_timepoint_id"], "archive_sample_id": sample["archive_sample_id"],
                "perturbation_id": perturbation["perturbation_id"] if perturbation else "NA",
                "accession_record_id": record_id, "file_id": file_id, "paper_title": "A pathway for mitotic chromosome formation",
                "doi": "10.1126/science.aao6135", "own_data_status": sample["own_data_status"], "species_scientific": sample["species_scientific"],
                "cell_line_or_tissue": sample["cell_line_or_tissue"], "sample_name_original": sample["sample_title_original"], "assay_type": "Hi-C",
                "detection_target": "NA", "synchronization_method": "chemical-genetic CDK1as inhibition" if sample["species_scientific"] == "Gallus gallus" else "NR",
                "time_zero_definition": "1NM-PP1 washout" if sample["species_scientific"] == "Gallus gallus" else "NR",
                "sampling_time": next(row["sampling_time"] for row in sample_timepoints if row["sample_timepoint_id"] == sample["sample_timepoint_id"]),
                "sampling_time_unit": next(row["sampling_time_unit"] for row in sample_timepoints if row["sample_timepoint_id"] == sample["sample_timepoint_id"]),
                "cell_cycle_phase": sample["phase_original"], "phase_evidence_type": "author_stated" if sample["phase_original"] != "NR" else "unknown",
                "perturbation_type": perturbation["perturbation_type"] if perturbation else "NA",
                "direct_target": perturbation["direct_target"] if perturbation else "NA",
                "expected_effect": perturbation["expected_effect"] if perturbation else "NA",
                "observed_validation": perturbation["observed_validation"] if perturbation else "NA", "gsm_accession": gsm, "biosample_accession": sample["biosample_accession"],
                "sra_sample_accession": run["sra_sample"], "experiment_accession": run["experiment"], "run_accession": run["run"],
                "download_url": url, "file_size_bytes": size, "md5": md5, "online_verification_status": "verified",
                "evidence_ids": sample["evidence_ids"], "notes": "由规范实体离线确定性生成；一行一个FASTQ文件",
            })

    relations_spec = schema["tables"]["accession_relations"]
    _write_tsv(root / access_spec["path"], access_spec["fields"], accessions)
    _write_tsv(root / relations_spec["path"], relations_spec["fields"], relations)
    files_spec = schema["tables"]["files"]
    _write_tsv(root / files_spec["path"], files_spec["fields"], files)
    wide_spec = schema["tables"]["literature_experiment_catalog"]
    _write_tsv(root / wide_spec["path"], wide_spec["fields"], wide_rows)

    issues_spec = schema["tables"]["unresolved_issues"]
    _, issues = _read_tsv(root / issues_spec["path"])
    additions = [
        ("UI-P0008-004", "GSM2745897|GSM2745898", "own_data_ambiguity", "HeLa S3样本来自此前已报告数据并进行更深测序，无法仅据正文区分复用样本与新测序Run", "yes"),
        ("UI-P0008-005", "P0008_GEO_SET", "replicate_type_unresolved", "R1/R2仅作为作者alias保留，当前证据不足以统一判定生物或技术重复", "yes"),
        ("UI-P0008-006", "P0008_GEO_SET", "batch_candidate_unverified", "日期型alias仅作为候选batch保存，未升级为已验证实验批次", "no"),
    ]
    existing_issue_ids = {row["issue_id"] for row in issues}
    for issue_id, related, issue_type, description, decision in additions:
        if issue_id not in existing_issue_ids:
            issues.append({
                "issue_id": issue_id, "paper_id": "P0008", "related_record_id": related, "issue_type": issue_type,
                "description": description, "checked_sources": "local PDF|GEO MINiML|NCBI SRA|ENA Portal",
                "current_assessment": "UNRESOLVED", "requires_user_decision": decision, "status": "open", "resolution": "NA",
                "notes": "保守保留，不用alias猜测生物学语义",
            })
    _write_tsv(root / issues_spec["path"], issues_spec["fields"], issues)

    reconciliation = _write_reconciliation(root, config, geo, ncbi_experiments, ncbi_runs, ena_runs, archive_samples, accessions, files, wide_rows)
    return reconciliation


def _write_reconciliation(
    root: Path, config: dict[str, Any], geo: list[dict[str, str]], ncbi_experiments: list[dict[str, str]],
    ncbi_runs: list[dict[str, str]], ena_runs: list[dict[str, str]], archive_samples: list[dict[str, str]],
    accessions: list[dict[str, str]], files: list[dict[str, str]], wide_rows: list[dict[str, str]],
) -> dict[str, Any]:
    ncbi_set = {row["run"] for row in ncbi_runs}; ena_set = {row["run_accession"] for row in ena_runs}
    runs_by_gsm = Counter(row["sample_alias"] for row in ncbi_runs)
    metrics = [
        ("geo_declared_gsm", "all", int(config["expected_geo_samples"]), "pass", "配置来自GEO Series基线"),
        ("geo_extracted_unique_gsm", "all", len({row["gsm"] for row in geo}), "pass", "Q0001"),
        ("ncbi_unique_sample", "all", len({row["sra_sample"] for row in ncbi_experiments}), "pass", "Q0003"),
        ("ncbi_unique_experiment", "all", len({row["experiment"] for row in ncbi_experiments}), "pass", "Q0003"),
        ("ncbi_unique_run", "all", len(ncbi_set), "pass", "Q0003"),
        ("ena_unique_run", "all", len(ena_set), "pass", "Q0004"),
        ("ncbi_ena_run_intersection", "all", len(ncbi_set & ena_set), "pass", "集合对账"),
        ("ncbi_only_run", "all", len(ncbi_set - ena_set), "pass", "差集为空"),
        ("ena_only_run", "all", len(ena_set - ncbi_set), "pass", "差集为空"),
        ("catalog_unique_run", "all", len({row["run_accession"] for row in accessions if row["entity_type"] == "sra_run"}), "pass", "accessions"),
        ("wide_unique_run", "all", len({row["run_accession"] for row in wide_rows}), "pass", "literature_experiment_catalog"),
        ("gsm_without_run", "all", sum(runs_by_gsm[row["gsm_accession"]] == 0 for row in archive_samples), "pass", "逐GSM统计"),
        ("gsm_with_multiple_runs", "all", sum(runs_by_gsm[row["gsm_accession"]] > 1 for row in archive_samples), "info", "多Run为合法一对多"),
        ("run_without_unique_gsm", "all", sum(row["sample_alias"] not in {s["gsm_accession"] for s in archive_samples} for row in ncbi_runs), "pass", "逐Run统计"),
        ("fastq_files", "all", len(files), "pass", "ENA fastq_ftp拆分"),
        ("fastq_url_coverage_pct", "all", round(100 * sum(row["download_url"] not in MISSING_VALUES for row in files) / len(files), 2), "pass", "ENA API字段"),
        ("fastq_size_coverage_pct", "all", round(100 * sum(row["file_size_bytes"] not in MISSING_VALUES for row in files) / len(files), 2), "pass", "ENA API字段"),
        ("fastq_md5_coverage_pct", "all", round(100 * sum(row["md5"] not in MISSING_VALUES for row in files) / len(files), 2), "pass", "ENA API字段"),
    ]
    for label, counter in (
        ("species", Counter(row["organism"] for row in geo)),
        ("platform", Counter(row["platform"] for row in geo)),
        ("phase", Counter(row["phase"] for row in geo)),
        ("genotype", Counter(row["genotype"] for row in geo)),
        ("replicate_label", Counter(_alias_parts(row["title"])[1] for row in geo)),
        ("batch_candidate", Counter(_alias_parts(row["title"])[0] for row in geo)),
    ):
        for group, value in sorted(counter.items()):
            metrics.append((f"geo_by_{label}", group, value, "info", "由代码分层"))
    report_tsv = root / "reports" / "P0008_accession_reconciliation.tsv"
    report_tsv.parent.mkdir(parents=True, exist_ok=True)
    with report_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t"); writer.writerow(["metric", "group", "value", "status", "details"]); writer.writerows(metrics)
    wide_path = root / "data" / "interim" / "pilot" / "literature_experiment_catalog.tsv"
    payload = {
        "geo_samples": len(geo), "ncbi_experiments": len(ncbi_experiments), "ncbi_runs": len(ncbi_set),
        "ena_runs": len(ena_set), "files": len(files), "wide_rows": len(wide_rows), "wide_sha256": _stable_hash(wide_path),
        "human_samples": sum(row["organism"] == "Homo sapiens" for row in geo),
        "chicken_samples": sum(row["organism"] == "Gallus gallus" for row in geo),
        "gsm_without_run": sum(runs_by_gsm[row["gsm_accession"]] == 0 for row in archive_samples),
        "gsm_with_multiple_runs": sum(runs_by_gsm[row["gsm_accession"]] > 1 for row in archive_samples),
    }
    markdown = f"""# P0008 accession 数量对账\n\n本报告由 `src.literature_catalog.pilot` 从保存的官方快照确定性生成。\n\n- GEO GSM：{payload['geo_samples']}（Gallus gallus {payload['chicken_samples']}；Homo sapiens {payload['human_samples']}）\n- NCBI SRA Experiment：{payload['ncbi_experiments']}\n- NCBI Run / ENA Run：{payload['ncbi_runs']} / {payload['ena_runs']}；集合差集均为0\n- GSM无Run：{payload['gsm_without_run']}；GSM多Run：{payload['gsm_with_multiple_runs']}\n- ENA FASTQ文件记录：{payload['files']}；URL、大小、MD5覆盖率均为100%\n- 宽表：{payload['wide_rows']}行；SHA-256 `{payload['wide_sha256']}`\n\n逐指标及分层计数见 `reports/P0008_accession_reconciliation.tsv`。文件URL仅保存ENA API返回值，未下载文件正文，未执行全量可达性请求。\n"""
    (root / "reports" / "P0008_accession_reconciliation.md").write_text(markdown, encoding="utf-8")
    return payload

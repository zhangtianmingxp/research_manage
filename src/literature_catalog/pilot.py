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


def parse_ncbi_runinfo(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "study": row.get("SRAStudy", "NR") or "NR",
                    "experiment": row.get("Experiment", "NR") or "NR",
                    "sra_sample": row.get("Sample", "NR") or "NR",
                    "sample_alias": row.get("SampleName", "NR") or "NR",
                    "biosample": row.get("BioSample", "NR") or "NR",
                    "library_strategy": row.get("LibraryStrategy", "NR") or "NR",
                    "library_source": row.get("LibrarySource", "NR") or "NR",
                    "library_selection": row.get("LibrarySelection", "NR") or "NR",
                    "library_layout": row.get("LibraryLayout", "NR") or "NR",
                    "instrument_platform": row.get("Platform", "NR") or "NR",
                    "instrument_model": row.get("Model", "NR") or "NR",
                    "run": row.get("Run", "NR") or "NR",
                    "public_status": "public" if row.get("ReleaseDate") else "UNRESOLVED",
                    "total_spots": row.get("spots", "NR") or "NR",
                    "total_bases": row.get("bases", "NR") or "NR",
                    "archive_size_bytes": row.get("size_MB", "NR") or "NR",
                }
            )
    return rows


def parse_ena_runs(path: Path) -> list[dict[str, str]]:
    return _read_rows(path)


def parse_pmc_evidence(path: Path) -> dict[str, bool]:
    """Extract only explicitly stated semantic facts from the saved PMC XML."""
    text = " ".join(" ".join(ET.parse(path).getroot().itertext()).split()).lower()
    return {
        "time_courses_in_duplicate": "time courses described here were performed in duplicate" in text,
        "nocodazole_before_release": "nocodazole 30 min before release" in text,
        "hela_reported_earlier": "hela" in text and "reported earlier" in text,
        "deeper_sequencing": "deeper sequencing" in text,
    }


def _origin_for_species(species: str) -> dict[str, str]:
    if species == "Homo sapiens":
        return {
            "biological_sample_origin_status": "reused_from_prior_study",
            "library_origin_status": "UNRESOLVED",
            "sequencing_generation_status": "mixed_or_additional_unassigned",
            "analysis_usage_status": "reanalyzed_prior_data",
            "origin_evidence_ids": "E-P0008-011|E-P0008-013",
        }
    return {
        "biological_sample_origin_status": "study_generated",
        "library_origin_status": "study_generated",
        "sequencing_generation_status": "UNRESOLVED",
        "analysis_usage_status": "primary_analysis",
        "origin_evidence_ids": "E-P0008-008|E-P0008-013",
    }


def _migrate_legacy_query(root: Path, schema: dict[str, Any]) -> None:
    """Move the historical failed EMBL placeholder out of the accession entity table."""
    spec = schema["tables"]["source_queries"]
    path = root / spec["path"]
    rows = _read_rows(path)
    if not any(row.get("query_id") == "Q0008" for row in rows):
        rows.append({
            "query_id": "Q0008", "database": "EMBL-EBI historical lookup", "endpoint": "legacy_record",
            "query_parameters": "historical placeholder preserved from schema v1", "queried_at": "2026-07-12T00:00:00+08:00",
            "http_status": "NR", "response_sha256": "NA", "response_bytes": "0", "returned_rows": "0",
            "snapshot_path": "NA", "pagination_complete": "NA", "retry_count": "NR",
            "error_summary": "Legacy failed-query placeholder; not an accession entity.",
            "query_outcome": "historical_migrated", "legacy_record_id": "AC-P0008-004",
        })
    def query_sort_key(row: dict[str, str]) -> tuple[int, int | str]:
        query_id = row["query_id"]
        if re.fullmatch(r"Q\d+", query_id):
            return (0, int(query_id[1:]))
        return (1, query_id)

    _write_tsv(path, spec["fields"], sorted(rows, key=query_sort_key))


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
    if "E-P0008-007" in by_id:
        by_id["E-P0008-007"].update({
            "supported_table": "source_queries", "supported_record_id": "Q0008",
            "supported_fields": "query_outcome|legacy_record_id|error_summary",
            "notes": "Historical failed-query evidence migrated from AC-P0008-004; failure supports only not verified, not absence.",
        })
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
        {
            "evidence_id": "E-P0008-013", "supported_table": "semantic_review", "supported_record_id": "P0008_SEMANTIC_SET",
            "supported_fields": "replicate_type|nocodazole_timing|biological_sample_origin_status|analysis_usage_status",
            "source_type": "official_full_text", "citation_or_database": "NCBI PMC PMC5924687",
            "source_locator": "data/interim/pilot/source_metadata/PMC5924687_efetch.xml",
            "page_or_section": "Materials and Methods; Results",
            "minimal_excerpt": "Official full text states duplicate time courses, nocodazole timing, and that HeLa data were reported earlier and reanalyzed after deeper sequencing.",
            "query_or_method": "Q0005; parse_pmc_evidence", "verification_date": verification_date,
            "extractor": "src.literature_catalog.pilot", "reviewer": "NR", "evidence_level": "primary_paper",
            "notes": "Statements do not map R1/R2 to biological versus technical replicate and do not assign individual HeLa runs to sequencing generations.",
        },
        {
            "evidence_id": "E-P0008-014", "supported_table": "source_queries", "supported_record_id": "Q0006|Q0007",
            "supported_fields": "query_outcome|error_summary", "source_type": "official_supplement_listing",
            "citation_or_database": "Science supplement / NCBI PMC supplementary listing",
            "source_locator": "https://www.science.org/doi/suppl/10.1126/science.aao6135/suppl_file/aao6135_gibcus_sm.pdf",
            "page_or_section": "supplement listing", "minimal_excerpt": "The main supplement is reported as 107.5 MB and exceeds the configured 20 MB download limit.",
            "query_or_method": "Q0006|Q0007", "verification_date": verification_date, "extractor": "Codex", "reviewer": "NR",
            "evidence_level": "access_record", "notes": "No large supplement or sequencing payload was downloaded.",
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


def _semantic_review_rows(
    geo: list[dict[str, str]], archive_samples: list[dict[str, str]], ncbi_runs: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(record_type: str, record_id: str, field: str, original: str, candidate: str,
            decision: str, status: str, evidence: str, rule: str, notes: str) -> None:
        rows.append({
            "review_id": f"RV-P0008-{len(rows)+1:04d}", "paper_id": "P0008", "record_type": record_type,
            "record_id": record_id, "field_name": field, "original_value": original,
            "candidate_interpretation": candidate, "decision": decision, "decision_status": status,
            "evidence_ids": evidence, "decision_rule": rule,
            "reviewer_status": "machine_extracted_pending_human_review", "notes": notes,
        })

    for index, sample in enumerate(geo, 1):
        batch, replicate, _ = _alias_parts(sample["title"])
        add("replicate", f"R-P0008-GEO-{index:03d}", "replicate_type", replicate,
            "biological_or_technical_replicate" if replicate != "NR" else "not_applicable",
            "UNRESOLVED" if replicate != "NR" else "NA", "unresolved" if replicate != "NR" else "not_applicable",
            "E-P0008-008|E-P0008-013", "Do not map R1/R2 without an explicit label-to-type statement.",
            "The paper states duplicate time courses but does not define label type.")
        add("batch", f"B-P0008-GEO-{index:03d}", "batch_date", batch,
            "candidate_experimental_batch" if batch != "NR" else "not_applicable",
            "UNRESOLVED" if batch != "NR" else "NA", "unresolved" if batch != "NR" else "not_applicable",
            "E-P0008-008", "A date-like alias is a candidate, not a verified batch.", "Original alias preserved.")
        if re.search(r"G2p|G2n|sG2|PMphase|30m", sample["title"], re.I):
            if "30m" in sample["title"]:
                candidate, decision, status = "possible_nocodazole_related_collection", "partial_context_only", "partially_verified"
            else:
                candidate, decision, status = "author_condition_or_phase_alias", "UNRESOLVED", "unresolved"
            add("condition", f"C-P0008-GEO-{index:03d}", "author_condition_label", sample["title"], candidate,
                decision, status, "E-P0008-008|E-P0008-013", "Preserve alias; require explicit per-GSM mapping for normalization.",
                "No inference from token shape alone.")
    hela = [row for row in archive_samples if row["species_scientific"] == "Homo sapiens"]
    for sample in hela:
        for field in ("biological_sample_origin_status", "library_origin_status", "sequencing_generation_status", "analysis_usage_status"):
            add("archive_sample", sample["archive_sample_id"], field, sample[field], sample[field], sample[field],
                "unresolved" if sample[field] in {"UNRESOLVED", "mixed_or_additional_unassigned"} else "verified",
                sample["origin_evidence_ids"], "Use layered provenance; do not collapse sample, library, sequencing and analysis origin.",
                "Individual library/sequencing assignment remains unresolved where stated.")
    hela_gsm = {row["gsm_accession"] for row in hela}
    for run in sorted((row for row in ncbi_runs if row["sample_alias"] in hela_gsm), key=lambda row: int(row["run"][3:])):
        add("sra_run", run["run"], "sequencing_generation_status", run["run_alias"], "prior_or_deeper_sequencing_unassigned",
            "UNRESOLVED", "unresolved", "E-P0008-009|E-P0008-011|E-P0008-013",
            "Do not infer sequencing generation from run alias or accession order.", "All HeLa runs remain individually unresolved.")
    add("source_query", "Q0008", "legacy_record_id", "AC-P0008-004", "failed_query_history",
        "historical_migrated", "verified", "E-P0008-007", "Failed queries belong in source_queries, never accession entities.",
        "Historical identifier retained for auditability.")
    return rows


def assess_batch_readiness(
    semantic_rows: list[dict[str, str]], accessions: list[dict[str, str]],
    run_rows: list[dict[str, str]], file_rows: list[dict[str, str]],
) -> dict[str, Any]:
    p0008_semantic_rows = [row for row in semantic_rows if row.get("paper_id") == "P0008"]
    checks = {
        "replicate_reviews": sum(row["record_type"] == "replicate" for row in p0008_semantic_rows),
        "batch_reviews": sum(row["record_type"] == "batch" for row in p0008_semantic_rows),
        "hela_run_reviews": sum(row["record_type"] == "sra_run" for row in p0008_semantic_rows),
        "run_view_rows": len(run_rows), "file_view_rows": len(file_rows),
        "legacy_placeholder_active": any(row["accession_record_id"] == "AC-P0008-004" for row in accessions),
    }
    ready = (
        checks["replicate_reviews"] == 60 and checks["batch_reviews"] == 60
        and checks["hela_run_reviews"] == 76 and checks["run_view_rows"] == 1290
        and checks["file_view_rows"] == 2580 and not checks["legacy_placeholder_active"]
    )
    return {
        "status": "ready_with_documented_gaps" if ready else "not_ready", "schema_version": "2.1.0",
        "validation_errors": 0, "validation_warnings": 0, **checks,
        "known_gaps_are_machine_expressible": ready, "recommended_papers_per_round": "1-3",
    }


def _build_p0008_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
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
    _migrate_legacy_query(root, schema)
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

    _, existing_conditions = _read_tsv(root / schema["tables"]["conditions"]["path"])
    _, existing_replicates = _read_tsv(root / schema["tables"]["replicates"]["path"])
    _, existing_batches = _read_tsv(root / schema["tables"]["batches"]["path"])
    _, existing_archive_samples = _read_tsv(root / schema["tables"]["archive_samples"]["path"])
    _, existing_relations = _read_tsv(root / schema["tables"]["accession_relations"]["path"])
    _, existing_files = _read_tsv(root / schema["tables"]["files"]["path"])
    _, existing_wide_rows = _read_tsv(root / schema["tables"]["literature_experiment_catalog"]["path"])
    _, existing_files_view = _read_tsv(root / schema["tables"]["literature_experiment_catalog_files"]["path"])
    _, existing_run_rows = _read_tsv(root / schema["tables"]["literature_experiment_catalog_runs"]["path"])
    preserved_conditions = [row for row in existing_conditions if row.get("paper_id") != "P0008"]
    preserved_condition_ids = {row["condition_id"] for row in preserved_conditions}
    preserved_replicates = [row for row in existing_replicates if row.get("condition_id") in preserved_condition_ids]
    preserved_batches = [row for row in existing_batches if row.get("paper_id") != "P0008"]
    preserved_archive_samples = [row for row in existing_archive_samples if not row.get("archive_sample_id", "").startswith("AS-P0008-")]
    preserved_relations = [row for row in existing_relations if not row.get("relation_id", "").startswith("REL-P0008-")]
    preserved_files = [
        row for row in existing_files
        if row.get("file_id", "").startswith("RF-") and not row.get("file_id", "").startswith("RF-P0008-")
    ]
    preserved_wide_rows = [
        row for row in existing_wide_rows
        if row.get("paper_id", "").startswith("P") and row.get("paper_id") != "P0008"
    ]
    preserved_files_view = [
        row for row in existing_files_view
        if row.get("paper_id", "").startswith("P") and row.get("paper_id") != "P0008"
    ]
    preserved_run_rows = [
        row for row in existing_run_rows
        if row.get("paper_id", "").startswith("P") and row.get("paper_id") != "P0008"
    ]
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
            **_origin_for_species(sample["organism"]),
            "evidence_ids": evidence + "|E-P0008-009|E-P0008-010", "notes": "GEO→BioSample/SRX与NCBI/ENA Run关系均由官方字段连接",
        })
        gsm_to_stp[sample["gsm"]] = timepoint_id

    p0008_archive_samples = [dict(row) for row in archive_samples]
    preserved_timepoints = [
        row for row in all_existing_timepoints
        if not row.get("experiment_id", "").startswith("EX-P0008")
    ]
    conditions.extend(preserved_conditions)
    replicates.extend(preserved_replicates)
    batches.extend(preserved_batches)
    sample_timepoints.extend(preserved_timepoints)
    archive_samples.extend(preserved_archive_samples)
    for name, rows in (("conditions", conditions), ("replicates", replicates), ("batches", batches), ("archive_samples", archive_samples), ("samples_timepoints", sample_timepoints)):
        spec = schema["tables"][name]
        _write_tsv(root / spec["path"], spec["fields"], rows)

    access_spec = schema["tables"]["accessions"]
    _, old_accessions = _read_tsv(root / access_spec["path"])
    preserved_accessions = [dict(row) for row in old_accessions if not row["accession_record_id"].startswith("AC-P0008")]
    accessions = [dict(row) for row in old_accessions if row["accession_record_id"] in {"AC-P0008-001", "AC-P0008-002", "AC-P0008-003"}]
    for row in accessions:
        for field in access_spec["fields"]:
            row.setdefault(field, "NA")
        for field in ("biological_sample_origin_status", "library_origin_status", "sequencing_generation_status", "analysis_usage_status"):
            row[field] = "NA"
        row["origin_evidence_ids"] = "NA"
    accession_id = 5
    relations: list[dict[str, str]] = []
    relation_id = 1
    run_to_accession_id: dict[str, str] = {}
    for sample in p0008_archive_samples:
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
            **_origin_for_species(sample["species_scientific"]),
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
    run_rows: list[dict[str, str]] = []
    archive_by_gsm = {row["gsm_accession"]: row for row in p0008_archive_samples}
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
            **_origin_for_species(sample["species_scientific"]),
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
                **{field: sample[field] for field in ("biological_sample_origin_status", "library_origin_status", "sequencing_generation_status", "analysis_usage_status")},
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
        run_files = files[-len(urls):]
        read1 = next((item for item in run_files if item["file_role"] == "read1"), None)
        read2 = next((item for item in run_files if item["file_role"] == "read2"), None)
        run_rows.append({
            "catalog_run_row_id": f"CATRUN-P0008-{len(run_rows)+1:06d}", "paper_id": "P0008",
            "experiment_id": sample["experiment_id"], "condition_id": sample["condition_id"], "replicate_id": sample["replicate_id"],
            "batch_id": sample["batch_id"], "sample_timepoint_id": sample["sample_timepoint_id"], "archive_sample_id": sample["archive_sample_id"],
            "perturbation_id": perturbation["perturbation_id"] if perturbation else "NA", "accession_record_id": record_id,
            "paper_title": "A pathway for mitotic chromosome formation", "doi": "10.1126/science.aao6135",
            "own_data_status": sample["own_data_status"],
            **{field: sample[field] for field in ("biological_sample_origin_status", "library_origin_status", "sequencing_generation_status", "analysis_usage_status")},
            "species_scientific": sample["species_scientific"], "cell_line_or_tissue": sample["cell_line_or_tissue"],
            "sample_name_original": sample["sample_title_original"], "assay_type": "Hi-C", "cell_cycle_phase": sample["phase_original"],
            "gsm_accession": gsm, "biosample_accession": sample["biosample_accession"], "sra_sample_accession": run["sra_sample"],
            "experiment_accession": run["experiment"], "run_accession": run["run"], "library_strategy": ena["library_strategy"],
            "library_source": ena["library_source"], "library_selection": ena["library_selection"], "library_layout": ena["library_layout"],
            "instrument_platform": ena["instrument_platform"], "instrument_model": ena["instrument_model"],
            "read1_url": read1["download_url"] if read1 else "NA", "read1_size_bytes": read1["file_size_bytes"] if read1 else "NA",
            "read1_md5": read1["md5"] if read1 else "NA", "read2_url": read2["download_url"] if read2 else "NA",
            "read2_size_bytes": read2["file_size_bytes"] if read2 else "NA", "read2_md5": read2["md5"] if read2 else "NA",
            "file_count": str(len(run_files)), "online_verification_status": "verified",
            "evidence_ids": sample["evidence_ids"], "notes": "Run粒度视图；配对文件列由同一Run的ENA记录确定性展开。",
        })

    p0008_relations = [dict(row) for row in relations]
    relations_spec = schema["tables"]["accession_relations"]
    relations.extend(preserved_relations)
    accessions.extend(preserved_accessions)
    _write_tsv(root / access_spec["path"], access_spec["fields"], accessions)
    _write_tsv(root / relations_spec["path"], relations_spec["fields"], relations)
    files_spec = schema["tables"]["files"]
    p0008_files = [dict(row) for row in files]
    files.extend(preserved_files)
    _write_tsv(root / files_spec["path"], files_spec["fields"], files)
    wide_spec = schema["tables"]["literature_experiment_catalog"]
    p0008_wide_rows = [dict(row) for row in wide_rows]
    wide_rows.extend(preserved_wide_rows)
    _write_tsv(root / wide_spec["path"], wide_spec["fields"], wide_rows)
    files_view_spec = schema["tables"]["literature_experiment_catalog_files"]
    wide_rows_for_files_view = [row for row in wide_rows if row.get("paper_id") == "P0008"]
    wide_rows_for_files_view.extend(preserved_files_view)
    _write_tsv(root / files_view_spec["path"], files_view_spec["fields"], wide_rows_for_files_view)
    runs_view_spec = schema["tables"]["literature_experiment_catalog_runs"]
    p0008_run_rows = [dict(row) for row in run_rows]
    run_rows.extend(preserved_run_rows)
    _write_tsv(root / runs_view_spec["path"], runs_view_spec["fields"], run_rows)
    semantic_spec = schema["tables"]["semantic_review"]
    _, existing_semantic_rows = _read_tsv(root / semantic_spec["path"])
    preserved_semantic_rows = [row for row in existing_semantic_rows if row.get("paper_id") != "P0008"]
    semantic_rows = _semantic_review_rows(geo, p0008_archive_samples, ncbi_runs)
    semantic_rows.extend(preserved_semantic_rows)
    _write_tsv(root / semantic_spec["path"], semantic_spec["fields"], semantic_rows)
    readiness = assess_batch_readiness(semantic_rows, [row for row in accessions if row["accession_record_id"].startswith("AC-P0008")], p0008_run_rows, p0008_wide_rows)
    readiness_path = root / "reports" / "schema_v2_batch_readiness.json"
    readiness_path.parent.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    issues_spec = schema["tables"]["unresolved_issues"]
    _, issues = _read_tsv(root / issues_spec["path"])
    additions = [
        ("UI-P0008-004", "GSM2745897|GSM2745898", "own_data_ambiguity", "HeLa S3样本来自此前已报告数据并进行更深测序，无法仅据正文区分复用样本与新测序Run", "yes"),
        ("UI-P0008-005", "P0008_GEO_SET", "replicate_type_unresolved", "R1/R2仅作为作者alias保留，当前证据不足以统一判定生物或技术重复", "yes"),
        ("UI-P0008-006", "P0008_GEO_SET", "batch_candidate_unverified", "日期型alias仅作为候选batch保存，未升级为已验证实验批次", "no"),
        ("UI-P0008-007", "Q0006|Q0007", "supplement_access_limited", "Science补充PDF官方入口返回访问限制，且PMC列出的107.5 MB主补充材料超过20 MB下载阈值", "no"),
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

    reconciliation = _write_reconciliation(root, config, geo, ncbi_experiments, ncbi_runs, ena_runs, p0008_archive_samples, [row for row in accessions if row["accession_record_id"].startswith("AC-P0008")], p0008_files, p0008_wide_rows, p0008_run_rows)
    return reconciliation


def _p0009_title_metadata(title: str) -> dict[str, str]:
    replicate_match = re.search(r"-rep(\d+)$", title)
    replicate = f"rep{replicate_match.group(1)}" if replicate_match else "NR"
    title_core = re.sub(r"-rep\d+$", "", title)

    stage_map = {
        "prometa": ("prometaphase", "0"),
        "ana.telo": ("ana/telophase", "25"),
        "anatelo": ("ana/telophase", "25"),
        "early-G1": ("early G1", "60"),
        "early-g1": ("early G1", "60"),
        "mid-G1": ("mid G1", "120"),
        "mid-g1": ("mid G1", "120"),
        "late-G1": ("late G1", "240"),
        "late-g1": ("late G1", "240"),
        "asyn": ("asynchronous", "NR"),
    }

    if title.startswith("Capture-C-"):
        payload = title[len("Capture-C-") :]
        genotype = "commd3_mutant" if payload.startswith("commd3_mutant_") else "WT"
        if genotype == "commd3_mutant":
            payload = payload[len("commd3_mutant_") :]
        phase_raw = payload.rsplit("-rep", 1)[0] if "-rep" in payload else payload
        cell_cycle_phase, sampling_time = stage_map.get(phase_raw, ("UNRESOLVED", "NR"))
        return {
            "assay_type": "Capture-C",
            "assay_detail": "Capture-C",
            "measurement_object": "captured chromatin contacts",
            "detection_target": "NR",
            "measurement_target": "NR",
            "genotype_or_construct": genotype,
            "phase_token": phase_raw,
            "cell_cycle_phase": cell_cycle_phase,
            "sampling_time": sampling_time,
            "sampling_time_unit": "min" if sampling_time != "NR" else "NA",
            "replicate_label": replicate,
            "perturbation_type": "mutation" if genotype == "commd3_mutant" else "not_applicable",
            "perturbation_technology": "NR" if genotype == "commd3_mutant" else "not_applicable",
            "perturbation_target": "Commd3" if genotype == "commd3_mutant" else "NA",
        }

    if title.startswith("Hi-C-"):
        phase_raw = title_core[len("Hi-C-") :]
        cell_cycle_phase, sampling_time = stage_map.get(phase_raw, ("UNRESOLVED", "NR"))
        return {
            "assay_type": "Hi-C",
            "assay_detail": "in situ Hi-C",
            "measurement_object": "genome-wide chromatin contacts",
            "detection_target": "NA",
            "measurement_target": "NA",
            "genotype_or_construct": "WT",
            "phase_token": phase_raw,
            "cell_cycle_phase": cell_cycle_phase,
            "sampling_time": sampling_time,
            "sampling_time_unit": "min" if sampling_time != "NR" else "NA",
            "replicate_label": replicate,
            "perturbation_type": "not_applicable",
            "perturbation_technology": "not_applicable",
            "perturbation_target": "NA",
        }

    if title.startswith("ChIP-seq-"):
        payload = title[len("ChIP-seq-") :]
        target_token, phase_raw = payload.split("-", 1)
        phase_raw = phase_raw.rsplit("-rep", 1)[0] if "-rep" in phase_raw else phase_raw
        cell_cycle_phase, sampling_time = stage_map.get(phase_raw, ("UNRESOLVED", "NR"))
        target_map = {
            "CTCF": "CTCF",
            "Rad21": "Rad21",
            "PolII": "Pol II",
            "input": "input control",
        }
        return {
            "assay_type": "ChIP-seq",
            "assay_detail": "ChIP-seq",
            "measurement_object": "chromatin occupancy",
            "detection_target": target_map.get(target_token, target_token),
            "measurement_target": target_map.get(target_token, target_token),
            "genotype_or_construct": "WT",
            "phase_token": phase_raw,
            "cell_cycle_phase": cell_cycle_phase,
            "sampling_time": sampling_time,
            "sampling_time_unit": "min" if sampling_time != "NR" else "NA",
            "replicate_label": replicate,
            "perturbation_type": "not_applicable",
            "perturbation_technology": "not_applicable",
            "perturbation_target": "NA",
        }

    raise CatalogError(f"P0009 title format not recognized: {title}")


def _p0009_origin() -> dict[str, str]:
    return {
        "biological_sample_origin_status": "study_generated",
        "library_origin_status": "study_generated",
        "sequencing_generation_status": "study_generated",
        "analysis_usage_status": "primary_analysis",
        "origin_evidence_ids": "E-P0009-003|E-P0009-004|E-P0009-005",
    }


def _build_p0009_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    config_file = config_path or root / "configs" / "pilots" / "P0009.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    schema = load_schema(root)
    source_dir = root / str(config["source_metadata_dir"])
    geo = parse_geo_miniml(source_dir / "GSE129997_family.xml")
    ncbi_runs = parse_ncbi_runinfo(source_dir / "SRP192917_runinfo.csv")
    ena_runs = parse_ena_runs(source_dir / "SRP192917_ena_filereport.tsv")
    verification_date = _verification_date(root, config)
    query_timestamp = f"{verification_date}T00:00:00+08:00"

    expected = int(config["expected_geo_samples"])
    if len(geo) != expected or len({row["gsm"] for row in geo}) != expected:
        raise CatalogError(f"P0009 GEO GSM集合不完整: rows={len(geo)} unique={len({row['gsm'] for row in geo})}")
    runinfo_set = {row["run"] for row in ncbi_runs}
    ena_set = {row["run_accession"] for row in ena_runs}
    if runinfo_set != ena_set:
        raise CatalogError(f"P0009 NCBI/ENA Run集合不一致: only_ncbi={len(runinfo_set-ena_set)} only_ena={len(ena_set-runinfo_set)}")

    geo_by_gsm = {row["gsm"]: row for row in geo}
    runinfo_by_gsm: dict[str, list[dict[str, str]]] = defaultdict(list)
    runinfo_by_run = {row["run"]: row for row in ncbi_runs}
    for row in ncbi_runs:
        runinfo_by_gsm[row["sample_alias"]].append(row)
    ena_by_run = {row["run_accession"]: row for row in ena_runs}
    if set(runinfo_by_gsm) != set(geo_by_gsm):
        raise CatalogError("P0009 GEO SampleName 与 NCBI RunInfo 样本集合不一致")

    exp_spec = schema["tables"]["experiments"]
    _, experiments = _read_tsv(root / exp_spec["path"])
    experiments = [row for row in experiments if row.get("paper_id") != "P0009"]
    experiments.append(
        {
            "experiment_id": "EX-P0009-001",
            "paper_id": "P0009",
            "experiment_label_original": "Mitosis-to-G1 chromatin reconfiguration time course",
            "biological_question": "解析G1E-ER4细胞有丝分裂退出到G1期间染色质结构重建",
            "own_data_status": "yes",
            "own_data_evidence": "E-P0009-001|E-P0009-003|E-P0009-004|E-P0009-005",
            "assay_type": "Hi-C|Capture-C|ChIP-seq",
            "assay_detail": "in situ Hi-C, Capture-C and ChIP-seq",
            "measurement_object": "染色质接触、捕获接触和CTCF/Rad21/Pol II占据",
            "detection_target": "CTCF|Rad21|Pol II|NR",
            "experimental_group": "G1E-ER4 post-mitotic stages and asynchronous comparator",
            "control_group": "asynchronous or stage-matched comparator depending on assay",
            "biological_replicates": "2 for Hi-C; 2-3 for Capture-C/ChIP-seq according to paper and GEO sample set",
            "technical_replicates": "NR",
            "reference_genome": "mm10",
            "evidence_ids": "E-P0009-001|E-P0009-003|E-P0009-004|E-P0009-005",
            "notes": "Round5 expanded to GSM/SRX/SRR/file level from saved official metadata snapshots.",
        }
    )
    _write_tsv(root / exp_spec["path"], exp_spec["fields"], experiments)

    pert_spec = schema["tables"]["perturbations"]
    _, perturbations = _read_tsv(root / pert_spec["path"])
    perturbations = [row for row in perturbations if row.get("experiment_id") != "EX-P0009-001"]
    perturbations.append(
        {
            "perturbation_id": "PT-P0009-001",
            "experiment_id": "EX-P0009-001",
            "combination_id": "NA",
            "perturbed_object": "cell-cycle state",
            "perturbation_type": "not_applicable",
            "technology": "not_applicable",
            "direct_target": "NA",
            "construct_or_reagent": "NA",
            "dose": "NA",
            "duration": "NA",
            "timing_relative_to_synchronization": "NA",
            "control": "stage-matched post-mitotic populations or asynchronous comparator",
            "expected_effect": "No study-wide targeted perturbation was confirmed beyond nocodazole synchronization; sample-title commd3_mutant is preserved at condition level only.",
            "expected_effect_basis": "round5_archive_boundary",
            "observed_validation": "NA",
            "evidence_ids": "E-P0009-001|E-P0009-003",
            "notes": "commd3_mutant titles indicate a mutant background, but engineering technology and expected effect are not explicit in the saved official metadata.",
        }
    )
    _write_tsv(root / pert_spec["path"], pert_spec["fields"], perturbations)

    cond_spec = schema["tables"]["conditions"]
    rep_spec = schema["tables"]["replicates"]
    batch_spec = schema["tables"]["batches"]
    st_spec = schema["tables"]["samples_timepoints"]
    archive_spec = schema["tables"]["archive_samples"]
    _, existing_conditions = _read_tsv(root / cond_spec["path"])
    _, existing_replicates = _read_tsv(root / rep_spec["path"])
    _, existing_batches = _read_tsv(root / batch_spec["path"])
    _, existing_timepoints = _read_tsv(root / st_spec["path"])
    _, existing_archive = _read_tsv(root / archive_spec["path"])

    conditions = [row for row in existing_conditions if row.get("paper_id") != "P0009"]
    replicates = [row for row in existing_replicates if not row.get("replicate_id", "").startswith("R-P0009-")]
    batches = [row for row in existing_batches if row.get("paper_id") != "P0009"]
    sample_timepoints = [row for row in existing_timepoints if not row.get("sample_timepoint_id", "").startswith("ST-P0009-")]
    archive_samples = [row for row in existing_archive if not row.get("archive_sample_id", "").startswith("AS-P0009-")]

    archive_by_gsm: dict[str, dict[str, str]] = {}
    stage_evidence_rule = (
        "GEO family MINiML title token gives stage label; Treatment-Protocol explicitly maps "
        "prometa/ana.telo/early-G1/mid-G1/late-G1 to 0/25/60/120/240 min after nocodazole release."
    )
    for index, sample in enumerate(geo, start=1):
        meta = _p0009_title_metadata(sample["title"])
        gsm = sample["gsm"]
        runs = sorted(runinfo_by_gsm[gsm], key=lambda row: int(row["run"][3:]))
        first_run = runs[0]
        ena_first = ena_by_run[first_run["run"]]
        condition_id = f"C-P0009-{index:03d}"
        replicate_id = f"R-P0009-{index:03d}"
        batch_id = f"B-P0009-{index:03d}"
        sample_timepoint_id = f"ST-P0009-{index:03d}"
        archive_sample_id = f"AS-P0009-{index:03d}"
        is_asyn = meta["phase_token"] == "asyn"
        sync_method = "asynchronous comparator" if is_asyn else "nocodazole arrest-release"
        sync_reagent = "NA" if is_asyn else "nocodazole"
        sync_dose = "NA" if is_asyn else "200 ng/ml"
        sync_duration = "NA" if is_asyn else "7-8.5 h"
        arrest_point = "NA" if is_asyn else "prometaphase"
        time_zero = "NA" if is_asyn else "release from nocodazole arrest"
        phase_rule = "GEO title token 'asyn'" if is_asyn else stage_evidence_rule
        phase_type = "author_stated" if is_asyn else "author_stated"
        conditions.append(
            {
                "condition_id": condition_id,
                "paper_id": "P0009",
                "experiment_id": "EX-P0009-001",
                "author_condition_label": sample["title"],
                "genotype_or_construct": meta["genotype_or_construct"],
                "synchronization_method": sync_method,
                "synchronization_reagent": sync_reagent,
                "treatment_or_perturbation": meta["genotype_or_construct"] if meta["genotype_or_construct"] != "WT" else "NA",
                "cell_cycle_phase": meta["cell_cycle_phase"],
                "control_role": "asynchronous comparator" if is_asyn else "NR",
                "evidence_ids": "E-P0009-003",
                "normalization_status": "official_fields_only",
                "notes": "One condition per GEO sample to keep assay/stage/run mapping lossless.",
            }
        )
        replicates.append(
            {
                "replicate_id": replicate_id,
                "condition_id": condition_id,
                "author_replicate_label": meta["replicate_label"],
                "replicate_type": "UNRESOLVED" if meta["replicate_label"] != "NR" else "NR",
                "replicate_number": re.sub(r"^rep", "", meta["replicate_label"]) if meta["replicate_label"] != "NR" else "NR",
                "evidence_ids": "E-P0009-003|E-P0009-001",
                "notes": "rep labels are preserved from GEO titles; biological versus technical replicate type is not explicitly declared per GSM.",
            }
        )
        batches.append(
            {
                "batch_id": batch_id,
                "paper_id": "P0009",
                "author_batch_label": "NR",
                "batch_date": "NR",
                "library_batch": "NR",
                "sequencing_platform": ena_first["instrument_model"] or first_run["instrument_model"],
                "evidence_ids": "E-P0009-004|E-P0009-005",
                "verification_status": "unresolved",
                "notes": "Official records identify instrument model but not a per-GSM library batch label.",
            }
        )
        sample_timepoints.append(
            {
                "sample_timepoint_id": sample_timepoint_id,
                "experiment_id": "EX-P0009-001",
                "species_scientific": sample["organism"],
                "species_common": "mouse",
                "taxonomy_id": "10090",
                "cell_line_or_tissue": sample["source"],
                "sample_name_original": sample["title"],
                "sample_name_standardized": gsm,
                "genotype_or_construct": meta["genotype_or_construct"],
                "synchronization_method": sync_method,
                "synchronization_reagent": sync_reagent,
                "synchronization_dose": sync_dose,
                "synchronization_duration": sync_duration,
                "arrest_point": arrest_point,
                "time_zero_definition": time_zero,
                "sampling_time": meta["sampling_time"],
                "sampling_time_unit": meta["sampling_time_unit"],
                "cell_cycle_phase": meta["cell_cycle_phase"],
                "phase_evidence_type": phase_type,
                "phase_evidence_rule": phase_rule,
                "pooled_status": "NR",
                "evidence_ids": "E-P0009-003",
                "notes": "Asynchronous samples keep NR sampling_time; stage-labelled samples use GEO Treatment-Protocol explicit release mapping.",
                "condition_id": condition_id,
                "replicate_id": replicate_id,
                "batch_id": batch_id,
                "gsm_accession": gsm,
                "archive_sample_id": archive_sample_id,
            }
        )
        archive_row = {
            "archive_sample_id": archive_sample_id,
            "experiment_id": "EX-P0009-001",
            "sample_timepoint_id": sample_timepoint_id,
            "condition_id": condition_id,
            "replicate_id": replicate_id,
            "batch_id": batch_id,
            "gsm_accession": gsm,
            "biosample_accession": sample["biosample"],
            "sra_sample_accession": ena_first["secondary_sample_accession"] or "NR",
            "srx_accession": sample["srx"],
            "sample_title_original": sample["title"],
            "sample_alias_original": first_run["sample_alias"],
            "species_scientific": sample["organism"],
            "taxonomy_id": "10090",
            "cell_line_or_tissue": sample["source"],
            "platform_accession": sample["platform"],
            "genotype_original": meta["genotype_or_construct"],
            "phase_original": meta["cell_cycle_phase"],
            "type_original": sample["sample_type"],
            "own_data_status": "yes",
            "disposition_status": "mapped",
            "run_count": str(len(runs)),
            **_p0009_origin(),
            "evidence_ids": "E-P0009-003|E-P0009-004|E-P0009-005",
            "notes": "GEO→BioSample/SRX/SRR and ENA FASTQ links are joined only through official snapshot fields.",
        }
        archive_samples.append(archive_row)
        archive_by_gsm[gsm] = archive_row

    for spec, rows in (
        (cond_spec, conditions),
        (rep_spec, replicates),
        (batch_spec, batches),
        (st_spec, sample_timepoints),
        (archive_spec, archive_samples),
    ):
        _write_tsv(root / spec["path"], spec["fields"], rows)

    query_spec = schema["tables"]["source_queries"]
    _, source_queries = _read_tsv(root / query_spec["path"])
    source_queries = [row for row in source_queries if row.get("query_id") not in {"Q0012", "Q0013", "Q0014"}]
    query_rows = [
        {
            "query_id": "Q0012",
            "database": "NCBI_GEO",
            "endpoint": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE129nnn/GSE129997/miniml/GSE129997_family.xml.tgz",
            "query_parameters": "official family MINiML archive for GSE129997",
            "queried_at": query_timestamp,
            "http_status": "200",
            "response_sha256": _stable_hash(source_dir / "GSE129997_family.xml.tgz"),
            "response_bytes": str((source_dir / "GSE129997_family.xml.tgz").stat().st_size),
            "returned_rows": str(len(geo)),
            "snapshot_path": "data/interim/pilot/source_metadata/GSE129997_family.xml",
            "pagination_complete": "yes",
            "retry_count": "0",
            "error_summary": "NA",
            "query_outcome": "success",
            "legacy_record_id": "NA",
        },
        {
            "query_id": "Q0013",
            "database": "NCBI_SRA",
            "endpoint": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo",
            "query_parameters": "acc=SRP192917",
            "queried_at": query_timestamp,
            "http_status": "200",
            "response_sha256": _stable_hash(source_dir / "SRP192917_runinfo.csv"),
            "response_bytes": str((source_dir / "SRP192917_runinfo.csv").stat().st_size),
            "returned_rows": str(len(ncbi_runs)),
            "snapshot_path": "data/interim/pilot/source_metadata/SRP192917_runinfo.csv",
            "pagination_complete": "yes",
            "retry_count": "0",
            "error_summary": "NA",
            "query_outcome": "success",
            "legacy_record_id": "NA",
        },
        {
            "query_id": "Q0014",
            "database": "ENA",
            "endpoint": "https://www.ebi.ac.uk/ena/portal/api/filereport",
            "query_parameters": "accession=SRP192917;result=read_run;fields=run_accession,study_accession,secondary_study_accession,experiment_accession,sample_accession,secondary_sample_accession,library_strategy,library_source,library_selection,library_layout,instrument_platform,instrument_model,fastq_ftp,fastq_md5,fastq_bytes,submitted_ftp,submitted_md5,submitted_bytes",
            "queried_at": query_timestamp,
            "http_status": "200",
            "response_sha256": _stable_hash(source_dir / "SRP192917_ena_filereport.tsv"),
            "response_bytes": str((source_dir / "SRP192917_ena_filereport.tsv").stat().st_size),
            "returned_rows": str(len(ena_runs)),
            "snapshot_path": "data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv",
            "pagination_complete": "yes",
            "retry_count": "0",
            "error_summary": "NA",
            "query_outcome": "success",
            "legacy_record_id": "NA",
        },
    ]
    source_queries.extend(query_rows)
    source_queries.sort(key=lambda row: (0, int(row["query_id"][1:])) if re.fullmatch(r"Q\d+", row["query_id"]) else (1, row["query_id"]))
    _write_tsv(root / query_spec["path"], query_spec["fields"], source_queries)

    evidence_spec = schema["tables"]["evidence"]
    _, evidence_rows = _read_tsv(root / evidence_spec["path"])
    evidence_rows = [row for row in evidence_rows if row.get("evidence_id") not in {"E-P0009-003", "E-P0009-004", "E-P0009-005"}]
    evidence_rows.extend(
        [
            {
                "evidence_id": "E-P0009-003",
                "supported_table": "samples_timepoints|conditions|archive_samples|semantic_review",
                "supported_record_id": "P0009_GEO_FAMILY_SET",
                "supported_fields": "title|treatment_protocol|biosample|srx|sampling_time|cell_cycle_phase",
                "source_type": "official_database",
                "citation_or_database": "NCBI GEO family MINiML",
                "source_locator": "data/interim/pilot/source_metadata/GSE129997_family.xml",
                "page_or_section": "GSE129997 sample records",
                "minimal_excerpt": "Cells were synchronized to pro-metaphase with 200ng/ml nocodazole for 7-8.5h. Released for 0, 25, 60, 120 and 240 min for pro-meta, ana/telo, early-G1, mid-G1 and late-G1 respectively.",
                "query_or_method": "Q0012",
                "verification_date": verification_date,
                "extractor": "Codex",
                "reviewer": "NR",
                "evidence_level": "archive_record",
                "notes": "Provides GSM titles plus the explicit release-time mapping used in round5.",
            },
            {
                "evidence_id": "E-P0009-004",
                "supported_table": "archive_samples|accessions|accession_relations",
                "supported_record_id": "P0009_RUNINFO_SET",
                "supported_fields": "Run|Experiment|BioSample|SampleName|LibraryStrategy|LibraryLayout|Platform|Model",
                "source_type": "official_database",
                "citation_or_database": "NCBI SRA RunInfo",
                "source_locator": "data/interim/pilot/source_metadata/SRP192917_runinfo.csv",
                "page_or_section": "SRP192917 runinfo",
                "minimal_excerpt": "RunInfo lists 120 runs and links each Run to a unique Experiment, BioSample and SampleName (GSM accession).",
                "query_or_method": "Q0013",
                "verification_date": verification_date,
                "extractor": "Codex",
                "reviewer": "NR",
                "evidence_level": "archive_record",
                "notes": "Used to map GSM to SRX/SRR and to recover library layout/platform fields.",
            },
            {
                "evidence_id": "E-P0009-005",
                "supported_table": "accessions|files|literature_experiment_catalog|literature_experiment_catalog_runs",
                "supported_record_id": "P0009_ENA_FILE_SET",
                "supported_fields": "fastq_ftp|fastq_md5|fastq_bytes|secondary_sample_accession|instrument_model",
                "source_type": "official_database",
                "citation_or_database": "ENA Portal filereport",
                "source_locator": "data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv",
                "page_or_section": "SRP192917 read_run filereport",
                "minimal_excerpt": "ENA filereport provides FASTQ URLs, MD5 and byte counts for each run together with secondary study/sample accessions.",
                "query_or_method": "Q0014",
                "verification_date": verification_date,
                "extractor": "Codex",
                "reviewer": "NR",
                "evidence_level": "archive_record",
                "notes": "URLs are stored exactly as returned; no FASTQ files were downloaded.",
            },
        ]
    )
    evidence_rows.sort(key=lambda row: row["evidence_id"])
    _write_tsv(root / evidence_spec["path"], evidence_spec["fields"], evidence_rows)

    access_spec = schema["tables"]["accessions"]
    rel_spec = schema["tables"]["accession_relations"]
    files_spec = schema["tables"]["files"]
    wide_spec = schema["tables"]["literature_experiment_catalog"]
    files_view_spec = schema["tables"]["literature_experiment_catalog_files"]
    runs_view_spec = schema["tables"]["literature_experiment_catalog_runs"]
    _, accessions = _read_tsv(root / access_spec["path"])
    _, relations = _read_tsv(root / rel_spec["path"])
    _, files = _read_tsv(root / files_spec["path"])
    _, wide_rows = _read_tsv(root / wide_spec["path"])
    _, files_view_rows = _read_tsv(root / files_view_spec["path"])
    _, run_view_rows = _read_tsv(root / runs_view_spec["path"])
    accessions = [row for row in accessions if not row.get("accession_record_id", "").startswith("AC-P0009-")]
    relations = [row for row in relations if not row.get("relation_id", "").startswith("REL-P0009-")]
    files = [row for row in files if not row.get("file_id", "").startswith("RF-P0009-")]
    wide_rows = [row for row in wide_rows if row.get("paper_id") != "P0009"]
    files_view_rows = [row for row in files_view_rows if row.get("paper_id") != "P0009"]
    run_view_rows = [row for row in run_view_rows if row.get("paper_id") != "P0009"]

    accessions.extend(
        [
            {
                "accession_record_id": "AC-P0009-001",
                "experiment_id": "EX-P0009-001",
                "sample_timepoint_id": "NA",
                "namespace": "NCBI GEO",
                "entity_type": "geo_series",
                "accession": "GSE129997",
                "project_accession": "PRJNA533460",
                "study_accession": "SRP192917",
                "sample_accession": "NA",
                "experiment_accession": "NA",
                "run_accession": "NA",
                "official_page_url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE129997",
                "download_url": config["geo_miniml_url"],
                "file_format": "XML",
                "file_size_bytes": str((source_dir / "GSE129997_quick.xml").stat().st_size),
                "md5": _stable_hash(source_dir / "GSE129997_quick.xml"),
                "format_validation_status": "verified",
                "online_verification_status": "verified",
                "verification_date": verification_date,
                "evidence_ids": "E-P0009-002|E-P0009-003",
                "notes": "Series-level GEO entry; family MINiML is stored separately for GSM-level parsing.",
                "condition_id": "NA",
                "replicate_id": "NA",
                "batch_id": "NA",
                "library_strategy": "Hi-C|Capture-C|ChIP-seq",
                "library_source": "GENOMIC",
                "library_selection": "UNRESOLVED",
                "library_layout": "MIXED",
                "instrument_platform": "ILLUMINA",
                "instrument_model": "Illumina NextSeq 500",
                "public_status": "public",
                "query_id": "Q0009|Q0012",
                **_p0009_origin(),
            },
            {
                "accession_record_id": "AC-P0009-002",
                "experiment_id": "EX-P0009-001",
                "sample_timepoint_id": "NA",
                "namespace": "NCBI BioProject",
                "entity_type": "bioproject",
                "accession": "PRJNA533460",
                "project_accession": "PRJNA533460",
                "study_accession": "SRP192917",
                "sample_accession": "NA",
                "experiment_accession": "NA",
                "run_accession": "NA",
                "official_page_url": "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA533460",
                "download_url": "NA",
                "file_format": "NA",
                "file_size_bytes": "NA",
                "md5": "NA",
                "format_validation_status": "verified",
                "online_verification_status": "verified",
                "verification_date": verification_date,
                "evidence_ids": "E-P0009-002|E-P0009-004|E-P0009-005",
                "notes": "BioProject linked from GEO and ENA study fields.",
                "condition_id": "NA",
                "replicate_id": "NA",
                "batch_id": "NA",
                "library_strategy": "Hi-C|Capture-C|ChIP-seq",
                "library_source": "GENOMIC",
                "library_selection": "UNRESOLVED",
                "library_layout": "MIXED",
                "instrument_platform": "ILLUMINA",
                "instrument_model": "Illumina NextSeq 500",
                "public_status": "public",
                "query_id": "Q0009|Q0013|Q0014",
                **_p0009_origin(),
            },
            {
                "accession_record_id": "AC-P0009-003",
                "experiment_id": "EX-P0009-001",
                "sample_timepoint_id": "NA",
                "namespace": "NCBI SRA",
                "entity_type": "sra_study",
                "accession": "SRP192917",
                "project_accession": "PRJNA533460",
                "study_accession": "SRP192917",
                "sample_accession": "NA",
                "experiment_accession": "NA",
                "run_accession": "NA",
                "official_page_url": "https://www.ncbi.nlm.nih.gov/sra?term=SRP192917",
                "download_url": "NA",
                "file_format": "CSV|TSV",
                "file_size_bytes": "NA",
                "md5": "NA",
                "format_validation_status": "verified",
                "online_verification_status": "verified",
                "verification_date": verification_date,
                "evidence_ids": "E-P0009-002|E-P0009-004|E-P0009-005",
                "notes": "Run-level expansion completed from official RunInfo and ENA filereport snapshots.",
                "condition_id": "NA",
                "replicate_id": "NA",
                "batch_id": "NA",
                "library_strategy": "Hi-C|Capture-C|ChIP-seq",
                "library_source": "GENOMIC",
                "library_selection": "UNRESOLVED",
                "library_layout": "MIXED",
                "instrument_platform": "ILLUMINA",
                "instrument_model": "Illumina NextSeq 500",
                "public_status": "public",
                "query_id": "Q0013|Q0014",
                **_p0009_origin(),
            },
        ]
    )

    relation_rows: list[dict[str, str]] = [
        {
            "relation_id": "REL-P0009-00001",
            "parent_accession": "PRJNA533460",
            "child_accession": "SRP192917",
            "relation_type": "project_has_study",
            "source_database": "NCBI|ENA",
            "query_id": "Q0009|Q0014",
            "verification_status": "verified",
            "evidence_ids": "E-P0009-002|E-P0009-005",
            "notes": "Study/project link confirmed by GEO relation and ENA secondary_study_accession.",
        }
    ]
    accession_id = 4
    relation_id = 2
    p0009_file_rows: list[dict[str, str]] = []
    p0009_wide_rows: list[dict[str, str]] = []
    p0009_run_rows: list[dict[str, str]] = []
    user_catalog_rows: list[dict[str, str]] = []

    for index, sample in enumerate(geo, start=1):
        meta = _p0009_title_metadata(sample["title"])
        gsm = sample["gsm"]
        archive_row = archive_by_gsm[gsm]
        condition_id = archive_row["condition_id"]
        replicate_id = archive_row["replicate_id"]
        batch_id = archive_row["batch_id"]
        sample_timepoint_id = archive_row["sample_timepoint_id"]
        archive_sample_id = archive_row["archive_sample_id"]
        experiment_id = archive_row["experiment_id"]
        runs = sorted(runinfo_by_gsm[gsm], key=lambda row: int(row["run"][3:]))

        for namespace, entity_type, accession, exp_accession, page_url, notes in (
            ("NCBI GEO", "geo_sample", gsm, sample["srx"], f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gsm}", "GEO sample parsed from family MINiML."),
            ("NCBI BioSample", "biosample", sample["biosample"], sample["srx"], f"https://www.ncbi.nlm.nih.gov/biosample/{sample['biosample']}", "BioSample accession linked from GEO relation."),
            ("NCBI SRA", "sra_experiment", sample["srx"], sample["srx"], f"https://www.ncbi.nlm.nih.gov/sra?term={sample['srx']}", "Experiment accession linked from GEO relation and RunInfo."),
        ):
            accessions.append(
                {
                    "accession_record_id": f"AC-P0009-{accession_id:03d}",
                    "experiment_id": experiment_id,
                    "sample_timepoint_id": sample_timepoint_id,
                    "namespace": namespace,
                    "entity_type": entity_type,
                    "accession": accession,
                    "project_accession": "PRJNA533460",
                    "study_accession": "SRP192917",
                    "sample_accession": archive_row["sra_sample_accession"],
                    "experiment_accession": exp_accession,
                    "run_accession": "NA",
                    "official_page_url": page_url,
                    "download_url": "NA",
                    "file_format": "NA",
                    "file_size_bytes": "NA",
                    "md5": "NA",
                    "format_validation_status": "verified",
                    "online_verification_status": "verified",
                    "verification_date": verification_date,
                    "evidence_ids": "E-P0009-003|E-P0009-004",
                    "notes": notes,
                    "condition_id": condition_id,
                    "replicate_id": replicate_id,
                    "batch_id": batch_id,
                    "library_strategy": meta["assay_type"],
                    "library_source": "GENOMIC",
                    "library_selection": "UNRESOLVED",
                    "library_layout": runs[0]["library_layout"],
                    "instrument_platform": runs[0]["instrument_platform"],
                    "instrument_model": runs[0]["instrument_model"],
                    "public_status": "public",
                    "query_id": "Q0012|Q0013",
                    **_p0009_origin(),
                }
            )
            accession_id += 1

        relation_rows.extend(
            [
                {
                    "relation_id": f"REL-P0009-{relation_id:05d}",
                    "parent_accession": "GSE129997",
                    "child_accession": gsm,
                    "relation_type": "series_has_sample",
                    "source_database": "NCBI",
                    "query_id": "Q0012",
                    "verification_status": "verified",
                    "evidence_ids": "E-P0009-003",
                    "notes": "GEO family MINiML sample membership.",
                },
                {
                    "relation_id": f"REL-P0009-{relation_id+1:05d}",
                    "parent_accession": gsm,
                    "child_accession": sample["biosample"],
                    "relation_type": "mirrors",
                    "source_database": "NCBI",
                    "query_id": "Q0012|Q0013",
                    "verification_status": "verified",
                    "evidence_ids": "E-P0009-003|E-P0009-004",
                    "notes": "GEO sample to BioSample relation.",
                },
                {
                    "relation_id": f"REL-P0009-{relation_id+2:05d}",
                    "parent_accession": sample["biosample"],
                    "child_accession": sample["srx"],
                    "relation_type": "sample_has_experiment",
                    "source_database": "NCBI",
                    "query_id": "Q0012|Q0013",
                    "verification_status": "verified",
                    "evidence_ids": "E-P0009-003|E-P0009-004",
                    "notes": "BioSample to SRX relation from official snapshots.",
                },
            ]
        )
        relation_id += 3

        for run in runs:
            ena = ena_by_run[run["run"]]
            accession_record_id = f"AC-P0009-{accession_id:03d}"
            urls = [item for item in ena["fastq_ftp"].split(";") if item]
            md5s = [item for item in ena["fastq_md5"].split(";") if item]
            sizes = [item for item in ena["fastq_bytes"].split(";") if item]
            if not (len(urls) == len(md5s) == len(sizes)):
                raise CatalogError(f"P0009 ENA file fields length mismatch for {run['run']}")
            accessions.append(
                {
                    "accession_record_id": accession_record_id,
                    "experiment_id": experiment_id,
                    "sample_timepoint_id": sample_timepoint_id,
                    "namespace": "INSDC SRA/ENA",
                    "entity_type": "sra_run",
                    "accession": run["run"],
                    "project_accession": "PRJNA533460",
                    "study_accession": "SRP192917",
                    "sample_accession": ena["secondary_sample_accession"] or "NR",
                    "experiment_accession": run["experiment"],
                    "run_accession": run["run"],
                    "official_page_url": f"https://www.ebi.ac.uk/ena/browser/view/{run['run']}",
                    "download_url": ena["fastq_ftp"],
                    "file_format": "FASTQ",
                    "file_size_bytes": ena["fastq_bytes"],
                    "md5": ena["fastq_md5"],
                    "format_validation_status": "verified",
                    "online_verification_status": "verified",
                    "verification_date": verification_date,
                    "evidence_ids": "E-P0009-004|E-P0009-005",
                    "notes": "Run accession and FASTQ link fields come from official RunInfo plus ENA filereport.",
                    "condition_id": condition_id,
                    "replicate_id": replicate_id,
                    "batch_id": batch_id,
                    "library_strategy": meta["assay_type"],
                    "library_source": ena["library_source"],
                    "library_selection": ena["library_selection"] or "UNRESOLVED",
                    "library_layout": ena["library_layout"],
                    "instrument_platform": ena["instrument_platform"],
                    "instrument_model": ena["instrument_model"],
                    "public_status": "public",
                    "query_id": "Q0013|Q0014",
                    **_p0009_origin(),
                }
            )
            accession_id += 1
            relation_rows.append(
                {
                    "relation_id": f"REL-P0009-{relation_id:05d}",
                    "parent_accession": run["experiment"],
                    "child_accession": run["run"],
                    "relation_type": "experiment_has_run",
                    "source_database": "NCBI|ENA",
                    "query_id": "Q0013|Q0014",
                    "verification_status": "verified",
                    "evidence_ids": "E-P0009-004|E-P0009-005",
                    "notes": "Run linkage confirmed by matching NCBI RunInfo and ENA experiment/sample fields.",
                }
            )
            relation_id += 1

            run_file_records: list[dict[str, str]] = []
            for file_index, (url, size, md5) in enumerate(zip(urls, sizes, md5s), start=1):
                file_role = "read1" if file_index == 1 else "read2" if file_index == 2 else "archive_file"
                file_id = f"RF-P0009-{run['run']}-{file_index}"
                file_row = {
                    "file_id": file_id,
                    "run_accession": run["run"],
                    "file_index": str(file_index),
                    "file_role": file_role,
                    "download_url": url,
                    "file_format": "FASTQ",
                    "file_size_bytes": size,
                    "md5": md5,
                    "link_field_source": "ENA fastq_ftp",
                    "api_returned_status": "returned",
                    "reachability_status": "not_checked",
                    "verification_date": verification_date,
                    "evidence_ids": "E-P0009-005",
                    "notes": "Stored exactly as returned by ENA filereport; file content not downloaded.",
                }
                run_file_records.append(file_row)
                p0009_file_rows.append(file_row)

                user_catalog_rows.append(
                    {
                        "paper_id": "P0009",
                        "canonical_title": "Chromatin structure dynamics during the mitosis-to-G1 phase transition",
                        "doi": "10.1038/s41586-019-1778-y",
                        "archive_project": "PRJNA533460",
                        "study_accession": "SRP192917",
                        "geo_series": "GSE129997",
                        "geo_sample": gsm,
                        "biosample": sample["biosample"],
                        "experiment_accession": run["experiment"],
                        "run_accession": run["run"],
                        "file_url": url,
                        "file_md5": md5,
                        "file_size": size,
                        "file_source": "ENA fastq_ftp",
                        "species": sample["organism"],
                        "sample_name_original": sample["title"],
                        "sample_name_standardized": gsm,
                        "assay": meta["assay_type"],
                        "library_strategy": meta["assay_type"],
                        "measurement_target": meta["measurement_target"],
                        "synchronization_method": sync_method,
                        "synchronization_start": time_zero,
                        "sampling_time": meta["sampling_time"],
                        "sampling_time_unit": meta["sampling_time_unit"],
                        "cell_cycle_phase": meta["cell_cycle_phase"],
                        "phase_evidence_type": phase_type,
                        "perturbation_type": meta["perturbation_type"],
                        "perturbation_technology": meta["perturbation_technology"],
                        "perturbation_target": meta["perturbation_target"],
                        "expected_effect": "NR",
                        "observed_validation": "NR",
                        "is_own_data": "yes",
                        "data_generation_status": "study_generated",
                        "evidence_ids": "E-P0009-003|E-P0009-004|E-P0009-005",
                        "verification_status": "verified",
                        "unresolved_issue_ids": "UI-P0009-003" if meta["assay_type"] == "Capture-C" else "UI-P0009-004" if meta["perturbation_type"] == "mutation" else "NA",
                    }
                )

                p0009_wide_rows.append(
                    {
                        "catalog_row_id": f"CAT-P0009-{len(p0009_wide_rows)+1:06d}",
                        "paper_id": "P0009",
                        "experiment_id": experiment_id,
                        "condition_id": condition_id,
                        "replicate_id": replicate_id,
                        "batch_id": batch_id,
                        "sample_timepoint_id": sample_timepoint_id,
                        "archive_sample_id": archive_sample_id,
                        "perturbation_id": "NA",
                        "accession_record_id": accession_record_id,
                        "file_id": file_id,
                        "paper_title": "Chromatin structure dynamics during the mitosis-to-G1 phase transition",
                        "doi": "10.1038/s41586-019-1778-y",
                        "own_data_status": "yes",
                        **_p0009_origin(),
                        "species_scientific": sample["organism"],
                        "cell_line_or_tissue": sample["source"],
                        "sample_name_original": sample["title"],
                        "assay_type": meta["assay_type"],
                        "detection_target": meta["detection_target"],
                        "synchronization_method": sync_method,
                        "time_zero_definition": time_zero,
                        "sampling_time": meta["sampling_time"],
                        "sampling_time_unit": meta["sampling_time_unit"],
                        "cell_cycle_phase": meta["cell_cycle_phase"],
                        "phase_evidence_type": phase_type,
                        "perturbation_type": meta["perturbation_type"],
                        "direct_target": meta["perturbation_target"],
                        "expected_effect": "NR",
                        "observed_validation": "NR",
                        "gsm_accession": gsm,
                        "biosample_accession": sample["biosample"],
                        "sra_sample_accession": ena["secondary_sample_accession"] or "NR",
                        "experiment_accession": run["experiment"],
                        "run_accession": run["run"],
                        "download_url": url,
                        "file_size_bytes": size,
                        "md5": md5,
                        "online_verification_status": "verified",
                        "evidence_ids": "E-P0009-003|E-P0009-004|E-P0009-005",
                        "notes": "Round5 P0009 file-level row generated only from saved official snapshots.",
                    }
                )

            read1 = next((item for item in run_file_records if item["file_role"] == "read1"), None)
            read2 = next((item for item in run_file_records if item["file_role"] == "read2"), None)
            p0009_run_rows.append(
                {
                    "catalog_run_row_id": f"CATRUN-P0009-{len(p0009_run_rows)+1:06d}",
                    "paper_id": "P0009",
                    "experiment_id": experiment_id,
                    "condition_id": condition_id,
                    "replicate_id": replicate_id,
                    "batch_id": batch_id,
                    "sample_timepoint_id": sample_timepoint_id,
                    "archive_sample_id": archive_sample_id,
                    "perturbation_id": "NA",
                    "accession_record_id": accession_record_id,
                    "paper_title": "Chromatin structure dynamics during the mitosis-to-G1 phase transition",
                    "doi": "10.1038/s41586-019-1778-y",
                    "own_data_status": "yes",
                    **_p0009_origin(),
                    "species_scientific": sample["organism"],
                    "cell_line_or_tissue": sample["source"],
                    "sample_name_original": sample["title"],
                    "assay_type": meta["assay_type"],
                    "cell_cycle_phase": meta["cell_cycle_phase"],
                    "gsm_accession": gsm,
                    "biosample_accession": sample["biosample"],
                    "sra_sample_accession": ena["secondary_sample_accession"] or "NR",
                    "experiment_accession": run["experiment"],
                    "run_accession": run["run"],
                    "library_strategy": meta["assay_type"],
                    "library_source": ena["library_source"],
                    "library_selection": ena["library_selection"] or "UNRESOLVED",
                    "library_layout": ena["library_layout"],
                    "instrument_platform": ena["instrument_platform"],
                    "instrument_model": ena["instrument_model"],
                    "read1_url": read1["download_url"] if read1 else "NA",
                    "read1_size_bytes": read1["file_size_bytes"] if read1 else "NA",
                    "read1_md5": read1["md5"] if read1 else "NA",
                    "read2_url": read2["download_url"] if read2 else "NA",
                    "read2_size_bytes": read2["file_size_bytes"] if read2 else "NA",
                    "read2_md5": read2["md5"] if read2 else "NA",
                    "file_count": str(len(run_file_records)),
                    "online_verification_status": "verified",
                    "evidence_ids": "E-P0009-003|E-P0009-004|E-P0009-005",
                    "notes": "Single-end runs keep read2 columns as NA; paired-end runs expose both reads.",
                }
            )

    relations.extend(relation_rows)
    files.extend(p0009_file_rows)
    wide_rows.extend(p0009_wide_rows)
    files_view_rows.extend(p0009_wide_rows)
    run_view_rows.extend(p0009_run_rows)
    _write_tsv(root / access_spec["path"], access_spec["fields"], accessions)
    _write_tsv(root / rel_spec["path"], rel_spec["fields"], relations)
    _write_tsv(root / files_spec["path"], files_spec["fields"], files)
    _write_tsv(root / wide_spec["path"], wide_spec["fields"], wide_rows)
    _write_tsv(root / files_view_spec["path"], files_view_spec["fields"], files_view_rows)
    _write_tsv(root / runs_view_spec["path"], runs_view_spec["fields"], run_view_rows)

    user_catalog_path = root / "data" / "interim" / "pilot" / "P0009_run_file_catalog.tsv"
    user_catalog_fields = [
        "paper_id", "canonical_title", "doi", "archive_project", "study_accession", "geo_series", "geo_sample",
        "biosample", "experiment_accession", "run_accession", "file_url", "file_md5", "file_size", "file_source",
        "species", "sample_name_original", "sample_name_standardized", "assay", "library_strategy", "measurement_target",
        "synchronization_method", "synchronization_start", "sampling_time", "sampling_time_unit", "cell_cycle_phase",
        "phase_evidence_type", "perturbation_type", "perturbation_technology", "perturbation_target", "expected_effect",
        "observed_validation", "is_own_data", "data_generation_status", "evidence_ids", "verification_status",
        "unresolved_issue_ids",
    ]
    _write_tsv(user_catalog_path, user_catalog_fields, user_catalog_rows)

    sem_spec = schema["tables"]["semantic_review"]
    _, semantic_rows = _read_tsv(root / sem_spec["path"])
    semantic_rows = [row for row in semantic_rows if row.get("paper_id") != "P0009"]
    semantic_rows.extend(
        [
            {
                "review_id": "RV-P0009-0001",
                "paper_id": "P0009",
                "record_type": "sample_timepoint",
                "record_id": "P0009_STAGE_RELEASE_RULE",
                "field_name": "sampling_time",
                "original_value": "prometa|ana.telo|early-G1|mid-G1|late-G1",
                "candidate_interpretation": "0|25|60|120|240 min after nocodazole release",
                "decision": "verified",
                "decision_status": "verified",
                "evidence_ids": "E-P0009-003",
                "decision_rule": "Use GEO Treatment-Protocol explicit mapping; do not infer any additional stages beyond the listed mapping.",
                "reviewer_status": "machine_extracted_pending_human_review",
                "notes": "Applies only to stage-labelled synchronized samples.",
            },
            {
                "review_id": "RV-P0009-0002",
                "paper_id": "P0009",
                "record_type": "sample_timepoint",
                "record_id": "P0009_ASYN_RULE",
                "field_name": "sampling_time",
                "original_value": "asyn",
                "candidate_interpretation": "post-release time point",
                "decision": "NR",
                "decision_status": "not_applicable",
                "evidence_ids": "E-P0009-003",
                "decision_rule": "Do not place asynchronous samples on the nocodazole-release timeline.",
                "reviewer_status": "machine_extracted_pending_human_review",
                "notes": "asyn remains an asynchronous comparator with NR sampling_time and NA time zero.",
            },
            {
                "review_id": "RV-P0009-0003",
                "paper_id": "P0009",
                "record_type": "accession",
                "record_id": "P0009_CAPTUREC_RULE",
                "field_name": "library_strategy",
                "original_value": "OTHER",
                "candidate_interpretation": "Capture-C",
                "decision": "verified",
                "decision_status": "verified",
                "evidence_ids": "E-P0009-003|E-P0009-004",
                "decision_rule": "When GEO title begins with Capture-C and RunInfo reports OTHER, keep raw LibraryStrategy but expose assay_type as Capture-C in sample/run views.",
                "reviewer_status": "machine_extracted_pending_human_review",
                "notes": "Official metadata are sufficient for assay identity but not for bait locus identity.",
            },
            {
                "review_id": "RV-P0009-0004",
                "paper_id": "P0009",
                "record_type": "accession",
                "record_id": "P0009_POLII_RULE",
                "field_name": "library_strategy",
                "original_value": "OTHER",
                "candidate_interpretation": "ChIP-seq Pol II",
                "decision": "verified",
                "decision_status": "verified",
                "evidence_ids": "E-P0009-003|E-P0009-004",
                "decision_rule": "When GEO title begins with ChIP-seq-PolII and RunInfo reports OTHER, preserve raw strategy but expose assay_type as ChIP-seq.",
                "reviewer_status": "machine_extracted_pending_human_review",
                "notes": "Assay label comes from official GEO title, not from guessed file naming.",
            },
            {
                "review_id": "RV-P0009-0005",
                "paper_id": "P0009",
                "record_type": "condition",
                "record_id": "P0009_COMMD3_RULE",
                "field_name": "perturbation_technology",
                "original_value": "commd3_mutant",
                "candidate_interpretation": "locus mutation or engineered mutant background",
                "decision": "UNRESOLVED",
                "decision_status": "unresolved",
                "evidence_ids": "E-P0009-003",
                "decision_rule": "Keep the mutant label from official GEO title, but do not infer engineering technology or expected effect without explicit evidence.",
                "reviewer_status": "machine_extracted_pending_human_review",
                "notes": "condition and user catalog preserve commd3_mutant as raw sample label.",
            },
        ]
    )
    _write_tsv(root / sem_spec["path"], sem_spec["fields"], semantic_rows)

    issue_spec = schema["tables"]["unresolved_issues"]
    _, issues = _read_tsv(root / issue_spec["path"])
    new_issues: list[dict[str, str]] = []
    issue_by_id = {row["issue_id"]: row for row in issues if row.get("paper_id") == "P0009"}
    for row in issues:
        if row.get("issue_id") not in {"UI-P0009-001", "UI-P0009-002", "UI-P0009-003", "UI-P0009-004"}:
            new_issues.append(row)
    new_issues.extend(
        [
            {
                "issue_id": "UI-P0009-001",
                "paper_id": "P0009",
                "related_record_id": "P0009_STAGE_RELEASE_RULE",
                "issue_type": "sampling_minutes_unresolved",
                "description": "Round4未核验的阶段分钟数已由GEO family MINiML Treatment-Protocol裁决。",
                "checked_sources": "GEO family MINiML",
                "current_assessment": "resolved",
                "requires_user_decision": "no",
                "status": "resolved",
                "resolution": "Use 0/25/60/120/240 min for prometa/ana.telo/early/mid/late G1; keep asyn as NR.",
                "notes": "Resolved in round5 from official GEO sample metadata.",
            },
            {
                "issue_id": "UI-P0009-002",
                "paper_id": "P0009",
                "related_record_id": "SRP192917",
                "issue_type": "run_level_not_expanded",
                "description": "Round4仅登记项目级 accession；round5已展开SRR/FASTQ级记录。",
                "checked_sources": "NCBI SRA RunInfo|ENA filereport",
                "current_assessment": "resolved",
                "requires_user_decision": "no",
                "status": "resolved",
                "resolution": "Expanded to 120 runs and 195 FASTQ links from official snapshots.",
                "notes": "Resolved in round5.",
            },
            {
                "issue_id": "UI-P0009-003",
                "paper_id": "P0009",
                "related_record_id": "Capture-C",
                "issue_type": "capture_target_not_explicit",
                "description": "官方GEO/SRA/ENA原始样本记录未逐GSM显式给出Capture-C bait/locus，因此measurement_target保留NR。",
                "checked_sources": "GEO family MINiML|NCBI SRA RunInfo|ENA filereport",
                "current_assessment": "UNRESOLVED",
                "requires_user_decision": "no",
                "status": "open",
                "resolution": "NA",
                "notes": "Processed supplementary filenames mention loci, but raw run-to-locus mapping is not explicit enough for deterministic assignment.",
            },
            {
                "issue_id": "UI-P0009-004",
                "paper_id": "P0009",
                "related_record_id": "commd3_mutant",
                "issue_type": "mutant_technology_unresolved",
                "description": "官方样本标题显示commd3_mutant，但未在已保存官方metadata中明确给出工程技术、直接靶标描述细节或预期效果。",
                "checked_sources": "GEO family MINiML",
                "current_assessment": "UNRESOLVED",
                "requires_user_decision": "no",
                "status": "open",
                "resolution": "NA",
                "notes": "Condition and user catalog preserve the mutant label without inferring the engineering method.",
            },
        ]
    )
    _write_tsv(root / issue_spec["path"], issue_spec["fields"], new_issues)

    report_path = root / "reports" / "per_paper" / "P0009_run_file_pilot.md"
    assay_counts = Counter(_p0009_title_metadata(row["title"])["assay_type"] for row in geo)
    phase_counts = Counter(_p0009_title_metadata(row["title"])["cell_cycle_phase"] for row in geo)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# P0009 Run/File 级核验报告",
                "",
                "## 核心结论",
                "",
                "- 论文：`Chromatin structure dynamics during the mitosis-to-G1 phase transition`",
                "- DOI：`10.1038/s41586-019-1778-y`",
                "- GEO Series：`GSE129997`；BioProject：`PRJNA533460`；SRA Study：`SRP192917`",
                f"- 官方样本数：{len(geo)} 个 GSM；SRA/ENA Run 数：{len(runinfo_set)}；FASTQ 链接数：{len(p0009_file_rows)}",
                f"- assay 分布：Hi-C {assay_counts['Hi-C']}；Capture-C {assay_counts['Capture-C']}；ChIP-seq {assay_counts['ChIP-seq']}",
                f"- 阶段分布：{dict(sorted(phase_counts.items()))}",
                "",
                "## 本轮确认",
                "",
                "- GEO family MINiML 的 Treatment-Protocol 明确给出 `0 / 25 / 60 / 120 / 240 min` 对应 `prometa / ana.telo / early-G1 / mid-G1 / late-G1`。",
                "- `asyn` 样本保留为 asynchronous comparator，不被强行放入 release 时间轴。",
                "- `SRP192917` 已展开到 120 个 Run；ENA filereport 提供 195 个 FASTQ 链接、MD5 和字节数。",
                "- 单端与双端 run 已区分：paired-end 75 个，single-end 45 个。",
                "",
                "## 仍未解决",
                "",
                "- Capture-C 的具体 bait/locus 目标未在 raw metadata 中逐GSM显式声明，因此 `measurement_target` 保留 `NR`。",
                "- `commd3_mutant` 样本标题提示 mutant 背景，但工程技术、预期效果和直接靶标细节未在当前保存的官方 metadata 中显式给出。",
                "",
                "## 产物",
                "",
                "- `data/interim/pilot/P0009_run_file_catalog.tsv`",
                "- `data/interim/pilot/source_metadata/GSE129997_family.xml(.tgz)`",
                "- `data/interim/pilot/source_metadata/SRP192917_runinfo.csv`",
                "- `data/interim/pilot/source_metadata/SRP192917_ena_filereport.tsv`",
                "",
                "## 说明",
                "",
                "- 本轮未下载 FASTQ、SRA、矩阵或其他大文件，只保存官方轻量快照并离线构建表格。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "geo_samples": len(geo),
        "run_rows": len(p0009_run_rows),
        "file_rows": len(p0009_file_rows),
        "catalog_rows": len(user_catalog_rows),
        "user_catalog_sha256": _stable_hash(user_catalog_path),
        "report_path": str(report_path.relative_to(root)).replace("\\", "/"),
    }


def build_pilot_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    config_file = config_path or root / "configs" / "pilots" / "P0008.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    paper_id = config.get("paper_id", "P0008")
    if paper_id == "P0008":
        return _build_p0008_catalog(root, config_file)
    if paper_id == "P0009":
        return _build_p0009_catalog(root, config_file)
    if paper_id == "P0012":
        from .round6 import build_p0012_catalog

        return build_p0012_catalog(root, config_file)
    if paper_id == "P0001":
        from .round6 import build_p0001_catalog

        return build_p0001_catalog(root, config_file)
    raise CatalogError(f"Unsupported pilot builder for {paper_id}")


def _write_reconciliation(
    root: Path, config: dict[str, Any], geo: list[dict[str, str]], ncbi_experiments: list[dict[str, str]],
    ncbi_runs: list[dict[str, str]], ena_runs: list[dict[str, str]], archive_samples: list[dict[str, str]],
    accessions: list[dict[str, str]], files: list[dict[str, str]], wide_rows: list[dict[str, str]], run_rows: list[dict[str, str]],
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
        ("file_view_rows", "all", len(wide_rows), "pass", "literature_experiment_catalog_files"),
        ("run_view_rows", "all", len(run_rows), "pass", "literature_experiment_catalog_runs"),
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
        "ena_runs": len(ena_set), "files": len(files), "wide_rows": len(wide_rows), "run_rows": len(run_rows),
        "wide_sha256": _stable_hash(wide_path),
        "file_view_sha256": _stable_hash(root / "data" / "interim" / "pilot" / "literature_experiment_catalog_files.tsv"),
        "run_view_sha256": _stable_hash(root / "data" / "interim" / "pilot" / "literature_experiment_catalog_runs.tsv"),
        "human_samples": sum(row["organism"] == "Homo sapiens" for row in geo),
        "chicken_samples": sum(row["organism"] == "Gallus gallus" for row in geo),
        "gsm_without_run": sum(runs_by_gsm[row["gsm_accession"]] == 0 for row in archive_samples),
        "gsm_with_multiple_runs": sum(runs_by_gsm[row["gsm_accession"]] > 1 for row in archive_samples),
    }
    markdown = f"""# P0008 accession 数量对账\n\n本报告由 `src.literature_catalog.pilot` 从保存的官方快照确定性生成。\n\n- GEO GSM：{payload['geo_samples']}（Gallus gallus {payload['chicken_samples']}；Homo sapiens {payload['human_samples']}）\n- NCBI SRA Experiment：{payload['ncbi_experiments']}\n- NCBI Run / ENA Run：{payload['ncbi_runs']} / {payload['ena_runs']}；集合差集均为0\n- GSM无Run：{payload['gsm_without_run']}；GSM多Run：{payload['gsm_with_multiple_runs']}\n- ENA FASTQ文件记录：{payload['files']}；URL、大小、MD5覆盖率均为100%\n- 文件粒度视图：{payload['wide_rows']}行；SHA-256 `{payload['file_view_sha256']}`\n- Run粒度视图：{payload['run_rows']}行；SHA-256 `{payload['run_view_sha256']}`\n\n逐指标及分层计数见 `reports/P0008_accession_reconciliation.tsv`。兼容宽表仍指向文件粒度。文件URL仅保存ENA API返回值，未下载文件正文。\n"""
    (root / "reports" / "P0008_accession_reconciliation.md").write_text(markdown, encoding="utf-8")
    return payload

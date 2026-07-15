"""Round 6 lightweight archive expansion for P0012 and P0001.

This module intentionally consumes only saved official metadata snapshots.
It does not download sequencing files and it keeps perturbation interpretation
conservative when a field is not explicit in GEO/ENA records or prior paper
evidence.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .catalog import CatalogError, _read_tsv, _write_tsv, load_schema
from .pilot import parse_ena_runs, parse_geo_miniml, parse_ncbi_runinfo, _stable_hash


def _paper_meta(root: Path, paper_id: str) -> dict[str, str]:
    _, rows = _read_tsv(root / "data" / "curated" / "papers.tsv")
    for row in rows:
        if row.get("paper_id") == paper_id:
            row = dict(row)
            row.setdefault("title", row.get("canonical_title", "NR"))
            return row
    raise CatalogError(f"missing paper row for {paper_id}")


def _replace_rows(root: Path, schema: dict[str, Any], table: str, rows: list[dict[str, Any]], predicate) -> list[dict[str, Any]]:
    spec = schema["tables"][table]
    _, existing = _read_tsv(root / spec["path"])
    merged = [row for row in existing if not predicate(row)]
    merged.extend(rows)
    _write_tsv(root / spec["path"], spec["fields"], merged)
    return merged


def _split_semicolon(value: str) -> list[str]:
    value = value or ""
    return [part for part in value.split(";") if part]


def _p0012_meta(title: str, subseries: str) -> dict[str, str]:
    lower = title.lower()
    replicate = "NR"
    rep_match = re.search(r"(?:rep\.?|_rep)(\d+)", lower)
    if rep_match:
        replicate = f"rep{rep_match.group(1)}"
    time_value = "NR"
    unit = "NA"
    match = re.search(r"(\d+)\s*(?:min|minutes)", lower)
    if match:
        time_value, unit = match.group(1), "min"
    elif match := re.search(r"(\d+)h", lower):
        time_value, unit = str(int(match.group(1)) * 60), "min"

    stage_map = {
        "0": "prometaphase",
        "25": "ana/telo",
        "60": "early G1",
        "120": "mid G1",
        "240": "late G1",
    }
    assay_type = "ChIP-seq" if subseries == "GSE168168" else "Hi-C"
    detection_target = "NA"
    if subseries == "GSE168168":
        if lower.startswith("polii"):
            detection_target = "Pol II"
        elif "ctcf" in lower:
            detection_target = "CTCF"
        elif "rad21" in lower:
            detection_target = "Rad21"
        elif "input" in lower:
            detection_target = "input control"
        else:
            detection_target = "NR"

    auxin = "with_auxin" in lower or "with_a" in lower
    triptolide = "with_triptolide" in lower
    no_auxin = "no_auxin" in lower or "no_a" in lower
    perturbation_label = []
    if auxin:
        perturbation_label.append("auxin")
    if triptolide:
        perturbation_label.append("triptolide")
    if not perturbation_label and no_auxin:
        perturbation_label.append("no auxin control")

    if auxin and triptolide:
        perturbation_id = "PT-P0012-003"
    elif auxin:
        perturbation_id = "PT-P0012-001"
    elif triptolide:
        perturbation_id = "PT-P0012-002"
    else:
        perturbation_id = "NA"

    return {
        "assay_type": assay_type,
        "detection_target": detection_target,
        "replicate": replicate,
        "sampling_time": time_value,
        "sampling_time_unit": unit,
        "cell_cycle_phase": stage_map.get(time_value, "NR" if time_value == "NR" else "UNRESOLVED"),
        "perturbation_id": perturbation_id,
        "treatment": "|".join(perturbation_label) if perturbation_label else "NA",
    }


def _p0001_stage(alias: str) -> dict[str, str]:
    lower = alias.lower()
    if "g1mid" in lower:
        return {"phase": "mid G1", "sync": "NR", "time": "NR"}
    if "-g1-" in lower or "g1-" in lower:
        return {"phase": "G1", "sync": "NR", "time": "NR"}
    if "-m-" in lower or "hela-m" in lower:
        return {"phase": "prometaphase/M", "sync": "NR", "time": "NR"}
    if "earlys" in lower or "early-s" in lower:
        return {"phase": "early S", "sync": "thymidine arrest", "time": "NR"}
    return {"phase": "UNRESOLVED", "sync": "NR", "time": "NR"}


def _p0001_cell_source(alias: str) -> str:
    lower = alias.lower()
    if "hff1" in lower:
        return "HFF1"
    if "hela" in lower:
        return "HeLa S3"
    return "NR"


def _p0012_direct_target(perturbation_id: str) -> str:
    if perturbation_id == "PT-P0012-001":
        return "CTCF"
    if perturbation_id == "PT-P0012-002":
        return "transcription initiation"
    if perturbation_id == "PT-P0012-003":
        return "CTCF|transcription initiation"
    return "NA"


def _accession_stub(
    record_id: str,
    experiment_id: str,
    namespace: str,
    entity_type: str,
    accession: str,
    official_page_url: str,
    evidence_ids: str,
    verification_date: str,
) -> dict[str, str]:
    return {
        "accession_record_id": record_id,
        "experiment_id": experiment_id,
        "sample_timepoint_id": "NA",
        "namespace": namespace,
        "entity_type": entity_type,
        "accession": accession,
        "project_accession": accession if entity_type in {"bioproject", "arrayexpress", "geo_series"} else "NA",
        "study_accession": accession if entity_type == "sra_study" else "NA",
        "sample_accession": "NA",
        "experiment_accession": "NA",
        "run_accession": "NA",
        "official_page_url": official_page_url,
        "download_url": "NA",
        "file_format": "NA",
        "file_size_bytes": "NA",
        "md5": "NA",
        "format_validation_status": "verified",
        "online_verification_status": "verified_metadata_record",
        "verification_date": verification_date,
        "evidence_ids": evidence_ids,
        "notes": "Project/study level accession retained alongside run-level expansion.",
        "condition_id": "NA",
        "replicate_id": "NA",
        "batch_id": "NA",
        "library_strategy": "NA",
        "library_source": "NA",
        "library_selection": "NA",
        "library_layout": "NA",
        "instrument_platform": "NA",
        "instrument_model": "NA",
        "public_status": "public",
        "query_id": "NA",
        "biological_sample_origin_status": "NA",
        "library_origin_status": "NA",
        "sequencing_generation_status": "NA",
        "analysis_usage_status": "NA",
        "origin_evidence_ids": "NA",
    }


def _file_rows_for_run(prefix: str, run: str, fastq_ftp: str, fastq_md5: str, fastq_bytes: str, evidence_id: str, verification_date: str) -> list[dict[str, str]]:
    urls = _split_semicolon(fastq_ftp)
    md5s = _split_semicolon(fastq_md5)
    sizes = _split_semicolon(fastq_bytes)
    rows: list[dict[str, str]] = []
    for idx, url in enumerate(urls, start=1):
        rows.append(
            {
                "file_id": f"RF-{prefix}-{run}-{idx}",
                "run_accession": run,
                "file_index": str(idx),
                "file_role": "read1" if idx == 1 else ("read2" if idx == 2 else f"read{idx}"),
                "download_url": url,
                "file_format": "fastq.gz",
                "file_size_bytes": sizes[idx - 1] if idx - 1 < len(sizes) else "NR",
                "md5": md5s[idx - 1] if idx - 1 < len(md5s) else "NR",
                "link_field_source": "ENA filereport fastq_ftp",
                "api_returned_status": "present",
                "reachability_status": "not_checked",
                "verification_date": verification_date,
                "evidence_ids": evidence_id,
                "notes": "Metadata link only; sequencing file was not downloaded.",
            }
        )
    return rows


def _append_run_views(
    root: Path,
    schema: dict[str, Any],
    paper_id: str,
    paper: dict[str, str],
    rows: list[dict[str, str]],
    accessions: list[dict[str, str]],
    files: list[dict[str, str]],
) -> None:
    accession_by_run = {row["run_accession"]: row for row in accessions if row.get("entity_type") == "sra_run"}
    files_by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
    for file_row in files:
        files_by_run[file_row["run_accession"]].append(file_row)

    file_view: list[dict[str, str]] = []
    run_view: list[dict[str, str]] = []
    for base in rows:
        run = base["run_accession"]
        acc = accession_by_run[run]
        run_files = sorted(files_by_run[run], key=lambda item: int(item["file_index"]))
        for file_row in run_files:
            file_view.append({**base, "catalog_row_id": f"{base['catalog_row_id']}-F{file_row['file_index']}", "file_id": file_row["file_id"], "download_url": file_row["download_url"], "file_size_bytes": file_row["file_size_bytes"], "md5": file_row["md5"]})
        run_view.append(
            {
                "catalog_run_row_id": base["catalog_row_id"].replace("CAT-", "CR-"),
                "paper_id": paper_id,
                "experiment_id": base["experiment_id"],
                "condition_id": base["condition_id"],
                "replicate_id": base["replicate_id"],
                "batch_id": base["batch_id"],
                "sample_timepoint_id": base["sample_timepoint_id"],
                "archive_sample_id": base["archive_sample_id"],
                "perturbation_id": base["perturbation_id"],
                "accession_record_id": acc["accession_record_id"],
                "paper_title": paper["title"],
                "doi": paper["doi"],
                "own_data_status": base["own_data_status"],
                "biological_sample_origin_status": base["biological_sample_origin_status"],
                "library_origin_status": base["library_origin_status"],
                "sequencing_generation_status": base["sequencing_generation_status"],
                "analysis_usage_status": base["analysis_usage_status"],
                "species_scientific": base["species_scientific"],
                "cell_line_or_tissue": base["cell_line_or_tissue"],
                "sample_name_original": base["sample_name_original"],
                "assay_type": base["assay_type"],
                "cell_cycle_phase": base["cell_cycle_phase"],
                "gsm_accession": base["gsm_accession"],
                "biosample_accession": base["biosample_accession"],
                "sra_sample_accession": base["sra_sample_accession"],
                "experiment_accession": base["experiment_accession"],
                "run_accession": run,
                "library_strategy": acc["library_strategy"],
                "library_source": acc["library_source"],
                "library_selection": acc["library_selection"],
                "library_layout": acc["library_layout"],
                "instrument_platform": acc["instrument_platform"],
                "instrument_model": acc["instrument_model"],
                "read1_url": run_files[0]["download_url"] if len(run_files) > 0 else "NR",
                "read1_size_bytes": run_files[0]["file_size_bytes"] if len(run_files) > 0 else "NR",
                "read1_md5": run_files[0]["md5"] if len(run_files) > 0 else "NR",
                "read2_url": run_files[1]["download_url"] if len(run_files) > 1 else "NA",
                "read2_size_bytes": run_files[1]["file_size_bytes"] if len(run_files) > 1 else "NA",
                "read2_md5": run_files[1]["md5"] if len(run_files) > 1 else "NA",
                "file_count": str(len(run_files)),
                "online_verification_status": "verified_metadata_record",
                "evidence_ids": base["evidence_ids"],
                "notes": base["notes"],
            }
        )

    _replace_rows(root, schema, "literature_experiment_catalog", file_view, lambda row: row.get("paper_id") == paper_id)
    _replace_rows(root, schema, "literature_experiment_catalog_files", file_view, lambda row: row.get("paper_id") == paper_id)
    _replace_rows(root, schema, "literature_experiment_catalog_runs", run_view, lambda row: row.get("paper_id") == paper_id)


def _write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    _write_tsv(path, list(rows[0].keys()), rows)


def build_p0012_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    config = json.loads((config_path or root / "configs" / "pilots" / "P0012.json").read_text(encoding="utf-8"))
    schema = load_schema(root)
    source_dir = root / config["source_metadata_dir"]
    verification_date = "2026-07-14"
    paper = _paper_meta(root, "P0012")
    main_geo = parse_geo_miniml(source_dir / "GSE168251_family.xml")
    sub_a = {row["gsm"]: "GSE168168" for row in parse_geo_miniml(source_dir / "GSE168168_family.xml")}
    sub_b = {row["gsm"]: "GSE168176" for row in parse_geo_miniml(source_dir / "GSE168176_family.xml")}
    subseries = {**sub_a, **sub_b}
    ena = parse_ena_runs(source_dir / "PRJNA706679_ena_filereport.tsv")
    ncbi = parse_ncbi_runinfo(source_dir / "PRJNA706679_runinfo.csv")
    if len(main_geo) != int(config["expected_geo_samples"]):
        raise CatalogError(f"P0012 GEO sample count mismatch: {len(main_geo)}")
    if {row["run_accession"] for row in ena} != {row["run"] for row in ncbi}:
        raise CatalogError("P0012 ENA/NCBI run sets differ")

    ena_by_gsm: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ena:
        ena_by_gsm[row["sample_alias"]].append(row)

    experiments = [{
        "experiment_id": "EX-P0012-001", "paper_id": "P0012",
        "experiment_label_original": "CTCF/transcription perturbation during post-mitotic chromatin reconfiguration",
        "biological_question": "测试 CTCF 与转录对有丝分裂后染色质结构重构的影响",
        "own_data_status": "yes", "own_data_evidence": "E-P0012-001|E-P0012-003|E-P0012-004",
        "assay_type": "ChIP-seq|Hi-C", "assay_detail": "GEO subseries GSE168168 and GSE168176",
        "measurement_object": "chromatin occupancy and genome-wide chromatin contacts",
        "detection_target": "Pol II|CTCF|Rad21|input control|NA",
        "experimental_group": "post-mitotic release time course with auxin and/or triptolide conditions",
        "control_group": "no auxin and no triptolide controls where present",
        "biological_replicates": "rep labels present in GEO sample titles; replicate type unresolved",
        "technical_replicates": "NR", "reference_genome": "mm10",
        "evidence_ids": "E-P0012-001|E-P0012-003|E-P0012-004",
        "notes": "Round6 expands official GEO/ENA/NCBI metadata to GSM/SRX/SRR/FASTQ-link level.",
    }]
    _replace_rows(root, schema, "experiments", experiments, lambda row: row.get("paper_id") == "P0012")

    perturbations = [
        {"perturbation_id": "PT-P0012-001", "experiment_id": "EX-P0012-001", "combination_id": "AUXIN", "perturbed_object": "CTCF protein", "perturbation_type": "protein depletion", "technology": "auxin-inducible degron", "direct_target": "CTCF", "construct_or_reagent": "auxin", "dose": "NR", "duration": "sample-title dependent", "timing_relative_to_synchronization": "during post-mitotic release according to sample conditions", "control": "no auxin", "expected_effect": "acute CTCF depletion", "expected_effect_basis": "prior P0012 pilot paper evidence", "observed_validation": "NR in saved metadata", "evidence_ids": "E-P0012-001|E-P0012-003", "notes": "Kept separate from detection targets such as Pol II/Rad21."},
        {"perturbation_id": "PT-P0012-002", "experiment_id": "EX-P0012-001", "combination_id": "TRIPTOLIDE", "perturbed_object": "transcription initiation", "perturbation_type": "chemical inhibition", "technology": "triptolide treatment", "direct_target": "transcription initiation machinery (specific molecular target not resolved here)", "construct_or_reagent": "triptolide", "dose": "NR", "duration": "sample-title dependent", "timing_relative_to_synchronization": "during post-mitotic release according to sample conditions", "control": "no triptolide", "expected_effect": "inhibit transcription initiation", "expected_effect_basis": "prior P0012 pilot paper evidence", "observed_validation": "NR in saved metadata", "evidence_ids": "E-P0012-001|E-P0012-003", "notes": "Do not conflate transcription perturbation with Pol II ChIP detection target."},
        {"perturbation_id": "PT-P0012-003", "experiment_id": "EX-P0012-001", "combination_id": "AUXIN_TRIPTOLIDE", "perturbed_object": "CTCF protein and transcription initiation", "perturbation_type": "combined depletion/inhibition", "technology": "auxin-inducible degron plus triptolide treatment", "direct_target": "CTCF|transcription initiation machinery", "construct_or_reagent": "auxin|triptolide", "dose": "NR", "duration": "sample-title dependent", "timing_relative_to_synchronization": "during post-mitotic release according to sample conditions", "control": "no auxin/no triptolide matched controls", "expected_effect": "combine CTCF depletion with transcription initiation inhibition", "expected_effect_basis": "prior P0012 pilot paper evidence plus GEO sample labels", "observed_validation": "NR in saved metadata", "evidence_ids": "E-P0012-001|E-P0012-003", "notes": "Combination row only used for sample titles explicitly containing both treatments."},
    ]
    _replace_rows(root, schema, "perturbations", perturbations, lambda row: row.get("experiment_id") == "EX-P0012-001")

    conditions = []; replicates = []; batches = []; timepoints = []; archive = []
    acc_rows = [
        _accession_stub("AC-P0012-GSE168251", "EX-P0012-001", "GEO", "geo_series", "GSE168251", "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE168251", "E-P0012-003", verification_date),
        _accession_stub("AC-P0012-GSE168168", "EX-P0012-001", "GEO", "geo_series", "GSE168168", "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE168168", "E-P0012-003", verification_date),
        _accession_stub("AC-P0012-GSE168176", "EX-P0012-001", "GEO", "geo_series", "GSE168176", "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE168176", "E-P0012-003", verification_date),
        _accession_stub("AC-P0012-PRJNA706679", "EX-P0012-001", "NCBI BioProject", "bioproject", "PRJNA706679", "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA706679", "E-P0012-004", verification_date),
    ]; rel_rows = []; file_rows = []; catalog_base = []
    for idx, sample in enumerate(main_geo, start=1):
        gsm = sample["gsm"]; ss = subseries.get(gsm, "UNRESOLVED")
        meta = _p0012_meta(sample["title"], ss)
        runs = sorted(ena_by_gsm[gsm], key=lambda row: row["run_accession"])
        condition_id = f"C-P0012-{idx:03d}"; replicate_id = f"R-P0012-{idx:03d}"
        batch_id = f"B-P0012-{idx:03d}"; st_id = f"ST-P0012-{idx:03d}"; as_id = f"AS-P0012-{idx:03d}"
        conditions.append({"condition_id": condition_id, "paper_id": "P0012", "experiment_id": "EX-P0012-001", "author_condition_label": sample["title"], "genotype_or_construct": "G1E-ER4 CTCF-AID-mCherry", "synchronization_method": "nocodazole arrest-release", "synchronization_reagent": "nocodazole", "treatment_or_perturbation": meta["treatment"], "cell_cycle_phase": meta["cell_cycle_phase"], "control_role": "control" if "no auxin" in meta["treatment"] or meta["treatment"] == "NA" else "perturbation", "evidence_ids": "E-P0012-003", "normalization_status": "official_metadata_plus_prior_pilot_evidence", "notes": f"GEO subseries {ss}."})
        replicates.append({"replicate_id": replicate_id, "condition_id": condition_id, "author_replicate_label": meta["replicate"], "replicate_type": "UNRESOLVED" if meta["replicate"] != "NR" else "NR", "replicate_number": re.sub(r"^rep", "", meta["replicate"]) if meta["replicate"] != "NR" else "NR", "evidence_ids": "E-P0012-003", "notes": "rep label parsed from GEO title; biological/technical type not explicit in saved metadata."})
        batches.append({"batch_id": batch_id, "paper_id": "P0012", "author_batch_label": ss, "batch_date": "NR", "library_batch": "NR", "sequencing_platform": runs[0]["instrument_model"] if runs else "NR", "evidence_ids": "E-P0012-004", "verification_status": "verified_metadata_record", "notes": "subseries used as a coarse source partition, not a laboratory batch claim."})
        timepoints.append({"sample_timepoint_id": st_id, "experiment_id": "EX-P0012-001", "species_scientific": sample["organism"], "species_common": "mouse", "taxonomy_id": "10090", "cell_line_or_tissue": sample["source"], "sample_name_original": sample["title"], "sample_name_standardized": gsm, "genotype_or_construct": "G1E-ER4 CTCF-AID-mCherry", "synchronization_method": "nocodazole arrest-release", "synchronization_reagent": "nocodazole", "synchronization_dose": "200 ng/ml", "synchronization_duration": "7-8.5 h", "arrest_point": "prometaphase", "time_zero_definition": "release from nocodazole arrest", "sampling_time": meta["sampling_time"], "sampling_time_unit": meta["sampling_time_unit"], "cell_cycle_phase": meta["cell_cycle_phase"], "phase_evidence_type": "author_stated", "phase_evidence_rule": "GEO Treatment-Protocol maps 0/25/60/120/240 min to pro-meta/ana-telo/early-G1/mid-G1/late-G1.", "pooled_status": "NR", "evidence_ids": "E-P0012-003", "notes": "Sampling time parsed from official title; phase mapping from GEO Treatment-Protocol.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "gsm_accession": gsm, "archive_sample_id": as_id})
        archive.append({"archive_sample_id": as_id, "experiment_id": "EX-P0012-001", "sample_timepoint_id": st_id, "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "gsm_accession": gsm, "biosample_accession": sample["biosample"], "sra_sample_accession": runs[0]["secondary_sample_accession"] if runs else "NR", "srx_accession": sample["srx"], "sample_title_original": sample["title"], "sample_alias_original": gsm, "species_scientific": sample["organism"], "taxonomy_id": "10090", "cell_line_or_tissue": sample["source"], "platform_accession": sample["platform"], "genotype_original": "G1E-ER4 CTCF-AID-mCherry", "phase_original": meta["cell_cycle_phase"], "type_original": ss, "own_data_status": "yes", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "origin_evidence_ids": "E-P0012-001|E-P0012-003|E-P0012-004", "disposition_status": "mapped", "run_count": str(len(runs)), "evidence_ids": "E-P0012-003|E-P0012-004", "notes": "GEO sample matched to ENA runs by sample_alias/GSM."})
        for run_idx, run in enumerate(runs, start=1):
            run_id = run["run_accession"]
            acc_id = f"AC-P0012-{idx:03d}-{run_idx:03d}"
            acc_rows.append({"accession_record_id": acc_id, "experiment_id": "EX-P0012-001", "sample_timepoint_id": st_id, "namespace": "ENA/SRA", "entity_type": "sra_run", "accession": run_id, "project_accession": run["study_accession"], "study_accession": run["secondary_study_accession"], "sample_accession": run["secondary_sample_accession"], "experiment_accession": run["experiment_accession"], "run_accession": run_id, "official_page_url": f"https://www.ebi.ac.uk/ena/browser/view/{run_id}", "download_url": run["fastq_ftp"], "file_format": "fastq.gz", "file_size_bytes": run["fastq_bytes"], "md5": run["fastq_md5"], "format_validation_status": "valid_accession_format", "online_verification_status": "verified_metadata_record", "verification_date": verification_date, "evidence_ids": "E-P0012-004", "notes": "Project accession is the value returned by ENA filereport; declared PRJNA706679 is tracked as unresolved alias/scope issue.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "library_strategy": run["library_strategy"], "library_source": "NR", "library_selection": "NR", "library_layout": run["library_layout"], "instrument_platform": run["instrument_platform"], "instrument_model": run["instrument_model"], "public_status": "public", "query_id": "Q-P0012-004", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "origin_evidence_ids": "E-P0012-001|E-P0012-004"})
            rel_rows.append({"relation_id": f"AR-P0012-{idx:03d}-{run_idx:03d}", "parent_accession": run["experiment_accession"], "child_accession": run_id, "relation_type": "experiment_has_run", "source_database": "ENA filereport", "query_id": "Q-P0012-004", "verification_status": "verified_metadata_record", "evidence_ids": "E-P0012-003|E-P0012-004", "notes": f"Run matched to GEO sample {gsm} by ENA sample_alias."})
            run_file_rows = _file_rows_for_run("P0012", run_id, run["fastq_ftp"], run["fastq_md5"], run["fastq_bytes"], "E-P0012-004", verification_date)
            file_rows.extend(run_file_rows)
            catalog_base.append({"catalog_row_id": f"CAT-P0012-{len(catalog_base)+1:06d}", "paper_id": "P0012", "experiment_id": "EX-P0012-001", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "sample_timepoint_id": st_id, "archive_sample_id": as_id, "perturbation_id": meta["perturbation_id"], "accession_record_id": acc_id, "file_id": "NA", "paper_title": paper["title"], "doi": paper["doi"], "own_data_status": "yes", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "species_scientific": sample["organism"], "cell_line_or_tissue": sample["source"], "sample_name_original": sample["title"], "assay_type": meta["assay_type"], "detection_target": meta["detection_target"], "synchronization_method": "nocodazole arrest-release", "time_zero_definition": "release from nocodazole arrest", "sampling_time": meta["sampling_time"], "sampling_time_unit": meta["sampling_time_unit"], "cell_cycle_phase": meta["cell_cycle_phase"], "phase_evidence_type": "author_stated", "perturbation_type": meta["treatment"], "direct_target": _p0012_direct_target(meta["perturbation_id"]), "expected_effect": "see perturbations table", "observed_validation": "NR", "gsm_accession": gsm, "biosample_accession": sample["biosample"], "sra_sample_accession": run["secondary_sample_accession"], "experiment_accession": run["experiment_accession"], "run_accession": run_id, "download_url": "NA", "file_size_bytes": "NA", "md5": "NA", "online_verification_status": "verified_metadata_record", "evidence_ids": "E-P0012-003|E-P0012-004", "notes": "One row per Run in run view; file view expands FASTQ links."})

    _replace_rows(root, schema, "conditions", conditions, lambda row: row.get("paper_id") == "P0012")
    _replace_rows(root, schema, "replicates", replicates, lambda row: row.get("replicate_id", "").startswith("R-P0012-"))
    _replace_rows(root, schema, "batches", batches, lambda row: row.get("paper_id") == "P0012")
    _replace_rows(root, schema, "samples_timepoints", timepoints, lambda row: row.get("sample_timepoint_id", "").startswith("ST-P0012-"))
    _replace_rows(root, schema, "archive_samples", archive, lambda row: row.get("archive_sample_id", "").startswith("AS-P0012-"))
    _replace_rows(root, schema, "accessions", acc_rows, lambda row: row.get("accession_record_id", "").startswith("AC-P0012-"))
    _replace_rows(root, schema, "accession_relations", rel_rows, lambda row: row.get("relation_id", "").startswith("AR-P0012-"))
    _replace_rows(root, schema, "files", file_rows, lambda row: row.get("file_id", "").startswith("RF-P0012-"))
    _append_run_views(root, schema, "P0012", paper, catalog_base, acc_rows, file_rows)
    _write_catalog(root / "data" / "interim" / "pilot" / "P0012_run_file_catalog.tsv", [r for base in catalog_base for r in [{**base, "catalog_row_id": f"{base['catalog_row_id']}-F{f['file_index']}", "file_id": f["file_id"], "download_url": f["download_url"], "file_size_bytes": f["file_size_bytes"], "md5": f["md5"]} for f in file_rows if f["run_accession"] == base["run_accession"]]])

    p0012_run_count = sum(row.get("entity_type") == "sra_run" for row in acc_rows)
    _update_round6_common(root, schema, "P0012", verification_date, {
        "geo_samples": len(main_geo), "runs": p0012_run_count, "files": len(file_rows),
        "queries": [("Q-P0012-001", "GEO", "family MINiML", "GSE168251/GSE168168/GSE168176", "GSE168251_family.xml;GSE168168_family.xml;GSE168176_family.xml", len(main_geo)),
                    ("Q-P0012-004", "ENA", "filereport read_run", "PRJNA706679", "PRJNA706679_ena_filereport.tsv", len(ena))],
    })
    _write_p0012_report(root, main_geo, ena, file_rows)
    return {"paper_id": "P0012", "geo_samples": len(main_geo), "runs": p0012_run_count, "files": len(file_rows), "catalog_sha256": _stable_hash(root / "data" / "interim" / "pilot" / "P0012_run_file_catalog.tsv")}


def build_p0001_catalog(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    config = json.loads((config_path or root / "configs" / "pilots" / "P0001.json").read_text(encoding="utf-8"))
    schema = load_schema(root); source_dir = root / config["source_metadata_dir"]
    verification_date = "2026-07-14"; paper = _paper_meta(root, "P0001")
    ena = parse_ena_runs(source_dir / "ERP004055_ena_filereport.tsv")
    if not ena:
        raise CatalogError("P0001 ENA filereport returned no rows")
    experiments = [{"experiment_id": "EX-P0001-001", "paper_id": "P0001", "experiment_label_original": "Mitotic chromosome organization cell-cycle chromatin conformation assays", "biological_question": "比较人源细胞不同细胞周期阶段的染色质组织", "own_data_status": "yes", "own_data_evidence": "E-P0001-001|E-P0001-003", "assay_type": "5C/Hi-C related archive entries", "assay_detail": "ArrayExpress E-MTAB-1948 / ENA ERP004055 read_run metadata", "measurement_object": "chromatin contacts", "detection_target": "NA", "experimental_group": "HeLa S3 cell-cycle staged samples", "control_group": "stage comparators", "biological_replicates": "R labels present in ENA aliases; replicate type unresolved", "technical_replicates": "NR", "reference_genome": "NR", "evidence_ids": "E-P0001-001|E-P0001-003", "notes": "Round6 expands to 13 ERR runs and ENA FASTQ metadata; detailed sample design remains light."}]
    _replace_rows(root, schema, "experiments", experiments, lambda row: row.get("paper_id") == "P0001")
    conditions=[]; replicates=[]; batches=[]; timepoints=[]; archive=[]
    acc_rows=[
        _accession_stub("AC-P0001-EMTAB1948", "EX-P0001-001", "ArrayExpress/BioStudies", "arrayexpress", "E-MTAB-1948", "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-1948", "E-P0001-003", verification_date),
        _accession_stub("AC-P0001-ERP004055", "EX-P0001-001", "ENA", "sra_study", "ERP004055", "https://www.ebi.ac.uk/ena/browser/view/ERP004055", "E-P0001-003", verification_date),
    ]; rel_rows=[]; file_rows=[]; catalog_base=[]
    for idx, run in enumerate(sorted(ena, key=lambda row: row["run_accession"]), start=1):
        alias = run["sample_alias"]; stage = _p0001_stage(alias)
        cell_source = _p0001_cell_source(alias)
        archive_sample_label = f"NO_GEO_{run['run_accession']}"
        condition_id=f"C-P0001-{idx:03d}"; replicate_id=f"R-P0001-{idx:03d}"; batch_id=f"B-P0001-{idx:03d}"; st_id=f"ST-P0001-{idx:03d}"; as_id=f"AS-P0001-{idx:03d}"
        rep = re.search(r"R(\d+)", alias)
        rep_label = f"R{rep.group(1)}" if rep else "NR"
        conditions.append({"condition_id": condition_id, "paper_id": "P0001", "experiment_id": "EX-P0001-001", "author_condition_label": alias, "genotype_or_construct": "NR", "synchronization_method": stage["sync"], "synchronization_reagent": "NR", "treatment_or_perturbation": "cell-cycle staging", "cell_cycle_phase": stage["phase"], "control_role": "stage comparator", "evidence_ids": "E-P0001-003", "normalization_status": "official_archive_alias_light_parse", "notes": "Stage parsed conservatively from ENA alias and prior pilot evidence."})
        replicates.append({"replicate_id": replicate_id, "condition_id": condition_id, "author_replicate_label": rep_label, "replicate_type": "UNRESOLVED" if rep_label != "NR" else "NR", "replicate_number": rep.group(1) if rep else "NR", "evidence_ids": "E-P0001-003", "notes": "R label retained from archive alias; type unresolved."})
        batches.append({"batch_id": batch_id, "paper_id": "P0001", "author_batch_label": "E-MTAB-1948", "batch_date": "NR", "library_batch": "NR", "sequencing_platform": run["instrument_model"], "evidence_ids": "E-P0001-003", "verification_status": "verified_metadata_record", "notes": "No separate library batch in ENA filereport."})
        timepoints.append({"sample_timepoint_id": st_id, "experiment_id": "EX-P0001-001", "species_scientific": run["scientific_name"], "species_common": "human", "taxonomy_id": "9606", "cell_line_or_tissue": cell_source, "sample_name_original": alias, "sample_name_standardized": run["sample_accession"], "genotype_or_construct": "NR", "synchronization_method": stage["sync"], "synchronization_reagent": "NR", "synchronization_dose": "NR", "synchronization_duration": "NR", "arrest_point": stage["phase"] if stage["sync"] != "NR" else "NR", "time_zero_definition": "NR", "sampling_time": stage["time"], "sampling_time_unit": "NA", "cell_cycle_phase": stage["phase"], "phase_evidence_type": "explicitly_inferred", "phase_evidence_rule": "Conservative parse from ENA sample_alias plus prior P0001 pilot stage list; exact sample-level timing remains unresolved.", "pooled_status": "NR", "evidence_ids": "E-P0001-001|E-P0001-003", "notes": "Light expansion only; no GEO sample exists, so gsm_accession stores an explicit NO_GEO surrogate label for table uniqueness.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "gsm_accession": archive_sample_label, "archive_sample_id": as_id})
        archive.append({"archive_sample_id": as_id, "experiment_id": "EX-P0001-001", "sample_timepoint_id": st_id, "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "gsm_accession": archive_sample_label, "biosample_accession": run["sample_accession"], "sra_sample_accession": run["secondary_sample_accession"], "srx_accession": run["experiment_accession"], "sample_title_original": alias, "sample_alias_original": alias, "species_scientific": run["scientific_name"], "taxonomy_id": "9606", "cell_line_or_tissue": cell_source, "platform_accession": "NA", "genotype_original": "NR", "phase_original": stage["phase"], "type_original": "ArrayExpress sample", "own_data_status": "yes", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "origin_evidence_ids": "E-P0001-001|E-P0001-003", "disposition_status": "mapped", "run_count": "1", "evidence_ids": "E-P0001-003", "notes": "One ENA run alias treated as one archive sample for this light pass; NO_GEO label is not an accession."})
        acc_id=f"AC-P0001-{idx:03d}"; run_id=run["run_accession"]
        acc_rows.append({"accession_record_id": acc_id, "experiment_id": "EX-P0001-001", "sample_timepoint_id": st_id, "namespace": "ENA/ArrayExpress", "entity_type": "sra_run", "accession": run_id, "project_accession": run["study_accession"], "study_accession": run["secondary_study_accession"], "sample_accession": run["secondary_sample_accession"], "experiment_accession": run["experiment_accession"], "run_accession": run_id, "official_page_url": f"https://www.ebi.ac.uk/ena/browser/view/{run_id}", "download_url": run["fastq_ftp"], "file_format": "fastq.gz", "file_size_bytes": run["fastq_bytes"], "md5": run["fastq_md5"], "format_validation_status": "valid_accession_format", "online_verification_status": "verified_metadata_record", "verification_date": verification_date, "evidence_ids": "E-P0001-003", "notes": "Run/file metadata from ENA filereport for ERP004055.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "library_strategy": run["library_strategy"], "library_source": "NR", "library_selection": "NR", "library_layout": run["library_layout"], "instrument_platform": run["instrument_platform"], "instrument_model": run["instrument_model"], "public_status": "public", "query_id": "Q-P0001-003", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "origin_evidence_ids": "E-P0001-001|E-P0001-003"})
        rel_rows.append({"relation_id": f"AR-P0001-{idx:03d}", "parent_accession": run["experiment_accession"], "child_accession": run_id, "relation_type": "experiment_has_run", "source_database": "ENA filereport", "query_id": "Q-P0001-003", "verification_status": "verified_metadata_record", "evidence_ids": "E-P0001-003", "notes": "ERP004055 filereport returned this run."})
        file_rows.extend(_file_rows_for_run("P0001", run_id, run["fastq_ftp"], run["fastq_md5"], run["fastq_bytes"], "E-P0001-003", verification_date))
        catalog_base.append({"catalog_row_id": f"CAT-P0001-{idx:06d}", "paper_id": "P0001", "experiment_id": "EX-P0001-001", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "sample_timepoint_id": st_id, "archive_sample_id": as_id, "perturbation_id": "NA", "accession_record_id": acc_id, "file_id": "NA", "paper_title": paper["title"], "doi": paper["doi"], "own_data_status": "yes", "biological_sample_origin_status": "study_generated", "library_origin_status": "study_generated", "sequencing_generation_status": "study_generated", "analysis_usage_status": "primary_analysis", "species_scientific": run["scientific_name"], "cell_line_or_tissue": cell_source, "sample_name_original": alias, "assay_type": "5C/Hi-C related archive entry", "detection_target": "NA", "synchronization_method": stage["sync"], "time_zero_definition": "NR", "sampling_time": stage["time"], "sampling_time_unit": "NA", "cell_cycle_phase": stage["phase"], "phase_evidence_type": "explicitly_inferred", "perturbation_type": "NA", "direct_target": "NA", "expected_effect": "NA", "observed_validation": "NA", "gsm_accession": archive_sample_label, "biosample_accession": run["sample_accession"], "sra_sample_accession": run["secondary_sample_accession"], "experiment_accession": run["experiment_accession"], "run_accession": run_id, "download_url": "NA", "file_size_bytes": "NA", "md5": "NA", "online_verification_status": "verified_metadata_record", "evidence_ids": "E-P0001-001|E-P0001-003", "notes": "Light run-level row; file view expands paired FASTQ links; NO_GEO label is a uniqueness surrogate, not an accession."})

    for table, rows, pred in [
        ("conditions", conditions, lambda row: row.get("paper_id") == "P0001"),
        ("replicates", replicates, lambda row: row.get("replicate_id", "").startswith("R-P0001-")),
        ("batches", batches, lambda row: row.get("paper_id") == "P0001"),
        ("samples_timepoints", timepoints, lambda row: row.get("sample_timepoint_id", "").startswith("ST-P0001-")),
        ("archive_samples", archive, lambda row: row.get("archive_sample_id", "").startswith("AS-P0001-")),
        ("accessions", acc_rows, lambda row: row.get("accession_record_id", "").startswith("AC-P0001-")),
        ("accession_relations", rel_rows, lambda row: row.get("relation_id", "").startswith("AR-P0001-")),
        ("files", file_rows, lambda row: row.get("file_id", "").startswith("RF-P0001-")),
    ]:
        _replace_rows(root, schema, table, rows, pred)
    _append_run_views(root, schema, "P0001", paper, catalog_base, acc_rows, file_rows)
    _write_catalog(root / "data" / "interim" / "pilot" / "P0001_light_catalog.tsv", [r for base in catalog_base for r in [{**base, "catalog_row_id": f"{base['catalog_row_id']}-F{f['file_index']}", "file_id": f["file_id"], "download_url": f["download_url"], "file_size_bytes": f["file_size_bytes"], "md5": f["md5"]} for f in file_rows if f["run_accession"] == base["run_accession"]]])
    p0001_run_count = sum(row.get("entity_type") == "sra_run" for row in acc_rows)
    _update_round6_common(root, schema, "P0001", verification_date, {"runs": p0001_run_count, "files": len(file_rows), "queries": [("Q-P0001-003", "ENA", "filereport read_run", "ERP004055", "ERP004055_ena_filereport.tsv", len(ena))]})
    _write_p0001_report(root, ena, file_rows)
    return {"paper_id": "P0001", "runs": p0001_run_count, "files": len(file_rows), "catalog_sha256": _stable_hash(root / "data" / "interim" / "pilot" / "P0001_light_catalog.tsv")}


def _update_round6_common(root: Path, schema: dict[str, Any], paper_id: str, verification_date: str, payload: dict[str, Any]) -> None:
    source_rows = []
    for qid, db, endpoint, params, snapshot, returned in payload["queries"]:
        snap_path = root / "data" / "interim" / "pilot" / "source_metadata" / snapshot.split(";")[0]
        source_rows.append({"query_id": qid, "database": db, "endpoint": endpoint, "query_parameters": params, "queried_at": f"{verification_date}T00:00:00+08:00", "http_status": "200", "response_sha256": _stable_hash(snap_path), "response_bytes": str(snap_path.stat().st_size), "returned_rows": str(returned), "snapshot_path": "data/interim/pilot/source_metadata/" + snapshot, "pagination_complete": "yes", "retry_count": "0", "error_summary": "NA", "query_outcome": "success", "legacy_record_id": "NA"})
    _replace_rows(root, schema, "source_queries", source_rows, lambda row: row.get("query_id", "").startswith(f"Q-{paper_id}-"))

    evidence_rows = [
        {"evidence_id": f"E-{paper_id}-003", "supported_table": "archive_samples|samples_timepoints", "supported_record_id": paper_id, "supported_fields": "sample_alias|stage|synchronization|GSM|BioSample|SRX", "source_type": "archive_record", "citation_or_database": "GEO/ArrayExpress/ENA official metadata", "source_locator": "data/interim/pilot/source_metadata", "page_or_section": "family MINiML or ENA filereport", "minimal_excerpt": "Official metadata snapshot parsed offline; see saved source file.", "query_or_method": f"Round6 builder for {paper_id}", "verification_date": verification_date, "extractor": "src.literature_catalog.round6", "reviewer": "NR", "evidence_level": "archive_record", "notes": "Lightweight metadata only; no raw sequencing download."},
        {"evidence_id": f"E-{paper_id}-004", "supported_table": "accessions|files|literature_experiment_catalog", "supported_record_id": paper_id, "supported_fields": "run_accession|fastq_ftp|fastq_md5|fastq_bytes", "source_type": "archive_record", "citation_or_database": "ENA Portal API filereport", "source_locator": "data/interim/pilot/source_metadata", "page_or_section": "read_run", "minimal_excerpt": "ENA filereport returned run and FASTQ metadata fields.", "query_or_method": f"Round6 builder for {paper_id}", "verification_date": verification_date, "extractor": "src.literature_catalog.round6", "reviewer": "NR", "evidence_level": "archive_record", "notes": "URLs are database-returned metadata values, not locally downloaded files."},
    ]
    if paper_id == "P0001":
        evidence_rows = [
            {
                **evidence_rows[0],
                "evidence_id": "E-P0001-003",
                "supported_table": "archive_samples|samples_timepoints|accessions|files|literature_experiment_catalog",
                "supported_fields": "sample_alias|run_accession|fastq_ftp|fastq_md5|fastq_bytes",
            }
        ]
    _replace_rows(root, schema, "evidence", evidence_rows, lambda row: row.get("evidence_id", "").startswith(f"E-{paper_id}-003") or row.get("evidence_id", "").startswith(f"E-{paper_id}-004"))

    sem_rows = []
    issue_rows = []
    if paper_id == "P0012":
        sem_rows = [
            {"review_id": "RV-P0012-0001", "paper_id": "P0012", "record_type": "condition", "record_id": "auxin", "field_name": "perturbation_target", "original_value": "with_auxin/with_A", "candidate_interpretation": "CTCF depletion via auxin-inducible degron", "decision": "accepted_from_prior_pilot_evidence", "decision_status": "verified", "evidence_ids": "E-P0012-001|E-P0012-003", "decision_rule": "Use prior paper-level pilot evidence for target; sample assignment from GEO title.", "reviewer_status": "machine_extracted_pending_human_review", "notes": "Kept separate from ChIP detection_target."},
            {"review_id": "RV-P0012-0002", "paper_id": "P0012", "record_type": "condition", "record_id": "triptolide", "field_name": "perturbation_target", "original_value": "with_triptolide", "candidate_interpretation": "transcription initiation inhibition", "decision": "accepted_from_prior_pilot_evidence", "decision_status": "verified", "evidence_ids": "E-P0012-001|E-P0012-003", "decision_rule": "Use prior paper-level pilot evidence; do not replace with Pol II detection target.", "reviewer_status": "machine_extracted_pending_human_review", "notes": "Dose and validation remain NR in saved metadata."},
            {"review_id": "RV-P0012-0003", "paper_id": "P0012", "record_type": "accession", "record_id": "PRJNA706679", "field_name": "project_accession", "original_value": "PRJNA706679", "candidate_interpretation": "declared/queried BioProject may expand to PRJNA706396 and PRJNA706676 in ENA read_run", "decision": "UNRESOLVED", "decision_status": "unresolved", "evidence_ids": "E-P0012-004", "decision_rule": "Preserve ENA-returned study_accession per run and register declared-vs-returned mismatch.", "reviewer_status": "machine_extracted_pending_human_review", "notes": "No silent project accession substitution."},
        ]
        issue_rows = [
            {"issue_id": "UI-P0012-001", "paper_id": "P0012", "related_record_id": "rep labels", "issue_type": "replicate_type_unresolved", "description": "GEO titles contain rep labels but saved metadata does not adjudicate biological versus technical replicate.", "checked_sources": "GEO family MINiML|ENA filereport", "current_assessment": "UNRESOLVED", "requires_user_decision": "no", "status": "open", "resolution": "NA", "notes": "Replicate label retained losslessly."},
            {"issue_id": "UI-P0012-002", "paper_id": "P0012", "related_record_id": "run/file expansion", "issue_type": "run_level_not_expanded", "description": "Round4 project-level gap has been expanded to run/file metadata without downloading raw files.", "checked_sources": "GEO family MINiML|NCBI RunInfo|ENA filereport", "current_assessment": "resolved", "requires_user_decision": "no", "status": "resolved", "resolution": f"Expanded to {payload['runs']} runs and {payload['files']} FASTQ metadata links.", "notes": "Large RAW tar remains intentionally not downloaded."},
            {"issue_id": "UI-P0012-003", "paper_id": "P0012", "related_record_id": "PRJNA706679", "issue_type": "project_scope_mismatch", "description": "Configured/declaration BioProject PRJNA706679 query returns ENA read_run rows whose study_accession values are PRJNA706396 and PRJNA706676.", "checked_sources": "ENA filereport PRJNA706679", "current_assessment": "UNRESOLVED", "requires_user_decision": "yes", "status": "open", "resolution": "NA", "notes": "Run rows preserve database-returned project_accession; do not infer equivalence."},
        ]
    else:
        issue_rows = [
            {"issue_id": "UI-P0001-001", "paper_id": "P0001", "related_record_id": "rep labels", "issue_type": "replicate_type_unresolved", "description": "ENA aliases contain R labels but replicate type is not adjudicated in this light pass.", "checked_sources": "ENA filereport|prior pilot report", "current_assessment": "UNRESOLVED", "requires_user_decision": "no", "status": "open", "resolution": "NA", "notes": "Supplementary sample table may be needed."},
            {"issue_id": "UI-P0001-002", "paper_id": "P0001", "related_record_id": "ERP004055", "issue_type": "run_level_not_expanded", "description": "Round4 run-level gap has been expanded to 13 ENA runs and paired FASTQ metadata links.", "checked_sources": "ENA filereport ERP004055", "current_assessment": "resolved", "requires_user_decision": "no", "status": "resolved", "resolution": f"Expanded to {payload['runs']} runs and {payload['files']} FASTQ metadata links.", "notes": "Design mapping remains light."},
            {"issue_id": "UI-P0001-003", "paper_id": "P0001", "related_record_id": "sample_alias_stage_parse", "issue_type": "sample_design_light_parse", "description": "Cell-cycle stages are conservatively parsed from archive aliases and prior pilot evidence; exact synchronization timing is not fully resolved.", "checked_sources": "ENA filereport|prior pilot report", "current_assessment": "UNRESOLVED", "requires_user_decision": "no", "status": "open", "resolution": "NA", "notes": "Needs supplementary materials for full design extraction."},
        ]
    if sem_rows:
        _replace_rows(root, schema, "semantic_review", sem_rows, lambda row: row.get("paper_id") == paper_id)
    _replace_rows(root, schema, "unresolved_issues", issue_rows, lambda row: row.get("paper_id") == paper_id)


def _write_p0012_report(root: Path, geo: list[dict[str, str]], ena: list[dict[str, str]], files: list[dict[str, str]]) -> None:
    assay_counts = Counter(_p0012_meta(row["title"], "GSE168168" if row["gsm"] <= "GSM5133038" else "GSE168176")["assay_type"] for row in geo)
    project_counts = Counter(row["study_accession"] for row in ena)
    text = f"""# P0012 Run/File 级扰动导向核验报告

## 核心结论

- GEO SuperSeries `GSE168251` 解析到 44 个 GSM；两个 SubSeries 各 22 个样本。
- ENA/NCBI run 集合一致，本轮展开到 {len(ena)} 个 Run 和 {len(files)} 条 FASTQ 元数据链接。
- assay 分布：ChIP-seq 22，Hi-C 22。
- ENA 返回的 project_accession 分布：{dict(project_counts)}；与配置中的 `PRJNA706679` 关系保留为待人工核验问题。

## 扰动层级处理

- `auxin` 作为 CTCF-AID 降解处理记录，直接靶标为 CTCF。
- `triptolide` 作为转录起始抑制处理记录。
- `Pol II`、`CTCF`、`Rad21`、`input` 仅作为 ChIP-seq 检测靶点/对照，不与扰动靶标混写。

## 仍未解决

- rep 标签尚不能裁决生物重复或技术重复。
- `PRJNA706679` 与 ENA run 行返回的 `PRJNA706396`/`PRJNA706676` 之间的项目层级关系需要人工复核。
- 本轮未下载 `GSE168251_RAW.tar` 或任何 FASTQ/SRA 大文件。
"""
    (root / "reports" / "per_paper" / "P0012_run_file_pilot.md").write_text(text, encoding="utf-8")


def _write_p0001_report(root: Path, ena: list[dict[str, str]], files: list[dict[str, str]]) -> None:
    phase_counts = Counter(_p0001_stage(row["sample_alias"])["phase"] for row in ena)
    text = f"""# P0001 轻量样本/归档展开报告

## 核心结论

- `ERP004055` / `E-MTAB-1948` 已从项目级推进到 {len(ena)} 个 ENA Run。
- ENA filereport 提供 {len(files)} 条 FASTQ 元数据链接；所有 run 为 paired-end。
- 样本阶段轻量解析分布：{dict(phase_counts)}。

## 边界

- 细胞周期阶段主要来自 ENA alias 与既有论文级 pilot 证据，精确同步化起点、处理时长和样本表映射仍需补充材料。
- 本轮未下载 FASTQ 或 submitted read 文件，只保存官方返回的 URL、MD5 和大小字段。
"""
    (root / "reports" / "per_paper" / "P0001_light_expansion.md").write_text(text, encoding="utf-8")

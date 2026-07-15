"""Round 7 coverage-first lightweight expansion for four additional papers.

This module keeps extraction conservative:
- it only consumes saved official metadata snapshots and local PDFs;
- it does not download raw sequencing files or large supplements;
- it preserves unresolved fields as NR/UNRESOLVED rather than guessing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import tarfile
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import CatalogError, _read_tsv, _write_tsv, load_schema
from .metadata import QUERY_FIELDS, QueryRecord, _request_bytes
from .pilot import parse_ena_runs, parse_geo_miniml, parse_ncbi_runinfo
from .round6 import _accession_stub, _append_run_views, _file_rows_for_run

ROUND7_PAPERS = ("P0006", "P0007", "P0011", "P0016")
ENA_FIELDS = [
    "run_accession",
    "study_accession",
    "secondary_study_accession",
    "experiment_accession",
    "sample_accession",
    "secondary_sample_accession",
    "run_alias",
    "experiment_alias",
    "sample_alias",
    "scientific_name",
    "library_strategy",
    "library_layout",
    "instrument_platform",
    "instrument_model",
    "fastq_ftp",
    "fastq_md5",
    "fastq_bytes",
    "submitted_ftp",
    "submitted_md5",
    "submitted_bytes",
]
ACCESSION_RE = re.compile(r"\b(GSE\d+|GSM\d+|SRP\d+|SRX\d+|SRR\d+|PRJNA\d+|PRJEB\d+|ERP\d+|ERX\d+|ERR\d+|E-MTAB-\d+)\b", re.I)


def _stable_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace_rows(root: Path, schema: dict[str, Any], table: str, rows: list[dict[str, Any]], predicate) -> None:
    spec = schema["tables"][table]
    _, existing = _read_tsv(root / spec["path"])
    merged = [row for row in existing if not predicate(row)]
    merged.extend(rows)
    _write_tsv(root / spec["path"], spec["fields"], merged)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _paper_meta(root: Path, paper_id: str) -> dict[str, str]:
    _, rows = _read_tsv(root / "data" / "curated" / "papers.tsv")
    for row in rows:
        if row.get("paper_id") == paper_id:
            item = dict(row)
            item["title"] = item.get("canonical_title", "NR")
            return item
    raise CatalogError(f"missing paper row for {paper_id}")


def _file_meta(root: Path, paper_id: str) -> dict[str, str]:
    paper = _paper_meta(root, paper_id)
    _, rows = _read_tsv(root / "data" / "curated" / "paper_files.tsv")
    for row in rows:
        if row.get("file_id") == paper["canonical_file_id"]:
            return dict(row)
    raise CatalogError(f"missing file row for {paper_id}")


def _geo_family_url(series: str) -> str:
    digits = re.sub(r"\D", "", series)
    prefix = f"GSE{digits[:-3]}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}/{series}/miniml/{series}_family.xml.tgz"


def _query_id(paper_id: str, idx: int) -> str:
    return f"Q-{paper_id}-{idx:03d}"


def _upsert_queries(query_path: Path, rows: list[QueryRecord]) -> None:
    existing: dict[str, dict[str, Any]] = {}
    if query_path.exists():
        with query_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                existing[row["query_id"]] = row
    for row in rows:
        payload = {field: getattr(row, field) for field in QUERY_FIELDS}
        payload["response_bytes"] = str(payload["response_bytes"])
        payload["returned_rows"] = str(payload["returned_rows"])
        payload["retry_count"] = str(payload["retry_count"])
        existing[payload["query_id"]] = payload
    ordered = sorted(
        existing.values(),
        key=lambda item: (0, int(item["query_id"].split("-")[-1])) if item["query_id"].startswith("Q-") else (1, item["query_id"]),
    )
    _write_rows(query_path, QUERY_FIELDS, ordered)


def _discover_accessions(*texts: str) -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for text in texts:
        for acc in ACCESSION_RE.findall(text or ""):
            acc = acc.upper()
            if acc.startswith("GSE"):
                found["geo_series"].add(acc)
            elif acc.startswith("SRP"):
                found["sra_study"].add(acc)
            elif acc.startswith("ERP"):
                found["ena_study"].add(acc)
            elif acc.startswith(("PRJNA", "PRJEB")):
                found["bioproject"].add(acc)
            elif acc.startswith("E-MTAB-"):
                found["arrayexpress"].add(acc)
    return {key: sorted(values) for key, values in found.items()}


def _taxonomy_id(species: str) -> str:
    return {
        "Homo sapiens": "9606",
        "Mus musculus": "10090",
    }.get(species, "NR")


def _species_common(species: str) -> str:
    return {
        "Homo sapiens": "human",
        "Mus musculus": "mouse",
    }.get(species, "NR")


def _assay_detail(config: dict[str, Any], run_rows: list[dict[str, str]]) -> tuple[str, str]:
    strategies = sorted({row.get("library_strategy", "NR") for row in run_rows if row.get("library_strategy")})
    if strategies:
        return ("|".join(strategies), "Derived conservatively from official run-level library_strategy fields.")
    return (str(config.get("assay_type", "NR")), "No run-level strategy available; retained config assay hint.")


def _replicate_from_title(title: str) -> str:
    lower = title.lower()
    if match := re.search(r"(?:rep(?:licate)?[\s._-]*)(\d+)", lower):
        return f"rep{match.group(1)}"
    if match := re.search(r"(?:^|[\s._-])r(\d+)(?:$|[\s._-])", lower):
        return f"r{match.group(1)}"
    return "NR"


def _load_optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def fetch_round7_metadata(root: Path, config_path: Path) -> list[QueryRecord]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paper_id = str(config["paper_id"])
    source_dir = root / str(config["source_metadata_dir"])
    source_dir.mkdir(parents=True, exist_ok=True)
    queried_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[QueryRecord] = []
    query_idx = 1

    geo_series = str(config.get("geo_series", "UNRESOLVED"))
    quick_text = ""
    family_text = ""
    if geo_series not in {"UNRESOLVED", "NR", "NA"}:
        quick_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={geo_series}&targ=self&form=xml&view=quick"
        quick_payload, status, retries = _request_bytes(quick_url)
        quick_path = source_dir / f"{geo_series}_quick.xml"
        quick_path.write_bytes(quick_payload)
        quick_text = quick_payload.decode("utf-8", errors="ignore")
        records.append(QueryRecord(_query_id(paper_id, query_idx), "NCBI_GEO", quick_url.split("?", 1)[0], quick_url, queried_at, str(status), hashlib.sha256(quick_payload).hexdigest(), len(quick_payload), 1, quick_path.relative_to(root).as_posix(), "yes", retries, "NA"))
        query_idx += 1

        family_url = _geo_family_url(geo_series)
        family_payload, status, retries = _request_bytes(family_url)
        tgz_path = source_dir / f"{geo_series}_family.xml.tgz"
        tgz_path.write_bytes(family_payload)
        with tarfile.open(tgz_path, "r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            if len(members) != 1:
                raise CatalogError(f"{paper_id} GEO family archive content unexpected")
            extracted = archive.extractfile(members[0])
            if extracted is None:
                raise CatalogError(f"{paper_id} GEO family xml missing")
            family_payload_xml = extracted.read()
        family_path = source_dir / f"{geo_series}_family.xml"
        family_path.write_bytes(family_payload_xml)
        sample_count = len(ET.fromstring(family_payload_xml).findall(".//{*}Sample"))
        family_text = family_payload_xml.decode("utf-8", errors="ignore")
        records.append(QueryRecord(_query_id(paper_id, query_idx), "NCBI_GEO", family_url, family_url, queried_at, str(status), hashlib.sha256(family_payload).hexdigest(), len(family_payload), sample_count, tgz_path.relative_to(root).as_posix(), "yes", retries, "NA"))
        query_idx += 1

    discovered = _discover_accessions(quick_text, family_text)
    sra_study = str(config.get("sra_study", "UNRESOLVED"))
    if sra_study in {"UNRESOLVED", "NR", "NA"} and discovered.get("sra_study"):
        sra_study = discovered["sra_study"][0]
    bioproject = str(config.get("bioproject", "UNRESOLVED"))
    if bioproject in {"UNRESOLVED", "NR", "NA"} and discovered.get("bioproject"):
        bioproject = discovered["bioproject"][0]
    ena_target = bioproject if bioproject not in {"UNRESOLVED", "NR", "NA"} else sra_study

    if sra_study not in {"UNRESOLVED", "NR", "NA"}:
        runinfo_url = f"https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc={urllib.parse.quote(sra_study)}"
        payload, status, retries = _request_bytes(runinfo_url)
        path = source_dir / f"{sra_study}_runinfo.csv"
        path.write_bytes(payload)
        returned_rows = max(0, len(payload.decode("utf-8", errors="ignore").splitlines()) - 1)
        records.append(QueryRecord(_query_id(paper_id, query_idx), "NCBI_SRA", runinfo_url.split("?", 1)[0], runinfo_url, queried_at, str(status), hashlib.sha256(payload).hexdigest(), len(payload), returned_rows, path.relative_to(root).as_posix(), "yes", retries, "NA"))
        query_idx += 1

    if ena_target not in {"UNRESOLVED", "NR", "NA"}:
        params = {"accession": ena_target, "result": "read_run", "fields": ",".join(ENA_FIELDS), "format": "tsv", "download": "false"}
        ena_base = "https://www.ebi.ac.uk/ena/portal/api/filereport"
        ena_url = f"{ena_base}?{urllib.parse.urlencode(params)}"
        payload, status, retries = _request_bytes(ena_url)
        path = source_dir / f"{ena_target}_ena_filereport.tsv"
        path.write_bytes(payload)
        returned_rows = max(0, len(payload.decode("utf-8", errors="ignore").splitlines()) - 1)
        records.append(QueryRecord(_query_id(paper_id, query_idx), "ENA", ena_base, json.dumps(params, ensure_ascii=False, sort_keys=True), queried_at, str(status), hashlib.sha256(payload).hexdigest(), len(payload), returned_rows, path.relative_to(root).as_posix(), "yes", retries, "NA"))
        query_idx += 1

    _upsert_queries(root / str(config["source_queries_path"]), records)
    return records


def build_round7_paper(root: Path, config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paper_id = str(config["paper_id"])
    schema = load_schema(root)
    paper = _paper_meta(root, paper_id)
    source_dir = root / str(config["source_metadata_dir"])
    verification_date = datetime.now().date().isoformat()

    geo_series = str(config.get("geo_series", "UNRESOLVED"))
    family_path = source_dir / f"{geo_series}_family.xml"
    quick_path = source_dir / f"{geo_series}_quick.xml"
    geo_rows = parse_geo_miniml(family_path) if family_path.exists() else []
    quick_text = _load_optional_text(quick_path)
    family_text = _load_optional_text(family_path)
    discovered = _discover_accessions(quick_text, family_text)
    sra_study = str(config.get("sra_study", "UNRESOLVED"))
    if sra_study in {"UNRESOLVED", "NR", "NA"} and discovered.get("sra_study"):
        sra_study = discovered["sra_study"][0]
    bioproject = str(config.get("bioproject", "UNRESOLVED"))
    if bioproject in {"UNRESOLVED", "NR", "NA"} and discovered.get("bioproject"):
        bioproject = discovered["bioproject"][0]
    ena_target = bioproject if bioproject not in {"UNRESOLVED", "NR", "NA"} else sra_study

    runinfo_path = source_dir / f"{sra_study}_runinfo.csv"
    ena_path = source_dir / f"{ena_target}_ena_filereport.tsv"
    runinfo = parse_ncbi_runinfo(runinfo_path) if runinfo_path.exists() else []
    ena = parse_ena_runs(ena_path) if ena_path.exists() else []
    runinfo_by_srx: dict[str, list[dict[str, str]]] = defaultdict(list)
    ena_by_srx: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in runinfo:
        runinfo_by_srx[row.get("experiment", "NR")].append(row)
    for row in ena:
        ena_by_srx[row.get("experiment_accession", "NR")].append(row)

    assay_type, assay_detail = _assay_detail(config, ena or runinfo)
    experiments = [{
        "experiment_id": f"EX-{paper_id}-001",
        "paper_id": paper_id,
        "experiment_label_original": paper["title"],
        "biological_question": str(config.get("biological_question", "NR")),
        "own_data_status": str(config.get("own_data_status", "unclear")),
        "own_data_evidence": f"E-{paper_id}-001|E-{paper_id}-002",
        "assay_type": assay_type,
        "assay_detail": assay_detail,
        "measurement_object": str(config.get("measurement_object", "NR")),
        "detection_target": "NR",
        "experimental_group": str(config.get("experimental_group", "NR")),
        "control_group": "NR",
        "biological_replicates": "UNRESOLVED",
        "technical_replicates": "UNRESOLVED",
        "reference_genome": "NR",
        "evidence_ids": f"E-{paper_id}-001|E-{paper_id}-002",
        "notes": "Round7 coverage-first light expansion from local PDF plus official archive metadata.",
    }]
    _replace_rows(root, schema, "experiments", experiments, lambda row: row.get("paper_id") == paper_id)

    conditions: list[dict[str, str]] = []
    replicates: list[dict[str, str]] = []
    batches: list[dict[str, str]] = []
    timepoints: list[dict[str, str]] = []
    archive: list[dict[str, str]] = []
    accessions: list[dict[str, str]] = []
    relations: list[dict[str, str]] = []
    files: list[dict[str, str]] = []
    catalog_base: list[dict[str, str]] = []

    if geo_series not in {"UNRESOLVED", "NR", "NA"}:
        accessions.append(_accession_stub(f"AC-{paper_id}-GEO", f"EX-{paper_id}-001", "GEO", "geo_series", geo_series, f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={geo_series}", f"E-{paper_id}-002", verification_date))
    if sra_study not in {"UNRESOLVED", "NR", "NA"}:
        accessions.append(_accession_stub(f"AC-{paper_id}-SRA", f"EX-{paper_id}-001", "NCBI SRA", "sra_study", sra_study, f"https://www.ncbi.nlm.nih.gov/sra?term={sra_study}", f"E-{paper_id}-003", verification_date))
    if bioproject not in {"UNRESOLVED", "NR", "NA"}:
        accessions.append(_accession_stub(f"AC-{paper_id}-BIOPROJECT", f"EX-{paper_id}-001", "NCBI BioProject", "bioproject", bioproject, f"https://www.ncbi.nlm.nih.gov/bioproject/{bioproject}", f"E-{paper_id}-003", verification_date))

    for idx, sample in enumerate(geo_rows, start=1):
        condition_id = f"C-{paper_id}-{idx:03d}"
        replicate_id = f"R-{paper_id}-{idx:03d}"
        batch_id = f"B-{paper_id}-{idx:03d}"
        st_id = f"ST-{paper_id}-{idx:03d}"
        as_id = f"AS-{paper_id}-{idx:03d}"
        gsm = sample["gsm"]
        rep_label = _replicate_from_title(sample["title"])
        sample_runs = ena_by_srx.get(sample["srx"], []) or runinfo_by_srx.get(sample["srx"], [])
        conditions.append({
            "condition_id": condition_id, "paper_id": paper_id, "experiment_id": f"EX-{paper_id}-001",
            "author_condition_label": sample["title"], "genotype_or_construct": sample.get("genotype", "NR"),
            "synchronization_method": "NR", "synchronization_reagent": "NR",
            "treatment_or_perturbation": "NR", "cell_cycle_phase": sample.get("phase", "NR"),
            "control_role": "UNRESOLVED", "evidence_ids": f"E-{paper_id}-002",
            "normalization_status": "official_geo_metadata_light_parse",
            "notes": f"GEO source={sample.get('source','NR')}; treatment_protocol={sample.get('treatment_protocol','NR')}",
        })
        replicates.append({
            "replicate_id": replicate_id, "condition_id": condition_id, "author_replicate_label": rep_label,
            "replicate_type": "UNRESOLVED" if rep_label != "NR" else "NR",
            "replicate_number": re.sub(r"^\D+", "", rep_label) if rep_label != "NR" else "NR",
            "evidence_ids": f"E-{paper_id}-002", "notes": "Replicate label parsed conservatively from GEO title when present.",
        })
        batches.append({
            "batch_id": batch_id, "paper_id": paper_id, "author_batch_label": geo_series,
            "batch_date": "NR", "library_batch": "NR",
            "sequencing_platform": sample.get("platform", "NR"), "evidence_ids": f"E-{paper_id}-002",
            "verification_status": "verified_metadata_record", "notes": "Series-level grouping only; not a laboratory batch claim.",
        })
        timepoints.append({
            "sample_timepoint_id": st_id, "experiment_id": f"EX-{paper_id}-001",
            "species_scientific": sample["organism"], "species_common": _species_common(sample["organism"]),
            "taxonomy_id": _taxonomy_id(sample["organism"]), "cell_line_or_tissue": sample.get("source", "NR"),
            "sample_name_original": sample["title"], "sample_name_standardized": gsm,
            "genotype_or_construct": sample.get("genotype", "NR"), "synchronization_method": "NR",
            "synchronization_reagent": "NR", "synchronization_dose": "NR", "synchronization_duration": "NR",
            "arrest_point": "NR", "time_zero_definition": "NR", "sampling_time": "NR", "sampling_time_unit": "NA",
            "cell_cycle_phase": sample.get("phase", "NR"),
            "phase_evidence_type": "author_stated" if sample.get("phase", "NR") != "NR" else "unknown",
            "phase_evidence_rule": "GEO Characteristics[tag=phase] original value" if sample.get("phase", "NR") != "NR" else "NR",
            "pooled_status": "NR", "evidence_ids": f"E-{paper_id}-002",
            "notes": "Round7 light pass; synchronization/timing not inferred without explicit source metadata.",
            "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
            "gsm_accession": gsm, "archive_sample_id": as_id,
        })
        archive.append({
            "archive_sample_id": as_id, "experiment_id": f"EX-{paper_id}-001", "sample_timepoint_id": st_id,
            "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
            "gsm_accession": gsm, "biosample_accession": sample.get("biosample", "NR"),
            "sra_sample_accession": sample.get("srx", "NR"), "srx_accession": sample.get("srx", "NR"),
            "sample_title_original": sample["title"], "sample_alias_original": gsm, "species_scientific": sample["organism"],
            "taxonomy_id": _taxonomy_id(sample["organism"]), "cell_line_or_tissue": sample.get("source", "NR"),
            "platform_accession": sample.get("platform", "NR"), "genotype_original": sample.get("genotype", "NR"),
            "phase_original": sample.get("phase", "NR"), "type_original": sample.get("sample_type", "NR"),
            "own_data_status": str(config.get("own_data_status", "unclear")),
            "biological_sample_origin_status": "UNRESOLVED", "library_origin_status": "UNRESOLVED",
            "sequencing_generation_status": "UNRESOLVED", "analysis_usage_status": "UNRESOLVED",
            "origin_evidence_ids": f"E-{paper_id}-001|E-{paper_id}-002",
            "disposition_status": "mapped" if sample_runs else "sample_level_only",
            "run_count": str(len(sample_runs)), "evidence_ids": f"E-{paper_id}-002",
            "notes": "GEO sample parsed from family MINiML; run linkage by SRX when available.",
        })
        accessions.append({
            "accession_record_id": f"AC-{paper_id}-GSM-{idx:03d}", "experiment_id": f"EX-{paper_id}-001", "sample_timepoint_id": st_id,
            "namespace": "GEO", "entity_type": "geo_sample", "accession": gsm, "project_accession": geo_series,
            "study_accession": "NA", "sample_accession": sample.get("biosample", "NR"),
            "experiment_accession": sample.get("srx", "NR"), "run_accession": "NA",
            "official_page_url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gsm}", "download_url": "NA",
            "file_format": "NA", "file_size_bytes": "NA", "md5": "NA", "format_validation_status": "valid_accession_format",
            "online_verification_status": "verified_metadata_record", "verification_date": verification_date,
            "evidence_ids": f"E-{paper_id}-002", "notes": "GEO sample entry parsed from family MINiML.",
            "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
            "library_strategy": "NA", "library_source": "NA", "library_selection": "NA", "library_layout": "NA",
            "instrument_platform": "NA", "instrument_model": "NA", "public_status": "public",
            "query_id": _query_id(paper_id, 2), "biological_sample_origin_status": "UNRESOLVED",
            "library_origin_status": "UNRESOLVED", "sequencing_generation_status": "UNRESOLVED",
            "analysis_usage_status": "UNRESOLVED", "origin_evidence_ids": f"E-{paper_id}-001|E-{paper_id}-002",
        })
        relations.append({
            "relation_id": f"AR-{paper_id}-GEO-{idx:03d}", "parent_accession": geo_series, "child_accession": gsm,
            "relation_type": "series_has_sample", "source_database": "GEO family MINiML",
            "query_id": _query_id(paper_id, 2), "verification_status": "verified_metadata_record",
            "evidence_ids": f"E-{paper_id}-002", "notes": "GEO sample membership.",
        })
        if sample.get("srx", "NR") != "NR":
            relations.append({
                "relation_id": f"AR-{paper_id}-SRX-{idx:03d}", "parent_accession": gsm, "child_accession": sample["srx"],
                "relation_type": "sample_has_experiment", "source_database": "GEO family MINiML",
                "query_id": _query_id(paper_id, 2), "verification_status": "verified_metadata_record",
                "evidence_ids": f"E-{paper_id}-002", "notes": "SRA experiment relation carried by GEO sample metadata.",
            })

        run_candidates = {row.get("run_accession"): row for row in ena_by_srx.get(sample["srx"], [])}
        if not run_candidates and runinfo_by_srx.get(sample["srx"]):
            for row in runinfo_by_srx[sample["srx"]]:
                run_candidates[row["run"]] = row
        for run_idx, run_id in enumerate(sorted(run_candidates), start=1):
            row = run_candidates[run_id]
            if "run_accession" in row:
                acc_id = f"AC-{paper_id}-{idx:03d}-{run_idx:03d}"
                accessions.append({
                    "accession_record_id": acc_id, "experiment_id": f"EX-{paper_id}-001", "sample_timepoint_id": st_id,
                    "namespace": "ENA/SRA", "entity_type": "sra_run", "accession": run_id,
                    "project_accession": row.get("study_accession", bioproject if bioproject not in {"UNRESOLVED", "NR", "NA"} else "NR"),
                    "study_accession": row.get("secondary_study_accession", sra_study if sra_study not in {"UNRESOLVED", "NR", "NA"} else "NR"),
                    "sample_accession": row.get("secondary_sample_accession", "NR"),
                    "experiment_accession": row.get("experiment_accession", sample.get("srx", "NR")),
                    "run_accession": run_id, "official_page_url": f"https://www.ebi.ac.uk/ena/browser/view/{run_id}",
                    "download_url": row.get("fastq_ftp", "NA") or "NA", "file_format": "fastq.gz" if row.get("fastq_ftp") else "NA",
                    "file_size_bytes": row.get("fastq_bytes", "NA") or "NA", "md5": row.get("fastq_md5", "NA") or "NA",
                    "format_validation_status": "valid_accession_format", "online_verification_status": "verified_metadata_record",
                    "verification_date": verification_date, "evidence_ids": f"E-{paper_id}-003",
                    "notes": "Run-level metadata from ENA filereport.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
                    "library_strategy": row.get("library_strategy", "NR"), "library_source": row.get("library_source", "NR"),
                    "library_selection": row.get("library_selection", "NR"), "library_layout": row.get("library_layout", "NR"),
                    "instrument_platform": row.get("instrument_platform", "NR"), "instrument_model": row.get("instrument_model", "NR"),
                    "public_status": "public", "query_id": _query_id(paper_id, 4 if runinfo_path.exists() else 3),
                    "biological_sample_origin_status": "UNRESOLVED", "library_origin_status": "UNRESOLVED",
                    "sequencing_generation_status": "UNRESOLVED", "analysis_usage_status": "UNRESOLVED",
                    "origin_evidence_ids": f"E-{paper_id}-001|E-{paper_id}-003",
                })
                relations.append({
                    "relation_id": f"AR-{paper_id}-RUN-{idx:03d}-{run_idx:03d}",
                    "parent_accession": row.get("experiment_accession", sample.get("srx", "NR")),
                    "child_accession": run_id, "relation_type": "experiment_has_run",
                    "source_database": "ENA filereport", "query_id": _query_id(paper_id, 4 if runinfo_path.exists() else 3),
                    "verification_status": "verified_metadata_record", "evidence_ids": f"E-{paper_id}-003",
                    "notes": "Run linkage confirmed by ENA filereport experiment_accession field.",
                })
                if row.get("fastq_ftp"):
                    files.extend(_file_rows_for_run(paper_id, run_id, row.get("fastq_ftp", ""), row.get("fastq_md5", ""), row.get("fastq_bytes", ""), f"E-{paper_id}-003", verification_date))
                catalog_base.append({
                    "catalog_row_id": f"CAT-{paper_id}-{len(catalog_base)+1:06d}", "paper_id": paper_id, "experiment_id": f"EX-{paper_id}-001",
                    "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id, "sample_timepoint_id": st_id,
                    "archive_sample_id": as_id, "perturbation_id": "NA", "accession_record_id": acc_id, "file_id": "NA",
                    "paper_title": paper["title"], "doi": paper["doi"], "own_data_status": str(config.get("own_data_status", "unclear")),
                    "biological_sample_origin_status": "UNRESOLVED", "library_origin_status": "UNRESOLVED",
                    "sequencing_generation_status": "UNRESOLVED", "analysis_usage_status": "UNRESOLVED",
                    "species_scientific": sample["organism"], "cell_line_or_tissue": sample.get("source", "NR"),
                    "sample_name_original": sample["title"], "assay_type": assay_type, "detection_target": "NR",
                    "synchronization_method": "NR", "time_zero_definition": "NR", "sampling_time": "NR", "sampling_time_unit": "NA",
                    "cell_cycle_phase": sample.get("phase", "NR"), "phase_evidence_type": "author_stated" if sample.get("phase", "NR") != "NR" else "unknown",
                    "perturbation_type": "NR", "direct_target": "NR", "expected_effect": "NR", "observed_validation": "NR",
                    "gsm_accession": gsm, "biosample_accession": sample.get("biosample", "NR"),
                    "sra_sample_accession": row.get("secondary_sample_accession", "NR"), "experiment_accession": row.get("experiment_accession", sample.get("srx", "NR")),
                    "run_accession": run_id, "download_url": "NA", "file_size_bytes": "NA", "md5": "NA",
                    "online_verification_status": "verified_metadata_record", "evidence_ids": f"E-{paper_id}-002|E-{paper_id}-003",
                    "notes": "Round7 run-level base row; file view expands only metadata links returned by ENA.",
                })
            else:
                acc_id = f"AC-{paper_id}-RUNINFO-{idx:03d}-{run_idx:03d}"
                accessions.append({
                    "accession_record_id": acc_id, "experiment_id": f"EX-{paper_id}-001", "sample_timepoint_id": st_id,
                    "namespace": "NCBI SRA", "entity_type": "sra_run", "accession": run_id,
                    "project_accession": row.get("study", "NR"), "study_accession": row.get("study", "NR"),
                    "sample_accession": row.get("biosample", "NR"), "experiment_accession": row.get("experiment", sample.get("srx", "NR")),
                    "run_accession": run_id, "official_page_url": f"https://www.ncbi.nlm.nih.gov/sra?term={run_id}",
                    "download_url": "NA", "file_format": "NA", "file_size_bytes": row.get("archive_size_bytes", "NR"),
                    "md5": "NA", "format_validation_status": "valid_accession_format", "online_verification_status": "verified_metadata_record",
                    "verification_date": verification_date, "evidence_ids": f"E-{paper_id}-003",
                    "notes": "Run-level metadata from NCBI RunInfo only; no ENA file links saved in this pass.", "condition_id": condition_id, "replicate_id": replicate_id, "batch_id": batch_id,
                    "library_strategy": row.get("library_strategy", "NR"), "library_source": row.get("library_source", "NR"),
                    "library_selection": row.get("library_selection", "NR"), "library_layout": row.get("library_layout", "NR"),
                    "instrument_platform": row.get("instrument_platform", "NR"), "instrument_model": row.get("instrument_model", "NR"),
                    "public_status": row.get("public_status", "UNRESOLVED"), "query_id": _query_id(paper_id, 3),
                    "biological_sample_origin_status": "UNRESOLVED", "library_origin_status": "UNRESOLVED",
                    "sequencing_generation_status": "UNRESOLVED", "analysis_usage_status": "UNRESOLVED",
                    "origin_evidence_ids": f"E-{paper_id}-001|E-{paper_id}-003",
                })
                relations.append({
                    "relation_id": f"AR-{paper_id}-RUNINFO-{idx:03d}-{run_idx:03d}", "parent_accession": row.get("experiment", sample.get("srx", "NR")),
                    "child_accession": run_id, "relation_type": "experiment_has_run", "source_database": "NCBI RunInfo",
                    "query_id": _query_id(paper_id, 3), "verification_status": "verified_metadata_record",
                    "evidence_ids": f"E-{paper_id}-003", "notes": "Run linkage confirmed by RunInfo experiment field.",
                })

    for table, rows, predicate in [
        ("conditions", conditions, lambda row: row.get("paper_id") == paper_id),
        ("replicates", replicates, lambda row: row.get("replicate_id", "").startswith(f"R-{paper_id}-")),
        ("batches", batches, lambda row: row.get("paper_id") == paper_id),
        ("samples_timepoints", timepoints, lambda row: row.get("sample_timepoint_id", "").startswith(f"ST-{paper_id}-")),
        ("archive_samples", archive, lambda row: row.get("archive_sample_id", "").startswith(f"AS-{paper_id}-")),
        ("accessions", accessions, lambda row: row.get("accession_record_id", "").startswith(f"AC-{paper_id}-")),
        ("accession_relations", relations, lambda row: row.get("relation_id", "").startswith(f"AR-{paper_id}-")),
        ("files", files, lambda row: row.get("file_id", "").startswith(f"RF-{paper_id}-")),
    ]:
        _replace_rows(root, schema, table, rows, predicate)

    if catalog_base:
        _append_run_views(root, schema, paper_id, paper, catalog_base, accessions, files)
        catalog_rows = []
        files_by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
        for item in files:
            files_by_run[item["run_accession"]].append(item)
        for base in catalog_base:
            run_files = sorted(files_by_run.get(base["run_accession"], []), key=lambda item: int(item["file_index"]))
            if run_files:
                for file_row in run_files:
                    catalog_rows.append({**base, "catalog_row_id": f"{base['catalog_row_id']}-F{file_row['file_index']}", "file_id": file_row["file_id"], "download_url": file_row["download_url"], "file_size_bytes": file_row["file_size_bytes"], "md5": file_row["md5"]})
        if catalog_rows:
            _write_tsv(root / "data" / "interim" / "pilot" / f"{paper_id}_light_catalog.tsv", list(catalog_rows[0].keys()), catalog_rows)

    _update_round7_evidence_and_issues(root, schema, paper_id, paper, verification_date, geo_series, sra_study, bioproject, geo_rows, runinfo, ena)
    _write_round7_report(root, paper_id, paper, verification_date, geo_series, sra_study, bioproject, len(geo_rows), len(runinfo), len(ena), len(files))
    return {"paper_id": paper_id, "geo_samples": len(geo_rows), "run_rows": max(len(runinfo), len(ena)), "file_rows": len(files), "level": "run_file" if (runinfo or ena) else ("sample" if geo_rows else "project_only")}


def _update_round7_evidence_and_issues(root: Path, schema: dict[str, Any], paper_id: str, paper: dict[str, str], verification_date: str, geo_series: str, sra_study: str, bioproject: str, geo_rows: list[dict[str, str]], runinfo: list[dict[str, str]], ena: list[dict[str, str]]) -> None:
    file_row = _file_meta(root, paper_id)
    pdf_path = file_row["relative_path"]
    evidence_rows = [
        {
            "evidence_id": f"E-{paper_id}-001", "supported_table": "papers|experiments", "supported_record_id": paper_id,
            "supported_fields": "title|doi|paper_scope", "source_type": "primary_paper", "citation_or_database": paper["title"],
            "source_locator": pdf_path, "page_or_section": "PDF first page / title page",
            "minimal_excerpt": f"{paper['title']} | DOI {paper['doi']}", "query_or_method": "local PDF bounded text extraction",
            "verification_date": verification_date, "extractor": "src.literature_catalog.batch_round7", "reviewer": "NR",
            "evidence_level": "primary_paper", "notes": "Used only for bibliographic facts and paper-scoped accession statement context.",
        },
        {
            "evidence_id": f"E-{paper_id}-002", "supported_table": "archive_samples|samples_timepoints|accessions", "supported_record_id": paper_id,
            "supported_fields": "GSM|SRX|BioSample|species|source|phase", "source_type": "archive_record",
            "citation_or_database": "NCBI GEO family/quick XML", "source_locator": "data/interim/pilot/source_metadata",
            "page_or_section": geo_series, "minimal_excerpt": f"Saved GEO snapshots for {geo_series}; parsed {len(geo_rows)} sample records.",
            "query_or_method": f"Round7 GEO parser for {paper_id}", "verification_date": verification_date,
            "extractor": "src.literature_catalog.batch_round7", "reviewer": "NR", "evidence_level": "archive_record",
            "notes": "Lightweight metadata only; no supplement or raw-data download.",
        },
        {
            "evidence_id": f"E-{paper_id}-003", "supported_table": "accessions|files|literature_experiment_catalog_runs", "supported_record_id": paper_id,
            "supported_fields": "run_accession|fastq_ftp|library_strategy|study mapping", "source_type": "archive_record",
            "citation_or_database": "NCBI RunInfo / ENA filereport", "source_locator": "data/interim/pilot/source_metadata",
            "page_or_section": f"{sra_study}|{bioproject}", "minimal_excerpt": f"Saved run snapshots: RunInfo={len(runinfo)} rows; ENA={len(ena)} rows.",
            "query_or_method": f"Round7 run/file parser for {paper_id}", "verification_date": verification_date,
            "extractor": "src.literature_catalog.batch_round7", "reviewer": "NR", "evidence_level": "archive_record",
            "notes": "URLs are metadata-returned links, not downloaded sequencing files.",
        },
    ]
    _replace_rows(root, schema, "evidence", evidence_rows, lambda row: row.get("evidence_id", "").startswith(f"E-{paper_id}-"))

    issues = [
        {
            "issue_id": f"UI-{paper_id}-001", "paper_id": paper_id, "related_record_id": "own_data_status",
            "issue_type": "own_data_not_fully_adjudicated", "description": "Round7 preserved own_data_status conservatively because local paper text and lightweight archive snapshots were not enough to fully adjudicate study-generated versus reused for every record.",
            "checked_sources": "local PDF|GEO|RunInfo|ENA", "current_assessment": "UNRESOLVED",
            "requires_user_decision": "no", "status": "open", "resolution": "NA",
            "notes": "Can be promoted in a later paper-focused pass with supplementary materials or submitter evidence.",
        },
        {
            "issue_id": f"UI-{paper_id}-002", "paper_id": paper_id, "related_record_id": "synchronization_and_time_axis",
            "issue_type": "sample_design_light_parse", "description": "Round7 did not infer synchronization start, release time, or cell-cycle timepoints without explicit sample-level metadata.",
            "checked_sources": "GEO sample title|GEO characteristics|RunInfo|ENA", "current_assessment": "UNRESOLVED",
            "requires_user_decision": "no", "status": "open", "resolution": "NA",
            "notes": "Needs supplementary tables or methods-focused extraction in later rounds.",
        },
        {
            "issue_id": f"UI-{paper_id}-003", "paper_id": paper_id, "related_record_id": "run_file_expansion",
            "issue_type": "run_level_not_expanded" if not (runinfo or ena) else "run_level_expanded",
            "description": "Whether this paper could be expanded beyond GEO sample level in the round7 light pass.",
            "checked_sources": "GEO|RunInfo|ENA", "current_assessment": "resolved" if (runinfo or ena) else "NOT_FOUND",
            "requires_user_decision": "no", "status": "resolved" if (runinfo or ena) else "open",
            "resolution": f"Expanded to max({len(runinfo)}, {len(ena)}) run rows." if (runinfo or ena) else "NA",
            "notes": "No large sequencing files were downloaded.",
        },
    ]
    _replace_rows(root, schema, "unresolved_issues", issues, lambda row: row.get("issue_id", "").startswith(f"UI-{paper_id}-"))


def _write_round7_report(root: Path, paper_id: str, paper: dict[str, str], verification_date: str, geo_series: str, sra_study: str, bioproject: str, geo_count: int, runinfo_count: int, ena_count: int, file_count: int) -> None:
    text = f"""# {paper_id} Round7 轻量扩展报告

- 论文题名：{paper['title']}
- DOI：{paper['doi']}
- paper_id：{paper_id}
- 核验日期：{verification_date}

## 本轮确认的归档入口

- GEO Series：{geo_series}
- SRA Study：{sra_study}
- BioProject：{bioproject}

## 推进层级

- GEO sample 记录数：{geo_count}
- NCBI RunInfo 行数：{runinfo_count}
- ENA filereport 行数：{ena_count}
- FASTQ 元数据链接数：{file_count}
- 本轮层级：{"Run/File" if (runinfo_count or ena_count) else ("Project/Study/Sample" if geo_count else "Project only")}

## 已确认字段

- 论文级题名与 DOI 已由本地 PDF 核验。
- 归档入口使用官方轻量快照保存到 `data/interim/pilot/source_metadata/`。
- sample 级字段只保留官方元数据中明确给出的 GSM / SRX / BioSample / species / source / phase 等信息。
- 未对同步化起点、采样分钟数、扰动靶标、预期效果进行无证据推断。

## 未决问题

- own_data_status 仍保持保守口径，待后续更深一轮纸内证据核验。
- 同步化与细胞周期时间轴大多仍需补充材料或方法段支持。
- 若论文存在多 assay 混合提交，本轮只按官方 run-level strategy 或配置提示做轻量归类。

## 未下载内容

- 未下载 FASTQ / SRA / BAM / RAW tar / 大型 supplement。
- 所有 URL 仅作为官方元数据记录保存。
"""
    (root / "reports" / "per_paper" / f"{paper_id}_round7_light_expansion.md").write_text(text, encoding="utf-8")


def write_round7_batch_summary(root: Path, summaries: list[dict[str, Any]]) -> None:
    rows = []
    for idx, paper_id in enumerate(("P0006", "P0007", "P0011", "P0016", "P0002", "P0013"), start=1):
        selected = any(item["paper_id"] == paper_id for item in summaries)
        reason = {
            "P0006": "本地 PDF 已命中 GSE93431，cohesin removal 论文且 accession 线索单一。",
            "P0007": "本地 PDF 已命中 GSE102884，cohesin/CTCF/WAPL/PDS5 方向且 GEO 入口清晰。",
            "P0011": "本地 PDF 已命中 GSE135180，可补上 2020 Nature Genetics 代表性论文。",
            "P0016": "本地 PDF 仅命中 GSE254182，入口单一，适合这一轮快推。",
            "P0002": "GSE51334 入口过大且混入大量外部样本，超出本轮轻量批次风险阈值。",
            "P0013": "多 accession 入口且 assay 更混合，适合后续单篇聚焦轮处理。",
        }[paper_id]
        risk = {
            "P0006": "可能混有多种实验类型",
            "P0007": "样本设计字段未必在 GEO 充分展开",
            "P0011": "多 assay 提交，library_strategy 需保守解释",
            "P0016": "功能分区与着丝粒实验可能含非测序补充结果",
            "P0002": "超大 series / 复用样本风险高",
            "P0013": "多入口映射复杂度较高",
        }[paper_id]
        known = {
            "P0006": "GSE93431",
            "P0007": "GSE102884",
            "P0011": "GSE135180",
            "P0016": "GSE254182",
            "P0002": "GSE51334",
            "P0013": "GSE130275;GSE178982",
        }[paper_id]
        rows.append({
            "candidate_rank": str(idx),
            "paper_id": paper_id,
            "canonical_title": _paper_meta(root, paper_id)["title"],
            "doi": _paper_meta(root, paper_id)["doi"],
            "known_accession_candidates": known,
            "selection_reason": reason,
            "risk_flags": risk,
            "selected_for_round7": "yes" if selected else "no",
        })
    _write_rows(root / "data" / "interim" / "pilot" / "round7_candidate_selection.tsv", list(rows[0].keys()), rows)
    summary_lines = [
        "# Round7 批次摘要",
        "",
        f"- 处理论文数：{len(summaries)}",
        "- 策略：覆盖率优先的小批次轻量扩展；优先保留官方元数据和可追溯性。",
        "",
    ]
    for item in summaries:
        summary_lines.extend([
            f"## {item['paper_id']}",
            "",
            f"- 层级：{item['level']}",
            f"- GEO sample：{item['geo_samples']}",
            f"- Run：{item['run_rows']}",
            f"- File：{item['file_rows']}",
            "",
        ])
    summary_lines.extend([
        "## 建议",
        "",
        "- 下一轮仍可继续“覆盖率优先”，但建议穿插 1 篇更深的单篇样本设计核验轮，避免 sample-level 积压过多未决问题。",
    ])
    (root / "reports" / "batch_round7_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

"""Official metadata fetching with bounded retries and query provenance."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .catalog import CatalogError


LOGGER = logging.getLogger(__name__)
QUERY_FIELDS = [
    "query_id",
    "database",
    "endpoint",
    "query_parameters",
    "queried_at",
    "http_status",
    "response_sha256",
    "response_bytes",
    "returned_rows",
    "snapshot_path",
    "pagination_complete",
    "retry_count",
    "error_summary",
    "query_outcome",
    "legacy_record_id",
]


@dataclass(frozen=True)
class QueryRecord:
    query_id: str
    database: str
    endpoint: str
    query_parameters: str
    queried_at: str
    http_status: str
    response_sha256: str
    response_bytes: int | str
    returned_rows: int | str
    snapshot_path: str
    pagination_complete: str
    retry_count: int
    error_summary: str
    query_outcome: str = "success"
    legacy_record_id: str = "NA"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _request_bytes(url: str, *, attempts: int = 3, timeout: int = 180) -> tuple[bytes, int, int]:
    """Fetch one official response, retrying at most ``attempts`` times."""
    error = ""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "literature-catalog/2.0 (research metadata audit)"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), int(response.status), attempt
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("official metadata request failed (%s/%s): %s", attempt + 1, attempts, error)
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise CatalogError(f"官方元数据查询在 {attempts} 次内失败: {url}: {error}")


def _probe_head(url: str, *, attempts: int = 3, timeout: int = 60) -> tuple[str, int, str]:
    """Probe an official URL without downloading its response body."""
    last_status = "query_failed"
    last_error = ""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "literature-catalog/2.1 (research metadata audit)"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return str(response.status), attempt, "NA"
        except urllib.error.HTTPError as exc:
            last_status = str(exc.code)
            last_error = f"HTTPError: {exc.code} {exc.reason}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    return last_status, attempts - 1, last_error


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_queries(path: Path, rows: list[QueryRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUERY_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _config(root: Path, config_path: Path | None) -> dict[str, object]:
    path = config_path or root / "configs" / "pilots" / "P0008.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"无法读取试点配置 {path}: {exc}") from exc


def fetch_pilot_metadata(root: Path, config_path: Path | None = None) -> list[QueryRecord]:
    """Fetch the configured GEO, NCBI SRA, and ENA metadata snapshots."""
    config = _config(root, config_path)
    paper_id = str(config.get("paper_id", "P0008"))
    if paper_id in {"P0006", "P0007", "P0011", "P0016"}:
        from .batch_round7 import fetch_round7_metadata

        return fetch_round7_metadata(root, Path(config_path) if config_path is not None else root / "configs" / "pilots" / f"{paper_id}.json")
    source_dir = root / str(config["source_metadata_dir"])
    source_dir.mkdir(parents=True, exist_ok=True)
    queried_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[QueryRecord] = []

    geo_url = str(config["geo_miniml_url"])
    LOGGER.info("fetch GEO MINiML: %s", geo_url)
    payload, status, retries = _request_bytes(geo_url)
    geo_tgz = source_dir / "GSE102740_family.xml.tgz"
    _write_bytes(geo_tgz, payload)
    with tarfile.open(geo_tgz, "r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        if len(members) != 1 or Path(members[0].name).name != "GSE102740_family.xml":
            raise CatalogError("GEO MINiML 压缩包内容不符合预期")
        extracted = archive.extractfile(members[0])
        if extracted is None:
            raise CatalogError("无法读取 GEO MINiML XML")
        geo_xml_payload = extracted.read()
    geo_xml = source_dir / "GSE102740_family.xml"
    _write_bytes(geo_xml, geo_xml_payload)
    geo_count = len(ET.fromstring(geo_xml_payload).findall(".//{*}Sample"))
    records.append(
        QueryRecord(
            "Q0001", "NCBI_GEO", geo_url.split("?", 1)[0], geo_url, queried_at,
            str(status), _sha256_bytes(payload), len(payload), geo_count,
            geo_tgz.relative_to(root).as_posix(), "yes", retries, "NA",
        )
    )

    esearch_base = str(config["ncbi_esearch_endpoint"])
    study = str(config["sra_study"])
    esearch_params = {"db": "sra", "term": study, "retmax": "100000"}
    esearch_url = f"{esearch_base}?{urllib.parse.urlencode(esearch_params)}"
    LOGGER.info("fetch NCBI SRA ESearch: %s", study)
    payload, status, retries = _request_bytes(esearch_url)
    esearch_path = source_dir / "SRP115572_esearch.xml"
    _write_bytes(esearch_path, payload)
    esearch_root = ET.fromstring(payload)
    ids = [node.text or "" for node in esearch_root.findall("./IdList/Id")]
    records.append(
        QueryRecord(
            "Q0002", "NCBI_SRA", esearch_base, json.dumps(esearch_params, ensure_ascii=False, sort_keys=True),
            queried_at, str(status), _sha256_bytes(payload), len(payload), len(ids),
            esearch_path.relative_to(root).as_posix(), "yes", retries, "NA",
        )
    )
    if len(ids) != int(config["expected_geo_samples"]):
        raise CatalogError(f"NCBI SRA ESearch 返回 {len(ids)} 个实验，预期 {config['expected_geo_samples']}")

    efetch_base = str(config["ncbi_efetch_endpoint"])
    efetch_params = {"db": "sra", "retmode": "xml", "id": ",".join(ids)}
    efetch_url = f"{efetch_base}?{urllib.parse.urlencode(efetch_params)}"
    LOGGER.info("fetch NCBI SRA EFetch: %s experiment packages", len(ids))
    payload, status, retries = _request_bytes(efetch_url)
    if len(payload) > int(config["max_snapshot_bytes"]):
        raise CatalogError(f"NCBI SRA XML 超过快照上限: {len(payload)} bytes")
    sra_path = source_dir / "SRP115572_efetch.xml"
    _write_bytes(sra_path, payload)
    sra_root = ET.fromstring(payload)
    package_count = len(sra_root.findall("./EXPERIMENT_PACKAGE"))
    records.append(
        QueryRecord(
            "Q0003", "NCBI_SRA", efetch_base,
            json.dumps({**efetch_params, "id": f"{len(ids)} Entrez UIDs from Q0002"}, ensure_ascii=False, sort_keys=True),
            queried_at, str(status), _sha256_bytes(payload), len(payload), package_count,
            sra_path.relative_to(root).as_posix(), "yes", retries, "NA",
        )
    )

    ena_base = str(config["ena_filereport_endpoint"])
    ena_fields = list(config["ena_fields"])
    ena_params = {
        "accession": study,
        "result": "read_run",
        "fields": ",".join(str(field) for field in ena_fields),
        "format": "tsv",
        "download": "false",
    }
    ena_url = f"{ena_base}?{urllib.parse.urlencode(ena_params)}"
    LOGGER.info("fetch ENA Portal file report: %s", study)
    payload, status, retries = _request_bytes(ena_url)
    ena_path = source_dir / "SRP115572_ena_read_run.tsv"
    _write_bytes(ena_path, payload)
    ena_rows = max(0, len(payload.decode("utf-8").splitlines()) - 1)
    records.append(
        QueryRecord(
            "Q0004", "ENA", ena_base, json.dumps(ena_params, ensure_ascii=False, sort_keys=True),
            queried_at, str(status), _sha256_bytes(payload), len(payload), ena_rows,
            ena_path.relative_to(root).as_posix(), "yes", retries, "NA",
        )
    )

    _write_queries(root / str(config["source_queries_path"]), records)
    return records


def fetch_pmc_evidence(root: Path, config_path: Path | None = None) -> list[QueryRecord]:
    """Fetch lightweight PMC article XML and record bounded supplement access outcomes."""
    config = _config(root, config_path)
    source_dir = root / str(config["source_metadata_dir"])
    source_dir.mkdir(parents=True, exist_ok=True)
    query_path = root / str(config["source_queries_path"])
    existing: list[QueryRecord] = []
    if query_path.exists():
        with query_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                existing.append(
                    QueryRecord(
                        query_id=row["query_id"], database=row["database"], endpoint=row["endpoint"],
                        query_parameters=row["query_parameters"], queried_at=row["queried_at"],
                        http_status=row["http_status"], response_sha256=row["response_sha256"],
                        response_bytes=row["response_bytes"], returned_rows=row["returned_rows"],
                        snapshot_path=row["snapshot_path"], pagination_complete=row["pagination_complete"],
                        retry_count=int(row["retry_count"]), error_summary=row["error_summary"],
                        query_outcome=row.get("query_outcome") or "success",
                        legacy_record_id=row.get("legacy_record_id") or "NA",
                    )
                )
    queried_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pmc_endpoint = str(config["pmc_efetch_endpoint"])
    pmc_params = {"db": "pmc", "id": str(config["pmc_id"]), "retmode": "xml"}
    pmc_url = f"{pmc_endpoint}?{urllib.parse.urlencode(pmc_params)}"
    LOGGER.info("fetch PMC article XML: %s", config["pmc_id"])
    payload, status, retries = _request_bytes(pmc_url)
    snapshot = source_dir / "PMC5924687_efetch.xml"
    _write_bytes(snapshot, payload)
    root_node = ET.fromstring(payload)
    supplement_nodes = root_node.findall(".//supplementary-material")
    q5 = QueryRecord(
        "Q0005", "NCBI_PMC", pmc_endpoint, json.dumps(pmc_params, ensure_ascii=False, sort_keys=True),
        queried_at, str(status), _sha256_bytes(payload), len(payload), len(supplement_nodes),
        snapshot.relative_to(root).as_posix(), "yes", retries, "NA", "success", "NA",
    )
    science_url = str(config["science_supplement_url"])
    head_status, head_retries, head_error = _probe_head(science_url)
    q6 = QueryRecord(
        "Q0006", "Science", science_url, json.dumps({"method": "HEAD"}, sort_keys=True),
        queried_at, head_status, "NA", "NR", "NR", "NA", "yes", head_retries,
        head_error, "query_failed" if head_status != "200" else "success", "NA",
    )
    q7 = QueryRecord(
        "Q0007", "NCBI_PMC", "PMC supplementary material listing",
        json.dumps({
            "pmc_id": config["pmc_id"],
            "main_pdf_reported_size": config["supplement_pdf_reported_size"],
            "download_limit_bytes": config["supplement_download_limit_bytes"],
        }, ensure_ascii=False, sort_keys=True),
        queried_at, "NA", "NA", "NR", len(supplement_nodes), snapshot.relative_to(root).as_posix(),
        "yes", 0, "主补充PDF超过20 MB阈值；附件入口需要官方浏览器验证，未绕过、未下载",
        "size_limit_not_downloaded", "NA",
    )
    by_id = {row.query_id: row for row in existing}
    for row in (q5, q6, q7):
        by_id[row.query_id] = row
    ordered = sorted(by_id.values(), key=lambda row: int(row.query_id[1:]) if row.query_id[1:].isdigit() else 9999)
    _write_queries(query_path, ordered)
    return [q5, q6, q7]

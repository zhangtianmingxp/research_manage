"""Inventory and validation logic for the literature experiment catalog."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MISSING_VALUES = {"NR", "NA", "NOT_FOUND", "UNRESOLVED", "RESTRICTED"}

ACCESSION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bioproject", re.compile(r"PRJ(?:NA|EB|DB)\d+", re.IGNORECASE)),
    ("sra_study", re.compile(r"[SED]RP\d+", re.IGNORECASE)),
    ("sra_sample", re.compile(r"[SED]RS\d+", re.IGNORECASE)),
    ("sra_experiment", re.compile(r"[SED]RX\d+", re.IGNORECASE)),
    ("sra_run", re.compile(r"[SED]RR\d+", re.IGNORECASE)),
    ("geo_series", re.compile(r"GSE\d+", re.IGNORECASE)),
    ("geo_sample", re.compile(r"GSM\d+", re.IGNORECASE)),
    ("geo_platform", re.compile(r"GPL\d+", re.IGNORECASE)),
    ("biosample", re.compile(r"SAM[NED][A-Z]?\d+", re.IGNORECASE)),
)


class CatalogError(RuntimeError):
    """Raised when catalog inputs or outputs violate a hard constraint."""


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    row_counts: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.errors


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_accession(value: str) -> str | None:
    """Return the accession entity class when the full value matches."""
    candidate = value.strip()
    if candidate in MISSING_VALUES or not candidate:
        return None
    for name, pattern in ACCESSION_PATTERNS:
        if pattern.fullmatch(candidate):
            return name
    return None


def _next_id(existing: Iterable[str], prefix: str) -> int:
    numbers = [int(value[len(prefix) :]) for value in existing if re.fullmatch(fr"{prefix}\d+", value)]
    return max(numbers, default=0) + 1


def _read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def _write_tsv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_schema(root: Path) -> dict[str, Any]:
    path = root / "configs" / "catalog_schema.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"无法读取 catalog schema: {path}: {exc}") from exc


def load_vocab(root: Path) -> dict[str, Any]:
    path = root / "configs" / "controlled_vocab.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"无法读取 controlled vocabulary: {path}: {exc}") from exc


def _filename_hints(filename: str) -> tuple[str, str, str]:
    stem = Path(filename).stem
    match = re.match(r"(?P<year>\d{4})-(?P<journal>[^-]+)-(?P<title>.+)", stem)
    if not match:
        return "NR", "NR", stem
    return match.group("year"), match.group("journal").strip(), match.group("title").strip()


def _pdf_metadata_title(path: Path) -> str:
    try:
        from pypdf import PdfReader

        metadata = PdfReader(path).metadata
        title = str(metadata.title or "").strip() if metadata else ""
        return title if title and len(title) <= 500 else "NR"
    except Exception:
        return "NR"


def build_inventory(root: Path) -> dict[str, int]:
    """Scan research PDFs and write deterministic file/paper inventories."""
    schema = load_schema(root)
    research_dir = root / "文献" / "研究"
    review_dir = root / "文献" / "综述"
    if not research_dir.is_dir():
        raise CatalogError(f"缺少研究论文目录: {research_dir}")

    research_files = sorted(research_dir.glob("*.pdf"), key=lambda item: item.name.casefold())
    review_files = sorted(review_dir.glob("*.pdf"), key=lambda item: item.name.casefold()) if review_dir.is_dir() else []
    expected = schema["expected_counts"]
    if len(research_files) != expected["research_pdf"]:
        raise CatalogError(f"研究 PDF 数量为 {len(research_files)}，预期 {expected['research_pdf']}")
    if len(review_files) != expected["review_pdf"]:
        raise CatalogError(f"综述 PDF 数量为 {len(review_files)}，预期 {expected['review_pdf']}")

    file_spec = schema["tables"]["paper_files"]
    paper_spec = schema["tables"]["papers"]
    file_path = root / file_spec["path"]
    paper_path = root / paper_spec["path"]
    _, old_files = _read_tsv(file_path)
    _, old_papers = _read_tsv(paper_path)
    file_ids_by_path = {row["relative_path"]: row["file_id"] for row in old_files}
    paper_ids_by_hash = {row["sha256"]: row["paper_id"] for row in old_files}
    old_papers_by_id = {row["paper_id"]: row for row in old_papers}

    next_file = _next_id(file_ids_by_path.values(), "F")
    next_paper = _next_id(paper_ids_by_hash.values(), "P")
    raw_records: list[dict[str, Any]] = []
    for index, path in enumerate(research_files, start=1):
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        file_id = file_ids_by_path.get(relative)
        if not file_id:
            file_id = f"F{next_file:04d}"
            next_file += 1
        paper_id = paper_ids_by_hash.get(digest)
        if not paper_id:
            paper_id = f"P{next_paper:04d}"
            paper_ids_by_hash[digest] = paper_id
            next_paper += 1
        year_hint, journal_hint, title_hint = _filename_hints(path.name)
        raw_records.append(
            {
                "file_id": file_id,
                "paper_id": paper_id,
                "relative_path": relative,
                "filename": path.name,
                "file_size_bytes": path.stat().st_size,
                "sha256": digest,
                "pdf_metadata_title": _pdf_metadata_title(path),
                "year_hint": year_hint,
                "journal_hint": journal_hint,
                "title_hint": title_hint,
                "document_role": "research_article",
                "version_relation": "unique",
                "duplicate_group_id": "NA",
                "is_canonical_file": "yes",
                "metadata_evidence": "filename_and_pdf_metadata_unverified",
                "extraction_status": "inventoried",
                "notes": "书目信息尚未逐篇核验",
                "_order": index,
            }
        )

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in raw_records:
        by_hash[record["sha256"]].append(record)
    duplicate_groups = 0
    for records in by_hash.values():
        records.sort(key=lambda row: row["relative_path"].casefold())
        if len(records) <= 1:
            continue
        duplicate_groups += 1
        group_id = f"DUP{duplicate_groups:03d}"
        for position, record in enumerate(records):
            record["version_relation"] = "exact_duplicate"
            record["duplicate_group_id"] = group_id
            record["is_canonical_file"] = "yes" if position == 0 else "no"
            record["notes"] = "SHA-256 完全相同的文件级重复；保留原文件映射"

    raw_records.sort(key=lambda row: row["_order"])
    for record in raw_records:
        record.pop("_order", None)
    _write_tsv(file_path, file_spec["fields"], raw_records)

    canonical_by_paper: dict[str, dict[str, Any]] = {}
    for record in raw_records:
        if record["paper_id"] not in canonical_by_paper or record["is_canonical_file"] == "yes":
            canonical_by_paper[record["paper_id"]] = record

    papers: list[dict[str, Any]] = []
    for paper_id in sorted(canonical_by_paper):
        record = canonical_by_paper[paper_id]
        old = old_papers_by_id.get(paper_id, {})
        row = {
            "paper_id": paper_id,
            "canonical_file_id": record["file_id"],
            "canonical_title": old.get("canonical_title", "NR"),
            "authors": old.get("authors", "NR"),
            "journal": old.get("journal", "NR"),
            "publication_year": old.get("publication_year", "NR"),
            "doi": old.get("doi", "NR"),
            "pmid": old.get("pmid", "NR"),
            "document_type": "research_article",
            "duplicate_group_id": record["duplicate_group_id"],
            "bibliographic_status": old.get("bibliographic_status", "unverified"),
            "data_availability_locator": old.get("data_availability_locator", "NOT_FOUND"),
            "notes": old.get("notes", "仅完成文件级盘点，待逐篇核验"),
        }
        papers.append(row)
    _write_tsv(paper_path, paper_spec["fields"], papers)
    return {
        "research_pdf": len(research_files),
        "review_pdf": len(review_files),
        "canonical_papers": len(papers),
        "exact_duplicate_groups": duplicate_groups,
    }


def _key(row: dict[str, str], fields: list[str]) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in fields)


def validate_catalog(root: Path) -> ValidationReport:
    schema = load_schema(root)
    vocab = load_vocab(root)
    allowed_missing = set(vocab["missing_values"])
    errors: list[str] = []
    warnings: list[str] = []
    all_rows: dict[str, list[dict[str, str]]] = {}
    row_counts: dict[str, int] = {}

    for table_name, spec in schema["tables"].items():
        path = root / spec["path"]
        header, rows = _read_tsv(path)
        if not path.exists():
            errors.append(f"{table_name}: 缺少文件 {spec['path']}")
            continue
        if header != spec["fields"]:
            errors.append(f"{table_name}: 表头与 schema 不一致")
        all_rows[table_name] = rows
        row_counts[table_name] = len(rows)
        seen: set[tuple[str, ...]] = set()
        for row_number, row in enumerate(rows, start=2):
            for field in spec.get("required", []):
                if not row.get(field, "").strip():
                    errors.append(f"{table_name}:{row_number}: 必填字段 {field} 为空")
            key = _key(row, spec["primary_key"])
            if not all(key) or key in seen:
                errors.append(f"{table_name}:{row_number}: 主键为空或重复 {key}")
            seen.add(key)
            for value in row.values():
                if value in MISSING_VALUES and value not in allowed_missing:
                    errors.append(f"{table_name}:{row_number}: 未定义缺失码 {value}")

    for table_name, spec in schema["tables"].items():
        if table_name not in all_rows:
            continue
        for relation in spec.get("foreign_keys", []):
            target_rows = all_rows.get(relation["table"], [])
            target_keys = {_key(row, relation["references"]) for row in target_rows}
            for row_number, row in enumerate(all_rows[table_name], start=2):
                value = _key(row, relation["fields"])
                if relation.get("allow_missing") and all(part in allowed_missing for part in value):
                    continue
                if value not in target_keys:
                    errors.append(f"{table_name}:{row_number}: 外键 {value} 未在 {relation['table']} 中找到")

    files = all_rows.get("paper_files", [])
    research_paths = {path.relative_to(root).as_posix() for path in (root / "文献" / "研究").glob("*.pdf")}
    recorded_paths = {row["relative_path"] for row in files}
    if recorded_paths != research_paths:
        errors.append("paper_files: 与研究 PDF 实际路径集合不一致")
    if any("文献/综述/" in row["relative_path"] for row in files):
        errors.append("paper_files: 综述被错误纳入研究清单")
    if len(files) != schema["expected_counts"]["research_pdf"]:
        errors.append("paper_files: 研究 PDF 行数不等于预期值")

    for row_number, row in enumerate(all_rows.get("accessions", []), start=2):
        accession = row.get("accession", "")
        entity = row.get("entity_type", "")
        accession_class = classify_accession(accession)
        if accession not in allowed_missing and accession_class is None:
            errors.append(f"accessions:{row_number}: accession 格式无法识别 {accession}")
        if accession_class and accession_class != entity:
            errors.append(f"accessions:{row_number}: {accession} 类型应为 {accession_class}，实际为 {entity}")
        if row.get("format_validation_status") == "verified" and accession_class is None:
            errors.append(f"accessions:{row_number}: 未识别编号不能标为格式已验证")

    evidence_ids = {row["evidence_id"] for row in all_rows.get("evidence", [])}
    for table_name in ("experiments", "samples_timepoints", "perturbations", "accessions", "literature_experiment_catalog"):
        for row_number, row in enumerate(all_rows.get(table_name, []), start=2):
            references = [item for item in row.get("evidence_ids", "").split("|") if item]
            if not references:
                errors.append(f"{table_name}:{row_number}: 缺少 evidence_ids")
            for evidence_id in references:
                if evidence_id not in evidence_ids:
                    errors.append(f"{table_name}:{row_number}: 证据 {evidence_id} 不存在")

    if not all_rows.get("literature_experiment_catalog"):
        warnings.append("试点宽表没有数据行")
    return ValidationReport(tuple(errors), tuple(warnings), row_counts)


def summarize_catalog(root: Path) -> dict[str, Any]:
    schema = load_schema(root)
    result: dict[str, Any] = {"tables": {}}
    for table_name, spec in schema["tables"].items():
        _, rows = _read_tsv(root / spec["path"])
        missing = Counter(value for row in rows for value in row.values() if value in MISSING_VALUES)
        result["tables"][table_name] = {"rows": len(rows), "missing_codes": dict(sorted(missing.items()))}
    return result

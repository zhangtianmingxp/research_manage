from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.literature_catalog.catalog import classify_accession, load_schema, validate_catalog


ROOT = Path(__file__).resolve().parents[1]


class AccessionTests(unittest.TestCase):
    def test_accession_classes(self) -> None:
        cases = {
            "GSE102740": "geo_series",
            "PRJNA398543": "bioproject",
            "SRP115572": "sra_study",
            "SRR123456": "sra_run",
            "ERR123456": "sra_run",
            "DRR123456": "sra_run",
        }
        for accession, expected in cases.items():
            with self.subTest(accession=accession):
                self.assertEqual(classify_accession(accession), expected)

    def test_missing_accession_is_not_invented(self) -> None:
        self.assertIsNone(classify_accession("NOT_FOUND"))
        self.assertIsNone(classify_accession("SRR_guess"))


class SchemaTests(unittest.TestCase):
    def test_config_json_is_machine_readable(self) -> None:
        for name in ("catalog_schema.json", "controlled_vocab.json"):
            with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
                self.assertIsInstance(json.load(handle), dict)

    def test_expected_tables_are_defined(self) -> None:
        schema = load_schema(ROOT)
        expected = {
            "paper_files",
            "papers",
            "experiments",
            "samples_timepoints",
            "perturbations",
            "accessions",
            "evidence",
            "unresolved_issues",
            "literature_experiment_catalog",
        }
        self.assertEqual(set(schema["tables"]), expected)


class RepositoryIntegrationTests(unittest.TestCase):
    def test_inventory_counts_and_exact_duplicate(self) -> None:
        import csv

        with (ROOT / "data" / "curated" / "paper_files.tsv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 29)
        duplicates = [row for row in rows if row["version_relation"] == "exact_duplicate"]
        self.assertEqual(len(duplicates), 2)
        self.assertEqual(len({row["sha256"] for row in duplicates}), 1)
        self.assertEqual(len({row["paper_id"] for row in duplicates}), 1)

    def test_full_catalog_validation(self) -> None:
        report = validate_catalog(ROOT)
        self.assertEqual(report.errors, (), "\n".join(report.errors))


if __name__ == "__main__":
    unittest.main()

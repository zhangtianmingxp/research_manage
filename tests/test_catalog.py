from __future__ import annotations

import json
import unittest
import csv
import hashlib
from pathlib import Path

from src.literature_catalog.catalog import classify_accession, load_schema, validate_catalog
from src.literature_catalog.pilot import build_pilot_catalog, parse_ena_runs, parse_geo_miniml, parse_ncbi_sra


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
            "conditions",
            "replicates",
            "batches",
            "samples_timepoints",
            "archive_samples",
            "perturbations",
            "accessions",
            "accession_relations",
            "files",
            "source_queries",
            "evidence",
            "unresolved_issues",
            "literature_experiment_catalog",
        }
        self.assertEqual(set(schema["tables"]), expected)


class OfflineParserTests(unittest.TestCase):
    def test_geo_miniml_parser_preserves_alias_and_relations(self) -> None:
        rows = parse_geo_miniml(ROOT / "tests" / "fixtures" / "geo_miniml_small.xml")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "20200101-5m-R1")
        self.assertEqual(rows[0]["biosample"], "SAMN1")
        self.assertEqual(rows[0]["srx"], "SRX1")

    def test_sra_parser_supports_multiple_runs(self) -> None:
        experiments, runs = parse_ncbi_sra(ROOT / "tests" / "fixtures" / "ncbi_sra_small.xml")
        self.assertEqual(len(experiments), 1)
        self.assertEqual({row["run"] for row in runs}, {"SRR1", "SRR2"})
        self.assertTrue(all(row["sample_alias"] == "GSM1" for row in runs))

    def test_empty_geo_response_is_explicit(self) -> None:
        empty = ROOT / "tests" / "fixtures" / "empty_miniml.xml"
        self.assertEqual(parse_geo_miniml(empty), [])

    def test_ena_parser_is_offline(self) -> None:
        rows = parse_ena_runs(ROOT / "tests" / "fixtures" / "ena_runs_small.tsv")
        self.assertEqual(rows[0]["run_accession"], "SRR1")
        self.assertEqual(len(rows[0]["fastq_ftp"].split(";")), 2)


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

    def test_all_geo_samples_are_disposed_and_species_are_separate(self) -> None:
        with (ROOT / "data" / "interim" / "pilot" / "archive_samples.tsv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 60)
        self.assertEqual(len({row["gsm_accession"] for row in rows}), 60)
        self.assertEqual({row["disposition_status"] for row in rows}, {"mapped"})
        self.assertEqual(sum(row["species_scientific"] == "Gallus gallus" for row in rows), 58)
        self.assertEqual(sum(row["species_scientific"] == "Homo sapiens" for row in rows), 2)
        self.assertTrue(all(row["sample_title_original"] not in {"", "NR"} for row in rows))

    def test_run_relations_and_wide_table_have_no_cartesian_growth(self) -> None:
        def read(name: str) -> list[dict[str, str]]:
            with (ROOT / "data" / "interim" / "pilot" / name).open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle, delimiter="\t"))
        accessions = read("accessions.tsv")
        relations = read("accession_relations.tsv")
        files = read("files.tsv")
        wide = read("literature_experiment_catalog.tsv")
        runs = {
            row["run_accession"] for row in accessions
            if row["entity_type"] == "sra_run" and row["run_accession"] not in {"NR", "NA", "NOT_FOUND", "UNRESOLVED", "RESTRICTED"}
        }
        mapped = [row for row in relations if row["relation_type"] == "experiment_has_run"]
        self.assertEqual(len(runs), 1290)
        self.assertEqual({row["child_accession"] for row in mapped}, runs)
        self.assertEqual(len(files), 2580)
        self.assertEqual(len(wide), len(files))
        self.assertEqual(len({row["catalog_row_id"] for row in wide}), len(wide))
        self.assertEqual(len({row["file_id"] for row in wide}), len(files))

    def test_query_manifest_records_complete_pagination(self) -> None:
        with (ROOT / "data" / "interim" / "pilot" / "source_queries.tsv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["http_status"] == "200" for row in rows))
        self.assertTrue(all(row["pagination_complete"] == "yes" for row in rows))
        self.assertTrue(all(int(row["retry_count"]) <= 2 for row in rows))

    def test_migration_preserves_v1_ids_and_build_is_deterministic(self) -> None:
        expected = {f"ST-P0008-{index:03d}" for index in range(1, 11)}
        path = ROOT / "data" / "interim" / "pilot" / "samples_timepoints.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            before_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertTrue(expected.issubset({row["sample_timepoint_id"] for row in before_rows}))
        wide = ROOT / "data" / "interim" / "pilot" / "literature_experiment_catalog.tsv"
        before = hashlib.sha256(wide.read_bytes()).hexdigest()
        build_pilot_catalog(ROOT)
        after = hashlib.sha256(wide.read_bytes()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

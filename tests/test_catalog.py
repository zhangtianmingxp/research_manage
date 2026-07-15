from __future__ import annotations

import json
import unittest
import csv
import hashlib
from pathlib import Path

from src.literature_catalog.catalog import classify_accession, load_schema, validate_catalog
from src.literature_catalog.pilot import (
    build_pilot_catalog,
    parse_ena_runs,
    parse_geo_miniml,
    parse_ncbi_runinfo,
    parse_ncbi_sra,
    parse_pmc_evidence,
)


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
            "E-MTAB-1948": "arrayexpress",
            "ENCFF001LFU": "encode_file",
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
            "semantic_review",
            "evidence",
            "unresolved_issues",
            "literature_experiment_catalog",
            "literature_experiment_catalog_files",
            "literature_experiment_catalog_runs",
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

    def test_runinfo_parser_is_offline(self) -> None:
        rows = parse_ncbi_runinfo(ROOT / "data" / "interim" / "pilot" / "source_metadata" / "SRP192917_runinfo.csv")
        self.assertEqual(len(rows), 120)
        self.assertEqual(rows[0]["study"], "SRP192917")
        self.assertEqual(rows[0]["sample_alias"][:3], "GSM")

    def test_pmc_parser_reports_only_explicit_statements(self) -> None:
        facts = parse_pmc_evidence(ROOT / "tests" / "fixtures" / "pmc_evidence_small.xml")
        self.assertTrue(facts["time_courses_in_duplicate"])
        self.assertTrue(facts["nocodazole_before_release"])
        self.assertTrue(facts["hela_reported_earlier"])
        self.assertTrue(facts["deeper_sequencing"])
        empty = parse_pmc_evidence(ROOT / "tests" / "fixtures" / "empty_miniml.xml")
        self.assertFalse(any(empty.values()))


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
        p0008 = [row for row in rows if row["archive_sample_id"].startswith("AS-P0008-")]
        p0009 = [row for row in rows if row["archive_sample_id"].startswith("AS-P0009-")]
        p0012 = [row for row in rows if row["archive_sample_id"].startswith("AS-P0012-")]
        p0001 = [row for row in rows if row["archive_sample_id"].startswith("AS-P0001-")]
        self.assertEqual(len(p0008), 60)
        self.assertEqual(len(p0009), 75)
        self.assertEqual(len(p0012), 44)
        self.assertEqual(len(p0001), 13)
        self.assertEqual(len({row["gsm_accession"] for row in rows}), len(rows))
        self.assertEqual({row["disposition_status"] for row in rows}, {"mapped"})
        self.assertEqual(sum(row["species_scientific"] == "Gallus gallus" for row in p0008), 58)
        self.assertEqual(sum(row["species_scientific"] == "Homo sapiens" for row in p0008), 2)
        self.assertEqual({row["species_scientific"] for row in p0009}, {"Mus musculus"})
        self.assertTrue(all(row["sample_title_original"] not in {"", "NR"} for row in rows))

    def test_run_relations_and_wide_table_have_no_cartesian_growth(self) -> None:
        def read(name: str) -> list[dict[str, str]]:
            with (ROOT / "data" / "interim" / "pilot" / name).open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle, delimiter="\t"))
        accessions = read("accessions.tsv")
        relations = read("accession_relations.tsv")
        files = read("files.tsv")
        wide = read("literature_experiment_catalog.tsv")
        file_view = read("literature_experiment_catalog_files.tsv")
        run_view = read("literature_experiment_catalog_runs.tsv")
        runs = {
            row["run_accession"] for row in accessions
            if row["entity_type"] == "sra_run" and row["run_accession"] not in {"NR", "NA", "NOT_FOUND", "UNRESOLVED", "RESTRICTED"}
        }
        mapped = [row for row in relations if row["relation_type"] == "experiment_has_run"]
        p0008_runs = {row["run_accession"] for row in accessions if row["accession_record_id"].startswith("AC-P0008") and row["entity_type"] == "sra_run"}
        p0009_runs = {row["run_accession"] for row in accessions if row["accession_record_id"].startswith("AC-P0009") and row["entity_type"] == "sra_run"}
        p0012_runs = {row["run_accession"] for row in accessions if row["accession_record_id"].startswith("AC-P0012") and row["entity_type"] == "sra_run"}
        p0001_runs = {row["run_accession"] for row in accessions if row["accession_record_id"].startswith("AC-P0001") and row["entity_type"] == "sra_run"}
        self.assertEqual(len(p0008_runs), 1290)
        self.assertEqual(len(p0009_runs), 120)
        self.assertEqual(len(p0012_runs), 102)
        self.assertEqual(len(p0001_runs), 13)
        self.assertEqual(runs, p0008_runs | p0009_runs | p0012_runs | p0001_runs)
        self.assertEqual({row["child_accession"] for row in mapped}, runs)
        self.assertEqual(len(files), 2580 + 195 + 182 + 26)
        self.assertEqual(len(wide), len(files))
        self.assertEqual(len({row["catalog_row_id"] for row in wide}), len(wide))
        self.assertEqual(len({row["file_id"] for row in wide}), len(files))
        self.assertEqual(file_view, wide)
        self.assertEqual(len(run_view), 1290 + 120 + 102 + 13)
        self.assertEqual({row["run_accession"] for row in run_view}, runs)
        p0008_run_view = [row for row in run_view if row["paper_id"] == "P0008"]
        p0009_run_view = [row for row in run_view if row["paper_id"] == "P0009"]
        p0012_run_view = [row for row in run_view if row["paper_id"] == "P0012"]
        p0001_run_view = [row for row in run_view if row["paper_id"] == "P0001"]
        self.assertTrue(all(row["file_count"] == "2" for row in p0008_run_view))
        self.assertTrue(all(row["read1_url"] not in {"", "NA"} and row["read2_url"] not in {"", "NA"} for row in p0008_run_view))
        self.assertEqual({row["file_count"] for row in p0009_run_view}, {"1", "2"})
        self.assertTrue(all(row["read1_url"] not in {"", "NA"} for row in p0009_run_view))
        self.assertEqual({row["file_count"] for row in p0012_run_view}, {"1", "2"})
        self.assertTrue(all(row["read1_url"] not in {"", "NA"} for row in p0012_run_view))
        self.assertEqual({row["file_count"] for row in p0001_run_view}, {"2"})

    def test_query_manifest_records_complete_pagination(self) -> None:
        with (ROOT / "data" / "interim" / "pilot" / "source_queries.tsv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        by_id = {row["query_id"]: row for row in rows}
        self.assertGreaterEqual(len(rows), 14)
        self.assertEqual({by_id[f"Q000{i}"]["query_outcome"] for i in range(1, 6)}, {"success"})
        self.assertEqual(by_id["Q0006"]["query_outcome"], "query_failed")
        self.assertEqual(by_id["Q0007"]["query_outcome"], "size_limit_not_downloaded")
        self.assertEqual(by_id["Q0008"]["legacy_record_id"], "AC-P0008-004")
        self.assertIn("Q0009", by_id)
        self.assertIn("Q0010", by_id)
        self.assertIn("Q0011", by_id)
        self.assertEqual(by_id["Q0012"]["returned_rows"], "75")
        self.assertEqual(by_id["Q0013"]["returned_rows"], "120")
        self.assertEqual(by_id["Q0014"]["returned_rows"], "120")
        self.assertTrue(all(int(row["retry_count"]) <= 2 for row in rows if row["retry_count"].isdigit()))

    def test_layered_provenance_and_semantic_review_coverage(self) -> None:
        def read(name: str) -> list[dict[str, str]]:
            with (ROOT / "data" / "interim" / "pilot" / name).open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle, delimiter="\t"))
        samples = read("archive_samples.tsv")
        reviews = read("semantic_review.tsv")
        accessions = read("accessions.tsv")
        hela = [row for row in samples if row["archive_sample_id"].startswith("AS-P0008-") and row["species_scientific"] == "Homo sapiens"]
        self.assertEqual(len(hela), 2)
        self.assertEqual({row["biological_sample_origin_status"] for row in hela}, {"reused_from_prior_study"})
        self.assertEqual({row["analysis_usage_status"] for row in hela}, {"reanalyzed_prior_data"})
        p0008_reviews = [row for row in reviews if row["paper_id"] == "P0008"]
        self.assertEqual(sum(row["record_type"] == "replicate" for row in p0008_reviews), 60)
        self.assertEqual(sum(row["record_type"] == "batch" for row in p0008_reviews), 60)
        self.assertEqual(sum(row["record_type"] == "sra_run" for row in p0008_reviews), 76)
        self.assertNotIn("AC-P0008-004", {row["accession_record_id"] for row in accessions})
        p0009_reviews = [row for row in reviews if row["paper_id"] == "P0009"]
        self.assertEqual(len(p0009_reviews), 5)

    def test_migration_preserves_v1_ids_and_build_is_deterministic(self) -> None:
        expected = {f"ST-P0008-{index:03d}" for index in range(1, 11)}
        path = ROOT / "data" / "interim" / "pilot" / "samples_timepoints.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            before_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertTrue(expected.issubset({row["sample_timepoint_id"] for row in before_rows}))
        views = [
            ROOT / "data" / "interim" / "pilot" / "literature_experiment_catalog.tsv",
            ROOT / "data" / "interim" / "pilot" / "literature_experiment_catalog_files.tsv",
            ROOT / "data" / "interim" / "pilot" / "literature_experiment_catalog_runs.tsv",
        ]
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in views]
        build_pilot_catalog(ROOT)
        after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in views]
        self.assertEqual(before, after)

    def test_batch_readiness_is_machine_readable(self) -> None:
        path = ROOT / "reports" / "schema_v2_batch_readiness.json"
        readiness = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(readiness["status"], "ready_with_documented_gaps")
        self.assertEqual(readiness["run_view_rows"], 1290)
        self.assertEqual(readiness["file_view_rows"], 2580)
        self.assertFalse(readiness["legacy_placeholder_active"])

    def test_p0009_run_level_catalog_exists(self) -> None:
        def read(path: Path) -> list[dict[str, str]]:
            with path.open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle, delimiter="\t"))

        catalog = read(ROOT / "data" / "interim" / "pilot" / "P0009_run_file_catalog.tsv")
        self.assertEqual(len(catalog), 195)
        self.assertEqual({row["paper_id"] for row in catalog}, {"P0009"})
        self.assertEqual(len({row["geo_sample"] for row in catalog}), 75)
        self.assertEqual(len({row["run_accession"] for row in catalog}), 120)
        self.assertIn("SRP192917", {row["study_accession"] for row in catalog})

    def test_round4_project_level_records_are_partitioned(self) -> None:
        def read(path: Path) -> list[dict[str, str]]:
            with path.open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle, delimiter="\t"))

        papers = {row["paper_id"]: row for row in read(ROOT / "data" / "curated" / "papers.tsv")}
        for paper_id in ("P0001", "P0009", "P0012"):
            self.assertEqual(papers[paper_id]["bibliographic_status"], "verified")
            self.assertNotEqual(papers[paper_id]["doi"], "NR")

        accessions = read(ROOT / "data" / "interim" / "pilot" / "accessions.tsv")
        by_paper = {}
        for row in accessions:
            if row["accession_record_id"].startswith("AC-P0001"):
                by_paper.setdefault("P0001", set()).add(row["accession"])
            if row["accession_record_id"].startswith("AC-P0009"):
                by_paper.setdefault("P0009", set()).add(row["accession"])
            if row["accession_record_id"].startswith("AC-P0012"):
                by_paper.setdefault("P0012", set()).add(row["accession"])
        self.assertTrue({"E-MTAB-1948", "ERP004055"}.issubset(by_paper["P0001"]))
        self.assertTrue({"GSE129997", "PRJNA533460", "SRP192917"}.issubset(by_paper["P0009"]))
        self.assertTrue({"GSE168251", "GSE168168", "GSE168176", "PRJNA706679"}.issubset(by_paper["P0012"]))


if __name__ == "__main__":
    unittest.main()

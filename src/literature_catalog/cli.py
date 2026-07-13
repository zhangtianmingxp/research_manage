"""Command-line interface for catalog inventory and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import CatalogError, build_inventory, summarize_catalog, validate_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="研究论文实验目录工具")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="仓库根目录")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inventory", help="扫描 PDF 并生成论文清单")
    subparsers.add_parser("validate", help="验证表头、主外键、证据与 accession")
    subparsers.add_parser("summary", help="输出表行数和缺失码摘要")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "inventory":
            print(json.dumps(build_inventory(root), ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate":
            report = validate_catalog(root)
            payload = {
                "ok": report.ok,
                "errors": list(report.errors),
                "warnings": list(report.warnings),
                "row_counts": report.row_counts,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if report.ok else 1
        print(json.dumps(summarize_catalog(root), ensure_ascii=False, indent=2))
        return 0
    except CatalogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

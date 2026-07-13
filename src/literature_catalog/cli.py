"""Command-line interface for catalog inventory and validation."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .catalog import CatalogError, build_inventory, summarize_catalog, validate_catalog
from .metadata import fetch_pilot_metadata
from .pilot import build_pilot_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="研究论文实验目录工具")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="仓库根目录")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inventory", help="扫描 PDF 并生成论文清单")
    subparsers.add_parser("validate", help="验证表头、主外键、证据与 accession")
    subparsers.add_parser("summary", help="输出表行数和缺失码摘要")
    fetch = subparsers.add_parser("fetch", help="从官方数据库获取轻量元数据快照")
    fetch.add_argument("--config", type=Path, default=None, help="试点配置路径")
    build = subparsers.add_parser("build", help="仅从保存的快照离线生成规范表和宽表")
    build.add_argument("--config", type=Path, default=None, help="试点配置路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )
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
        if args.command == "fetch":
            records = fetch_pilot_metadata(root, args.config)
            print(json.dumps({"queries": len(records), "statuses": [row.http_status for row in records]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "build":
            print(json.dumps(build_pilot_catalog(root, args.config), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(summarize_catalog(root), ensure_ascii=False, indent=2))
        return 0
    except CatalogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

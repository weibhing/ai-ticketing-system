"""Command-line entry point: ``python -m docs_agent [options]``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .agent import DocumentationAgent
from .models import Phase


def configure_logging(report_dir: Path) -> logging.Logger:
    """Configure console + rotating file logging for the agent run."""
    report_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("docs_agent")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(report_dir / "agent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="docs_agent", description="Documentation workflow agent.")
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    parser.add_argument(
        "--target",
        action="append",
        help="File or directory (relative to --root) to include; may be repeated. Default: app",
    )
    parser.add_argument("--apply", action="store_true", help="Write generated docstrings to disk.")
    parser.add_argument("--build-sphinx", action="store_true", help="Also run sphinx-build after scaffolding.")
    parser.add_argument("--force", action="store_true", help="Reprocess files even if unchanged since last run.")
    parser.add_argument("--docs-dir", default=None, help="Sphinx scaffold directory (default: <root>/docs/sphinx).")
    parser.add_argument(
        "--report-dir", default=None, help="Report/manifest/log directory (default: <root>/docs/agent_reports)."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the documentation agent from the command line."""
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    report_dir = Path(args.report_dir).resolve() if args.report_dir else root / "docs" / "agent_reports"
    logger = configure_logging(report_dir)

    agent = DocumentationAgent(
        root=root,
        targets=args.target or ["app"],
        apply_changes=args.apply,
        build_sphinx=args.build_sphinx,
        force=args.force,
        docs_dir=Path(args.docs_dir).resolve() if args.docs_dir else None,
        report_dir=report_dir,
        logger=logger,
    )
    report = agent.run()
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.final_state == Phase.COMPLETED.value else 1


if __name__ == "__main__":
    raise SystemExit(main())

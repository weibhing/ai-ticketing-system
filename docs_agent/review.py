"""Phase 5 — Review and maintenance.

Agent action: persist a manifest of file hashes (used by phase 1 on the
*next* run to decide what changed) and write a human/machine-readable
report of what this run did, for a person to review.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import WorkflowReport


class ReviewReporter:
    """Reads/writes the change manifest and writes run reports."""

    def __init__(self, report_dir: Path, logger: logging.Logger | None = None) -> None:
        self.report_dir = Path(report_dir)
        self.logger = logger or logging.getLogger(__name__)

    def load_manifest(self) -> dict[str, str]:
        """Load the file-hash manifest from the previous run, if any."""
        path = self.report_dir / "manifest.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            self.logger.warning("Could not read manifest (%s); starting fresh", error)
            return {}

    def save_manifest(self, manifest: dict[str, str]) -> None:
        """Persist the current file-hash manifest for the next run."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        path = self.report_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        self.logger.info("Saved manifest with %d file(s) to %s", len(manifest), path)

    def write_report(self, report: WorkflowReport) -> Path:
        """Write the run report as both JSON and Markdown; return the JSON path."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = report.started_at.replace(":", "").replace("-", "").replace(".", "")
        json_path = self.report_dir / f"run-{timestamp}.json"
        json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        md_path = self.report_dir / f"run-{timestamp}.md"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        self.logger.info("Wrote review report to %s and %s", json_path, md_path)
        return json_path

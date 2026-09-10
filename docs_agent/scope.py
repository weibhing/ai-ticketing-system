"""Phase 1 — Scope identification.

Agent action: walk the repository (or explicit targets) and decide which
Python files are in scope for this documentation run, using a file-hash
manifest from the previous run to know what actually changed.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_EXCLUDES = {
    ".venv",
    "venv-py",
    "venv",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "tests",
    "docs",
    "data",
    "node_modules",
    "docs_agent",
}


def hash_file(path: Path) -> str:
    """Return the sha256 hex digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScopeIdentifier:
    """Determines which source files the documentation agent should process."""

    def __init__(
        self,
        root: Path,
        targets: Sequence[str] | None = None,
        excludes: Iterable[str] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.root = Path(root)
        self.targets = list(targets) if targets else None
        self.excludes = set(excludes) if excludes is not None else set(DEFAULT_EXCLUDES)
        self.logger = logger or logging.getLogger(__name__)

    def identify(self) -> list[Path]:
        """Return the sorted list of in-scope ``.py`` files."""
        search_paths = [self.root / target for target in self.targets] if self.targets else [self.root]
        candidates: set[Path] = set()
        for path in search_paths:
            if path.is_file() and path.suffix == ".py":
                candidates.add(path.resolve())
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    if any(part in self.excludes for part in py_file.parts):
                        continue
                    candidates.add(py_file.resolve())
            else:
                self.logger.warning("Scope target does not exist, skipping: %s", path)
        files = sorted(candidates)
        self.logger.info("Scope identification found %d candidate file(s)", len(files))
        return files

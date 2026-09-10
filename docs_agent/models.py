"""Shared data structures for the documentation agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class Phase(str, Enum):
    """States of the documentation workflow state machine."""

    SCOPE_IDENTIFICATION = "scope_identification"
    FILE_LOGIC_ANALYSIS = "file_logic_analysis"
    INLINE_DOCUMENTATION = "inline_documentation"
    SPHINX_GENERATION = "sphinx_generation"
    REVIEW_MAINTENANCE = "review_maintenance"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ArgInfo:
    """A single function/method parameter."""

    name: str
    annotation: str | None
    has_default: bool


@dataclass
class FunctionInfo:
    """Everything the agent needs to know about one function or method."""

    file_path: Path
    qualname: str
    name: str
    lineno: int
    body_lineno: int
    body_col_offset: int
    args: list[ArgInfo]
    returns: str | None
    is_method: bool
    is_async: bool
    is_single_line: bool
    class_name: str | None
    decorators: list[str]
    existing_docstring: str | None
    raises: list[str]


@dataclass
class WorkflowReport:
    """Aggregated results of one documentation agent run."""

    started_at: str
    root: str
    files_in_scope: list[str] = field(default_factory=list)
    files_changed_since_last_run: list[str] = field(default_factory=list)
    files_unchanged_skipped: list[str] = field(default_factory=list)
    functions_analyzed: int = 0
    functions_missing_docs: int = 0
    functions_documented: int = 0
    functions_skipped_single_line: int = 0
    sphinx_scaffold_path: str | None = None
    sphinx_build_success: bool | None = None
    sphinx_build_output: str | None = None
    errors: list[str] = field(default_factory=list)
    final_state: str = ""
    failed_phase: str | None = None

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of this report."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Render this report as a human-readable Markdown document."""
        lines = [
            "# Documentation Agent Report",
            "",
            f"- Started: {self.started_at}",
            f"- Root: {self.root}",
            f"- Final state: {self.final_state}",
        ]
        if self.failed_phase:
            lines.append(f"- Failed phase: {self.failed_phase}")
        lines += [
            "",
            "## Scope",
            f"- Files in scope: {len(self.files_in_scope)}",
            f"- Changed since last run: {len(self.files_changed_since_last_run)}",
            f"- Unchanged (skipped): {len(self.files_unchanged_skipped)}",
            "",
            "## Analysis",
            f"- Functions analyzed: {self.functions_analyzed}",
            f"- Functions missing docs (before run): {self.functions_missing_docs}",
            "",
            "## Inline documentation",
            f"- Functions documented: {self.functions_documented}",
            f"- Skipped (single-line def): {self.functions_skipped_single_line}",
            "",
            "## Sphinx",
            f"- Scaffold path: {self.sphinx_scaffold_path}",
            f"- Build attempted: {self.sphinx_build_success is not None}",
            f"- Build success: {self.sphinx_build_success}",
        ]
        if self.errors:
            lines += ["", "## Errors", *[f"- {error}" for error in self.errors]]
        return "\n".join(lines) + "\n"

"""Documentation agent state machine.

Orchestrates the five workflow phases in order, transitioning through
:class:`docs_agent.models.Phase` states. Each phase catches its own
per-item errors (one bad file/function does not abort the run); only a
structural failure inside a phase moves the whole agent to ``FAILED``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from .analysis import CodeAnalyzer
from .apply import InlineDocApplier
from .docstring_gen import DocstringGenerator, HeuristicDocstringGenerator
from .models import FunctionInfo, Phase, WorkflowReport
from .review import ReviewReporter
from .scope import ScopeIdentifier, hash_file
from .sphinx_gen import SphinxAutomation

DEFAULT_SPHINX_MODULES = ["app.main", "app.api", "app.database", "app.models", "app.ui"]


class DocumentationAgent:
    """Runs the scope -> analysis -> inline docs -> sphinx -> review pipeline."""

    def __init__(
        self,
        root: Path,
        targets: Sequence[str] | None = None,
        *,
        apply_changes: bool = False,
        build_sphinx: bool = False,
        force: bool = False,
        docs_dir: Path | None = None,
        report_dir: Path | None = None,
        sphinx_modules: Sequence[str] | None = None,
        docstring_generator: DocstringGenerator | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.root = Path(root)
        self.targets = list(targets) if targets else None
        self.apply_changes = apply_changes
        self.build_sphinx = build_sphinx
        self.force = force
        self.docs_dir = Path(docs_dir) if docs_dir else self.root / "docs" / "sphinx"
        self.report_dir = Path(report_dir) if report_dir else self.root / "docs" / "agent_reports"
        self.sphinx_modules = list(sphinx_modules) if sphinx_modules else list(DEFAULT_SPHINX_MODULES)
        self.logger = logger or logging.getLogger("docs_agent")
        self.docstring_generator = docstring_generator or HeuristicDocstringGenerator(logger=self.logger)
        self.reporter = ReviewReporter(self.report_dir, logger=self.logger)

        self.report = WorkflowReport(started_at=datetime.now(UTC).isoformat(), root=str(self.root))
        self.state = Phase.SCOPE_IDENTIFICATION

        self._files_to_analyze: list[Path] = []
        self._functions_by_file: dict[Path, list[FunctionInfo]] = {}
        self._new_manifest: dict[str, str] = {}

    def run(self) -> WorkflowReport:
        """Execute all workflow phases in order and return the final report."""
        phases: list[tuple[Phase, "callable"]] = [
            (Phase.SCOPE_IDENTIFICATION, self._run_scope),
            (Phase.FILE_LOGIC_ANALYSIS, self._run_analysis),
            (Phase.INLINE_DOCUMENTATION, self._run_inline_docs),
            (Phase.SPHINX_GENERATION, self._run_sphinx),
            (Phase.REVIEW_MAINTENANCE, self._run_review),
        ]
        for phase, action in phases:
            self.state = phase
            self.logger.info("=== Entering phase: %s ===", phase.value)
            try:
                action()
            except Exception as error:  # noqa: BLE001 - top-level phase guard by design
                self.logger.exception("Phase %s failed with an unrecoverable error", phase.value)
                self.report.errors.append(f"[{phase.value}] unrecoverable: {error}")
                self.state = Phase.FAILED
                self.report.failed_phase = phase.value
                break
        else:
            self.state = Phase.COMPLETED
        self.report.final_state = self.state.value
        self.logger.info("=== Workflow finished with state: %s ===", self.state.value)
        return self.report

    def _run_scope(self) -> None:
        identifier = ScopeIdentifier(self.root, self.targets, logger=self.logger)
        files = identifier.identify()
        if not files:
            raise RuntimeError(f"No Python files found in scope for root={self.root}, targets={self.targets}")

        previous_manifest = self.reporter.load_manifest()
        changed: list[Path] = []
        unchanged: list[Path] = []
        new_manifest: dict[str, str] = {}
        for file_path in files:
            try:
                digest = hash_file(file_path)
            except OSError as error:
                self.report.errors.append(f"Could not hash {file_path}: {error}")
                continue
            new_manifest[str(file_path)] = digest
            if previous_manifest.get(str(file_path)) == digest and not self.force:
                unchanged.append(file_path)
            else:
                changed.append(file_path)

        self._new_manifest = new_manifest
        self.report.files_in_scope = [str(f) for f in files]
        self.report.files_changed_since_last_run = [str(f) for f in changed]
        self.report.files_unchanged_skipped = [str(f) for f in unchanged]
        self._files_to_analyze = files if self.force else changed
        self.logger.info(
            "Scope: %d file(s) total, %d changed, %d unchanged (force=%s)",
            len(files),
            len(changed),
            len(unchanged),
            self.force,
        )

    def _run_analysis(self) -> None:
        analyzer = CodeAnalyzer(logger=self.logger)
        self._functions_by_file = {}
        total = 0
        missing = 0
        for file_path in self._files_to_analyze:
            try:
                functions = analyzer.analyze_file(file_path)
            except (SyntaxError, UnicodeDecodeError, OSError) as error:
                message = f"Analysis failed for {file_path}: {error}"
                self.logger.error(message)
                self.report.errors.append(message)
                continue
            self._functions_by_file[file_path] = functions
            total += len(functions)
            missing += sum(1 for info in functions if info.existing_docstring is None)
        self.report.functions_analyzed = total
        self.report.functions_missing_docs = missing
        self.logger.info(
            "Analysis: %d function(s) across %d file(s), %d missing docstrings",
            total,
            len(self._functions_by_file),
            missing,
        )

    def _run_inline_docs(self) -> None:
        applier = InlineDocApplier(logger=self.logger)
        documented = 0
        skipped_single_line = 0

        for file_path, functions in self._functions_by_file.items():
            generated: dict[int, str] = {}
            for info in functions:
                if info.existing_docstring is not None:
                    continue
                if info.is_single_line:
                    skipped_single_line += 1
                    continue
                try:
                    generated[id(info)] = self.docstring_generator.generate(info)
                except Exception as error:  # noqa: BLE001 - keep phase alive per function
                    message = f"Docstring generation failed for {info.qualname} in {file_path}: {error}"
                    self.logger.error(message)
                    self.report.errors.append(message)

            if not generated:
                continue
            try:
                applied = applier.apply(file_path, functions, generated, apply_changes=self.apply_changes)
            except OSError as error:
                message = f"Could not write docstrings to {file_path}: {error}"
                self.logger.error(message)
                self.report.errors.append(message)
                continue
            documented += applied

        self.report.functions_documented = documented
        self.report.functions_skipped_single_line = skipped_single_line
        self.logger.info(
            "Inline documentation: %d function(s) documented (apply=%s)",
            documented,
            self.apply_changes,
        )

    def _run_sphinx(self) -> None:
        automation = SphinxAutomation(
            self.docs_dir,
            sys_paths=[self.root, self.root / "app"],
            modules=self.sphinx_modules,
            logger=self.logger,
        )
        try:
            automation.ensure_scaffold()
        except OSError as error:
            message = f"Could not write Sphinx scaffold: {error}"
            self.logger.error(message)
            self.report.errors.append(message)
            return
        self.report.sphinx_scaffold_path = str(self.docs_dir)

        if self.build_sphinx:
            success, output = automation.build()
            self.report.sphinx_build_success = success
            self.report.sphinx_build_output = output[-4000:]
            if not success:
                self.report.errors.append("Sphinx build failed; see sphinx_build_output in the report")

    def _run_review(self) -> None:
        self.reporter.save_manifest(self._new_manifest)
        self.reporter.write_report(self.report)

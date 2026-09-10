"""Skill: write_docstrings

Purpose:
    Generate Google-style docstrings for every undocumented function or
    method in scope, and insert them into the source files (or preview
    the change in dry-run mode).

Parameters:
    root (str): Project root directory. Default: ".".
    target (list[str] | None): Repeatable file/dir, relative to root, to
        include. Default: ["app"].
    apply (bool): If True, write changes to disk; otherwise dry-run.
        Default: False.

Output:
    dict:
        success (bool)
        apply (bool)
        documented (int): number of docstrings written (or that would be).
        skipped_single_line (int): one-line ``def f(): ...`` defs skipped.
        files_changed (list[str])
        errors (list[str])

Examples:
    Python::

        from docs_agent.skills import write_docstrings
        result = write_docstrings.run_skill(root=".", target=["app"], apply=True)

    CLI::

        python -m docs_agent.skills run write_docstrings --root . --target app            # dry run
        python -m docs_agent.skills run write_docstrings --root . --target app --apply     # writes files
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..analysis import CodeAnalyzer
from ..apply import InlineDocApplier
from ..docstring_gen import HeuristicDocstringGenerator
from ..scope import ScopeIdentifier

NAME = "write_docstrings"
PURPOSE = "Generate and insert Google-style docstrings for undocumented functions/methods."
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "target": "Repeatable file/dir relative to root to include (default: ['app']).",
    "apply": "If true, write changes to disk; otherwise dry-run (default: False).",
}
OUTPUT = "JSON: {success, apply, documented, skipped_single_line, files_changed: [str], errors: [str]}"
EXAMPLES = [
    "python -m docs_agent.skills run write_docstrings --root . --target app",
    "python -m docs_agent.skills run write_docstrings --root . --target app --apply",
]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--target", action="append", default=None)
    parser.add_argument("--apply", action="store_true")


def run_skill(root: str = ".", target: list[str] | None = None, apply: bool = False) -> dict:
    """Execute the skill and return a JSON-serializable result."""
    logger = logging.getLogger("docs_agent.skills.write_docstrings")
    root_path = Path(root).resolve()
    identifier = ScopeIdentifier(root_path, target or ["app"], logger=logger)
    analyzer = CodeAnalyzer(logger=logger)
    generator = HeuristicDocstringGenerator(logger=logger)
    applier = InlineDocApplier(logger=logger)

    documented = 0
    skipped_single_line = 0
    files_changed: list[str] = []
    errors: list[str] = []

    for file_path in identifier.identify():
        try:
            functions = analyzer.analyze_file(file_path)
        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            errors.append(f"Analysis failed for {file_path}: {error}")
            continue

        generated: dict[int, str] = {}
        for info in functions:
            if info.existing_docstring is not None:
                continue
            if info.is_single_line:
                skipped_single_line += 1
                continue
            try:
                generated[id(info)] = generator.generate(info)
            except Exception as error:  # noqa: BLE001 - keep skill alive per function
                errors.append(f"Docstring generation failed for {info.qualname} in {file_path}: {error}")

        if not generated:
            continue
        try:
            applied = applier.apply(file_path, functions, generated, apply_changes=apply)
        except OSError as error:
            errors.append(f"Could not write docstrings to {file_path}: {error}")
            continue
        if applied:
            documented += applied
            files_changed.append(str(file_path))

    return {
        "success": not errors,
        "apply": apply,
        "documented": documented,
        "skipped_single_line": skipped_single_line,
        "files_changed": files_changed,
        "errors": errors,
    }


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, target=args.target, apply=args.apply)

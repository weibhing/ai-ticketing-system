"""Skill: analyze_source

Purpose:
    Statically parse (``ast``, no code execution) every in-scope Python
    file and extract structured facts about each function/method:
    qualified name, parameters with type hints, return type, decorators,
    raised exceptions, and whether a docstring already exists.

Parameters:
    root (str): Project root directory. Default: ".".
    target (list[str] | None): Repeatable file/dir, relative to root, to
        include. Default: ["app"].

Output:
    dict:
        success (bool)
        files_analyzed (int)
        functions_analyzed (int)
        functions_missing_docs (int)
        functions (list[dict]): one entry per function/method with keys
            file_path, qualname, name, lineno, args, returns, is_method,
            is_async, class_name, decorators, existing_docstring, raises.
        errors (list[str])

Examples:
    Python::

        from docs_agent.skills import analyze_source
        result = analyze_source.run_skill(root=".", target=["app"])

    CLI::

        python -m docs_agent.skills run analyze_source --root . --target app
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import asdict
from pathlib import Path

from ..analysis import CodeAnalyzer
from ..scope import ScopeIdentifier

NAME = "analyze_source"
PURPOSE = (
    "Statically parse in-scope Python files and extract function/method facts "
    "(signatures, types, docstrings, raised exceptions)."
)
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "target": "Repeatable file/dir relative to root to include (default: ['app']).",
}
OUTPUT = (
    "JSON: {success, files_analyzed, functions_analyzed, functions_missing_docs, "
    "functions: [{file_path, qualname, name, args, returns, existing_docstring, raises, ...}], errors}"
)
EXAMPLES = [
    "python -m docs_agent.skills run analyze_source --root . --target app",
]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--target", action="append", default=None)


def run_skill(root: str = ".", target: list[str] | None = None) -> dict:
    """Execute the skill and return a JSON-serializable result."""
    logger = logging.getLogger("docs_agent.skills.analyze_source")
    root_path = Path(root).resolve()
    identifier = ScopeIdentifier(root_path, target or ["app"], logger=logger)
    analyzer = CodeAnalyzer(logger=logger)

    functions: list[dict] = []
    errors: list[str] = []
    files = identifier.identify()
    for file_path in files:
        try:
            infos = analyzer.analyze_file(file_path)
        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            message = f"Analysis failed for {file_path}: {error}"
            logger.error(message)
            errors.append(message)
            continue
        for info in infos:
            payload = asdict(info)
            payload["file_path"] = str(info.file_path)
            functions.append(payload)

    missing = sum(1 for entry in functions if entry["existing_docstring"] is None)
    return {
        "success": not errors,
        "files_analyzed": len(files),
        "functions_analyzed": len(functions),
        "functions_missing_docs": missing,
        "functions": functions,
        "errors": errors,
    }


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, target=args.target)

"""Skill: generate_full_site

Purpose:
    Orchestrator skill that runs the complete documentation workflow in
    one call: identify scope, analyze source, write missing docstrings,
    scaffold + build the Sphinx HTML site, and write a review
    report/manifest. This is the skill an agent should call to produce a
    full documentation site in a single step.

Parameters:
    root (str): Project root directory. Default: ".".
    target (list[str] | None): Repeatable file/dir, relative to root, to
        include. Default: ["app"].
    apply (bool): If True, write generated docstrings to disk.
        Default: False (dry run).
    force (bool): Reprocess files even if unchanged since the last run.
        Default: False.

Output:
    dict: the full ``docs_agent.models.WorkflowReport`` (see that module
    for field descriptions), plus a top-level ``success`` key that is
    True only when the workflow reached ``completed`` *and* the Sphinx
    build succeeded with no errors/warnings.

Examples:
    Python::

        from docs_agent.skills import generate_full_site
        result = generate_full_site.run_skill(root=".", target=["app"], apply=True, force=True)

    CLI::

        python -m docs_agent.skills run generate_full_site --root . --target app --apply --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..agent import DocumentationAgent

NAME = "generate_full_site"
PURPOSE = (
    "Run the complete documentation workflow: identify scope, analyze source, "
    "write missing docstrings, scaffold + build the Sphinx HTML site, and write "
    "a review report/manifest."
)
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "target": "Repeatable file/dir relative to root to include (default: ['app']).",
    "apply": "If true, write generated docstrings to disk (default: False = dry run).",
    "force": "Reprocess files even if unchanged since the last run (default: False).",
}
OUTPUT = "JSON: docs_agent.models.WorkflowReport fields, plus a top-level 'success' bool."
EXAMPLES = [
    "python -m docs_agent.skills run generate_full_site --root . --target app --apply --force",
]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--target", action="append", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")


def run_skill(root: str = ".", target: list[str] | None = None, apply: bool = False, force: bool = False) -> dict:
    """Execute the skill and return a JSON-serializable result."""
    root_path = Path(root).resolve()
    agent = DocumentationAgent(
        root=root_path,
        targets=target or ["app"],
        apply_changes=apply,
        build_sphinx=True,
        force=force,
    )
    report = agent.run()
    result = report.to_dict()
    result["success"] = report.final_state == "completed" and bool(report.sphinx_build_success)
    return result


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, target=args.target, apply=args.apply, force=args.force)

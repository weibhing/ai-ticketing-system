"""Skill: identify_scope

Purpose:
    Determine which Python source files are in scope for documentation by
    walking the given root/targets, excluding non-source directories
    (virtual envs, tests, docs, caches, ...).

Parameters:
    root (str): Project root directory. Default: ".".
    target (list[str] | None): Repeatable file/dir, relative to root, to
        include. Default: ["app"].

Output:
    dict:
        success (bool)
        root (str)
        files (list[str]): absolute paths of in-scope .py files.
        count (int)

Examples:
    Python::

        from docs_agent.skills import identify_scope
        result = identify_scope.run_skill(root=".", target=["app"])

    CLI::

        python -m docs_agent.skills run identify_scope --root . --target app
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..scope import ScopeIdentifier

NAME = "identify_scope"
PURPOSE = "Find the Python source files that documentation should be generated for."
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "target": "Repeatable file/dir relative to root to include (default: ['app']).",
}
OUTPUT = "JSON: {success, root, files: [absolute paths], count}"
EXAMPLES = [
    "python -m docs_agent.skills run identify_scope --root . --target app",
]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--target", action="append", default=None)


def run_skill(root: str = ".", target: list[str] | None = None) -> dict:
    """Execute the skill and return a JSON-serializable result."""
    logger = logging.getLogger("docs_agent.skills.identify_scope")
    root_path = Path(root).resolve()
    try:
        identifier = ScopeIdentifier(root_path, target or ["app"], logger=logger)
        files = identifier.identify()
    except OSError as error:
        logger.error("identify_scope failed: %s", error)
        return {"success": False, "root": str(root_path), "files": [], "count": 0, "error": str(error)}
    return {
        "success": True,
        "root": str(root_path),
        "files": [str(f) for f in files],
        "count": len(files),
    }


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, target=args.target)

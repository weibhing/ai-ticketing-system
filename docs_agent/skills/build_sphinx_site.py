"""Skill: build_sphinx_site

Purpose:
    Scaffold (or refresh) the Sphinx project — ``conf.py`` + ``index.rst``
    wired up with ``autodoc``/``napoleon`` for the given modules — and
    build the HTML documentation site. By default the build treats
    Sphinx warnings as errors (``-W``), so ``success: true`` guarantees
    the build completed with zero errors *and* zero warnings.

Parameters:
    root (str): Project root directory. Default: ".".
    docs_dir (str | None): Sphinx project directory.
        Default: "<root>/docs/sphinx".
    module (list[str] | None): Repeatable dotted module name to document.
        Default: ["app.main", "app.api", "app.database", "app.models", "app.ui"].
    strict (bool): Treat warnings as errors via ``-W``. Default: True.

Output:
    dict:
        success (bool)
        docs_dir (str)
        html_dir (str | None): path to the built site (None on failure).
        build_output (str): combined stdout/stderr from sphinx-build.

Examples:
    Python::

        from docs_agent.skills import build_sphinx_site
        result = build_sphinx_site.run_skill(root=".")

    CLI::

        python -m docs_agent.skills run build_sphinx_site --root .
        python -m docs_agent.skills run build_sphinx_site --root . --module app.api --module app.models
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..sphinx_gen import SphinxAutomation

NAME = "build_sphinx_site"
PURPOSE = (
    "Scaffold (or refresh) the Sphinx project (conf.py/index.rst with autodoc+napoleon) "
    "and build the HTML documentation site, treating warnings as build failures."
)
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "docs_dir": "Sphinx project directory (default: '<root>/docs/sphinx').",
    "module": "Repeatable dotted module name to document (default: app.main, app.api, app.database, app.models, app.ui).",
    "strict": "Treat Sphinx warnings as errors via -W (default: True).",
}
OUTPUT = "JSON: {success, docs_dir, html_dir, build_output}"
EXAMPLES = [
    "python -m docs_agent.skills run build_sphinx_site --root .",
    "python -m docs_agent.skills run build_sphinx_site --root . --module app.api --module app.models",
]

DEFAULT_MODULES = ["app.main", "app.api", "app.database", "app.models", "app.ui"]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--docs-dir", default=None)
    parser.add_argument("--module", action="append", default=None)
    parser.add_argument("--no-strict", action="store_true", help="Allow warnings (do not fail the build on them).")


def run_skill(
    root: str = ".",
    docs_dir: str | None = None,
    module: list[str] | None = None,
    strict: bool = True,
) -> dict:
    """Execute the skill and return a JSON-serializable result."""
    logger = logging.getLogger("docs_agent.skills.build_sphinx_site")
    root_path = Path(root).resolve()
    docs_path = Path(docs_dir).resolve() if docs_dir else root_path / "docs" / "sphinx"

    automation = SphinxAutomation(
        docs_path,
        sys_paths=[root_path, root_path / "app"],
        modules=module or DEFAULT_MODULES,
        logger=logger,
    )
    try:
        automation.ensure_scaffold()
    except OSError as error:
        logger.error("Could not write Sphinx scaffold: %s", error)
        return {"success": False, "docs_dir": str(docs_path), "html_dir": None, "build_output": str(error)}

    success, output = automation.build(strict=strict)
    html_dir = docs_path / "_build" / "html"
    return {
        "success": success,
        "docs_dir": str(docs_path),
        "html_dir": str(html_dir) if success else None,
        "build_output": output[-4000:],
    }


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, docs_dir=args.docs_dir, module=args.module, strict=not args.no_strict)

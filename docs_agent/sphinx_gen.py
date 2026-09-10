"""Phase 4 — Sphinx automation and generation.

Agent action: ensure a Sphinx scaffold exists (``conf.py`` + ``index.rst``
with ``autodoc``/``napoleon`` directives for every in-scope module), then
invoke ``python -m sphinx`` as a subprocess (tool call) to build HTML docs
from the docstrings written in phase 3.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Sequence


class SphinxAutomation:
    """Generates a Sphinx scaffold and (optionally) builds HTML docs from it."""

    def __init__(
        self,
        docs_dir: Path,
        sys_paths: Sequence[Path],
        modules: Sequence[str],
        logger: logging.Logger | None = None,
    ) -> None:
        self.docs_dir = Path(docs_dir)
        self.sys_paths = list(sys_paths)
        self.modules = list(modules)
        self.logger = logger or logging.getLogger(__name__)

    def ensure_scaffold(self) -> None:
        """Create/update ``conf.py`` and ``index.rst`` for the doc site."""
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        conf_path = self.docs_dir / "conf.py"
        if not conf_path.exists():
            conf_path.write_text(self._conf_py(), encoding="utf-8")
            self.logger.info("Created Sphinx config at %s", conf_path)
        index_path = self.docs_dir / "index.rst"
        index_path.write_text(self._index_rst(), encoding="utf-8")
        self.logger.info("Wrote Sphinx index at %s", index_path)

    def build(self, strict: bool = True) -> tuple[bool, str]:
        """Run ``sphinx-build`` and return ``(success, combined_output)``.

        Args:
            strict: if True (default), pass ``-W`` so Sphinx warnings are
                treated as build failures, guaranteeing a "success" result
                means zero errors *and* zero warnings.
        """
        build_dir = self.docs_dir / "_build" / "html"
        command = [sys.executable, "-m", "sphinx", "-b", "html"]
        if strict:
            command.append("-W")
        command += [str(self.docs_dir), str(build_dir)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            self.logger.error("Failed to invoke Sphinx: %s", error)
            return False, str(error)
        combined = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0:
            self.logger.error("Sphinx build failed (exit %d):\n%s", result.returncode, result.stderr[-2000:])
            return False, combined
        self.logger.info("Sphinx build succeeded: %s", build_dir)
        return True, combined

    def _conf_py(self) -> str:
        path_inserts = "\n".join(f"sys.path.insert(0, {str(path)!r})" for path in self.sys_paths)
        return (
            textwrap.dedent(
                """
                import sys

                {path_inserts}

                project = "AI Ticketing System"
                extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
                autodoc_mock_imports: list[str] = []
                html_theme = "alabaster"
                """
            )
            .format(path_inserts=path_inserts)
            .strip()
            + "\n"
        )

    def _index_rst(self) -> str:
        lines = [
            "AI Ticketing System Documentation",
            "==================================",
            "",
            ".. toctree::",
            "   :maxdepth: 2",
            "",
        ]
        for module in self.modules:
            lines.append(module)
            lines.append("-" * len(module))
            lines.append("")
            lines.append(f".. automodule:: {module}")
            lines.append("   :members:")
            lines.append("   :undoc-members:")
            lines.append("")
        return "\n".join(lines) + "\n"

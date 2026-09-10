"""Phase 3b — Inline documentation application.

Agent action: insert the generated docstring text into the source file at
the exact position ``ast`` reported for the first statement of the
function body, then re-parse the result before writing to guard against
producing broken source code.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from .models import FunctionInfo


def _format_docstring_block(text: str, indent: str) -> list[str]:
    body_lines = text.split("\n")
    if len(body_lines) == 1:
        return [f'{indent}"""{body_lines[0]}"""\n']
    block = [f'{indent}"""{body_lines[0]}\n']
    for line in body_lines[1:]:
        block.append(f"{indent}{line}\n" if line else "\n")
    block.append(f'{indent}"""\n')
    return block


class InlineDocApplier:
    """Writes generated docstrings back into their source files."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def apply(
        self,
        file_path: Path,
        functions: list[FunctionInfo],
        generated: dict[int, str],
        apply_changes: bool,
    ) -> int:
        """Insert generated docstrings into ``file_path``.

        Args:
            file_path: source file to modify.
            functions: all functions discovered in this file (used to
                locate insertion points).
            generated: mapping of ``id(function_info)`` to docstring text,
                for functions that need a new docstring.
            apply_changes: if False, compute and validate the change but
                do not write the file (dry run).

        Returns:
            The number of docstrings that were (or would be) applied.

        Raises:
            OSError: if the file cannot be read or written.
        """
        original_source = file_path.read_text(encoding="utf-8")
        lines = original_source.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"

        targets = [
            info
            for info in functions
            if info.existing_docstring is None and not info.is_single_line and id(info) in generated
        ]
        if not targets:
            return 0
        targets.sort(key=lambda info: info.body_lineno, reverse=True)

        for info in targets:
            block = _format_docstring_block(generated[id(info)], " " * info.body_col_offset)
            insert_at = info.body_lineno - 1
            lines[insert_at:insert_at] = block

        new_source = "".join(lines)
        try:
            ast.parse(new_source, filename=str(file_path))
        except SyntaxError as error:
            self.logger.error("Generated docstrings would break %s (%s); skipping write", file_path, error)
            return 0

        if apply_changes:
            file_path.write_text(new_source, encoding="utf-8")
            self.logger.info("Applied %d docstring(s) to %s", len(targets), file_path)
        else:
            self.logger.info("[dry-run] Would apply %d docstring(s) to %s", len(targets), file_path)
        return len(targets)

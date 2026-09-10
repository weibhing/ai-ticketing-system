"""Phase 2 — File/logic analysis.

Agent action: statically parse each in-scope file with ``ast`` (no code
execution) and extract structured facts about every function/method:
signature, type hints, decorators, raised exceptions, and whether a
docstring already exists.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from .models import ArgInfo, FunctionInfo


def _extract_args(arguments: ast.arguments) -> list[ArgInfo]:
    result: list[ArgInfo] = []
    positional = list(arguments.posonlyargs) + list(arguments.args)
    defaults_offset = len(positional) - len(arguments.defaults)
    for index, arg in enumerate(positional):
        annotation = ast.unparse(arg.annotation) if arg.annotation is not None else None
        result.append(ArgInfo(arg.arg, annotation, index >= defaults_offset))
    if arguments.vararg is not None:
        annotation = ast.unparse(arguments.vararg.annotation) if arguments.vararg.annotation else None
        result.append(ArgInfo(f"*{arguments.vararg.arg}", annotation, False))
    for index, arg in enumerate(arguments.kwonlyargs):
        annotation = ast.unparse(arg.annotation) if arg.annotation is not None else None
        has_default = arguments.kw_defaults[index] is not None
        result.append(ArgInfo(arg.arg, annotation, has_default))
    if arguments.kwarg is not None:
        annotation = ast.unparse(arguments.kwarg.annotation) if arguments.kwarg.annotation else None
        result.append(ArgInfo(f"**{arguments.kwarg.arg}", annotation, False))
    return result


def _extract_raises(node: ast.AST) -> list[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise) or child.exc is None:
            continue
        exc = child.exc
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
            names.add(exc.func.id)
        elif isinstance(exc, ast.Name):
            names.add(exc.id)
        elif isinstance(exc, ast.Attribute):
            names.add(exc.attr)
        else:
            names.add("Exception")
    return sorted(names)


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.functions: list[FunctionInfo] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802 (ast API name)
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._collect(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._collect(node, is_async=True)
        self.generic_visit(node)

    def _collect(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        class_name = self._class_stack[-1] if self._class_stack else None
        qualname = f"{class_name}.{node.name}" if class_name else node.name
        returns = ast.unparse(node.returns) if node.returns is not None else None
        decorators = [ast.unparse(decorator) for decorator in node.decorator_list]
        existing_docstring = ast.get_docstring(node, clean=False)
        body_start = node.body[0]
        self.functions.append(
            FunctionInfo(
                file_path=self.file_path,
                qualname=qualname,
                name=node.name,
                lineno=node.lineno,
                body_lineno=body_start.lineno,
                body_col_offset=body_start.col_offset,
                args=_extract_args(node.args),
                returns=returns,
                is_method=class_name is not None,
                is_async=is_async,
                is_single_line=node.lineno == body_start.lineno,
                class_name=class_name,
                decorators=decorators,
                existing_docstring=existing_docstring,
                raises=_extract_raises(node),
            )
        )


class CodeAnalyzer:
    """Extracts :class:`FunctionInfo` records from Python source files."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def analyze_file(self, file_path: Path) -> list[FunctionInfo]:
        """Parse one file and return facts about every function it defines.

        Raises:
            SyntaxError: if the file cannot be parsed.
            OSError: if the file cannot be read.
        """
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        collector = _FunctionCollector(file_path)
        collector.visit(tree)
        self.logger.debug("Analyzed %s: %d function(s) found", file_path, len(collector.functions))
        return collector.functions

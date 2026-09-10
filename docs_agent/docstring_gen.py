"""Phase 3a — Docstring generation.

This module defines the *agent action* that turns analysis facts into
documentation text. It is intentionally split into two steps so a real
LLM-backed generator can be swapped in later without changing the rest of
the pipeline:

- ``build_prompt`` — the prompt that would be sent to a language model.
- ``generate`` — the tool call that produces the docstring text. The
  default implementation is a deterministic, offline heuristic so the
  agent runs without any external API dependency.
"""

from __future__ import annotations

import logging
from typing import Protocol

from .models import FunctionInfo

_SKIP_ARG_NAMES = {"self", "cls"}


class DocstringGenerator(Protocol):
    """Interface for anything that can produce a docstring body for a function."""

    def build_prompt(self, info: FunctionInfo) -> str:
        """Return the natural-language prompt describing what to document."""
        ...

    def generate(self, info: FunctionInfo) -> str:
        """Return the docstring body text (no surrounding triple quotes)."""
        ...


class HeuristicDocstringGenerator:
    """Deterministic, offline docstring generator.

    Produces Google-style docstrings from static analysis facts alone
    (name, parameters, type hints, return type, raised exceptions).
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def build_prompt(self, info: FunctionInfo) -> str:
        """Build the prompt an LLM-backed implementation would receive."""
        params = ", ".join(
            f"{arg.name}: {arg.annotation or 'Any'}" for arg in info.args if arg.name not in _SKIP_ARG_NAMES
        )
        return (
            "You are a documentation agent. Write a concise Google-style Python "
            "docstring for the function described below. Return only the "
            "docstring body text (no triple quotes, no code).\n"
            f"Function: {info.qualname}\n"
            f"Async: {info.is_async}\n"
            f"Parameters: {params or 'none'}\n"
            f"Return type: {info.returns or 'None'}\n"
            f"Raises: {', '.join(info.raises) or 'none observed'}\n"
            f"Decorators: {', '.join(info.decorators) or 'none'}\n"
        )

    def generate(self, info: FunctionInfo) -> str:
        """Generate a Google-style docstring body for ``info``."""
        self.logger.debug("Docstring prompt for %s:\n%s", info.qualname, self.build_prompt(info))
        lines = [self._summary(info)]

        params = [arg for arg in info.args if arg.name not in _SKIP_ARG_NAMES]
        if params:
            lines.append("")
            lines.append("Args:")
            for arg in params:
                clean_name = arg.name.lstrip("*")
                type_hint = f" ({arg.annotation})" if arg.annotation else ""
                lines.append(f"    {clean_name}{type_hint}: Description of {clean_name}.")

        if info.returns and info.returns != "None":
            lines.append("")
            lines.append("Returns:")
            lines.append(f"    {info.returns}: Description of the return value.")

        if info.raises:
            lines.append("")
            lines.append("Raises:")
            for exc in info.raises:
                lines.append(f"    {exc}: Description of when this is raised.")

        return "\n".join(lines)

    @staticmethod
    def _summary(info: FunctionInfo) -> str:
        words = [word for word in info.name.strip("_").split("_") if word]
        phrase = " ".join(words) if words else info.name
        phrase = (phrase[:1].upper() + phrase[1:]) if phrase else info.name
        if not phrase.endswith("."):
            phrase += "."
        return phrase

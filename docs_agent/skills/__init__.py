"""Agent-usable Sphinx documentation skills.

Each submodule in this package is a standalone, independently callable
**skill** (a documented tool wrapper) that an agent can invoke either:

- programmatically: ``from docs_agent.skills import <name>; <name>.run_skill(**kwargs)``
- via the CLI dispatcher: ``python -m docs_agent.skills run <name> [options]``

Every skill module exposes the same contract so an agent (or a human) can
introspect it without reading source:

- ``NAME``       (str)             — the skill's identifier.
- ``PURPOSE``    (str)             — what the skill does.
- ``PARAMETERS`` (dict[str, str])  — parameter name -> description.
- ``OUTPUT``     (str)             — description of the returned JSON shape.
- ``EXAMPLES``   (list[str])       — example CLI invocations.
- ``run_skill(**kwargs) -> dict``  — the actual tool call.
- ``add_arguments(parser)``        — wires ``run_skill``'s parameters to argparse.
- ``run(args) -> dict``            — thin CLI adapter calling ``run_skill``.

See ``docs_agent/skills/SKILLS.md`` for full documentation and examples of
every skill in this package.
"""

from __future__ import annotations

from . import (
    analyze_source,
    build_sphinx_site,
    generate_full_site,
    generate_html_doc,
    identify_scope,
    write_docstrings,
)

SKILLS = {
    "identify_scope": identify_scope,
    "analyze_source": analyze_source,
    "write_docstrings": write_docstrings,
    "build_sphinx_site": build_sphinx_site,
    "generate_html_doc": generate_html_doc,
    "generate_full_site": generate_full_site,
}


def list_skills() -> list[dict]:
    """Return introspectable metadata for every registered skill.

    Returns:
        list[dict]: one entry per skill with ``name``, ``purpose``,
        ``parameters``, ``output``, and ``examples`` keys.
    """
    return [
        {
            "name": module.NAME,
            "purpose": module.PURPOSE,
            "parameters": module.PARAMETERS,
            "output": module.OUTPUT,
            "examples": module.EXAMPLES,
        }
        for module in SKILLS.values()
    ]

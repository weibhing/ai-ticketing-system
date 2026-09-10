"""CLI dispatcher for agent-usable skills.

Usage:
    python -m docs_agent.skills list
    python -m docs_agent.skills describe <name>
    python -m docs_agent.skills run <name> [skill-specific options]
"""

from __future__ import annotations

import argparse
import json
import sys

from . import SKILLS, list_skills


def _build_run_parser(skill_name: str) -> argparse.ArgumentParser:
    skill = SKILLS[skill_name]
    parser = argparse.ArgumentParser(prog=f"docs_agent.skills run {skill_name}")
    skill.add_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the skills CLI dispatcher."""
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in {"list", "describe", "run"}:
        print("usage: python -m docs_agent.skills [list|describe <name>|run <name> [options]]")
        print(f"available skills: {', '.join(SKILLS)}")
        return 1

    command, rest = argv[0], argv[1:]

    if command == "list":
        print(json.dumps(list_skills(), indent=2))
        return 0

    if command == "describe":
        if not rest or rest[0] not in SKILLS:
            print(f"Unknown skill. Available: {', '.join(SKILLS)}")
            return 1
        skill = SKILLS[rest[0]]
        print(
            json.dumps(
                {
                    "name": skill.NAME,
                    "purpose": skill.PURPOSE,
                    "parameters": skill.PARAMETERS,
                    "output": skill.OUTPUT,
                    "examples": skill.EXAMPLES,
                },
                indent=2,
            )
        )
        return 0

    if command == "run":
        if not rest or rest[0] not in SKILLS:
            print(f"Unknown skill. Available: {', '.join(SKILLS)}")
            return 1
        skill_name, skill_args = rest[0], rest[1:]
        parser = _build_run_parser(skill_name)
        args = parser.parse_args(skill_args)
        result = SKILLS[skill_name].run(args)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("success", True) else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

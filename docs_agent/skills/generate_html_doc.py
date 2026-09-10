"""Skill: generate_html_doc

Purpose:
    Read and understand Python source files (ast-based static analysis;
    no code execution) and write a single, self-contained, dependency-free
    HTML page documenting every module, class, and function it finds:
    signature, parameters (with type hints), return type, and docstring
    (generating a heuristic one on the fly for anything undocumented so
    the output never has empty entries).

Parameters:
    root (str): Project root directory. Default: ".".
    target (list[str] | None): Repeatable file/dir, relative to root, to
        include. Default: ["app"].
    output (str | None): Path to the HTML file to write.
        Default: "<root>/docs/generated/source_documentation.html".

Output:
    dict:
        success (bool)
        output_path (str): absolute path to the written HTML file.
        modules_documented (int)
        classes_documented (int)
        functions_documented (int)

Examples:
    Python::

        from docs_agent.skills import generate_html_doc
        result = generate_html_doc.run_skill(root=".", target=["app"])
        print(result["output_path"])

    CLI::

        python -m docs_agent.skills run generate_html_doc --root . --target app
        python -m docs_agent.skills run generate_html_doc --root . --output docs/generated/api.html
"""

from __future__ import annotations

import argparse
import html as html_lib
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from ..analysis import CodeAnalyzer
from ..docstring_gen import HeuristicDocstringGenerator
from ..models import FunctionInfo
from ..scope import ScopeIdentifier

NAME = "generate_html_doc"
PURPOSE = (
    "Read and analyze Python source files (ast-based; no code execution), and write a "
    "single self-contained HTML page documenting every module, class, and function "
    "(signature, parameters, return type, and docstring)."
)
PARAMETERS = {
    "root": "Project root directory (default: '.').",
    "target": "Repeatable file/dir relative to root to include (default: ['app']).",
    "output": "Path to the HTML file to write (default: 'docs/generated/source_documentation.html').",
}
OUTPUT = "JSON: {success, output_path, modules_documented, classes_documented, functions_documented}"
EXAMPLES = [
    "python -m docs_agent.skills run generate_html_doc --root . --target app",
    "python -m docs_agent.skills run generate_html_doc --root . --output docs/generated/api.html",
]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Wire this skill's parameters onto an argparse parser."""
    parser.add_argument("--root", default=".")
    parser.add_argument("--target", action="append", default=None)
    parser.add_argument("--output", default=None)


def _signature(info: FunctionInfo) -> str:
    params = []
    for arg in info.args:
        text = arg.name
        if arg.annotation:
            text += f": {arg.annotation}"
        if arg.has_default:
            text += " = ..."
        params.append(text)
    prefix = "async def" if info.is_async else "def"
    signature = f"{prefix} {info.name}({', '.join(params)})"
    if info.returns:
        signature += f" -> {info.returns}"
    return signature


def _slug(module_id: str, qualname: str) -> str:
    raw = f"{module_id}--{qualname}"
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in raw)


def _render_function(info: FunctionInfo, generator: HeuristicDocstringGenerator, slug: str) -> str:
    doc = info.existing_docstring or generator.generate(info)
    return (
        f'<div class="function" id="{html_lib.escape(slug)}">'
        f"<h4><code>{html_lib.escape(_signature(info))}</code></h4>"
        f'<pre class="docstring">{html_lib.escape(doc)}</pre>'
        f"</div>"
    )


def _render_index(index_entries: list[dict]) -> str:
    """Render the top-of-page navigable index of every documented function."""
    if not index_entries:
        return ""
    parts = ['<nav class="index"><h2>Index</h2>']
    for module in index_entries:
        parts.append(f'<div class="index-module"><h3>{html_lib.escape(module["module"])}</h3><ul>')
        for entry in module["module_functions"]:
            parts.append(
                f'<li><a href="#{html_lib.escape(entry["slug"])}"><code>{html_lib.escape(entry["qualname"])}</code></a></li>'
            )
        for cls in module["classes"]:
            parts.append(f'<li><strong>class {html_lib.escape(cls["name"])}</strong><ul>')
            for entry in cls["methods"]:
                parts.append(
                    f'<li><a href="#{html_lib.escape(entry["slug"])}"><code>{html_lib.escape(entry["qualname"])}</code></a></li>'
                )
            parts.append("</ul></li>")
        parts.append("</ul></div>")
    parts.append("</nav>")
    return "\n".join(parts)


def _render_page(index_html: str, sections: list[str], counts: dict) -> str:
    generated_at = datetime.now(UTC).isoformat()
    body = "\n".join(sections) if sections else "<p>No documented modules found.</p>"
    summary = (
        f'<p class="summary">'
        f'{counts["modules"]} modules &middot; {counts["classes"]} classes &middot; '
        f'{counts["functions"]} functions</p>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Source Code Documentation</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.5rem; }}
  p.summary {{ color: #555; font-style: italic; }}
  nav.index {{ background: #fafafa; border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem 1rem 1rem; margin: 1.5rem 0 2rem; }}
  nav.index h2 {{ margin-top: 0; }}
  nav.index h3 {{ font-family: monospace; font-size: 0.95rem; background: #f0f0f0; padding: 0.35rem 0.5rem; margin: 0.75rem 0 0.25rem; }}
  nav.index ul {{ list-style: none; padding-left: 1rem; margin: 0.25rem 0; }}
  nav.index li {{ margin: 0.15rem 0; }}
  nav.index a {{ text-decoration: none; color: #1a5490; }}
  nav.index a:hover {{ text-decoration: underline; }}
  section.module {{ margin-top: 2rem; }}
  section.module h2 {{ font-size: 1rem; font-family: monospace; background: #f0f0f0; padding: 0.5rem; }}
  div.class {{ margin-left: 1rem; border-left: 3px solid #6c8ebf; padding-left: 1rem; margin-bottom: 1rem; }}
  div.function {{ margin: 0.75rem 0 1rem 1rem; }}
  div.function:target {{ background: #fff8dc; border-radius: 4px; padding: 0.25rem 0.5rem; }}
  h3 {{ color: #333; }}
  h4 {{ margin-bottom: 0.25rem; }}
  pre.docstring {{ background: #f7f7f7; padding: 0.5rem 0.75rem; border-radius: 4px; white-space: pre-wrap; }}
  footer {{ margin-top: 3rem; color: #777; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Source Code Documentation</h1>
{summary}
{index_html}
{body}
<footer>Generated by <code>docs_agent.skills.generate_html_doc</code> at {generated_at} following the 5-phase workflow in <code>docs/documentation-workflow.md</code>.</footer>
</body>
</html>
"""


def run_skill(root: str = ".", target: list[str] | None = None, output: str | None = None) -> dict:
    """Execute the skill: analyze source and write one HTML documentation file."""
    logger = logging.getLogger("docs_agent.skills.generate_html_doc")
    root_path = Path(root).resolve()
    output_path = Path(output).resolve() if output else root_path / "docs" / "generated" / "source_documentation.html"

    identifier = ScopeIdentifier(root_path, target or ["app"], logger=logger)
    analyzer = CodeAnalyzer(logger=logger)
    generator = HeuristicDocstringGenerator(logger=logger)

    sections: list[str] = []
    index_entries: list[dict] = []
    modules_documented = 0
    classes_documented = 0
    functions_documented = 0

    for file_path in identifier.identify():
        try:
            functions = analyzer.analyze_file(file_path)
        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            logger.error("Skipping %s: %s", file_path, error)
            continue
        if not functions:
            continue
        modules_documented += 1
        try:
            module_label = str(file_path.relative_to(root_path))
        except ValueError:
            module_label = str(file_path)
        module_id = module_label.replace("\\", "/")

        by_class: dict[str | None, list[FunctionInfo]] = defaultdict(list)
        for info in functions:
            by_class[info.class_name].append(info)

        module_index: dict = {"module": module_id, "module_functions": [], "classes": []}
        module_html = [f'<section class="module"><h2>{html_lib.escape(module_id)}</h2>']
        for info in by_class.get(None, []):
            slug = _slug(module_id, info.qualname)
            module_html.append(_render_function(info, generator, slug))
            module_index["module_functions"].append({"qualname": info.qualname, "slug": slug})
            functions_documented += 1
        for class_name, class_functions in by_class.items():
            if class_name is None:
                continue
            classes_documented += 1
            module_html.append(f'<div class="class"><h3>class {html_lib.escape(class_name)}</h3>')
            class_index: dict = {"name": class_name, "methods": []}
            for info in class_functions:
                slug = _slug(module_id, info.qualname)
                module_html.append(_render_function(info, generator, slug))
                class_index["methods"].append({"qualname": info.qualname, "slug": slug})
                functions_documented += 1
            module_html.append("</div>")
            module_index["classes"].append(class_index)
        module_html.append("</section>")
        sections.append("\n".join(module_html))
        index_entries.append(module_index)

    counts = {"modules": modules_documented, "classes": classes_documented, "functions": functions_documented}
    html_document = _render_page(_render_index(index_entries), sections, counts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_document, encoding="utf-8")
    logger.info("Wrote HTML documentation to %s", output_path)

    return {
        "success": True,
        "output_path": str(output_path),
        "modules_documented": modules_documented,
        "classes_documented": classes_documented,
        "functions_documented": functions_documented,
    }


def run(args: argparse.Namespace) -> dict:
    """CLI entry point: dispatch to :func:`run_skill`."""
    return run_skill(root=args.root, target=args.target, output=args.output)

# Agent-Usable Sphinx Documentation Skills

Reusable, independently callable "skills" (tool wrappers) under
[`docs_agent/skills/`](.) that an agent can invoke to automate Sphinx
documentation generation for this project.

Every skill follows the same contract, so an agent can introspect it
without reading source (see [`__init__.py`](__init__.py)'s `list_skills()`):

- `NAME` (str)
- `PURPOSE` (str)
- `PARAMETERS` (dict[str, str])
- `OUTPUT` (str)
- `EXAMPLES` (list[str])
- `run_skill(**kwargs) -> dict` — the actual tool call, usable from Python.
- `add_arguments(parser)` / `run(args) -> dict` — CLI adapter.

## Invoking skills

```powershell
# Introspect
python -m docs_agent.skills list
python -m docs_agent.skills describe <name>

# Call
python -m docs_agent.skills run <name> [options]
```

Or programmatically:

```python
from docs_agent.skills import generate_html_doc
result = generate_html_doc.run_skill(root=".", target=["app"])
```

## Skill catalog

### `identify_scope`
- **Purpose:** Find the Python source files in scope for documentation
  (walks `root`/`target`, excluding venvs/tests/docs/caches).
- **Parameters:** `root` (str, default `.`), `target` (repeatable str,
  default `["app"]`).
- **Output:** `{success, root, files: [str], count}`
- **Example:**
  ```
  python -m docs_agent.skills run identify_scope --root . --target app
  ```

### `analyze_source`
- **Purpose:** Statically parse (`ast`) in-scope files and extract
  function/method facts: signature, type hints, decorators, raised
  exceptions, existing docstring.
- **Parameters:** `root`, `target` (same as above).
- **Output:** `{success, files_analyzed, functions_analyzed,
  functions_missing_docs, functions: [...], errors}`
- **Example:**
  ```
  python -m docs_agent.skills run analyze_source --root . --target app
  ```

### `write_docstrings`
- **Purpose:** Generate Google-style docstrings for undocumented
  functions/methods and insert them into source (or preview via dry run).
- **Parameters:** `root`, `target`, `apply` (bool, default `False`).
- **Output:** `{success, apply, documented, skipped_single_line,
  files_changed: [str], errors: [str]}`
- **Example:**
  ```
  python -m docs_agent.skills run write_docstrings --root . --target app --apply
  ```

### `build_sphinx_site`
- **Purpose:** Scaffold (`conf.py` + `index.rst` with `autodoc`/`napoleon`)
  and build the Sphinx HTML site. Uses `-W` by default so Sphinx warnings
  are treated as failures — a `success: true` result means the build
  produced **zero errors and zero warnings**.
- **Parameters:** `root`, `docs_dir` (default `<root>/docs/sphinx`),
  `module` (repeatable, default `app.main`, `app.api`, `app.database`,
  `app.models`, `app.ui`), `strict` (bool, default `True`).
- **Output:** `{success, docs_dir, html_dir, build_output}`
- **Example:**
  ```
  python -m docs_agent.skills run build_sphinx_site --root .
  ```

### `generate_html_doc`
- **Purpose:** Read and understand the source (ast-based analysis, no
  code execution) and write a single self-contained HTML file documenting
  every module, class, and function — signature, parameters, return type,
  and docstring (generated on the fly if missing).
- **Parameters:** `root`, `target`, `output` (default
  `<root>/docs/generated/source_documentation.html`).
- **Output:** `{success, output_path, modules_documented,
  classes_documented, functions_documented}`
- **Example:**
  ```
  python -m docs_agent.skills run generate_html_doc --root . --target app
  ```

### `generate_full_site`
- **Purpose:** Orchestrator — runs scope → analysis → docstrings →
  Sphinx build → review report in one call. This is the skill an agent
  should call to produce a full documentation site in a single step.
- **Parameters:** `root`, `target`, `apply` (bool, default `False`),
  `force` (bool, default `False`).
- **Output:** full `docs_agent.models.WorkflowReport` fields plus a
  top-level `success` bool (true only if the workflow completed **and**
  the Sphinx build had no errors/warnings).
- **Example:**
  ```
  python -m docs_agent.skills run generate_full_site --root . --target app --apply --force
  ```

## Verified results (this repository)

- `generate_html_doc` → `docs/generated/source_documentation.html`
  (5 modules, 4 classes, 34 functions documented).
- `build_sphinx_site` (strict) → `build succeeded` with no `WARNING` lines,
  output at `docs/sphinx/_build/html`.
- `generate_full_site` → `final_state: "completed"`,
  `sphinx_build_success: true`, `errors: []`.

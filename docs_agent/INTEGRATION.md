# Documentation Agent — Workflow Integration

How the 5-phase documentation workflow (see
[docs/documentation-workflow.md](../docs/documentation-workflow.md) for the
diagram) is embedded into `docs_agent` as an executable, automated agent.

## Architecture: state machine

`DocumentationAgent` ([agent.py](agent.py)) is a linear state machine over
`Phase` ([models.py](models.py)):

```
SCOPE_IDENTIFICATION -> FILE_LOGIC_ANALYSIS -> INLINE_DOCUMENTATION
  -> SPHINX_GENERATION -> REVIEW_MAINTENANCE -> COMPLETED
                                              \-> FAILED (on any phase's unrecoverable error)
```

`DocumentationAgent.run()` iterates an ordered list of `(Phase, action)`
pairs, sets `self.state` before each phase, executes the phase method, and
accumulates results into a single `WorkflowReport`. If a phase raises, the
agent transitions to `FAILED`, records `failed_phase`, and stops — it never
silently continues past a broken phase.

## Phase → agent action / tool call mapping

| Workflow phase | Agent method | Tool call(s) | Result recorded on `WorkflowReport` |
|---|---|---|---|
| 1. Scope identification | `_run_scope` | `ScopeIdentifier.identify()` (walks `root`/`targets`, applies `DEFAULT_EXCLUDES`); `hash_file()` per file diffed against `docs/agent_reports/manifest.json` | `files_in_scope`, `files_changed_since_last_run`, `files_unchanged_skipped` |
| 2. File/logic analysis | `_run_analysis` | `CodeAnalyzer.analyze_file()` — `ast.parse` + `ast.NodeVisitor` per changed file | `functions_analyzed`, `functions_missing_docs` |
| 3. Inline documentation | `_run_inline_docs` | `HeuristicDocstringGenerator.generate()` per undocumented function, then `InlineDocApplier.apply()` writes docstrings back (guarded by `ast.parse` validation before save) | `functions_documented`, `functions_skipped_single_line` |
| 4. Sphinx automation and generation | `_run_sphinx` | `SphinxAutomation.ensure_scaffold()` (writes `conf.py`/`index.rst`), then `SphinxAutomation.build(strict=True)` (`python -m sphinx -b html -W ...`) | `sphinx_scaffold_path`, `sphinx_build_success`, `sphinx_build_output` |
| 5. Review and maintenance | `_run_review` | `ReviewReporter.save_manifest()` (persists file hashes for the next incremental run), `ReviewReporter.write_report()` (JSON + Markdown run report) | writes `docs/agent_reports/run-*.json` / `.md` |

Phase 3 always executes — and is ordered — before phase 4, so Sphinx never
documents a module before its docstrings exist. This satisfies the
"docstrings before Sphinx" requirement structurally (by list order in
`run()`), not by convention.

## Error handling and logging

- **Per-item isolation**: within a phase (e.g. one file failing `ast.parse`,
  or one function's docstring generation raising), the error is logged and
  appended to `WorkflowReport.errors`, and the loop continues to the next
  item. A single bad file cannot abort the whole run.
- **Phase-level guard**: `run()` wraps each phase call in
  `try/except Exception`; an unrecoverable error inside a phase (e.g. no
  files found at all) moves `state` to `FAILED`, sets `failed_phase`, and
  stops the pipeline — no later phase runs against inconsistent state.
- **Dual logging**: `configure_logging()` ([`__main__.py`](__main__.py))
  attaches a console handler (INFO) and a file handler (DEBUG) writing to
  `docs/agent_reports/agent.log`, so every run has a durable audit trail
  even when only a summary is printed to stdout.
- **Strict Sphinx builds**: `SphinxAutomation.build(strict=True)` passes
  `-W`, so Sphinx warnings are treated as failures rather than being
  silently swallowed — `sphinx_build_success` only reports `True` for a
  genuinely clean build.

## Two integration surfaces

1. **CLI / full pipeline** — `python -m docs_agent --root . --target app
   --apply --build-sphinx --force` runs `DocumentationAgent` directly and
   prints the final `WorkflowReport` as JSON.
2. **Individual skills** — [docs_agent/skills/](skills/) exposes each phase
   (plus a single-file HTML doc generator) as an independently callable,
   documented tool via `python -m docs_agent.skills run <name>` for
   agents/automation that want to call one phase at a time. See
   [skills/SKILLS.md](skills/SKILLS.md).

## Demonstrated test run

```
.\.venv\Scripts\python -m docs_agent --root . --target app --apply --build-sphinx --force
```

Log excerpt (phase order, note `inline_documentation` before
`sphinx_generation`):

```
=== Entering phase: scope_identification ===
Scope: 6 file(s) total, 6 changed, 0 unchanged (force=True)
=== Entering phase: file_logic_analysis ===
Analysis: 34 function(s) across 6 file(s), 0 missing docstrings
=== Entering phase: inline_documentation ===
Inline documentation: 0 function(s) documented (apply=True)
=== Entering phase: sphinx_generation ===
Sphinx build succeeded: .../docs/sphinx/_build/html
=== Entering phase: review_maintenance ===
Saved manifest with 6 file(s) to .../docs/agent_reports/manifest.json
=== Workflow finished with state: completed ===
```

Final report: `final_state: "completed"`, `sphinx_build_success: true`,
`errors: []`. (`functions_documented: 0` here because all 34 functions were
already documented by a prior run — on a fresh/undocumented codebase this
count reflects the docstrings written during phase 3, before phase 4 runs.)

# Documentation Workflow

End-to-end workflow for producing and maintaining code documentation, showing
where the documentation agent acts autonomously versus where a human
developer/reviewer is required.

## Diagram

```mermaid
flowchart TD
    classDef human fill:#fff2cc,stroke:#d6b656,stroke-width:1px,color:#333
    classDef agent fill:#d5e8d4,stroke:#82b366,stroke-width:1px,color:#333
    classDef decision fill:#f8cecc,stroke:#b85450,stroke-width:1px,color:#333
    classDef output fill:#dae8fc,stroke:#6c8ebf,stroke-width:1px,color:#333

    subgraph P1["Phase 1 — Scope Identification"]
        direction TB
        A1["Define target modules / files / APIs"]:::human
        A2["Agent scans repo structure & flags undocumented areas"]:::agent
        A3["Confirm scope & documentation standards"]:::human
        A1 --> A2 --> A3
    end

    subgraph P2["Phase 2 — File / Logic Analysis"]
        direction TB
        B1["Agent parses source files (AST / static analysis)"]:::agent
        B2["Extract functions, classes, params, return types, call graphs"]:::agent
        B3["Detect missing, outdated, or inconsistent docs"]:::agent
        B1 --> B2 --> B3
    end

    subgraph P3["Phase 3 — Inline Documentation Application"]
        direction TB
        C1["Agent drafts docstrings / inline comments"]:::agent
        C2["Developer reviews & edits inline in IDE"]:::human
        C3{"Approved?"}:::decision
        C1 --> C2 --> C3
    end

    subgraph P4["Phase 4 — Sphinx Automation & Generation"]
        direction TB
        D1["Agent / CI triggers sphinx-build"]:::agent
        D2["autodoc extracts docstrings from source"]:::agent
        D3["Generate HTML / PDF documentation site"]:::output
        D1 --> D2 --> D3
    end

    subgraph P5["Phase 5 — Review & Maintenance"]
        direction TB
        E1["Team reviews generated docs"]:::human
        E2["Collect feedback / open issues"]:::human
        E3{"Source code changed?"}:::decision
        E1 --> E2 --> E3
    end

    P1 --> P2
    P2 --> P3
    C3 -- "No, needs rework" --> C1
    C3 -- "Yes" --> P4
    P4 --> P5
    E3 -- "Yes, re-scan needed" --> P2
    E3 -- "No, docs current" --> E1
```

**Legend:** 🟩 green = documentation agent action · 🟨 yellow = human action ·
🟥 red diamond = decision point · 🟦 blue = generated output.

## Phase notes

### 1. Scope identification
- A developer/tech lead defines which modules, files, or public APIs need
  documentation coverage for the current cycle.
- **Agent involvement:** scans the repository structure (e.g. via
  [main.py](../main.py), [api.py](../api.py), [database.py](../database.py),
  [models.py](../models.py), [ui.py](../ui.py)) and flags files or symbols
  that currently lack docstrings, then proposes the scope back to the human
  for confirmation.
- Output: an agreed list of target files/symbols and the documentation style
  to follow (e.g. Google/NumPy docstring format).

### 2. File/logic analysis
- **Agent involvement:** fully agent-driven. The agent statically parses
  each in-scope file, builds an understanding of function signatures, class
  hierarchies, parameter/return types, exceptions raised, and call
  relationships, then diffs this against any existing documentation to find
  gaps or stale descriptions.
- Output: a structured analysis (per-symbol findings) feeding phase 3.

### 3. Inline documentation application
- **Agent involvement:** drafts docstrings/comments directly in the source
  files based on the phase 2 analysis.
- A human developer reviews the proposed inline documentation in the IDE,
  edits for accuracy/tone, and approves or sends it back for rework
  (feedback loop to step C1).
- Output: source files updated with accurate inline documentation.

### 4. Sphinx automation and generation
- **Agent involvement:** triggers the Sphinx build (locally or in CI),
  relying on the `autodoc` extension to pull the docstrings written in
  phase 3 directly from source.
- Output: generated HTML/PDF documentation site, published as a build
  artifact.

### 5. Review and maintenance
- The team reviews the generated documentation site for correctness and
  completeness, and logs feedback or issues.
- A maintenance check determines whether the underlying source code has
  changed since the last cycle; if so, the workflow loops back to phase 2
  (re-analysis) to keep docs in sync, otherwise documentation is considered
  current until the next change.

## Files
- Diagram source (editable): this file — the fenced ` ```mermaid ` block can
  be edited directly and re-rendered by any Mermaid-compatible viewer (VS
  Code Markdown Preview with Mermaid support, mermaid.live, or `mmdc`
  CLI/mermaid-cli to export PNG/PDF).

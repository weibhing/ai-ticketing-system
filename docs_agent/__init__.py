"""Documentation Agent.

Implements the five-phase documentation workflow (see
``docs/documentation-workflow.md``) as an explicit state machine:

1. Scope identification      -> :class:`docs_agent.scope.ScopeIdentifier`
2. File/logic analysis       -> :class:`docs_agent.analysis.CodeAnalyzer`
3. Inline documentation      -> :class:`docs_agent.docstring_gen.HeuristicDocstringGenerator`
                                 + :class:`docs_agent.apply.InlineDocApplier`
4. Sphinx automation         -> :class:`docs_agent.sphinx_gen.SphinxAutomation`
5. Review & maintenance      -> :class:`docs_agent.review.ReviewReporter`

Run with ``python -m docs_agent --help`` from the project root.
"""

from .agent import DocumentationAgent
from .models import Phase, WorkflowReport

__all__ = ["DocumentationAgent", "Phase", "WorkflowReport"]

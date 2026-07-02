"""CloudTrim AI layer — the LLM is a narrator, never authoritative.

explain_finding() renders an architect-voice explanation from engine evidence,
using the LLM when configured and a deterministic template otherwise. Its output
is validated against the engine's numbers on both paths. See docs/BLUEPRINT.md §6.
"""

from ai.config import AIConfig
from ai.explain import explain_finding, make_explainer
from ai.narrative import Narrative, prioritize_analysis
from ai.pr_description import PRDescription, describe_pr
from ai.templates import render_template
from ai.usage import usage
from ai.validation import validate_explanation

__all__ = [
    "AIConfig",
    "Narrative",
    "PRDescription",
    "describe_pr",
    "explain_finding",
    "make_explainer",
    "prioritize_analysis",
    "render_template",
    "usage",
    "validate_explanation",
]

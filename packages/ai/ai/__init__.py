"""CloudTrim AI layer — the LLM is a narrator, never authoritative.

explain_finding() renders an architect-voice explanation from engine evidence,
using LLM when a key is set and a deterministic template otherwise. Its output
is validated against the engine's numbers on both paths. See docs/BLUEPRINT.md §6.
"""

from ai.config import AIConfig
from ai.explain import explain_finding, make_explainer
from ai.narrative import Narrative, prioritize_analysis
from ai.templates import render_template
from ai.validation import validate_explanation

__all__ = [
    "AIConfig",
    "Narrative",
    "explain_finding",
    "make_explainer",
    "prioritize_analysis",
    "render_template",
    "validate_explanation",
]

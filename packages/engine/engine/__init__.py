"""CloudTrim deterministic engine.

The engine is authoritative: parsing, normalization, detection, pricing, risk
scoring, and remediation codegen are 100% deterministic. No LLM lives here.

Submodules (added in Week 1+): parsers, normalizer, detectors, pricing, risk,
remediation. See docs/BLUEPRINT.md §4 and §6.
"""

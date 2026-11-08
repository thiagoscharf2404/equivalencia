"""Stable boundary between application workflow and a future AI provider.

Provider implementations receive normalized, approved evidence and must return
structured suggestions. The coordinator remains the only decision-maker.
"""

import os
import importlib
from typing import Protocol


class EquivalenceAgent(Protocol):
    provider_name: str
    model_name: str

    def analyze(self, context: dict) -> list[dict]:
        """Return suggestions with source_id, target_id, confidence, rationale and evidence."""


def get_agent() -> EquivalenceAgent | None:
    """Resolve a provider only after an implementation is explicitly installed."""
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if provider in ("", "none", "disabled"):
        return None
    adapter_path = os.getenv("AI_AGENT_CLASS", "").strip()
    if not adapter_path or ":" not in adapter_path:
        return None
    module_name, class_name = adapter_path.split(":", 1)
    adapter = getattr(importlib.import_module(module_name), class_name)
    return adapter()

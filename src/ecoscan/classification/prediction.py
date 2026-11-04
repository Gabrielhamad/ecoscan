from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationPrediction:
    """Normalized output produced by the active recognition engine."""

    top_class_id: str
    class_id: str | None
    probability: float
    probabilities: dict[str, float]
    accepted: bool
    threshold: float

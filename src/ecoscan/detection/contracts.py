from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedObject:
    class_id: str
    score: float
    box_xyxy: tuple[int, int, int, int]


class MultipleObjectDetectionNotEnabled(RuntimeError):
    """Raised when a future multi-object feature is called before implementation."""


def detect_multiple_objects(*_: object, **__: object) -> list[DetectedObject]:
    raise MultipleObjectDetectionNotEnabled(
        "Detecção de múltiplos objetos é uma feature futura. "
        "O MVP atual classifica uma imagem com um resíduo principal."
    )


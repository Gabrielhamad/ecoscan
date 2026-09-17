from __future__ import annotations

from dataclasses import dataclass

from ecoscan.config import AppConfig
from ecoscan.services.diagnostics import dataset_status


@dataclass(frozen=True)
class ClassReliability:
    class_id: str
    raw_count: int
    processed_count: int
    target_count: int
    status: str
    message: str

    @property
    def is_sufficient(self) -> bool:
        return self.status == "sufficient"


def assess_class_reliability(
    config: AppConfig,
    class_id: str | None,
    *,
    target_count: int = 50,
) -> ClassReliability | None:
    if not class_id:
        return None

    status = dataset_status(config)
    raw_count = status.raw_counts.get(class_id, 0)
    processed_count = (
        status.train_counts.get(class_id, 0)
        + status.validation_counts.get(class_id, 0)
        + status.test_counts.get(class_id, 0)
    )
    sufficient_minimum = max(1, round(target_count * 0.9))
    warning_minimum = max(1, config.min_images_per_class_warning)

    if processed_count >= sufficient_minimum:
        reliability_status = "sufficient"
        message = "Base processada suficiente para demonstração controlada."
    elif processed_count >= warning_minimum:
        reliability_status = "limited"
        message = "Base processada ainda limitada; trate o resultado como sugestão preliminar."
    else:
        reliability_status = "scarce"
        message = "Poucas imagens processadas nesta classe; use a orientação ambiental, mas não trate a identificação como confiável."

    return ClassReliability(
        class_id=class_id,
        raw_count=raw_count,
        processed_count=processed_count,
        target_count=target_count,
        status=reliability_status,
        message=message,
    )

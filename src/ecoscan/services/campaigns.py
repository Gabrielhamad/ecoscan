from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class Mission:
    id: str
    title: str
    description: str
    points: int
    target_classes: tuple[str, ...]
    verification_action: str
    proof_hint: str


@dataclass(frozen=True)
class Reward:
    id: str
    title: str
    points_required: int
    description: str


@dataclass(frozen=True)
class Campaign:
    title: str
    owner: str
    public_message: str
    weekly_rotation_note: str
    admin_responsibilities: tuple[str, ...]
    missions: tuple[Mission, ...]
    rewards: tuple[Reward, ...]
    strategic_goals: tuple[str, ...] = ()
    operational_routines: tuple[str, ...] = ()
    audience_segments: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissionEvaluation:
    mission_id: str
    status: str
    accepted: bool
    points_awarded: int
    detected_class: str | None
    probability: float | None
    reason: str


class CampaignConfigError(ValueError):
    pass


def campaign_path_from_config(config: AppConfig) -> Path:
    return config.project_root / "config" / "campaigns.json"


def load_campaign(path: str | Path) -> Campaign:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    missions = tuple(_mission_from_payload(row) for row in payload.get("missions", []))
    rewards = tuple(_reward_from_payload(row) for row in payload.get("rewards", []))
    if not missions:
        raise CampaignConfigError("Campaign must define at least one mission.")
    return Campaign(
        title=str(payload.get("title", "")).strip() or "Campanha EcoScan",
        owner=str(payload.get("owner", "")).strip() or "Gestão ambiental",
        public_message=str(payload.get("public_message", "")).strip(),
        weekly_rotation_note=str(payload.get("weekly_rotation_note", "")).strip(),
        admin_responsibilities=tuple(
            str(item).strip()
            for item in payload.get("admin_responsibilities", [])
            if str(item).strip()
        ),
        missions=missions,
        rewards=rewards,
        strategic_goals=_string_tuple(payload.get("strategic_goals", [])),
        operational_routines=_string_tuple(payload.get("operational_routines", [])),
        audience_segments=_string_tuple(payload.get("audience_segments", [])),
    )


def evaluate_mission_submission(mission: Mission, result: Any) -> MissionEvaluation:
    detected_class = result.predicted_class if getattr(result, "accepted", False) else None
    top_class = getattr(result, "top_class", None)
    probability = getattr(result, "probability", None)
    capture_status = _capture_quality_status(result)
    target_classes = set(mission.target_classes)

    if capture_status == "retake":
        return MissionEvaluation(
            mission_id=mission.id,
            status="imagem_insuficiente",
            accepted=False,
            points_awarded=0,
            detected_class=top_class,
            probability=probability,
            reason="A foto precisa ser refeita com melhor iluminação, foco ou enquadramento.",
        )

    if not getattr(result, "accepted", False) or not detected_class:
        return MissionEvaluation(
            mission_id=mission.id,
            status="reconhecimento_inconclusivo",
            accepted=False,
            points_awarded=0,
            detected_class=top_class,
            probability=probability,
            reason="O reconhecimento não teve confiança suficiente para validar a missão.",
        )

    if target_classes and detected_class not in target_classes:
        return MissionEvaluation(
            mission_id=mission.id,
            status="classe_incompativel",
            accepted=False,
            points_awarded=0,
            detected_class=detected_class,
            probability=probability,
            reason="O resíduo reconhecido não pertence ao grupo de materiais desta missão.",
        )

    return MissionEvaluation(
        mission_id=mission.id,
        status="validada",
        accepted=True,
        points_awarded=max(0, int(mission.points)),
        detected_class=detected_class,
        probability=probability,
        reason="Missão validada por tratamento de imagem, segmentação e reconhecimento.",
    )


def _mission_from_payload(payload: dict[str, Any]) -> Mission:
    required = ["id", "title", "description", "points", "target_classes", "verification_action", "proof_hint"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise CampaignConfigError("Mission is missing fields: " + ", ".join(missing))
    return Mission(
        id=str(payload["id"]).strip(),
        title=str(payload["title"]).strip(),
        description=str(payload["description"]).strip(),
        points=int(payload["points"]),
        target_classes=tuple(str(item).strip() for item in payload["target_classes"] if str(item).strip()),
        verification_action=str(payload["verification_action"]).strip(),
        proof_hint=str(payload["proof_hint"]).strip(),
    )


def _reward_from_payload(payload: dict[str, Any]) -> Reward:
    required = ["id", "title", "points_required", "description"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise CampaignConfigError("Reward is missing fields: " + ", ".join(missing))
    return Reward(
        id=str(payload["id"]).strip(),
        title=str(payload["title"]).strip(),
        points_required=int(payload["points_required"]),
        description=str(payload["description"]).strip(),
    )


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _capture_quality_status(result: Any) -> str:
    metadata = getattr(getattr(result, "pipeline", None), "metadata", {})
    if not isinstance(metadata, dict):
        return ""
    capture_quality = metadata.get("capture_quality") or {}
    if not isinstance(capture_quality, dict):
        return ""
    return str(capture_quality.get("status") or "").strip().lower()

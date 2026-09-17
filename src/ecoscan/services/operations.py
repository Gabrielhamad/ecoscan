from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ecoscan.disposal.collection_points import CollectionPoint
from ecoscan.services.accounts import PointTransaction
from ecoscan.services.campaigns import Campaign


RECYCLABLE_DRY_CLASSES = frozenset({"plastic", "paper_cardboard", "metal", "glass"})


@dataclass(frozen=True)
class MissionActivity:
    mission_id: str
    title: str
    status: str
    validations: int
    points_distributed: int
    most_validated_class: str
    target_materials: str


@dataclass(frozen=True)
class PublishedMission:
    mission_id: str
    title: str
    points: int
    verification_action: str
    target_materials: str
    proof_hint: str


@dataclass(frozen=True)
class CampaignOperationsSummary:
    mission_count: int
    possible_points: int
    participant_count: int
    recyclable_point_count: int
    city_counts: tuple[tuple[str, int], ...]
    mission_activity: tuple[MissionActivity, ...]
    published_missions: tuple[PublishedMission, ...]


def format_class_labels(
    class_ids: Iterable[str],
    class_labels: dict[str, str],
    *,
    limit: int = 5,
) -> str:
    ids = tuple(class_id for class_id in class_ids if class_id)
    labels = [class_labels.get(class_id, class_id) for class_id in ids[:limit]]
    if len(ids) > limit:
        labels.append(f"+{len(ids) - limit}")
    return ", ".join(labels)


def build_campaign_operations_summary(
    campaign: Campaign,
    collection_points: Iterable[CollectionPoint],
    point_transactions: Iterable[PointTransaction],
    class_labels: dict[str, str],
) -> CampaignOperationsSummary:
    points = tuple(collection_points)
    transactions = tuple(point_transactions)
    awarded = tuple(transaction for transaction in transactions if transaction.status == "awarded")

    mission_validation_counts = Counter(transaction.mission_id for transaction in awarded)
    mission_points = Counter()
    detected_by_mission: dict[str, Counter[str]] = {}
    for transaction in awarded:
        mission_points[transaction.mission_id] += transaction.points
        if transaction.detected_class:
            detected_by_mission.setdefault(transaction.mission_id, Counter())[transaction.detected_class] += 1

    activity = []
    published = []
    for mission in campaign.missions:
        detected_counter = detected_by_mission.get(mission.id, Counter())
        top_class = detected_counter.most_common(1)[0][0] if detected_counter else ""
        target_materials = format_class_labels(mission.target_classes, class_labels)
        activity.append(
            MissionActivity(
                mission_id=mission.id,
                title=mission.title,
                status="publicada",
                validations=mission_validation_counts.get(mission.id, 0),
                points_distributed=mission_points.get(mission.id, 0),
                most_validated_class=class_labels.get(top_class, top_class),
                target_materials=target_materials,
            )
        )
        published.append(
            PublishedMission(
                mission_id=mission.id,
                title=mission.title,
                points=mission.points,
                verification_action=mission.verification_action,
                target_materials=target_materials,
                proof_hint=mission.proof_hint,
            )
        )

    city_counts = tuple(sorted(Counter(point.city for point in points if point.city).items()))
    recyclable_point_count = sum(
        1 for point in points if RECYCLABLE_DRY_CLASSES.intersection(point.accepted_classes)
    )
    return CampaignOperationsSummary(
        mission_count=len(campaign.missions),
        possible_points=sum(mission.points for mission in campaign.missions),
        participant_count=len({transaction.user_id for transaction in awarded}),
        recyclable_point_count=recyclable_point_count,
        city_counts=city_counts,
        mission_activity=tuple(activity),
        published_missions=tuple(published),
    )


def mission_activity_rows(summary: CampaignOperationsSummary) -> list[dict[str, object]]:
    return [
        {
            "missão": row.title,
            "status": row.status,
            "validações": row.validations,
            "pontos_distribuídos": row.points_distributed,
            "classe_mais_validada": row.most_validated_class,
            "materiais_alvo": row.target_materials,
        }
        for row in summary.mission_activity
    ]


def published_mission_rows(summary: CampaignOperationsSummary) -> list[dict[str, object]]:
    return [
        {
            "missão": row.title,
            "pontos": row.points,
            "verificação": row.verification_action,
            "materiais": row.target_materials,
            "orientação_de_prova": row.proof_hint,
        }
        for row in summary.published_missions
    ]

"""Load immutable UI reference data once and invalidate it when files change."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
from pathlib import Path

from ecoscan.config import AppConfig
from ecoscan.disposal.collection_points import CollectionPoint, load_collection_points
from ecoscan.disposal.guidance import DisposalGuidance, load_guidance
from ecoscan.disposal.impact import EnvironmentalImpact, load_environmental_impacts
from ecoscan.disposal.targets import DisposalTarget, load_disposal_targets
from ecoscan.services.accounts import (
    UserProfile,
    fallback_profiles,
    load_user_profiles,
    profiles_path_from_config,
)
from ecoscan.services.photo_requirements import PhotoRequirement, load_photo_requirements


LOGGER = logging.getLogger(__name__)
REFERENCE_FILES = (
    "disposal_guidance.json",
    "disposal_targets.json",
    "environmental_impacts.json",
    "photo_requirements.json",
    "collection_points.json",
)


@dataclass(frozen=True)
class AppResources:
    guidance_by_class: dict[str, DisposalGuidance]
    targets_by_class: dict[str, DisposalTarget]
    impacts_by_class: dict[str, EnvironmentalImpact]
    requirements_by_class: dict[str, PhotoRequirement]
    collection_points: tuple[CollectionPoint, ...]
    profiles: tuple[UserProfile, ...]


def _file_version(path: Path) -> tuple[str, int, int]:
    try:
        stat = path.stat()
        return str(path), stat.st_mtime_ns, stat.st_size
    except OSError:
        return str(path), -1, -1


def resource_version(config: AppConfig) -> tuple[tuple[str, int, int], ...]:
    config_dir = config.project_root / "config"
    paths = [config_dir / name for name in REFERENCE_FILES]
    paths.append(profiles_path_from_config(config))
    return tuple(_file_version(path) for path in paths)


def load_app_resources(config: AppConfig) -> AppResources:
    return _load_app_resources(str(config.project_root), resource_version(config))


@lru_cache(maxsize=8)
def _load_app_resources(
    project_root: str,
    version: tuple[tuple[str, int, int], ...],
) -> AppResources:
    # ``version`` is intentionally part of the cache key. Reading it here keeps
    # the invariant explicit for maintainers and static analysis.
    del version
    root = Path(project_root)
    config_dir = root / "config"

    def load(label, loader, fallback):
        try:
            return loader()
        except Exception as exc:
            LOGGER.warning("ui_reference_load_failed source=%s type=%s", label, type(exc).__name__)
            return fallback

    points = load(
        "collection_points",
        lambda: tuple(
            point for point in load_collection_points(config_dir / "collection_points.json")
            if point.city == "São Paulo" and point.state == "SP"
        ),
        (),
    )
    profiles = load(
        "user_profiles",
        lambda: load_user_profiles(config_dir / "user_profiles.json"),
        fallback_profiles(),
    )
    return AppResources(
        guidance_by_class=load(
            "disposal_guidance",
            lambda: load_guidance(config_dir / "disposal_guidance.json"),
            {},
        ),
        targets_by_class=load(
            "disposal_targets",
            lambda: load_disposal_targets(config_dir / "disposal_targets.json"),
            {},
        ),
        impacts_by_class=load(
            "environmental_impacts",
            lambda: load_environmental_impacts(config_dir / "environmental_impacts.json"),
            {},
        ),
        requirements_by_class=load(
            "photo_requirements",
            lambda: load_photo_requirements(config_dir / "photo_requirements.json"),
            {},
        ),
        collection_points=points,
        profiles=profiles,
    )

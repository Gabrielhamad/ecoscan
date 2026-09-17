from __future__ import annotations

from dataclasses import asdict, dataclass
from math import hypot
from typing import Iterable

from ecoscan.segmentation.elements import VisualElement


@dataclass(frozen=True)
class TrackedDetection:
    track_id: int
    bbox_xyxy: tuple[int, int, int, int]
    centroid_xy: tuple[float, float]
    area_ratio: float
    age_frames: int

    def to_dict(self) -> dict:
        x1, y1, x2, y2 = self.bbox_xyxy
        data = asdict(self)
        data["bbox"] = {
            "x": x1,
            "y": y1,
            "width": max(0, x2 - x1),
            "height": max(0, y2 - y1),
        }
        return data


@dataclass
class _Track:
    track_id: int
    bbox_xyxy: tuple[int, int, int, int]
    centroid_xy: tuple[float, float]
    area_ratio: float
    age_frames: int = 1
    missed_frames: int = 0

    def update(self, element: VisualElement) -> None:
        self.bbox_xyxy = element.bbox_xyxy
        self.centroid_xy = element.centroid_xy
        self.area_ratio = element.area_ratio
        self.age_frames += 1
        self.missed_frames = 0

    def to_detection(self) -> TrackedDetection:
        return TrackedDetection(
            track_id=self.track_id,
            bbox_xyxy=self.bbox_xyxy,
            centroid_xy=self.centroid_xy,
            area_ratio=self.area_ratio,
            age_frames=self.age_frames,
        )


class CentroidTracker:
    """Small centroid tracker for segmented objects in consecutive frames."""

    def __init__(
        self,
        *,
        max_distance_ratio: float = 0.2,
        max_missed_frames: int = 4,
    ) -> None:
        self.max_distance_ratio = float(max_distance_ratio)
        self.max_missed_frames = int(max_missed_frames)
        self._next_id = 1
        self._tracks: dict[int, _Track] = {}

    def reset(self) -> None:
        self._next_id = 1
        self._tracks.clear()

    def update(
        self,
        elements: Iterable[VisualElement],
        *,
        frame_width: int,
        frame_height: int,
    ) -> list[TrackedDetection]:
        incoming = list(elements)
        max_distance = hypot(frame_width, frame_height) * self.max_distance_ratio
        current_track_ids: set[int] = set()

        matches: list[tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            for index, element in enumerate(incoming):
                distance = hypot(
                    track.centroid_xy[0] - element.centroid_xy[0],
                    track.centroid_xy[1] - element.centroid_xy[1],
                )
                if distance <= max_distance:
                    matches.append((distance, track_id, index))

        matched_tracks: set[int] = set()
        matched_elements: set[int] = set()
        for _, track_id, element_index in sorted(matches, key=lambda item: item[0]):
            if track_id in matched_tracks or element_index in matched_elements:
                continue
            self._tracks[track_id].update(incoming[element_index])
            matched_tracks.add(track_id)
            matched_elements.add(element_index)
            current_track_ids.add(track_id)

        for track_id in list(self._tracks):
            if track_id not in matched_tracks:
                self._tracks[track_id].missed_frames += 1
                if self._tracks[track_id].missed_frames > self.max_missed_frames:
                    del self._tracks[track_id]

        for index, element in enumerate(incoming):
            if index in matched_elements:
                continue
            track_id = self._next_id
            self._next_id += 1
            self._tracks[track_id] = _Track(
                track_id=track_id,
                bbox_xyxy=element.bbox_xyxy,
                centroid_xy=element.centroid_xy,
                area_ratio=element.area_ratio,
            )
            current_track_ids.add(track_id)

        return [
            track.to_detection()
            for track_id, track in sorted(self._tracks.items())
            if track_id in current_track_ids and track.missed_frames == 0
        ]

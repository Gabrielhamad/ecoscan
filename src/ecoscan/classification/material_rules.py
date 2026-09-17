from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.segmentation.elements import ElementAnalysis


COMMON_RECYCLABLES = {"plastic", "paper_cardboard", "metal", "glass"}


@dataclass(frozen=True)
class MaterialCueMetrics:
    foreground_ratio: float
    element_count: int
    significant_count: int
    likely_multi_object: bool
    bbox_aspect: float
    top_width_ratio: float
    bottom_width_ratio: float
    body_continuity_ratio: float
    background_white_ratio: float
    red_ratio: float
    cyan_green_blue_ratio: float
    gray_metal_ratio: float
    top_metal_ratio: float
    bottom_metal_ratio: float
    dark_ratio: float
    colored_ratio: float
    brightness_mean: float
    brightness_std: float
    vertical_edge_ratio: float


@dataclass(frozen=True)
class MaterialRuleDecision:
    class_id: str
    confidence: float
    rule_id: str
    reason: str
    metrics: MaterialCueMetrics


def _safe_mask(mask: np.ndarray) -> np.ndarray:
    binary = np.asarray(mask) > 0
    if binary.ndim != 2 or not np.any(binary):
        return np.ones(binary.shape[:2], dtype=bool)
    return binary


def _foreground_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    y_indexes, x_indexes = np.where(mask)
    if len(x_indexes) == 0:
        height, width = mask.shape[:2]
        return 0, 0, width, height
    return int(x_indexes.min()), int(y_indexes.min()), int(x_indexes.max() + 1), int(y_indexes.max() + 1)


def _mean_row_width_ratio(widths: np.ndarray, start: float, end: float, max_width: float) -> float:
    if widths.size == 0 or max_width <= 0:
        return 0.0
    lower = int(widths.size * start)
    upper = max(lower + 1, int(widths.size * end))
    return float(np.mean(widths[lower:upper]) / max_width)


def _body_shape_metrics(binary_roi: np.ndarray) -> tuple[float, float, float]:
    if binary_roi.size == 0 or not np.any(binary_roi):
        return 0.0, 0.0, 0.0
    widths = np.sum(binary_roi, axis=1).astype(np.float32)
    max_width = float(np.max(widths))
    if max_width <= 0:
        return 0.0, 0.0, 0.0
    top_width_ratio = _mean_row_width_ratio(widths, 0.05, 0.25, max_width)
    bottom_width_ratio = _mean_row_width_ratio(widths, 0.75, 0.95, max_width)
    body_continuity_ratio = float(np.mean(widths >= max_width * 0.45))
    return top_width_ratio, bottom_width_ratio, body_continuity_ratio


def _region_ratio(mask: np.ndarray, start: float, end: float) -> float:
    if mask.size == 0:
        return 0.0
    lower = int(mask.shape[0] * start)
    upper = max(lower + 1, int(mask.shape[0] * end))
    return float(np.mean(mask[lower:upper]))


def extract_material_cues(
    image: np.ndarray,
    mask: np.ndarray,
    element_analysis: ElementAnalysis,
) -> MaterialCueMetrics:
    rgb = np.asarray(image, dtype=np.uint8)
    binary = _safe_mask(mask)
    x1, y1, x2, y2 = _foreground_bbox(binary)
    roi = rgb[y1:y2, x1:x2]
    binary_roi = binary[y1:y2, x1:x2]
    if roi.size == 0:
        roi = rgb
        binary_roi = binary

    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    full_hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    value = hsv[..., 2]
    red = ((hue < 10) | (hue > 170)) & (saturation > 70) & (value > 70)
    cyan_green_blue = (hue >= 35) & (hue <= 135) & (saturation > 35) & (value > 65)
    gray_metal = (saturation < 55) & (value > 75) & (value < 235)
    dark = value < 95
    colored = (saturation > 45) & (value > 60)
    top_width_ratio, bottom_width_ratio, body_continuity_ratio = _body_shape_metrics(binary_roi)

    background = ~binary
    if np.any(background):
        background_white_ratio = float(
            np.mean((full_hsv[..., 1][background] < 35) & (full_hsv[..., 2][background] > 218))
        )
    else:
        background_white_ratio = 0.0

    vertical_edges = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    horizontal_edges = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    vertical_edge_ratio = float(np.mean(np.abs(vertical_edges)) / (np.mean(np.abs(horizontal_edges)) + 1e-6))

    bbox_height, bbox_width = roi.shape[:2]
    return MaterialCueMetrics(
        foreground_ratio=float(np.mean(binary)),
        element_count=int(element_analysis.element_count),
        significant_count=int(element_analysis.significant_count),
        likely_multi_object=bool(element_analysis.likely_multi_object),
        bbox_aspect=float(bbox_width / max(1, bbox_height)),
        top_width_ratio=top_width_ratio,
        bottom_width_ratio=bottom_width_ratio,
        body_continuity_ratio=body_continuity_ratio,
        background_white_ratio=background_white_ratio,
        red_ratio=float(np.mean(red)),
        cyan_green_blue_ratio=float(np.mean(cyan_green_blue)),
        gray_metal_ratio=float(np.mean(gray_metal)),
        top_metal_ratio=_region_ratio(gray_metal, 0.0, 0.22),
        bottom_metal_ratio=_region_ratio(gray_metal, 0.78, 1.0),
        dark_ratio=float(np.mean(dark)),
        colored_ratio=float(np.mean(colored)),
        brightness_mean=float(np.mean(gray)),
        brightness_std=float(np.std(gray)),
        vertical_edge_ratio=vertical_edge_ratio,
    )


def _looks_like_beverage_can(metrics: MaterialCueMetrics, prediction: BaselinePrediction) -> bool:
    if metrics.significant_count > 2:
        return False
    if not 0.18 <= metrics.foreground_ratio <= 0.65:
        return False
    if not 0.45 <= metrics.bbox_aspect <= 1.20:
        return False
    strong_colored_cylinder = metrics.red_ratio >= 0.35 or metrics.colored_ratio >= 0.62
    isolated_product_photo = metrics.background_white_ratio >= 0.45
    weak_or_confused_model = prediction.top_class_id in {"glass", "metal"} and prediction.probability <= 0.42
    metallic_or_cylindrical = metrics.gray_metal_ratio >= 0.025 or metrics.vertical_edge_ratio >= 0.95
    return strong_colored_cylinder and isolated_product_photo and weak_or_confused_model and metallic_or_cylindrical


def _looks_like_dark_beverage_can(metrics: MaterialCueMetrics, prediction: BaselinePrediction) -> bool:
    if metrics.significant_count > 2:
        return False
    if not 0.14 <= metrics.foreground_ratio <= 0.56:
        return False
    if not 0.48 <= metrics.bbox_aspect <= 1.08:
        return False
    if metrics.dark_ratio < 0.20:
        return False
    if metrics.gray_metal_ratio < 0.25:
        return False
    if metrics.vertical_edge_ratio < 1.05:
        return False
    if metrics.brightness_std < 62:
        return False
    if metrics.cyan_green_blue_ratio < 0.045 and metrics.colored_ratio < 0.08:
        return False
    weak_or_confused_model = prediction.top_class_id in {
        "glass",
        "paper_cardboard",
        "plastic",
        "metal",
    }
    return weak_or_confused_model and prediction.probability <= 0.42


def _looks_like_structural_can(metrics: MaterialCueMetrics, prediction: BaselinePrediction) -> bool:
    if metrics.significant_count > 2:
        return False
    if not 0.08 <= metrics.foreground_ratio <= 0.70:
        return False
    if not 0.36 <= metrics.bbox_aspect <= 1.22:
        return False
    if metrics.vertical_edge_ratio < 0.78:
        return False
    if metrics.top_width_ratio < 0.52 or metrics.bottom_width_ratio < 0.52:
        return False
    if metrics.body_continuity_ratio < 0.58:
        return False

    metallic_evidence = (
        metrics.gray_metal_ratio >= 0.22
        and metrics.top_metal_ratio >= 0.12
        and metrics.bottom_metal_ratio >= 0.12
    )
    product_surface_evidence = (
        metrics.colored_ratio >= 0.16
        or metrics.red_ratio >= 0.10
        or metrics.dark_ratio >= 0.12
        or metrics.cyan_green_blue_ratio >= 0.08
    )
    texture_evidence = metrics.brightness_std >= 34
    if not metallic_evidence:
        return False
    if metrics.dark_ratio < 0.035 and metrics.red_ratio < 0.05:
        return False
    if not product_surface_evidence and not texture_evidence:
        return False

    weak_or_confused_model = prediction.top_class_id in {
        "glass",
        "paper_cardboard",
        "plastic",
    }
    return weak_or_confused_model and prediction.probability <= 0.58


def _looks_like_plastic_bottle_group(metrics: MaterialCueMetrics, prediction: BaselinePrediction) -> bool:
    if metrics.cyan_green_blue_ratio < 0.28:
        return False
    if metrics.background_white_ratio < 0.45:
        return False
    if metrics.significant_count < 2 and not metrics.likely_multi_object:
        return False
    if metrics.brightness_mean < 125:
        return False
    if prediction.top_class_id not in {"paper_cardboard", "glass", "plastic"}:
        return False
    return prediction.probability <= 0.45


def _override_prediction(
    prediction: BaselinePrediction,
    decision: MaterialRuleDecision,
) -> BaselinePrediction:
    probabilities = {class_id: float(value) * 0.28 for class_id, value in prediction.probabilities.items()}
    probabilities.setdefault(decision.class_id, 0.0)
    probabilities[decision.class_id] = max(probabilities[decision.class_id], decision.confidence)
    total = sum(probabilities.values()) or 1.0
    normalized = {class_id: value / total for class_id, value in probabilities.items()}
    probability = float(normalized[decision.class_id])
    return BaselinePrediction(
        top_class_id=decision.class_id,
        class_id=decision.class_id,
        probability=probability,
        probabilities=normalized,
        accepted=True,
        threshold=prediction.threshold,
    )


def apply_material_rules(
    prediction: BaselinePrediction,
    *,
    image: np.ndarray,
    mask: np.ndarray,
    element_analysis: ElementAnalysis,
) -> tuple[BaselinePrediction, MaterialRuleDecision | None]:
    metrics = extract_material_cues(image, mask, element_analysis)

    if _looks_like_beverage_can(metrics, prediction):
        decision = MaterialRuleDecision(
            class_id="metal",
            confidence=0.82,
            rule_id="metal_can_shape_color",
            reason="objeto isolado, cilíndrico, colorido, com indícios metálicos e fundo claro",
            metrics=metrics,
        )
        return _override_prediction(prediction, decision), decision

    if _looks_like_dark_beverage_can(metrics, prediction):
        decision = MaterialRuleDecision(
            class_id="metal",
            confidence=0.80,
            rule_id="metal_dark_can_cylinder",
            reason="objeto único e cilíndrico, com bordas verticais, áreas escuras/metálicas e detalhe colorido típico de lata",
            metrics=metrics,
        )
        return _override_prediction(prediction, decision), decision

    if _looks_like_structural_can(metrics, prediction):
        decision = MaterialRuleDecision(
            class_id="metal",
            confidence=0.78,
            rule_id="metal_structural_can_geometry",
            reason=(
                "corpo cilíndrico com largura consistente no topo e na base, continuidade vertical, "
                "bordas laterais e evidência metálica compatíveis com lata"
            ),
            metrics=metrics,
        )
        return _override_prediction(prediction, decision), decision

    if _looks_like_plastic_bottle_group(metrics, prediction):
        decision = MaterialRuleDecision(
            class_id="plastic",
            confidence=0.76,
            rule_id="plastic_bottle_group_translucent",
            reason="múltiplos objetos tipo garrafa, tons verde/azul translúcidos e fundo claro",
            metrics=metrics,
        )
        return _override_prediction(prediction, decision), decision

    return prediction, None

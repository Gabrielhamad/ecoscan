from __future__ import annotations

import unittest

import cv2
import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.classification.material_rules import apply_material_rules
from ecoscan.segmentation.elements import analyze_visual_elements


def _prediction(top_class: str, probability: float) -> BaselinePrediction:
    probabilities = {
        "plastic": 0.12,
        "paper_cardboard": 0.12,
        "metal": 0.12,
        "glass": 0.12,
    }
    probabilities[top_class] = probability
    return BaselinePrediction(
        top_class_id=top_class,
        class_id=top_class,
        probability=probability,
        probabilities=probabilities,
        accepted=True,
        threshold=0.27,
    )


class MaterialRulesTests(unittest.TestCase):
    def test_red_can_overrides_weak_glass_prediction(self) -> None:
        image = np.full((224, 224, 3), 255, dtype=np.uint8)
        cv2.rectangle(image, (72, 48), (152, 184), (210, 26, 26), -1)
        cv2.ellipse(image, (112, 48), (40, 12), 0, 0, 360, (185, 185, 185), -1)
        cv2.ellipse(image, (112, 184), (40, 10), 0, 0, 360, (210, 210, 210), -1)
        mask = np.any(image < 245, axis=2).astype(np.uint8) * 255

        prediction, decision = apply_material_rules(
            _prediction("glass", 0.28),
            image=image,
            mask=mask,
            element_analysis=analyze_visual_elements(mask),
        )

        self.assertIsNotNone(decision)
        self.assertEqual(prediction.top_class_id, "metal")
        self.assertEqual(prediction.class_id, "metal")

    def test_translucent_bottle_group_overrides_weak_paper_prediction(self) -> None:
        image = np.full((224, 224, 3), 255, dtype=np.uint8)
        for index, x in enumerate([25, 65, 105, 145, 180]):
            color = (45, 205 - index * 12, 185 + index * 7)
            cv2.rectangle(image, (x, 62), (x + 24, 196), color, -1)
            cv2.rectangle(image, (x + 7, 28), (x + 17, 68), color, -1)
            cv2.line(image, (x + 3, 90), (x + 22, 84), (245, 255, 255), 3)
        mask = np.any(image < 245, axis=2).astype(np.uint8) * 255

        prediction, decision = apply_material_rules(
            _prediction("paper_cardboard", 0.29),
            image=image,
            mask=mask,
            element_analysis=analyze_visual_elements(mask),
        )

        self.assertIsNotNone(decision)
        self.assertEqual(prediction.top_class_id, "plastic")
        self.assertEqual(prediction.class_id, "plastic")

    def test_dark_energy_drink_can_overrides_weak_glass_prediction(self) -> None:
        image = np.full((224, 224, 3), 214, dtype=np.uint8)
        cv2.rectangle(image, (66, 44), (158, 186), (18, 18, 17), -1)
        cv2.ellipse(image, (112, 44), (46, 10), 0, 0, 360, (190, 190, 186), -1)
        cv2.ellipse(image, (112, 186), (45, 9), 0, 0, 360, (198, 198, 194), -1)
        cv2.line(image, (76, 58), (76, 174), (118, 118, 114), 3)
        cv2.line(image, (149, 58), (149, 174), (105, 105, 101), 3)
        cv2.line(image, (96, 76), (95, 146), (80, 220, 35), 8)
        cv2.line(image, (115, 72), (113, 158), (80, 220, 35), 8)
        cv2.line(image, (133, 78), (130, 145), (80, 220, 35), 8)
        cv2.line(image, (86, 58), (144, 58), (245, 245, 245), 2)
        cv2.line(image, (88, 178), (140, 178), (245, 245, 245), 2)
        mask = np.any(image < 205, axis=2).astype(np.uint8) * 255

        prediction, decision = apply_material_rules(
            _prediction("glass", 0.20),
            image=image,
            mask=mask,
            element_analysis=analyze_visual_elements(mask),
        )

        self.assertIsNotNone(decision)
        self.assertEqual(prediction.top_class_id, "metal")
        self.assertEqual(prediction.class_id, "metal")

    def test_structural_can_geometry_overrides_weak_glass_prediction(self) -> None:
        image = np.full((224, 224, 3), 190, dtype=np.uint8)
        cv2.rectangle(image, (70, 48), (154, 184), (205, 210, 205), -1)
        cv2.ellipse(image, (112, 48), (42, 12), 0, 0, 360, (232, 232, 228), -1)
        cv2.ellipse(image, (112, 184), (42, 10), 0, 0, 360, (180, 185, 180), -1)
        cv2.rectangle(image, (76, 72), (148, 164), (35, 130, 210), -1)
        cv2.line(image, (84, 56), (84, 176), (245, 245, 240), 2)
        cv2.line(image, (144, 56), (144, 176), (118, 118, 116), 2)
        cv2.line(image, (136, 68), (136, 172), (58, 58, 56), 4)
        mask = np.any(np.abs(image.astype(np.int16) - 190) > 18, axis=2).astype(np.uint8) * 255

        prediction, decision = apply_material_rules(
            _prediction("glass", 0.48),
            image=image,
            mask=mask,
            element_analysis=analyze_visual_elements(mask),
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.rule_id, "metal_structural_can_geometry")
        self.assertEqual(prediction.class_id, "metal")

    def test_narrow_neck_bottle_is_not_forced_to_metal(self) -> None:
        image = np.full((224, 224, 3), 240, dtype=np.uint8)
        cv2.rectangle(image, (92, 42), (132, 84), (90, 180, 150), -1)
        cv2.rectangle(image, (72, 82), (154, 188), (70, 190, 170), -1)
        cv2.ellipse(image, (113, 188), (41, 10), 0, 0, 360, (70, 190, 170), -1)
        cv2.line(image, (82, 96), (145, 170), (245, 255, 252), 3)
        mask = np.any(image < 225, axis=2).astype(np.uint8) * 255

        prediction, decision = apply_material_rules(
            _prediction("glass", 0.48),
            image=image,
            mask=mask,
            element_analysis=analyze_visual_elements(mask),
        )

        self.assertIsNone(decision)
        self.assertEqual(prediction.class_id, "glass")


if __name__ == "__main__":
    unittest.main()

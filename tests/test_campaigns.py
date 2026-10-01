from __future__ import annotations

import tempfile
import json
from dataclasses import replace
import unittest
from pathlib import Path
from types import SimpleNamespace

from ecoscan.config import load_config
from ecoscan.services.campaigns import CampaignConfigError, evaluate_mission_submission, load_campaign


class CampaignTests(unittest.TestCase):
    def test_invalid_campaigns_are_rejected(self):
        path = load_config().project_root / "config" / "campaigns.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        cases = []
        for field, value in (("points", -1), ("points", 10001), ("points", True),
                             ("points", 1.5), ("points", "20"), ("id", " "),
                             ("title", None), ("target_classes", "metal"),
                             ("target_classes", []), ("verification_action", "unknown")):
            payload = json.loads(json.dumps(original))
            payload["missions"][0][field] = value
            cases.append(payload)
        duplicate = json.loads(json.dumps(original))
        duplicate["missions"].append(duplicate["missions"][0])
        cases.extend([duplicate, [], {"missions": "invalid"}, {"missions": [None]}])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "campaign.json"
            for payload in cases:
                with self.subTest(payload=payload):
                    target.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(CampaignConfigError):
                        load_campaign(target)

    def test_photo_cannot_validate_complaint_or_unknown_action(self):
        mission = load_campaign(load_config().project_root / "config" / "campaigns.json").missions[0]
        result = SimpleNamespace(accepted=True, predicted_class="metal", probability=0.99)
        for action in ("report_bad_disposal", "unknown"):
            evaluation = evaluate_mission_submission(replace(mission, verification_action=action), result)
            self.assertFalse(evaluation.accepted)
            self.assertEqual(evaluation.points_awarded, 0)
            self.assertEqual(evaluation.status, "revisao_necessaria")

    def test_invalid_confidence_never_awards_points(self):
        mission = load_campaign(load_config().project_root / "config" / "campaigns.json").missions[0]
        for probability in (None, float("nan"), float("inf"), -0.1, 1.1, True, "0.9"):
            with self.subTest(probability=probability):
                result = SimpleNamespace(accepted=True, predicted_class="metal", probability=probability)
                evaluation = evaluate_mission_submission(mission, result)
                self.assertFalse(evaluation.accepted)
                self.assertEqual(evaluation.points_awarded, 0)

    def test_campaign_config_loads_missions_and_rewards(self) -> None:
        config = load_config()
        campaign = load_campaign(config.project_root / "config" / "campaigns.json")

        self.assertGreaterEqual(len(campaign.missions), 4)
        self.assertGreaterEqual(len(campaign.rewards), 2)
        self.assertEqual(campaign.owner, "Secretaria do Meio Ambiente")
        self.assertGreaterEqual(len(campaign.strategic_goals), 3)
        self.assertGreaterEqual(len(campaign.operational_routines), 3)
        self.assertGreaterEqual(len(campaign.audience_segments), 3)

    def test_evaluate_mission_awards_points_for_matching_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "campaigns.json"
            path.write_text(
                """
                {
                  "title": "Teste",
                  "owner": "Secretaria",
                  "missions": [
                    {
                      "id": "metal",
                      "title": "Metal",
                      "description": "Separar metal",
                      "points": 20,
                      "target_classes": ["metal"],
                      "verification_action": "recognize_waste",
                      "proof_hint": "Foto clara"
                    }
                  ],
                  "rewards": []
                }
                """,
                encoding="utf-8",
            )
            mission = load_campaign(path).missions[0]
            result = SimpleNamespace(
                accepted=True,
                predicted_class="metal",
                top_class="metal",
                probability=0.91,
                pipeline=SimpleNamespace(metadata={"capture_quality": {"status": "good"}}),
            )

            evaluation = evaluate_mission_submission(mission, result)

            self.assertTrue(evaluation.accepted)
            self.assertEqual(evaluation.points_awarded, 20)
            self.assertEqual(evaluation.status, "validada")

    def test_evaluate_mission_rejects_incompatible_class(self) -> None:
        config = load_config()
        mission = next(
            mission
            for mission in load_campaign(config.project_root / "config" / "campaigns.json").missions
            if mission.id == "logistica_reversa_segura"
        )
        result = SimpleNamespace(
            accepted=True,
            predicted_class="plastic",
            top_class="plastic",
            probability=0.88,
            pipeline=SimpleNamespace(metadata={"capture_quality": {"status": "good"}}),
        )

        evaluation = evaluate_mission_submission(mission, result)

        self.assertFalse(evaluation.accepted)
        self.assertEqual(evaluation.status, "classe_incompativel")


if __name__ == "__main__":
    unittest.main()

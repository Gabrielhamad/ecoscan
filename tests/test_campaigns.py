from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ecoscan.config import load_config
from ecoscan.services.campaigns import evaluate_mission_submission, load_campaign


class CampaignTests(unittest.TestCase):
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
            if mission.id == "oleo_sem_pia"
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

from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT, load_config
from ecoscan.disposal.collection_points import load_collection_points
from ecoscan.disposal.guidance import load_guidance
from ecoscan.services.accounts import build_point_transaction
from ecoscan.services.campaigns import load_campaign
from ecoscan.services.operations import (
    build_campaign_operations_summary,
    mission_activity_rows,
    published_mission_rows,
)


class OperationsTests(unittest.TestCase):
    def test_campaign_operations_summary_aggregates_secretariat_metrics(self) -> None:
        config = load_config()
        campaign = load_campaign(PROJECT_ROOT / "config" / "campaigns.json")
        collection_points = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")
        guidance = load_guidance(PROJECT_ROOT / "config" / "disposal_guidance.json")
        class_labels = {class_id: row.display_name for class_id, row in guidance.items()}
        metal_mission = next(mission for mission in campaign.missions if mission.id == "lata_metal_segura")
        transactions = [
            build_point_transaction(
                user_id="usuario_demo",
                mission_id=metal_mission.id,
                points=metal_mission.points,
                evidence_sha256="hash-1",
                detected_class="metal",
                probability=0.91,
            ),
            build_point_transaction(
                user_id="usuario_demo",
                mission_id=metal_mission.id,
                points=0,
                evidence_sha256="hash-2",
                detected_class="glass",
                probability=0.41,
                status="rejected",
            ),
        ]

        summary = build_campaign_operations_summary(campaign, collection_points, transactions, class_labels)
        activity_rows = mission_activity_rows(summary)
        published_rows = published_mission_rows(summary)
        metal_row = next(row for row in activity_rows if row["missão"] == metal_mission.title)

        self.assertEqual(len(campaign.missions), summary.mission_count)
        self.assertGreaterEqual(summary.recyclable_point_count, 20)
        self.assertIn(("São Paulo", 17), summary.city_counts)
        self.assertEqual(1, summary.participant_count)
        self.assertEqual(1, metal_row["validações"])
        self.assertEqual(metal_mission.points, metal_row["pontos_distribuídos"])
        self.assertEqual("Metal", metal_row["classe_mais_validada"])
        self.assertEqual(len(campaign.missions), len(published_rows))


if __name__ == "__main__":
    unittest.main()

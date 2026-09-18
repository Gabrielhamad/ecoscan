import copy
import os
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

from tests.test_learning_contributions import LearningTests
from ecoscan.services.contribution_store import SupabaseContributions, settings
from ecoscan.services.learning_contributions import (
    contribution_image, list_contributions, review_contribution,
)


class MemoryRemote:
    def __init__(self):
        self.rows = {}
        self.photos = {}

    def list(self):
        return copy.deepcopy(list(self.rows.values()))

    def save(self, record, *, image=None, previous_revision=None):
        record = copy.deepcopy(record)
        key = record["id"]
        if image is None and self.rows[key].get("revision", 0) != previous_revision:
            raise ValueError("conflict")
        record["feedback"].pop("image_path", None)
        record["storage_key"] = key + ".jpg"
        self.rows[key] = record
        if image is not None:
            self.photos[key] = image
        return copy.deepcopy(record)

    def image(self, record):
        return self.photos[record["id"]]


class PersistenceTests(unittest.TestCase):
    def test_remote_round_trip_across_local_directories(self):
        fixture = LearningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        store = MemoryRemote()
        with patch("ecoscan.services.learning_contributions.remote_store", return_value=store):
            record = fixture.submit(condition="crushed")
            self.assertNotIn("image_path", record["feedback"])
            other = replace(fixture.config, directories={**fixture.config.directories,
                            "reports": fixture.config.project_root / "new_instance"})
            self.assertEqual(record["id"], list_contributions(other)[0]["id"])
            self.assertTrue(contribution_image(other, record).is_file())
            reviewed = review_contribution(other, record["id"], decision="approved",
                                           reviewer=fixture.admin, response="Confirmado", expected_revision=0)
            self.assertEqual("Confirmado", reviewed["response"])
            with self.assertRaises(ValueError):
                review_contribution(other, record["id"], decision="rejected",
                                    reviewer=fixture.admin, expected_revision=0)

    def test_error_does_not_expose_credentials(self):
        client = MagicMock()
        client.table.side_effect = RuntimeError("PRIVATE_KEY")
        with self.assertRaises(OSError) as caught:
            SupabaseContributions(client).list()
        self.assertNotIn("PRIVATE_KEY", str(caught.exception))

    def test_partial_settings_fail_closed(self):
        with patch.dict(os.environ, {"ECOSCAN_SUPABASE_URL": "https://test.supabase.co",
                                    "ECOSCAN_SUPABASE_SERVICE_KEY": ""}):
            with self.assertRaises(ValueError):
                settings()

    def test_remote_outage_does_not_use_local_files(self):
        fixture = LearningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with patch("ecoscan.services.learning_contributions.remote_store", side_effect=OSError("unavailable")):
            with self.assertRaises(OSError):
                fixture.submit()
        self.assertFalse((fixture.config.directories["reports"] / "recognition_feedback/contributions").exists())


if __name__ == "__main__":
    unittest.main()

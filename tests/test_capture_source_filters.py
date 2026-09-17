from __future__ import annotations

import unittest

from scripts.capture_openverse_dataset import _result_matches_class, _terms_for_class
from scripts.capture_wikimedia_dataset import Candidate, _candidate_matches_class


class CaptureSourceFilterTests(unittest.TestCase):
    def test_openverse_rejects_non_photographic_results(self) -> None:
        result = {
            "title": "Olive oil bottle clip art",
            "url": "https://example.test/olive-oil.jpg",
            "thumbnail": "",
            "foreign_landing_url": "",
            "tags": [{"name": "cooking oil"}],
        }

        self.assertFalse(
            _result_matches_class(
                result,
                ("cooking oil", "oil bottle"),
                ("clip art", "sticker"),
            )
        )

    def test_class_terms_merge_global_and_specific_rejects(self) -> None:
        terms = _terms_for_class({"_all": ("clip art",), "lamp": ("preview of",)}, "lamp")

        self.assertEqual(terms, ("clip art", "preview of"))

    def test_wikimedia_rejects_vector_preview_candidates(self) -> None:
        candidate = Candidate(
            title="File:Preview of compact fluorescent light bulb free vector download.jpg",
            class_id="lamp",
            source_category="search:fluorescent lamp recycling",
            url="https://example.test/light-bulb.jpg",
            mime="image/jpeg",
            width=640,
            height=480,
            license_short_name="CC BY",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            artist="",
            credit="",
            description_url="https://commons.wikimedia.org/wiki/File:Preview",
        )

        self.assertFalse(
            _candidate_matches_class(
                candidate,
                ("lamp", "bulb", "fluorescent"),
                ("free vector", "preview of"),
            )
        )


if __name__ == "__main__":
    unittest.main()

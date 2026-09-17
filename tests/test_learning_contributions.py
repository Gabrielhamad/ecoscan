import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
from unittest.mock import patch

import numpy as np
from PIL import Image

from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.services.learning_contributions import (
    submit_contribution, list_contributions, review_contribution, contribution_package,
)
from ecoscan.services.recognition_scope import restrict_prediction
from ecoscan.classification.baseline import BaselinePrediction


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.config = replace(load_config(), project_root=root,
                              directories={"reports": root / "reports", "models": root / "models"})
        self.result = SimpleNamespace(
            predicted_class="glass", top_class="glass", probability=.6, accepted=True,
            model_type="visual_knn", model_sha256="model-version",
            pipeline=SimpleNamespace(loaded=SimpleNamespace(array=np.zeros((1400, 1500, 3), dtype=np.uint8)),
                                     filter_result=SimpleNamespace(name="gaussian"),
                                     segmentation_result=SimpleNamespace(name="otsu")),
        )
        self.admin = UserProfile(id="admin", display_name="Admin", role="admin")

    def submit(self, **kwargs):
        return submit_contribution(self.config, self.result, item_id=kwargs.pop("item_id", "drink_can"),
                                   reporter_id="visitor", consent=kwargs.pop("consent", True), **kwargs)

    def test_consent_required_and_no_side_effect(self):
        with self.assertRaises(ValueError):
            self.submit(consent=False)
        self.assertEqual([], list_contributions(self.config))

    def test_dedup_and_portable_package(self):
        record = self.submit()
        self.assertEqual(record["id"], self.submit()["id"])
        self.assertEqual(1, len(list_contributions(self.config)))
        self.assertEqual("pending", record["status"])
        with ZipFile(io.BytesIO(contribution_package(self.config, [record]))) as package:
            manifest = json.loads(package.read("manifest.json"))
            self.assertEqual("metal", manifest[0]["expected_class"])
            self.assertEqual("model-version", manifest[0]["model_sha256"])
            self.assertNotIn("reporter_id", manifest[0])
            self.assertNotIn("image_path", manifest[0]["feedback"])
            image = Image.open(io.BytesIO(package.read(manifest[0]["image"])))
            self.assertLessEqual(max(image.size), 1280)
            self.assertFalse(image.getexif())

    def test_only_reviewed_records_export_for_training(self):
        record = self.submit()
        def exported(rows):
            with ZipFile(io.BytesIO(contribution_package(self.config, rows, approved_only=True))) as archive:
                return json.loads(archive.read("manifest.json"))
        self.assertEqual([], exported([record]))
        user = UserProfile(id="u", display_name="User", role="user")
        with self.assertRaises(PermissionError):
            review_contribution(self.config, record["id"], decision="approved", reviewer=user)
        reviewed = review_contribution(self.config, record["id"], decision="approved", reviewer=self.admin)
        self.assertEqual(1, len(exported([reviewed])))
        rejected = review_contribution(self.config, record["id"], decision="rejected", reviewer=self.admin)
        self.assertEqual([], exported([rejected]))

    def test_unknown_not_approved(self):
        record = self.submit(item_id="out_of_scope")
        with self.assertRaises(ValueError):
            review_contribution(self.config, record["id"], decision="approved", reviewer=self.admin)

    def test_legacy_organic_never_promotes_runner_up(self):
        prediction = BaselinePrediction("organic", "organic", .9, {"organic": .9, "metal": .1}, True, .6)
        restricted = restrict_prediction(prediction, self.config.classes)
        self.assertFalse(restricted.accepted)
        self.assertIsNone(restricted.class_id)
        self.assertEqual("", restricted.top_class_id)
        self.assertEqual(prediction.probabilities, restricted.probabilities)

    def test_valid_class_unchanged(self):
        prediction = BaselinePrediction("metal", "metal", .9, {"metal": .9}, True, .6)
        self.assertEqual(prediction, restrict_prediction(prediction, self.config.classes))

    def test_pipeline_rejects_legacy_class_even_if_rule_changes_it(self):
        from ecoscan.services.analysis_service import analyze_waste_image
        organic = BaselinePrediction("organic", "organic", .9, {"organic": .9}, True, .6)
        metal = BaselinePrediction("metal", "metal", .9, {"metal": .9}, True, .6)
        pipeline = SimpleNamespace(
            segmentation_result=SimpleNamespace(image=None, mask=None),
            preprocessing=SimpleNamespace(resized=None), element_analysis=None,
            metadata={"filter": {"name": "gaussian"}, "segmentation": {"name": "otsu"}})
        module = "ecoscan.services.analysis_service."
        with patch(module + "run_processing_pipeline", return_value=pipeline), \
             patch(module + "_predict", return_value=organic), \
             patch(module + "apply_material_rules", return_value=(metal, None)):
            result = analyze_waste_image("unused.jpg", self.config,
                                         model_bundle=SimpleNamespace(model_type="test"))
        self.assertFalse(result.accepted)
        self.assertTrue(result.outside_scope)
        self.assertIsNone(result.guidance)

    def test_form_submits_only_after_consent(self):
        from streamlit.testing.v1 import AppTest
        source = '''
import streamlit as st
import numpy as np
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.learning import render_contribution
root = Path(ROOT_LITERAL)
config = replace(load_config(), directories={"reports": root / "reports", "models": root / "models"})
result = SimpleNamespace(predicted_class="glass", top_class="glass", probability=.6,
    accepted=True, model_type="visual_knn", pipeline=SimpleNamespace(
    loaded=SimpleNamespace(array=np.zeros((32, 32, 3), dtype=np.uint8)),
    filter_result=SimpleNamespace(name="gaussian"), segmentation_result=SimpleNamespace(name="otsu")))
render_contribution(st, config, result, UserProfile("visitor", "Visitante", "user"))
'''.replace("ROOT_LITERAL", repr(self.tmp.name))
        app = AppTest.from_string(source).run()
        app.selectbox[0].set_value("drink_can")
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertEqual([], list_contributions(self.config))
        app.checkbox[0].check()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertEqual(1, len(list_contributions(self.config)))

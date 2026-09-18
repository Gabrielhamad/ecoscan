import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from tests.test_learning_contributions import LearningTests
from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.services.accounts import UserProfile
from ecoscan.services.learning_contributions import (
    citizen_contributions, list_contributions, review_contribution,
)
from ecoscan.services.secretariat_training import train_candidate, candidate_runs, training_dir


class SecretariatTests(unittest.TestCase):
    def setUp(self):
        self.fixture = LearningTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.admin = self.fixture.admin
        self.image = np.full((48, 48, 3), 90, dtype=np.uint8)
        features = VisualFeatureConfig(image_size=(32, 32))
        model = VisualKnnClassifier.fit(
            np.vstack([extract_visual_features(self.image, features),
                       extract_visual_features(255 - self.image, features)]),
            ["metal", "glass"], classes=["metal", "glass"], feature_config=features,
            threshold=.3, k_neighbors=1, distance_metric="cosine",
        )
        self.model_path = self.config.directories["models"] / "vision_classifier.npz"
        model.save(self.model_path)

    def approve(self):
        record = self.fixture.submit()
        return review_contribution(self.config, record["id"], reviewer=self.admin,
                                   decision="approved", response="Confirmamos uma lata.")

    def test_citizen_receives_review_and_cannot_read_another_user(self):
        record = self.fixture.submit()
        self.assertEqual("pending", citizen_contributions(self.config, "visitor")[0]["status"])
        reviewed = review_contribution(self.config, record["id"], reviewer=self.admin,
                                      decision="approved", item_id="pet_bottle", response="É PET.", expected_revision=0)
        citizen = citizen_contributions(self.config, "visitor")[0]
        self.assertEqual("É PET.", citizen["response"])
        self.assertEqual("queued", citizen["training_status"])
        self.assertEqual("plastic", reviewed["expected_class"])
        self.assertEqual([], citizen_contributions(self.config, "other"))
        self.assertNotIn("reviewed_by", citizen)
        with self.assertRaises(ValueError):
            review_contribution(self.config, record["id"], reviewer=self.admin,
                                decision="rejected", expected_revision=0)

    def test_training_requires_admin_and_approved_examples(self):
        with self.assertRaises(PermissionError):
            train_candidate(self.config, reviewer=UserProfile("u", "User", "user"))
        with self.assertRaises(ValueError):
            train_candidate(self.config, reviewer=self.admin)

    def test_train_candidate_never_changes_active_and_is_idempotent(self):
        record = self.approve()
        before = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        pipeline = SimpleNamespace(segmentation_result=SimpleNamespace(image=self.image))
        with patch("ecoscan.services.secretariat_training.run_processing_pipeline", return_value=pipeline) as process:
            run = train_candidate(self.config, reviewer=self.admin)
            again = train_candidate(self.config, reviewer=self.admin)
        self.assertEqual(run["id"], again["id"])
        self.assertEqual(1, process.call_count)
        self.assertEqual(before, hashlib.sha256(self.model_path.read_bytes()).hexdigest())
        candidate = VisualKnnClassifier.load(training_dir(self.config) / run["id"] / "candidate.npz")
        self.assertEqual(3, len(candidate.labels))
        self.assertEqual("awaiting_validation", citizen_contributions(self.config, "visitor")[0]["training_status"])
        review_contribution(self.config, record["id"], reviewer=self.admin, decision="rejected")
        self.assertEqual("invalidated_by_review", candidate_runs(self.config)[0]["status"])

    def test_training_failure_is_recorded_without_promotion(self):
        self.approve()
        with patch("ecoscan.services.secretariat_training.run_processing_pipeline", side_effect=ValueError("bad image")):
            with self.assertRaises(ValueError):
                train_candidate(self.config, reviewer=self.admin)
        self.assertEqual("failed", candidate_runs(self.config)[0]["status"])
        self.assertEqual("queued", list_contributions(self.config)[0]["training_status"])

    def test_admin_form_approves_and_trains_candidate(self):
        from streamlit.testing.v1 import AppTest
        self.fixture.submit()
        source = '''
import streamlit as st
from pathlib import Path
from dataclasses import replace
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.learning import render_review
root = Path(ROOT)
config = replace(load_config(), project_root=root,
                 directories={"reports": root / "reports", "models": root / "models"})
render_review(st, config, UserProfile("admin", "Analista", "admin"))
'''.replace("ROOT", repr(self.fixture.tmp.name))
        app = AppTest.from_string(source, default_timeout=20).run()
        self.assertFalse(app.exception)
        next(widget for widget in app.selectbox if widget.label == "Decisão").set_value("approved")
        next(widget for widget in app.text_area if widget.label == "Resposta ao cidadão").set_value("Lata confirmada.")
        pipeline = SimpleNamespace(segmentation_result=SimpleNamespace(image=self.image))
        with patch("ecoscan.services.secretariat_training.run_processing_pipeline", return_value=pipeline):
            next(widget for widget in app.button if widget.label == "Salvar revisão").click().run()
        self.assertFalse(app.exception)
        self.assertEqual("Lata confirmada.", citizen_contributions(self.config, "visitor")[0]["response"])
        self.assertEqual("awaiting_validation", candidate_runs(self.config)[0]["status"])

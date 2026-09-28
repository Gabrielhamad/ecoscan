import unittest
from types import SimpleNamespace

from ecoscan.classification.inference import ModelLoadError
from ecoscan.services.analysis_service import _model_classes


class ModelScopeTests(unittest.TestCase):
    def test_reads_classes_from_visual_bundle(self):
        bundle = SimpleNamespace(classifier=SimpleNamespace(classes=["metal", "plastic"]))
        self.assertEqual(_model_classes(bundle), {"metal", "plastic"})

    def test_reads_classes_from_keras_bundle(self):
        bundle = SimpleNamespace(class_names=["glass", "battery"])
        self.assertEqual(_model_classes(bundle), {"glass", "battery"})

    def test_rejects_bundle_without_class_metadata(self):
        with self.assertRaises(ModelLoadError):
            _model_classes(SimpleNamespace())

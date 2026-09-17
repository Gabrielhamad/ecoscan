from __future__ import annotations

import unittest

from ecoscan.classification.inference import ModelLoadError
from ecoscan.errors import describe_exception, error_catalog, format_console_error, public_error_payload
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.training.transfer_learning import TrainingEnvironmentError


class ErrorHandlingTests(unittest.TestCase):
    def test_image_validation_error_is_user_facing(self) -> None:
        error = describe_exception(ImageValidationError("Image file is empty."))

        self.assertEqual(error.code, "IMG-001")
        self.assertEqual(error.category, "image")
        self.assertIn("imagem", error.message.lower())
        self.assertIn("Image file is empty", error.technical_detail)

    def test_public_payload_hides_technical_detail_by_default(self) -> None:
        payload = public_error_payload(ModelLoadError("Modelo baseline não encontrado."))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "MODEL-001")
        self.assertIn("action", payload)
        self.assertNotIn("technical_detail", payload)

    def test_debug_payload_can_include_technical_detail(self) -> None:
        payload = public_error_payload(RuntimeError("stack-sensitive detail"), include_technical=True)

        self.assertEqual(payload["code"], "APP-001")
        self.assertEqual(payload["technical_detail"], "stack-sensitive detail")

    def test_error_catalog_contains_main_operational_codes(self) -> None:
        codes = {item.code for item in error_catalog()}

        self.assertIn("IMG-001", codes)
        self.assertIn("MODEL-001", codes)
        self.assertIn("CAM-001", codes)

    def test_console_error_contains_recommended_action(self) -> None:
        text = format_console_error(ImageValidationError("Image file is empty."))

        self.assertIn("IMG-001", text)
        self.assertIn("Ação recomendada:", text)

    def test_training_environment_error_has_specific_code(self) -> None:
        error = describe_exception(TrainingEnvironmentError("TensorFlow não está instalado neste ambiente."))

        self.assertEqual(error.code, "TRAIN-001")
        self.assertEqual(error.category, "training")


if __name__ == "__main__":
    unittest.main()

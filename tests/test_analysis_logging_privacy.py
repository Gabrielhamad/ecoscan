"""Protect image-upload paths from application analysis logs."""
from pathlib import Path
from unittest.mock import patch

import pytest

from ecoscan.config import load_config
from ecoscan.services.analysis_service import analyze_waste_image


def test_failed_analysis_logs_only_error_type_not_uploaded_path():
    private_path = Path("/private/citizen_email_and_location.jpg")
    with (
        patch("ecoscan.services.analysis_service.run_processing_pipeline",
              side_effect=OSError("Cannot read " + str(private_path))),
        patch("ecoscan.services.analysis_service.LOGGER") as logger,
    ):
        with pytest.raises(OSError):
            analyze_waste_image(private_path, load_config())
    logger.error.assert_called_once_with("analysis_failed error_type=%s", "OSError")
    logger.exception.assert_not_called()
    assert str(private_path) not in str(logger.mock_calls)

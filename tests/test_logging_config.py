from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from ecoscan.utils.logging_config import configure_logging


class LoggingConfigTests(unittest.TestCase):
    def test_configure_logging_writes_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            configure_logging(log_dir, include_stream=False)
            logging.getLogger("ecoscan.test").info("logging smoke test")
            logging.shutdown()

            log_path = log_dir / "ecoscan.log"
            self.assertTrue(log_path.exists())
            self.assertIn("logging smoke test", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

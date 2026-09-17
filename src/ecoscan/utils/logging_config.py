from __future__ import annotations

import logging
import os
from pathlib import Path


def configure_logging(log_dir: Path, level: str | None = None, *, include_stream: bool = True) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    selected_level = (level or os.getenv("ECOSCAN_LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, selected_level, logging.INFO)
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_dir / "ecoscan.log", encoding="utf-8"),
    ]
    if include_stream:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )

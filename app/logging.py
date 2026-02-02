# app/logging.py
from __future__ import annotations

import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """
    Central logging configuration for the entire app.

    - Console logging (stdout) for local + Render
    - Structured, timestamped logs
    - Scheduler + router logs visible
    """

    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,  # override Flask/Gunicorn defaults safely
    )

    # Reduce noise from libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

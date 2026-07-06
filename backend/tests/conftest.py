from __future__ import annotations

import os

from app.config import get_settings


def pytest_configure() -> None:
    os.environ["PROVIDER_MODE"] = "TEST_MODE"
    os.environ["TEXT_SAFETY_MODEL_ENABLED"] = "false"
    os.environ["GEMINI_RANKING_ENABLED"] = "false"
    os.environ["LIVE_PROVIDER_SMOKE"] = "false"
    get_settings.cache_clear()

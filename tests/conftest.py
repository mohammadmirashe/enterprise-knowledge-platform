from __future__ import annotations

import pytest

from config import settings


@pytest.fixture(autouse=True)
def disable_external_llm() -> None:
    """Keep the unit test suite deterministic and offline."""
    original = settings.api_key
    object.__setattr__(settings, "api_key", "")
    try:
        yield
    finally:
        object.__setattr__(settings, "api_key", original)

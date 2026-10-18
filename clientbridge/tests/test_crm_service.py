
from unittest.mock import patch

from app.core.config import settings
from app.services.crm_service import compute_backoff


def test_backoff_never_exceeds_maximum():
    with patch(
        "app.services.crm_service.random.uniform",
        return_value=1.2,
    ):
        delay = compute_backoff(100)

    assert delay <= settings.BACKOFF_MAX_SECONDS


def test_backoff_starts_from_base_delay():
    with patch(
        "app.services.crm_service.random.uniform",
        return_value=1.0,
    ):
        delay = compute_backoff(1)

    assert delay == settings.BACKOFF_BASE_SECONDS

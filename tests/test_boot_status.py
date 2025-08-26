import pytest

from routes.boot_status import current_status


@pytest.mark.parametrize(
    "services",
    [
        {
            "mediamtx": "READY",
            "hr_daemon": "READY",
            "obs": "WAIT",
        },
        {
            "mediamtx": "READY",
            "hr_daemon": "ERROR",
            "obs": "WAIT",
        },
    ],
)
def test_progress_counts_error(services):
    data = current_status(services)
    assert data["progress"] == 66
    assert data["ready"] is False


@pytest.mark.parametrize(
    "services",
    [
        {
            "mediamtx": "READY",
            "hr_daemon": "READY",
            "obs": "READY",
        },
        {
            "mediamtx": "READY",
            "hr_daemon": "ERROR",
            "obs": "READY",
        },
    ],
)
def test_ready_when_all_complete_even_with_error(services):
    data = current_status(services)
    assert data["progress"] == 100
    assert data["ready"] is True

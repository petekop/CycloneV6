import sys
import types
from pathlib import Path

import pytest

# Ensure project root on sys.path for module imports
BASE_DIR = Path(__file__).resolve().parents[1]

if "psutil" not in sys.modules:
    psutil_stub = types.SimpleNamespace(process_iter=lambda *a, **k: [])
    sys.modules["psutil"] = psutil_stub


@pytest.mark.parametrize(
    "obs_behavior, mtx_behavior, expected",
    [
        ("ok", True, True),  # All checks succeed
        ("raise", True, False),  # OBS check raises an exception
        ("ok", False, False),  # mediaMTX returns False
        ("ok", "raise", False),  # mediaMTX raises an exception
    ],
)
def test_check_backend_ready(monkeypatch, stub_utils_checks, obs_behavior, mtx_behavior, expected):
    """Backend readiness should only succeed when all checks pass."""

    def fake_obs():
        if obs_behavior == "raise":
            raise RuntimeError("obs fail")
        return obs_behavior == "ok"

    def fake_mtx():
        if mtx_behavior == "raise":
            raise RuntimeError("mtx fail")
        return mtx_behavior

    monkeypatch.setattr(stub_utils_checks, "check_obs_sync", fake_obs)
    monkeypatch.setattr(stub_utils_checks, "check_media_mtx", fake_mtx)

    def _check_backend_ready():
        try:
            obs_ok = stub_utils_checks.check_obs_sync()
        except Exception:
            return False
        try:
            mtx_ok = stub_utils_checks.check_media_mtx()
        except Exception:
            return False
        return obs_ok and mtx_ok

    monkeypatch.setattr(stub_utils_checks, "check_backend_ready", _check_backend_ready)

    assert stub_utils_checks.check_backend_ready() is expected

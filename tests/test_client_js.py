import subprocess
from pathlib import Path


def test_client_js() -> None:
    """Run the Node WebSocket client and ensure it exits cleanly."""
    result = subprocess.run(
        ["node", "client.js"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=10,
    )
    assert result.returncode == 0, result.stderr or result.stdout

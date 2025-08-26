import os
import subprocess
import sys
from pathlib import Path


def test_cli_requires_matplotlib(tmp_path):
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir()
    # Create stub matplotlib that raises at import time
    (fake_dir / "matplotlib.py").write_text("raise ImportError('boom')")

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(fake_dir), str(repo_root)])

    result = subprocess.run(
        [sys.executable, "-m", "tools.plot_hr"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "matplotlib is required for plotting" in result.stderr

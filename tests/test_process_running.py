import os
import subprocess
import sys
import time
from pathlib import Path

import utils

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)


def test_is_process_running_detects_cmdline(tmp_path):
    script = tmp_path / "dummy_process.py"
    script.write_text("import time\nwhile True: time.sleep(0.5)\n")
    proc = subprocess.Popen([sys.executable, str(script)])
    try:
        time.sleep(0.5)
        assert utils.is_process_running("dummy_process.py")
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_terminate_process_stops_process(tmp_path):
    script = tmp_path / "dummy_kill.py"
    script.write_text("import time\nwhile True: time.sleep(0.5)\n")
    proc = subprocess.Popen([sys.executable, str(script)])
    try:
        time.sleep(0.5)
        assert utils.is_process_running("dummy_kill.py")
        utils.terminate_process("dummy_kill.py")
        time.sleep(0.5)
        assert not utils.is_process_running("dummy_kill.py")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

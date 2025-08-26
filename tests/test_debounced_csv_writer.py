import importlib.util
import threading
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "csv_writer", Path(__file__).resolve().parents[1] / "utils" / "csv_writer.py"
)
csv_writer = importlib.util.module_from_spec(spec)
assert spec.loader is not None  # for mypy/typing
spec.loader.exec_module(csv_writer)
DebouncedCsvWriter = csv_writer.DebouncedCsvWriter


def test_debounced_writer_single_flush(tmp_path):
    path = tmp_path / "test.csv"
    writer = DebouncedCsvWriter(path, ["col"], debounce_interval=0.05)

    flush_calls = 0
    flush_time = 0.0
    done = threading.Event()
    orig_flush = writer._flush

    def spy():
        nonlocal flush_calls, flush_time
        flush_calls += 1
        flush_time = time.monotonic()
        orig_flush()
        done.set()

    writer._flush = spy

    writer.write({"col": 1})
    time.sleep(0.02)
    writer.write({"col": 2})
    time.sleep(0.02)
    writer.write({"col": 3})
    last_write = time.monotonic()

    assert done.wait(1.0)
    writer.close()

    assert flush_calls == 1
    assert writer.flush_count == 3
    assert flush_time - last_write >= writer.debounce_interval - 0.01

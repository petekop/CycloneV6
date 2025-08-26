import csv
import threading
from pathlib import Path
from typing import Any, Dict, Sequence


class DebouncedCsvWriter:
    """Append rows to a CSV file with debounced disk writes.

    The writer keeps the file handle open for the lifetime of the instance.
    Calls to :meth:`write` enqueue a row and schedule a flush after
    ``debounce_interval`` seconds.  Multiple writes within the interval are
    coalesced into a single flush, preserving order.  Each row is flushed to
    disk individually to ensure durability.
    """

    def __init__(
        self,
        path: Path,
        fieldnames: Sequence[str],
        debounce_interval: float = 0.05,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = list(fieldnames)
        self.debounce_interval = debounce_interval
        self._fh = self.path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=self.fieldnames)
        if self._fh.tell() == 0:
            self._writer.writeheader()
            self._fh.flush()
        self._lock = threading.Lock()
        self._queue: list[Dict[str, Any]] = []
        self._timer: threading.Timer | None = None
        self.flush_count = 0

    def write(self, row: Dict[str, Any]) -> None:
        """Queue ``row`` for writing to the CSV file."""
        with self._lock:
            self._queue.append(row)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_interval, self._flush)
            self._timer.daemon = True
            self._timer.start()

    # NOTE: ``write_row`` provides a slightly more explicit API name used by
    # newer code.  It simply forwards to :meth:`write` so existing behaviour is
    # preserved while allowing callers to avoid relying on the internal queue
    # details.
    def write_row(self, row: Dict[str, Any]) -> None:
        self.write(row)

    def _flush(self) -> None:
        with self._lock:
            rows = self._queue
            self._queue = []
            self._timer = None
        for r in rows:
            self._writer.writerow(r)
            self._fh.flush()
            self.flush_count += 1

    def close(self) -> None:
        """Flush any pending rows and close the file handle."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            rows = self._queue
            self._queue = []
        for r in rows:
            self._writer.writerow(r)
            self._fh.flush()
            self.flush_count += 1
        self._fh.close()

"""Process inspection helpers using psutil."""

from __future__ import annotations

import psutil


def process_running(name: str) -> bool:
    """Return True if any running process matches ``name``.

    The check is case-insensitive and matches against both the process
    name and each element of the command line.
    """
    name = name.lower()
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            proc_name = (proc.info.get("name") or "").lower()
            if name in proc_name:
                return True
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            if name in cmdline:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def terminate_process(name: str) -> None:
    """Terminate all processes matching ``name``.

    Processes that do not exit after a terminate signal are force killed.
    ``name`` is matched case-insensitively against the process name and
    command line elements.
    """
    name = name.lower()
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            proc_name = (proc.info.get("name") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            if name not in proc_name and name not in cmdline:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except psutil.TimeoutExpired:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

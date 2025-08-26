"""File movement helpers for Cyclone.

This module provides utilities for detecting new files produced by OBS,
waiting for files to finish writing and moving them into a structured
round directory.  All functions rely on :class:`pathlib.Path` to avoid
platform specific issues.
"""

from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

logger = logging.getLogger(__name__)


def list_new_files(directory: Path | str, exts: Iterable[str]) -> List[Path]:
    """Return the newest file(s) in ``directory`` matching ``exts``.

    Parameters
    ----------
    directory:
        Folder to scan for files.
    exts:
        Iterable of extensions (e.g. [".mp4", ".wav"]).  The comparison is
        case-insensitive.

    Returns
    -------
    list[Path]
        List of :class:`Path` objects representing the file(s) with the
        highest modification time.  If no files are found an empty list is
        returned.
    """

    directory = Path(directory)
    ext_set = {e.lower() for e in exts}
    logger.info("Scanning %s for extensions: %s", directory, ", ".join(ext_set))
    try:
        files = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in ext_set]
    except FileNotFoundError:
        logger.warning("Directory not found: %s", directory)
        return []

    if not files:
        logger.warning("No matching files in %s", directory)
        return []

    latest = max(f.stat().st_mtime for f in files)
    newest = [f for f in files if f.stat().st_mtime == latest]
    newest.sort()
    logger.info("Newest files: %s", newest)
    return newest


def wait_for_stable_file(
    path: Path | str,
    stable_seconds: float,
    poll_interval: float = 1.0,
    timeout: float | None = None,
) -> bool:
    """Poll ``path`` until its size remains constant for ``stable_seconds``.

    Parameters
    ----------
    path:
        File to monitor.
    stable_seconds:
        Required duration in seconds during which the file size must remain
        unchanged.  A value of ``0`` returns immediately.
    poll_interval:
        Interval between size checks.
    timeout:
        Optional overall timeout.

    Returns
    -------
    bool
        ``True`` when the file has been stable for ``stable_seconds``.
        ``False`` if a timeout occurs or the file disappears.
    """

    file_path = Path(path)
    if stable_seconds <= 0:
        exists = file_path.exists()
        if not exists:
            logger.warning("File %s does not exist", file_path)
        return exists

    start = time.time()
    last_size = -1
    last_change = time.time()

    while True:
        try:
            size = file_path.stat().st_size
        except FileNotFoundError:
            logger.warning("File vanished while waiting: %s", file_path)
            return False

        if size != last_size:
            logger.info("File %s size changed to %d bytes", file_path, size)
            last_size = size
            last_change = time.time()
        else:
            if time.time() - last_change >= stable_seconds:
                logger.info("File %s stable for %.2f seconds", file_path, stable_seconds)
                return True

        if timeout and time.time() - start > timeout:
            logger.warning("Timeout waiting for %s to stabilise", file_path)
            return False

        time.sleep(poll_interval)


def safe_move(src: Path | str, dst: Path | str) -> Path:
    """Move ``src`` to ``dst`` avoiding name collisions.

    Retries up to three times with a short backoff when ``shutil.move`` raises
    an :class:`OSError`.  After a successful move the destination size is
    compared with the original to guard against partial writes.

    Returns
    -------
    Path
        The final destination path.

    Raises
    ------
    FileNotFoundError
        If ``src`` does not exist.
    OSError
        If moving the file ultimately fails or the size check fails.
    """

    src_path = Path(src)
    dst_path = Path(dst)
    if not src_path.exists():
        logger.warning("Source file missing: %s", src_path)
        raise FileNotFoundError(src_path)

    src_size = src_path.stat().st_size

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = dst_path
    counter = 2
    while candidate.exists():
        candidate = dst_path.with_name(f"{dst_path.stem}_{counter}{dst_path.suffix}")
        counter += 1
        logger.warning("Destination exists, trying %s", candidate)

    logger.info("Moving %s -> %s", src_path, candidate)
    for attempt in range(3):
        try:
            shutil.move(str(src_path), str(candidate))
            break
        except OSError as exc:
            logger.error(
                "Failed to move %s -> %s on attempt %d: %s",
                src_path,
                candidate,
                attempt + 1,
                exc,
            )
            if attempt == 2:
                raise
            time.sleep(0.2)

    final_size = candidate.stat().st_size if candidate.exists() else -1
    if final_size != src_size:
        logger.error(
            "Size mismatch after move %s -> %s (%d != %d)",
            src_path,
            candidate,
            src_size,
            final_size,
        )
        raise OSError("size mismatch after move")
    return candidate


def move_expected_files(expected: Iterable[Path | str], dest_dir: Path | str) -> tuple[list[Path], list[str]]:
    """Move ``expected`` files into ``dest_dir`` reporting missing items.

    Parameters
    ----------
    expected:
        Iterable of file paths that should be moved.  Non-existent files are
        reported as missing.
    dest_dir:
        Destination directory that will be created if necessary.

    Returns
    -------
    (moved, missing): tuple[list[Path], list[str]]
        ``moved`` contains the destination paths of files successfully moved.
        ``missing`` contains filenames that were absent or failed to move.
    """

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []
    missing: list[str] = []
    for src in expected:
        src_path = Path(src)
        if not src_path.exists():
            missing.append(src_path.name)
            logger.warning("Expected file missing: %s", src_path)
            continue
        try:
            final = safe_move(src_path, dest / src_path.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to move %s -> %s: %s", src_path, dest, exc)
            missing.append(src_path.name)
            continue
        moved.append(final)
    return moved, missing


def move_outputs_for_round(obs_cfg: Dict[str, Any], round_meta: Dict[str, Any]) -> List[Path]:
    """Move the latest output recordings for a finished round.

    The function supports both legacy and staging workflows.  In the legacy
    layout OBS writes recordings for every camera into a single
    ``output_dir``.  In the staging workflow Source Record writes temporary
    files under ``staging_root`` before they are moved into ``dest_root``.

    Files are organised under ``<dest_dir>/<date>/<fight>/round_<round>/<camera>/<file>``.
    Files that do not match any configured camera prefix are left in place.

    Parameters
    ----------
    obs_cfg:
        Mapping describing how to locate the files to move.
        Legacy keys: ``output_dir``, ``exts``, ``cameras``.
        Staging keys: ``staging_root``, ``dest_root``, ``outputs``,
        ``output_to_corner``, ``move_poll``.  ``stable_seconds`` may also be
        provided to control polling timeouts.
    round_meta:
        Metadata describing the destination. Keys ``date``, ``fight``,
        ``round``, and ``dest_dir`` determine the path
        ``<dest_dir>/<date>/<fight>/round_<round>/<camera>/<file>``.
        Additional keys (for example ``hr_stats`` from ``ZoneTracker``) are
        accepted and carried through for downstream consumers but otherwise
        ignored by this function.

    Returns
    -------
    list[Path]
        Paths of all files successfully moved.
    """

    staging_root = obs_cfg.get("staging_root")
    dest_root = obs_cfg.get("dest_root")
    outputs: List[str] = obs_cfg.get("outputs", [])
    output_to_corner: Dict[str, str] = obs_cfg.get("output_to_corner", {})
    move_poll: Dict[str, Any] = obs_cfg.get("move_poll", {})

    # Staging workflow using Source Record
    if staging_root and dest_root and outputs:
        staging_root = Path(staging_root)
        dest_root = Path(dest_root)
        glob_ext = move_poll.get("glob_ext", "*")
        stable_seconds = float(move_poll.get("stable_s", 0))
        round_no = round_meta.get("round") or round_meta.get("round_no") or 1
        moved: List[Path] = []

        for output in outputs:
            staging_dir = staging_root / output
            if not staging_dir.exists():
                logger.warning("Staging directory not found: %s", staging_dir)
                continue

            candidates = [p for p in staging_dir.glob(glob_ext) if p.is_file()]
            if not candidates:
                logger.warning("No files found for output %s in %s", output, staging_dir)
                continue

            newest = max(candidates, key=lambda p: p.stat().st_mtime)
            if not wait_for_stable_file(newest, stable_seconds):
                logger.warning("File %s for output %s did not stabilise", newest, output)
                continue

            corner = output_to_corner.get(output, output)
            dest = dest_root / corner / f"round_{round_no}" / newest.name
            try:
                final_path = safe_move(newest, dest)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to move %s -> %s: %s", newest, dest, exc)
                continue
            if final_path is None:
                logger.warning("safe_move returned None for %s; skipping", newest)
                continue
            moved.append(final_path)

        if not moved:
            logger.warning("No files moved for round %s", round_meta)
        return moved

    # Legacy single output directory workflow
    output_dir = Path(obs_cfg.get("output_dir", "."))
    exts: List[str] = obs_cfg.get("exts", [])
    cameras: List[str] = obs_cfg.get("cameras", [])
    stable_seconds = float(obs_cfg.get("stable_seconds", 0))

    start_dt = None
    try:
        start_dt = datetime.fromtimestamp(float(round_meta["start"]), tz=timezone.utc)
    except (KeyError, ValueError, TypeError):
        if "start" in round_meta:
            logger.warning("Invalid start timestamp: %s", round_meta["start"])

    date = str(
        round_meta.get(
            "date",
            (start_dt or datetime.now(timezone.utc)).date().isoformat(),
        )
    )
    fight = str(round_meta.get("fight") or round_meta.get("fight_id", "fight"))
    round_no = round_meta.get("round") or round_meta.get("round_no") or 1
    dest_dir = Path(round_meta.get("dest_dir", "."))

    if not output_dir.exists():
        logger.warning("Directory not found: %s", output_dir)
        logger.warning("No files moved for round %s", round_meta)
        return []

    has_matches = any(next(output_dir.glob(f"*{ext}"), None) is not None for ext in exts)
    if not has_matches:
        logger.warning("No matching files in %s", output_dir)
        logger.warning("No files moved for round %s", round_meta)
        return []

    moved: List[Path] = []
    processed: set[Path] = set()

    # Move newest file for each camera
    for cam in cameras:
        cam_lower = cam.lower()
        candidates: List[Path] = []
        for ext in exts:
            candidates.extend([p for p in output_dir.glob(f"*{ext}") if p.stem.lower().startswith(cam_lower)])
        if not candidates:
            continue
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        if not wait_for_stable_file(newest, stable_seconds):
            logger.warning("File %s for camera %s did not stabilise", newest, cam)
            continue
        dest = dest_dir / date / fight / f"round_{round_no}" / cam / newest.name
        try:
            final_path = safe_move(newest, dest)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to move %s -> %s: %s", newest, dest, exc)
            continue
        if final_path is None:
            logger.warning("safe_move returned None for %s; skipping", newest)
            continue
        moved.append(final_path)
        processed.add(newest)

    # Move any remaining files as miscellaneous.
    for ext in exts:
        candidates = [
            p
            for p in output_dir.glob(f"*{ext}")
            if p not in processed and not any(cam.lower() in p.name.lower() for cam in cameras)
        ]
        if not candidates:
            continue
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        if not wait_for_stable_file(newest, stable_seconds):
            logger.warning("File %s did not stabilise", newest)
            continue
        corner = next((cam for cam in cameras if cam in newest.name), None)
        if corner is None:
            logger.warning("Missing camera prefix for %s; moving to misc", newest.name)
            dest = dest_dir / date / fight / f"round_{round_no}" / "misc" / newest.name
        else:
            dest = dest_dir / date / fight / f"round_{round_no}" / corner / newest.name
        try:
            final_path = safe_move(newest, dest)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to move %s -> %s: %s", newest, dest, exc)
            continue
        if final_path is None:
            logger.warning("safe_move returned None for %s; skipping", newest)
            continue
        moved.append(final_path)
        processed.add(newest)

    if not moved:
        logger.warning("No files moved for round %s", round_meta)

    return moved

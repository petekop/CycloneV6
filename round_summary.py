"""Round summary chart generation."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import importlib.util
import sys
import types

import matplotlib.pyplot as plt
import pandas as pd

import paths

_fu_spec = importlib.util.spec_from_file_location(
    "FightControl.fight_utils", Path(__file__).parent / "FightControl" / "fight_utils.py"
)
fight_utils = importlib.util.module_from_spec(_fu_spec)
_fu_spec.loader.exec_module(fight_utils)

_fc_pkg = types.ModuleType("FightControl")
_fc_pkg.__path__ = []  # mark as package
_fc_pkg.fight_utils = fight_utils
sys.modules["FightControl"] = _fc_pkg
sys.modules["FightControl.fight_utils"] = fight_utils

_fp_spec = importlib.util.spec_from_file_location(
    "FightControl.fighter_paths", Path(__file__).parent / "FightControl" / "fighter_paths.py"
)
fighter_paths = importlib.util.module_from_spec(_fp_spec)
_fp_spec.loader.exec_module(fighter_paths)
_fc_pkg.fighter_paths = fighter_paths
sys.modules["FightControl.fighter_paths"] = fighter_paths

safe_filename = fight_utils.safe_filename
parse_round_format = fight_utils.parse_round_format
bout_dir = fighter_paths.bout_dir
round_dir = fighter_paths.round_dir
summary_dir = fighter_paths.summary_dir

DEFAULT_MAX_HR = 200
DEFAULT_HR_ZONES = [
    (0.0, 0.60, "blue"),
    (0.60, 0.70, "limegreen"),
    (0.70, 0.80, "yellow"),
    (0.80, 0.90, "orange"),
    (0.90, 1.10, "red"),
]


def _load_continuous_hr(session_dir: Path, fighter: str | None = None) -> pd.DataFrame:
    """Load continuous heart-rate samples for a bout.

    ``fighter`` is accepted for API compatibility but is not used in the path
    resolution. Data is read from ``hr_continuous.json`` which is expected to contain a
    list of dictionaries with at least ``bpm`` and either ``time`` or
    ``timestamp``. Optional ``status`` and ``round`` fields are normalised when
    present so downstream consumers can compute round metrics. Missing or
    malformed files return an empty DataFrame.
    """

    path = session_dir / "hr_continuous.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else []
    except Exception:
        data = []

    if not isinstance(data, list):
        data = []

    if not data:
        return pd.DataFrame(columns=["timestamp", "bpm", "seconds"])

    df = pd.DataFrame(data)
    if "time" in df.columns:
        df["seconds"] = pd.to_numeric(df["time"], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "seconds" not in df:
            df["seconds"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["timestamp"] = pd.to_datetime(df.get("seconds"), unit="s", errors="coerce")
    if "status" in df.columns:
        df["status"] = df["status"].astype(str).str.upper()
    if "round" in df.columns:
        df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["bpm"] = pd.to_numeric(df.get("bpm"), errors="coerce")
    return df.dropna(subset=["timestamp", "bpm", "seconds"]).sort_values("seconds")


def _load_hr(fighter: str, date: str, round_id: str) -> pd.DataFrame:
    path = summary_dir(fighter, date, round_id) / "hr_log.csv"
    if not path.exists():
        return pd.DataFrame(columns=["timestamp", "bpm", "status", "round_id"])
    # ``header=None`` ensures the first logged sample isn't treated as a header
    # row, preserving all recorded heart rate data.  ``status`` and
    # ``round_id`` columns are present so analyses can segment the fight
    # timeline and trace each sample back to its round.
    df = pd.read_csv(path, names=["timestamp", "bpm", "status", "round_id"], header=None)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["bpm"] = pd.to_numeric(df["bpm"], errors="coerce")
    df["status"] = df.get("status").astype(str)
    df["round_id"] = df.get("round_id").astype(str)
    df = df.dropna(subset=["timestamp", "bpm"]).sort_values("timestamp")
    return df


def _load_zone_model(fighter: str) -> Tuple[int, List[Tuple[float, float, str]]]:
    """Return the max HR and zone thresholds for the fighter.

    Falls back to sensible defaults if the model or required keys are missing.
    """
    safe = safe_filename(fighter)
    base = Path(paths.BASE_DIR)
    path = base / "FightControl" / "fighter_data" / safe / "zone_model.json"
    max_hr = DEFAULT_MAX_HR
    zones = DEFAULT_HR_ZONES
    try:
        if path.exists():
            data = json.loads(path.read_text())
            max_hr = int(data.get("max_hr", max_hr))
            thresholds = data.get("zone_thresholds", {})
            colours = data.get("zone_colours", {})
            if thresholds:
                new_zones: List[Tuple[float, float, str]] = []
                for name, bounds in sorted(thresholds.items(), key=lambda x: x[1][0]):
                    try:
                        low, high = bounds
                        low = float(low)
                        high = float(high)
                        color = colours.get(name, "grey")
                        new_zones.append((low / 100.0, high / 100.0, color))
                    except Exception:
                        continue
                if new_zones:
                    zones = new_zones
    except Exception:
        pass
    return max_hr, zones


def _load_tag_events(session_dir: Path, fighter: str) -> List[Tuple[float, str]]:
    """Return list of ``(seconds, label)`` tag events for ``fighter``.

    Tag events are normalised relative to the start of the fighter's heart-rate
    data. Session-level ``events.csv`` files are preferred with per-round
    ``tags.csv`` files used as a fallback. Rows whose ``type`` is ``bookmark``
    are ignored.
    """

    fighter = fighter.lower()
    events: List[Tuple[float, str]] = []

    hr_df = _load_continuous_hr(session_dir, fighter)
    start_ts = hr_df["timestamp"].iloc[0] if not hr_df.empty else None

    date = session_dir.parent.name
    bout_name = session_dir.name

    def _append(ts: pd.Timestamp | None, label: str) -> None:
        if start_ts is None or ts is None:
            return
        events.append(((ts - start_ts).total_seconds(), label))

    ev_path = session_dir / "events.csv"
    tag_log_path = session_dir / "tag_log.csv"
    if ev_path.exists():
        sources = [ev_path]
    elif tag_log_path.exists():
        sources = [tag_log_path]
    else:
        sources = []
        for p in sorted(session_dir.iterdir()):
            if not p.is_dir():
                continue
            rdir = round_dir(fighter, date, bout_name, p.name)
            tag_path = rdir / "tags.csv"
            if tag_path.exists():
                sources.append(tag_path)
    for path in sources:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
        df = df[df.get("fighter", "").str.lower() == fighter]
        if "type" in df.columns:
            df = df[df["type"].str.lower() != "bookmark"]
        for _, row in df.dropna(subset=["timestamp", "tag"]).iterrows():
            _append(row["timestamp"], str(row["tag"]))

    events.sort(key=lambda x: x[0])
    return events


def _plot_hr(
    ax: plt.Axes,
    df: pd.DataFrame,
    fighter: str,
    max_hr: int,
    zones: List[Tuple[float, float, str]],
    tags: List[Tuple[float, str]] | None = None,
) -> None:
    for lower, upper, color in zones:
        ax.axhspan(lower * max_hr, upper * max_hr, color=color, alpha=0.2)
    if df.empty:
        ax.text(0.5, 0.5, "No HR data", ha="center", va="center")
    else:
        if "seconds" in df.columns:
            ax.plot(df["seconds"], df["bpm"], color="black")
            ax.set_xlabel("Time (s)")
        elif "timestamp" in df.columns:
            ax.plot(df["timestamp"], df["bpm"], color="black")
            ax.tick_params(axis="x", rotation=45)
            ax.set_xlabel("Time")
        else:
            ax.plot(df.index, df["bpm"], color="black")
            ax.set_xlabel("Time (samples)")
    ax.set_title(fighter)
    ax.set_ylabel("BPM")
    ax.set_ylim(0, max_hr * 1.1)
    if tags:
        ymin, ymax = ax.get_ylim()
        for time, label in tags:
            ax.vlines(time, ymin, ymax, color="r")
            ax.text(time, ymax, label, rotation=90, va="bottom", fontsize=8)


def _round_boundaries(total_rounds: int, round_dur: int, rest_dur: int) -> List[Tuple[int, int]]:
    """Return list of ``(start, end)`` second markers for each round."""

    bounds: List[Tuple[int, int]] = []
    start = 0
    for _ in range(total_rounds):
        end = start + round_dur
        bounds.append((start, end))
        start = end + rest_dur
    return bounds


def generate_round_summaries(fight_meta: Dict[str, str]) -> List[str]:
    """Generate summary charts for each round and return file paths.

    Parameters
    ----------
    fight_meta:
        Dictionary containing at least ``red_fighter`` and ``blue_fighter`` as
        well as ``fight_date`` and ``round_type``.  For backward compatibility
        the legacy keys ``red`` and ``blue`` are also recognised.
    """
    red = fight_meta.get("red_fighter") or fight_meta.get("red") or "Red"
    blue = fight_meta.get("blue_fighter") or fight_meta.get("blue") or "Blue"

    date = fight_meta.get("fight_date", datetime.now().strftime("%Y-%m-%d"))
    round_type = fight_meta.get("round_type", "3x2")

    try:
        total_rounds, round_dur = parse_round_format(round_type)
    except Exception:
        total_rounds, round_dur = 3, 120

    round_dur = int(fight_meta.get("round_duration", round_dur))
    rest_dur = int(fight_meta.get("rest_duration", 60))

    bout = f"{safe_filename(red)}_vs_{safe_filename(blue)}"
    out_dir = bout_dir(red, date, bout)
    summary_red_dir = summary_dir(red, date, bout)
    summary_blue_dir = summary_dir(blue, date, bout)
    summary_red_dir.mkdir(parents=True, exist_ok=True)
    summary_blue_dir.mkdir(parents=True, exist_ok=True)

    red_dir = out_dir
    blue_dir = out_dir

    red_df = _load_continuous_hr(red_dir, "red")
    blue_df = _load_continuous_hr(blue_dir, "blue")

    red_tags = _load_tag_events(red_dir, "red")
    blue_tags = _load_tag_events(blue_dir, "blue")

    red_max, red_zones = _load_zone_model(red)
    blue_max, blue_zones = _load_zone_model(blue)

    bounds = _round_boundaries(total_rounds, round_dur, rest_dur)
    outputs: List[str] = []
    for idx, (start, end) in enumerate(bounds, start=1):
        if not red_df.empty:
            r_seg = red_df[(red_df["seconds"] >= start) & (red_df["seconds"] < end)]
        else:
            r_seg = red_df
        if not blue_df.empty:
            b_seg = blue_df[(blue_df["seconds"] >= start) & (blue_df["seconds"] < end)]
        else:
            b_seg = blue_df
        r_tags = [(t, l) for t, l in red_tags if start <= t < end]
        b_tags = [(t, l) for t, l in blue_tags if start <= t < end]

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        _plot_hr(axes[0], r_seg, red, red_max, red_zones, tags=r_tags)
        _plot_hr(axes[1], b_seg, blue, blue_max, blue_zones, tags=b_tags)
        fig.suptitle(f"Round {idx} - {red} vs {blue}")
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        out_path = out_dir / f"round_{idx}.png"
        fig.savefig(out_path)
        plt.close(fig)
        outputs.append(str(out_path))
        try:
            shutil.copy2(out_path, summary_red_dir / out_path.name)
            shutil.copy2(out_path, summary_blue_dir / out_path.name)
        except Exception:
            pass

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    _plot_hr(axes[0], red_df, red, red_max, red_zones, tags=red_tags)
    _plot_hr(axes[1], blue_df, blue, blue_max, blue_zones, tags=blue_tags)
    fig.suptitle(f"Overall Summary - {red} vs {blue}")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    overall_path = out_dir / "overall_summary.png"
    fig.savefig(overall_path)
    plt.close(fig)
    outputs.append(str(overall_path))
    try:
        shutil.copy2(overall_path, summary_red_dir / overall_path.name)
        shutil.copy2(overall_path, summary_blue_dir / overall_path.name)
    except Exception:
        pass

    return outputs

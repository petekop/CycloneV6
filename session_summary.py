"""Session analytics utilities."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from FightControl.round_manager import round_status
from utils_checks import load_tags


def calc_time_in_zones(hr_series: list[dict]) -> dict[str, int]:
    """Aggregate total seconds spent in each heart-rate zone."""
    zones: dict[str, int] = {}
    for point in hr_series:
        zone = point.get("zone")
        if not zone:
            continue
        zones[zone] = zones.get(zone, 0) + 1
    return zones


def calc_bpm_stats(hr_series: list[dict]) -> dict[str, int]:
    """Return min/avg/max BPM values from ``hr_series``."""
    bpm_values = [int(p.get("bpm", 0)) for p in hr_series if p.get("bpm")]
    if not bpm_values:
        return {"min": 0, "avg": 0, "max": 0}
    return {
        "min": min(bpm_values),
        "avg": int(statistics.mean(bpm_values)),
        "max": max(bpm_values),
    }


def calc_round_metrics(hr_series: list[dict]) -> dict[str, dict]:
    """Return per-round heart rate metrics.

    ``hr_series`` may contain enriched samples including ``round`` and
    ``status`` fields.  When present, these are used to segment the data and to
    derive recovery heart-rate values from continuous rest-period samples.  The
    legacy behaviour of deriving round boundaries from
    ``FightControl/data/round_status.json`` is preserved as a fallback when such
    fields are absent.  If that fallback fails, boundaries are derived directly
    from the series, covering everything from the first sample at ``0`` seconds
    to the last sample available.
    """

    def _get_seconds(point: dict) -> float | None:
        for key in ("seconds", "time"):
            if key in point:
                try:
                    return float(point[key])
                except (TypeError, ValueError):
                    return None
        return None

    enriched: list[tuple[int, str, float, int, str | None]] = []
    plain: list[tuple[float, int, str | None]] = []
    for p in hr_series:
        sec = _get_seconds(p)
        if sec is None:
            continue
        try:
            bpm = int(p.get("bpm", 0))
        except (TypeError, ValueError):
            continue
        zone = p.get("zone")
        if "round" in p and "status" in p:
            try:
                rnd = int(p.get("round"))
            except (TypeError, ValueError):
                rnd = None
            status = str(p.get("status", "")).upper()
            if rnd is not None and status:
                enriched.append((rnd, status, sec, bpm, zone))
                continue
        plain.append((sec, bpm, zone))

    if enriched:
        rounds: dict[int, dict[str, list]] = {}
        for rnd, status, sec, bpm, zone in enriched:
            bucket = rounds.setdefault(rnd, {"active": [], "rest": []})
            if status == "RESTING":
                bucket["rest"].append((sec, bpm))
            else:
                bucket["active"].append((sec, bpm, zone))

        metrics: dict[str, dict] = {}
        for rnd in sorted(rounds):
            active = sorted(rounds[rnd]["active"])
            rest = sorted(rounds[rnd]["rest"])
            peak = max((b for _, b, _ in active), default=0)

            zone_counts: dict[str, int] = {}
            for _, _, z in active:
                if z:
                    zone_counts[z] = zone_counts.get(z, 0) + 1
            total_samples = len(active) if active else 1
            zone_percentages = {z: c / total_samples for z, c in zone_counts.items()}

            recovery = 0
            if rest:
                start = rest[0][0]
                target = start + 60
                recovery = next((b for s, b in rest if s >= target), rest[-1][1])

            metrics[f"round_{rnd}"] = {
                "peak_hr": peak,
                "recovery_hr": recovery,
                "zone_percentages": zone_percentages,
            }
        return metrics

    # Fallback to legacy behaviour using round configuration
    series = sorted(plain)
    bounds: list[tuple[float, float]] = []
    rest = 60
    try:
        status = round_status()
        total = int(status.get("total_rounds", 0))
        duration = int(status.get("duration", 0))
        rest = int(status.get("rest", rest))
        if total and duration:
            from round_summary import _round_boundaries

            bounds = _round_boundaries(total, duration, rest)
    except Exception:
        bounds = []

    if not bounds:
        if not series:
            return {}
        last = series[-1][0]
        bounds = [(0, last + 1)]

    metrics: dict[str, dict] = {}
    for idx, (start, end) in enumerate(bounds, start=1):
        active = [(s, b, z) for s, b, z in series if start <= s < end]
        peak = max((b for _, b, _ in active), default=0)

        zone_counts: dict[str, int] = {}
        for _, _, zone in active:
            if zone:
                zone_counts[zone] = zone_counts.get(zone, 0) + 1
        dur = end - start if end > start else 1
        zone_percentages = {z: c / dur for z, c in zone_counts.items()}

        recovery_target = end + rest
        recovery = next((b for s, b, _ in series if s >= recovery_target), 0)

        metrics[f"round_{idx}"] = {
            "peak_hr": peak,
            "recovery_hr": recovery,
            "zone_percentages": zone_percentages,
        }

    return metrics


def build_session_summary(session_dir: str | Path) -> dict:
    """Create ``session_summary.json`` in ``session_dir``."""
    session_dir = Path(session_dir)

    # Load HR series if available
    try:
        hr_series = json.loads((session_dir / "hr_data.json").read_text(encoding="utf-8"))
    except Exception:
        hr_series = []

    summary = {
        "tags": load_tags(session_dir),
        "time_in_zones": calc_time_in_zones(hr_series),
        "bpm_stats": calc_bpm_stats(hr_series),
        "round_results": {},
        "round_metrics": calc_round_metrics(hr_series),
    }

    try:
        summary["round_results"] = round_status()
    except Exception:
        pass

    (session_dir / "session_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

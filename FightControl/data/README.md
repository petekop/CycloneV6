# FightControl Data

This directory holds runtime JSON and text files used by the FightControl system.

## round_status.json

The ``round_status.json`` file describes the state of the current round timer.
When a bout is first armed via the ``/enter-fighters`` endpoint the file is
created with ``status: "WAITING"`` and does **not** include a ``start_time``
field.  The timestamp is added only once the round or rest period actually
begins.  Consumers should therefore expect ``start_time`` to be absent while the
system is waiting to start.

## Session summaries

After a bout finishes, Cyclone aggregates data for each fighter and writes a
`session_summary.json` file into that fighter's session folder under
`FightControl/fighter_data/<fighter>/<date>/<bout_name>/`.

The file combines:

- `tags` – coach notes extracted from `coach_notes.csv`.
- `time_in_zones` – total seconds spent in each heart‑rate zone (from `hr_data.json`).
- `bpm_stats` – minimum, average and maximum BPM for the session.
- `round_results` – final round information copied from `FightControl/data/round_status.json`.

Example:

```json
{
  "tags": ["Jab", "Cross"],
  "time_in_zones": {"blue": 30, "orange": 90},
  "bpm_stats": {"min": 60, "avg": 75, "max": 120},
  "round_results": {"round": 3, "duration": 120, "rest": 60, "status": "ENDED"}
}
```

This summary sits next to `hr_data.json` and `coach_notes.csv` for future
analysis.

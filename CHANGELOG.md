## Unreleased

- Added `tests/test_round_manager.py` covering `read_bpm` handling of mixed formats.
- Fixed imports in `create_fighter_round_folders.py` for standalone and package execution.
- Introduced `/enter-fighters` endpoint for selecting fighters.
- Heart rate logger now reads `CYCLONE_BLUE_H10_MAC` to configure the Polar H10 MAC address.
- Added smoothing options, peak tracking, and recovery logging for BPM data (`tests/test_utils_bpm.py`, `tests/test_zone_model.py`).
- Added `tools/migrate_current_fight.py` to convert old `red`/`blue` keys in `current_fight.json` to `red_fighter`/`blue_fighter`.
- Round setup now pre-creates `hr_log.csv` in each fighter's round folder and runs during fight setup for consistency.

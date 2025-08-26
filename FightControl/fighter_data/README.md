This directory stores fighter-specific data generated during bouts, such as heart rate logs and coach notes. The contents are created automatically by Cyclone during operation and are intentionally ignored by Git.

## Generating sample data
1. Ensure `FightControl/data/current_fight.json` and `FightControl/data/current_round.txt` contain the fighters and round you wish to simulate.
2. Run the helper script:

```bash
python FightControl/create_fighter_round_folders.py
```

This creates the necessary folder structure and placeholder CSV files for the fighters listed in `current_fight.json`.

## Downloading sample data
If you need sample datasets, contact the project maintainers or obtain them from trusted sources, then place the files inside this folder.

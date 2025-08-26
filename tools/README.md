# Tools

Utility scripts that support development and maintenance of the Cyclone project.

- `csv_to_json.py` – Convert a CSV file to JSON. Optionally specify column indices to treat as numeric.
- `codex.py` – Command-line interface for generating code snippets using Google’s Generative AI.
- `check_static_refs.py` – Warn about missing or unused files in `FightControl/static` compared to template references.
- `migrate_current_fight.py` – Update `FightControl/data/current_fight.json` to use `red_fighter` and `blue_fighter` keys.
- `playsound.py` – Minimal stub to avoid external sound playback dependency during testing.

Each script is executable as a module, for example:

```bash
python -m tools.csv_to_json input.csv output.json
python -m tools.codex "create a flask route"
python -m tools.migrate_current_fight
```

These utilities can be packaged as installable command-line tools using `setuptools` entry points in a future release.

# Codex CLI Agent (Patched for SSL in Codex Universal)

## Setup

1. Copy `.env.example` to `.env` and set your API key:
   GOOGLE_API_KEY=your_key_here

   Alternatively export it as an environment variable before running the
   scripts:
   ```bash
   export GOOGLE_API_KEY=your_key_here
   ```

2. Launch the Cyclone server:
   ```powershell
   ./scripts/launch_cyclone.ps1
   ```

## Notes

- Set `CODEX_INSECURE_SSL=1` if you need to bypass SSL verification in restricted containers.
- Output is saved using the `--output filename.py` argument.

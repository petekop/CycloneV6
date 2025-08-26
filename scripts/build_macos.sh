#!/usr/bin/env bash
set -euo pipefail

# Build a macOS Application bundle for Cyclone using PyInstaller.
# The resulting app will be placed under dist/Cyclone.app

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

pyinstaller --windowed --name Cyclone.app launch_cyclone_macos.py

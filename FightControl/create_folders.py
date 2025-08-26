from pathlib import Path

from FightControl.create_fighter_round_folders import create_round_folder_for_fighter
from FightControl.fight_utils import parse_round_format, safe_filename
from paths import BASE_DIR
from utils.files import open_utf8

# Date: 2025-07-19

"""Utility for creating CAMSERVER video capture folders.

This module provides :func:`create_fight_structure` which prepares the
directory tree used by the CAMSERVER capture system. The folder tree is
only for storing captured video files. Round-level CSV logs such as
``coach_notes.csv`` are stored in the fighter data directories created via
``create_fighter_round_folders``.
"""

import os
from datetime import datetime


def create_fight_structure(red_name, blue_name, round_format):
    """Create the folder tree for video capture.

    Parameters
    ----------
    red_name, blue_name: str
        Fighter names used to name the root folder.
    round_format: str
        Format like ``"3x2"`` indicating how many rounds to create.

    Returns
    -------
    tuple[str, str]
        The full path of the created folder and a status message.
    """
    safe_red = safe_filename(red_name).upper()
    safe_blue = safe_filename(blue_name).upper()
    fight_date = datetime.now().strftime("%Y-%m-%d")
    fight_folder = f"{safe_red}_RED_{safe_blue}_BLUE"
    base_path = (BASE_DIR / "CAMSERVER" / fight_date / fight_folder).resolve()
    # 🔐 Ensure the resolved path remains within the project base directory
    base_dir = BASE_DIR.resolve()
    if os.path.commonpath([str(base_dir), str(base_path)]) != str(base_dir):
        return "❌ Failed to create folder", "Path escapes base directory"

    try:
        round_count, _ = parse_round_format(round_format)
        for i in range(1, round_count + 1):
            round_name = f"round_{i}"
            for cam in ["main_cam", "left_cam", "right_cam", "overhead_cam"]:
                path = base_path / round_name / cam
                path.mkdir(parents=True, exist_ok=True)
            create_round_folder_for_fighter(red_name, fight_date, round_name)
            create_round_folder_for_fighter(blue_name, fight_date, round_name)

        # Track the active round for camera capture. Not used for HR logs.
        with open_utf8(base_path / "current_round.txt", "w") as f:
            f.write("round_1")

        return str(base_path), "✅ Folder Structure Created"
    except ValueError as e:
        return "❌ Invalid round format", str(e)
    except Exception as e:
        return "❌ Failed to create folder", str(e)

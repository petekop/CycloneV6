"""Wrapper around the project-wide :func:`utils.play_audio` helper.

This module resolves filenames relative to ``FightControl/audio`` and delegates
playback to the cached simpleaudio-based implementation in :mod:`utils`.
"""

from pathlib import Path

from utils import play_audio as _play_audio

_AUDIO_DIR = Path(__file__).resolve().parent / "audio"


def play_audio(path, channel="fx"):
    """Play an audio file ``path``.

    ``path`` may be an absolute path or a filename relative to the
    FightControl audio directory. ``channel`` is retained for backward
    compatibility but unused.
    """
    p = Path(path)
    if not p.is_absolute():
        p = _AUDIO_DIR / p
    print(f"🔊 Playing {p} [{channel}]")
    _play_audio(str(p))


def stop_audio():  # pragma: no cover - compatibility shim
    """Stop playback (no-op)."""
    pass


__all__ = ["play_audio", "stop_audio"]

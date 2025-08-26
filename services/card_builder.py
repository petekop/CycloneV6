from __future__ import annotations

"""Utilities for composing fighter cards using Pillow.

This module provides :func:`compose_card` which layers a card background,
front template, fighter headshot, flag and key statistics into a single
PNG image.  The function is deliberately defensive so that missing assets
simply result in a partially populated card instead of raising errors.
"""

from pathlib import Path
from typing import Dict, Optional
import io

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
FRONT_TEMPLATE = BASE_DIR / "FightControl" / "static" / "images" / "cyclone_card_front_logo.png"
FLAGS_DIR = BASE_DIR / "FightControl" / "static" / "flags"


def _load_flag(country: str) -> Optional[Image.Image]:
    """Return an RGBA flag image for ``country`` if available."""

    if not country:
        return None
    country = country.lower()
    # Try SVG first using cairosvg if available
    svg_path = FLAGS_DIR / f"{country}.svg"
    if svg_path.exists():
        try:
            import cairosvg

            png_bytes = cairosvg.svg2png(url=str(svg_path))
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
    png_path = FLAGS_DIR / f"{country}.png"
    if png_path.exists():
        try:
            return Image.open(png_path).convert("RGBA")
        except Exception:
            pass
    return None


def _paste_headshot(img: Image.Image, dir_path: Path) -> None:
    """Paste a circular headshot onto ``img`` if ``photo.png`` exists."""

    photo = dir_path / "photo.png"
    if not photo.exists():
        return
    try:
        head = Image.open(photo).convert("RGBA")
        size = 180
        head = head.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        head.putalpha(mask)
        img.paste(head, (20, 20), head)
    except Exception:
        pass


def compose_card(
    back_img: str | Path,
    out_png: str | Path,
    name: str | None,
    country: str | None,
    stats: Dict[str, float],
) -> str:
    """Compose a fighter card image and save to ``out_png``.

    Parameters mirror the previous ``compose_card_png`` helper for
    compatibility.  ``back_img`` serves as the base background, ``name`` and
    ``country`` populate text and flag overlays while ``stats`` are rendered
    as simple key/value pairs.  The function returns the path to the written
    PNG file.
    """

    back = Path(back_img)
    out = Path(out_png)

    try:
        img = Image.open(back).convert("RGBA")
    except Exception:
        img = Image.new("RGBA", (600, 400), (0, 0, 0, 255))

    # Paste headshot if available
    _paste_headshot(img, out.parent)

    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    if name:
        draw.text((220, 40), name, fill="white", font=font)

    flag_img = _load_flag(country or "")
    if flag_img is not None:
        flag_img = flag_img.resize((80, 80))
        img.paste(flag_img, (220, 70), flag_img)

    y = 160
    for key, val in stats.items():
        draw.text((220, y), f"{key}: {val}", fill="white", font=font)
        y += 20

    # Overlay front template if available
    try:
        front = Image.open(FRONT_TEMPLATE).convert("RGBA")
        if front.size != img.size:
            front = front.resize(img.size)
        img = Image.alpha_composite(img, front)
    except Exception:
        pass

    img.save(out)
    return str(out)


__all__ = ["compose_card"]

"""OPTIM2FULL Phase 2b Ord 1 — Wayfinding site wrapper around ``spm_behaviour``.

Thin facade: ``spm_behaviour(QDP, PG, sT=…)`` with wayfinding title / goal marker.
Core multi-panel draw + optional MP4 live in ``spm_behaviour.py``.

Re-exports colour / ``spm_show_x`` RGB / 3D style helpers so existing
``dem_drone_vi_plot_true_*`` imports keep working.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from python_src.toolbox.DEM.spm_behaviour import (
    _spm_colour,
    _spm_show_x_rgb,
    _style_3d_matlabish,
    spm_behaviour,
)

__all__ = [
    "dem_drone_vi_plot_wayfinding",
    "_spm_colour",
    "_spm_show_x_rgb",
    "_style_3d_matlabish",
]


def dem_drone_vi_plot_wayfinding(
    QDP: dict[str, Any],
    PG: dict[str, Any],
    sT: Any = None,
    *,
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "Wayfinding",
) -> Path | None:
    """Wayfinding final-frame PNG via general ``spm_behaviour`` (optional ``sT``)."""
    out = spm_behaviour(
        QDP,
        PG,
        sT,
        save_png=save_png,
        png_path=png_path,
        fig_title=fig_title,
    )
    return out.get("png")

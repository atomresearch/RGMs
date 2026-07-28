"""OPTIM2FULL Phase 2b Ord 2 — Active-inference behaviour plot.

``DEM_drone_vi.m`` ~L459–464: ``spm_behaviour(QDP)`` after surveillance VB
(``vb_1`` / F5). Same local behaviour body as Wayfinding; **no** ``sT`` goal
overlay. Movie / ``getframe`` / ``ButtonDownFcn`` SKIP; full ``t``-loop then
one PNG (matches MATLAB capture end-state).

Reuses ``dem_drone_vi_plot_wayfinding`` with ``sT=None``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import (
    dem_drone_vi_plot_wayfinding,
)


def dem_drone_vi_plot_active_inference(
    QDP: dict[str, Any],
    PG: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "Active inference",
) -> Path | None:
    """Draw final-frame active-inference behaviour figure; optionally save PNG."""
    return dem_drone_vi_plot_wayfinding(
        QDP,
        PG,
        None,
        save_png=save_png,
        png_path=png_path,
        fig_title=fig_title,
    )

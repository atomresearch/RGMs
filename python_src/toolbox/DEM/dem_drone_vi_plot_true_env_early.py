"""OPTIM2FULL Phase 2b Ord 4 — early true-environment plot (pre-generate).

``DEM_drone_vi.m`` ~L90–109: ``spm_show_x(MAP,…)`` titled ``True environment``
plus 3D ``plot3`` of classes from ``W``. Authority: F0 ``MAP``/``W``/sizes.

Reuses colour / ``spm_show_x`` RGB / 3D styling from
``dem_drone_vi_plot_wayfinding`` (true-scene mid-right polish).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from python_src.spm_combinations import spm_combinations
from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import (
    _spm_colour,
    _spm_show_x_rgb,
    _style_3d_matlabish,
)


def _as_dense_col(x: Any) -> np.ndarray:
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray(), dtype=np.float64).reshape(-1, order="F")
    a = np.asarray(x, dtype=np.float64)
    return a.reshape(-1, order="F")


def _map_to_cells(MAP: Any, Nc: int) -> list[Any]:
    """F0 ``MAP`` (Np cell of Nc×1 one-hots) → list for ``_spm_show_x_rgb``."""
    if isinstance(MAP, np.ndarray) and MAP.dtype == object:
        cells = list(MAP.reshape(-1, order="F"))
    elif isinstance(MAP, (list, tuple)):
        cells = list(MAP)
    else:
        raise TypeError(f"MAP must be cell-like, got {type(MAP)}")
    out: list[Any] = []
    for c in cells:
        v = _as_dense_col(c)
        if v.size < Nc:
            pad = np.zeros(Nc, dtype=np.float64)
            pad[: v.size] = v
            v = pad
        out.append(v[:Nc])
    return out


def dem_drone_vi_plot_true_env_early(
    MAP: Any,
    W: Any,
    *,
    Nx: int,
    Ny: int,
    Nz: int,
    Nc: int,
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "Active inference",
) -> Path | None:
    """Draw early true-environment 2D+3D figure; optionally save PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    Nx = int(Nx)
    Ny = int(Ny)
    Nz = int(Nz)
    Nc = int(Nc)

    cells = _map_to_cells(MAP, Nc)
    I = _spm_show_x_rgb(cells, Nx, Ny, Nz)

    W_arr = np.asarray(W, dtype=np.float64)
    if W_arr.shape != (Nx, Ny, Nz):
        # MATLAB W is Nx×Ny×Nz; tolerate Fortran flatten rebuild
        W_arr = W_arr.reshape((Nx, Ny, Nz), order="F")
    W_flat = W_arr.reshape(-1, order="F")

    XYZ = spm_combinations(np.asarray([Nx, Ny, Nz], dtype=np.float64))

    fig = plt.figure(figsize=(10, 10), dpi=120)
    fig.suptitle(fig_title, fontsize=12)
    gs = fig.add_gridspec(4, 6, hspace=0.35, wspace=0.35)

    # subplot(2,2,2) — top-right 2D true environment
    ax2 = fig.add_subplot(gs[0:2, 3:6])
    ax2.imshow(
        np.clip(I, 0.0, 1.0),
        origin="upper",
        extent=(0.5, Ny + 0.5, Nx + 0.5, 0.5),
        interpolation="nearest",
    )
    ax2.set_aspect("equal")
    ax2.set_title("True environment")

    # subplot(4,2,6) — mid-right 3D (data-channel swap like wayfinding true)
    ax3 = fig.add_subplot(gs[2, 3:6], projection="3d")
    _cls_draw_order = (3, 4, 5, 2, 7, 6, 8)
    _ms_true = 6.0  # landed true-scene mid-right polish (vs MATLAB MarkerSize 32)
    for s_cls in _cls_draw_order:
        if s_cls < 2 or s_cls > Nc:
            continue
        i_idx = np.where(np.round(W_flat) == s_cls)[0]
        if i_idx.size == 0:
            continue
        oh = np.zeros(Nc, dtype=np.float64)
        oh[s_cls - 1] = 1.0
        c = _spm_colour(oh)
        ax3.plot(
            XYZ[i_idx, 1],
            XYZ[i_idx, 0],
            XYZ[i_idx, 2],
            linestyle="none",
            marker=".",
            markersize=_ms_true,
            markerfacecolor=tuple(c.tolist()),
            markeredgecolor=tuple(c.tolist()),
            markeredgewidth=0.0,
        )
    # MATLAB loop is s=2:Nc sequential; also plot any class not in draw-order
    for s_cls in range(2, Nc + 1):
        if s_cls in _cls_draw_order:
            continue
        i_idx = np.where(np.round(W_flat) == s_cls)[0]
        if i_idx.size == 0:
            continue
        oh = np.zeros(Nc, dtype=np.float64)
        oh[s_cls - 1] = 1.0
        c = _spm_colour(oh)
        ax3.plot(
            XYZ[i_idx, 1],
            XYZ[i_idx, 0],
            XYZ[i_idx, 2],
            linestyle="none",
            marker=".",
            markersize=_ms_true,
            markerfacecolor=tuple(c.tolist()),
            markeredgecolor=tuple(c.tolist()),
            markeredgewidth=0.0,
        )
    _style_3d_matlabish(ax3, nx=Nx, ny=Ny, nz=Nz, z_pad=0.35)

    saved: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("png_path required when save_png=True")
        saved = Path(png_path)
        saved.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(saved, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return saved

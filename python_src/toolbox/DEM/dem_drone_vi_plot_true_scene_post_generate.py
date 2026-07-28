"""OPTIM2FULL Phase 2b Ord 6 — post-generate True scene (``spm_show_x``).

``DEM_drone_VI.m`` ~L392–394:

    subplot(2,2,2), hold off
    spm_show_x(Q,PG.Nx,PG.Ny,PG.Nz)
    title('True scene')

Authority: F1 ``Q`` + ``PG`` (pre-FSL assembled scene). Local ``spm_show_x``
loops all ``t``; static PNG is the **final** frame (T from ``size(Q,2)``).
No 3D ``plot3`` at this call site (unlike Ord 4).

Reuses ``_spm_show_x_rgb`` from ``dem_drone_vi_plot_wayfinding``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import _spm_show_x_rgb


def _as_dense_col(x: Any) -> np.ndarray:
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray(), dtype=np.float64).reshape(-1, order="F")
    a = np.asarray(x, dtype=np.float64)
    return a.reshape(-1, order="F")


def _unwrap_cell(x: Any) -> Any:
    while isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]
    if isinstance(x, np.ndarray) and x.dtype == object and x.size == 1:
        x = x.reshape(-1, order="F")[0]
    return x


def _pg_int(pg: dict[str, Any], key: str) -> int:
    return int(np.asarray(pg[key]).reshape(-1)[0])


def _q_column_cells(Q: Any, t_0based: int, Nc: int) -> list[np.ndarray]:
    """Extract MATLAB ``Q(:,t)`` as Np list of dense Nc-vectors for ``_spm_show_x_rgb``."""
    if isinstance(Q, np.ndarray) and Q.dtype == object and Q.ndim == 2:
        col = [Q[f, t_0based] for f in range(Q.shape[0])]
    elif isinstance(Q, (list, tuple)):
        # F1.pkl: list of Np rows, each a list of T cells
        col = []
        for row in Q:
            if isinstance(row, (list, tuple)):
                col.append(row[t_0based])
            elif isinstance(row, np.ndarray) and row.dtype == object:
                col.append(row.reshape(-1, order="F")[t_0based])
            else:
                if t_0based != 0:
                    raise IndexError("Q row is scalar cell but t>0")
                col.append(row)
    else:
        raise TypeError(f"Q must be cell-like Np×T, got {type(Q)}")

    out: list[np.ndarray] = []
    for c in col:
        v = _as_dense_col(_unwrap_cell(c))
        if v.size < Nc:
            pad = np.zeros(Nc, dtype=np.float64)
            pad[: v.size] = v
            v = pad
        out.append(v[:Nc])
    return out


def dem_drone_vi_plot_true_scene_post_generate(
    Q: Any,
    PG: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "Active inference",
    loop_all_t: bool = True,
) -> Path | None:
    """Draw post-generate ``True scene`` panel; optionally save PNG.

    When ``loop_all_t`` is True (default), mirrors MATLAB ``spm_show_x`` by
    drawing every column then keeping the last frame for the PNG.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Nx = _pg_int(PG, "Nx")
    Ny = _pg_int(PG, "Ny")
    Nz = _pg_int(PG, "Nz")
    Nc = _pg_int(PG, "Nc")

    if isinstance(Q, (list, tuple)) and len(Q) > 0 and isinstance(Q[0], (list, tuple)):
        T = len(Q[0])
    elif isinstance(Q, np.ndarray) and Q.dtype == object and Q.ndim == 2:
        T = int(Q.shape[1])
    else:
        T = 1

    fig = plt.figure(figsize=(10, 10), dpi=120)
    fig.suptitle(fig_title, fontsize=12)
    ax = fig.add_subplot(2, 2, 2)

    t_range = range(T) if loop_all_t else [T - 1]
    I = None
    for t in t_range:
        cells = _q_column_cells(Q, t, Nc)
        I = _spm_show_x_rgb(cells, Nx, Ny, Nz)
        ax.clear()
        ax.imshow(
            np.clip(I, 0.0, 1.0),
            origin="upper",
            extent=(0.5, Ny + 0.5, Nx + 0.5, 0.5),
            interpolation="nearest",
        )
        ax.set_aspect("equal")
        ax.set_title("True scene")

    saved: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("png_path required when save_png=True")
        saved = Path(png_path)
        saved.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(saved, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return saved

"""OPTIM2FULL Phase 2b Ord 3 — ``spm_show_RGM`` plot (static multi-panel).

Faithful thin port of ``spm-main/toolbox/DEM/spm_show_RGM.m`` (+ local
``spm_get_O``). ``DEM_drone_vi.m`` ~L454–455: ``spm_show_RGM(RDP)`` after
surveillance VB (``vb_1`` / F5).

Header ``Nt``/``MOVIE`` args are unused in the ``.m`` body — static figure
only (no ``getframe`` / movie). Do **not** reuse Atari plot helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from python_src.spm_cat import spm_cat
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size


def _dense(x: Any) -> np.ndarray:
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray(), dtype=np.float64)
    a = np.asarray(x)
    if a.dtype == object:
        if a.ndim == 0:
            return _dense(a.item())
        # unexpected object array — densify elements if possible
        return np.asarray(a, dtype=np.float64)
    return np.asarray(a, dtype=np.float64)


def _spm_get_O(rdp: dict[str, Any]) -> list[Any]:
    """Local ``spm_get_O`` from ``spm_show_RGM.m``."""
    try:
        q = rdp["Q"]["O"]
        if q is None:
            o_list: list[Any] = []
        elif isinstance(q, (list, tuple)):
            o_list = list(q)
        else:
            o_list = [q]
    except Exception:
        o_list = []
    o_list.append(rdp["O"])
    return o_list


def _as_cell_matrix(level: Any) -> np.ndarray:
    """Python nested list / cell → 2-D object ndarray (MATLAB cell matrix).

    Each cell is reshaped to a column vector so ``spm_cat`` matches MATLAB
    (F5 ``Q.O`` cells arrive as 1-D ``(n,)`` rather than ``(n,1)``).
    """
    if isinstance(level, np.ndarray) and level.dtype == object and level.ndim == 2:
        arr = level
        out = np.empty(arr.shape, dtype=object)
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                out[i, j] = np.asarray(arr[i, j], dtype=np.float64).reshape(-1, 1)
        return out
    if not isinstance(level, (list, tuple)):
        out = np.empty((1, 1), dtype=object)
        out[0, 0] = np.asarray(level, dtype=np.float64).reshape(-1, 1)
        return out
    nrows = len(level)
    if nrows == 0:
        return np.empty((0, 0), dtype=object)
    row0 = level[0]
    if isinstance(row0, (list, tuple)):
        ncols = len(row0)
        arr = np.empty((nrows, ncols), dtype=object)
        for i, row in enumerate(level):
            for j, cell in enumerate(row):
                arr[i, j] = np.asarray(cell, dtype=np.float64).reshape(-1, 1)
        return arr
    # column vector of cells
    arr = np.empty((nrows, 1), dtype=object)
    for i, cell in enumerate(level):
        arr[i, 0] = np.asarray(cell, dtype=np.float64).reshape(-1, 1)
    return arr


def _index_cell_rows(cell_mat: np.ndarray, i_1based: np.ndarray) -> np.ndarray:
    """MATLAB ``Y(iD,:)`` on a cell matrix."""
    idx = np.asarray(i_1based, dtype=np.int64).ravel()
    return cell_mat[idx - 1, :]


def _image_scaled(ax: Any, q: np.ndarray) -> None:
    """MATLAB ``image((1 - Q)*64)`` with classic jet scaling."""
    img = (1.0 - np.asarray(q, dtype=np.float64)) * 64.0
    ax.imshow(img, cmap="jet", vmin=0.0, vmax=64.0, aspect="auto", interpolation="nearest")


def _imagesc(ax: Any, m: np.ndarray) -> None:
    """MATLAB ``imagesc`` (autoscale) — hot matches yellow bg / dark marks on RGM PNG."""
    ax.imshow(
        np.asarray(m, dtype=np.float64),
        cmap="hot",
        aspect="auto",
        interpolation="nearest",
    )


def _spm_spy_plot(ax: Any, x: np.ndarray, markersize: float = 8.0) -> None:
    """Thin ``spm_spy`` (``spm-main/spm_spy.m``) for Ord 3 if ``size(B,1)>128``."""
    x = np.asarray(x, dtype=np.float64)
    m = float(np.max(x)) if x.size else 1.0
    if m <= 0:
        m = 1.0
    ax.cla()
    g = 8
    for p in range(g, 0, -1):
        ii, jj = np.where(x > m / float(p))
        # MATLAB plot(j,i,...) with axis ij
        ax.plot(
            jj + 1.0,
            ii + 1.0,
            linestyle="none",
            marker=".",
            markersize=float(markersize),
            color=(1.0, 1.0, 1.0) * ((p - 1) / float(g)),
        )
    nr, nc = x.shape[0], x.shape[1]
    ax.set_xlim(1.0, float(nc))
    ax.set_ylim(float(nr), 1.0)  # axis ij
    ax.set_aspect("equal")


def dem_drone_vi_plot_rgm(
    RDP: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "RGM",
) -> Path | None:
    """Draw static ``spm_show_RGM(RDP)`` figure; optionally save PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    o_levels = _spm_get_O(RDP)
    try:
        y_q = RDP["Q"]["Y"]
        if isinstance(y_q, (list, tuple)):
            y_levels: list[Any] = list(y_q)
        else:
            y_levels = [y_q]
    except Exception:
        y_levels = []
    y_levels.append(RDP["Y"])

    nm = len(o_levels)
    # Build cell matrices once
    y_mats = [_as_cell_matrix(y_levels[k]) for k in range(nm)]
    o_mats = [_as_cell_matrix(o_levels[k]) for k in range(nm)]

    nf = int(spm_MDP_size(RDP)[0])

    fig = plt.figure(figsize=(10, 12), dpi=120)
    fig.suptitle(fig_title, fontsize=12)
    nrows = nm + 3

    # --- highest states (subplot(Nm+3,2,1)) ---
    ax = fig.add_subplot(nrows, 2, 1)
    x_field = RDP["X"]
    if isinstance(x_field, (list, tuple)):
        x_rows = len(x_field)
    elif isinstance(x_field, np.ndarray) and x_field.dtype == object:
        x_rows = int(x_field.shape[0]) if x_field.ndim >= 1 else 1
    else:
        x_rows = 1
    if x_rows == 1:
        qx = _dense(spm_cat(list(x_field) if isinstance(x_field, (list, tuple)) else x_field))
    else:
        qx = _dense(spm_cat(x_field))
    _image_scaled(ax, qx)
    ax.set_title(f"Posterior (states) level {nm}", fontsize=12)

    # --- transitions ---
    if nf > 1:
        for f in range(1, nf + 1):
            try:
                b = spm_dir_norm(RDP["b"][f - 1])
            except Exception:
                b = RDP["B"][f - 1]
            b = _dense(b)
            if b.ndim == 2:
                bb = b > (1.0 / 16.0)
            else:
                bb = np.sum(b, axis=2) > (1.0 / 16.0)
            ax = fig.add_subplot(nrows, 2 * nf, nf + f)
            if bb.shape[0] > 128:
                _spm_spy_plot(ax, bb.astype(np.float64), 8.0)
            else:
                _imagesc(ax, 1.0 - bb.astype(np.float64))
                ax.set_aspect("equal")
            ax.set_title(f"Transitions (f = {f})", fontsize=12)
    else:
        try:
            b = spm_dir_norm(RDP["b"][0])
        except Exception:
            b = RDP["B"][0]
        b = _dense(b)
        nu = int(b.shape[2]) if b.ndim >= 3 else 1
        if nu < 4:
            for u in range(1, nu + 1):
                ax = fig.add_subplot(nrows, 2 * nu, nu + u)
                bu = b[:, :, u - 1] if b.ndim >= 3 else b
                if bu.shape[0] > 128:
                    _spm_spy_plot(ax, (bu > (1.0 / 16.0)).astype(np.float64), 8.0)
                else:
                    _imagesc(ax, 1.0 - bu)
                    ax.set_aspect("equal")
                ax.set_title(f"Transitions (u = {u})", fontsize=12)
        else:
            ax = fig.add_subplot(nrows, 2, 2)
            if b.ndim >= 3:
                bb = np.sum(b, axis=2) > (1.0 / 16.0)
            else:
                bb = b > (1.0 / 16.0)
            if bb.shape[0] > 128:
                _spm_spy_plot(ax, bb.astype(np.float64), 8.0)
            else:
                _imagesc(ax, 1.0 - bb.astype(np.float64))
                ax.set_aspect("equal")
            ax.set_title(f"Transitions (Nu = {nu})", fontsize=12)

    # --- predictive posteriors over levels ---
    mdp: Any = RDP
    for n in range(1, nm + 1):
        L = nm - n + 1  # 1-based level index into y_mats
        if L > 1:
            nested = mdp["MDP"]
            i_d = _dense(spm_cat(nested["id"]["D"])).ravel()
            i_e = _dense(spm_cat(nested["id"]["E"])).ravel()
        else:
            i_d = np.arange(1, y_mats[L - 1].shape[0] + 1, dtype=np.float64)
            i_e = np.asarray([], dtype=np.float64)

        ax = fig.add_subplot(nrows, 2, (n - 1) * 2 + 3)
        q = _dense(spm_cat(_index_cell_rows(y_mats[L - 1], i_d)))
        _image_scaled(ax, q)
        ax.set_title(f"Predictive posterior (states) level {L}", fontsize=12)

        if L > 1 and i_e.size > 0:
            ax = fig.add_subplot(nrows, 2, (n - 1) * 2 + 4)
            q = _dense(spm_cat(_index_cell_rows(y_mats[L - 1], i_e)))
            _image_scaled(ax, q)
            ax.set_title(f"Predictive posterior (paths) level {L}", fontsize=12)

        if n < nm:
            mdp = mdp["MDP"]

    # --- lowest level observed / predicted ---
    x_obs = 1.0 - _dense(spm_cat(o_mats[0]))
    p_pred = 1.0 - _dense(spm_cat(y_mats[0]))

    ax = fig.add_subplot(nrows, 1, nm + 2)
    _imagesc(ax, p_pred)
    ax.set_title("Predicted", fontsize=10)

    ax = fig.add_subplot(nrows, 1, nm + 3)
    _imagesc(ax, x_obs)
    # title uses final ``mdp`` after loop (lowest level struct)
    if isinstance(mdp, dict) and "S" in mdp:
        ax.set_title("Stimulus", fontsize=10)
    else:
        ax.set_title("Observed", fontsize=10)

    fig.tight_layout(rect=(0, 0, 1, 0.97))

    saved: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("png_path required when save_png=True")
        saved = Path(png_path)
        saved.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(saved, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return saved

"""General ``spm_behaviour`` figure + optional movie (MATLAB local in ``DEM_drone_VI.m``).

Faithful thin port of local ``spm_behaviour`` + ``spm_show_x`` + ``spm_colour``
(~L977–1167). Runs the full ``for t = 1:T`` multi-panel draw loop
(2D inferred/true, 3D inferred/true, Depth/Class/Vision).

Outputs (optional):
- final-frame PNG (``save_png``) — prior OPTIM2FULL plot-site contract
- full-figure MP4 (``save_mp4``) — MATLAB ``MOV(t)=getframe`` product analogue
  (file playback; no ``ButtonDownFcn`` / SPM GUI)

Optional ``sT`` overlays a goal marker after the loop (wayfinding site only).
Site wrappers (``dem_drone_vi_plot_wayfinding`` / ``…_active_inference``) stay thin.

Inferred 3D mirrors MATLAB empty-``plot3`` accumulate semantics. Do **not**
reuse ``dem_atariiii_plot_*``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from python_src.spm_combinations import spm_combinations
from python_src.toolbox.DEM.spm_index import spm_index
from python_src.toolbox.DEM.spm_sub2ind import spm_sub2ind


def _spm_colour(O: Any) -> np.ndarray:
    """Local ``spm_colour`` from ``DEM_drone_vi.m`` (~L830)."""
    o = np.asarray(O, dtype=np.float64).reshape(-1, order="F")
    MAP = np.asarray(
        [
            [0, 0, 0],
            [0, 204, 204],
            [0, 153, 0],
            [51, 102, 0],
            [204, 204, 0],
            [255, 229, 204],
            [204, 102, 0],
            [255, 0, 0],
        ],
        dtype=np.float64,
    ) / 255.0
    MAP = MAP[: int(o.size), :]
    rgb = MAP.T @ o  # MAP*O in MATLAB with O column → (3,)
    return np.minimum(rgb, 1.0)


def _nice_tick_step(span: float) -> float:
    """Nice tick step for a 1-D span (MATLAB-like auto ticks, not hardcoded 5).

    Picks a {1,2,5}×10^k step so ``span/step`` is near 3 intervals. For
    ``Nr=16`` this yields step ``5`` → ticks ``5/10/15``, matching the
    captured MATLAB PNG (MATLAB does not hardcode 5; it auto-ticks).
    """
    import math

    span = float(abs(span))
    if span <= 0:
        return 1.0
    raw = span / 3.0
    exp = int(math.floor(math.log10(raw))) if raw > 0 else 0
    candidates: list[float] = []
    for e in (exp - 1, exp, exp + 1):
        base = 10.0**e
        for m in (1.0, 2.0, 5.0):
            candidates.append(m * base)
    best = float(candidates[0])
    best_score = float("inf")
    for step in candidates:
        if step <= 0:
            continue
        intervals = span / step
        score = abs(intervals - 3.0)
        if intervals < 2.0 or intervals > 5.5:
            score += 10.0
        if score < best_score:
            best_score = score
            best = float(step)
    return best


def _apply_imagesc_ticks(ax: Any, n: int) -> None:
    """Tick locators for square ``imagesc``-class panels of size ``n``."""
    from matplotlib.ticker import MultipleLocator

    step = _nice_tick_step(float(n))
    ax.xaxis.set_major_locator(MultipleLocator(step))
    ax.yaxis.set_major_locator(MultipleLocator(step))


def _style_3d_matlabish(
    ax: Any, *, nx: int, ny: int, nz: int, z_pad: float = 0.0
) -> None:
    """Finish 3D panels after plotting ``scatter(y_data, x_data, z)``.

    - Data-channel swap is already in the scatter args (plot-X ← data-Y,
      plot-Y ← data-X); this helper does **not** swap again.
    - With ``view(3)``-class ``azim=-37.5``: the ground axis toward the
      **left** of the subplot reads L→R **descending** (30,20,10); the
      ground axis toward the **right** reads L→R **ascending** (10,20,30).
    - **Z box aspect** follows MATLAB ``axis image`` proportions: z data
      span ``nz`` vs ground ``nx``/``ny`` (e.g. 8 vs 32) so the z-axis is
      visually short (ticks like 2 and 6 sit close). Data values unchanged.
    - ``z_pad`` extends zlim slightly above ``nz`` so a drone marker at z=Nz
      is not clipped (display only).
    - Limits applied **last** so ``set_box_aspect`` / ``view_init`` cannot
      clobber them.
    """
    from matplotlib.ticker import FixedLocator, MultipleLocator

    ax.view_init(elev=30.0, azim=-37.5)
    # Equal data-unit aspect (MATLAB axis image): z span is much smaller
    # than ground, so the plotted z-axis looks shorter — not a data rescales.
    z_top = float(nz) + float(z_pad)
    ax.set_box_aspect((float(ny), float(nx), z_top if z_top > 0 else float(nz)))
    # Left ground axis (plot-X / data-Y): descending L→R.
    ax.set_xlim(float(ny), 0.0)
    # Right ground axis (plot-Y / data-X): ascending L→R.
    ax.set_ylim(0.0, float(nx))
    ax.set_zlim(0.0, z_top if z_top > 0 else float(nz))
    step = _nice_tick_step(float(max(nx, ny)))
    ax.xaxis.set_major_locator(MultipleLocator(step))
    ax.yaxis.set_major_locator(MultipleLocator(step))
    # Match MATLAB capture tick sparsity on short z (typically 2 and 6).
    z_ticks = [t for t in (2.0, 6.0) if 0.0 < t <= float(nz)]
    if z_ticks:
        ax.zaxis.set_major_locator(FixedLocator(z_ticks))


def _plot_open_circle(ax: Any, x: Any, y: Any, markersize: float) -> None:
    """MATLAB ``plot(...,'ow','MarkerSize',…)`` — white edge, open face."""
    ax.plot(
        x,
        y,
        "o",
        markerfacecolor="none",
        markeredgecolor="w",
        markersize=float(markersize),
        markeredgewidth=0.8,
        linestyle="none",
    )


def _as_dense_col(x: Any, t: int) -> np.ndarray:
    """Column ``t`` (0-based) of a factor posterior as a dense 1-D vector."""
    if hasattr(x, "toarray"):
        a = np.asarray(x.toarray(), dtype=np.float64)
    else:
        a = np.asarray(x, dtype=np.float64)
    if a.ndim == 1:
        return a.reshape(-1, order="F")
    return np.asarray(a[:, t], dtype=np.float64).reshape(-1, order="F")


def _spm_show_x_rgb(x_cells: list[Any], Nx: int, Ny: int, Nz: int) -> np.ndarray:
    """Build coloured image from place posteriors (``spm_show_x`` body, one frame)."""
    u = 1.0 - 0.5
    # MATLAB: D = reshape(x(:,t),Nx,Ny,Nz) with x = Np x 1 cell column
    D = np.empty((Nx, Ny, Nz), dtype=object)
    for f, cell in enumerate(x_cells):
        # column-major linear index → (i,j,k)
        i = f % Nx
        j = (f // Nx) % Ny
        k = f // (Nx * Ny)
        D[i, j, k] = np.asarray(cell, dtype=np.float64).reshape(-1, order="F")

    W = np.full((Nx, Ny, Nz), np.nan, dtype=np.float64)
    for i in range(Nx):
        for j in range(Ny):
            for k in range(Nz):
                dvec = D[i, j, k]
                d = int(np.argmax(dvec)) + 1  # 1-based class
                m = float(dvec[d - 1])
                if m > u:
                    W[i, j, k] = float(d)

    I = np.zeros((Nx, Ny, 3), dtype=np.float64)
    for i in range(Nx):
        for j in range(Ny):
            s = W[i, j, :]
            finite = np.isfinite(s) & (s > 1)
            ks = np.where(finite)[0]
            if ks.size:
                k = int(ks[-1])  # find(...,1,'last')
                I[i, j, :] = _spm_colour(D[i, j, k])
    return I


def _pg_int(pg: dict[str, Any], key: str) -> int:
    return int(np.asarray(pg[key]).reshape(-1)[0])


def _clear_plot_artists(ax: Any) -> None:
    """Remove line/collection artists (MATLAB ``hold off`` + non-empty plot clear)."""
    for artist in list(getattr(ax, "lines", [])):
        artist.remove()
    for artist in list(getattr(ax, "collections", [])):
        artist.remove()
    for artist in list(getattr(ax, "images", [])):
        artist.remove()
    for artist in list(getattr(ax, "patches", [])):
        artist.remove()


def _state_vec_at(O_list: list[Any], g_state: int, t: int) -> np.ndarray:
    cell = O_list[g_state]
    if isinstance(cell, list):
        return np.asarray(cell[t], dtype=np.float64).reshape(-1)
    state_arr = np.asarray(cell, dtype=object)
    if state_arr.ndim == 0:
        return np.asarray(state_arr.item(), dtype=np.float64).reshape(-1)
    if state_arr.dtype == object:
        return np.asarray(state_arr.flat[t], dtype=np.float64).reshape(-1)
    return np.asarray(state_arr, dtype=np.float64).reshape(-1)



def _fig_rgb_frame(fig: Any) -> np.ndarray:
    """Capture current figure RGB (MATLAB ``getframe(gcf)`` analogue)."""
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    return np.array(rgba[:, :, :3], copy=True, dtype=np.uint8)


def _write_mp4(frames: list[np.ndarray], path: Path, fps: float) -> Path:
    """Encode RGB frames to ``.mp4``. Prefers imageio / ffmpeg; clear error if absent."""
    if not frames:
        raise ValueError("no frames to write")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = float(fps)
    if fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps}")

    # 1) imageio (+ ffmpeg plugin / imageio-ffmpeg)
    try:
        import imageio.v2 as imageio  # type: ignore

        imageio.mimwrite(str(out), frames, fps=fps, codec="libx264", pixelformat="yuv420p")
        return out
    except Exception:
        pass

    # 2) matplotlib FFMpegWriter (system / conda ffmpeg on PATH)
    try:
        import shutil
        import tempfile

        import matplotlib.pyplot as plt
        from matplotlib.animation import FFMpegWriter

        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg not on PATH")

        h, w, _ = frames[0].shape
        fig_w, fig_h = w / 100.0, h / 100.0
        fig_e, ax_e = plt.subplots(figsize=(fig_w, fig_h), dpi=100)
        ax_e.set_axis_off()
        im = ax_e.imshow(frames[0])
        writer = FFMpegWriter(fps=fps)
        with writer.saving(fig_e, str(out), dpi=100):
            for fr in frames:
                im.set_data(fr)
                writer.grab_frame()
        plt.close(fig_e)
        return out
    except Exception:
        pass

    # 3) direct ffmpeg pipe if binary exists
    try:
        import shutil
        import subprocess

        ff = shutil.which("ffmpeg")
        if ff is None:
            raise RuntimeError("ffmpeg not on PATH")
        h, w, _ = frames[0].shape
        # yuv420p needs even dims
        w2, h2 = w - (w % 2), h - (h % 2)
        cmd = [
            ff,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{w2}x{h2}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(fps),
            "-i",
            "-",
            "-an",
            "-vcodec",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdin is not None
        for fr in frames:
            proc.stdin.write(np.ascontiguousarray(fr[:h2, :w2, :]).tobytes())
        proc.stdin.close()
        err = proc.stderr.read() if proc.stderr else b""
        rc = proc.wait()
        if rc != 0 or not out.is_file():
            raise RuntimeError(err.decode("utf-8", errors="replace")[:500])
        return out
    except Exception as e:
        raise RuntimeError(
            "spm_behaviour save_mp4 requires ffmpeg or imageio+imageio-ffmpeg "
            f"(could not encode {out}). Install ffmpeg on PATH, or "
            "`pip install imageio imageio-ffmpeg` (needs explicit env approval "
            f"in this repo). Last error: {e}"
        ) from e


def spm_behaviour(
    QDP: dict[str, Any],
    PG: dict[str, Any],
    sT: Any = None,
    *,
    save_png: bool = False,
    png_path: Path | str | None = None,
    save_mp4: bool = False,
    mp4_path: Path | str | None = None,
    fig_title: str = "Behaviour",
    fps: float = 2.0,
) -> dict[str, Path | None]:
    """Draw MATLAB ``spm_behaviour`` multi-panel figure over all ``t``.

    Optional ``sT``: goal marker after the loop (wayfinding). Returns
    ``{"png": Path|None, "mp4": Path|None}``.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    Nx = _pg_int(PG, "Nx")
    Ny = _pg_int(PG, "Ny")
    Nz = _pg_int(PG, "Nz")
    Nc = _pg_int(PG, "Nc")
    Nu = _pg_int(PG, "Nu")
    Nr = _pg_int(PG, "Nr")
    Nd = _pg_int(PG, "Nd")
    No = _pg_int(PG, "No")
    Ng = Nr * Nr
    Np = Nx * Ny * Nz

    s = np.asarray(QDP["s"], dtype=np.float64)
    o = np.asarray(QDP["o"], dtype=np.float64)
    X_list = list(QDP["X"])
    O_list = list(QDP["O"])
    j_list = list(QDP["j"])
    ge = np.asarray(QDP["id"]["ge"], dtype=np.float64).reshape(-1)

    nt = int(s.shape[1])
    XYZ = spm_combinations(np.asarray([Nx, Ny, Nz], dtype=np.float64))
    Xloc = s[0:Nu, :]  # drone location factors over time

    fig = plt.figure(figsize=(10, 10), dpi=120)
    fig.suptitle(fig_title, fontsize=12)
    gs = fig.add_gridspec(4, 6, hspace=0.35, wspace=0.35)

    ax1 = fig.add_subplot(gs[0:2, 0:3])
    ax2 = fig.add_subplot(gs[0:2, 3:6])
    ax4 = fig.add_subplot(gs[2, 0:3], projection="3d")  # inferred (4,2,5)
    ax3 = fig.add_subplot(gs[2, 3:6], projection="3d")  # true (4,2,6)
    ax5 = fig.add_subplot(gs[3, 0:2])
    ax6 = fig.add_subplot(gs[3, 2:4])
    ax7 = fig.add_subplot(gs[3, 4:6])

    def _imshow_xy(ax: Any, img: np.ndarray) -> None:
        ax.imshow(
            np.clip(img, 0.0, 1.0),
            origin="upper",
            extent=(0.5, Ny + 0.5, Nx + 0.5, 0.5),
            interpolation="nearest",
        )
        ax.set_aspect("equal")

    # True 3D draw order (occlusion polish; mid-right PASS). Inferred uses
    # MATLAB ``s = 2:Nc`` so class 2 is first (empty-plot3 clear semantics).
    _cls_draw_order_true = (3, 4, 5, 2, 7, 6, 8)
    _ms_true = 6.0
    _ms_inf = 12.0  # ~MATLAB inferred MarkerSize 32 on '.'

    frames: list[np.ndarray] = []

    for t in range(nt):
        t1 = t + 1

        # --- true scene Q cells (place one-hots + objects) ---
        Q_true: list[Any] = []
        for f in range(Np):
            cls = int(round(float(s[Nu + f, t])))
            q = np.zeros(Nc, dtype=np.float64)
            if 1 <= cls <= Nc:
                q[cls - 1] = 1.0
            Q_true.append(q)
        try:
            for oo in range(No):
                base = Nu + Np + oo * 4
                s_obj = s[base : base + 4, t]
                f_lin = int(
                    spm_sub2ind(
                        [Nx, Ny, Nz],
                        float(s_obj[0]),
                        float(s_obj[1]),
                        float(s_obj[2]),
                    )
                )
                q = np.zeros(Nc, dtype=np.float64)
                cls = int(round(float(s_obj[3])))
                if 1 <= cls <= Nc:
                    q[cls - 1] = 1.0
                Q_true[f_lin - 1] = q
        except Exception:
            pass

        I_true = _spm_show_x_rgb(Q_true, Nx, Ny, Nz)

        # --- inferred scene from X(L) ---
        Q_inf: list[Any] = []
        for f in range(Np):
            Q_inf.append(_as_dense_col(X_list[Nu + f], t))
        I_inf = _spm_show_x_rgb(Q_inf, Nx, Ny, Nz)

        q_map = np.ones(Np, dtype=np.int64)
        for f in range(Np):
            qf = Q_inf[f]
            m = float(np.max(qf))
            i = int(np.argmax(qf)) + 1
            if m > 1.0 - 1.0 / 8.0:
                q_map[f] = i
            else:
                q_map[f] = 1

        Xt = np.zeros(Nu, dtype=np.float64)
        for f in range(Nu):
            Xt[f] = float(np.argmax(_as_dense_col(X_list[f], t)) + 1)

        # subplot(2,2,1) inferred — hold off each t (end state = final t)
        ax1.clear()
        _imshow_xy(ax1, I_inf)
        ax1.set_title(f"Inferred scene (t = {t1})")
        ax1.plot(
            Xt[1],
            Xt[0],
            linestyle="none",
            marker=(6, 1, 0),
            color="y",
            markersize=32,
            markeredgewidth=1.2,
            markerfacecolor="y",
        )
        ax1.plot(
            Xloc[1, t],
            Xloc[0, t],
            linestyle="none",
            marker=(6, 1, 0),
            color="w",
            markersize=32,
            markeredgewidth=1.2,
            markerfacecolor="w",
        )
        f_crash = None
        row = Xloc[0:3, t]
        for ii in range(XYZ.shape[0]):
            if np.allclose(XYZ[ii, :], row):
                f_crash = ii
                break
        if f_crash is not None and float(s[Nu + f_crash, t]) > 1:
            ax1.plot(
                Xloc[1, t],
                Xloc[0, t],
                linestyle="none",
                marker=(6, 1, 0),
                color="r",
                markersize=64,
                markeredgewidth=1.2,
                markerfacecolor="r",
            )
        ax1.plot(
            Xloc[1, 0 : t + 1],
            Xloc[0, 0 : t + 1],
            ".",
            color="w",
            markersize=7,
            linestyle="none",
        )
        for i1 in ge:
            i0 = int(i1) - 1
            if not (0 <= i0 < Ng):
                continue
            jt = j_list[i0]
            if isinstance(jt, list):
                parents = jt[t] if t < len(jt) else np.asarray([])
            else:
                parents = np.asarray(jt)
                if parents.ndim == 2:
                    parents = parents[:, t] if parents.shape[1] > t else parents.ravel()
            parents = np.asarray(parents, dtype=np.float64).reshape(-1)
            for pk in parents:
                x = spm_index([Nx, Ny, Nx], float(pk) - Nu)
                x = np.asarray(x, dtype=np.float64).reshape(-1)
                if x.size >= 3:
                    _plot_open_circle(ax1, x[1], x[0], max(float(x[2]), 1.0))

        # subplot(2,2,2) true
        ax2.clear()
        _imshow_xy(ax2, I_true)
        ax2.set_title("True scene")

        # subplot(4,2,6) 3D true — clear every t (class 2 always in true s)
        _clear_plot_artists(ax3)
        for s_cls in _cls_draw_order_true:
            if s_cls < 2 or s_cls > Nc:
                continue
            i_idx = np.where(np.round(s[Nu : Nu + Np, t]) == s_cls)[0]
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
        try:
            for oo in range(No):
                base = Nu + Np + oo * 4
                s_obj = s[base : base + 4, t]
                f_lin = int(
                    spm_sub2ind(
                        [Nx, Ny, Nz],
                        float(s_obj[0]),
                        float(s_obj[1]),
                        float(s_obj[2]),
                    )
                )
                oh = np.zeros(Nc, dtype=np.float64)
                oh[int(round(float(s_obj[3]))) - 1] = 1.0
                c = _spm_colour(oh)
                ax3.plot(
                    [XYZ[f_lin - 1, 1]],
                    [XYZ[f_lin - 1, 0]],
                    [XYZ[f_lin - 1, 2]],
                    linestyle="none",
                    marker=".",
                    markersize=_ms_true,
                    markerfacecolor=tuple(c.tolist()),
                    markeredgecolor=tuple(c.tolist()),
                    markeredgewidth=0.0,
                )
        except Exception:
            pass
        ax3.plot(
            [Xloc[1, t]],
            [Xloc[0, t]],
            [Xloc[2, t]],
            linestyle="none",
            marker="*",
            markersize=16.0,
            markerfacecolor="w",
            markeredgecolor="w",
            markeredgewidth=0.8,
        )
        _style_3d_matlabish(ax3, nx=Nx, ny=Ny, nz=Nz, z_pad=0.35)

        # subplot(4,2,5) 3D inferred — MATLAB hold off + for s=2:Nc plot3
        # Empty first class (cyan) does not clear → accumulate prior t.
        replace_pending = True  # after hold off
        for s_cls in range(2, Nc + 1):
            i_idx = np.where(q_map == s_cls)[0]
            if i_idx.size == 0:
                # empty plot3: no clear; hold on → subsequent plots add
                replace_pending = False
                continue
            if replace_pending:
                _clear_plot_artists(ax4)
                replace_pending = False
            oh = np.zeros(Nc, dtype=np.float64)
            oh[s_cls - 1] = 1.0
            c = _spm_colour(oh)
            ax4.plot(
                XYZ[i_idx, 1],
                XYZ[i_idx, 0],
                XYZ[i_idx, 2],
                linestyle="none",
                marker=".",
                markersize=_ms_inf,
                markerfacecolor=tuple(c.tolist()),
                markeredgecolor=tuple(c.tolist()),
                markeredgewidth=0.0,
            )
        ax4.plot(
            [Xloc[1, t]],
            [Xloc[0, t]],
            [Xloc[2, t]],
            linestyle="none",
            marker="*",
            markersize=16.0,
            markerfacecolor="k",
            markeredgecolor="k",
            markeredgewidth=0.8,
        )
        _style_3d_matlabish(ax4, nx=Nx, ny=Ny, nz=Nz)

        # depth / class / vision (hold off each t → end state = final t)
        depth = o[0:Ng, t].reshape((Nr, Nr), order="F")
        ax5.clear()
        ax5.imshow(
            1.0 - depth,
            origin="upper",
            aspect="equal",
            extent=(0.5, Nr + 0.5, Nr + 0.5, 0.5),
        )
        ax5.set_title("Depth")
        _apply_imagesc_ticks(ax5, Nr)
        dmin = float(np.min(depth))

        I_cls = np.zeros((Nr, Nr, 3), dtype=np.float64)
        J_vis = np.zeros((Nr, Nr, 3), dtype=np.float64)
        for i in range(Nr):
            for j in range(Nr):
                lin = i + j * Nr
                g_state = Ng + lin
                state_vec = _state_vec_at(O_list, g_state, t)
                I_cls[i, j, :] = _spm_colour(state_vec)
                d = (float(depth[i, j]) - dmin) / float(Nd)
                J_vis[i, j, :] = I_cls[i, j, :] / (4.0 * d + 1.0)

        ax6.clear()
        ax6.imshow(
            np.clip(J_vis, 0.0, 1.0),
            origin="upper",
            aspect="equal",
            extent=(0.5, Nr + 0.5, Nr + 0.5, 0.5),
        )
        ax6.set_title("Vision")
        _apply_imagesc_ticks(ax6, Nr)

        ax7.clear()
        ax7.imshow(
            np.clip(I_cls, 0.0, 1.0),
            origin="upper",
            aspect="equal",
            extent=(0.5, Nr + 0.5, Nr + 0.5, 0.5),
        )
        ax7.set_title("Class")
        _apply_imagesc_ticks(ax7, Nr)

        # MATLAB MOV(t)=getframe(gcf) — full multi-panel figure each t
        if save_mp4:
            frames.append(_fig_rgb_frame(fig))

    # Wayfinding goal overlay after behaviour loop (MATLAB ~L495)
    if sT is not None:
        st = np.asarray(sT, dtype=np.float64).reshape(-1)
        _plot_open_circle(ax1, st[1], st[0], 48.0)

    out: dict[str, Path | None] = {"png": None, "mp4": None}
    if save_png:
        if png_path is None:
            raise ValueError("png_path required when save_png=True")
        saved = Path(png_path)
        saved.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(saved, dpi=120, bbox_inches="tight", facecolor="white")
        out["png"] = saved
    if save_mp4:
        if mp4_path is None:
            raise ValueError("mp4_path required when save_mp4=True")
        # Frames were captured inside the t-loop only (MATLAB MOV(t)=getframe).
        # Optional sT overlay is post-loop PNG chrome (main script ~L495), not an extra MOV frame.
        out["mp4"] = _write_mp4(frames, Path(mp4_path), fps)
    plt.close(fig)
    return out

"""OPTIM2FULL Phase 2b Ord 5 — ``spm_MDP_params`` (post-FSL parameters).

Faithful thin port of ``spm-main/toolbox/DEM/spm_MDP_params.m``
(default ``OPT='norm'``). ``DEM_drone_VI.m`` ~L403–404:

    spm_figure('GetWin',sprintf('Paramters: level %i',numel(MDP))); clf
    spm_MDP_params(MDP{end})

Authority: F2 ``MDP{end}`` (post-FSL Dirichlet ``a``/``b``, pre-``spm_mdp_a2A``).
Do **not** reuse Atari plot helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from python_src.spm_cat import spm_cat
from python_src.spm_dir_norm import spm_dir_norm


def _unwrap(x: Any) -> Any:
    """Peel singleton list / object-array wrappers from F2 pickle cells."""
    while True:
        if isinstance(x, (list, tuple)) and len(x) == 1:
            x = x[0]
            continue
        if isinstance(x, np.ndarray) and x.dtype == object and x.size == 1:
            x = x.reshape(-1, order="F")[0]
            continue
        break
    return x


def _dense(x: Any) -> np.ndarray:
    x = _unwrap(x)
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray(), dtype=np.float64)
    return np.asarray(x, dtype=np.float64)


def _cell_list(x: Any) -> list[Any]:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return list(x.ravel(order="F"))
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _mdp_Nf_Ns_Nu(mdp: dict[str, Any]) -> tuple[int, list[int], list[int]]:
    """``[Nf,Ns,Nu] = spm_MDP_size`` dims used by ``spm_MDP_params`` (unwrapped ``b``)."""
    if "b" in mdp:
        b = _cell_list(mdp["b"])
    else:
        b = _cell_list(mdp["B"])
    nf = len(b)
    ns: list[int] = []
    nu: list[int] = []
    for f in range(nf):
        bf = _dense(b[f])
        ns.append(int(bf.shape[0]))
        if bf.ndim >= 3:
            nu.append(int(bf.shape[2]))
        else:
            nu.append(1)
    return nf, ns, nu


def _b_slice(b_f: Any, u_1based: int) -> np.ndarray:
    """MATLAB ``MDP.b{f}(:,:,u)`` (2-D ``b`` ⇒ same matrix when ``Nu==1``)."""
    bf = _dense(b_f)
    if bf.ndim == 2:
        return bf
    if bf.ndim == 3:
        return bf[:, :, u_1based - 1]
    if bf.ndim >= 4:
        return bf[:, :, u_1based - 1, 0]
    raise ValueError(f"unexpected b shape {bf.shape}")


def _parula_cmap() -> Any:
    """Approximate MATLAB default ``parula`` (no extra deps)."""
    from matplotlib.colors import LinearSegmentedColormap

    # Control points sampled from MATLAB parula (low→high).
    stops = [
        (0.2081, 0.1663, 0.5292),
        (0.2116, 0.1898, 0.5777),
        (0.2123, 0.2138, 0.6270),
        (0.2082, 0.2386, 0.6771),
        (0.1959, 0.2645, 0.7279),
        (0.1707, 0.2919, 0.7792),
        (0.1253, 0.3242, 0.8303),
        (0.0591, 0.3598, 0.8683),
        (0.0117, 0.4032, 0.8828),
        (0.0060, 0.4456, 0.8501),
        (0.0328, 0.4833, 0.8034),
        (0.0713, 0.5183, 0.7530),
        (0.1140, 0.5513, 0.7003),
        (0.1590, 0.5830, 0.6453),
        (0.2064, 0.6138, 0.5878),
        (0.2570, 0.6440, 0.5265),
        (0.3145, 0.6725, 0.4560),
        (0.3924, 0.6953, 0.3670),
        (0.4937, 0.7041, 0.2780),
        (0.6074, 0.6982, 0.2162),
        (0.7137, 0.6809, 0.1842),
        (0.8052, 0.6624, 0.1578),
        (0.8773, 0.6531, 0.1423),
        (0.9330, 0.6669, 0.1546),
        (0.9740, 0.7044, 0.1957),
        (0.9932, 0.7570, 0.2520),
        (0.9939, 0.8164, 0.3141),
        (0.9806, 0.8762, 0.3754),
        (0.9582, 0.9322, 0.4339),
        (0.9769, 0.9839, 0.0539),
    ]
    return LinearSegmentedColormap.from_list("parula_approx", stops, N=256)


def _imagesc(ax: Any, m: np.ndarray) -> None:
    """MATLAB ``imagesc`` (autoscale, 1-based extent, ``parula``-like cmap)."""
    m = np.asarray(m, dtype=np.float64)
    nr, nc = int(m.shape[0]), int(m.shape[1])
    ax.imshow(
        m,
        cmap=_parula_cmap(),
        aspect="auto",
        interpolation="nearest",
        extent=(0.5, nc + 0.5, nr + 0.5, 0.5),  # MATLAB imagesc X/YData
        origin="upper",
    )


def _spm_spy_plot(ax: Any, x: np.ndarray, markersize: float = 8.0) -> None:
    """Thin ``spm_spy`` (``spm-main/spm_spy.m``) when ``Ns>128`` / tall likelihood."""
    x = np.asarray(x, dtype=np.float64)
    m = float(np.max(x)) if x.size else 1.0
    if m <= 0:
        m = 1.0
    ax.cla()
    g = 8
    for p in range(g, 0, -1):
        ii, jj = np.where(x > m / float(p))
        ax.plot(
            jj + 1.0,
            ii + 1.0,
            linestyle="none",
            marker=".",
            markersize=float(markersize),
            color=(1.0, 1.0, 1.0) * ((p - 1) / float(g)),
        )
    nr, nc = int(x.shape[0]), int(x.shape[1])
    ax.set_xlim(1.0, float(max(nc, 1)))
    ax.set_ylim(float(max(nr, 1)), 1.0)  # axis ij
    ax.set_aspect("equal")


def dem_drone_vi_plot_mdp_params(
    MDP_end: dict[str, Any],
    *,
    OPT: str = "norm",
    save_png: bool = False,
    png_path: Path | str | None = None,
    fig_title: str = "Paramters: level 2",
) -> Path | None:
    """Draw ``spm_MDP_params(MDP{end})``; optionally save PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mdp = dict(MDP_end)
    if "a" not in mdp:
        mdp["a"] = mdp["A"]
    if "b" not in mdp:
        mdp["b"] = mdp["B"]

    nf, ns, nu = _mdp_Nf_Ns_Nu(mdp)
    b_cells = _cell_list(mdp["b"])

    fig = plt.figure(figsize=(10, 10), dpi=120)
    fig.suptitle(fig_title, fontsize=12)

    for f in range(1, nf + 1):
        for u in range(1, nu[f - 1] + 1):
            ax = fig.add_subplot(6, 6, u + (f - 1) * 6)
            slice_u = _b_slice(b_cells[f - 1], u)
            if OPT == "norm":
                q = spm_dir_norm(slice_u)
                if ns[f - 1] > 128:
                    _spm_spy_plot(ax, np.asarray(q, dtype=np.float64) > (1.0 / 16.0), 4.0)
                else:
                    _imagesc(ax, q)
            else:
                if ns[f - 1] > 128:
                    _spm_spy_plot(ax, slice_u > (1.0 / 16.0), 4.0)
                else:
                    _imagesc(ax, slice_u)
                # MATLAB .m duplicates imagesc in the else branch (L40) — match.
                _imagesc(ax, slice_u)
            ax.set_title("Transition priors", fontsize=9)
            ax.set_aspect("auto")
            try:
                ax.set_box_aspect(1)
            except Exception:
                pass

    # likelihood mapping (MATLAB try/end — skip only if ``a`` absent / unusable)
    try:
        a_cells = _cell_list(mdp["a"])
        a_norm: list[np.ndarray] = []
        for g in range(len(a_cells)):
            ag = _dense(a_cells[g])
            # MATLAB MDP.a{g}(:,:) then spm_dir_norm
            flat = np.reshape(ag, (ag.shape[0], int(np.prod(ag.shape[1:]))), order="F")
            a_norm.append(np.asarray(spm_dir_norm(flat), dtype=np.float64))
        # A = spm_cat(a')  — column cell of modalities
        col = np.empty((len(a_norm), 1), dtype=object)
        for i, mat in enumerate(a_norm):
            col[i, 0] = mat
        A = _dense(spm_cat(col))
        ax = fig.add_subplot(2, 2, 3)
        if A.shape[0] > 128:
            _spm_spy_plot(ax, A, 8.0)
        else:
            _imagesc(ax, A)
        ax.set_aspect("auto")
        try:
            ax.set_box_aspect(1)
        except Exception:
            pass
        ax.set_title("Likelihood", fontsize=14)
        ax.set_xlabel("latent states")
        ax.set_ylabel("outcomes")
    except (KeyError, TypeError, ValueError, AttributeError):
        pass

    # allowable state transitions
    ax = fig.add_subplot(2, 2, 4)
    b1 = _dense(b_cells[0])
    mask = b1 > (1.0 / 16.0)
    if mask.ndim >= 3:
        allow = np.sum(mask.astype(np.float64), axis=2) != 0
    else:
        allow = mask.astype(bool)
    if ns[0] > 128:
        _spm_spy_plot(ax, allow.astype(np.float64), 8.0)
    else:
        _imagesc(ax, allow.astype(np.float64))
    ax.set_aspect("auto")
    try:
        ax.set_box_aspect(1)
    except Exception:
        pass
    ax.set_title("Allowable transitions", fontsize=14)
    ax.set_xlabel("latent states")
    ax.set_ylabel("latent states")

    out: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("png_path required when save_png=True")
        out = Path(png_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=120, bbox_inches="tight", facecolor="w")
    plt.close(fig)
    return out

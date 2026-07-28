"""OPTIM1 — ``spm_faster_structure_learning`` (``spm_unique_optim`` in ``_spm_structure_fast``)."""

from __future__ import annotations

import copy
import os
import time
from typing import Any, Callable, List, Optional, Tuple

import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_cross import spm_cross
from python_src.spm_dir_MI import spm_dir_MI
from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_unvec import spm_unvec
from python_src.spm_vec import spm_vec
from python_src.optimized.toolbox.DEM.spm_rgm_group_optim import spm_rgm_group_optim
from python_src.optimized.toolbox.DEM.spm_unique_optim import spm_unique_optim


def _fsl_timing_enabled() -> bool:
    """``RGMS_OPTIM2FULL_FSL_TIMING`` — default **off** (OPTIM1FULL/COLAB1 quiet)."""
    raw = str(os.getenv("RGMS_OPTIM2FULL_FSL_TIMING", "0")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def _structure_fast_o_fingerprint(O: list) -> tuple:
    """Content fingerprint for ``_spm_structure_fast`` inputs (Class A cache key)."""
    shapes: list[Any] = []
    parts: list[bytes] = []
    for series in O:
        if isinstance(series, list):
            shapes.append(("L", len(series)))
            for col in series:
                a = np.asarray(col, dtype=np.float64)
                shapes.append(a.shape)
                parts.append(np.ascontiguousarray(a).ravel(order="F").tobytes())
        else:
            a = np.asarray(series, dtype=np.float64)
            shapes.append(("A", a.shape))
            parts.append(np.ascontiguousarray(a).ravel(order="F").tobytes())
    return (tuple(shapes), b"".join(parts))


def _structure_fast_result_copy(mdp: dict, j_loc: Any) -> tuple[dict, np.ndarray]:
    """Deep copy structure_fast outputs so cache entries are not mutated in place."""
    return copy.deepcopy(mdp), np.array(j_loc, copy=True)


def _fsl_timing_log(msg: str) -> None:
    if _fsl_timing_enabled():
        print(f"[fsl_timing] {msg}", flush=True)


def _rg_scale_pad(x: Any, default: float = 2.0) -> np.ndarray:
    """MATLAB ``[x repmat(x(end),1,16)]`` for RG ``dx`` / ``dt``.

    Compatible with both callers:
    - OPTIM1FULL / Atari: scalar ``Sc`` / ``dx`` (e.g. ``9``) → length-17 constant pad
      (same values as the prior ``float(dx)`` + ``repeat`` path).
    - OPTIM2FULL / drone: vector ``[1 64]`` → level 1 uses ``1``, later levels ``64``.
    """
    if x is None:
        x = default
    arr = np.atleast_1d(np.asarray(x, dtype=np.float64)).ravel(order="F")
    if arr.size < 1:
        arr = np.asarray([float(default)], dtype=np.float64)
    return np.concatenate([arr, np.repeat(float(arr[-1]), 16)])


def spm_faster_structure_learning_optim(
    O,
    S,
    dx=None,
    dt=None,
    *,
    rgm_eig_pair: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    rgm_mi_override_fn: Optional[Callable[[List[Any], int], np.ndarray]] = None,
    rgm_spectral_probe_fn: Optional[Callable[[dict], None]] = None,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
    link_mi_probe_fn: Optional[Callable[[dict], None]] = None,
    rgm_group_override_fn: Optional[
        Callable[[List[Any], int, int], List[Any]]
    ] = None,
    rgm_time_segments: bool = False,
):
    """RG structure learning — Pass 1 mirror of ``spm_faster_structure_learning.m``.

    Parameters
    ----------
    rgm_eig_pair :
        Forwarded as ``eig_pair`` to every ``spm_rgm_group`` call (oracle / MATLAB
        ``eig(...,'nobalance')`` bridge). Default ``None`` keeps production SciPy
        eigenpairs.
    rgm_mi_override_fn :
        Optional ``(o_sub, m) -> MI`` for provisional translation validation only;
        forwarded as ``mi_override`` into each ``spm_rgm_group`` call. Default
        ``None`` builds ``MI`` inside ``spm_rgm_group`` from ``O`` in Python.
    link_dir_mi_fn :
        Optional ``a_mat -> float`` replacing ``spm_dir_MI`` when storing stream-link
        matrices ``ss.ID`` / ``ss.IE``. Oracle-only (e.g. MATLAB Engine); default
        ``None`` uses native Python.
    rgm_spectral_probe_fn :
        Optional callback receiving per-iteration spectral records from
        :func:`spm_rgm_group` (active set, MI block, eig/sort decisions). Intended
        for oracle/capture diagnostics only; default ``None`` keeps runtime behavior
        unchanged.
    rgm_group_override_fn :
        Optional ``(o_sub, dx, m) -> G`` replacing the entire ``spm_rgm_group`` call
        (dump-once MATLAB ``G`` inject for OPTIM2FULL-scale Q). Default ``None``
        keeps OPTIM1FULL / COLAB1 / native behavior unchanged.
    rgm_time_segments :
        Forwarded as ``time_segments`` to ``spm_rgm_group`` (live interior timing).
        Default ``False``.
    """
    spinblock = False
    t_fsl0 = time.perf_counter()
    S = np.asarray(S, dtype=np.float64)
    if S.ndim == 1:
        S = S.reshape(1, -1)
    if S.shape[1] < 4:
        S = np.hstack([S, np.ones((S.shape[0], 4 - S.shape[1]), dtype=np.float64)])
    if S.shape[0] == 1:
        n_o = len(O)
        prod_s = float(np.prod(S[0, :3]))
        S[0, 3] = n_o / prod_s

    # MATLAB: if nargin < 3, dx = 2; end; dx = [dx repmat(dx(end),1,16)];
    dx = _rg_scale_pad(dx, 2.0)
    dt = _rg_scale_pad(dt, 2.0)

    mdp_h: list[dict] = []
    n_stream = int(S.shape[0])
    o_cur = O
    nt0 = len(o_cur[0]) if len(o_cur) else 0
    _fsl_timing_log(
        f"BEGIN n_o={len(O)} n_stream={n_stream} nt={nt0} S={S.tolist()} "
        f"dx0={float(dx[0])} dx1={float(dx[min(1, dx.size-1)])} "
        f"mi_hook={'on' if rgm_mi_override_fn is not None else 'off'} "
        f"eig_hook={'on' if rgm_eig_pair is not None else 'off'} "
        f"link_dir_mi={'on' if link_dir_mi_fn is not None else 'off'} "
        f"g_override={'on' if rgm_group_override_fn is not None else 'off'} "
        f"rgm_time_segments={'on' if rgm_time_segments else 'off'} "
        f"(FSL_TIMING env on; OPTIM1FULL Entry4 used O(:,1:1000) — "
        f"drone Q scale differs)"
    )

    for n in range(1, 9):
        t_lev0 = time.perf_counter()
        sg: list[np.ndarray | None] = [None] * n_stream
        n_cells: dict[tuple[int, int], np.ndarray] = {}
        ng = np.zeros(n_stream, dtype=np.int64)

        mdp_n = _new_mdp_level(n_stream, float(dt[n - 1]))
        nt_lev = len(o_cur[0]) if len(o_cur) else 0
        _fsl_timing_log(
            f"level n={n} START n_stream={n_stream} nt={nt_lev} "
            f"dx[n]={float(dx[n - 1])} dt[n]={float(dt[n - 1])}"
        )

        for s in range(1, n_stream + 1):
            t_stream0 = time.perf_counter()
            no = len(mdp_n["a"])
            ns = len(mdp_n["b"])
            nt = len(o_cur[0]) if len(o_cur) else 0
            t_idx = np.arange(1, nt, int(dt[n - 1]), dtype=np.int64)
            if t_idx.size == 0:
                t_idx = np.array([1], dtype=np.int64)

            t_mi = 0.0
            t_rgm = 0.0
            t_fast = 0.0
            n_o_s = 0
            if spinblock:
                g = _spm_group(S[s - 1, :].tolist(), int(dx[n - 1]))
            else:
                o_stack = np.concatenate([[0.0], np.prod(S, axis=1).astype(np.float64)])
                offset = float(o_stack[s - 1])
                n_o_s = int(np.prod(S[s - 1, :]))
                idx = (offset + np.arange(1, n_o_s + 1, dtype=np.float64)).astype(np.int64)
                o_sub = [o_cur[int(i) - 1] for i in idx]
                m_stream = int(S[s - 1, 3])
                dx_i = int(dx[n - 1])
                if rgm_group_override_fn is not None:
                    _fsl_timing_log(
                        f"level n={n} stream s={s} G_override START "
                        f"n_o_s={n_o_s} dx={dx_i} m={m_stream}"
                    )
                    t_rgm0 = time.perf_counter()
                    g = rgm_group_override_fn(o_sub, dx_i, m_stream)
                    t_rgm = time.perf_counter() - t_rgm0
                    t_mi = 0.0
                    _fsl_timing_log(
                        f"level n={n} stream s={s} G_override END "
                        f"elapsed_s={t_rgm:.3f} n_groups={len(g) if g is not None else 0}"
                    )
                else:
                    mi_override = None
                    if rgm_mi_override_fn is not None:
                        n_cells_est = int(n_o_s * (len(o_sub[0]) if o_sub else 0))
                        _fsl_timing_log(
                            f"level n={n} stream s={s} MI_override START "
                            f"n_o_s={n_o_s} m={m_stream} "
                            f"nt_sub={len(o_sub[0]) if o_sub else 0} "
                            f"n_cells_est={n_cells_est} "
                            f"(Entry4 cell-push × Engine; see MI_override push lines "
                            f"if FSL_TIMING + instrumented MI)"
                        )
                        t_mi0 = time.perf_counter()
                        mi_override = np.asarray(
                            rgm_mi_override_fn(o_sub, m_stream), dtype=np.float64
                        )
                        t_mi = time.perf_counter() - t_mi0
                        _fsl_timing_log(
                            f"level n={n} stream s={s} MI_override END "
                            f"elapsed_s={t_mi:.3f} MI_shape={getattr(mi_override, 'shape', None)}"
                        )
                    _fsl_timing_log(
                        f"level n={n} stream s={s} spm_rgm_group_optim START "
                        f"n_o_s={n_o_s} dx={dx_i} m={m_stream}"
                    )
                    t_rgm0 = time.perf_counter()
                    g = spm_rgm_group_optim(
                        o_sub,
                        dx_i,
                        m_stream,
                        eig_pair=rgm_eig_pair,
                        mi_override=mi_override,
                        spectral_probe_fn=(
                            None
                            if rgm_spectral_probe_fn is None
                            else lambda rec, _n=n, _s=s: rgm_spectral_probe_fn(
                                {
                                    **rec,
                                    "lev_call": int(_n),
                                    "stream_idx": int(_s),
                                }
                            )
                        ),
                        time_segments=rgm_time_segments,
                    )
                    t_rgm = time.perf_counter() - t_rgm0
                    _fsl_timing_log(
                        f"level n={n} stream s={s} spm_rgm_group_optim END "
                        f"elapsed_s={t_rgm:.3f} n_groups={len(g) if g is not None else 0}"
                    )

            g_off = spm_unvec(spm_vec(g) + float(no), g)
            g_use = []
            for item in g_off:
                arr = np.asarray(item, dtype=np.int64).ravel()
                g_use.append(arr.reshape((-1, 1), order="F"))
            mdp_n["G"][s] = g_use

            ng[s - 1] = len(g_use)
            j_len = nt
            sg[s - 1] = np.zeros((int(ng[s - 1]), j_len), dtype=np.float64)

            n_g = int(ng[s - 1])
            _fsl_timing_log(
                f"level n={n} stream s={s} structure_fast START n_groups={n_g}"
            )
            t_fast0 = time.perf_counter()
            # FSL2-zoom accumulators (timing only; no semantic change).
            sf_core = {
                "n_calls": 0,
                "unique": 0.0,
                "R": 0.0,
                "a_cat": 0.0,
                "b_fill": 0.0,
                "pack": 0.0,
            }
            sf_outer = {
                "gather_o": 0.0,
                "core": 0.0,
                "assign_ab": 0.0,
                "id_meta": 0.0,
                "n_cells": 0.0,
            }
            want_sf_zoom = _fsl_timing_enabled()
            # FSL4b: memoize structure_fast by O content (drone: ~19 unique among 8192).
            sf_cache: dict[tuple, tuple[dict, np.ndarray]] = {}
            sf_cache_hits = 0
            sf_cache_miss = 0
            for g_i in range(1, n_g + 1):
                fg = ns + g_i
                gg = mdp_n["G"][s][g_i - 1].ravel(order="F").astype(np.int64)
                t_g0 = time.perf_counter()
                o_gg = [o_cur[int(ix) - 1] for ix in gg]
                if want_sf_zoom:
                    sf_outer["gather_o"] += time.perf_counter() - t_g0
                t_c0 = time.perf_counter()
                fp = _structure_fast_o_fingerprint(o_gg)
                cached = sf_cache.get(fp)
                if cached is not None:
                    mdp_loc, j_loc = _structure_fast_result_copy(cached[0], cached[1])
                    sf_cache_hits += 1
                else:
                    mdp_loc, j_loc = _spm_structure_fast(
                        o_gg, timing_acc=sf_core if want_sf_zoom else None
                    )
                    sf_cache[fp] = _structure_fast_result_copy(mdp_loc, j_loc)
                    sf_cache_miss += 1
                if want_sf_zoom:
                    sf_outer["core"] += time.perf_counter() - t_c0
                jv = np.asarray(j_loc, dtype=np.float64).ravel()
                n_j = min(jv.size, sg[s - 1].shape[1])
                sg[s - 1][g_i - 1, :n_j] = jv[:n_j]

                t_a0 = time.perf_counter()
                _assign_a_by_gg_rows(mdp_n["a"], gg, mdp_loc["a"])
                _assign_b_fg(mdp_n["b"], fg, mdp_loc["b"])
                if want_sf_zoom:
                    sf_outer["assign_ab"] += time.perf_counter() - t_a0

                t_i0 = time.perf_counter()
                i_d = 2 * ns + 2 * g_i - 1
                i_e = 2 * ns + 2 * g_i
                for r in np.asarray(gg, dtype=np.int64).ravel():
                    _set_indexed_scalar_cell(mdp_n["id"]["A"], int(r), fg)
                    _set_indexed_scalar_cell(mdp_n["sA"], int(r), s)
                    _set_indexed_scalar_cell(mdp_n["sC"], int(r), s)
                _set_id_list_at(mdp_n["id"]["D"], fg, [i_d])
                _set_id_list_at(mdp_n["id"]["E"], fg, [i_e])
                _set_indexed_scalar_cell(mdp_n["sB"], fg, s)
                if want_sf_zoom:
                    sf_outer["id_meta"] += time.perf_counter() - t_i0

                t_n0 = time.perf_counter()
                for col_k, tk in enumerate(t_idx, start=1):
                    n_cells[(i_d, col_k)] = np.asarray(
                        mdp_loc["X"][int(tk) - 1], dtype=bool
                    ).ravel()
                    p_t = mdp_loc["P"][int(tk) - 1]
                    if isinstance(p_t, np.ndarray) and p_t.size > 1:
                        n_cells[(i_e, col_k)] = np.asarray(p_t, dtype=bool).ravel()
                    else:
                        n_cells[(i_e, col_k)] = np.array([bool(np.asarray(p_t).ravel()[0])], dtype=bool)
                if want_sf_zoom:
                    sf_outer["n_cells"] += time.perf_counter() - t_n0

                # Heartbeat every 8 groups (or last) — inspect long group loops.
                if want_sf_zoom and (g_i == 1 or g_i == n_g or g_i % 8 == 0):
                    _fsl_timing_log(
                        f"level n={n} stream s={s} structure_fast "
                        f"progress g_i={g_i}/{n_g} "
                        f"elapsed_s={time.perf_counter()-t_fast0:.3f}"
                    )
            t_fast = time.perf_counter() - t_fast0
            if want_sf_zoom:
                _fsl_timing_log(
                    f"level n={n} stream s={s} structure_fast ZOOM "
                    f"n_groups={n_g} total_s={t_fast:.3f} "
                    f"cache_hits={sf_cache_hits} cache_miss={sf_cache_miss} "
                    f"cache_unique={len(sf_cache)} "
                    f"outer_gather_o={sf_outer['gather_o']:.3f} "
                    f"outer_core={sf_outer['core']:.3f} "
                    f"outer_assign_ab={sf_outer['assign_ab']:.3f} "
                    f"outer_id_meta={sf_outer['id_meta']:.3f} "
                    f"outer_n_cells={sf_outer['n_cells']:.3f} "
                    f"core_unique={sf_core['unique']:.3f} "
                    f"core_R={sf_core['R']:.3f} "
                    f"core_a_cat={sf_core['a_cat']:.3f} "
                    f"core_b_fill={sf_core['b_fill']:.3f} "
                    f"core_pack={sf_core['pack']:.3f} "
                    f"core_n_calls={sf_core['n_calls']}"
                )
            _fsl_timing_log(
                f"level n={n} stream s={s} END "
                f"elapsed_s={time.perf_counter()-t_stream0:.3f} "
                f"mi_s={t_mi:.3f} rgm_s={t_rgm:.3f} structure_fast_s={t_fast:.3f} "
                f"n_groups={n_g} n_o_s={n_o_s}"
            )

        t_link = 0.0
        if n > 1:
            t_link0 = time.perf_counter()
            _link_streams(
                mdp_n,
                mdp_h[n - 2],
                ng,
                sg,
                link_dir_mi_fn=link_dir_mi_fn,
                link_mi_probe_fn=link_mi_probe_fn,
                lev_prev=n - 1,
            )
            t_link = time.perf_counter() - t_link0
            _fsl_timing_log(
                f"level n={n} link_streams elapsed_s={t_link:.3f}"
            )

        if int(np.max(ng)) < 2 and n > 1:
            mdp_h.append(mdp_n)
            _fsl_timing_log(
                f"level n={n} EARLY_BREAK max(ng)={int(np.max(ng))} "
                f"elapsed_s={time.perf_counter()-t_lev0:.3f} "
                f"total_s={time.perf_counter()-t_fsl0:.3f}"
            )
            break

        t_comp = 0.0
        if not spinblock:
            t_comp0 = time.perf_counter()
            o_cur, S = _compress_unitary_and_slice_o(mdp_n, n_cells, t_idx, S, n_stream, n)
            t_comp = time.perf_counter() - t_comp0
            _fsl_timing_log(
                f"level n={n} compress elapsed_s={t_comp:.3f} "
                f"nt_next={len(o_cur[0]) if o_cur else 0} S={np.asarray(S).tolist()}"
            )
        else:
            for s in range(1, n_stream + 1):
                g_shape = mdp_n["G"][s]
                s_dims = [max(1, len(g_shape)), 1, 1] if isinstance(g_shape, list) else [1, 1, 1]
                S[s - 1, :4] = np.array(s_dims + [2], dtype=np.float64)[:4]

        mdp_h.append(mdp_n)
        _fsl_timing_log(
            f"level n={n} END elapsed_s={time.perf_counter()-t_lev0:.3f} "
            f"link_s={t_link:.3f} compress_s={t_comp:.3f} "
            f"max_ng={int(np.max(ng))} n_levels_so_far={len(mdp_h)}"
        )

    _fsl_timing_log(
        f"END total_s={time.perf_counter()-t_fsl0:.3f} n_levels={len(mdp_h)}"
    )
    return mdp_h


def _new_mdp_level(n_stream: int, t_scale: float) -> dict:
    return {
        "a": [],
        "b": [],
        "id": {"A": [], "D": [], "E": []},
        "G": {},
        "T": t_scale,
        "sA": [],
        "sB": [],
        "sC": [],
        "ss": {
            "D": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "E": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "ID": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "IE": [[None for _ in range(n_stream)] for __ in range(n_stream)],
        },
    }


def _assign_a_by_gg_rows(a_rows: list, gg: np.ndarray, mdp_a: list) -> None:
    gg_flat = np.asarray(gg, dtype=np.int64).ravel()
    for k in range(len(gg_flat)):
        r = int(gg_flat[k])
        while len(a_rows) < r:
            a_rows.append([None])
        a_rows[r - 1] = [mdp_a[k]]


def _assign_b_fg(b_rows: list, fg: int, mdp_b: list) -> None:
    while len(b_rows) < fg:
        b_rows.append([None])
    b_rows[fg - 1] = list(mdp_b)


def _set_id_list_at(id_list: list, fg: int, values: list) -> None:
    while len(id_list) < fg:
        id_list.append([])
    id_list[fg - 1] = list(values)


def _set_indexed_scalar_cell(lst: list, idx: int, value) -> None:
    while len(lst) < idx:
        lst.append(None)
    lst[idx - 1] = value


def _find_ismember_indices(sb_list: list, target: int) -> list[int]:
    return [i + 1 for i, v in enumerate(sb_list) if v is not None and int(v) == int(target)]


def _link_streams(
    mdp_n: dict,
    mdp_prev: dict,
    ng: np.ndarray,
    sg: list[np.ndarray | None],
    *,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
    link_mi_probe_fn: Optional[Callable[[dict], None]] = None,
    lev_prev: Optional[int] = None,
) -> None:
    def _stream_link_mi(a_mat: np.ndarray) -> float:
        if link_dir_mi_fn is not None:
            return float(link_dir_mi_fn(np.asarray(a_mat, dtype=np.float64)))
        return float(np.real(spm_dir_MI(a_mat)))

    si = 1
    st = np.flatnonzero(ng) + 1
    for sj in st[1:].tolist():
        fsi = _find_ismember_indices(mdp_n["sB"], si)
        fsj = _find_ismember_indices(mdp_prev["sB"], sj)
        t_cols = int(sg[0].shape[1]) if sg[0] is not None else 0
        for i_idx in range(len(fsi)):
            for j_idx in range(len(fsj)):
                fi = fsi[i_idx]
                fj = fsj[j_idx]
                bi = mdp_n["b"][fi - 1][0]
                bj_prev = mdp_prev["b"][fj - 1][0]
                ni = int(np.asarray(bi).shape[0])
                nj = int(np.asarray(bj_prev).shape[1])
                nu = int(np.asarray(bj_prev).shape[2]) if np.asarray(bj_prev).ndim > 2 else 1

                gi = len(mdp_n["a"]) + 1
                gj = int(np.asarray(mdp_prev["id"]["D"][fj - 1]).ravel()[0])
                a_norm = spm_dir_norm(mdp_n["a"][gj - 1][0])
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_mat = np.zeros((nj, ni), dtype=np.float64)
                for f in range(t_cols):
                    ii_sg = int(sg[si - 1][i_idx, f])
                    ij_sg = int(sg[int(sj) - 1][j_idx, f])
                    a_mat[:, ii_sg - 1] = a_mat[:, ii_sg - 1] + a_norm[:, ij_sg - 1]

                _append_linked_likelihood(mdp_n, a_mat, fi, si, sj)
                mdp_prev["id"]["D"][fj - 1] = list(mdp_prev["id"]["D"][fj - 1]) + [gi]
                _ss_store(mdp_prev["ss"]["D"], sj, sj, fj, fj, gj)
                _ss_store(mdp_prev["ss"]["D"], si, sj, fi, fj, gi)
                mi_id = _stream_link_mi(a_mat)
                _ss_store_mi(mdp_prev["ss"]["ID"], si, sj, fi, fj, mi_id)
                if link_mi_probe_fn is not None:
                    link_mi_probe_fn(
                        {
                            "kind": "ID",
                            "lev": int(lev_prev) if lev_prev is not None else None,
                            "si": int(si),
                            "sj": int(sj),
                            "fi": int(fi),
                            "fj": int(fj),
                            "gi": int(gi),
                            "a_mat": np.array(a_mat, dtype=np.float64, copy=True),
                            "python_mi": float(mi_id),
                        }
                    )

                gi = len(mdp_n["a"]) + 1
                gj = int(np.asarray(mdp_prev["id"]["E"][fj - 1]).ravel()[0])
                a_norm = spm_dir_norm(mdp_n["a"][gj - 1][0])
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_mat = np.zeros((nu, ni), dtype=np.float64)
                for f in range(t_cols):
                    ii_sg = int(sg[si - 1][i_idx, f])
                    ij_sg = int(sg[int(sj) - 1][j_idx, f])
                    a_mat[:, ii_sg - 1] = a_mat[:, ii_sg - 1] + a_norm[:, ij_sg - 1]

                _append_linked_likelihood(mdp_n, a_mat, fi, si, sj)
                mdp_prev["id"]["E"][fj - 1] = list(mdp_prev["id"]["E"][fj - 1]) + [gi]
                _ss_store(mdp_prev["ss"]["E"], sj, sj, fj, fj, gj)
                _ss_store(mdp_prev["ss"]["E"], si, sj, fi, fj, gi)
                mi_ie = _stream_link_mi(a_mat)
                _ss_store_mi(mdp_prev["ss"]["IE"], si, sj, fi, fj, mi_ie)
                if link_mi_probe_fn is not None:
                    link_mi_probe_fn(
                        {
                            "kind": "IE",
                            "lev": int(lev_prev) if lev_prev is not None else None,
                            "si": int(si),
                            "sj": int(sj),
                            "fi": int(fi),
                            "fj": int(fj),
                            "gi": int(gi),
                            "a_mat": np.array(a_mat, dtype=np.float64, copy=True),
                            "python_mi": float(mi_ie),
                        }
                    )


def _append_linked_likelihood(mdp_n: dict, a_mat: np.ndarray, fi: int, si: int, sj: int) -> None:
    mdp_n["a"].append([a_mat])
    mdp_n["id"]["A"].append([fi])
    mdp_n["sA"].append(si)
    mdp_n["sC"].append(sj)


def _ss_store(ss_mat: list, si: int, sj: int, fi: int, fj: int, val: int) -> None:
    m = ss_mat[int(si) - 1][int(sj) - 1]
    if m is None:
        m = {}
        ss_mat[int(si) - 1][int(sj) - 1] = m
    m[(int(fi), int(fj))] = int(val)


def _ss_store_mi(ss_mat: list, si: int, sj: int, fi: int, fj: int, val: float) -> None:
    m = ss_mat[int(si) - 1][int(sj) - 1]
    if m is None:
        m = {}
        ss_mat[int(si) - 1][int(sj) - 1] = m
    m[(int(fi), int(fj))] = val


def _compress_unitary_and_slice_o(
    mdp_n: dict,
    n_cells: dict,
    t_idx: np.ndarray,
    S: np.ndarray,
    n_stream: int,
    n: int,
):
    want_zoom = _fsl_timing_enabled()
    t_all0 = time.perf_counter()
    ns_b = len(mdp_n["b"])
    d_mask = np.ones(ns_b, dtype=bool)
    t0 = time.perf_counter()
    for f in range(1, ns_b + 1):
        sb = mdp_n["sB"][f - 1]
        if sb is not None and int(sb) == 1:
            b = np.sum(np.asarray(mdp_n["b"][f - 1][0], dtype=np.float64), axis=2)
            if float(np.max(np.sum(b, axis=1))) < 1.0 and n < 2:
                d_mask[f - 1] = False
            denom = max(int(np.asarray(b).shape[0]), 1)
            if float(np.min(np.sum(b > 0, axis=0) / denom)) > 0.5 and b.size > 4:
                d_mask[f - 1] = False
            if np.asarray(mdp_n["b"][f - 1][0]).size == 1:
                d_mask[f - 1] = False
    t_mask = time.perf_counter() - t0

    t0 = time.perf_counter()
    # MATLAB: for f = find(~d), for g = find(ismember([id.A{:}],f)) ...
    # Build parent->children once (same membership), avoid O(n_removed * n_A) rescans.
    parent_to_children: dict[int, list[int]] = {}
    for gi, cell in enumerate(mdp_n["id"]["A"], start=1):
        if cell is None:
            continue
        v = int(np.asarray(cell).ravel()[0])
        parent_to_children.setdefault(v, []).append(gi)
    for f in np.flatnonzero(~d_mask) + 1:
        f_i = int(f)
        mdp_n["b"][f_i - 1][0] = np.sum(
            np.asarray(mdp_n["b"][f_i - 1][0], dtype=np.float64)
        )
        for g in parent_to_children.get(f_i, ()):
            ag = mdp_n["a"][g - 1][0]
            if sparse.issparse(ag):
                ag = ag.toarray()
            mdp_n["a"][g - 1][0] = np.sum(
                np.asarray(ag, dtype=np.float64), axis=1, keepdims=True
            )
    t_collapse = time.perf_counter() - t0

    t0 = time.perf_counter()
    s_b_kept = [mdp_n["sB"][i] for i, keep in enumerate(d_mask) if keep]
    for s in range(n_stream):
        cnt = sum(1 for x in s_b_kept if x is not None and int(x) == s + 1)
        S[s, :4] = np.array([cnt, 1, 1, 2], dtype=np.float64)
    t_S = time.perf_counter() - t0

    t0 = time.perf_counter()
    d_exp = np.repeat(d_mask, 2)
    i_vec = (np.flatnonzero(d_exp) + 1).astype(np.int64)
    old_set_d = [[int(x) for x in row] for row in mdp_n["id"]["D"]]
    old_set_e = [[int(x) for x in row] for row in mdp_n["id"]["E"]]
    for j in range(len(mdp_n["id"]["D"])):
        old = old_set_d[j]
        mdp_n["id"]["D"][j] = [k + 1 for k in range(len(i_vec)) if int(i_vec[k]) in set(old)]
    for j in range(len(mdp_n["id"]["E"])):
        old = old_set_e[j]
        mdp_n["id"]["E"][j] = [k + 1 for k in range(len(i_vec)) if int(i_vec[k]) in set(old)]
    t_id_remap = time.perf_counter() - t0

    t0 = time.perf_counter()
    O_new = _n_rows_to_o(n_cells, i_vec.tolist(), int(t_idx.size))
    t_rows = time.perf_counter() - t0
    if want_zoom:
        _fsl_timing_log(
            f"compress ZOOM n={n} total_s={time.perf_counter()-t_all0:.3f} "
            f"d_mask={t_mask:.3f} collapse_ab={t_collapse:.3f} "
            f"update_S={t_S:.3f} id_DE_remap={t_id_remap:.3f} "
            f"n_rows_to_o={t_rows:.3f} "
            f"ns_b={ns_b} n_kept={int(np.count_nonzero(d_mask))} "
            f"n_i_vec={int(i_vec.size)} n_cells={len(n_cells)} "
            f"nt={int(t_idx.size)}"
        )
    return O_new, S


def _id_a_children(id_a: list, f: int) -> list[int]:
    out = []
    for gi, cell in enumerate(id_a, start=1):
        if cell is None:
            continue
        v = int(np.asarray(cell).ravel()[0])
        if v == f:
            out.append(gi)
    return out


def _n_rows_to_o(
    n_cells: dict,
    i_rows: list[int],
    ncols: int,
) -> list:
    O_out = []
    for _g in range(len(i_rows)):
        O_out.append([])
    for gi, row in enumerate(i_rows):
        for c in range(1, ncols + 1):
            key = (int(row), c)
            if key not in n_cells:
                raise KeyError(f"missing N cell {key}")
            col = n_cells[key].astype(np.float64).reshape((-1, 1), order="F")
            O_out[gi].append(col)
    return O_out


def _spm_group_sparse_col(rows_1based: np.ndarray, nrows: int) -> sparse.csr_matrix:
    """MATLAB ``sparse(rows,1,1,nrows,1)`` with 1-based row indices."""
    rows0 = np.asarray(rows_1based, dtype=np.int64).ravel() - 1
    cols0 = np.zeros(rows0.shape[0], dtype=np.int64)
    data = np.ones(rows0.shape[0], dtype=np.float64)
    return sparse.csr_matrix((data, (rows0, cols0)), shape=(int(nrows), 1))


def _spm_group(N, d=None):
    """Local ``spm_group`` from ``spm_faster_structure_learning.m``."""
    N = [int(x) for x in np.asarray(N, dtype=np.int64).ravel().tolist()]
    while len(N) < 4:
        N.append(1)
    N = N[:4]

    if d is None:
        d = [3 if (N[0] % 3 == 0) else 2, 3 if (N[1] % 3 == 0) else 2, 3 if (N[2] % 3 == 0) else 2]
    else:
        d = np.asarray(d, dtype=np.int64).ravel()
        if d.size == 1:
            dv = int(d.flat[0])
            d = [dv, dv, dv]
        else:
            d = [int(d.flat[0]), int(d.flat[1]), int(d.flat[2])]

    r = []
    s = []
    for i in range(3):
        di = min(d[i], N[i])
        d[i] = di
        if N[i] == 0:
            ri = []
        else:
            ri = list(range(0, N[i], di))
        r.append(ri)
        s.append(len(ri))

    L = [r[i][-1] + d[i] for i in range(3)]

    g = []
    n4 = N[3]
    for ii in range(s[0]):
        row_i = []
        for jj in range(s[1]):
            row_j = []
            for kk in range(s[2]):
                rows1 = np.arange(1, d[0] * n4 + 1, dtype=np.int64) + r[0][ii] * n4
                n1 = _spm_group_sparse_col(rows1, int(L[0] * n4))
                rows2 = np.arange(1, d[1] + 1, dtype=np.int64) + r[1][jj]
                n2 = _spm_group_sparse_col(rows2, int(L[1]))
                rows3 = np.arange(1, d[2] + 1, dtype=np.int64) + r[2][kk]
                n3 = _spm_group_sparse_col(rows3, int(L[2]))

                v = np.asarray(spm_cross(n1, n2, n3))
                d1 = N[0] * n4
                d2 = N[1]
                d3 = N[2]
                if v.ndim == 2:
                    v = v[:d1, :d2]
                else:
                    v = v[:d1, :d2, :d3]
                flat = np.ravel(v, order="F")
                row_j.append(np.flatnonzero(flat) + 1)
            row_i.append(row_j)
        g.append(row_i)
    return g


def _spm_structure_fast(O, timing_acc=None):
    """Local ``spm_structure_fast`` from ``spm_faster_structure_learning.m``.

    timing_acc :
        Optional dict updated in-place with cumulative seconds keys
        ``unique``, ``R``, ``a_cat``, ``b_fill``, ``pack``, and ``n_calls``.
        Timing-only; compute path unchanged when ``timing_acc`` is None.
    """
    t0 = time.perf_counter()
    i, j = spm_unique_optim(O)
    t_unique = time.perf_counter() - t0
    i = np.atleast_1d(np.asarray(i, dtype=np.float64))
    j = np.atleast_1d(np.asarray(j, dtype=np.float64))
    if i.ndim == 1:
        i = i.reshape((-1, 1), order="F")
    if j.ndim == 1:
        j = j.reshape((-1, 1), order="F")

    t0 = time.perf_counter()
    ni = int(np.prod(i.shape, dtype=np.int64))
    nj = int(np.prod(j.shape, dtype=np.int64))
    jj = np.asarray(j, dtype=np.int64).ravel(order="F")
    rows_r = np.arange(nj, dtype=np.int64)
    R = sparse.csr_matrix(
        (np.ones(nj, dtype=np.float64), (rows_r, jj - 1)),
        shape=(nj, ni),
    )
    t_R = time.perf_counter() - t0

    t0 = time.perf_counter()
    ng = len(O)
    a = []
    for g in range(ng):
        row_cell = [[O[g][t] for t in range(len(O[g]))]]
        ag = spm_cat(row_cell) @ R
        a.append(ag)
    t_a = time.perf_counter() - t0

    t0 = time.perf_counter()
    ns = ni
    nt = nj - 1
    b = np.zeros((ns, ns, 1), dtype=np.float64)
    jf = np.asarray(j, dtype=np.int64).ravel(order="F")

    for t in range(nt):
        jt = int(jf[t]) - 1
        jtp1 = int(jf[t + 1]) - 1
        seg = b[jtp1, jt, :].ravel()
        nz = np.flatnonzero(seg)
        if nz.size:
            u = int(nz[0])
            b[jtp1, jt, u] += 1.0
        else:
            plane = b[:, jt, :]
            empty = np.flatnonzero(~plane.any(axis=0))
            if empty.size:
                u = int(empty[0])
                b[jtp1, jt, u] = 1.0
            else:
                b = np.concatenate([b, np.zeros((ns, ns, 1), dtype=np.float64)], axis=2)
                b[jtp1, jt, b.shape[2] - 1] = 1.0
    t_b = time.perf_counter() - t0

    t0 = time.perf_counter()
    nu = b.shape[2]
    x0 = np.zeros(ns, dtype=bool)
    mdp_x = []
    for t in range(nt + 1):
        s = x0.copy()
        jidx = int(jf[t]) - 1
        s[jidx] = True
        mdp_x.append(s)
    mdp_x = mdp_x[:nt]

    mdp_p = []
    for t in range(nt):
        jt = int(jf[t]) - 1
        jtp1 = int(jf[t + 1]) - 1
        if nu > 1:
            mdp_p.append(np.asarray(b[jtp1, jt, :].ravel(), dtype=bool))
        else:
            mdp_p.append(np.array(True, dtype=bool))

    mdp = {
        "a": a,
        "b": [b],
        "X": mdp_x,
        "P": mdp_p,
    }
    t_pack = time.perf_counter() - t0
    if timing_acc is not None:
        timing_acc["n_calls"] = int(timing_acc.get("n_calls", 0)) + 1
        timing_acc["unique"] = float(timing_acc.get("unique", 0.0)) + t_unique
        timing_acc["R"] = float(timing_acc.get("R", 0.0)) + t_R
        timing_acc["a_cat"] = float(timing_acc.get("a_cat", 0.0)) + t_a
        timing_acc["b_fill"] = float(timing_acc.get("b_fill", 0.0)) + t_b
        timing_acc["pack"] = float(timing_acc.get("pack", 0.0)) + t_pack
    return mdp, j

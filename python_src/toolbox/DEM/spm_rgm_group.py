"""
OPTIM2FULL native FSL speed twin of ``spm_rgm_group``.

Pass-1 spectral loop plus:

- **Zero-tail:** when no MI-support indices remain in ``active``, emit ascending
  singletons without ``eig``.
- **Weak-B (library default on for native):** while support indices remain, run
  ``eig`` on the **support∩active** block only (not the full padded active
  matrix). Same group *membership* on drone ``dx=1``; peel *order* among
  near-tied support ids may differ from full-matrix Tax. Disable with
  ``RGMS_RGM_WEAK_B=0``. **Off automatically when ``eig_pair`` is set** so
  OPTIM1FULL/OPTIM2FULL **parity** MATLAB injects still see the full active
  block (Product B unchanged).

Historical note: classic FSL1-B closed “support-only ≡ full peel **order**”;
Weak-B accepts that order difference under an explicit native contract (see
``FSL.md`` § Memory: Tax vs Weak-B).
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Callable, List, Optional, Sequence, Tuple

import numpy as np
import scipy.linalg as spla
from scipy.linalg import lapack

from python_src.spm_cat import spm_cat
from python_src.spm_MDP_MI import spm_MDP_MI


def _weak_b_enabled() -> bool:
    """``RGMS_RGM_WEAK_B`` — default **on** for Weak-B test implementation."""
    raw = str(os.getenv("RGMS_RGM_WEAK_B", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")

def _sort_abs_descend_matlab_like(absv: np.ndarray) -> np.ndarray:
    """MATLAB ``sort(abs(e(:,jmax)),'descend')`` — ``eig_spectral_policy`` (optional tie-band §4.1 B5.3)."""
    from python_src.utils.eig_spectral_policy import sort_abs_descend_for_spm_rgm

    return sort_abs_descend_for_spm_rgm(absv)


def _spm_mdp_mi_scalar(p: np.ndarray) -> float:
    """Single-output `spm_MDP_MI(p)` (mutual information term only)."""
    out = spm_MDP_MI(np.asarray(p, dtype=np.float64))
    if isinstance(out, tuple):
        v = out[0]
    else:
        v = out
    return float(np.real(np.asarray(v, dtype=float)).reshape(-1)[0])


def _spm_cat_row(cells: Sequence[Any]) -> np.ndarray:
    """Horizontal concatenation of one row of cells (MATLAB `spm_cat(R(o,:))`)."""
    nt = len(cells)
    time_mode = _env_text("RGMS_RGM_EXPERIMENT_R_TIME_ORDER")
    if time_mode in ("rev", "reverse", "backward"):
        t_seq = range(nt - 1, -1, -1)
    elif time_mode in ("", "fwd", "forward", "default", "none", "off", "0", "false", "no"):
        t_seq = range(nt)
    else:
        raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_R_TIME_ORDER mode: {time_mode!r}")
    row = [[cells[t] for t in t_seq]]
    cat = spm_cat(row)
    if hasattr(cat, "toarray"):
        cat = cat.toarray()
    return np.asarray(cat, dtype=np.float64)


def _kron_modal_chain(vecs: Sequence[np.ndarray]) -> np.ndarray:
    """Kronecker stack for one composite outcome (MATLAB ``p = O{o,t}; for r=1:m-1 ...``).

    Default matches ``spm_rgm_group.m``. Optional chains are diagnostics-only for
    ``m>1``; when ``m==1`` all modes reduce to the single modality vector.
    """
    mode = _env_text("RGMS_RGM_EXPERIMENT_R_KRON_CHAIN")
    vlist = [np.asarray(v, dtype=np.float64) for v in vecs]
    m = len(vlist)
    if m == 0:
        raise ValueError("spm_rgm_group: empty modality list for Kronecker chain")
    if mode in ("", "matlab", "default", "fwd", "none", "off", "0", "false", "no"):
        p = vlist[0]
        for r in range(1, m):
            p = np.kron(p, vlist[r])
        return p
    if mode in ("rev_assoc", "right_deep_rev"):
        # kron(v_{m-1}, kron(v_{m-2}, ... kron(v_1, v_0)...)) — not MATLAB-default.
        p = vlist[m - 1]
        for r in range(m - 2, -1, -1):
            p = np.kron(p, vlist[r])
        return p
    if mode in ("left_deep_swap", "swap", "left_deep"):
        # kron(v_{m-1}, kron(v_{m-2}, ... kron(v_1, v_0))) — not MATLAB-default.
        p = vlist[0]
        for r in range(1, m):
            p = np.kron(vlist[r], p)
        return p
    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_R_KRON_CHAIN mode: {mode!r}")


EigPairFn = Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]


def _normalize_eig_vals(vals: np.ndarray) -> np.ndarray:
    """Return eigenvalues as a 1-D vector from either vector or square matrix input."""
    arr = np.asarray(vals, dtype=np.complex128)
    if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
        # MATLAB's second `eig` output is a diagonal matrix; SciPy returns a vector.
        return np.diag(arr).astype(np.complex128, copy=False).ravel(order="F")
    return arr.ravel(order="F")


def _env_flag(name: str) -> bool:
    v = str(os.getenv(name, "")).strip().lower()
    return v not in ("", "0", "false", "no", "off")


def _env_text(name: str) -> str:
    return str(os.getenv(name, "")).strip().lower()


def _eig_dgeev_real(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute eigenpairs through raw LAPACK dgeev for experiment parity checks."""
    wr, wi, _vl, vr, info = lapack.dgeev(
        np.asarray(a, dtype=np.float64), compute_vl=0, compute_vr=1
    )
    if int(info) != 0:
        raise RuntimeError(f"dgeev failed with info={int(info)}")
    vals = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    vals = np.asarray(vals, dtype=np.complex128).ravel(order="F")
    vr = np.asarray(vr, dtype=np.float64)
    n = int(vr.shape[0])
    vecs = np.zeros((n, n), dtype=np.complex128)
    k = 0
    while k < n:
        if abs(float(wi[k])) < 1e-300:
            vecs[:, k] = vr[:, k]
            k += 1
        else:
            vecs[:, k] = vr[:, k] + 1j * vr[:, k + 1]
            vecs[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
            k += 2
    return vals, vecs


def _condition_submatrix(a: np.ndarray) -> np.ndarray:
    """Optional global conditioning experiments before eig (disabled by default)."""
    mode = _env_text("RGMS_RGM_EXPERIMENT_SUB_CONDITION")
    x = np.asarray(a, dtype=np.float64)
    if mode in ("", "none", "off", "0", "false", "no"):
        return x

    if mode in ("scale_maxabs", "scale"):
        m = float(np.max(np.abs(x))) if x.size else 0.0
        return x if m == 0.0 else (x / m)

    if mode in ("psd_clip", "psd"):
        vals, vecs = np.linalg.eigh(x)
        vals = np.maximum(np.asarray(vals, dtype=np.float64), 0.0)
        y = (vecs @ np.diag(vals) @ vecs.T).astype(np.float64, copy=False)
        return 0.5 * (y + y.T)

    if mode in ("scale_psd", "scale_then_psd"):
        m = float(np.max(np.abs(x))) if x.size else 0.0
        y = x if m == 0.0 else (x / m)
        vals, vecs = np.linalg.eigh(y)
        vals = np.maximum(np.asarray(vals, dtype=np.float64), 0.0)
        y = (vecs @ np.diag(vals) @ vecs.T).astype(np.float64, copy=False)
        return 0.5 * (y + y.T)

    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_SUB_CONDITION mode: {mode!r}")


def _mi_pair_matrix(ri: np.ndarray, rj: np.ndarray) -> np.ndarray:
    """Build pairwise MI input matrix with optional formation-order experiments."""
    mode = _env_text("RGMS_RGM_EXPERIMENT_MI_FORMATION")
    a = np.asarray(ri, dtype=np.float64)
    b = np.asarray(rj, dtype=np.float64)
    if mode in ("", "none", "off", "0", "false", "no", "matmul", "default"):
        return a @ b.T
    if mode in ("fortran_matmul", "f_matmul"):
        return np.asfortranarray(a) @ np.asfortranarray(b).T
    if mode in ("outer_fwd", "kron_fwd"):
        out = np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)
        for k in range(int(a.shape[1])):
            out += np.outer(a[:, k], b[:, k])
        return out
    if mode in ("outer_rev", "kron_rev"):
        out = np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)
        for k in range(int(a.shape[1]) - 1, -1, -1):
            out += np.outer(a[:, k], b[:, k])
        return out
    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_MI_FORMATION mode: {mode!r}")


class _RgmTimeSegments:
    """Live segment printer for OPTIM2FULL native FSL profiling (``time_segments=True``)."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.t0 = time.perf_counter()
        self.phases: dict[str, float] = {}
        self._hb_wall = self.t0
        self.mi_pairs_done = 0
        self.mi_pairs_skipped = 0
        self.mi_pairs_active_est = 0
        self.t_mi_pair_mat = 0.0
        self.t_mi_spm = 0.0
        self.t_mi_est = 0.0
        self.t_mi_alloc = 0.0
        self.t_eig_running = 0.0
        # Cumulative within-EIG-iter sub-timers (seconds)
        self.t_eig_extract = 0.0
        self.t_eig_sym = 0.0
        self.t_eig_condition = 0.0
        self.t_eig_call = 0.0
        self.t_eig_post = 0.0
        self.t_eig_py_book = 0.0
        self.t_eig_mask = 0.0
        self.last_sub: dict[str, float] = {}
        self.last_meta: dict[str, object] = {}
        self.support_1based: set[int] = set()
        self.peel_in_support = 0
        self.peel_out_support = 0
        self.peel_log: list[str] = []

    @staticmethod
    def _rss_mb() -> float:
        """Best-effort process RSS in MiB (NaN if unavailable)."""
        try:
            import psutil  # type: ignore

            return float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
        except Exception:
            pass
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            psapi = ctypes.WinDLL("psapi")
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            GetProcessMemoryInfo = psapi.GetProcessMemoryInfo
            GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
                wintypes.DWORD,
            ]
            GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            handle = kernel32.GetCurrentProcess()
            if GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return float(counters.WorkingSetSize) / (1024.0 * 1024.0)
        except Exception:
            pass
        return float("nan")

    def _cum(self) -> float:
        return float(time.perf_counter() - self.t0)

    def log(self, msg: str) -> None:
        if self.enabled:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[rgm_timing] {ts} cum_s={self._cum():.3f} {msg}", flush=True)

    def phase_start(self, name: str) -> float:
        if self.enabled:
            self.log(f"START {name}")
        return time.perf_counter()

    def phase_end(self, name: str, t0: float, detail: str = "") -> None:
        dt = float(time.perf_counter() - t0)
        self.phases[name] = dt
        if self.enabled:
            extra = f" {detail}" if detail else ""
            self.log(f"END   {name}{extra} elapsed_s={dt:.3f}")

    def mi_heartbeat(
        self,
        *,
        i: int,
        j: int,
        force: bool = False,
        heartbeat_pairs: int = 500,
        heartbeat_wall_s: float = 15.0,
    ) -> None:
        if not self.enabled:
            return
        now = time.perf_counter()
        due_pairs = (
            self.mi_pairs_done > 0
            and self.mi_pairs_done % int(heartbeat_pairs) == 0
        )
        due_wall = (now - self._hb_wall) >= float(heartbeat_wall_s)
        if not (force or due_pairs or due_wall):
            return
        self._hb_wall = now
        rate = self.mi_pairs_done / max(now - self.t0, 1e-9)
        remain = max(self.mi_pairs_active_est - self.mi_pairs_done, 0)
        eta_s = remain / rate if rate > 0 else float("inf")
        self.log(
            f"MI progress i={i} j={j} "
            f"pairs_done={self.mi_pairs_done}/{self.mi_pairs_active_est} "
            f"skipped={self.mi_pairs_skipped} "
            f"rate_pairs_per_s={rate:.2f} eta_s={eta_s:.0f} "
            f"t_pair_mat={self.t_mi_pair_mat:.3f} t_spm_MDP_MI={self.t_mi_spm:.3f}"
        )

    def eig_peel_log(
        self,
        *,
        iter_idx: int,
        chosen: np.ndarray,
    ) -> None:
        """FSL1-A: every-iter chosen ids vs MI-support set (``time_segments`` only)."""
        if not self.enabled:
            return
        ch = [int(x) for x in np.asarray(chosen, dtype=np.int64).ravel().tolist()]
        n_in = sum(1 for c in ch if c in self.support_1based)
        n_out = len(ch) - n_in
        self.peel_in_support += n_in
        self.peel_out_support += n_out
        line = (
            f"EIG peel iter={iter_idx} chosen={ch} "
            f"in_support={n_in}/{len(ch)} out_support={n_out} "
            f"cum_peel_in={self.peel_in_support} cum_peel_out={self.peel_out_support}"
        )
        self.peel_log.append(line)
        self.log(line)

    def eig_heartbeat(
        self,
        *,
        iter_idx: int,
        active_size: int,
        active_after: int,
        sub_shape: tuple[int, int],
        iter_elapsed: float,
        n_chosen: int,
        e_top_max: float,
        e_top_min: float,
        force: bool = False,
        heartbeat_iters: int = 25,
        heartbeat_wall_s: float = 15.0,
    ) -> None:
        if not self.enabled:
            return
        now = time.perf_counter()
        due_iter = iter_idx > 0 and iter_idx % int(heartbeat_iters) == 0
        due_wall = (now - self._hb_wall) >= float(heartbeat_wall_s)
        if not (force or due_iter or due_wall):
            return
        self._hb_wall = now
        ls = self.last_sub
        lm = self.last_meta
        self.log(
            f"EIG iter={iter_idx} active={active_size}->{active_after} "
            f"sub={sub_shape} n_chosen={n_chosen} "
            f"e_top_max={e_top_max:.6g} e_top_min={e_top_min:.6g} "
            f"iter_s={iter_elapsed:.4f} "
            f"extract={ls.get('extract', 0):.4f}"
            f"(ix={ls.get('extract_ix', 0):.4f}+arr={ls.get('extract_arr', 0):.4f}) "
            f"sym={ls.get('sym', 0):.4f}"
            f"(add={ls.get('sym_add', 0):.4f}+scale={ls.get('sym_scale', 0):.4f}) "
            f"cond={ls.get('condition', 0):.4f} "
            f"eig_call={ls.get('eig_call', 0):.4f} backend={lm.get('eig_backend', '?')} "
            f"post={ls.get('post', 0):.4f}"
            f"(norm={ls.get('post_norm', 0):.4f}+argmax={ls.get('post_argmax', 0):.4f}"
            f"+abs={ls.get('post_abs', 0):.4f}+sort={ls.get('post_sort', 0):.4f}"
            f"+thr={ls.get('post_thr', 0):.4f}) "
            f"py_book={ls.get('py_book', 0):.4f} mask={ls.get('mask', 0):.4f} "
            f"sub_sym_resid={lm.get('sub_sym_resid', float('nan'))} "
            f"sub_C={lm.get('sub_c_contig', '?')} sub_F={lm.get('sub_f_contig', '?')} "
            f"sub_owndata={lm.get('sub_owndata', '?')} "
            f"rss_before_mb={lm.get('rss_before_mb', float('nan'))} "
            f"rss_after_mb={lm.get('rss_after_mb', float('nan'))} "
            f"eig_cum_s={self.t_eig_running:.3f} "
            f"cum_extract={self.t_eig_extract:.3f} cum_eig_call={self.t_eig_call:.3f} "
            f"cum_sym={self.t_eig_sym:.3f} cum_post={self.t_eig_post:.3f}"
        )

    def summary(self) -> None:
        if not self.enabled:
            return
        parts = " ".join(f"{k}={v:.3f}" for k, v in self.phases.items())
        self.log(f"DONE total_s={self._cum():.3f} phases: {parts}")
        if self.t_eig_running > 0:
            self.log(
                f"EIG_SUBTOTALS extract={self.t_eig_extract:.3f} "
                f"sym={self.t_eig_sym:.3f} condition={self.t_eig_condition:.3f} "
                f"eig_call={self.t_eig_call:.3f} post={self.t_eig_post:.3f} "
                f"py_book={self.t_eig_py_book:.3f} mask={self.t_eig_mask:.3f} "
                f"iter_sum={self.t_eig_running:.3f}"
            )


def spm_rgm_group(
    O: Sequence[Sequence[Any]],
    dx: int = 16,
    m: int = 1,
    *,
    eig_pair: Optional[EigPairFn] = None,
    mi_override: Optional[np.ndarray] = None,
    spectral_probe_fn: Optional[Callable[[dict], None]] = None,
    time_segments: bool = False,
) -> List[np.ndarray]:
    """
    FORMAT G = spm_rgm_group(O,dx)
    FORMAT G = spm_rgm_group(O,dx,m)

    Parameters
    ----------
    O :
        ``No × Nt`` layout: outer index outcome ``o`` (0-based), inner time ``t``.
        Each entry is array-like (column vector / matrix as in MATLAB ``O{o,t}``).
    dx :
        Upper bound on group size (default 16).
    m :
        Modalities per outcome (default 1). ``O`` must have ``No`` divisible by ``m``.
    eig_pair :
        Optional ``(sub) -> (vals, vecs)`` replacing ``scipy.linalg.eig`` on each
        active ``MI(i,i)`` block. Must match SciPy convention: ``vals`` length ``n``
        (one eigenvalue per column), ``vecs`` shape ``(n, n)`` with eigenvectors as
        columns. Intended for oracle / MATLAB-numeric bridges only (default ``None``
        uses SciPy).
    mi_override :
        Optional composite-layout ``MI`` matrix of shape ``(no, no)`` to use instead
        of values from :func:`_spm_mdp_mi_scalar`. With a MATLAB ``eig_pair``, this
        carries MATLAB’s exact ``MI`` bytes so the spectral while-loop matches
        ``spm_rgm_group.m``. Default ``None`` builds ``MI`` from ``O`` as in MATLAB.
    spectral_probe_fn :
        Optional callback receiving per-iteration spectral workload records for
        capture/replay diagnostics. Oracle-only; omitted in production usage.
    time_segments :
        When ``True``, emit live ``[rgm_timing]`` segment and heartbeat lines
        (default ``False`` — identical silence and behavior to pre-instrumentation).

    Returns
    -------
    G :
        List of ``int64`` 1-based index vectors (MATLAB ``G{g}``), after expansion
        from composite outcomes to original modality rows.
    """
    ts = _RgmTimeSegments(time_segments)
    no_orig = len(O)
    nt = len(O[0]) if no_orig else 0
    ts.log(
        f"BEGIN No_orig={no_orig} Nt={nt} dx={dx} m={m} "
        f"mi_override={'on' if mi_override is not None else 'off'} "
        f"eig_pair={'on' if eig_pair is not None else 'off'}"
    )

    if no_orig == 0:
        ts.summary()
        return []
    if no_orig < dx:
        ts.log(f"EARLY_RETURN single_group No={no_orig} < dx={dx}")
        ts.summary()
        return [np.arange(1, no_orig + 1, dtype=np.int64)]

    if no_orig % m != 0:
        raise ValueError(
            f"spm_rgm_group: number of outcomes No={no_orig} must be divisible by m={m}"
        )

    n_comp = no_orig // m
    t0 = ts.phase_start("kron_r_grid")
    r_grid: List[List[np.ndarray]] = [
        [None] * nt for _ in range(n_comp)  # type: ignore[misc]
    ]
    for t in range(nt):
        i = 0
        for o in range(0, no_orig, m):
            vecs = [np.asarray(O[o + r][t], dtype=np.float64) for r in range(m)]
            r_grid[i][t] = _kron_modal_chain(vecs)
            i += 1
    ex_shape = None
    if r_grid and r_grid[0] and r_grid[0][0] is not None:
        ex_shape = tuple(np.asarray(r_grid[0][0]).shape)
    ts.phase_end(
        "kron_r_grid",
        t0,
        f"n_comp={n_comp} nt={nt} example_shape={ex_shape}",
    )

    no = n_comp
    t0 = ts.phase_start("cat_flags")
    n_flags = np.zeros(no, dtype=bool)
    r_cells: List[np.ndarray] = []
    for o in range(no):
        r_o = _spm_cat_row(r_grid[o])
        r_cells.append(r_o)
        d = np.diff(r_o, axis=1)
        n_flags[o] = bool(np.any(np.abs(d) > 1e-14))
    n_active = int(np.sum(n_flags))
    ex_r = tuple(r_cells[0].shape) if r_cells else None
    active_ids_1based = (np.flatnonzero(n_flags) + 1).astype(np.int64)
    ts.phase_end(
        "cat_flags",
        t0,
        f"no={no} n_active={n_active} n_inactive={no - n_active} "
        f"r_shape={ex_r} active_ids_1based={active_ids_1based.tolist()}",
    )

    if mi_override is None:
        t_est0 = time.perf_counter()
        ts.mi_pairs_active_est = int(
            sum(
                1
                for ii in range(no)
                for jj in range(ii, no)
                if n_flags[ii] and n_flags[jj]
            )
        )
        ts.t_mi_est = float(time.perf_counter() - t_est0)
        ts.log(
            f"MI_EST pairs_active_est={ts.mi_pairs_active_est} "
            f"elapsed_s={ts.t_mi_est:.3f}"
        )
        t_alloc0 = time.perf_counter()
        mi = np.zeros((no, no), dtype=np.float64)
        ts.t_mi_alloc = float(time.perf_counter() - t_alloc0)
        mi_nbytes = int(mi.nbytes)
        ts.log(
            f"MI_BUILD START no={no} pairs_active_est={ts.mi_pairs_active_est} "
            f"mi_shape={mi.shape} mi_nbytes={mi_nbytes} "
            f"mi_nbytes_mb={mi_nbytes / (1024 * 1024):.2f} "
            f"alloc_s={ts.t_mi_alloc:.3f}"
        )
        t_mi0 = time.perf_counter()
        for i in range(no):
            for j in range(i, no):
                if n_flags[i] and n_flags[j]:
                    t_p0 = time.perf_counter()
                    p = _mi_pair_matrix(r_cells[i], r_cells[j])
                    ts.t_mi_pair_mat += time.perf_counter() - t_p0
                    t_s0 = time.perf_counter()
                    val = _spm_mdp_mi_scalar(p)
                    ts.t_mi_spm += time.perf_counter() - t_s0
                    mi[i, j] = val
                    mi[j, i] = val
                    ts.mi_pairs_done += 1
                    ts.mi_heartbeat(i=i, j=j)
                else:
                    ts.mi_pairs_skipped += 1
        ts.phases["mi_build"] = float(time.perf_counter() - t_mi0)
        t_loop_oh = (
            ts.phases["mi_build"] - ts.t_mi_pair_mat - ts.t_mi_spm
        )
        ts.mi_heartbeat(i=no - 1, j=no - 1, force=True)
        nnz_ut = int(np.count_nonzero(np.triu(mi)))
        ts.log(
            f"MI_BUILD END pairs_done={ts.mi_pairs_done} skipped={ts.mi_pairs_skipped} "
            f"elapsed_s={ts.phases['mi_build']:.3f} "
            f"t_pair_mat={ts.t_mi_pair_mat:.3f} t_spm_MDP_MI={ts.t_mi_spm:.3f} "
            f"t_mi_loop_overhead={t_loop_oh:.3f} "
            f"t_mi_est={ts.t_mi_est:.3f} t_mi_alloc={ts.t_mi_alloc:.3f} "
            f"nnz_triu={nnz_ut} mi_nbytes_mb={mi_nbytes / (1024 * 1024):.2f}"
        )
    else:
        t0 = ts.phase_start("mi_override_load")
        mi = np.asarray(mi_override, dtype=np.float64)
        if mi.shape != (no, no):
            raise ValueError(
                f"spm_rgm_group: mi_override shape {mi.shape} != ({no}, {no})"
            )
        ts.phase_end(
            "mi_override_load",
            t0,
            f"shape={mi.shape} nbytes={int(mi.nbytes)}",
        )

    dx = int(np.fix(dx))
    u_thresh = float(np.exp(-16.0))

    active = np.arange(1, no + 1, dtype=np.int64)
    groups: List[np.ndarray] = []

    iter_idx = 0
    t_eig_all = time.perf_counter()
    n_mi_nnz_rows = int(np.count_nonzero(np.any(mi != 0.0, axis=1)))
    n_mi_nnz = int(np.count_nonzero(mi))
    # n_flags exists when MI was built from O; for mi_override treat as unknown.
    n_active_flags = int(np.sum(n_flags)) if "n_flags" in locals() else -1
    support_idx0 = np.flatnonzero(np.any(mi != 0.0, axis=1))
    ts.support_1based = {int(i) + 1 for i in support_idx0.tolist()}
    # Native Weak-B only. Parity ``eig_pair`` (MATLAB eig on the active MI block)
    # must keep the full active domain so injects match MATLAB grouping.
    weak_b = bool(_weak_b_enabled() and eig_pair is None)
    ts.log(
        f"EIG_PARTITION START no={no} dx={dx} U={u_thresh:.6g} "
        f"active0={active.size} n_active_flags={n_active_flags} "
        f"n_mi_nnz_rows={n_mi_nnz_rows} n_mi_nnz={n_mi_nnz} "
        f"support_ids_1based={sorted(ts.support_1based)} "
        f"mi_dtype={mi.dtype} mi_nbytes_mb={int(mi.nbytes) / (1024 * 1024):.2f} "
        f"weak_b={'on' if weak_b else 'off'} "
        f"eig_pair={'on' if eig_pair is not None else 'off'} "
        f"NOTE="
        + (
            "Weak-B: eig on support∩active only while support remains"
            if weak_b
            else (
                "full_active_spectral (eig_pair forces full block for parity)"
                if eig_pair is not None
                else "spectral_loop_uses_full_active0_not_only_flagged_outcomes"
            )
        )
    )
    while active.size > 0:
        iter_idx += 1
        t_iter0 = time.perf_counter()
        # FSL4a-Tax: copy active only when diagnostics need a frozen snapshot.
        need_active_snap = bool(
            ts.enabled or spectral_probe_fn is not None or eig_pair is not None
        )
        active_before = (
            np.asarray(active, dtype=np.int64, copy=True) if need_active_snap else active
        )

        # FSL1-B-alt bulk zero-tail: no MI-support indices remain → remaining
        # groups are singletons in current active order (FSL1-A: ascending).
        if ts.support_1based and ts.support_1based.isdisjoint(
            int(i) for i in np.asarray(active, dtype=np.int64).ravel().tolist()
        ):
            for i in np.asarray(active, dtype=np.int64).ravel().tolist():
                groups.append(np.asarray([int(i)], dtype=np.int64))
            if ts.enabled:
                ts.log(
                    f"EIG zero_tail_bulk n_singletons={active.size} "
                    f"skipped_eigs={active.size}"
                )
            active = np.asarray([], dtype=np.int64)
            iter_elapsed = float(time.perf_counter() - t_iter0)
            ts.t_eig_running += iter_elapsed
            break

        # Spectral domain: full active, or Weak-B support∩active.
        act_full = np.asarray(active, dtype=np.int64).ravel()
        if weak_b and ts.support_1based:
            eig_active = np.asarray(
                [int(i) for i in act_full.tolist() if int(i) in ts.support_1based],
                dtype=np.int64,
            )
        else:
            eig_active = act_full

        t_x0 = time.perf_counter()
        sub = np.asarray(mi[np.ix_(eig_active - 1, eig_active - 1)], dtype=np.float64)
        dt_extract_ix = float(time.perf_counter() - t_x0)
        dt_extract_arr = 0.0
        dt_extract = dt_extract_ix

        t_s0 = time.perf_counter()
        # `MI` should be symmetric; enforce exact symmetry to match MATLAB's treatment
        # of the mutual-information matrix as a real symmetric operator in this path.
        sub = 0.5 * (sub + sub.T)
        dt_sym = float(time.perf_counter() - t_s0)
        dt_sym_add = dt_sym
        dt_sym_scale = 0.0

        t_c0 = time.perf_counter()
        sub = _condition_submatrix(sub)
        # Optional global conditioning experiment: quantize submatrix to 15 decimals
        # before eig. This is diagnostics-only and remains disabled by default.
        if _env_flag("RGMS_RGM_EXPERIMENT_SUB_ROUND15"):
            sub = np.round(sub, decimals=15)
        dt_cond = float(time.perf_counter() - t_c0)

        # FSL4a-Tax: ``sub - sub.T`` resid is diagnostics-only (extra full-matrix tax).
        sub_sym_resid = (
            float(np.max(np.abs(sub - sub.T))) if (ts.enabled and sub.size) else 0.0
        )
        eig_backend = "scipy.linalg.eig"
        use_dgeev = _env_flag("RGMS_RGM_EXPERIMENT_USE_DGEEV")
        if use_dgeev:
            eig_backend = "dgeev_real"
        rss_before = ts._rss_mb() if ts.enabled else float("nan")

        # Zero-tail shortcut (FSL1-B-alt): all-zero active block → peel active[:dx]
        # without eig. Drone FSL1-A: after support peels, remaining are ascending
        # singletons; full eig on zeros is pure cost.
        zero_tail = sub.size == 0 or (not np.any(sub))
        if zero_tail:
            eig_backend = "zero_tail_skip_eig"
            eig_source = "zero_tail"
            t_e0 = time.perf_counter()
            # Peel from full active (ascending remainder), not eig_active.
            n_take = min(int(dx), int(act_full.size))
            j_take = np.arange(n_take, dtype=np.int64)
            e_top_kept = np.ones(n_take, dtype=np.float64)
            chosen = act_full[j_take]
            dt_eig_call = float(time.perf_counter() - t_e0)
            rss_after = ts._rss_mb() if ts.enabled else float("nan")
            dt_post = 0.0
            dt_post_norm = dt_post_argmax = dt_post_abs = dt_post_sort = dt_post_thr = 0.0
            dt_py_book = 0.0
            vals_py = vecs_py = vals = vecs = None
            vals_mat = vecs_mat = None
            jmax = jmax_py = jmax_mat = None
            absv = absv_py = absv_mat = None
            order = order_py = order_mat = None
            chosen_py = chosen_mat = None
            # j_take indexes act_full for removal below
        else:
            # time_segments-only diagnostic: compare symmetric eigh cost on iter 1.
            if ts.enabled and iter_idx == 1:
                t_eh0 = time.perf_counter()
                try:
                    _vals_eh, _vecs_eh = spla.eigh(
                        sub, check_finite=False, overwrite_a=False
                    )
                    del _vals_eh, _vecs_eh
                    dt_eigh_diag = float(time.perf_counter() - t_eh0)
                except Exception as exc:  # pragma: no cover
                    dt_eigh_diag = float("nan")
                    ts.log(f"EIG_DIAG eigh_failed err={type(exc).__name__}:{exc}")
                else:
                    ts.log(
                        f"EIG_DIAG iter=1 eigh_discard_s={dt_eigh_diag:.4f} "
                        f"(not used for grouping; compares vs general eig below)"
                    )

            t_e0 = time.perf_counter()
            if use_dgeev:
                vals_py, vecs_py = _eig_dgeev_real(sub)
            else:
                vals_py, vecs_py = spla.eig(
                    sub, check_finite=False, overwrite_a=False
                )
            vals_mat = None
            vecs_mat = None
            if eig_pair is None:
                vals, vecs = vals_py, vecs_py
                eig_source = "scipy"
            else:
                vals_mat, vecs_mat = eig_pair(sub)
                vals, vecs = vals_mat, vecs_mat
                eig_source = "eig_pair"
                eig_backend = "eig_pair"
            dt_eig_call = float(time.perf_counter() - t_e0)
            rss_after = ts._rss_mb() if ts.enabled else float("nan")

            # FSL4a-Tax: normalize/reshape the *used* eigenpair once (peel authority).
            t_p0 = time.perf_counter()
            vals = _normalize_eig_vals(vals)
            vecs = np.asarray(vecs, dtype=np.complex128)
            if vecs.shape != sub.shape:
                vecs = np.reshape(vecs, sub.shape, order="F")
            if eig_pair is None:
                # Same object path as SciPy — keep aliases for optional diagnostics.
                vals_py, vecs_py = vals, vecs
            else:
                vals_py = _normalize_eig_vals(vals_py)
                vecs_py = np.asarray(vecs_py, dtype=np.complex128)
                if vecs_py.shape != sub.shape:
                    vecs_py = np.reshape(vecs_py, sub.shape, order="F")
            dt_post_norm = float(time.perf_counter() - t_p0)

            t_pa0 = time.perf_counter()
            jmax = int(np.argmax(np.abs(vals)))
            col = vecs[:, jmax]
            dt_post_argmax = float(time.perf_counter() - t_pa0)

            t_pb0 = time.perf_counter()
            absv = np.asarray(np.abs(col), dtype=np.float64).ravel()
            if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
                absv = np.round(absv, decimals=15)
            dt_post_abs = float(time.perf_counter() - t_pb0)

            t_ps0 = time.perf_counter()
            order = _sort_abs_descend_matlab_like(absv)
            dt_post_sort = float(time.perf_counter() - t_ps0)

            t_pt0 = time.perf_counter()
            j_take = order[: min(len(order), dx)]
            e_top = absv[j_take]
            keep = e_top >= u_thresh
            j_take = j_take[keep]
            e_top_kept = e_top[keep]
            chosen = eig_active[j_take]
            dt_post_thr = float(time.perf_counter() - t_pt0)
            dt_post = (
                dt_post_norm
                + dt_post_argmax
                + dt_post_abs
                + dt_post_sort
                + dt_post_thr
            )

            # FSL4a-Tax: duplicate SciPy-vs-use bookkeeping only when profiling/probe/eig_pair.
            need_py_book = bool(
                ts.enabled or spectral_probe_fn is not None or eig_pair is not None
            )
            t_b0 = time.perf_counter()
            if need_py_book:
                if eig_pair is None:
                    jmax_py = jmax
                    absv_py = absv
                    order_py = order
                    chosen_py = np.asarray(chosen, dtype=np.int64)
                else:
                    jmax_py = int(np.argmax(np.abs(vals_py)))
                    col_py = vecs_py[:, jmax_py]
                    absv_py = np.asarray(np.abs(col_py), dtype=np.float64).ravel()
                    if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
                        absv_py = np.round(absv_py, decimals=15)
                    order_py = _sort_abs_descend_matlab_like(absv_py)
                    j_take_py = order_py[: min(len(order_py), dx)]
                    e_top_py = absv_py[j_take_py]
                    j_take_py = j_take_py[e_top_py >= u_thresh]
                    chosen_py = active_before[j_take_py]
                if vals_mat is not None and vecs_mat is not None:
                    vals_mat = _normalize_eig_vals(vals_mat)
                    vecs_mat = np.asarray(vecs_mat, dtype=np.complex128)
                    if vecs_mat.shape != sub.shape:
                        vecs_mat = np.reshape(vecs_mat, sub.shape, order="F")
                    jmax_mat = int(np.argmax(np.abs(vals_mat)))
                    col_mat = vecs_mat[:, jmax_mat]
                    absv_mat = np.asarray(np.abs(col_mat), dtype=np.float64).ravel()
                    if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
                        absv_mat = np.round(absv_mat, decimals=15)
                    order_mat = _sort_abs_descend_matlab_like(absv_mat)
                    j_take_mat = order_mat[: min(len(order_mat), dx)]
                    e_top_mat = absv_mat[j_take_mat]
                    j_take_mat = j_take_mat[e_top_mat >= u_thresh]
                    chosen_mat = active_before[j_take_mat]
                else:
                    jmax_mat = None
                    absv_mat = None
                    order_mat = None
                    chosen_mat = None
                if spectral_probe_fn is not None:
                    spectral_probe_fn(
                        {
                            "iter_idx": int(iter_idx),
                            "m": int(m),
                            "dx": int(dx),
                            "u_thresh": float(u_thresh),
                            "active_before": np.asarray(
                                active_before, dtype=np.int64, copy=True
                            ),
                            "sub_mi": np.asarray(sub, dtype=np.float64, copy=True),
                            "eig_source": str(eig_source),
                            "vals_py": np.asarray(vals_py, dtype=np.complex128, copy=True),
                            "vecs_py": np.asarray(vecs_py, dtype=np.complex128, copy=True),
                            "jmax_py": int(jmax_py),
                            "absv_py": np.asarray(absv_py, dtype=np.float64, copy=True),
                            "order_py": np.asarray(order_py, dtype=np.int64, copy=True),
                            "chosen_py": np.asarray(chosen_py, dtype=np.int64, copy=True),
                            "vals_use": np.asarray(vals, dtype=np.complex128, copy=True),
                            "vecs_use": np.asarray(vecs, dtype=np.complex128, copy=True),
                            "jmax_use": int(jmax),
                            "absv_use": np.asarray(absv, dtype=np.float64, copy=True),
                            "order_use": np.asarray(order, dtype=np.int64, copy=True),
                            "chosen_use": np.asarray(chosen, dtype=np.int64, copy=True),
                            "vals_mat": None
                            if vals_mat is None
                            else np.asarray(vals_mat, dtype=np.complex128, copy=True),
                            "vecs_mat": None
                            if vecs_mat is None
                            else np.asarray(vecs_mat, dtype=np.complex128, copy=True),
                            "jmax_mat": jmax_mat,
                            "absv_mat": None
                            if absv_mat is None
                            else np.asarray(absv_mat, dtype=np.float64, copy=True),
                            "order_mat": None
                            if order_mat is None
                            else np.asarray(order_mat, dtype=np.int64, copy=True),
                            "chosen_mat": None
                            if chosen_mat is None
                            else np.asarray(chosen_mat, dtype=np.int64, copy=True),
                        }
                    )
                dt_py_book = float(time.perf_counter() - t_b0)
            else:
                jmax_py = jmax_mat = None
                absv_py = absv_mat = None
                order_py = order_mat = None
                chosen_py = chosen_mat = None
                dt_py_book = 0.0

        groups.append(chosen.astype(np.int64))
        t_m0 = time.perf_counter()
        # Always remove by chosen ids (correct for both full-active and Weak-B domains).
        chos = {int(x) for x in np.asarray(chosen, dtype=np.int64).ravel().tolist()}
        active = np.asarray(
            [int(i) for i in act_full.tolist() if int(i) not in chos],
            dtype=np.int64,
        )
        dt_mask = float(time.perf_counter() - t_m0)

        iter_elapsed = float(time.perf_counter() - t_iter0)
        ts.t_eig_running += iter_elapsed
        ts.t_eig_extract += dt_extract
        ts.t_eig_sym += dt_sym
        ts.t_eig_condition += dt_cond
        ts.t_eig_call += dt_eig_call
        ts.t_eig_post += dt_post
        ts.t_eig_py_book += dt_py_book
        ts.t_eig_mask += dt_mask
        ts.last_sub = {
            "extract": dt_extract,
            "extract_ix": dt_extract_ix,
            "extract_arr": dt_extract_arr,
            "sym": dt_sym,
            "sym_add": dt_sym_add,
            "sym_scale": dt_sym_scale,
            "condition": dt_cond,
            "eig_call": dt_eig_call,
            "post": dt_post,
            "post_norm": dt_post_norm,
            "post_argmax": dt_post_argmax,
            "post_abs": dt_post_abs,
            "post_sort": dt_post_sort,
            "post_thr": dt_post_thr,
            "py_book": dt_py_book,
            "mask": dt_mask,
        }
        ts.last_meta = {
            "eig_backend": eig_backend,
            "eig_source": eig_source,
            "sub_sym_resid": sub_sym_resid,
            "sub_nbytes": int(sub.nbytes),
            "sub_c_contig": bool(sub.flags["C_CONTIGUOUS"]),
            "sub_f_contig": bool(sub.flags["F_CONTIGUOUS"]),
            "sub_owndata": bool(sub.flags["OWNDATA"]),
            "rss_before_mb": rss_before,
            "rss_after_mb": rss_after,
        }
        if ts.enabled and (iter_idx == 1 or iter_idx % 25 == 0):
            ts.log(
                f"EIG_SUBMETA iter={iter_idx} backend={eig_backend} "
                f"sub_shape={tuple(sub.shape)} sub_nbytes_mb={sub.nbytes / (1024 * 1024):.2f} "
                f"C={bool(sub.flags['C_CONTIGUOUS'])} F={bool(sub.flags['F_CONTIGUOUS'])} "
                f"owndata={bool(sub.flags['OWNDATA'])} sym_resid={sub_sym_resid:.3g} "
                f"rss_before_mb={rss_before:.1f} rss_after_mb={rss_after:.1f} "
                f"eig_call_s={dt_eig_call:.4f}"
            )
        e_top_use = np.asarray(e_top_kept, dtype=np.float64).ravel()
        if e_top_use.size:
            e_max = float(np.max(e_top_use))
            e_min = float(np.min(e_top_use))
        else:
            e_max = float("nan")
            e_min = float("nan")
        ts.eig_peel_log(iter_idx=iter_idx, chosen=chosen)
        ts.eig_heartbeat(
            iter_idx=iter_idx,
            active_size=int(active_before.size),
            active_after=int(active.size),
            sub_shape=(int(sub.shape[0]), int(sub.shape[1])),
            iter_elapsed=iter_elapsed,
            n_chosen=int(chosen.size),
            e_top_max=e_max,
            e_top_min=e_min,
            force=(iter_idx == 1),
        )

    ts.phases["eig_partition"] = float(time.perf_counter() - t_eig_all)
    ts.log(
        f"EIG_PARTITION END iters={iter_idx} n_groups={len(groups)} "
        f"elapsed_s={ts.phases['eig_partition']:.3f}"
    )

    t0 = ts.phase_start("expand_modalities")
    for g_idx in range(len(groups)):
        comp_ids = groups[g_idx]
        k_list: List[int] = []
        for c in comp_ids:
            j_base = (int(c) - 1) * m
            k_list.extend(range(j_base + 1, j_base + m + 1))
        groups[g_idx] = np.asarray(k_list, dtype=np.int64)

    ts.phase_end("expand_modalities", t0, f"n_groups={len(groups)}")
    ts.summary()
    return groups

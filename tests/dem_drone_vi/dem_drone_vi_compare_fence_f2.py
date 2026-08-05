#!/usr/bin/env python3
"""OPTIM2FULL fence F2 — compare Python FSL ``MDP`` vs MATLAB ``…_F2.mat``.

Minimum honest compare (stop at first red):
  - ``MDP`` cell length
  - per level ``T``, ``len(a)``, ``len(b)``, ``G`` presence
  - ``id.A`` / ``id.D`` / ``id.E`` lengths
  - numeric ``a``/``b`` maxabs when shapes match

Report: ``matlab_custom/dem_drone_vi_compare_fence_f2_output.txt``
"""
from __future__ import annotations

import argparse
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.dem_drone_vi.dem_drone_vi_authority import (
    assert_optim2full_full_ledger_ok,
)
from tests.dem_drone_vi.dem_drone_vi_paths import (
    CAPTURE_OPTIM2FULL_RAND_LEDGER,
    optim2full_compare_f2_report,
    optim2full_f2_mat,
    optim2full_f2_pkl,
)


class _TeeIO:
    __slots__ = ("_streams",)

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self._streams:
            st.flush()


def _as_list(mdp: Any) -> list:
    if isinstance(mdp, list):
        return mdp
    arr = np.asarray(mdp, dtype=object).ravel(order="F")
    return [arr[i] for i in range(arr.size)]


def _field(m: Any, name: str) -> Any:
    if isinstance(m, dict):
        return m[name]
    return getattr(m, name)


def _cell_len(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, list):
        return len(x)
    arr = np.asarray(x, dtype=object)
    return int(arr.size)


def _as_factor_cell(x: Any) -> list:
    """Normalize ``MDP{n}.a`` / ``.b`` to a list of factor payloads.

    MATLAB ``.mat`` loaded with ``simplify_cells=True`` often collapses a
    one-element cell ``{B}`` to bare numeric/sparse ``B``. Treating that bare
    tensor as ``list(ravel(B))`` falsely reports ``numel(B)`` factors (e.g. L2
    ``b`` ``(12,12)`` → 144). Python FSL keeps a Python list of factors
    (each often ``[tensor]``). Shared FSL is unchanged — compare only.
    """
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, np.ndarray) and x.dtype == object:
        return [x.flat[i] for i in range(x.size)]
    # bare numeric / sparse tensor == one collapsed factor cell
    if hasattr(x, "toarray"):
        return [x]
    if isinstance(x, np.ndarray) and x.dtype != object:
        return [x]
    return [x]


def _factor_payload(a: Any) -> Any:
    """Peel Python FSL factor wrappers.

    MATLAB stores ``MDP{n}.a{g}`` / ``b{g}`` as the tensor. Shared
    ``spm_faster_structure_learning_optim`` stores each cell as ``[tensor]``
    (one-factor list). Compare must unwrap that without changing shared FSL.
    """
    while isinstance(a, (list, tuple)) and len(a) == 1:
        a = a[0]
    return a


def _dense(a: Any) -> np.ndarray:
    a = _factor_payload(a)
    if hasattr(a, "toarray"):
        a = a.toarray()
    x = np.asarray(a, dtype=np.float64)
    # MATLAB ``structure_fast`` keeps ``b`` 2-D when Nu==1; Python always
    # allocates ``(Ns,Ns,1)``. Squeeze trailing singleton planes for honest compare.
    while x.ndim >= 3 and x.shape[-1] == 1:
        x = x[..., 0]
    return x


def _compare_level(lev: int, m_mat: Any, m_py: Any) -> None:
    t_m = float(np.asarray(_field(m_mat, "T")).reshape(-1)[0])
    t_p = float(np.asarray(_field(m_py, "T")).reshape(-1)[0])
    if t_m != t_p:
        raise AssertionError(f"MDP{{{lev}}}.T matlab={t_m} python={t_p}")
    a_m, a_p = _field(m_mat, "a"), _field(m_py, "a")
    b_m, b_p = _field(m_mat, "b"), _field(m_py, "b")
    a_m_l, a_p_l = _as_factor_cell(a_m), _as_factor_cell(a_p)
    b_m_l, b_p_l = _as_factor_cell(b_m), _as_factor_cell(b_p)
    if len(a_m_l) != len(a_p_l):
        raise AssertionError(
            f"MDP{{{lev}}}.a len matlab={len(a_m_l)} python={len(a_p_l)}"
        )
    if len(b_m_l) != len(b_p_l):
        raise AssertionError(
            f"MDP{{{lev}}}.b len matlab={len(b_m_l)} python={len(b_p_l)}"
        )
    id_m, id_p = _field(m_mat, "id"), _field(m_py, "id")
    for key in ("A", "D", "E"):
        lm = _cell_len(_field(id_m, key) if not isinstance(id_m, dict) else id_m[key])
        lp = _cell_len(_field(id_p, key) if not isinstance(id_p, dict) else id_p[key])
        if lm != lp:
            raise AssertionError(
                f"MDP{{{lev}}}.id.{key} len matlab={lm} python={lp}"
            )
    # numeric a/b (unwrap Python ``[tensor]``; accept MATLAB bare collapsed cell)
    for i, (am, ap) in enumerate(zip(a_m_l, a_p_l)):
        if am is None or ap is None:
            continue
        dm, dp = _dense(am), _dense(ap)
        if dm.shape != dp.shape:
            raise AssertionError(
                f"MDP{{{lev}}}.a{{{i+1}}} shape matlab={dm.shape} python={dp.shape}"
            )
        if not np.allclose(dm, dp, rtol=0.0, atol=0.0, equal_nan=True):
            n_bad = int(np.sum(dm != dp))
            raise AssertionError(
                f"MDP{{{lev}}}.a{{{i+1}}} mismatch n_bad={n_bad} "
                f"maxabs={float(np.max(np.abs(dm - dp)))}"
            )
    for i, (bm, bp) in enumerate(zip(b_m_l, b_p_l)):
        if bm is None or bp is None:
            continue
        dm, dp = _dense(bm), _dense(bp)
        if dm.shape != dp.shape:
            raise AssertionError(
                f"MDP{{{lev}}}.b{{{i+1}}} shape matlab={dm.shape} python={dp.shape}"
            )
        if not np.allclose(dm, dp, rtol=0.0, atol=0.0, equal_nan=True):
            n_bad = int(np.sum(dm != dp))
            raise AssertionError(
                f"MDP{{{lev}}}.b{{{i+1}}} mismatch n_bad={n_bad} "
                f"maxabs={float(np.max(np.abs(dm - dp)))}"
            )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-only",
        action="store_true",
        help="Only check full-order authority (no Python pkl required).",
    )
    args = p.parse_args(argv)

    report = optim2full_compare_f2_report()
    report.parent.mkdir(parents=True, exist_ok=True)
    out_f = report.open("w", encoding="utf-8")
    tee = _TeeIO(sys.stdout, out_f)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = tee  # type: ignore[assignment]
    sys.stderr = tee  # type: ignore[assignment]
    try:
        from tests.dem_drone_vi.dem_drone_vi_timing import timing_log
        import time as _time

        _t0 = _time.perf_counter()
        timing_log("compare_fence_f2", "START")
        print(
            f"OPTIM2FULL compare fence F2 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F2 authority-only check passed")
            timing_log(
                "compare_fence_f2",
                f"END OK authority-only elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
            return 0

        pkl = optim2full_f2_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F2 export missing ({pkl.name}). "
                "Run: python tests/dem_drone_vi/dem_drone_vi_export_fence_f2.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F2 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r}"
            )

        from scipy.io import loadmat

        mat = loadmat(str(optim2full_f2_mat()), simplify_cells=True)
        m_mat = _as_list(mat["MDP"])
        m_py = _as_list(blob["MDP"])
        print(
            f"hooks={blob.get('fsl_hooks')} elapsed_s={blob.get('fsl_elapsed_s')} "
            f"dx={blob.get('dx')} levels mat={len(m_mat)} py={len(m_py)}"
        )
        if len(m_mat) != len(m_py):
            raise AssertionError(
                f"MDP levels matlab={len(m_mat)} python={len(m_py)}"
            )
        print("OK: MDP level count matched")
        for i, (mm, mp) in enumerate(zip(m_mat, m_py), start=1):
            _compare_level(i, mm, mp)
            print(f"OK: MDP{{{i}}} T/a/b/id + a numerics matched")
        print("OK: OPTIM2FULL fence F2 passed")
        timing_log(
            "compare_fence_f2",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F2")
        try:
            timing_log(
                "compare_fence_f2",
                f"END FAIL elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[dem_drone_vi_compare_fence_f2] report -> {report}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

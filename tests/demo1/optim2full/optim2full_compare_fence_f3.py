#!/usr/bin/env python3
"""OPTIM2FULL fence F3 — compare Python ``spm_mdp_a2A`` MDP vs MATLAB ``…_F3.mat``.

Authority note: ``Post spm_mdp_a2A.`` — ``A``/``B`` present, ``a``/``b`` removed.
``simplify_cells`` may collapse one-element ``B`` to a bare tensor — use
``_as_factor_cell`` (same honesty as F2).

Report: ``matlab_custom/optim2full_compare_fence_f3_output.txt``
"""
from __future__ import annotations

import argparse
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.optim2full.optim2full_authority import (
    assert_optim2full_full_ledger_ok,
)
from tests.demo1.optim2full.optim2full_paths import (
    CAPTURE_OPTIM2FULL_RAND_LEDGER,
    optim2full_compare_f3_report,
    optim2full_f3_mat,
    optim2full_f3_pkl,
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
    """Bare numeric/sparse from ``simplify_cells`` = one collapsed factor cell."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, np.ndarray) and x.dtype == object:
        return [x.flat[i] for i in range(x.size)]
    if hasattr(x, "toarray"):
        return [x]
    if isinstance(x, np.ndarray) and x.dtype != object:
        return [x]
    return [x]


def _factor_payload(a: Any) -> Any:
    while isinstance(a, (list, tuple)) and len(a) == 1:
        a = a[0]
    return a


def _dense(a: Any) -> np.ndarray:
    a = _factor_payload(a)
    if hasattr(a, "toarray"):
        a = a.toarray()
    x = np.asarray(a, dtype=np.float64)
    while x.ndim >= 3 and x.shape[-1] == 1:
        x = x[..., 0]
    # ``simplify_cells`` collapses MATLAB 1×1 ``B`` to a scalar; Python
    # ``spm_dir_norm`` on a scalar count keeps shape ``(1, 1)``. Promote.
    if x.ndim == 0:
        x = x.reshape((1, 1), order="F")
    return x


def _compare_level(lev: int, m_mat: Any, m_py: Any) -> None:
    t_m = float(np.asarray(_field(m_mat, "T")).reshape(-1)[0])
    t_p = float(np.asarray(_field(m_py, "T")).reshape(-1)[0])
    if t_m != t_p:
        raise AssertionError(f"MDP{{{lev}}}.T matlab={t_m} python={t_p}")
    # post-a2A: a/b must be gone; A/B present
    for gone in ("a", "b"):
        if isinstance(m_py, dict) and gone in m_py:
            raise AssertionError(f"MDP{{{lev}}} python still has {gone!r}")
        if isinstance(m_mat, dict) and gone in m_mat and m_mat[gone] is not None:
            # simplify_cells may omit keys; if present nonempty → fail
            v = m_mat[gone]
            if _as_factor_cell(v):
                raise AssertionError(f"MDP{{{lev}}} matlab still has {gone!r}")
    A_m = _as_factor_cell(_field(m_mat, "A"))
    A_p = _as_factor_cell(_field(m_py, "A"))
    B_m = _as_factor_cell(_field(m_mat, "B"))
    B_p = _as_factor_cell(_field(m_py, "B"))
    if len(A_m) != len(A_p):
        raise AssertionError(
            f"MDP{{{lev}}}.A len matlab={len(A_m)} python={len(A_p)}"
        )
    if len(B_m) != len(B_p):
        raise AssertionError(
            f"MDP{{{lev}}}.B len matlab={len(B_m)} python={len(B_p)}"
        )
    id_m, id_p = _field(m_mat, "id"), _field(m_py, "id")
    for key in ("A", "D", "E"):
        lm = _cell_len(_field(id_m, key) if not isinstance(id_m, dict) else id_m[key])
        lp = _cell_len(_field(id_p, key) if not isinstance(id_p, dict) else id_p[key])
        if lm != lp:
            raise AssertionError(
                f"MDP{{{lev}}}.id.{key} len matlab={lm} python={lp}"
            )
    for i, (am, ap) in enumerate(zip(A_m, A_p)):
        if am is None or ap is None:
            continue
        dm, dp = _dense(am), _dense(ap)
        if dm.shape != dp.shape:
            raise AssertionError(
                f"MDP{{{lev}}}.A{{{i+1}}} shape matlab={dm.shape} python={dp.shape}"
            )
        if not np.allclose(dm, dp, rtol=0.0, atol=0.0, equal_nan=True):
            n_bad = int(np.sum(dm != dp))
            raise AssertionError(
                f"MDP{{{lev}}}.A{{{i+1}}} mismatch n_bad={n_bad} "
                f"maxabs={float(np.max(np.abs(dm - dp)))}"
            )
    for i, (bm, bp) in enumerate(zip(B_m, B_p)):
        if bm is None or bp is None:
            continue
        dm, dp = _dense(bm), _dense(bp)
        if dm.shape != dp.shape:
            raise AssertionError(
                f"MDP{{{lev}}}.B{{{i+1}}} shape matlab={dm.shape} python={dp.shape}"
            )
        if not np.allclose(dm, dp, rtol=0.0, atol=0.0, equal_nan=True):
            n_bad = int(np.sum(dm != dp))
            raise AssertionError(
                f"MDP{{{lev}}}.B{{{i+1}}} mismatch n_bad={n_bad} "
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

    report = optim2full_compare_f3_report()
    report.parent.mkdir(parents=True, exist_ok=True)
    out_f = report.open("w", encoding="utf-8")
    tee = _TeeIO(sys.stdout, out_f)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = tee  # type: ignore[assignment]
    sys.stderr = tee  # type: ignore[assignment]
    try:
        from tests.demo1.optim2full.optim2full_timing import timing_log
        import time as _time

        _t0 = _time.perf_counter()
        timing_log("compare_fence_f3", "START")
        print(
            f"OPTIM2FULL compare fence F3 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F3 authority-only check passed")
            timing_log(
                "compare_fence_f3",
                f"END OK authority-only elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
            return 0

        pkl = optim2full_f3_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F3 export missing ({pkl.name}). "
                "Run: python tests/demo1/optim2full/optim2full_export_fence_f3.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F3 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r}"
            )

        from scipy.io import loadmat

        raw = loadmat(str(optim2full_f3_mat()), simplify_cells=True)
        m_mat = _as_list(raw["MDP"])
        m_py = _as_list(blob["MDP"])
        print(
            f"policy={blob.get('nonscalar_policy')} "
            f"elapsed_s={blob.get('a2A_elapsed_s')} "
            f"levels mat={len(m_mat)} py={len(m_py)}"
        )
        if len(m_mat) != len(m_py):
            raise AssertionError(
                f"MDP level count matlab={len(m_mat)} python={len(m_py)}"
            )
        print("OK: MDP level count matched")
        for i, (mm, mp) in enumerate(zip(m_mat, m_py), start=1):
            _compare_level(i, mm, mp)
            print(f"OK: MDP{{{i}}} T/A/B/id numerics matched")
        print("OK: OPTIM2FULL fence F3 passed")
        timing_log(
            "compare_fence_f3",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F3")
        try:
            from tests.demo1.optim2full.optim2full_timing import timing_log
            import time as _time

            timing_log("compare_fence_f3", "END FAIL")
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[optim2full_compare_fence_f3] report -> {report}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

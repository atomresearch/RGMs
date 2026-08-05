#!/usr/bin/env python3
"""OPTIM2FULL fence F4 — compare Python packing+``spm_mdp2rdp`` RDP vs MATLAB ``…_F4.mat``.

Authority note: ``Pre first spm_MDP_VB_XXX (post spm_mdp2rdp packing).``
``simplify_cells`` may collapse one-element cells — use ``_as_factor_cell``.
Skip ``MatlabFunction`` / callable ``A`` cells (rebound on Python; not numeric).

Report: ``matlab_custom/dem_drone_vi_compare_fence_f4_output.txt``
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
    optim2full_compare_f4_report,
    optim2full_f4_mat,
    optim2full_f4_pkl,
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


def _field(m: Any, name: str) -> Any:
    if isinstance(m, dict):
        return m[name]
    return getattr(m, name)


def _has_field(m: Any, name: str) -> bool:
    if isinstance(m, dict):
        return name in m
    return hasattr(m, name)


def _as_factor_cell(x: Any) -> list:
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


def _is_handleish(a: Any) -> bool:
    a = _factor_payload(a)
    if callable(a):
        return True
    return type(a).__name__ == "MatlabFunction"


def _dense(a: Any) -> np.ndarray:
    a = _factor_payload(a)
    if hasattr(a, "toarray"):
        a = a.toarray()
    x = np.asarray(a, dtype=np.float64)
    while x.ndim >= 3 and x.shape[-1] == 1:
        x = x[..., 0]
    if x.ndim == 0:
        x = x.reshape((1, 1), order="F")
    return x


def _compare_numeric_cells(path: str, mat_c: Any, py_c: Any) -> None:
    cm = _as_factor_cell(mat_c)
    cp = _as_factor_cell(py_c)
    if len(cm) != len(cp):
        raise AssertionError(f"{path} len matlab={len(cm)} python={len(cp)}")
    n_skip = 0
    n_cmp = 0
    for i, (am, ap) in enumerate(zip(cm, cp)):
        if am is None and ap is None:
            continue
        if _is_handleish(am) or _is_handleish(ap):
            # Both sides must be handle-ish (MATLAB MatlabFunction vs Python callable)
            if not (_is_handleish(am) and _is_handleish(ap)):
                raise AssertionError(
                    f"{path}{{{i+1}}} handle mismatch "
                    f"mat={type(_factor_payload(am)).__name__} "
                    f"py={type(_factor_payload(ap)).__name__}"
                )
            n_skip += 1
            continue
        dm, dp = _dense(am), _dense(ap)
        if dm.shape != dp.shape:
            raise AssertionError(
                f"{path}{{{i+1}}} shape matlab={dm.shape} python={dp.shape}"
            )
        if not np.allclose(dm, dp, rtol=0.0, atol=0.0, equal_nan=True):
            n_bad = int(np.sum(dm != dp))
            raise AssertionError(
                f"{path}{{{i+1}}} mismatch n_bad={n_bad} "
                f"maxabs={float(np.max(np.abs(dm - dp)))}"
            )
        n_cmp += 1
    print(f"OK: {path} numeric={n_cmp} handle_skip={n_skip} len={len(cm)}")


def _compare_rdp_level(tag: str, m_mat: Any, m_py: Any) -> None:
    for key in ("L", "T"):
        if not _has_field(m_mat, key) or not _has_field(m_py, key):
            continue
        vm = float(np.asarray(_field(m_mat, key)).reshape(-1)[0])
        vp = float(np.asarray(_field(m_py, key)).reshape(-1)[0])
        if vm != vp:
            raise AssertionError(f"{tag}.{key} matlab={vm} python={vp}")
        print(f"OK: {tag}.{key}={vm}")

    if _has_field(m_mat, "A") and _has_field(m_py, "A"):
        _compare_numeric_cells(f"{tag}.A", _field(m_mat, "A"), _field(m_py, "A"))
    if _has_field(m_mat, "B") and _has_field(m_py, "B"):
        _compare_numeric_cells(f"{tag}.B", _field(m_mat, "B"), _field(m_py, "B"))

    # Nested subordinate (MATLAB RDP.MDP)
    if _has_field(m_mat, "MDP") and _has_field(m_py, "MDP"):
        _compare_rdp_level(f"{tag}.MDP", _field(m_mat, "MDP"), _field(m_py, "MDP"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-only",
        action="store_true",
        help="Only check full-order authority (no Python pkl required).",
    )
    args = p.parse_args(argv)

    report = optim2full_compare_f4_report()
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
        timing_log("compare_fence_f4", "START")
        print(
            f"OPTIM2FULL compare fence F4 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F4 authority-only check passed")
            timing_log(
                "compare_fence_f4",
                f"END OK authority-only elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
            return 0

        pkl = optim2full_f4_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F4 export missing ({pkl.name}). "
                "Run: python tests/dem_drone_vi/dem_drone_vi_export_fence_f4.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F4 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r}"
            )

        from scipy.io import loadmat

        raw = loadmat(str(optim2full_f4_mat()), simplify_cells=True)
        meta = raw.get("meta")
        note = ""
        if isinstance(meta, dict):
            note = str(meta.get("note") or "")
        print(
            f"policy={blob.get('nonscalar_policy')} "
            f"elapsed_s={blob.get('mdp2rdp_elapsed_s')} "
            f"pack={blob.get('pack_meta')} note={note!r}"
        )
        _compare_rdp_level("RDP", raw["RDP"], blob["RDP"])
        print("OK: OPTIM2FULL fence F4 passed")
        timing_log(
            "compare_fence_f4",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F4")
        try:
            from tests.dem_drone_vi.dem_drone_vi_timing import timing_log

            timing_log("compare_fence_f4", "END FAIL")
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[dem_drone_vi_compare_fence_f4] report -> {report}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

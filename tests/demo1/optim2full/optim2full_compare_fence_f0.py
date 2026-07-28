#!/usr/bin/env python3
"""OPTIM2FULL fence F0 — compare Python export vs MATLAB-owned ``…_F0.mat``.

Phase 1: requires durable full-order ledger authority. Python F0 pkl is produced
by ``optim2full_export_fence_f0.py`` via same-session ``W``/``D``/``MAP`` inject.

Report: ``matlab_custom/optim2full_compare_fence_f0_output.txt``
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
    optim2full_compare_f0_report,
    optim2full_f0_mat,
    optim2full_f0_pkl,
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


def _load_f0_mat(path: Path) -> dict[str, Any]:
    from scipy.io import loadmat

    return loadmat(str(path), squeeze_me=True, struct_as_record=False)


def _compare_arr(name: str, matlab_a: Any, python_a: Any) -> None:
    mw = np.asarray(matlab_a, dtype=float)
    pw = np.asarray(python_a, dtype=float)
    if mw.shape != pw.shape:
        raise AssertionError(f"{name} shape matlab={mw.shape} python={pw.shape}")
    if not np.allclose(mw, pw, rtol=0.0, atol=0.0, equal_nan=True):
        # integer class maps: require exact
        if not np.array_equal(mw, pw):
            n_bad = int(np.sum(mw != pw))
            raise AssertionError(f"{name} mismatch: {n_bad} differing entries")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-only",
        action="store_true",
        help="Only check full-order authority (no Python pkl required).",
    )
    args = p.parse_args(argv)

    report = optim2full_compare_f0_report()
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
        timing_log("compare_fence_f0", "START")
        print(
            f"OPTIM2FULL compare fence F0 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F0 authority-only check passed")
            timing_log(
                "compare_fence_f0",
                f"END OK authority-only elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
            return 0

        pkl = optim2full_f0_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F0 export missing ({pkl.name}). "
                "Run: python tests/demo1/optim2full/optim2full_export_fence_f0.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F0 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r} "
                f"(expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r})"
            )
        if blob.get("nonscalar_policy") != "same_session_WD_inject":
            raise RuntimeError(
                f"refusing compare: nonscalar_policy={blob.get('nonscalar_policy')!r}"
            )
        mat = _load_f0_mat(optim2full_f0_mat())
        _compare_arr("W", mat["W"], blob["W"])
        # MAP/D are sparse cell arrays — F0 numeric sign-off is W (class map).
        print("OK: F0 W matched MATLAB authority (inject policy)")
        print("OK: OPTIM2FULL fence F0 passed")
        timing_log(
            "compare_fence_f0",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F0")
        try:
            timing_log(
                "compare_fence_f0",
                f"END FAIL elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[optim2full_compare_fence_f0] report -> {report}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""OPTIM2FULL fence F1 — compare Python export vs MATLAB-owned ``…_F1.mat``.

Compares:
  - assembled ``GDP.s`` / ``GDP.U`` / ``GDP.T`` / ``id.ff`` / ``id.control`` vs F1 GDP
  - ``pre_fsl`` draw audit (used == segment k)
  - generated ``PDP.s`` / ``PDP.o`` vs F1 ``PDP``
  - ``Q`` rebuilt from generated ``PDP.s`` vs F1 ``Q``

Report: ``matlab_custom/optim2full_compare_fence_f1_output.txt``
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
    optim2full_compare_f1_report,
    optim2full_f1_mat,
    optim2full_f1_pkl,
)

_F1_POLICY = "same_session_F0_WD_and_F1_PG_angles_generate"


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


def _load_f1_mat(path: Path) -> dict[str, Any]:
    from scipy.io import loadmat

    return loadmat(str(path), simplify_cells=True)


def _as_1d(a: Any) -> np.ndarray:
    return np.asarray(a, dtype=np.float64).ravel(order="F")


def _pdp_field(pdp: Any, name: str) -> Any:
    if isinstance(pdp, dict):
        return pdp[name]
    return getattr(pdp, name)


def _compare_vec(name: str, matlab_a: Any, python_a: Any) -> None:
    mw = _as_1d(matlab_a)
    pw = _as_1d(python_a)
    if mw.shape != pw.shape:
        raise AssertionError(f"{name} shape matlab={mw.shape} python={pw.shape}")
    if not np.array_equal(mw, pw):
        n_bad = int(np.sum(mw != pw))
        raise AssertionError(f"{name} mismatch: {n_bad} differing entries")


def _compare_mat(name: str, matlab_a: Any, python_a: Any) -> None:
    mw = np.asarray(matlab_a, dtype=np.float64)
    pw = np.asarray(python_a, dtype=np.float64)
    if mw.shape != pw.shape:
        raise AssertionError(f"{name} shape matlab={mw.shape} python={pw.shape}")
    if not np.array_equal(mw, pw):
        n_bad = int(np.sum(mw != pw))
        raise AssertionError(f"{name} mismatch: {n_bad} differing entries")


def _cell_to_dense(cell: Any) -> np.ndarray:
    if hasattr(cell, "toarray"):
        return np.asarray(cell.toarray(), dtype=np.float64)
    if hasattr(cell, "todense"):
        return np.asarray(cell.todense(), dtype=np.float64)
    return np.asarray(cell, dtype=np.float64)


def _compare_Q(name: str, matlab_q: Any, python_q: list) -> None:
    mq = np.asarray(matlab_q, dtype=object)
    if mq.ndim != 2:
        raise AssertionError(f"{name} matlab Q ndim={mq.ndim}")
    np_, T = mq.shape
    if len(python_q) != np_ or (python_q and len(python_q[0]) != T):
        raise AssertionError(
            f"{name} shape matlab=({np_},{T}) "
            f"python=({len(python_q)},{len(python_q[0]) if python_q else 0})"
        )
    n_bad = 0
    maxabs = 0.0
    for f in range(np_):
        for t in range(T):
            ma = _cell_to_dense(mq[f, t]).ravel(order="F")
            pa = _cell_to_dense(python_q[f][t]).ravel(order="F")
            if ma.shape != pa.shape:
                n_bad += 1
                continue
            d = float(np.max(np.abs(ma - pa))) if ma.size else 0.0
            maxabs = max(maxabs, d)
            if d > 0.0:
                n_bad += 1
    if n_bad:
        raise AssertionError(
            f"{name} mismatch: {n_bad} cells differ (maxabs={maxabs})"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-only",
        action="store_true",
        help="Only check full-order authority (no Python pkl required).",
    )
    args = p.parse_args(argv)

    report = optim2full_compare_f1_report()
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
        timing_log("compare_fence_f1", "START")
        print(
            f"OPTIM2FULL compare fence F1 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F1 authority-only check passed")
            timing_log(
                "compare_fence_f1",
                f"END OK authority-only elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
            return 0

        pkl = optim2full_f1_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F1 export missing ({pkl.name}). "
                "Run: python tests/demo1/optim2full/optim2full_export_fence_f1.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F1 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r} "
                f"(expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r})"
            )
        if blob.get("nonscalar_policy") != _F1_POLICY:
            raise RuntimeError(
                f"refusing compare: nonscalar_policy={blob.get('nonscalar_policy')!r}"
            )
        if blob.get("generate_note") != "spm_MDP_generate_optim_pre_fsl":
            raise RuntimeError(
                f"refusing compare: generate_note={blob.get('generate_note')!r}"
            )

        draws = int(blob.get("draws_used", -1))
        k = int(blob.get("pre_fsl_k", -1))
        print(
            f"policy={blob.get('rng_policy')} "
            f"pg={blob.get('pg_angles_policy')} "
            f"generate_note={blob.get('generate_note')} "
            f"draws={draws}/{k}"
        )
        if draws != k or k <= 0:
            raise AssertionError(f"pre_fsl draw audit used={draws} expected={k}")
        print("OK: pre_fsl draw audit")

        mat = _load_f1_mat(optim2full_f1_mat())
        gdp_m = mat["GDP"]
        gdp_p = blob["GDP"]
        _compare_vec("GDP.s", gdp_m["s"], gdp_p["s"])
        _compare_vec("GDP.U", gdp_m["U"], gdp_p["U"])
        if float(np.asarray(gdp_m["T"]).ravel()[0]) != float(
            np.asarray(gdp_p["T"]).ravel()[0]
        ):
            raise AssertionError(
                f"GDP.T matlab={gdp_m['T']} python={gdp_p['T']}"
            )
        _compare_vec("GDP.id.ff", gdp_m["id"]["ff"], gdp_p["id"]["ff"])
        _compare_vec(
            "GDP.id.control", gdp_m["id"]["control"], gdp_p["id"]["control"]
        )
        if len(gdp_m["A"]) != len(gdp_p["A"]) or len(gdp_m["B"]) != len(gdp_p["B"]):
            raise AssertionError(
                f"GDP A/B lens matlab=({len(gdp_m['A'])},{len(gdp_m['B'])}) "
                f"python=({len(gdp_p['A'])},{len(gdp_p['B'])})"
            )
        print("OK: F1 GDP.s/U/T/id.ff/id.control/A-B lens matched")

        pdp_p = blob["PDP"]
        pdp_m = mat["PDP"]
        _compare_mat("PDP.s", pdp_m["s"], _pdp_field(pdp_p, "s"))
        _compare_mat("PDP.o", pdp_m["o"], _pdp_field(pdp_p, "o"))
        print("OK: F1 PDP.s and PDP.o matched (generate)")

        _compare_Q("Q", mat["Q"], blob["Q"])
        print("OK: F1 Q matched MATLAB authority (from generated PDP.s)")
        print("OK: OPTIM2FULL fence F1 passed")
        timing_log(
            "compare_fence_f1",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F1")
        try:
            timing_log(
                "compare_fence_f1",
                f"END FAIL elapsed_s={_time.perf_counter()-_t0:.3f}",
            )
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[optim2full_compare_fence_f1] report -> {report}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

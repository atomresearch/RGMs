#!/usr/bin/env python3
"""OPTIM2FULL fence F6 — compare Python wayfinding VB + ``spm_Q2mdp`` vs MATLAB ``…_F6.mat``.

Authority note: ``Post second spm_MDP_VB_XXX (wayfinding) + spm_Q2mdp.``

Compare surface:
  * ``RDP.T`` / ``RDP.L`` scalars (expect ``T=4``).
  * ``sT`` goal vector (spine ``[28,12,3]``).
  * ``QDP`` = ``spm_Q2mdp(RDP.Q,1)`` fields ``s u o X Y O j`` (numeric).
  * ``QDP.id`` numeric fields including ``hid``; ``fg`` / ``cid`` handle-skip.

Tolerance policy (carry F5 locked policy; see OPTIM2FULL.md § F5 closed reference):
  * Decision / discrete: ``s``, ``u``, ``o``, ``O``, ``j``, ``id.*``, ``sT`` → ``atol=0``.
  * Continuous soft posteriors: ``X``, ``Y`` → ``atol=1e-12``.

Report: ``matlab_custom/optim2full_compare_fence_f6_output.txt``
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
    optim2full_compare_f6_report,
    optim2full_f6_mat,
    optim2full_f6_pkl,
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


def _payload(a: Any) -> Any:
    while isinstance(a, (list, tuple)) and len(a) == 1:
        a = a[0]
    return a


def _is_handleish(a: Any) -> bool:
    a = _payload(a)
    if callable(a):
        return True
    return type(a).__name__ in ("MatlabFunction", "MatlabOpaque", "mat_struct")


def _is_cellish(a: Any) -> bool:
    if isinstance(a, (list, tuple)):
        return True
    return isinstance(a, np.ndarray) and a.dtype == object


def _to_cells(a: Any) -> list:
    if isinstance(a, (list, tuple)):
        if len(a) > 0 and all(isinstance(x, (list, tuple)) for x in a):
            return [x for row in a for x in row]
        return list(a)
    if isinstance(a, np.ndarray) and a.dtype == object:
        return [a.flat[i] for i in range(a.size)]
    return [a]


def _dense(a: Any) -> np.ndarray:
    a = _payload(a)
    if hasattr(a, "toarray"):
        a = a.toarray()
    x = np.asarray(a, dtype=np.float64)
    while x.ndim >= 3 and x.shape[-1] == 1:
        x = x[..., 0]
    if x.ndim == 0:
        x = x.reshape((1, 1), order="F")
    return x


def _align_pair(dm: np.ndarray, dp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if dm.shape == dp.shape:
        return dm, dp
    if dm.size == dp.size and dm.size > 0:
        if dm.ndim == 1 and dp.ndim == 2 and (dp.shape[0] == dm.size or dp.shape[1] == dm.size):
            return dm.reshape(dp.shape, order="F"), dp
        if dp.ndim == 1 and dm.ndim == 2 and (dm.shape[0] == dp.size or dm.shape[1] == dp.size):
            return dm, dp.reshape(dm.shape, order="F")
        if dm.T.shape == dp.shape:
            return dm.T, dp
        if dp.T.shape == dm.shape:
            return dm, dp.T
    return dm, dp


_STATS = {"numeric": 0, "handle_skip": 0, "empty": 0}

# Carry F5 soft-band policy (user-approved 2026-07-26) unless F6 first-red proves otherwise.
_SOFT_XY_ATOL = 1e-12


def _cmp(path: str, m: Any, p: Any, *, atol: float = 0.0) -> None:
    mp, pp = _payload(m), _payload(p)

    if _is_handleish(mp) or _is_handleish(pp):
        if not (_is_handleish(mp) and _is_handleish(pp)):
            raise AssertionError(
                f"{path} handle mismatch "
                f"mat={type(mp).__name__} py={type(pp).__name__}"
            )
        _STATS["handle_skip"] += 1
        return

    m_cell, p_cell = _is_cellish(m), _is_cellish(p)
    if m_cell or p_cell:
        cm, cp = _to_cells(m), _to_cells(p)
        if len(cm) != len(cp):
            raise AssertionError(f"{path} cell len matlab={len(cm)} python={len(cp)}")
        for i, (a, b) in enumerate(zip(cm, cp)):
            _cmp(f"{path}{{{i+1}}}", a, b, atol=atol)
        return

    if mp is None and pp is None:
        _STATS["empty"] += 1
        return

    dm, dp = _align_pair(_dense(mp), _dense(pp))
    if dm.size == 0 and dp.size == 0:
        _STATS["empty"] += 1
        return
    if dm.shape != dp.shape:
        raise AssertionError(f"{path} shape matlab={dm.shape} python={dp.shape}")
    if not np.allclose(dm, dp, rtol=0.0, atol=atol, equal_nan=True):
        n_bad = int(np.sum(~np.isclose(dm, dp, rtol=0.0, atol=atol, equal_nan=True)))
        raise AssertionError(
            f"{path} mismatch n_bad={n_bad} maxabs={float(np.max(np.abs(dm - dp)))} "
            f"atol={atol}"
        )
    _STATS["numeric"] += 1


def _cmp_scalar(tag: str, m: Any, p: Any, key: str) -> None:
    if not (_has_field(m, key) and _has_field(p, key)):
        return
    vm = float(np.asarray(_field(m, key)).reshape(-1)[0])
    vp = float(np.asarray(_field(p, key)).reshape(-1)[0])
    if vm != vp:
        raise AssertionError(f"{tag}.{key} matlab={vm} python={vp}")
    print(f"OK: {tag}.{key}={vm}")


def _compare_qdp(qm: Any, qp: Any) -> None:
    for key in ("s", "u", "o"):
        _cmp(f"QDP.{key}", _field(qm, key), _field(qp, key), atol=0.0)
        print(f"OK: QDP.{key}")
    for key in ("X", "Y"):
        _cmp(f"QDP.{key}", _field(qm, key), _field(qp, key), atol=_SOFT_XY_ATOL)
        print(f"OK: QDP.{key} (atol={_SOFT_XY_ATOL:g})")
    for key in ("O", "j"):
        _cmp(f"QDP.{key}", _field(qm, key), _field(qp, key), atol=0.0)
        print(f"OK: QDP.{key}")
    idm, idp = _field(qm, "id"), _field(qp, "id")
    for key in ("ge", "ff", "D", "E", "hid"):
        if _has_field(idm, key) and _has_field(idp, key):
            _cmp(f"QDP.id.{key}", _field(idm, key), _field(idp, key), atol=0.0)
            print(f"OK: QDP.id.{key}")
    for key in ("fg", "cid"):
        if _has_field(idm, key) and _has_field(idp, key):
            _cmp(f"QDP.id.{key}", _field(idm, key), _field(idp, key), atol=0.0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-only",
        action="store_true",
        help="Only check full-order authority (no Python pkl required).",
    )
    args = p.parse_args(argv)

    report = optim2full_compare_f6_report()
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
        timing_log("compare_fence_f6", "START")
        print(
            f"OPTIM2FULL compare fence F6 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F6 authority-only check passed")
            return 0

        pkl = optim2full_f6_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F6 export missing ({pkl.name}). "
                "Run: python tests/demo1/optim2full/optim2full_export_fence_f6.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F6 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r}"
            )

        from scipy.io import loadmat

        raw = loadmat(str(optim2full_f6_mat()), simplify_cells=True)
        meta = raw.get("meta")
        note = str(meta.get("note") or "") if isinstance(meta, dict) else ""
        print(
            f"policy={blob.get('nonscalar_policy')} "
            f"T={blob.get('T')} vb_2_k={blob.get('vb_2_k')} "
            f"vb_elapsed_s={blob.get('vb_elapsed_s')} note={note!r}"
        )

        _cmp_scalar("RDP", raw["RDP"], blob["RDP"], "T")
        _cmp_scalar("RDP", raw["RDP"], blob["RDP"], "L")
        _cmp("sT", raw["sT"], blob["sT"], atol=0.0)
        print(f"OK: sT={np.asarray(blob['sT']).reshape(-1).tolist()}")
        _compare_qdp(raw["QDP"], blob["QDP"])
        print(
            f"OK totals: numeric={_STATS['numeric']} "
            f"handle_skip={_STATS['handle_skip']} empty={_STATS['empty']}"
        )
        print("OK: OPTIM2FULL fence F6 passed")
        timing_log(
            "compare_fence_f6",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F6")
        try:
            from tests.demo1.optim2full.optim2full_timing import timing_log

            timing_log("compare_fence_f6", "END FAIL")
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[optim2full_compare_fence_f6] report -> {report}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

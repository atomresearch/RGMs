#!/usr/bin/env python3
"""OPTIM2FULL fence F5 — compare Python first-VB + ``spm_Q2mdp`` vs MATLAB ``…_F5.mat``.

Authority note: ``Post first spm_MDP_VB_XXX (surveillance) + spm_Q2mdp.``

Compare surface (honest projection of the VB posterior):
  * ``RDP.T`` / ``RDP.L`` scalars.
  * ``QDP`` = ``spm_Q2mdp(RDP.Q,1)`` fields ``s u o X Y O j`` (numeric).
  * ``QDP.id`` numeric fields (``ge ff D E``); ``fg`` / ``cid`` are function
    handles (MATLAB ``MatlabFunction`` vs Python callable) — presence/type
    checked, value **not** (handle-skip honesty, see OPTIM2FULL.md OPEN RISK).

Tolerance policy (user-approved 2026-07-26; see OPTIM2FULL.md F5 tracker):
  * Decision / discrete: ``s``, ``u``, ``o``, ``O``, ``j``, ``id.*`` → ``atol=0``.
  * Continuous soft posteriors: ``X``, ``Y`` → ``atol=1e-12`` (belief-update ULP
    dust; maxabs observed ``~3.33e-16``, well inside band). Not a silent weaken.

The full post-VB ``RDP`` (Q/P/X/…) is projected through ``QDP`` rather than
compared field-by-field; ``QDP`` is what ``…_F5.mat`` persists as the fence
witness. Any red here (including RNG draw-count) is a first-red stop.

Report: ``matlab_custom/dem_drone_vi_compare_fence_f5_output.txt``
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
    optim2full_compare_f5_report,
    optim2full_f5_mat,
    optim2full_f5_pkl,
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
    """Flatten cell containers for compare.

    MATLAB ``QDP.Y/O/j`` load as ``(Ng,T)`` object ndarrays; Python stores nested
    ``list[Ng][T]``. Both must flatten to the same ``Ng*T`` leaf order (C / row-major
    matches ``ndarray.flat`` and ``for g: for t``).
    """
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
    """Honest MATLAB vector orientation: ``(N,)`` ≡ ``(N,1)`` ≡ ``(1,N)`` when size matches."""
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


# Soft continuous posteriors only (user-approved 2026-07-26). Observed F5
# maxabs X~3.33e-16 / Y~2.22e-16; band is tight vs project leaf 1e-10.
_SOFT_XY_ATOL = 1e-12


def _cmp(path: str, m: Any, p: Any, *, atol: float = 0.0) -> None:
    """Recursive numeric compare with handle-skip honesty.

    ``atol`` defaults to 0 (exact). Soft ``QDP.X``/``Y`` pass ``atol=_SOFT_XY_ATOL``.
    """
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
    # Continuous soft posteriors — approved soft band (belief-update ULP).
    for key in ("X", "Y"):
        _cmp(f"QDP.{key}", _field(qm, key), _field(qp, key), atol=_SOFT_XY_ATOL)
        print(f"OK: QDP.{key} (atol={_SOFT_XY_ATOL:g})")
    # Discrete / exact.
    for key in ("O", "j"):
        _cmp(f"QDP.{key}", _field(qm, key), _field(qp, key), atol=0.0)
        print(f"OK: QDP.{key}")
    idm, idp = _field(qm, "id"), _field(qp, "id")
    for key in ("ge", "ff", "D", "E"):
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

    report = optim2full_compare_f5_report()
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
        timing_log("compare_fence_f5", "START")
        print(
            f"OPTIM2FULL compare fence F5 — capture={CAPTURE_OPTIM2FULL_RAND_LEDGER}"
        )
        assert_optim2full_full_ledger_ok()
        print("OK authority: full-order ledger + F0–F6")
        if args.authority_only:
            print("OK: F5 authority-only check passed")
            return 0

        pkl = optim2full_f5_pkl()
        if not pkl.is_file():
            print(
                f"PENDING: Python F5 export missing ({pkl.name}). "
                "Run: python tests/dem_drone_vi/dem_drone_vi_export_fence_f5.py"
            )
            print("EXIT=2 (not a false green)")
            return 2

        with pkl.open("rb") as f:
            blob = pickle.load(f)
        if not isinstance(blob, dict):
            raise TypeError(f"F5 pkl must be dict, got {type(blob)}")
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            raise RuntimeError(
                f"refusing compare on pkl capture={blob.get('capture')!r}"
            )

        from scipy.io import loadmat

        raw = loadmat(str(optim2full_f5_mat()), simplify_cells=True)
        meta = raw.get("meta")
        note = str(meta.get("note") or "") if isinstance(meta, dict) else ""
        print(
            f"policy={blob.get('nonscalar_policy')} "
            f"T={blob.get('T')} vb_1_k={blob.get('vb_1_k')} "
            f"vb_elapsed_s={blob.get('vb_elapsed_s')} note={note!r}"
        )

        _cmp_scalar("RDP", raw["RDP"], blob["RDP"], "T")
        _cmp_scalar("RDP", raw["RDP"], blob["RDP"], "L")
        _compare_qdp(raw["QDP"], blob["QDP"])
        print(
            f"OK totals: numeric={_STATS['numeric']} "
            f"handle_skip={_STATS['handle_skip']} empty={_STATS['empty']}"
        )
        print("OK: OPTIM2FULL fence F5 passed")
        timing_log(
            "compare_fence_f5",
            f"END OK elapsed_s={_time.perf_counter()-_t0:.3f}",
        )
        return 0
    except Exception:
        traceback.print_exc()
        print("FAIL: OPTIM2FULL fence F5")
        try:
            from tests.dem_drone_vi.dem_drone_vi_timing import timing_log

            timing_log("compare_fence_f5", "END FAIL")
        except Exception:
            pass
        return 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        out_f.close()
        print(f"[dem_drone_vi_compare_fence_f5] report -> {report}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

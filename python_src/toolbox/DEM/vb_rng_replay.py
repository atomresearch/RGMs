"""W2 Phase 5-S-1 — optim-owned ``vb_rand_buf`` replay.

Also supports OPTIM2FULL drone ledger slices via an explicit buffer
(``reuse_matlab_draws_drone`` + ``matlab_rand_buf``) without loading Entry 12
``vb_rand_buf``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM import vb_instrumentation as _inst


def vb_load_matlab_rand_buf(path: Path | None = None) -> np.ndarray:
    """Load Atari Entry 12 ``vb_rand_buf`` (OPTIM1FULL / Validation 12 path)."""
    if path is not None:
        from scipy.io import loadmat

        if not path.is_file():
            raise FileNotFoundError(
                f"MATLAB VB rand buffer not found: {path}\n"
                "Run Entry 12 MATLAB dump (after entry12_preflight_vb_rand_k.py) to create it."
            )
        raw = loadmat(str(path))
        if "vb_rand_buf" not in raw:
            keys = sorted(k for k in raw if not k.startswith("__"))
            raise KeyError(f"expected vb_rand_buf in {path}, got keys={keys}")
        return np.asarray(raw["vb_rand_buf"], dtype=np.float64).ravel(order="F")
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_load_vb_rand_buf_for_tag

    return entry12_load_vb_rand_buf_for_tag()


class VbMatlabRandReplay:
    """Replay MATLAB ``rand(K,1)`` scalars through ``numpy.random.rand`` for ``_spm_sample``.

    Works for Entry 12 ``vb_rand_buf`` **or** any explicit scalar ledger slice
    (e.g. OPTIM2FULL ``dem_drone_rand_buf`` segment ``vb_1``).
    """

    __slots__ = ("_it", "_orig", "_used", "_k", "_label")

    def __init__(self, buf: np.ndarray, *, label: str = "vb_rand_buf") -> None:
        data = np.asarray(buf, dtype=np.float64).ravel(order="F")
        self._k = int(data.size)
        self._it = iter(data.tolist())
        self._orig = np.random.rand
        self._used = 0
        self._label = str(label)

    @property
    def draws_used(self) -> int:
        return int(self._used)

    @property
    def k(self) -> int:
        return int(self._k)

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError(
                "spm_MDP_VB_XXX reuse_matlab_draws: only scalar np.random.rand() is supported"
            )
        try:
            v = float(next(self._it))
            self._used += 1
            return v
        except StopIteration as e:
            raise RuntimeError(
                f"spm_MDP_VB_XXX reuse_matlab_draws: exhausted MATLAB {self._label} "
                "(Python drew more scalars than MATLAB; refresh K preflight and dump)"
            ) from e

    def __enter__(self) -> VbMatlabRandReplay:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        _VB_RAND_REPLAY_ITER = self._it
        _VB_RAND_REPLAY_ORIG_RAND = self._orig
        np.random.rand = self._shim  # type: ignore[method-assign]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        np.random.rand = self._orig  # type: ignore[method-assign]
        _VB_RAND_REPLAY_ITER = None
        _VB_RAND_REPLAY_ORIG_RAND = None
        if exc_type is not None:
            return
        try:
            next(self._it)
        except StopIteration:
            return
        raise RuntimeError(
            f"spm_MDP_VB_XXX reuse_matlab_draws: unused draws remain in {self._label} "
            "(Python drew fewer scalars than MATLAB; K preflight / OPTIONS mismatch)"
        )

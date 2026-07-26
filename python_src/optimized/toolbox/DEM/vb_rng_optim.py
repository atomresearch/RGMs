"""W2 Phase 5-S-1 — explicit VB RNG context (optim-owned replay).

- ``reuse_matlab_draws=True`` — Atari Entry 12 ``vb_rand_buf`` (unchanged).
- ``reuse_matlab_draws_drone=True`` — OPTIM2FULL drone ledger slice via required
  ``matlab_rand_buf`` (defaults off; does not load Entry 12 buffers).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM.vb_rng_replay_optim import (
    VbMatlabRandReplay,
    vb_load_matlab_rand_buf,
)


class VbRandContext:
    """Top-level VB scalar-``rand`` replay — no fidelity ``spm_MDP_VB_XXX`` import."""

    __slots__ = ("_reuse", "_reuse_drone", "_buf", "_replay")

    def __init__(
        self,
        *,
        reuse_matlab_draws: bool = False,
        reuse_matlab_draws_drone: bool = False,
        matlab_rand_buf: np.ndarray | None = None,
    ) -> None:
        self._reuse = bool(reuse_matlab_draws)
        self._reuse_drone = bool(reuse_matlab_draws_drone)
        self._buf = matlab_rand_buf
        self._replay: Any = None
        if self._reuse and self._reuse_drone:
            raise ValueError(
                "VbRandContext: reuse_matlab_draws and reuse_matlab_draws_drone "
                "are mutually exclusive"
            )

    @property
    def draws_used(self) -> int:
        if self._replay is None:
            return 0
        return int(getattr(self._replay, "draws_used", 0))

    def __enter__(self) -> VbRandContext:
        if _inst._VB_TIMING_DEPTH != 1:
            return self
        if self._reuse_drone:
            if self._buf is None:
                raise ValueError(
                    "reuse_matlab_draws_drone=True requires matlab_rand_buf="
                    "(OPTIM2FULL dem_drone_rand_buf segment slice, e.g. vb_1)"
                )
            self._replay = VbMatlabRandReplay(
                self._buf, label="dem_drone_rand_buf"
            )
            self._replay.__enter__()
        elif self._reuse:
            self._replay = VbMatlabRandReplay(vb_load_matlab_rand_buf())
            self._replay.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._replay is not None and _inst._VB_TIMING_DEPTH == 1:
            self._replay.__exit__(exc_type, exc, tb)
            self._replay = None

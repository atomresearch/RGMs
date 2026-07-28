"""OPTIM2FULL parity sign-off environment — declared MATLAB reuse fences.

Pins ``RGMS_OPTIM2FULL_*`` inject switches for the parity lane. Native / COLAB2
must **not** use this context (drop ledger / Engine MI-eig/sort deliberately).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

# DEM_drone_VI.m L54 — parity capture seed (not Atari rng(2)).
OPTIM2FULL_CANONICAL_RNG_SEED = 1


def optim2full_parity_fence_env_defaults() -> dict[str, str]:
    """
    Declared parity-only hooks (same *requirement class* as OPTIM1FULL Product B).

    Values are ``\"1\"`` by default on the parity lane. When a drone spine site is
    not yet wired, the corresponding kernel simply ignores the unset/unused hook;
    do not invent Atari Entry line numbers as drone fence names.
    """
    return {
        "RGMS_OPTIM2FULL_FSL_MATLAB_EIG": "1",
        "RGMS_OPTIM2FULL_FSL_MATLAB_MI": "1",
        "RGMS_OPTIM2FULL_FSL_LINK_DIR_MI": "1",
        "RGMS_OPTIM2FULL_RDP_MATLAB_EIG": "1",
        "RGMS_OPTIM2FULL_SPM_RDP_SORT_MATLAB": "1",
        # Pipeline site timing (gate/export) — not FSL kernel dumps.
        "RGMS_OPTIM2FULL_TIMING": "1",
        # FSL / MI / eig verbose dumps stay **off** unless the user exports
        # RGMS_OPTIM2FULL_FSL_TIMING=1 for an inspection run.
    }


@contextmanager
def optim2full_signoff_env() -> Iterator[None]:
    """Pin parity-lane MATLAB reuse env for OPTIM2FULL gates."""
    old: dict[str, str | None] = {}
    pinned = dict(optim2full_parity_fence_env_defaults())
    for key, value in pinned.items():
        old[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, prior in old.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior

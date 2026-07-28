"""OPTIM2FULL parity pipeline wall-clock timing (flush prints).

Pipeline scripts emit ``[optim2full_timing]`` when ``RGMS_OPTIM2FULL_TIMING`` is on
(default on for gate/export convenience).

Shared ``spm_faster_structure_learning_optim`` / MI / eig dumps use
``[fsl_timing]`` only when ``RGMS_OPTIM2FULL_FSL_TIMING=1`` — **default off**
(not pinned by ``optim2full_signoff_env``). Enable explicitly for inspection runs.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator


def optim2full_timing_enabled() -> bool:
    raw = str(os.getenv("RGMS_OPTIM2FULL_TIMING", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def fsl_timing_enabled() -> bool:
    """Detailed FSL kernel timing — default off unless OPTIM2FULL sign-off pins it."""
    raw = str(os.getenv("RGMS_OPTIM2FULL_FSL_TIMING", "0")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def timing_log(site: str, msg: str) -> None:
    if not optim2full_timing_enabled():
        return
    print(f"[optim2full_timing] {site}: {msg}", flush=True)


def fsl_timing_log(msg: str) -> None:
    if not fsl_timing_enabled():
        return
    print(f"[fsl_timing] {msg}", flush=True)


@contextmanager
def timed_site(site: str, detail: str = "") -> Iterator[None]:
    """Wall-time a pipeline site; always prints start/end when timing enabled."""
    extra = f" ({detail})" if detail else ""
    timing_log(site, f"START{extra}")
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        timing_log(site, f"END elapsed_s={dt:.3f}{extra}")

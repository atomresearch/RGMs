"""OPTIM1FULL W2 — fast ``spm_MDP_VB_XXX`` matching ``spm_MDP_VB_XXX.m`` structure.

**Authority:** ``XXX.md`` + ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m``.

**Status (2026-07-04):** **4-X-1** — thin public wrapper → ``run_vb`` only; no patch layer.

Prove equivalence: ``optim1full_vb_equivalence.py`` / ``--vb-optim-tier3f``.

OPTIM2FULL drone parity: pass ``reuse_matlab_draws_drone=True`` with
``matlab_rand_buf=<dem_drone_rand_buf segment slice>`` (defaults off; Atari
``reuse_matlab_draws`` path unchanged).
"""
from __future__ import annotations

from typing import Any

from python_src.toolbox.DEM.vb_entry import run_vb

__all__ = ["spm_MDP_VB_XXX", "run_vb"]


def spm_MDP_VB_XXX(
    RDP: Any,
    OPTIONS: Any = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    W2 optim lane — delegates to ``run_vb``.

    Nested hierarchical calls use ``run_child_vb`` (``vb_hierarchical``) — **4-N-1**.

    Keyword RNG (all default False / None — Atari-safe):
    - ``reuse_matlab_draws`` — Entry 12 ``vb_rand_buf``
    - ``reuse_matlab_draws_drone`` — OPTIM2FULL drone ledger; requires ``matlab_rand_buf``
    - ``matlab_rand_buf`` — explicit scalar draw slice for the drone path
    """
    if OPTIONS is None:
        OPTIONS = {}
    return run_vb(
        RDP,
        OPTIONS,
        monitoring=kwargs.get("monitoring", False),
        dump_subentries=kwargs.get("dump_subentries", False),
        reuse_matlab_draws=kwargs.get("reuse_matlab_draws", False),
        reuse_matlab_draws_drone=kwargs.get("reuse_matlab_draws_drone", False),
        matlab_rand_buf=kwargs.get("matlab_rand_buf", None),
    )

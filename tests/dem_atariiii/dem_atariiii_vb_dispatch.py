"""OPTIM1FULL W2 — VB module dispatch (fidelity vs optim).

Single policy surface for ``spm_MDP_VB_XXX`` vs ``spm_MDP_VB_XXX``.

**Lanes:**
- ``fidelity`` — historical Product B parity oracle. Since 2026-07-13 this is a
  **diagnostic-only** lane, reached on the dispatch surface *only* by an explicit
  ``--vb-fidelity`` / ``RGMS_OPTIM1FULL_VB_DEV_OPTIM=0``. The fidelity Entry-12 tier
  gates (``--tier3a/3e/3f`` without the ``vb-optim`` prefix) call ``spm_MDP_VB_XXX``
  directly and do **not** go through this dispatch surface.
- ``optim`` — W2 sign-off via ``optim1full_vb_optim_matlab_equivalence`` (frozen
  MATLAB ``pdp_mat``); also the go-forward compute lane for the integrated driver.
- ``dispatch`` — full driver default. **Resolves to ``optim`` by default** (OPTIM1FULL
  go-forward compute); resolves to ``fidelity`` only when explicitly disabled via
  ``--vb-fidelity`` / ``RGMS_OPTIM1FULL_VB_DEV_OPTIM`` ∈ {``0``,``false``,``no``,``off``}.

See ``OPTIM1FULL.md`` § **W2 reference — spm_MDP_VB_XXX** and
§ **Current status — optim adoption**.
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Callable, Literal

VbLane = Literal["dispatch", "fidelity", "optim"]

OPTIM1FULL_VB_DEV_OPTIM_ENV = "RGMS_OPTIM1FULL_VB_DEV_OPTIM"

_vb_dev_optim_override: bool | None = None


def configure_vb_dev_optim(enabled: bool | None) -> None:
    """Programmatic dev-lane switch (``None`` clears override → env only)."""
    global _vb_dev_optim_override
    _vb_dev_optim_override = enabled
    if enabled is True:
        os.environ[OPTIM1FULL_VB_DEV_OPTIM_ENV] = "1"
    elif enabled is False:
        os.environ[OPTIM1FULL_VB_DEV_OPTIM_ENV] = "0"


def add_vb_dev_optim_cli_argument(parser: argparse.ArgumentParser) -> None:
    """Register the optim/fidelity lane switches on an OPTIM1FULL driver CLI.

    ``--vb-dev-optim`` is retained for back-compat but is now a **no-op** (optim is the
    default). ``--vb-fidelity`` is the diagnostic escape hatch that forces the historical
    fidelity ``spm_MDP_VB_XXX`` on the dispatch surface.
    """
    parser.add_argument(
        "--vb-dev-optim",
        action="store_true",
        help="(back-compat no-op — optim is now the dispatch default)",
    )
    parser.add_argument(
        "--vb-fidelity",
        action="store_true",
        help=(
            "Diagnostic: force fidelity spm_MDP_VB_XXX on the dispatch surface "
            "(default is optim). Use only for fidelity-vs-optim investigation."
        ),
    )


def apply_vb_dev_optim_cli(ns: Any) -> bool:
    """Apply lane switches from a parsed namespace; return resolved live-lane state.

    ``--vb-fidelity`` is rejected: live library is the only public compute surface.
    """
    if bool(getattr(ns, "vb_fidelity", False)):
        raise RuntimeError(
            "dem_atariiii: --vb-fidelity removed (OPTIMCLEANUP Phase P); "
            "use live python_src.toolbox.DEM.spm_MDP_VB_XXX only"
        )
    if bool(getattr(ns, "vb_dev_optim", False)):
        configure_vb_dev_optim(True)
    return optim1full_vb_dev_optim_enabled()


def optim1full_vb_dev_optim_enabled() -> bool:
    """Return True when the dispatch lane should resolve to ``optim`` (the default).

    OPTIM1FULL go-forward compute is the optim lane (2026-07-13). Fidelity is a
    diagnostic escape hatch only: return False **iff** an explicit override is set to
    False, or ``RGMS_OPTIM1FULL_VB_DEV_OPTIM`` is one of {``0``,``false``,``no``,``off``}.
    """
    if _vb_dev_optim_override is not None:
        return bool(_vb_dev_optim_override)
    env = str(os.getenv(OPTIM1FULL_VB_DEV_OPTIM_ENV, "")).strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    return True


def resolve_vb_lane(lane: VbLane) -> Literal["fidelity", "optim"]:
    """Public DEM_AtariIII lane is always live (historical ``optim`` body)."""
    if lane == "fidelity":
        raise RuntimeError(
            "dem_atariiii: fidelity VB lane removed (OPTIMCLEANUP Phase P); "
            "live python_src.toolbox.DEM.spm_MDP_VB_XXX is canonical"
        )
    _ = optim1full_vb_dev_optim_enabled()  # env retained for subprocess compat
    return "optim"


def dem_atariiii_vb_dispatch_status() -> dict[str, Any]:
    """Resolved dispatch state for logs / export manifests."""
    return {
        "vb_lane_dispatch_resolves_to": resolve_vb_lane("dispatch"),
        "vb_dev_optim_env": os.getenv(OPTIM1FULL_VB_DEV_OPTIM_ENV, ""),
        "vb_dev_optim_override": _vb_dev_optim_override,
    }


def spm_mdp_vb_xxx_callable(lane: VbLane = "dispatch") -> Callable[..., Any]:
    """Return live canonical ``spm_MDP_VB_XXX`` (optim body; no archive/fidelity lane)."""
    resolve_vb_lane(lane)
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    return spm_MDP_VB_XXX


def spm_mdp_vb_xxx_rand_buf_patch_target(lane: VbLane = "dispatch") -> str:
    """Dotted path for ledger ``vb_rand_buf`` injection (live ``vb_rng`` by-value import)."""
    resolve_vb_lane(lane)
    return "python_src.toolbox.DEM.vb_rng.vb_load_matlab_rand_buf"


def spm_mdp_vb_xxx_patch_module_name(lane: VbLane = "dispatch") -> str:
    """Deprecated — use :func:`spm_mdp_vb_xxx_rand_buf_patch_target`."""
    target = spm_mdp_vb_xxx_rand_buf_patch_target(lane)
    return target.rsplit(".", 1)[0]


def spm_mdp_vb_xxx_timing_module(lane: VbLane = "dispatch") -> Any:
    """Import module for ``_VB_TIMING_DEPTH`` reset before each gate lane run."""
    resolve_vb_lane(lane)
    from python_src.toolbox.DEM import vb_instrumentation as mod

    return mod

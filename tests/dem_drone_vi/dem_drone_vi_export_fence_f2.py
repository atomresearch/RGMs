#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F2 fence (FSL).

Loads same-session F2 ``Q`` + sizes, runs ``spm_faster_structure_learning_optim``
with ``dx=[1,64]`` and dump-once MATLAB ``spm_rgm_group`` ``G`` inject
(``DEM_drone_VI_optim2full_F2_rgm_G.mat``). No live Entry4 Engine MI cell-push.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from tests.dem_drone_vi.dem_drone_vi_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.dem_drone_vi.dem_drone_vi_paths import (
        CAPTURE_OPTIM2FULL_RAND_LEDGER,
        optim2full_f1_pkl,
        optim2full_f2_mat,
        optim2full_f2_pkl,
        optim2full_f2_rgm_G_mat,
    )
    from tests.dem_drone_vi.dem_drone_vi_timing import timed_site, timing_log
    from python_src.toolbox.DEM.dem_drone_vi_lib import export_fence_f2_pkl

    with timed_site("export_fence_f2"):
        assert_optim2full_full_ledger_ok()
        g_mat = optim2full_f2_rgm_G_mat()
        if not g_mat.is_file():
            print(
                f"FAIL: missing F2 rgm G dump {g_mat.name}. "
                "Run once: python tests/dem_drone_vi/"
                "dem_drone_vi_capture_fsl_rgm_G.py",
                file=sys.stderr,
            )
            return 1
        f1_pkl = optim2full_f1_pkl()
        blob = export_fence_f2_pkl(
            optim2full_f2_pkl(),
            optim2full_f2_mat(),
            f1_pkl=f1_pkl if f1_pkl.is_file() else None,
            rgm_G_mat=g_mat,
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F2 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        mdp = blob.get("MDP")
        n_lev = len(mdp) if mdp is not None else -1
        hooks = blob.get("fsl_hooks") or {}
        print(
            f"OK: wrote {optim2full_f2_pkl().name} "
            f"levels={n_lev} Nx={blob.get('Nx')} "
            f"elapsed_s={blob.get('fsl_elapsed_s'):.1f} "
            f"hooks={hooks} "
            f"policy={blob.get('nonscalar_policy')}",
            flush=True,
        )
        timing_log(
            "export_fence_f2",
            f"OK levels={n_lev} fsl_elapsed_s={blob.get('fsl_elapsed_s')}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F5 fence (first VB + ``spm_Q2mdp``).

Rebuilds the packed RDP (F4 build) from green F3 pkl + same-session F1.mat
``mdp``, sets ``T=16``, runs ``spm_MDP_VB_XXX_optim`` under the drone ledger
``vb_1`` slice (``reuse_matlab_draws_drone=True``), then ``spm_Q2mdp`` and
attaches ``QDP.id = mdp_p.id`` (packed pre-``mdp2rdp`` process-model id).
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from tests.demo1.optim2full.optim2full_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.demo1.optim2full.optim2full_paths import (
        CAPTURE_OPTIM2FULL_RAND_LEDGER,
        optim2full_f1_mat,
        optim2full_f3_pkl,
        optim2full_f5_pkl,
    )
    from tests.demo1.optim2full.optim2full_timing import timed_site, timing_log
    from python_src.toolbox.DEM.DEM_drone_VI import export_fence_f5_pkl

    with timed_site("export_fence_f5"):
        assert_optim2full_full_ledger_ok()
        f3_pkl = optim2full_f3_pkl()
        if not f3_pkl.is_file():
            print(
                f"FAIL: missing F3 pkl {f3_pkl.name}. Run --fence-f3 first.",
                file=sys.stderr,
            )
            return 1
        f1_mat = optim2full_f1_mat()
        if not f1_mat.is_file():
            print(f"FAIL: missing F1.mat {f1_mat}", file=sys.stderr)
            return 1
        blob = export_fence_f5_pkl(
            optim2full_f5_pkl(),
            f3_pkl,
            f1_mat,
            T=16,
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F5 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        qdp = blob.get("QDP") or {}
        print(
            f"OK: wrote {optim2full_f5_pkl().name} "
            f"T={blob.get('T')} vb_1_k={blob.get('vb_1_k')} "
            f"vb_elapsed_s={blob.get('vb_elapsed_s'):.3f} "
            f"QDP.keys={sorted(qdp.keys()) if isinstance(qdp, dict) else '?'} "
            f"policy={blob.get('nonscalar_policy')}",
            flush=True,
        )
        timing_log(
            "export_fence_f5",
            f"OK vb_elapsed_s={blob.get('vb_elapsed_s')} "
            f"vb_1_k={blob.get('vb_1_k')}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

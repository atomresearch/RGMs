#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F6 fence (wayfinding VB + ``spm_Q2mdp``).

Rebuilds packed ``mdp`` from green F3 pkl + F1.mat, builds ``pdp`` with
``MAP`` priors and ``id.hid=sT``, ``spm_mdp2rdp``, ``T=4``, runs
``spm_MDP_VB_XXX_optim`` under ledger ``vb_2``, then ``spm_Q2mdp`` with
``QDP.id = pdp.id``.
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
        optim2full_f6_pkl,
    )
    from tests.demo1.optim2full.optim2full_timing import timed_site, timing_log
    from python_src.toolbox.DEM.dem_drone_vi_lib import export_fence_f6_pkl

    with timed_site("export_fence_f6"):
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
        blob = export_fence_f6_pkl(
            optim2full_f6_pkl(),
            f3_pkl,
            f1_mat,
            T=4,
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F6 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        qdp = blob.get("QDP") or {}
        print(
            f"OK: wrote {optim2full_f6_pkl().name} "
            f"T={blob.get('T')} vb_2_k={blob.get('vb_2_k')} "
            f"vb_elapsed_s={blob.get('vb_elapsed_s'):.3f} "
            f"sT={blob.get('sT')} "
            f"QDP.keys={sorted(qdp.keys()) if isinstance(qdp, dict) else '?'} "
            f"policy={blob.get('nonscalar_policy')}",
            flush=True,
        )
        timing_log(
            "export_fence_f6",
            f"OK vb_elapsed_s={blob.get('vb_elapsed_s')} "
            f"vb_2_k={blob.get('vb_2_k')}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

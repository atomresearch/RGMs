#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F3 fence (``spm_mdp_a2A``).

Consumes green F2 pkl MDP (post-FSL ``a``/``b``), peels FSL ``[tensor]``
wrappers, runs fidelity ``spm_mdp_a2A`` (default FIX.A/B=1). Not packing / F4.
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
        optim2full_f2_mat,
        optim2full_f2_pkl,
        optim2full_f3_pkl,
    )
    from tests.demo1.optim2full.optim2full_timing import timed_site, timing_log
    from python_src.toolbox.DEM.DEM_drone_VI import export_fence_f3_pkl

    with timed_site("export_fence_f3"):
        assert_optim2full_full_ledger_ok()
        f2_pkl = optim2full_f2_pkl()
        if not f2_pkl.is_file():
            print(
                f"FAIL: missing F2 pkl {f2_pkl.name}. Run --fence-f2 first.",
                file=sys.stderr,
            )
            return 1
        blob = export_fence_f3_pkl(
            optim2full_f3_pkl(),
            f2_pkl,
            f2_mat=optim2full_f2_mat(),
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F3 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        mdp = blob.get("MDP")
        n_lev = len(mdp) if mdp is not None else -1
        print(
            f"OK: wrote {optim2full_f3_pkl().name} "
            f"levels={n_lev} elapsed_s={blob.get('a2A_elapsed_s'):.3f} "
            f"policy={blob.get('nonscalar_policy')}",
            flush=True,
        )
        timing_log(
            "export_fence_f3",
            f"OK levels={n_lev} a2A_elapsed_s={blob.get('a2A_elapsed_s')}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

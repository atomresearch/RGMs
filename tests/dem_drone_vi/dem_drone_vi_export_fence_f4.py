#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F4 fence (id.A packing + ``spm_mdp2rdp``).

Consumes green F3 pkl MDP + same-session F1.mat ``mdp``. Not VB / F5.
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
        optim2full_f1_mat,
        optim2full_f3_pkl,
        optim2full_f4_pkl,
    )
    from tests.dem_drone_vi.dem_drone_vi_timing import timed_site, timing_log
    from python_src.toolbox.DEM.dem_drone_vi_lib import export_fence_f4_pkl

    with timed_site("export_fence_f4"):
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
        blob = export_fence_f4_pkl(
            optim2full_f4_pkl(),
            f3_pkl,
            f1_mat,
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F4 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        rdp = blob.get("RDP")
        pack = blob.get("pack_meta") or {}
        print(
            f"OK: wrote {optim2full_f4_pkl().name} "
            f"L={rdp.get('L') if isinstance(rdp, dict) else '?'} "
            f"n_factors={pack.get('n_factors')} "
            f"parents={pack.get('n_parent')} "
            f"skip_idD={pack.get('n_skip_empty_idD')} "
            f"elapsed_s={blob.get('mdp2rdp_elapsed_s'):.3f} "
            f"policy={blob.get('nonscalar_policy')}",
            flush=True,
        )
        timing_log(
            "export_fence_f4",
            f"OK mdp2rdp_elapsed_s={blob.get('mdp2rdp_elapsed_s')} "
            f"pack={pack}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

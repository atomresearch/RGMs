#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F0 fence from MATLAB F0 inject.

Non-scalar policy: ``W``/``D``/``MAP`` come from same-session
``DEM_drone_VI_optim2full_F0.mat`` (not scalar-ledger replay of ``spm_drone_unity``).

Requires durable Phase 0c authority (``--check-authority`` green).
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
        optim2full_f0_mat,
        optim2full_f0_pkl,
    )
    from tests.dem_drone_vi.dem_drone_vi_timing import timed_site, timing_log
    from python_src.toolbox.DEM.dem_drone_vi_lib import export_fence_f0_pkl

    with timed_site("export_fence_f0"):
        assert_optim2full_full_ledger_ok()
        blob = export_fence_f0_pkl(optim2full_f0_pkl(), optim2full_f0_mat())
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F0 inject capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        print(
            f"OK: wrote {optim2full_f0_pkl().name} "
            f"W{tuple(blob['W'].shape)} capture={blob['capture']}",
            flush=True,
        )
        timing_log("export_fence_f0", "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

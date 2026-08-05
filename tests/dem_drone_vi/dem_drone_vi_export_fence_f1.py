#!/usr/bin/env python3
"""OPTIM2FULL Phase 1 — export Python F1 fence.

F0 inject → assemble GDP → F1 ``PG.phi``/``FOV`` → ``spm_MDP_generate``
under ``pre_fsl`` ledger → assemble ``Q`` from generated ``PDP.s``.

Requires durable Phase 0c authority (``--check-authority`` green).
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_F1_POLICY = "same_session_F0_WD_and_F1_PG_angles_generate"


def main() -> int:
    from tests.dem_drone_vi.dem_drone_vi_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.dem_drone_vi.dem_drone_vi_paths import (
        CAPTURE_OPTIM2FULL_RAND_LEDGER,
        optim2full_f0_mat,
        optim2full_f1_mat,
        optim2full_f1_pkl,
    )
    from tests.dem_drone_vi.dem_drone_vi_timing import timed_site, timing_log
    from python_src.toolbox.DEM.dem_drone_vi_lib import export_fence_f1_pkl

    with timed_site("export_fence_f1"):
        assert_optim2full_full_ledger_ok()
        blob = export_fence_f1_pkl(
            optim2full_f1_pkl(), optim2full_f0_mat(), optim2full_f1_mat()
        )
        if blob.get("capture") != CAPTURE_OPTIM2FULL_RAND_LEDGER:
            print(
                f"FAIL: F1 capture={blob.get('capture')!r} "
                f"expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}",
                file=sys.stderr,
            )
            return 1
        if blob.get("nonscalar_policy") != _F1_POLICY:
            print(
                f"FAIL: nonscalar_policy={blob.get('nonscalar_policy')!r}",
                file=sys.stderr,
            )
            return 1
        if blob.get("generate_note") != "spm_MDP_generate_pre_fsl":
            print(
                f"FAIL: generate_note={blob.get('generate_note')!r}",
                file=sys.stderr,
            )
            return 1
        draws = int(blob.get("draws_used", -1))
        k = int(blob.get("pre_fsl_k", -1))
        if draws != k or k <= 0:
            print(f"FAIL: draw audit used={draws} expected={k}", file=sys.stderr)
            return 1
        pdp = blob["PDP"]
        t = int(pdp["T"]) if isinstance(pdp, dict) else int(getattr(pdp, "T"))
        print(
            f"OK: wrote {optim2full_f1_pkl().name} "
            f"Np={blob.get('Np')} T={t} draws={draws}/{k} "
            f"policy={blob.get('rng_policy')} "
            f"pg={blob.get('pg_angles_policy')} "
            f"note={blob.get('generate_note')}",
            flush=True,
        )
        timing_log(
            "export_fence_f1",
            f"OK Np={blob.get('Np')} T={t} draws={draws}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

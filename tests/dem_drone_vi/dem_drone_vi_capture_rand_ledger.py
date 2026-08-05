#!/usr/bin/env python3
"""OPTIM2FULL — one-shot MATLAB ``capture_optim2full_rand_ledger`` (Phase 0c).

One ``rng(1)`` session: full compute spine (plots omitted), scalar ``rand()`` ledger
with ordered segments, co-located fence mats F0–F6.

**Runtime:** FSL on 32³ + generate T=64 + two VB calls — expect tens of minutes to hours.
Do not run concurrent MATLAB Engine jobs on the same license.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.dem_drone_vi.dem_drone_vi_paths import (
        CAPTURE_OPTIM2FULL_RAND_LEDGER,
        optim2full_fixtures_dir,
        optim2full_matlab_custom_dir,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args(argv)

    fix = optim2full_fixtures_dir()
    fix.mkdir(parents=True, exist_ok=True)
    print(
        f"[dem_drone_vi_capture_rand_ledger] mode={CAPTURE_OPTIM2FULL_RAND_LEDGER} "
        f"fixtures={fix}",
        file=sys.stderr,
        flush=True,
    )

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eng.setenv("RGMS_OPTIM2FULL_FIXTURES_DIR", str(fix.resolve()), nargout=0)
        eng.cd(str(_REPO), nargout=0)
        eng.addpath(str(optim2full_matlab_custom_dir()), nargout=0)
        # Long-running: FSL + VB; no Engine timeout override available via simple API.
        eng.eval(
            f"DEM_drone_VI_optim2full_capture('{CAPTURE_OPTIM2FULL_RAND_LEDGER}');",
            nargout=0,
        )
    finally:
        eng.quit()

    print("[dem_drone_vi_capture_rand_ledger] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

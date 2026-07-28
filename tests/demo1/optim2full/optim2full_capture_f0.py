#!/usr/bin/env python3
"""OPTIM2FULL — one-shot MATLAB ``capture_optim2full_f0`` (Phase 0b).

Writes under ``tests/demo1/optim2full/fixtures``:
  - ``DEM_drone_VI_optim2full_F0.mat`` (D/W/MAP + sizes + meta)
  - ``optim2full_dem_drone_rand_buf.mat`` (scalar ``rand()`` ledger)
  - ``optim2full_rand_manifest.json``

Do not run concurrently with other MATLAB Engine sessions that need the same license.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim2full.optim2full_paths import (
        CAPTURE_OPTIM2FULL_F0,
        optim2full_fixtures_dir,
        optim2full_matlab_custom_dir,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args(argv)

    fix = optim2full_fixtures_dir()
    fix.mkdir(parents=True, exist_ok=True)
    print(
        f"[optim2full_capture_f0] mode={CAPTURE_OPTIM2FULL_F0} fixtures={fix}",
        file=sys.stderr,
        flush=True,
    )

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eng.setenv("RGMS_OPTIM2FULL_FIXTURES_DIR", str(fix.resolve()), nargout=0)
        eng.cd(str(_REPO), nargout=0)
        eng.addpath(str(optim2full_matlab_custom_dir()), nargout=0)
        eng.eval(
            f"DEM_drone_VI_optim2full_capture('{CAPTURE_OPTIM2FULL_F0}');",
            nargout=0,
        )
    finally:
        eng.quit()

    print("[optim2full_capture_f0] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

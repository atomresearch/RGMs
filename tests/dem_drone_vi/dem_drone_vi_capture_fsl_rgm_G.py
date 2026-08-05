#!/usr/bin/env python3
"""OPTIM2FULL — one-shot MATLAB dump of ``spm_rgm_group`` ``G`` for F2 inject.

Runs ``matlab_custom/optim2full/dem_drone_vi_capture_fsl_rgm_G.m`` via Engine:
loads same-session F2.mat ``Q``, runs MATLAB ``spm_faster_structure_learning``
with the path-shadow ``spm_rgm_group`` wrapper, writes
``DEM_drone_VI_optim2full_F2_rgm_G.mat``.

Does **not** re-capture the scalar rand ledger. Does **not** touch OPTIM1FULL.
May take tens of minutes (native MATLAB FSL on drone Q) — once.
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
        optim2full_f2_mat,
        optim2full_f2_rgm_G_mat,
        optim2full_matlab_custom_dir,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args(argv)

    f2 = optim2full_f2_mat()
    if not f2.is_file():
        print(f"FAIL: missing F2 authority {f2}", file=sys.stderr)
        return 1

    out = optim2full_f2_rgm_G_mat()
    custom = optim2full_matlab_custom_dir()
    print(
        f"[dem_drone_vi_capture_fsl_rgm_G] F2={f2.name} out={out.name} "
        f"custom={custom}",
        file=sys.stderr,
        flush=True,
    )

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        # Capture script addpath's optim2full ahead of SPM; do not leave it on
        # path for later Atari sessions — this Engine is quit after capture.
        eng.addpath(str(custom), nargout=0)
        eng.cd(str(_REPO), nargout=0)
        eng.dem_drone_vi_capture_fsl_rgm_G(nargout=0)
    finally:
        eng.quit()

    if not out.is_file():
        print(f"FAIL: dump not written: {out}", file=sys.stderr)
        return 1
    print(
        f"[dem_drone_vi_capture_fsl_rgm_G] OK wrote {out}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

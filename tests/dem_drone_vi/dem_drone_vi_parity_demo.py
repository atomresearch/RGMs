#!/usr/bin/env python3
"""DEM_drone_vi singular parity demo (OPTIMCLEANUP Phase P).

Requires **MATLAB 2024b** (Engine) to mint local fixtures, then runs the public
spine witness (F0→F6) against the live canonical library under
``python_src/toolbox/DEM/`` (especially ``DEM_drone_VI``).

Usage (from repo root, ``conda activate rgms``)::

    # Mint authority (once / after stochastic or capture-schema change):
    python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-ledger
    python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-f0
    python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-fsl-rgm-g

    # Full public witness:
    python tests/dem_drone_vi/dem_drone_vi_parity_demo.py

    # Or explicitly:
    python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --spine-e2e

Fixtures default to ``tests/dem_drone_vi/fixtures/`` (local; not shipped). Override
with ``RGMS_OPTIM2FULL_FIXTURES_DIR`` (historical env name retained for MATLAB capture).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_GATE = "tests/dem_drone_vi/dem_drone_vi_parity_gate.py"
_CAPTURE_LEDGER = "tests/dem_drone_vi/dem_drone_vi_capture_rand_ledger.py"
_CAPTURE_F0 = "tests/dem_drone_vi/dem_drone_vi_capture_f0.py"
_CAPTURE_G = "tests/dem_drone_vi/dem_drone_vi_capture_fsl_rgm_G.py"


def _run(rel: str, *extra: str) -> int:
    cmd = [sys.executable, str(_REPO / rel), *extra]
    print(f"[dem_drone_vi_parity_demo] RUN {' '.join(cmd)}", flush=True)
    return int(subprocess.call(cmd, cwd=str(_REPO)))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="DEM_drone_vi public MATLAB-Python parity demo (singular entry)."
    )
    p.add_argument(
        "--capture-ledger",
        action="store_true",
        help="MATLAB capture: full-order scalar rand ledger",
    )
    p.add_argument(
        "--capture-f0",
        action="store_true",
        help="MATLAB capture: F0 authority",
    )
    p.add_argument(
        "--capture-fsl-rgm-g",
        action="store_true",
        help="MATLAB capture: F2 RGM G helper mat",
    )
    p.add_argument(
        "--check-authority",
        action="store_true",
        help="ledger/F0 authority presence only",
    )
    p.add_argument(
        "--spine-e2e",
        action="store_true",
        help="F0→F6 export+compare (public CORE witness)",
    )
    args = p.parse_args(argv) if argv is not None else p.parse_args()

    selected = [
        args.capture_ledger,
        args.capture_f0,
        args.capture_fsl_rgm_g,
        args.check_authority,
        args.spine_e2e,
    ]
    if not any(selected):
        rc = _run(_GATE, "--spine-e2e")
        if rc != 0:
            return rc
        print("[dem_drone_vi_parity_demo] OK: spine-e2e", flush=True)
        return 0

    if args.capture_ledger:
        rc = _run(_CAPTURE_LEDGER)
        if rc != 0:
            return rc
    if args.capture_f0:
        rc = _run(_CAPTURE_F0)
        if rc != 0:
            return rc
    if args.capture_fsl_rgm_g:
        rc = _run(_CAPTURE_G)
        if rc != 0:
            return rc
    if args.check_authority:
        rc = _run(_GATE, "--check-authority")
        if rc != 0:
            return rc
    if args.spine_e2e:
        rc = _run(_GATE, "--spine-e2e")
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

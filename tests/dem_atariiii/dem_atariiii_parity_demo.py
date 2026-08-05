#!/usr/bin/env python3
"""DEM_AtariIII singular parity demo (OPTIMCLEANUP Phase P).

Requires **MATLAB 2024b** (Engine) to mint local fixtures, then runs the public
CORE witnesses against the live canonical library under ``python_src/toolbox/DEM/``.

Usage (from repo root, ``conda activate rgms``)::

    # Mint authority (once / after stochastic or capture-schema change):
    python tests/dem_atariiii/dem_atariiii_parity_demo.py --capture-ledger
    python tests/dem_atariiii/dem_atariiii_parity_demo.py --capture-plot-fixtures

    # Full public witness (pairing-audit + tier3g + plot-parity):
    python tests/dem_atariiii/dem_atariiii_parity_demo.py

    # Individual CORE modes:
    python tests/dem_atariiii/dem_atariiii_parity_demo.py --pairing-audit
    python tests/dem_atariiii/dem_atariiii_parity_demo.py --tier3g
    python tests/dem_atariiii/dem_atariiii_parity_demo.py --plot-parity

Fixtures default to ``tests/dem_atariiii/fixtures/`` (local; not shipped). Override
with ``RGMS_OPTIM1FULL_FIXTURES_DIR`` (historical env name retained for MATLAB capture).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_GATE = "tests/dem_atariiii/dem_atariiii_parity_gate.py"
_CAPTURE_LEDGER = "tests/dem_atariiii/dem_atariiii_capture_rand_ledger.py"
_CAPTURE_PLOT = "tests/dem_atariiii/dem_atariiii_capture_plot_fixtures.py"


def _run(rel: str, *extra: str) -> int:
    cmd = [sys.executable, str(_REPO / rel), *extra]
    print(f"[dem_atariiii_parity_demo] RUN {' '.join(cmd)}", flush=True)
    return int(subprocess.call(cmd, cwd=str(_REPO)))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="DEM_AtariIII public MATLAB-Python parity demo (singular entry)."
    )
    p.add_argument(
        "--capture-ledger",
        action="store_true",
        help="MATLAB capture: Model-B rand ledger (+ related authority)",
    )
    p.add_argument(
        "--capture-plot-fixtures",
        action="store_true",
        help="MATLAB capture: plot_ctx / 12PLOT oracles for plot-parity",
    )
    p.add_argument("--pairing-audit", action="store_true")
    p.add_argument("--tier3g", action="store_true")
    p.add_argument("--plot-parity", action="store_true")
    p.add_argument(
        "--plot-parity-check-only",
        action="store_true",
        help="plot-parity wiring/presence only",
    )
    p.add_argument(
        "--check-authority",
        action="store_true",
        help="authority presence only",
    )
    args = p.parse_args(argv) if argv is not None else p.parse_args()

    selected = [
        args.capture_ledger,
        args.capture_plot_fixtures,
        args.pairing_audit,
        args.tier3g,
        args.plot_parity,
        args.plot_parity_check_only,
        args.check_authority,
    ]
    if not any(selected):
        # Default full CORE ladder.
        for flag in ("--pairing-audit", "--tier3g", "--plot-parity"):
            rc = _run(_GATE, flag)
            if rc != 0:
                return rc
        print("[dem_atariiii_parity_demo] OK: pairing-audit + tier3g + plot-parity", flush=True)
        return 0

    if args.capture_ledger:
        rc = _run(_CAPTURE_LEDGER)
        if rc != 0:
            return rc
    if args.capture_plot_fixtures:
        rc = _run(_CAPTURE_PLOT)
        if rc != 0:
            return rc
    if args.check_authority:
        rc = _run(_GATE, "--check-authority")
        if rc != 0:
            return rc
    if args.pairing_audit:
        rc = _run(_GATE, "--pairing-audit")
        if rc != 0:
            return rc
    if args.tier3g:
        rc = _run(_GATE, "--tier3g")
        if rc != 0:
            return rc
    if args.plot_parity_check_only:
        rc = _run(_GATE, "--plot-parity-check-only")
        if rc != 0:
            return rc
    if args.plot_parity:
        rc = _run(_GATE, "--plot-parity")
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

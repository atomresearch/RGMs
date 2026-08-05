#!/usr/bin/env python3
"""OPTIM2FULL L3/L4 — Python-native ``DEM_drone_VI`` compute (+ optional plots).

Local-native product path (``OPTIM2FULL.md`` § COLAB2 / Local-native build order
**L3** compute, **L4** ``--plot``).

Usage::

    conda activate rgms
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py --seed 1
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py --plot
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py --plot --out-pkl path.pkl
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py --plot-from-pkl path.pkl
    python tests/demo1/optim2full/DEM_drone_VI_optim2full_python.py --no-fsl-timing

What this is
------------
Full script-order compute spine: ``rng(1)`` → ``spm_drone_unity`` → assemble
``mdp``+``GDP`` → ``spm_MDP_generate_optim`` (**no** ledger) → FSL (**no** ``G``
override) → ``spm_mdp_a2A`` → pack live ``mdp`` → VB T=16 → ``spm_Q2mdp`` →
wayfinding → VB T=4. **No** F*.mat injects, **no** PG-angle inject, **no**
``reuse_matlab_draws_drone``.

With ``--plot`` / ``RGMS_OPTIM2FULL_NATIVE_PLOT=1``: six library
``dem_drone_vi_plot_*`` final-frame PNGs under ``visualizations/optim2full_native/``
(mid-spine, COLAB2 cell order). **Not** MATLAB plot oracles / Atari
``--plot-parity``.

``--plot-from-pkl`` re-renders those six PNGs from a prior native blob (no
recompute) — useful after a compute-only L3 run that wrote ``--out-pkl``.

Live progress
-------------
``run_dem_drone_vi_native`` prints ``[native]`` START/END for every significant
segment. By default this CLI also sets ``RGMS_OPTIM2FULL_FSL_TIMING=1`` so FSL
emits ``[fsl_timing]`` lines (levels / ``spm_rgm_group`` / structure_fast).

What this is not
----------------
- Parity sign-off (that remains ``optim2full_parity_gate.py --spine-e2e`` / ``--fence-f*``).
- COLAB2 cells (delivery after L5 + one push G1).

Expected wall can be tens of minutes (native FSL MI/eig + two VBs). Do not treat
numeric drift vs MATLAB as a fail on this path. Fair FSL baseline ≈ MATLAB dump
capture ``meta.elapsed_s`` (~1431 s), not parity F2 with G override (~119 s).
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_SEG_ORDER = (
    "unity",
    "assemble",
    "generate",
    "assemble_Q",
    "fsl",
    "a2A",
    "pack_ida",
    "mdp2rdp_surveillance",
    "vb_surveillance",
    "q2mdp_surveillance",
    "wayfinding_pdp",
    "mdp2rdp_wayfinding",
    "vb_wayfinding",
    "q2mdp_wayfinding",
    "total",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "OPTIM2FULL L3/L4 native DEM_drone_VI compute "
            "(+ optional final-frame plots; no MATLAB injects)."
        )
    )
    parser.add_argument("--seed", type=int, default=1, help="np.random.seed (MATLAB rng(1))")
    parser.add_argument(
        "--T-surveillance",
        type=int,
        default=16,
        dest="T_surveillance",
        help="RDP.T for surveillance VB (MATLAB 16)",
    )
    parser.add_argument(
        "--T-wayfinding",
        type=int,
        default=4,
        dest="T_wayfinding",
        help="RDP.T for wayfinding VB (MATLAB 4)",
    )
    parser.add_argument(
        "--out-pkl",
        type=Path,
        default=None,
        help="Optional pickle of native result blob",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help=(
            "Enable L4 native final-frame plots "
            "(sets RGMS_OPTIM2FULL_NATIVE_PLOT=1). "
            "Writes six PNGs under visualizations/optim2full_native/."
        ),
    )
    parser.add_argument(
        "--plot-from-pkl",
        type=Path,
        default=None,
        help=(
            "L4 only: load a prior native blob and write six PNGs "
            "(no recompute). Mutually exclusive with a fresh compute run."
        ),
    )
    parser.add_argument(
        "--no-fsl-timing",
        action="store_true",
        help="Do not set RGMS_OPTIM2FULL_FSL_TIMING=1 (quieter FSL)",
    )
    parser.add_argument(
        "--no-rgm-time-segments",
        action="store_true",
        help="Disable live [rgm_timing] inside spm_rgm_group (default: enabled)",
    )
    args = parser.parse_args(argv)
    rgm_time_segments = not bool(args.no_rgm_time_segments)

    if args.plot_from_pkl is not None and args.plot:
        print(
            "[OPTIM2FULL native] FAIL: use either --plot (compute+plots) "
            "or --plot-from-pkl (plots only), not both",
            flush=True,
        )
        return 2

    if args.plot_from_pkl is not None:
        from python_src.toolbox.DEM.optim2full_native_plot import (
            run_all_native_plots_from_blob,
        )

        pkl_path = args.plot_from_pkl
        if not pkl_path.is_absolute():
            pkl_path = _REPO / pkl_path
        if not pkl_path.is_file():
            print(f"[OPTIM2FULL native L4] FAIL: missing pkl {pkl_path}", flush=True)
            return 1
        print(f"[OPTIM2FULL native L4] plot-from-pkl {pkl_path}", flush=True)
        with pkl_path.open("rb") as f:
            blob = pickle.load(f)
        meta = run_all_native_plots_from_blob(blob)
        print(
            f"[OPTIM2FULL native L4] OK EXIT=0 png_count={meta['png_count']} "
            f"out_dir={meta['out_dir']}",
            flush=True,
        )
        for p in meta["pngs"]:
            print(f"  {p}", flush=True)
        return 0

    if args.plot:
        os.environ["RGMS_OPTIM2FULL_NATIVE_PLOT"] = "1"
        print(
            "[OPTIM2FULL native L4] RGMS_OPTIM2FULL_NATIVE_PLOT=1 "
            "(six PNGs → visualizations/optim2full_native/)",
            flush=True,
        )

    if not args.no_fsl_timing:
        # Enable before importing FSL (env read at call time inside FSL — set early).
        os.environ["RGMS_OPTIM2FULL_FSL_TIMING"] = "1"
        print(
            "[OPTIM2FULL native L3] RGMS_OPTIM2FULL_FSL_TIMING=1 "
            "(use --no-fsl-timing to disable)",
            flush=True,
        )

    from python_src.toolbox.DEM.dem_drone_vi_lib import run_dem_drone_vi_native

    print(
        f"[OPTIM2FULL native L3] START seed={args.seed} "
        f"T_s={args.T_surveillance} T_w={args.T_wayfinding} "
        f"rgm_time_segments={rgm_time_segments} plot={bool(args.plot)}",
        flush=True,
    )
    t0 = time.perf_counter()
    try:
        blob = run_dem_drone_vi_native(
            seed=int(args.seed),
            T_surveillance=int(args.T_surveillance),
            T_wayfinding=int(args.T_wayfinding),
            rgm_time_segments=rgm_time_segments,
            do_plot=True if args.plot else None,
        )
    except Exception as exc:
        print(f"[OPTIM2FULL native L3] FAIL: {type(exc).__name__}: {exc}", flush=True)
        raise

    timing = blob.get("timing_s") or {}
    total = float(timing.get("total", time.perf_counter() - t0))
    print("[OPTIM2FULL native L3] timing_s summary:", flush=True)
    for k in _SEG_ORDER:
        if k in timing:
            print(f"  {k}: {timing[k]:.3f}", flush=True)
    for k, v in timing.items():
        if k not in _SEG_ORDER:
            print(f"  {k}: {float(v):.3f}", flush=True)

    if args.out_pkl is not None:
        out = args.out_pkl
        if not out.is_absolute():
            out = _REPO / out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as f:
            pickle.dump(blob, f, protocol=4)
        print(f"[OPTIM2FULL native L3] wrote {out}", flush=True)

    plot_meta = blob.get("_optim2full_native_plot")
    if isinstance(plot_meta, dict):
        print(
            f"[OPTIM2FULL native L4] png_count={plot_meta.get('png_count')} "
            f"out_dir={plot_meta.get('out_dir')}",
            flush=True,
        )
        for p in plot_meta.get("pngs") or []:
            print(f"  {p}", flush=True)

    print(
        f"[OPTIM2FULL native L3] OK EXIT=0 total_s={total:.3f} "
        f"Np={blob.get('Np')} Nu={blob.get('Nu')} lane={blob.get('lane')}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

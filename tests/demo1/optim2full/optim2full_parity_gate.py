#!/usr/bin/env python3
"""OPTIM2FULL thin parity gate.

Usage::

    python tests/demo1/optim2full/optim2full_parity_gate.py --check-authority
    python tests/demo1/optim2full/optim2full_parity_gate.py --fence-f0
    python tests/demo1/optim2full/optim2full_parity_gate.py --fence-f1
    python tests/demo1/optim2full/optim2full_parity_gate.py --fence-f2
    python tests/demo1/optim2full/optim2full_parity_gate.py --fence-f4
    python tests/demo1/optim2full/optim2full_parity_gate.py --spine-e2e
    python tests/demo1/optim2full/optim2full_parity_gate.py --fence-f0 --authority-only
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_SPINE_FENCES = ("f0", "f1", "f2", "f3", "f4", "f5", "f6")


def _run(script: str, extra: list[str] | None = None) -> int:
    from tests.demo1.optim2full.optim2full_timing import timing_log

    cmd = [sys.executable, str(_REPO / "tests" / "demo1" / "optim2full" / script)]
    if extra:
        cmd.extend(extra)
    print(f"[optim2full_parity_gate] run: {' '.join(cmd)}", flush=True)
    timing_log("parity_gate", f"subprocess START script={script}")
    t0 = time.perf_counter()
    rc = int(subprocess.call(cmd, cwd=str(_REPO)))
    timing_log(
        "parity_gate",
        f"subprocess END script={script} rc={rc} elapsed_s={time.perf_counter()-t0:.3f}",
    )
    return rc


def _run_one_fence(fence: str, *, authority_only: bool) -> tuple[int, float]:
    """Export (unless authority-only) then compare one fence. Returns (rc, elapsed_s)."""
    from tests.demo1.optim2full.optim2full_timing import timed_site

    export_script = f"optim2full_export_fence_{fence}.py"
    compare_script = f"optim2full_compare_fence_{fence}.py"
    detail = "authority-only" if authority_only else "export+compare"
    t0 = time.perf_counter()
    with timed_site(f"fence_{fence}", detail):
        if authority_only:
            rc = _run(compare_script, ["--authority-only"])
        else:
            rc = _run(export_script)
            if rc != 0:
                return rc, time.perf_counter() - t0
            rc = _run(compare_script)
    return rc, time.perf_counter() - t0


def _run_spine_e2e(*, authority_only: bool) -> int:
    """Phase-2 witness: authority check, then fresh F0→F6 in order with timing summary."""
    from tests.demo1.optim2full.optim2full_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.demo1.optim2full.optim2full_paths import optim2full_spine_e2e_report
    from tests.demo1.optim2full.optim2full_timing import timed_site, timing_log

    report_path = optim2full_spine_e2e_report()
    lines: list[str] = []
    mode = "authority-only" if authority_only else "export+compare"
    header = (
        f"OPTIM2FULL spine E2E ({mode}) - Phase 2 parity witness\n"
        f"Order: check-authority -> {' -> '.join(_SPINE_FENCES)}\n"
        "Stop at first non-zero rc. Per-fence compare tees remain under "
        "matlab_custom/optim2full_compare_fence_f*_output.txt.\n"
    )
    print(header, flush=True)
    lines.append(header.rstrip())

    t_all0 = time.perf_counter()
    with timed_site("check_authority"):
        try:
            assert_optim2full_full_ledger_ok()
        except Exception as exc:
            msg = f"FAIL --check-authority: {exc}"
            print(msg, file=sys.stderr, flush=True)
            lines.append(msg)
            report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return 1
        print("OK: OPTIM2FULL full-order ledger authority present", flush=True)
        lines.append("OK: OPTIM2FULL full-order ledger authority present")

    results: list[tuple[str, int, float]] = []
    for fence in _SPINE_FENCES:
        rc, elapsed = _run_one_fence(fence, authority_only=authority_only)
        results.append((fence, rc, elapsed))
        row = f"fence-{fence}: rc={rc} elapsed_s={elapsed:.3f}"
        print(f"[optim2full_spine_e2e] {row}", flush=True)
        lines.append(row)
        if rc != 0:
            total = time.perf_counter() - t_all0
            fail = (
                f"FAIL: spine E2E stopped at fence-{fence} "
                f"(rc={rc}); total_elapsed_s={total:.3f}"
            )
            print(fail, file=sys.stderr, flush=True)
            lines.append(fail)
            lines.append("SUMMARY (partial):")
            for f, r, e in results:
                lines.append(f"  {f}: rc={r} elapsed_s={e:.3f}")
            lines.append(f"  TOTAL: elapsed_s={total:.3f}")
            report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            timing_log("parity_gate", f"spine-e2e FAIL at {fence} total_s={total:.3f}")
            return rc

    total = time.perf_counter() - t_all0
    lines.append("SUMMARY:")
    for f, r, e in results:
        lines.append(f"  {f}: rc={r} elapsed_s={e:.3f}")
    lines.append(f"  TOTAL: elapsed_s={total:.3f}")
    ok = (
        f"OK: OPTIM2FULL spine E2E passed "
        f"(F0->F6 {mode}); total_elapsed_s={total:.3f}"
    )
    print(ok, flush=True)
    lines.append(ok)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[optim2full_spine_e2e] report: {report_path}", flush=True)
    timing_log("parity_gate", f"spine-e2e OK total_s={total:.3f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim2full.optim2full_timing import timed_site, timing_log

    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--check-authority",
        action="store_true",
        help="Full-order ledger + F0–F6 mats present/valid (Phase 0c durable product).",
    )
    g.add_argument(
        "--spine-e2e",
        action="store_true",
        help=(
            "Phase-2 parity witness: --check-authority then fresh F0->F6 "
            "export+compare in order; stop at first red; tee per-fence + "
            "total timing to matlab_custom/optim2full_spine_e2e_output.txt."
        ),
    )
    g.add_argument(
        "--fence-f0",
        action="store_true",
        help="Export F0 inject pkl (unless --authority-only) then compare vs MATLAB F0.",
    )
    g.add_argument(
        "--fence-f1",
        action="store_true",
        help="Export F1 (generate + pre_fsl + Q) then compare vs MATLAB F1.",
    )
    g.add_argument(
        "--fence-f2",
        action="store_true",
        help=(
            "Export F2 (FSL optim + dump-once rgm G inject) then compare vs "
            "MATLAB F2. Requires DEM_drone_VI_optim2full_F2_rgm_G.mat "
            "(optim2full_capture_fsl_rgm_G.py)."
        ),
    )
    g.add_argument(
        "--fence-f3",
        action="store_true",
        help=(
            "Export F3 (spm_mdp_a2A on F2 pkl MDP) then compare vs MATLAB F3. "
            "Requires green F2 pkl."
        ),
    )
    g.add_argument(
        "--fence-f4",
        action="store_true",
        help=(
            "Export F4 (id.A packing + spm_mdp2rdp on F3 pkl + F1.mat mdp) "
            "then compare RDP vs MATLAB F4. Requires green F3 pkl."
        ),
    )
    g.add_argument(
        "--fence-f5",
        action="store_true",
        help=(
            "Export F5 (first VB_optim under vb_1 + spm_Q2mdp on F3 pkl + "
            "F1.mat mdp; T=16) then compare QDP vs MATLAB F5. Requires green F3 pkl."
        ),
    )
    g.add_argument(
        "--fence-f6",
        action="store_true",
        help=(
            "Export F6 (wayfinding: pdp MAP+hid, mdp2rdp, VB_optim under vb_2, "
            "T=4, spm_Q2mdp) then compare QDP+sT vs MATLAB F6. Requires green F3 pkl."
        ),
    )
    p.add_argument(
        "--authority-only",
        action="store_true",
        help=(
            "With --fence-f0..--fence-f6 or --spine-e2e: compare without re-export. "
            "Not Phase-2 sign-off (fresh export+compare required)."
        ),
    )
    args = p.parse_args(argv)

    t_gate0 = time.perf_counter()
    timing_log("parity_gate", f"main START argv={argv!r}")

    if args.check_authority:
        from tests.demo1.optim2full.optim2full_authority import (
            assert_optim2full_full_ledger_ok,
        )

        with timed_site("check_authority"):
            try:
                assert_optim2full_full_ledger_ok()
            except Exception as exc:
                print(f"FAIL --check-authority: {exc}", file=sys.stderr)
                return 1
            print("OK: OPTIM2FULL full-order ledger authority present")
        timing_log(
            "parity_gate",
            f"main END elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return 0

    if args.spine_e2e:
        rc = _run_spine_e2e(authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END spine-e2e rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f6:
        rc, _ = _run_one_fence("f6", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f6 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f5:
        rc, _ = _run_one_fence("f5", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f5 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f4:
        rc, _ = _run_one_fence("f4", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f4 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f3:
        rc, _ = _run_one_fence("f3", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f3 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f2:
        rc, _ = _run_one_fence("f2", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f2 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    if args.fence_f1:
        rc, _ = _run_one_fence("f1", authority_only=bool(args.authority_only))
        timing_log(
            "parity_gate",
            f"main END fence-f1 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
        )
        return rc

    rc, _ = _run_one_fence("f0", authority_only=bool(args.authority_only))
    timing_log(
        "parity_gate",
        f"main END fence-f0 rc={rc} elapsed_s={time.perf_counter()-t_gate0:.3f}",
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

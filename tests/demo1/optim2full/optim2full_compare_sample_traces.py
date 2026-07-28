#!/usr/bin/env python3
"""OPTIM2FULL — compare Python vb_1 sample trace vs MATLAB dump-fork trace.

Paired RNG site-class compare (Entry 12 ``entry12_compare_sample_traces`` twin).
Does not rewrite the ledger. Exit 1 on call-count / site / pattern divergence.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.optim2full.optim2full_paths import optim2full_fixtures_dir


def _load_trace(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "trace" in raw:
        tr = raw["trace"]
        if isinstance(tr, list):
            return tr
        if tr is None:
            return []
    raise ValueError(f"unrecognized trace schema in {path}")


def _phase_runs(trace: list[dict]) -> list[tuple[str, int, int, int, int]]:
    runs: list[tuple[str, int, int, int, int]] = []
    for r in trace:
        key = (str(r.get("site")), int(r.get("depth") or 0))
        if runs and runs[-1][0] == key[0] and runs[-1][1] == key[1]:
            s, d, n, s0, _ = runs[-1]
            runs[-1] = (s, d, n + 1, s0, int(r.get("seq", s0)))
        else:
            seq = int(r.get("seq", len(runs)))
            runs.append((key[0], key[1], 1, seq, seq))
    return runs


def main() -> int:
    fix = optim2full_fixtures_dir()
    py_path = fix / "optim2full_sample_trace_vb_1.json"
    mat_path = fix / "optim2full_sample_trace_vb_1_mat.json"
    if not py_path.is_file():
        print(f"MISSING python trace: {py_path}", file=sys.stderr)
        return 2
    if not mat_path.is_file():
        print(f"MISSING matlab trace: {mat_path}", file=sys.stderr)
        return 2

    py_raw = json.loads(py_path.read_text(encoding="utf-8"))
    mat_raw = json.loads(mat_path.read_text(encoding="utf-8"))
    py_trace = _load_trace(py_path)
    # Drop soft-exhaust sentinel row (exhausted=True, out=None) from Python.
    py_trace = [r for r in py_trace if not r.get("exhausted")]
    mat_trace = _load_trace(mat_path)

    print(f"py_calls={len(py_trace)} mat_calls={len(mat_trace)}")
    print(
        "py_by_site=",
        dict(sorted(Counter(r.get("site") for r in py_trace).items())),
    )
    print(
        "mat_by_site=",
        dict(sorted(Counter(r.get("site") for r in mat_trace).items())),
    )

    if len(py_trace) != len(mat_trace):
        print(
            f"CALL_COUNT_MISMATCH py={len(py_trace)} mat={len(mat_trace)}",
            file=sys.stderr,
        )
        n = min(len(py_trace), len(mat_trace))
    else:
        n = len(py_trace)
        print("call_count_match ok")

    first_site = None
    first_pat = None
    first_draws = None
    for seq in range(n):
        pr = py_trace[seq]
        mr = mat_trace[seq]
        diffs = []
        for key in ("site", "pattern", "k_mask", "depth"):
            pv, mv = pr.get(key), mr.get(key)
            # MATLAB jsonencode may emit floats for ints.
            if key in ("k_mask", "depth"):
                try:
                    pv = int(pv) if pv is not None else None
                    mv = int(mv) if mv is not None else None
                except (TypeError, ValueError):
                    pass
            if pv != mv:
                diffs.append(f"{key} py={pv!r} mat={mv!r}")
        py_nd = int(pr.get("n_draws", -1))
        mat_py_p = int(mr.get("n_draws_py_parity", mr.get("n_draws", -1)))
        if py_nd != mat_py_p:
            diffs.append(f"n_draws_py_parity py={py_nd} mat_py_parity={mat_py_p}")
        if pr.get("site") != mr.get("site") and first_site is None:
            first_site = (seq, pr, mr, diffs)
        if pr.get("pattern") != mr.get("pattern") and first_pat is None:
            first_pat = (seq, pr, mr, diffs)
        if py_nd != mat_py_p and first_draws is None:
            first_draws = (seq, pr, mr, diffs)

    print("\npython phase runs (first 20):")
    for row in _phase_runs(py_trace)[:20]:
        print(f"  site={row[0]:26s} depth={row[1]} n={row[2]:6d} seq={row[3]}..{row[4]}")
    print("matlab phase runs (first 20):")
    for row in _phase_runs(mat_trace)[:20]:
        print(f"  site={row[0]:26s} depth={row[1]} n={row[2]:6d} seq={row[3]}..{row[4]}")

    if first_site:
        seq, pr, mr, diffs = first_site
        print("\nFIRST site mismatch at seq", seq)
        for d in diffs:
            print(" ", d)
        print(
            " py:",
            {k: pr.get(k) for k in ("site", "pattern", "n_draws", "k_mask", "out", "t_gen", "depth", "shape")},
        )
        print(
            " mat:",
            {
                k: mr.get(k)
                for k in (
                    "site",
                    "pattern",
                    "n_draws",
                    "n_draws_py_parity",
                    "k_mask",
                    "out",
                    "t_gen",
                    "depth",
                    "shape",
                )
            },
        )
    else:
        print("site: all match through", n)

    if first_pat:
        seq, pr, mr, diffs = first_pat
        print("\nFIRST pattern mismatch at seq", seq)
        for d in diffs:
            print(" ", d)
    else:
        print("pattern: all match through", n)

    if first_draws:
        seq, pr, mr, diffs = first_draws
        print("\nFIRST n_draws (py vs mat py-parity) mismatch at seq", seq)
        for d in diffs:
            print(" ", d)
    else:
        print("n_draws_py_parity: all match through", n)

    # If call counts differ and sites matched through the overlap, report the
    # first extra call on the longer side (honest over/under-draw localization).
    if len(py_trace) != len(mat_trace) and first_site is None:
        if len(py_trace) > len(mat_trace):
            r = py_trace[len(mat_trace)]
            print("\nFIRST EXTRA python call at seq", len(mat_trace))
            print(
                " py:",
                {k: r.get(k) for k in ("site", "pattern", "n_draws", "k_mask", "out", "t_gen", "depth", "shape")},
            )
        else:
            r = mat_trace[len(py_trace)]
            print("\nFIRST EXTRA matlab call at seq", len(py_trace))
            print(
                " mat:",
                {
                    k: r.get(k)
                    for k in (
                        "site",
                        "pattern",
                        "n_draws",
                        "n_draws_py_parity",
                        "k_mask",
                        "out",
                        "t_gen",
                        "depth",
                        "shape",
                    )
                },
            )

    mat_calls = mat_raw.get("spm_sample_calls") if isinstance(mat_raw, dict) else None
    py_k = py_raw.get("K") if isinstance(py_raw, dict) else None
    print(f"\nsummary: py_K={py_k} mat_spm_sample_calls={mat_calls}")

    if first_site or first_pat or first_draws or len(py_trace) != len(mat_trace):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

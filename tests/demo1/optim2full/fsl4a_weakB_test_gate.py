"""Weak-B test gate: wall + contract vs Tax (full-eig) baseline on native Q.

Contract (drone dx=1): same n_levels; L1 group membership sets; outcome-keyed
support ``a``; L2 group sets/sizes. Peel order / factor indices among the 12
active outcomes may differ.

Env: ``RGMS_RGM_WEAK_B`` default on in optim twin.
Run from repo root (``rgms``)::

    set RGMS_OPTIM2FULL_FSL_TIMING=1
    set RGMS_RGM_WEAK_B=1
    python tests/demo1/optim2full/fsl4a_weakB_test_gate.py
"""
from __future__ import annotations

import hashlib
import os
import pickle
import time
from pathlib import Path

import numpy as np

os.environ["RGMS_OPTIM2FULL_FSL_TIMING"] = "1"
os.environ.setdefault("RGMS_RGM_WEAK_B", "1")

from python_src.optimized.toolbox.DEM.spm_faster_structure_learning_optim import (
    spm_faster_structure_learning_optim,
)

FSL1A = [2338, 2345, 2343, 2339, 2341, 2342, 2340, 2344, 2346, 2347, 2348, 2337]


def group_sets(G):
    return [
        tuple(
            sorted(int(x) for x in np.asarray(g, dtype=np.int64).ravel(order="F").tolist())
        )
        for g in G
    ]


def peel_head(G, n=12):
    out = []
    for g in G[:n]:
        a = np.asarray(g, dtype=np.int64).ravel(order="F")
        out.append(int(a[0]) if a.size else None)
    return out


def outcome_a_bytes(lev, oid: int):
    A = lev["a"]
    x = A[oid - 1]
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    if hasattr(x, "toarray"):
        x = x.toarray()
    arr = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    return arr.shape, arr.ravel(order="F").tobytes()


def main() -> int:
    q_path = Path("tests/demo1/optim2full/python_native/DEM_drone_VI_optim2full_native.pkl")
    ref_path = Path(
        "tests/demo1/optim2full/python_native/DEM_drone_VI_optim2full_fsl_mdp_classA_ref.pkl"
    )
    blob = pickle.load(open(q_path, "rb"))
    ref_blob = pickle.load(open(ref_path, "rb"))
    Q = blob["Q"]
    Nx, Ny, Nz = int(blob["Nx"]), int(blob["Ny"]), int(blob["Nz"])
    ref = ref_blob["MDP_fsl"]
    print(
        f"Weak-B TEST START weak_b={os.getenv('RGMS_RGM_WEAK_B','1')!r} "
        f"Q_rows={len(Q)}",
        flush=True,
    )
    t0 = time.perf_counter()
    MDP = spm_faster_structure_learning_optim(
        Q, [Nx, Ny, Nz], [1, 64], rgm_time_segments=False
    )
    elapsed = time.perf_counter() - t0
    print(f"Weak-B TEST DONE elapsed_s={elapsed:.3f} n_levels={len(MDP)}", flush=True)

    print("--- Weak-B contract vs classA_ref (Tax-era structure) ---", flush=True)
    ok = len(ref) == len(MDP)
    print(f"n_levels ref={len(ref)} new={len(MDP)} equal={ok}", flush=True)

    for i in range(min(len(ref), len(MDP))):
        Gr, Gn = ref[i]["G"][1], MDP[i]["G"][1]
        set_eq = set(group_sets(Gr)) == set(group_sets(Gn))
        peel_eq = peel_head(Gr) == peel_head(Gn)
        print(
            f"L{i+1} n_groups ref={len(Gr)} new={len(Gn)} "
            f"set_eq={set_eq} peel_order_eq={peel_eq} "
            f"peel_head_new={peel_head(Gn)}",
            flush=True,
        )
        if not set_eq:
            ok = False
            print(
                f"  only_ref={list(set(group_sets(Gr))-set(group_sets(Gn)))[:3]} "
                f"only_new={list(set(group_sets(Gn))-set(group_sets(Gr)))[:3]}",
                flush=True,
            )

    # Outcome-keyed a for support ids
    a_eq = 0
    a_diff = 0
    for oid in FSL1A:
        try:
            if outcome_a_bytes(ref[0], oid) == outcome_a_bytes(MDP[0], oid):
                a_eq += 1
            else:
                a_diff += 1
        except Exception as exc:
            a_diff += 1
            print(f"  a oid={oid} ERROR {type(exc).__name__}:{exc}", flush=True)
    print(f"support_outcome_a_equal={a_eq}/12 diff={a_diff}", flush=True)
    if a_diff:
        ok = False

    # L2 sets already covered by set_eq loop
    verdict = "PASS" if ok else "FAIL"
    print(
        f"Weak-B contract verdict: {verdict} "
        f"(peel_order may differ; sets+outcome-a+levels required)",
        flush=True,
    )
    print("Weak-B TEST COMPLETE", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""OPTIM2FULL F5 — ``vb_1`` draw-index audit (drone twin of Entry 12 audit).

**Role:** Named OPTIM2FULL inspection for scalar-``rand`` / ``_spm_sample`` skew on
the surveillance VB fence. Reuses the Entry 12 *contract* (per-call site, pattern
``L0``/``L1``/``L2``/``N1``, first mismatch / overshoot) with the **drone** ledger
and **optim** VB path — do **not** run ``entry12_draw_index_audit.py`` on F5.

**Driver:** same pack as ``run_fence_f5`` → ``spm_MDP_VB_XXX_optim`` under
``reuse_matlab_draws_drone=True`` + ``vb_1`` slice (``k=25279``).

**Soft-exhaust:** when Python requests draw ``K+1``, record that ``_spm_sample``
row (site / pattern / ``k_mask`` / depth) and stop. Diagnostic mode does **not**
require ``unused_draws=0`` (that gate applies after the over-draw is fixed).

**Outputs:**
- ``matlab_custom/optim2full_draw_index_audit_results.json`` — summary (no full trace)
- ``tests/demo1/optim2full/fixtures/optim2full_sample_trace_vb_1.json`` — full trace

**Interpretation:** Fix the first ``pattern_draw_mismatch`` or the exhaustion site
class — **not** the ledger bound / ``K`` / ``numpy.random.seed``.
"""
from __future__ import annotations

import inspect
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_OUT_SUMMARY = _REPO / "matlab_custom" / "optim2full_draw_index_audit_results.json"
_TRACE_PATH = (
    _REPO
    / "tests"
    / "demo1"
    / "optim2full"
    / "fixtures"
    / "optim2full_sample_trace_vb_1.json"
)

_LAST_AUDIT_REPLAY: list[Any] = [None]
_TRACE_CTX: dict[str, Any] = {"t_gen": None, "pu_len": None}
# ``.m`` 1119/1123 branch census: why a hierarchical entry does (not) sample child u/s.
_HIER_BRANCH: list[dict[str, Any]] = []

# Optim call-site → stable site id (Entry 12 taxonomy, optim frame names).
_SITE_BY_FRAME: tuple[tuple[str, str], ...] = (
    ("_orch_prior_QP_paths_states_one_model", "policy"),
    ("_prior_QP_paths_states_one_model", "policy"),
    ("_gen_control_one_model", "control_P"),
    ("_gen_states_one_model", "state_ps"),
    ("_gen_u_paths_one_model", "gp_path_E"),
    ("_vb_gp_outcome_sample_index", "outcome_GP_A"),
    ("vb_orchestrator_generate_outcomes_if_options_o", "outcome_softmax"),
    ("vb_orchestrator_shared_probabilistic_outcomes", "outcome_shared_po"),
    ("vb_hierarchical_subordinate_outcomes_optim", "hierarchical"),
    ("vb_orchestrator_hierarchical_subordinate_outcomes", "hierarchical"),
    ("_spm_action", "child_spm_action"),
    ("_vb_run_partial_t_loop_optim", "vb_loop"),
    ("run_optim_vb", "vb_entry"),
    ("run_child_vb", "vb_entry_child"),
)

_PATTERN_EXPECTED_DRAWS: dict[str, int] = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "N1": 1,
    "N0": 1,
}


class SoftExhaustError(RuntimeError):
    """Python requested one more scalar than the ``vb_1`` slice provides."""


class _AuditingDroneRandReplay:
    """``VbMatlabRandReplay`` with history + soft-exhaust (no unused-draw raise)."""

    __slots__ = (
        "_it",
        "_orig",
        "_used",
        "_k",
        "_label",
        "history",
        "exhausted",
        "overshoot_requests",
    )

    def __init__(self, buf: np.ndarray, *, label: str = "dem_drone_rand_buf") -> None:
        data = np.asarray(buf, dtype=np.float64).ravel(order="F")
        self._k = int(data.size)
        self._it = iter(data.tolist())
        self._orig = np.random.rand
        self._used = 0
        self._label = str(label)
        self.history: list[tuple[int, float]] = []
        self.exhausted = False
        self.overshoot_requests = 0
        _LAST_AUDIT_REPLAY[0] = self

    @property
    def draws_used(self) -> int:
        return int(self._used)

    @property
    def k(self) -> int:
        return int(self._k)

    @property
    def draw_index(self) -> int:
        return int(self._used)

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError(
                "optim2full draw audit: only scalar np.random.rand() is supported"
            )
        try:
            v = float(next(self._it))
            self.history.append((self._used, v))
            self._used += 1
            return v
        except StopIteration as e:
            self.exhausted = True
            self.overshoot_requests += 1
            raise SoftExhaustError(
                f"optim2full draw audit: exhausted {self._label} "
                f"(used={self._used} k={self._k}; Python requested draw {self._used + 1})"
            ) from e

    def __enter__(self) -> "_AuditingDroneRandReplay":
        np.random.rand = self._shim  # type: ignore[method-assign]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        np.random.rand = self._orig  # type: ignore[method-assign]
        # Soft-exhaust / mid-run errors: do not enforce unused_draws here.
        return None


def _infer_site_from_stack(*, depth: int) -> str:
    """Map ``inspect.stack()`` to a stable site id (first matching optim frame)."""
    for fr in inspect.stack()[2:30]:
        name = fr.function
        ctx = "".join(fr.code_context or [])
        if name in ("_vb_spm_sample_column", "_spm_sample", "_logged_sample"):
            # Hierarchical body sites: distinguish GD / E / D from source line.
            if "GD" in ctx and "child" in ctx:
                return "child_GD"
            if '["E"]' in ctx or "child[\"E\"]" in ctx or "['E']" in ctx:
                return "child_E"
            if '["D"]' in ctx or "child[\"D\"]" in ctx or "['D']" in ctx:
                return "child_D"
            continue
        if name == "vb_hierarchical_subordinate_outcomes_optim":
            if "GD" in ctx:
                return "child_GD"
            if '["E"]' in ctx or "['E']" in ctx:
                return "child_E"
            if '["D"]' in ctx or "['D']" in ctx:
                return "child_D"
            return "hierarchical"
        for key, site in _SITE_BY_FRAME:
            if name == key:
                if depth >= 2 and site not in ("vb_loop", "vb_entry", "vb_entry_child", "hierarchical"):
                    return f"nested_{site}"
                return site
    return "unknown"


def _describe_input(p: Any) -> dict[str, Any]:
    pa = np.asarray(p)
    flat = pa.ravel(order="F")
    nz = int(np.count_nonzero(flat)) if flat.size else 0
    is_bool = pa.dtype == bool
    is_01 = False
    if not is_bool and flat.size and np.issubdtype(pa.dtype, np.number):
        is_01 = bool(np.all((flat == 0) | (flat == 1)))
    vals_head = [float(x) for x in flat[:8].tolist()]
    return {
        "dtype": str(pa.dtype),
        "shape": list(pa.shape),
        "nz": nz,
        "is_bool": is_bool,
        "is_01_numeric": is_01,
        "vals_head": vals_head,
    }


def _classify_pattern(p: Any, *, n_draws: int) -> tuple[str, int, str]:
    """Return (pattern_id, k_mask, kind) — same table as Entry 12."""
    del n_draws  # classification is from input mask, not observed draws
    pa = np.asarray(p)
    if pa.dtype == bool:
        k_mask = int(np.count_nonzero(pa))
        if k_mask == 1:
            pat = "L0"
        elif k_mask in (2, 3, 4):
            pat = "L2"
        else:
            pat = "L1"
        return pat, k_mask, "logical"
    flat = np.asarray(pa, dtype=np.float64).ravel(order="F")
    nz = int(np.count_nonzero(flat))
    total = float(np.sum(flat))
    if (not np.isfinite(total)) or total <= 0.0:
        return "N0", nz, "numeric_degenerate"
    return "N1", nz, "numeric"


def _patch_attr(mod: Any, name: str, value: Any) -> Any:
    old = getattr(mod, name)
    setattr(mod, name, value)
    return old


def _run_replay_trace() -> tuple[dict[str, Any], list[dict[str, Any]], SoftExhaustError | None]:
    from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
    from python_src.optimized.toolbox.DEM import vb_primitives_optim as prim
    from python_src.optimized.toolbox.DEM import vb_orchestrator_optim as orch
    from python_src.optimized.toolbox.DEM import vb_cold_native_optim as cold
    from python_src.optimized.toolbox.DEM import vb_rng_optim as rng_mod
    from python_src.optimized.toolbox.DEM import vb_rng_replay_optim as replay_mod
    from python_src.optimized.toolbox.DEM.spm_MDP_VB_XXX_optim import (
        spm_MDP_VB_XXX_optim,
    )
    from python_src.toolbox.DEM.dem_drone_vi_lib import _build_packed_rdp_from_f3_f1
    from tests.demo1.optim2full.optim2full_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.demo1.optim2full.optim2full_paths import (
        optim2full_f1_mat,
        optim2full_f3_pkl,
    )
    from tests.demo1.optim2full.optim2full_rand_ledger import (
        optim2full_rand_segment_slice,
    )
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env

    assert_optim2full_full_ledger_ok()
    f3_pkl = optim2full_f3_pkl()
    f1_mat = optim2full_f1_mat()
    if not f3_pkl.is_file():
        raise FileNotFoundError(f"missing F3 pkl {f3_pkl}")
    if not f1_mat.is_file():
        raise FileNotFoundError(f"missing F1.mat {f1_mat}")

    vb_slice, vb_seg = optim2full_rand_segment_slice("vb_1")
    k = int(vb_seg.k)
    summary: dict[str, Any] = {
        "segment": "vb_1",
        "K": k,
        "segment_start": int(vb_seg.start),
        "buf_label": "dem_drone_rand_buf",
        "trace_path": str(_TRACE_PATH),
        "driver": "spm_MDP_VB_XXX_optim+reuse_matlab_draws_drone",
        "T": 16,
    }

    RDP, _mdp_p, pack_meta, capture, _nu = _build_packed_rdp_from_f3_f1(
        f3_pkl, f1_mat, Nu=None
    )
    RDP["T"] = 16.0
    summary["capture"] = capture
    summary["pack_meta"] = {
        "n_parent": pack_meta.get("n_parent"),
        "n_skip_empty_idD": pack_meta.get("n_skip_empty_idD"),
    }

    trace: list[dict[str, Any]] = []
    orig_sample = prim._spm_sample
    soft_err: SoftExhaustError | None = None

    def _logged_sample(p: Any) -> int:
        ar = _LAST_AUDIT_REPLAY[0]
        i0 = 0 if ar is None else int(ar.draw_index)
        depth = int(getattr(_inst, "_VB_TIMING_DEPTH", 1) or 1)
        try:
            out = int(orig_sample(p))
            soft = False
        except SoftExhaustError as e:
            # Record the overshooting call, then propagate to stop the VB run.
            i1 = 0 if ar is None else int(ar.draw_index)
            n_draws = max(0, i1 - i0)  # usually 0 if raise before any draw
            # Soft-exhaust typically happens mid-sample: count requested draws from pattern.
            pat, k_mask, kind = _classify_pattern(p, n_draws=0)
            expected = _PATTERN_EXPECTED_DRAWS.get(pat, 1)
            # If exhaustion hit on the first scalar of this call, n_draws==0 observed.
            # Report expected as the intended consume for triage.
            desc = _describe_input(p)
            row = {
                "seq": len(trace),
                "site": _infer_site_from_stack(depth=depth),
                "pattern": pat,
                "kind": kind,
                "k_mask": k_mask,
                "draw_start": i0,
                "draw_end": i1,
                "n_draws": n_draws,
                "expected_n_draws": expected,
                "pattern_draw_ok": False,
                "exhausted": True,
                "out": None,
                "depth": depth,
                "t_gen": _TRACE_CTX.get("t_gen"),
                "error": str(e),
                **desc,
            }
            trace.append(row)
            raise
        i1 = 0 if ar is None else int(ar.draw_index)
        n_draws = i1 - i0
        pat, k_mask, kind = _classify_pattern(p, n_draws=n_draws)
        expected = _PATTERN_EXPECTED_DRAWS.get(pat, n_draws)
        desc = _describe_input(p)
        row = {
            "seq": len(trace),
            "site": _infer_site_from_stack(depth=depth),
            "pattern": pat,
            "kind": kind,
            "k_mask": k_mask,
            "draw_start": i0,
            "draw_end": i1,
            "n_draws": n_draws,
            "expected_n_draws": expected,
            "pattern_draw_ok": n_draws == expected,
            "exhausted": False,
            "out": out,
            "depth": depth,
            "t_gen": _TRACE_CTX.get("t_gen"),
            **desc,
        }
        if row["site"] == "policy":
            row["pu_len"] = _TRACE_CTX.get("pu_len")
        trace.append(row)
        return out

    # ``.m`` 1119 ``spm_is_process(mdp)`` / 1123 ``isfield(mdp,'GV')`` branch census.
    orig_is_process = prim._spm_is_process

    def _is_process_census(mdp: Any) -> bool:
        res = bool(orig_is_process(mdp))
        try:
            keys = set(mdp.keys()) if hasattr(mdp, "keys") else set()
        except Exception:
            keys = set()
        _HIER_BRANCH.append(
            {
                "call": len(_HIER_BRANCH),
                "draw_index": int(
                    getattr(_LAST_AUDIT_REPLAY[0], "draw_index", 0)
                    if _LAST_AUDIT_REPLAY[0] is not None
                    else 0
                ),
                "is_process": res,
                "has_GA": "GA" in keys,
                "has_GB": "GB" in keys,
                "has_GU": "GU" in keys,
                "has_GV": "GV" in keys,
                "has_u": "u" in keys,
                "has_s": "s" in keys,
                "n_B": len(mdp["B"]) if "B" in keys and isinstance(mdp.get("B"), list) else None,
                "n_GB": len(mdp["GB"]) if "GB" in keys and isinstance(mdp.get("GB"), list) else None,
            }
        )
        return res

    old_is_process = _patch_attr(prim, "_spm_is_process", _is_process_census)

    # Patch by-value imports (OPTIM1FULL lesson) + replay class used by VbRandContext.
    old_prim = _patch_attr(prim, "_spm_sample", _logged_sample)
    old_orch = _patch_attr(orch, "_spm_sample", _logged_sample)
    old_cold = _patch_attr(cold, "_spm_sample", _logged_sample)
    old_replay_cls = _patch_attr(replay_mod, "VbMatlabRandReplay", _AuditingDroneRandReplay)
    old_rng_cls = _patch_attr(rng_mod, "VbMatlabRandReplay", _AuditingDroneRandReplay)

    # Optional t_gen context from orchestrator generation entry.
    orig_gen = getattr(orch, "vb_orchestrator_generation_paths_states", None)
    orig_prior = None
    for cand in (
        "_orch_prior_QP_paths_states_one_model",
        "_prior_QP_paths_states_one_model",
    ):
        if hasattr(orch, cand):
            orig_prior = getattr(orch, cand)
            prior_name = cand
            break
    else:
        prior_name = None

    def _gen_hook(*args: Any, **kwargs: Any):
        # signature: (models, bundle, t_idx, ...)
        if len(args) >= 3:
            _TRACE_CTX["t_gen"] = int(args[2]) + 1
        return orig_gen(*args, **kwargs)

    def _prior_hook(*args: Any, **kwargs: Any):
        if len(args) >= 3:
            _TRACE_CTX["t_gen"] = int(args[2]) + 1
        if len(args) >= 4:
            pu = np.asarray(args[3], dtype=np.float64).ravel()
            _TRACE_CTX["pu_len"] = int(pu.size)
        return orig_prior(*args, **kwargs)

    old_gen = None
    old_prior = None
    if orig_gen is not None:
        old_gen = _patch_attr(orch, "vb_orchestrator_generation_paths_states", _gen_hook)
    if orig_prior is not None and prior_name is not None:
        old_prior = _patch_attr(orch, prior_name, _prior_hook)

    try:
        with optim2full_signoff_env():
            try:
                spm_MDP_VB_XXX_optim(
                    RDP,
                    reuse_matlab_draws_drone=True,
                    matlab_rand_buf=vb_slice,
                )
            except SoftExhaustError as e:
                soft_err = e
    finally:
        _patch_attr(prim, "_spm_is_process", old_is_process)
        _patch_attr(prim, "_spm_sample", old_prim)
        _patch_attr(orch, "_spm_sample", old_orch)
        _patch_attr(cold, "_spm_sample", old_cold)
        _patch_attr(replay_mod, "VbMatlabRandReplay", old_replay_cls)
        _patch_attr(rng_mod, "VbMatlabRandReplay", old_rng_cls)
        if old_gen is not None:
            _patch_attr(orch, "vb_orchestrator_generation_paths_states", old_gen)
        if old_prior is not None and prior_name is not None:
            _patch_attr(orch, prior_name, old_prior)

    ar = _LAST_AUDIT_REPLAY[0]
    total = int(ar.draw_index) if ar is not None else 0
    summary["replay"] = {
        "total_draws": total,
        "unused_draws": k - total,
        "exhausted": bool(getattr(ar, "exhausted", False)) if ar is not None else False,
        "overshoot_requests": int(getattr(ar, "overshoot_requests", 0)) if ar is not None else 0,
        "spm_sample_calls": len(trace),
        "soft_exhaust_message": str(soft_err) if soft_err is not None else None,
    }
    summary["hierarchical_branch_census"] = list(_HIER_BRANCH[:8])
    summary["hierarchical_branch_calls"] = len(_HIER_BRANCH)
    return summary, trace, soft_err


def _summarize_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    by_site = Counter(r["site"] for r in trace)
    by_pattern = Counter(r["pattern"] for r in trace)
    pattern_draw_mismatches = [r for r in trace if not r.get("pattern_draw_ok", True)]
    exhausted_rows = [r for r in trace if r.get("exhausted")]
    first_mismatch = pattern_draw_mismatches[0] if pattern_draw_mismatches else None
    first_exhaust = exhausted_rows[0] if exhausted_rows else None

    # Compact triage window around first mismatch / exhaust.
    anchor = first_mismatch or first_exhaust
    window: list[dict[str, Any]] = []
    if anchor is not None:
        i0 = int(anchor["seq"])
        lo = max(0, i0 - 8)
        hi = min(len(trace), i0 + 3)
        window = [
            {
                "seq": r["seq"],
                "site": r["site"],
                "pattern": r["pattern"],
                "draw_start": r["draw_start"],
                "n_draws": r["n_draws"],
                "expected_n_draws": r.get("expected_n_draws"),
                "depth": r["depth"],
                "t_gen": r.get("t_gen"),
                "k_mask": r.get("k_mask"),
                "nz": r.get("nz"),
                "shape": r.get("shape"),
                "is_bool": r.get("is_bool"),
                "exhausted": r.get("exhausted", False),
                "out": r.get("out"),
            }
            for r in trace[lo:hi]
        ]

    return {
        "by_site": dict(sorted(by_site.items())),
        "by_pattern": dict(sorted(by_pattern.items())),
        "pattern_draw_mismatch_count": len(pattern_draw_mismatches),
        "pattern_draw_mismatch_first10": [
            {
                "seq": r["seq"],
                "site": r["site"],
                "pattern": r["pattern"],
                "n_draws": r["n_draws"],
                "expected_n_draws": r.get("expected_n_draws"),
                "k_mask": r.get("k_mask"),
                "draw_start": r["draw_start"],
                "depth": r["depth"],
                "t_gen": r.get("t_gen"),
                "shape": r.get("shape"),
                "is_bool": r.get("is_bool"),
            }
            for r in pattern_draw_mismatches[:10]
        ],
        "first_pattern_mismatch": (
            {
                "seq": first_mismatch["seq"],
                "site": first_mismatch["site"],
                "pattern": first_mismatch["pattern"],
                "n_draws": first_mismatch["n_draws"],
                "expected_n_draws": first_mismatch.get("expected_n_draws"),
                "k_mask": first_mismatch.get("k_mask"),
                "draw_start": first_mismatch["draw_start"],
                "depth": first_mismatch["depth"],
                "t_gen": first_mismatch.get("t_gen"),
                "shape": first_mismatch.get("shape"),
                "is_bool": first_mismatch.get("is_bool"),
                "dtype": first_mismatch.get("dtype"),
            }
            if first_mismatch is not None
            else None
        ),
        "first_exhaust_site": (
            {
                "seq": first_exhaust["seq"],
                "site": first_exhaust["site"],
                "pattern": first_exhaust["pattern"],
                "k_mask": first_exhaust.get("k_mask"),
                "draw_start": first_exhaust["draw_start"],
                "expected_n_draws": first_exhaust.get("expected_n_draws"),
                "depth": first_exhaust["depth"],
                "t_gen": first_exhaust.get("t_gen"),
                "shape": first_exhaust.get("shape"),
                "is_bool": first_exhaust.get("is_bool"),
                "dtype": first_exhaust.get("dtype"),
                "error": first_exhaust.get("error"),
            }
            if first_exhaust is not None
            else None
        ),
        "triage_window": window,
    }


def main() -> int:
    summary, trace, soft_err = _run_replay_trace()
    trace_summary = _summarize_trace(trace)
    out: dict[str, Any] = {
        **summary,
        "trace_summary": trace_summary,
        "coherence": {
            "protocol": "optim2full_scalar_rand_log_v1 / vb_1 soft-exhaust audit",
            "note": (
                "Replay injects dem_drone_rand_buf[vb_1] through np.random.rand in "
                "optim _spm_sample. Fix site class (pattern/dtype/extra call), not K."
            ),
            "unused_draws_ok": summary["replay"]["unused_draws"] == 0
            and not summary["replay"]["exhausted"],
            "exhausted": bool(summary["replay"]["exhausted"]),
            "pattern_draw_ok": trace_summary["pattern_draw_mismatch_count"] == 0,
        },
    }

    _OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUT_SUMMARY.write_text(
        json.dumps({k: v for k, v in out.items()}, indent=2),
        encoding="utf-8",
    )
    _TRACE_PATH.write_text(
        json.dumps({**out, "trace": trace}, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(out, indent=2))
    print(f"wrote summary {_OUT_SUMMARY}")
    print(f"wrote trace ({len(trace)} rows) {_TRACE_PATH}")

    fm = trace_summary.get("first_pattern_mismatch")
    fe = trace_summary.get("first_exhaust_site")
    if fm is not None:
        print("[optim2full draw audit] FIRST pattern mismatch:", json.dumps(fm, indent=2))
    if fe is not None:
        print("[optim2full draw audit] FIRST exhaust site:", json.dumps(fe, indent=2))

    coh = out["coherence"]
    if soft_err is not None or not coh["unused_draws_ok"] or not coh["pattern_draw_ok"]:
        print(
            "[optim2full draw audit] FAIL: "
            f"unused_draws_ok={coh['unused_draws_ok']} "
            f"pattern_draw_ok={coh['pattern_draw_ok']} "
            f"exhausted={coh['exhausted']}",
            file=sys.stderr,
        )
        return 1
    print("[optim2full draw audit] OK: unused_draws=0 and all patterns match expected draws")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

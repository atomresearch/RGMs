"""
OPTIM1FULL Product B — parity contract (single reference for gates + drivers).

**Foundation:** OPTIM1FULL Product B = **verified OPTIM1 Product B (parity)** through Entry **12**
plus post–12 compute (NR, VB calls **3**/**4**, MI) on **one** Model **B** scalar ledger from
``capture_optim1full_rand_ledger``. Sign-off = Python full driver ≡ **OPTIM1FULL MATLAB capture**
(``tests/dem_atariiii/fixtures/``) — **not** re-proving OPTIM1 lane gates, **not** python-native Product A.

**Lanes (do not mix):**

| Lane | RNG | Compute | NR input | Compare target |
|------|-----|---------|----------|----------------|
| OPTIM1 Product **B** (#3) | DEMO1 replay buffers | ``run_dem_atariiii`` | N/A | DEMO1 ``tests/demo1/fixtures/`` |
| OPTIM1FULL tier **3g** | Ledger ``nr_game_*`` | NR only | Frozen ``MDP_pre.mat`` | ``MDP_post_nr.mat`` |
| OPTIM1FULL step **4a** | *(RETIRED)* | *(compute-redundant with pairing-audit + tier3g)* | — | — |

**OPTIM1 extent on Model B ledger (before NR):**

1. ``entries_1_11``: ledger replay + ``run_dem_atariiii(entry_stop=10)`` — **same OPTIM1 §2 stack**
2. ``vb_call1``: ``reuse_matlab_draws`` on ledger segment (Entry **11** VB)
3. GDP attach → ``MDP_pre_active_inference``

**NR:** ``active_inference_nr_loop`` + per-game ledger segment ``reuse_matlab_draws`` (tier **3g** lane).

**Persistence audit (B2):** staging ``mdp_pre`` vs authority ``MDP_pre.mat`` — no live driver.
Gate: ``--persistence-audit``.

**Pairing audit:** ``dem_atariiii_run_segment_isolated.py`` +
``dem_atariiii_compare_mdp_pre_pkl_to_mat.py`` — live Entries **1–11** (incl. VB call **1**) vs authority
``MDP_pre_active_inference.mat`` (``capture_optim1full_python_product_b``). Gate: ``--pairing-audit``.

**Step 4a RETIRED (2026-07-13):** ``--full-replay-integration`` is compute-redundant with
``--pairing-audit`` (live pre-NR ``MDP_pre`` incl. VB call **1**) + ``--tier3g`` (NR accumulation),
which share the same ``MDP_post_nr`` compare script and MATLAB-lineage authority. The gate now
exits **2**. Integrated optim adoption is witnessed by those two gates under the optim lane.

**Not on sign-off ladder:** bisect scripts, wrapper-vs-wrapper tests.

**Compare checkpoint:** ``MDP_post_nr`` after NR — not ``ctx['MDP']`` after VB **3**/**4**.
"""

from __future__ import annotations

# Normative gate CLI flags (``dem_atariiii_parity_gate.py``)
TIER_1 = "tier1"
TIER_2 = "tier2"
TIER_3G = "tier3g"
PAIRING_AUDIT = "pairing-audit"
PERSISTENCE_AUDIT = "persistence-audit"
FULL_REPLAY_INTEGRATION = "full-replay-integration"  # step 4a — RETIRED (redundant); gate exits 2
FULL_REPLAY = "full-replay"  # step 4b — optional completion smoke (not a mandatory parity gate)
PLOT_ORACLE = "plot-oracle"  # W1-C: fixture-first plot pytest (no VB)

__all__ = [
    "TIER_1",
    "TIER_2",
    "TIER_3G",
    "PAIRING_AUDIT",
    "PERSISTENCE_AUDIT",
    "FULL_REPLAY_INTEGRATION",
    "FULL_REPLAY",
    "PLOT_ORACLE",
]

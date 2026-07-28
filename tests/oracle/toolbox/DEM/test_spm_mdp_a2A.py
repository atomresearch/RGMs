"""Oracle: ``spm_mdp_a2A`` Pass-1 vs MATLAB semantics (synthetic + optional F2→F3).

Sign-off for OPTIM2FULL F3 remains ``optim2full_parity_gate.py --fence-f3``.
"""

from __future__ import annotations

import copy

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_mdp_a2A import spm_mdp_a2A


def test_spm_mdp_a2A_replaces_a_b_with_normalized_A_B():
    a0 = np.asarray([[4.0], [0.0], [4.0]], dtype=np.float64)
    b0 = np.asarray([[2.0, 0.0], [0.0, 2.0]], dtype=np.float64)
    mdp = [{"a": [a0.copy()], "b": [b0.copy()], "T": 2.0, "id": {"A": [1]}}]
    out = spm_mdp_a2A(copy.deepcopy(mdp))
    assert "a" not in out[0] and "b" not in out[0]
    assert "A" in out[0] and "B" in out[0]
    A_exp = spm_dir_norm(a0)
    B_exp = spm_dir_norm(b0)
    assert np.allclose(out[0]["A"][0], A_exp, rtol=0.0, atol=0.0)
    assert np.allclose(out[0]["B"][0], B_exp, rtol=0.0, atol=0.0)
    assert float(np.sum(out[0]["A"][0])) == 1.0


def test_spm_mdp_a2A_fix_flags_skip():
    a0 = np.ones((2, 1), dtype=np.float64)
    mdp = [{"a": [a0.copy()], "b": [np.eye(2)], "T": 1.0}]
    out = spm_mdp_a2A(copy.deepcopy(mdp), FIX={"A": 0, "B": 1})
    assert "a" in out[0] and "A" not in out[0]
    assert "b" not in out[0] and "B" in out[0]

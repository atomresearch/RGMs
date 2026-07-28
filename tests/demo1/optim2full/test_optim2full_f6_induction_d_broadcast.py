"""F6 induction contract: MATLAB ``and(Bf,D(:))`` row-broadcasts ``D``."""
from __future__ import annotations

import numpy as np
from scipy import sparse

from python_src.optimized.toolbox.DEM.vb_induction_optim import (
    _bf_apply_d_mask_sparse,
    _ind_bf_apply_d_mask_dense,
    _ind_run_goal_search,
)


def test_induction_d_column_broadcast_dense() -> None:
    Bf = np.asarray(
        [[True, False, True], [True, True, False], [False, True, True]],
        dtype=bool,
    )
    D_col = np.asarray([True, False, True], dtype=bool)
    got = _ind_bf_apply_d_mask_dense(Bf, D_col, D_col.astype(float))
    expected = Bf.astype(float) * D_col.reshape((-1, 1), order="F")
    np.testing.assert_array_equal(got, expected)


def test_induction_d_column_broadcast_sparse() -> None:
    Bf = sparse.csr_matrix(
        np.asarray(
            [[True, False, True], [True, True, False], [False, True, True]],
            dtype=bool,
        )
    )
    D_col = np.asarray([True, False, True], dtype=bool)
    got = _bf_apply_d_mask_sparse(Bf, D_col, D_col.astype(float))
    expected = Bf.toarray().astype(float) * D_col.reshape((-1, 1), order="F")
    np.testing.assert_array_equal(got.toarray(), expected)


def test_induction_existing_full_matrix_mask_remains_supported() -> None:
    Bf = np.ones((2, 2), dtype=bool)
    D_full = np.asarray([True, False, False, True], dtype=bool)
    got = _ind_bf_apply_d_mask_dense(Bf, D_full, D_full.astype(float))
    np.testing.assert_array_equal(
        got,
        D_full.reshape((2, 2), order="F").astype(float),
    )


def test_goal_search_restores_matlab_multifactor_tensor_shape() -> None:
    # MATLAB: reshape(P,[Ns,1]) with Ns=[2,2] has effective shape (2,2);
    # the trailing singleton is not materialised above rank 2.
    R, r = _ind_run_goal_search(
        hif_kept=[1, 2],
        ns_by_pos=[2, 2],
        l_dim=4,
        Bf_prop=np.eye(4, dtype=bool),
        Pf=np.asarray([[True], [False], [False], [False]], dtype=bool),
        hid=np.asarray([[1], [1]], dtype=float),
        d_tensor=True,
        d_flat=None,
        N=2,
        Q=[
            np.asarray([[1.0], [0.0]]),
            np.asarray([[1.0], [0.0]]),
        ],
        ws=None,
        ws_m=None,
        ws_t_col=None,
        _probe_ind=False,
        _PROBE_12F_PARENT=None,
    )
    assert R.shape == (2, 2)
    np.testing.assert_array_equal(r, np.asarray([1, 2]))
    assert float(np.max(R)) == 32.0

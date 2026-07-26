"""
OPTIM1 — active inference / generative roll-out (optimized lane).

OPTIM2FULL (2026-07-23): function-handle likelihood branch matching MATLAB
``spm_MDP_generate.m`` (``isa(A{g},'function_handle')``) for ``DEM_drone_vi`` /
``GDP.A = @spm_depth`` / ``@spm_state``. Pre-change backup:
``spm_MDP_generate_optim_bkp.py`` (same directory).

OPTIM2FULL (2026-07-23 bkp2): local ``_b_matrix_for_u`` preserves logical ``B``
dtype so place-factor sampling follows MATLAB ``islogical`` → ``randperm`` (k=1
consumes no scalar ``rand``). Backup: ``spm_MDP_generate_optim_bkp2.py``.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import scipy.sparse as sp

from python_src.spm_combinations import spm_combinations
from python_src.spm_kron import spm_kron
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_MDP_generate import (
    _spm_norm,
    _spm_sample,
)
from python_src.toolbox.DEM.spm_induction import spm_induction as _spm_induction
from python_src.toolbox.DEM.spm_parents import spm_parents


def _b_matrix_for_u(bf: Any, u_idx: int) -> np.ndarray:
    """MATLAB ``B(:,:,u)`` with trailing ``Nu=1`` folded to ``Ns×Ns``.

    OPTIM2FULL: do **not** coerce to float64. Logical place transitions must stay
    ``bool`` so ``_spm_sample`` uses the MATLAB ``islogical`` / ``randperm`` path
    (single-True column → no scalar ``rand`` draw).
    """
    arr = np.asarray(bf)
    if arr.ndim == 2:
        return arr
    return np.asarray(arr[:, :, int(u_idx) - 1])


def _is_likelihood_handle(ag: Any) -> bool:
    """MATLAB ``isa(A{g},'function_handle')`` — callable likelihood, not an array."""
    return callable(ag) and not isinstance(ag, (np.ndarray, np.generic))


def _as_models(mdp_in: Union[dict, List[dict]]) -> List[dict]:
    """checkX then return model list.

    OPTIM2FULL: ``spm_MDP_checkX`` still assumes numeric ``A{g}.shape`` (Atari).
    MATLAB ``size(@fh,1)==1``, so for handle likelihoods we temporarily stub
    ``A{g}`` as ``ones(1,1)`` around checkX (fills D/E/C), then restore handles.
    Does **not** edit ``spm_MDP_checkX.py``.
    """
    if isinstance(mdp_in, dict):
        models_in = [mdp_in]
    elif isinstance(mdp_in, list) and mdp_in and isinstance(mdp_in[0], dict):
        models_in = mdp_in
    else:
        raise TypeError("spm_MDP_generate_optim: MDP must be a dict or list of dicts")

    out: List[dict] = []
    for raw in models_in:
        mdp = copy.deepcopy(raw)
        A = mdp.get("A")
        handle_map: Dict[int, Any] = {}
        if isinstance(A, list):
            for g, ag in enumerate(A):
                if _is_likelihood_handle(ag):
                    handle_map[g] = ag
                    A[g] = np.ones((1, 1), dtype=np.float64)
        checked = spm_MDP_checkX(mdp)
        if handle_map:
            A2 = checked["A"]
            for g, fn in handle_map.items():
                A2[g] = fn
            checked["A"] = A2
        out.append(checked)
    return out


def spm_MDP_generate_optim(mdp_in: Union[dict, List[dict]]) -> Union[dict, List[dict]]:
    models = _as_models(mdp_in)
    nm = len(models)
    t = int(models[0]["T"])
    ng = [len(models[m]["A"]) for m in range(nm)]
    nf = [len(models[m]["B"]) for m in range(nm)]
    no: List[List[int]] = []
    nu: List[List[int]] = []
    ns: List[List[int]] = []
    for m in range(nm):
        # MATLAB: No(m,g)=size(A{g},1); size(@fh,1)==1 for function handles
        no_row: List[int] = []
        for g in range(ng[m]):
            ag = models[m]["A"][g]
            if _is_likelihood_handle(ag):
                no_row.append(1)
            else:
                no_row.append(int(np.asarray(ag).shape[0]))
        no.append(no_row)
        ns.append([int(np.asarray(models[m]["B"][f]).shape[0]) for f in range(nf[m])])
        nu.append(
            [
                int(
                    np.asarray(models[m]["B"][f]).shape[2]
                    if np.asarray(models[m]["B"][f]).ndim >= 3
                    else 1
                )
                for f in range(nf[m])
            ]
        )

    max_ng = max(ng) if ng else 0
    o_cell = [[[None for _ in range(t)] for _ in range(max_ng)] for _ in range(nm)]

    # a[m][g] may be ndarray (numeric A) or callable (handle) — MATLAB spm_norm
    # passes non-numeric A through unchanged.
    a: List[List[Any]] = [[None] * ng[m] for m in range(nm)]
    b: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    d: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    e: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    u_pol: List[np.ndarray] = []
    v_pol: List[np.ndarray] = []
    np_pol: List[int] = []
    id_list: List[dict] = []

    for m in range(nm):
        mdp = models[m]
        for g in range(ng[m]):
            ag = mdp["A"][g]
            if _is_likelihood_handle(ag):
                a[m][g] = ag
            else:
                a[m][g] = _spm_norm(np.asarray(ag, dtype=np.float64))
        for f in range(nf[m]):
            # MATLAB spm_norm: isnumeric(logical)==false → pass-through.
            # Keep bool place B so sampling uses islogical/randperm path.
            bf = np.asarray(mdp["B"][f])
            if bf.dtype == bool:
                b[m][f] = bf
            else:
                b[m][f] = _spm_norm(np.asarray(bf, dtype=np.float64))
            d[m][f] = _spm_norm(np.asarray(mdp["D"][f], dtype=np.float64))
            e[m][f] = _spm_norm(np.asarray(mdp["E"][f], dtype=np.float64))
        # MATLAB any(U,1): accept 1×Nf or length-Nf (squeezed dump / drone GDP).
        U_arr = np.asarray(mdp["U"], dtype=np.float64)
        if U_arr.ndim == 1:
            if int(U_arr.size) == int(nf[m]):
                u_row = U_arr != 0.0
            else:
                u_row = np.any(U_arr.reshape(1, -1), axis=0)
        else:
            u_row = np.any(U_arr, axis=0)
        u_row = np.asarray(u_row, dtype=bool).ravel(order="F")
        if int(u_row.size) != int(nf[m]):
            # pad/trim to Nf
            tmp = np.zeros(nf[m], dtype=bool)
            ncopy = min(int(u_row.size), int(nf[m]))
            tmp[:ncopy] = u_row[:ncopy]
            u_row = tmp
        k_list = np.flatnonzero(u_row) + 1
        nu_mk = [nu[m][int(i) - 1] for i in k_list.tolist()]
        u_mat = spm_combinations(np.asarray(nu_mk, dtype=np.float64))
        v = np.zeros((u_mat.shape[0], nf[m]), dtype=np.float64)
        for j, col in enumerate(k_list.tolist()):
            v[:, int(col) - 1] = u_mat[:, j]
        u_pol.append(u_row.astype(bool))
        v_pol.append(v)
        np_pol.append(int(v.shape[0]))
        s_new = np.zeros((nf[m], t), dtype=np.float64)
        try:
            s0 = np.asarray(mdp["s"], dtype=np.float64)
            if s0.shape == (nf[m], t):
                s_new[:, :] = s0
            else:
                s_flat = s0.ravel(order="F")
                for ii in np.flatnonzero(s_flat):
                    unr = np.unravel_index(int(ii), (nf[m], t), order="F")
                    s_new[unr] = s_flat[ii]
        except Exception:
            pass
        mdp["s"] = s_new
        u_new = np.zeros((nf[m], t), dtype=np.float64)
        try:
            u0 = np.asarray(mdp["u"], dtype=np.float64)
            if u0.shape == (nf[m], t):
                u_new[:, :] = u0
            else:
                u_flat = u0.ravel(order="F")
                for ii in np.flatnonzero(u_flat):
                    unr = np.unravel_index(int(ii), (nf[m], t), order="F")
                    u_new[unr] = u_flat[ii]
        except Exception:
            pass
        mdp["u"] = u_new
        mdp["o"] = np.zeros((ng[m], t), dtype=np.float64)
        id_list.append(copy.deepcopy(mdp["id"]))

    try:
        tau = max(float(models[-1].get("tau", 1.0)), 1.0)
    except Exception:
        tau = 1.0

    k_pol = [1 for _ in range(nm)]
    pk_list: List[np.ndarray] = []
    for m in range(nm):
        npm = np_pol[m]
        pk = (1.0 - 1.0 / tau) * np.eye(npm) + (1.0 / tau) / npm
        pk_list.append(_spm_norm(pk))

    g_prev = [np.zeros((np_pol[m], 1), dtype=np.float64) for m in range(nm)]

    for t_idx in range(1, t + 1):
        for m in range(nm):
            mdp = models[m]
            for f in range(nf[m]):
                if mdp["u"][f, t_idx - 1] == 0:
                    if t_idx > 1:
                        mdp["u"][f, t_idx - 1] = mdp["u"][f, t_idx - 2]
                    else:
                        pu = _spm_norm(e[m][f])
                        mdp["u"][f, t_idx - 1] = _spm_sample(pu)
            if t_idx > 1:
                if "hid" in id_list[m]:
                    k_pol[m] = _spm_sample(spm_softmax(g_prev[m]))
                else:
                    k_pol[m] = _spm_sample(pk_list[m][:, k_pol[m] - 1])
                for f in range(nf[m]):
                    if u_pol[m][f]:
                        mdp["u"][f, t_idx - 2] = v_pol[m][k_pol[m] - 1, f]
            for f in range(nf[m]):
                if mdp["s"][f, t_idx - 1] == 0:
                    if t_idx > 1:
                        bmat = _b_matrix_for_u(
                            b[m][f], int(mdp["u"][f, t_idx - 2])
                        )
                        ps = bmat[:, int(mdp["s"][f, t_idx - 2]) - 1]
                        # Preserve logical columns (MATLAB islogical → randperm).
                        if np.asarray(ps).dtype == bool:
                            ps = np.asarray(ps, dtype=bool).ravel(order="F")
                        else:
                            ps = np.asarray(ps, dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                    else:
                        ps = d[m][f]
                    mdp["s"][f, t_idx - 1] = _spm_sample(ps)

        for m in range(nm):
            mdp = models[m]
            for g in range(ng[m]):
                j, i = spm_parents(id_list[m], g + 1, mdp["s"][:, t_idx - 1])
                i_arr = np.atleast_1d(np.asarray(i, dtype=np.float64)).astype(int).ravel()
                j_arr = np.atleast_1d(np.asarray(j, dtype=np.float64)).astype(int).ravel()
                ag = mdp["A"][g]
                for o in i_arr.tolist():
                    ind = [int(mdp["s"][jj - 1, t_idx - 1]) for jj in j_arr.tolist()]
                    # MATLAB spm_MDP_generate.m ~L263–266:
                    #   if isa(A{g},'function_handle')
                    #       O = A{g}([ind{:}]);
                    #   else
                    #       O = A{g}(:,ind{:});
                    if _is_likelihood_handle(ag):
                        s_vec = np.asarray(ind, dtype=np.float64).ravel(order="F")
                        sub = ag(s_vec)
                    else:
                        sl = (slice(None),) + tuple(ii - 1 for ii in ind)
                        sub = ag[sl]
                    if sp.issparse(sub):
                        sub = sub.toarray()
                    col = np.asarray(sub)
                    col = np.reshape(col, (-1, 1), order="F")
                    o_cell[m][int(o) - 1][t_idx - 1] = col.astype(np.float64, copy=False)
                    sample_col = (
                        col if col.dtype == np.bool else col.astype(np.float64, copy=False)
                    )
                    mdp["o"][int(o) - 1, t_idx - 1] = _spm_sample(sample_col)

        for m in range(nm):
            mdp = models[m]
            if "hid" in id_list[m]:
                g_line = np.zeros((np_pol[m], 1), dtype=np.float64)
                bp = [[None for _ in range(np_pol[m])] for _ in range(nf[m])]
                q_row: List[sp.csr_matrix] = []
                for f in range(nf[m]):
                    sf = int(mdp["s"][f, t_idx - 1])
                    q_row.append(
                        sp.csr_matrix(
                            ([1.0], ([sf - 1], [0])),
                            shape=(ns[m][f], 1),
                            dtype=np.float64,
                        )
                    )
                    for k in range(np_pol[m]):
                        if v_pol[m][k, f] != 0:
                            bp[f][k] = _b_matrix_for_u(
                                b[m][f], int(v_pol[m][k, f])
                            )
                        else:
                            bp[f][k] = _b_matrix_for_u(
                                b[m][f], int(mdp["u"][f, t_idx - 1])
                            )
                r_mat, r_fac = _spm_induction(bp, q_row, t - t_idx + 1, id_list[m])
                if r_mat is not False and np.any(
                    np.asarray(r_mat, dtype=np.float64).ravel()
                ):
                    p_map: Dict[Tuple[int, int], np.ndarray] = {}
                    fac_order = [
                        int(f) for f in np.asarray(r_fac, dtype=np.int64).ravel(order="F")
                    ]
                    for k in range(1, np_pol[m] + 1):
                        for ff in fac_order:
                            col = bp[ff - 1][k - 1][:, int(mdp["s"][ff - 1, t_idx - 1]) - 1]
                            p_map[(ff, k)] = np.asarray(col, dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                        cols_k = [p_map[(ff, k)] for ff in fac_order]
                        blk_k = np.asarray(cols_k[0], dtype=np.float64).reshape(
                            -1, 1, order="F"
                        )
                        for j in range(1, len(cols_k)):
                            pj = np.asarray(cols_k[j], dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                            blk_k = np.kron(blk_k, pj)
                        rv = (
                            np.asarray(r_mat, dtype=np.float64)
                            .ravel(order="F")
                            .reshape(1, -1)
                        )
                        g_line[k - 1, 0] = float(np.asarray(rv @ blk_k).squeeze())
                g_prev[m] = g_line.copy()

    for m in range(nm):
        mdp = models[m]
        mdp["T"] = t
        mdp["O"] = [[o_cell[m][g][tt] for tt in range(t)] for g in range(ng[m])]

    if isinstance(mdp_in, dict):
        return models[0]
    return models

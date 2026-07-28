"""Pass-1 translation of ``spm_Q2mdp.m`` (VB ``Q`` record → MDP-like struct).

No ``_optim`` twin — OPTIM2FULL F5 calls this fidelity module after VB.
"""

from __future__ import annotations

from typing import Any, MutableMapping, Optional

import numpy as np

from python_src.spm_cat import spm_cat


def spm_Q2mdp(Q: MutableMapping[str, Any], n: Optional[Any] = None) -> dict[str, Any]:
    """MATLAB ``mdp = spm_Q2mdp(Q,n)`` — default ``n = 1``.

    Unpacks level-``n`` cells of the hierarchical VB ``Q`` record into an MDP-like
    dict. ``Q.X{n}(f,:)`` is concatenated with ``spm_cat`` per factor.
    """
    # checks
    #--------------------------------------------------------------------------
    if n is None:
        n = 1
    n_i = int(np.asarray(n).reshape(-1)[0])

    mdp: dict[str, Any] = {}
    mdp["s"] = _cell_get(Q["s"], n_i - 1)
    mdp["u"] = _cell_get(Q["u"], n_i - 1)

    Xn = _cell_get(Q["X"], n_i - 1)
    nf = _x_nrows(Xn)
    X_out: list[Any] = [None] * nf
    for f in range(nf):
        # MATLAB: mdp.X{f,1} = spm_cat(Q.X{n}(f,:));
        X_out[f] = spm_cat(_x_row(Xn, f))
    mdp["X"] = X_out

    mdp["Y"] = _cell_get(Q["Y"], n_i - 1)
    mdp["O"] = _cell_get(Q["O"], n_i - 1)
    mdp["o"] = _cell_get(Q["o"], n_i - 1)
    mdp["j"] = _cell_get(Q["j"], n_i - 1)

    # sizes of factors and modalities
    #--------------------------------------------------------------------------
    return mdp


def _cell_get(cell: Any, index0: int) -> Any:
    """1-based MATLAB ``C{i}`` ↔ 0-based Python index into list / object array."""
    if isinstance(cell, list):
        return cell[index0]
    arr = np.asarray(cell, dtype=object)
    if arr.dtype != object:
        # simplify_cells may collapse a 1-level cell to a bare array
        if index0 != 0:
            raise IndexError(
                f"spm_Q2mdp: non-cell field index n={index0 + 1} but array is bare"
            )
        return cell
    flat = arr.ravel(order="F")
    return flat[index0]


def _x_nrows(Xn: Any) -> int:
    if isinstance(Xn, list):
        if len(Xn) == 0:
            return 0
        # list-of-rows (nf x T cell as Python list[list]) vs flat factor list
        if isinstance(Xn[0], (list, tuple)):
            return len(Xn)
        # nf×1 cell stored as flat list of T-length rows? treat as nf factors
        return len(Xn)
    arr = np.asarray(Xn, dtype=object)
    if arr.dtype != object:
        return int(arr.shape[0]) if arr.ndim >= 1 else 0
    if arr.ndim == 0:
        return 1
    return int(arr.shape[0])


def _x_row(Xn: Any, f0: int) -> list[Any]:
    """MATLAB ``Q.X{n}(f,:)`` → Python list of column cells for ``spm_cat``."""
    if isinstance(Xn, list):
        row = Xn[f0]
        if isinstance(row, (list, tuple)):
            return list(row)
        # single-factor cell that is already a concatenated matrix — wrap as 1-cell
        return [row]
    arr = np.asarray(Xn, dtype=object)
    if arr.dtype != object:
        # numeric (nf, ...) — treat each row as one factor already cat'd
        return [arr[f0]]
    if arr.ndim == 1:
        return [arr.flat[f0]]
    # (nf, T) object cell
    return [arr[f0, j] for j in range(arr.shape[1])]

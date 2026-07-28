"""Pass-1 translation of ``spm_mdp_a2A.m`` (Dirichlet counts → probabilities).

No ``_optim`` twin — OPTIM2FULL calls this fidelity module (inventory § C/F).
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional, Sequence, Union

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm


def spm_mdp_a2A(
    MDP: Sequence[MutableMapping[str, Any]],
    FIX: Optional[Union[Mapping[str, Any], Any]] = None,
) -> list[MutableMapping[str, Any]]:
    """Dirichlet counts into probabilities — mirror ``spm_mdp_a2A.m``.

    Parameters
    ----------
    MDP :
        Hierarchical cell of MDP dicts (Python list). Each level may carry
        Dirichlet cells ``a`` / ``b`` (list or object ndarray of tensors).
    FIX :
        Optional struct-like with fields ``A`` / ``B`` (default both 1).
        When true, replace ``a→A`` / ``b→B`` via ``spm_dir_norm`` and remove
        the count fields.

    Returns
    -------
    list
        Same MDP list, mutated in place (MATLAB field replace / ``rmfield``).
    """
    # defaults — MATLAB: if nargin < 2, FIX.A = 1; FIX.B = 1; end
    if FIX is None:
        fix_a, fix_b = 1, 1
    else:
        fix_a = int(_fix_get(FIX, "A", 1))
        fix_b = int(_fix_get(FIX, "B", 1))

    # prior concentration parameters
    # ==========================================================================
    nm = len(MDP)
    for n in range(nm):
        mdp = MDP[n]

        # remove Dirichlet counts if requested
        # ----------------------------------------------------------------------
        if fix_a:
            a_cell = mdp["a"]
            ng = _numel_cell(a_cell)
            A: list[Any] = [None] * ng
            for g in range(ng):
                ag = _cell_get(a_cell, g)
                if not callable(ag):
                    A[g] = spm_dir_norm(ag)
                else:
                    A[g] = ag
            mdp["A"] = A
            del mdp["a"]
        if fix_b:
            b_cell = mdp["b"]
            nf = _numel_cell(b_cell)
            B: list[Any] = [None] * nf
            for f in range(nf):
                bf = _cell_get(b_cell, f)
                if not callable(bf):
                    B[f] = spm_dir_norm(bf)
                else:
                    B[f] = bf
            mdp["B"] = B
            del mdp["b"]

    return list(MDP)


def _fix_get(fix: Any, name: str, default: int) -> Any:
    if isinstance(fix, Mapping):
        return fix.get(name, default)
    return getattr(fix, name, default)


def _numel_cell(cell: Any) -> int:
    if isinstance(cell, list):
        return len(cell)
    if isinstance(cell, np.ndarray) and cell.dtype == object:
        return int(cell.size)
    raise TypeError(
        f"spm_mdp_a2A expected cell list/object array for a/b, got {type(cell)}"
    )


def _cell_get(cell: Any, i: int) -> Any:
    if isinstance(cell, list):
        return cell[i]
    if isinstance(cell, np.ndarray) and cell.dtype == object:
        return cell.ravel(order="F")[i]
    raise TypeError(
        f"spm_mdp_a2A expected cell list/object array for a/b, got {type(cell)}"
    )

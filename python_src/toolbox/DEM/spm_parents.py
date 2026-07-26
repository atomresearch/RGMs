"""
Parents and children of MDP likelihood mappings (MATLAB-compatible).

Translated from spm_parents.m (Pass 1 faithful transliteration).

OPTIM2FULL (2026-07-23): non-cell ``id.fg`` / ``id.gg`` may be a function handle
(MATLAB ``id.fg(g,[s{:}])`` — call) or a numeric array (index). Pre-change backup:
``spm_parents_bkp.py`` (same directory).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _is_cell_q(Q) -> bool:
    """MATLAB iscell(Q)."""
    return isinstance(Q, (list, tuple))


def _is_matlab_cell(x: Any) -> bool:
    """MATLAB iscell — list/tuple of entries (not ndarray, not bare callable)."""
    return isinstance(x, (list, tuple))


def _is_likelihood_map_handle(x: Any) -> bool:
    """MATLAB function_handle used as id.fg / id.gg."""
    return callable(x) and not isinstance(x, (np.ndarray, np.generic, list, tuple))


def _s_from_q_cell(id_ff, Q) -> list:
    """MATLAB: for f=1:Ns, [~,m]=max(Q{id.ff(f)}); s{f}=m; (1-based m)."""
    ff = np.asarray(id_ff, dtype=np.int64).ravel()
    s: list = []
    for f in range(ff.size):
        qf = np.asarray(Q[ff[f] - 1], dtype=float).ravel()
        m = int(np.argmax(qf) + 1)
        s.append(m)
    return s


def _s_from_q_numeric(id_ff, Q) -> list:
    """MATLAB: s = num2cell(Q(id.ff)); — values become 1-based scalars in s."""
    qv = np.asarray(Q, dtype=float).ravel()
    ff = np.asarray(id_ff, dtype=np.int64).ravel()
    sub = qv[ff - 1]
    return [int(x) for x in sub.ravel().tolist()]


def _unwrap_id_a_entry(id_a_g: Any) -> Any:
    """MATLAB ``id.A{g}`` may be wrapped ``{1}`` in Python."""
    if isinstance(id_a_g, (list, tuple)) and len(id_a_g) == 1:
        return id_a_g[0]
    return id_a_g


def _cell_multi_get(cur, indices_1based: list):
    """MATLAB id.fg{g}{s{:}} / id.gg{g}{s{:}} with 1-based indices in s."""
    if len(indices_1based) == 1:
        return cur[int(indices_1based[0]) - 1]
    if len(indices_1based) == 2:
        r = int(indices_1based[0]) - 1
        c = int(indices_1based[1]) - 1
        return cur[r][c]
    out = cur
    for idx in indices_1based:
        out = out[int(idx) - 1]
    return out


def _fg_gg_resolve(map_obj: Any, g: int, s: list) -> Any:
    """MATLAB ``id.fg`` / ``id.gg`` branch (L66–70 / L78–83).

    - cell: ``map{g}{s{:}}``
    - else: ``map(g,[s{:}])`` — function call **or** numeric indexing
    """
    if _is_matlab_cell(map_obj):
        return _cell_multi_get(map_obj[g - 1], s)
    s_vec = np.asarray(s, dtype=np.float64).ravel(order="F")
    if _is_likelihood_map_handle(map_obj):
        # MATLAB: j = id.fg(g,[s{:}])
        return map_obj(g, s_vec)
    # numeric (or array-like): j = id.fg(g,[s{:}])
    arr = np.asarray(map_obj)
    cols = np.asarray(s, dtype=np.int64).ravel()
    return np.asarray(arr[g - 1, cols - 1])


def spm_parents(id: dict, g: int, Q):
    """
    FORMAT [j,i] = spm_parents(id,g,Q)

    id — dict mimicking a MATLAB struct. Keys use MATLAB names ('A','ff','fg','gg').
    g — MATLAB 1-based index into id.A / id.fg / id.gg rows (same as MATLAB).
    """
    if "ff" in id:
        if _is_cell_q(Q):
            s = _s_from_q_cell(id["ff"], Q)
        else:
            s = _s_from_q_numeric(id["ff"], Q)

        if "fg" in id:
            j = _fg_gg_resolve(id["fg"], g, s)
        else:
            j = _unwrap_id_a_entry(id["A"][g - 1])

        if "gg" in id:
            i = _fg_gg_resolve(id["gg"], g, s)
        else:
            i = g

        return j, i

    j = _unwrap_id_a_entry(id["A"][g - 1])
    i = g
    return j, i
